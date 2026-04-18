"""
Twilio SMS Service Module

Encapsulates Twilio client initialization, phone number cleaning,
and SMS sending logic for the Marketing SMS Module.
"""

import asyncio
import os
import re
import time
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

# --- Opt-out / Permanent Failure Detection ---

# Twilio error codes that indicate permanent failures (not worth retrying)
PERMANENT_FAIL_CODES = {"21610", "30005", "21211"}

# Keywords that indicate a recipient has opted out
STOP_WORDS = {"stop", "unsubscribe", "cancel", "end", "quit"}

# How many Twilio messages to scan for bad numbers
BAD_NUMBER_FETCH_LIMIT = 10000

# Firestore collection for real-time opt-out storage
_OPT_OUTS_COLLECTION = "opt_outs"

# Firestore collection tracking active batch sends across instances
_BATCHES_COLLECTION = "batches"

# Maximum concurrent Twilio API calls for batch sending
_SEND_CONCURRENCY = 10


# --- Cross-instance batch cancellation (Firestore-backed) ---


async def register_batch(batch_id: str) -> None:
    """Create the Firestore doc that other instances use to signal a cancel."""
    from app.database import _get_db, firestore
    db = _get_db()
    if not db or not firestore:
        return
    try:
        await db.collection(_BATCHES_COLLECTION).document(batch_id).set({
            "cancelled": False,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Could not register batch {batch_id} in Firestore: {e}")


async def is_batch_cancelled(batch_id: str) -> bool:
    """Check Firestore for the cross-instance cancel flag.

    Best-effort: on error returns False (don't surprise-cancel a live batch
    because Firestore hiccupped). The local asyncio.Event remains authoritative
    for same-instance cancels.
    """
    from app.database import _get_db
    db = _get_db()
    if not db:
        return False
    try:
        doc = await db.collection(_BATCHES_COLLECTION).document(batch_id).get()
        if not doc.exists:
            return False
        return bool(doc.to_dict().get("cancelled", False))
    except Exception as e:
        logger.error(f"Batch cancel-check failed for {batch_id}: {e}")
        return False


async def mark_batch_cancelled(batch_id: str) -> bool:
    """Write the cancel flag visible to every instance. True = write succeeded."""
    from app.database import _get_db
    db = _get_db()
    if not db:
        return False
    try:
        await db.collection(_BATCHES_COLLECTION).document(batch_id).set(
            {"cancelled": True}, merge=True
        )
        return True
    except Exception as e:
        logger.error(f"Could not mark batch {batch_id} cancelled: {e}")
        return False


async def clear_batch(batch_id: str) -> None:
    """Delete the Firestore marker after a batch ends (best-effort)."""
    from app.database import _get_db
    db = _get_db()
    if not db:
        return
    try:
        await db.collection(_BATCHES_COLLECTION).document(batch_id).delete()
    except Exception as e:
        logger.warning(f"Could not clear batch {batch_id} marker: {e}")

# --- Recently Sent Tracker (30-min dedup, Firestore-backed) ---

_DEDUP_TTL = 1800  # 30 minutes
_SENT_LOG_COLLECTION = "sent_log"


async def _is_recently_sent(phone_stripped: str) -> bool:
    """Check Firestore if this number was sent to within the dedup window.

    Dedup is advisory — a Firestore hiccup returns False so sends proceed.
    Compliance-critical filters (opt-outs) live in fetch_opt_outs, not here.
    """
    from app.database import _get_db
    db = _get_db()
    if not db:
        return False

    try:
        doc = await db.collection(_SENT_LOG_COLLECTION).document(phone_stripped).get()
        if not doc.exists:
            return False
        data = doc.to_dict()
        sent_at = data.get("sent_at")
        if sent_at is None:
            return False
        if hasattr(sent_at, 'timestamp'):
            return (time.time() - sent_at.timestamp()) < _DEDUP_TTL
        return False
    except Exception as e:
        logger.error(f"Dedup check failed for {phone_stripped} — may double-send: {e}")
        return False


async def _mark_sent(phone_stripped: str) -> None:
    """Record in Firestore that a message was sent to this number."""
    from app.database import _get_db, firestore
    db = _get_db()
    if not db or not firestore:
        return

    try:
        await db.collection(_SENT_LOG_COLLECTION).document(phone_stripped).set({
            "sent_at": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        logger.error(f"Dedup mark failed for {phone_stripped} — future dedup may miss: {e}")


# --- Twilio Client Singleton ---

_twilio_client: Optional[Client] = None


def get_twilio_client() -> Client:
    """
    Get or create the Twilio client singleton.
    
    Uses API Key authentication (more secure than Auth Token).
    Required environment variables:
    - TWILIO_ACCOUNT_SID
    - TWILIO_API_KEY_SID
    - TWILIO_API_KEY_SECRET
    
    Raises:
        ValueError: If Twilio credentials are not configured.
    """
    global _twilio_client
    
    if _twilio_client is None:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        api_key_sid = os.environ.get("TWILIO_API_KEY_SID")
        api_key_secret = os.environ.get("TWILIO_API_KEY_SECRET")
        
        if not account_sid or not api_key_sid or not api_key_secret:
            logger.error("Twilio credentials not configured in environment variables")
            raise ValueError(
                "Twilio credentials are not configured. Please set "
                "TWILIO_ACCOUNT_SID, TWILIO_API_KEY_SID, and TWILIO_API_KEY_SECRET."
            )
        
        # API Key authentication: pass api_key_sid as username, api_key_secret as password
        _twilio_client = Client(api_key_sid, api_key_secret, account_sid)
        logger.info("Twilio client initialized successfully with API Key authentication")
    
    return _twilio_client



def get_messaging_service_sid() -> str:
    """
    Get the Twilio Messaging Service SID from environment.
    
    Raises:
        ValueError: If messaging service SID is not configured.
    """
    sid = os.environ.get("TWILIO_MESSAGING_SERVICE_SID")
    if not sid:
        raise ValueError("TWILIO_MESSAGING_SERVICE_SID is not configured.")
    return sid


# --- Opt-out Storage (Firestore-backed) ---


class OptOutStoreUnavailable(Exception):
    """Raised when the opt-out store (Firestore) is unreachable.

    Callers should refuse to send rather than proceeding with an empty filter —
    silently dropping opt-outs is a TCPA exposure.
    """


async def add_opt_out(phone_stripped: str, reason: str = "inbound_stop") -> None:
    """Record a phone number as opted out in Firestore.

    Raises OptOutStoreUnavailable on any failure so the caller can decide
    whether to retry (webhook) or swallow (post-send permanent-failure hook).
    """
    from app.database import _get_db, firestore
    db = _get_db()
    if not db or not firestore:
        raise OptOutStoreUnavailable(
            f"Firestore unavailable — cannot save opt-out for {phone_stripped}"
        )

    try:
        await db.collection(_OPT_OUTS_COLLECTION).document(phone_stripped).set({
            "phone": f"+{phone_stripped}",
            "reason": reason,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        logger.info(f"Opt-out recorded: {phone_stripped} ({reason})")
    except Exception as e:
        logger.error(f"Failed to save opt-out for {phone_stripped}: {e}")
        raise OptOutStoreUnavailable(str(e)) from e


async def fetch_opt_outs() -> set:
    """Fetch all opted-out phone numbers from Firestore.

    Raises OptOutStoreUnavailable on failure — callers MUST refuse to send
    if this raises, to avoid TCPA violations from stale or missing opt-out data.
    """
    from app.database import _get_db
    db = _get_db()
    if not db:
        raise OptOutStoreUnavailable("Firestore client unavailable")

    try:
        docs = db.collection(_OPT_OUTS_COLLECTION).stream()
        numbers = set()
        async for doc in docs:
            numbers.add(doc.id)
        logger.info(f"Loaded {len(numbers)} opt-outs from Firestore")
        return numbers
    except Exception as e:
        logger.error(f"Failed to fetch opt-outs from Firestore: {e}")
        raise OptOutStoreUnavailable(str(e)) from e


def _scan_messages(messages) -> set:
    """Extract opt-outs and permanent failures from a list of Twilio messages.

    Used only by seed_opt_outs() for one-time migration.
    """
    stop = set()
    failed = set()
    for msg in messages:
        if msg.direction == "inbound" and msg.body and msg.body.strip().lower() in STOP_WORDS:
            stop.add(msg.from_.lstrip("+"))
        elif msg.direction == "outbound-api" and msg.status in ("failed", "undelivered"):
            code = str(msg.error_code) if msg.error_code else ""
            if code in PERMANENT_FAIL_CODES:
                failed.add(msg.to.lstrip("+"))
    return stop | failed


async def seed_opt_outs() -> int:
    """One-time migration: scan Twilio history and populate Firestore opt_outs.

    Scans the last BAD_NUMBER_FETCH_LIMIT messages for opt-outs and permanent
    failures, then writes them to Firestore. Safe to run multiple times
    (Firestore set() is idempotent).

    Returns the number of opt-outs seeded.
    """
    client = get_twilio_client()
    logger.info(f"Seeding opt-outs: scanning last {BAD_NUMBER_FETCH_LIMIT} Twilio messages...")
    # messages.list is a blocking HTTP paginator — run in a thread so the event loop stays free
    messages = await asyncio.to_thread(
        client.messages.list, limit=BAD_NUMBER_FETCH_LIMIT, page_size=1000
    )
    bad_numbers = _scan_messages(messages)

    for phone in bad_numbers:
        await add_opt_out(phone, reason="seeded")

    logger.info(f"Seeded {len(bad_numbers)} opt-outs from Twilio history")
    return len(bad_numbers)


# --- Phone Number Cleaning ---

def clean_phone_number(phone: str) -> str:
    """
    Clean and normalize a phone number to E.164 format.
    
    Args:
        phone: Raw phone number string (e.g., "(555) 123-4567", "555.123.4567")
    
    Returns:
        Cleaned phone number in E.164 format (e.g., "+15551234567")
    
    Raises:
        ValueError: If the phone number is invalid after cleaning.
    """
    if not phone:
        raise ValueError("Phone number cannot be empty")

    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())

    # + is only valid as a single leading character
    if cleaned.count('+') > 1 or ('+' in cleaned and not cleaned.startswith('+')):
        raise ValueError(f"Invalid phone number format: {phone}")

    # If it starts with +, keep it; otherwise process as US number
    if cleaned.startswith('+'):
        digits_only = cleaned[1:]
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError(f"Invalid phone number length: {phone}")
        return cleaned
    
    # Remove leading 1 if present (US country code without +)
    if cleaned.startswith('1') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    
    # Validate US phone number (10 digits)
    if len(cleaned) != 10:
        raise ValueError(f"Invalid phone number format: {phone}. Expected 10 digits for US numbers.")
    
    # Format as E.164 for US
    return f"+1{cleaned}"


# --- SMS Sending Functions ---

def personalize_message(template: str, name: str) -> str:
    """
    Replace [name] placeholder in message template with actual name.
    
    Args:
        template: Message template containing [name] placeholders.
        name: Customer name to insert.
    
    Returns:
        Personalized message string.
    """
    return template.replace("[name]", name)


async def send_sms(to: str, body: str, recipient_name: Optional[str] = None) -> str:
    """
    Send a single SMS message via Twilio.
    
    Args:
        to: Recipient phone number (will be cleaned/normalized).
        body: Message content (may contain [name] placeholder).
        recipient_name: Optional name for personalization.
    
    Returns:
        Twilio message SID on success.
    
    Raises:
        ValueError: If phone number is invalid or credentials missing.
        TwilioRestException: If Twilio API call fails.
    """
    client = get_twilio_client()
    messaging_service_sid = get_messaging_service_sid()
    
    # Clean the phone number
    cleaned_phone = clean_phone_number(to)
    
    # Personalize message if name provided
    final_message = body
    if recipient_name:
        final_message = personalize_message(body, recipient_name)
    
    try:
        message = await asyncio.to_thread(
            client.messages.create,
            messaging_service_sid=messaging_service_sid,
            to=cleaned_phone,
            body=final_message,
        )
        logger.info(f"SMS sent to {cleaned_phone}. SID: {message.sid}")
        return message.sid
    
    except TwilioRestException as e:
        # Record permanent failures as opt-outs in Firestore — best-effort so we
        # don't mask the Twilio error if the opt-out write itself fails.
        if str(e.code) in PERMANENT_FAIL_CODES:
            phone_stripped = cleaned_phone.lstrip("+")
            try:
                await add_opt_out(phone_stripped, reason=f"error_{e.code}")
            except OptOutStoreUnavailable as opt_err:
                logger.error(
                    f"Could not persist permanent-failure opt-out for {phone_stripped}: {opt_err}"
                )

        # Map Twilio errors to user-friendly messages
        if e.code == 20003:
            raise ValueError("SMS service authentication failed. Please check your Twilio credentials.")
        elif e.code == 21211:
            raise ValueError(f"Invalid phone number: {to}")
        elif e.code == 21608:
            raise ValueError("Unable to send SMS. Please verify your Twilio phone number is configured correctly.")
        elif e.code == 21610:
            raise ValueError(f"Cannot send SMS to {to}. This number has been unsubscribed.")
        elif "balance" in str(e).lower() or e.code == 21606:
            raise ValueError("Unable to send SMS. Please check your Twilio account balance.")
        else:
            logger.exception(f"Twilio error sending to {to}: {e}")
            raise


async def send_batch_sms(
    recipients: list[dict],
    message_template: str
) -> list[dict]:
    """
    Send SMS messages to multiple recipients with parallel sending.

    Phase 1 (sequential): Filters out duplicates, opt-outs, recent sends.
    Phase 2 (parallel): Sends up to _SEND_CONCURRENCY SMS at a time.

    Args:
        recipients: List of dicts with 'name' and 'phone' keys.
        message_template: Message template (may contain [name] placeholder).

    Returns:
        List of result dicts with 'name', 'phone', 'status', 'sid'/'error' keys.
    """
    # Fetch opt-outs from Firestore — if this fails, refuse to send.
    # Sending without the opt-out list is a TCPA violation risk.
    bad_numbers = await fetch_opt_outs()

    results: list[dict] = []
    sendable: list[int] = []  # indices into results for items to send
    seen_phones = set()

    # Phase 1: Filter
    for recipient in recipients:
        name = recipient.get("name", "")
        phone = recipient.get("phone", "")
        phone_stripped = phone.lstrip("+")
        result = {"name": name, "phone": phone, "status": "pending"}

        if phone_stripped in seen_phones:
            result["status"] = "failed"
            result["error"] = "Duplicate phone number (skipped)"
        elif phone_stripped in bad_numbers:
            result["status"] = "failed"
            result["error"] = "Opted out or previously failed (skipped)"
        elif await _is_recently_sent(phone_stripped):
            result["status"] = "failed"
            result["error"] = "Already sent to within last 30 minutes (skipped)"
        else:
            seen_phones.add(phone_stripped)
            sendable.append(len(results))

        results.append(result)

    # Phase 2: Send in parallel
    sem = asyncio.Semaphore(_SEND_CONCURRENCY)

    async def _send_one(idx: int):
        async with sem:
            r = results[idx]
            phone = r["phone"]
            name = r["name"]
            phone_stripped = phone.lstrip("+")
            try:
                sid = await send_sms(phone, message_template, name)
                await _mark_sent(phone_stripped)
                r["status"] = "sent"
                r["sid"] = sid
            except ValueError as e:
                r["status"] = "failed"
                r["error"] = str(e)
                logger.warning(f"Failed to send to {phone}: {e}")
            except TwilioRestException as e:
                r["status"] = "failed"
                r["error"] = f"Twilio error: {e.msg}"
                logger.error(f"Twilio error for {phone}: {e}")
            except Exception as e:
                r["status"] = "failed"
                r["error"] = "Unexpected error occurred"
                logger.exception(f"Unexpected error sending to {phone}: {e}")

    await asyncio.gather(*[_send_one(i) for i in sendable])

    return results
