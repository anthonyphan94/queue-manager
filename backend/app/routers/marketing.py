"""
Marketing Router Module

Handles CSV upload/preview, single SMS, and batch SMS endpoints
for the Marketing SMS Module.

AUTHENTICATION:
- /verify-pin: Public endpoint to verify PIN
- /preview-csv: Public (just parsing, no cost)
- /send-single: Protected (requires PIN header)
- /send-batch: Protected (requires PIN header)
"""

import asyncio
import io
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

import os

import pandas as pd
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from twilio.request_validator import RequestValidator

from app.services.twilio_service import (
    clean_phone_number,
    send_sms,
    send_batch_sms,
    fetch_opt_outs,
    add_opt_out,
    seed_opt_outs,
    _is_recently_sent,
    _mark_sent,
    STOP_WORDS,
    OptOutStoreUnavailable,
    register_batch,
    is_batch_cancelled,
    mark_batch_cancelled,
    clear_batch,
)
from app.services.sheets_service import fetch_phone_numbers
from app.auth import verify_pin, verify_pin_endpoint, change_pin

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/marketing", tags=["marketing"])


# --- Pydantic Models ---

class VerifyPinRequest(BaseModel):
    """Request body for PIN verification."""
    pin: str = Field(..., min_length=1, description="PIN code")


class VerifyPinResponse(BaseModel):
    """Response from PIN verification."""
    valid: bool
    message: str


class ChangePinRequest(BaseModel):
    """Request body for changing PIN."""
    current_pin: str = Field(..., min_length=1, description="Current PIN")
    new_pin: str = Field(..., min_length=4, max_length=20, description="New PIN (4-20 characters)")


class ChangePinResponse(BaseModel):
    """Response from PIN change."""
    success: bool
    message: str


class Contact(BaseModel):
    """A single contact from CSV or manual entry."""
    name: str = Field(..., min_length=1, max_length=100, description="Customer name")
    phone: str = Field(..., min_length=10, description="Phone number")
    row_index: Optional[int] = Field(
        default=None,
        description="1-based row number in the source (Google Sheet or CSV) for UI jump-to-row.",
    )


class SingleSmsRequest(BaseModel):
    """Request body for sending a single SMS."""
    name: str = Field(..., min_length=1, max_length=100, description="Customer name")
    phone: str = Field(..., min_length=10, description="Phone number")
    message: str = Field(..., min_length=1, max_length=1600, description="Message content")


class BatchSmsRequest(BaseModel):
    """Request body for sending batch SMS."""
    recipients: list[Contact] = Field(..., min_items=1, description="List of recipients")
    message: str = Field(..., min_length=1, max_length=1600, description="Message template")


class SmsResult(BaseModel):
    """Result of an SMS send operation."""
    name: str
    phone: str
    status: str  # "sent" | "failed"
    sid: Optional[str] = None
    error: Optional[str] = None


class PreviewResponse(BaseModel):
    """Response from CSV preview endpoint."""
    contacts: list[Contact]
    total_count: int
    valid_count: int
    invalid_count: int
    errors: list[str] = []


class SingleSmsResponse(BaseModel):
    """Response from single SMS send."""
    success: bool
    sid: Optional[str] = None
    error: Optional[str] = None


class BatchSmsResponse(BaseModel):
    """Response from batch SMS send."""
    total: int
    sent: int
    failed: int
    results: list[SmsResult]


# --- CSV Parsing Helper ---

def parse_csv_file(file_content: bytes) -> PreviewResponse:
    """
    Parse CSV file content and extract contacts.
    
    Handles both headerless files (columns by index) and files with headers.
    Column A (index 0) = Name, Column B (index 1) = Phone.
    """
    contacts = []
    errors = []
    
    try:
        # Try reading with UTF-8-sig to handle BOM
        content_str = file_content.decode('utf-8-sig')
    except UnicodeDecodeError:
        content_str = file_content.decode('latin-1')
    
    # Read CSV with pandas
    try:
        df = pd.read_csv(io.StringIO(content_str), header=None, dtype=str)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {str(e)}")
    
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    if len(df.columns) < 2:
        raise HTTPException(status_code=400, detail="CSV must have at least 2 columns (Name, Phone)")
    
    # Check if first row looks like headers — require EXACT match against a whitelist,
    # not substring (otherwise a real contact named "Dan Nameless" gets dropped).
    HEADER_LABELS = {
        "name", "full name", "first name", "last name", "customer", "customer name",
        "phone", "phone number", "number", "mobile", "cell", "cell phone", "contact",
    }
    first_row = df.iloc[0]
    first_vals = [str(v).lower().strip() for v in first_row.values[:2]]
    has_headers = any(val in HEADER_LABELS for val in first_vals)
    if has_headers:
        df = df.iloc[1:].reset_index(drop=True)

    # Process each row
    for idx, row in df.iterrows():
        # User-facing 1-based line number in the original CSV.
        # idx is now 0-based (after reset_index when headers were stripped).
        row_num = idx + (2 if has_headers else 1)
        
        name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        phone_raw = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        
        # Skip rows where both name and phone are empty
        if not name and not phone_raw:
            continue
        
        # Use "Customer" as default if no name provided
        if not name:
            name = "Customer"
        
        if not phone_raw:
            errors.append(f"Row {row_num}: Missing phone number for '{name}'")
            continue
        
        # Clean phone number
        try:
            cleaned_phone = clean_phone_number(phone_raw)
            contacts.append(Contact(name=name, phone=cleaned_phone, row_index=row_num))
        except ValueError as e:
            errors.append(f"Row {row_num}: {str(e)} (name: {name})")
    
    return PreviewResponse(
        contacts=contacts,
        total_count=len(df),
        valid_count=len(contacts),
        invalid_count=len(errors),
        errors=errors[:20]  # Limit error messages
    )


# --- Endpoints ---

@router.post("/verify-pin", response_model=VerifyPinResponse)
@limiter.limit("5/minute")
async def verify_pin_route(request: Request, body: VerifyPinRequest):
    """
    Verify the marketing PIN.

    Rate limited to 5 attempts per minute per IP.
    """
    is_valid = await verify_pin_endpoint(body.pin)

    if is_valid:
        logger.info("Marketing PIN verified successfully")
        return VerifyPinResponse(valid=True, message="PIN verified successfully")
    else:
        logger.warning(f"Invalid marketing PIN attempt from {request.client.host}")
        return VerifyPinResponse(valid=False, message="Invalid PIN")


@router.post("/change-pin", response_model=ChangePinResponse)
@limiter.limit("3/minute")
async def change_pin_route(request: Request, body: ChangePinRequest):
    """
    Change the marketing PIN.

    Requires current PIN for verification.
    Rate limited to 3 attempts per minute per IP.
    """
    success, message = await change_pin(body.current_pin, body.new_pin)

    if success:
        logger.info("Marketing PIN changed successfully")
    else:
        logger.warning(f"Failed to change marketing PIN from {request.client.host}")

    return ChangePinResponse(success=success, message=message)


@router.post("/preview-csv", response_model=PreviewResponse)
async def preview_csv(file: UploadFile = File(...), _: bool = Depends(verify_pin)):
    """
    Upload and parse a CSV file, returning a preview of contacts.
    
    Expects:
    - Column A (index 0): Customer Name
    - Column B (index 1): Phone Number
    
    Returns parsed contacts with validation results.
    
    NOTE: This endpoint is public (no PIN required) since it just
    parses data and doesn't send any SMS.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a .csv file")
    
    # Read file content
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    if len(content) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit")
    
    return parse_csv_file(content)


@router.post("/prepare", response_model=PreviewResponse)
async def prepare_recipients(_: bool = Depends(verify_pin)):
    """
    Fetch phone numbers from Google Sheets and clean against Twilio history.

    Pulls all contacts from the configured Google Sheet, then filters out:
    - Invalid phone numbers
    - Opt-outs (recipients who replied STOP/UNSUBSCRIBE/etc.)
    - Permanent failures (error codes 21610, 30005, 21211)
    - Duplicates

    PROTECTED: Requires X-Marketing-Pin header.
    """
    try:
        # Step 1: Fetch from Google Sheets
        logger.info("[prepare] Step 1: Fetching contacts from Google Sheets...")
        raw_contacts = fetch_phone_numbers()
        logger.info(f"[prepare] Step 1 done: {len(raw_contacts)} raw contacts fetched")
    except Exception as e:
        logger.error(f"[prepare] Step 1 FAILED: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch from Google Sheets. Please try again.")

    # Step 2: Fetch opt-outs from Firestore. Fail LOUD — if we can't verify
    # the opt-out list, we refuse to prepare a send list. TCPA risk otherwise.
    try:
        logger.info("[prepare] Step 2: Fetching opt-outs from Firestore...")
        bad_numbers = await fetch_opt_outs()
        logger.info(f"[prepare] Step 2 done: {len(bad_numbers)} opt-outs found")
    except OptOutStoreUnavailable as e:
        logger.error(f"[prepare] Step 2 FAILED: {e}")
        raise HTTPException(
            status_code=503,
            detail="Opt-out list is temporarily unavailable. Please try again shortly.",
        )

    # Step 3: Clean and filter
    logger.info("[prepare] Step 3: Cleaning and filtering contacts...")
    contacts = []
    errors = []
    seen_phones = set()
    dup_count = 0
    bad_count = 0
    invalid_count = 0

    for i, contact in enumerate(raw_contacts):
        name = contact["name"]
        phone_raw = contact["phone"]
        # gspread.get_all_records() treats row 1 as headers, so the first data
        # row (i=0) is sheet row 2. This matches what the operator sees in Sheets.
        row_num = i + 2

        # Validate phone format
        try:
            cleaned_phone = clean_phone_number(phone_raw)
        except ValueError as e:
            errors.append(f"Row {row_num}: {str(e)} (name: {name})")
            invalid_count += 1
            continue

        phone_stripped = cleaned_phone.lstrip("+")

        # Skip duplicates
        if phone_stripped in seen_phones:
            errors.append(f"Row {row_num}: Duplicate phone number (name: {name})")
            dup_count += 1
            continue
        seen_phones.add(phone_stripped)

        # Skip opt-outs and permanent failures
        if phone_stripped in bad_numbers:
            errors.append(f"Row {row_num}: Opted out or previously failed (name: {name})")
            bad_count += 1
            continue

        contacts.append(Contact(name=name, phone=cleaned_phone, row_index=row_num))

    logger.info(f"[prepare] Step 3 done: {len(contacts)} valid, {invalid_count} invalid, {dup_count} duplicates, {bad_count} opt-outs/failures")

    return PreviewResponse(
        contacts=contacts,
        total_count=len(raw_contacts),
        valid_count=len(contacts),
        invalid_count=len(errors),
        errors=errors[:20],
    )


@router.post("/send-single", response_model=SingleSmsResponse)
async def send_single_sms(request: SingleSmsRequest, _: bool = Depends(verify_pin)):
    """
    Send a single SMS message to one recipient.
    
    Supports [name] placeholder in message for personalization.
    
    PROTECTED: Requires X-Marketing-Pin header.

    """
    try:
        sid = await send_sms(
            to=request.phone,
            body=request.message,
            recipient_name=request.name
        )
        
        # TODO: Save to Firestore sms_history
        logger.info(f"Single SMS sent to {request.phone}, SID: {sid}")
        
        return SingleSmsResponse(success=True, sid=sid)
    
    except ValueError as e:
        return SingleSmsResponse(success=False, error=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error sending single SMS: {e}")
        return SingleSmsResponse(success=False, error="An unexpected error occurred. Please try again.")


@router.post("/send-batch", response_model=BatchSmsResponse)
async def send_batch(request: BatchSmsRequest, _: bool = Depends(verify_pin)):
    """
    Send SMS messages to multiple recipients.
    
    Supports [name] placeholder in message for personalization.
    Each recipient's name will replace [name] in their message.
    
    PROTECTED: Requires X-Marketing-Pin header.
    """

    recipients = [{"name": c.name, "phone": c.phone} for c in request.recipients]

    try:
        results = await send_batch_sms(recipients, request.message)

        sent_count = sum(1 for r in results if r["status"] == "sent")
        failed_count = sum(1 for r in results if r["status"] == "failed")

        logger.info(f"Batch SMS: {sent_count} sent, {failed_count} failed out of {len(results)}")

        return BatchSmsResponse(
            total=len(results),
            sent=sent_count,
            failed=failed_count,
            results=[SmsResult(**r) for r in results]
        )

    except OptOutStoreUnavailable as e:
        logger.error(f"Batch SMS refused: opt-out store unavailable: {e}")
        raise HTTPException(
            status_code=503,
            detail="Opt-out list is temporarily unavailable. Please try again shortly.",
        )
    except Exception as e:
        logger.exception(f"Batch SMS error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch SMS request")


# --- Streaming Batch Send with Progress ---

# Local asyncio.Event for same-instance fast-path cancel. The authoritative
# cross-instance cancel flag lives in Firestore (batches/{batch_id}.cancelled).
_active_batches: dict[str, asyncio.Event] = {}

# How often to consult the Firestore cancel flag during a send
_CANCEL_POLL_INTERVAL_SEC = 2.0


@router.post("/send-batch-stream")
async def send_batch_stream(request: Request, body: BatchSmsRequest, _: bool = Depends(verify_pin)):
    """
    Send SMS messages with real-time progress via Server-Sent Events.

    Returns an SSE stream with events:
    - {type: "start", batch_id, total}
    - {type: "progress", current, total, sent, failed, last_phone, last_status}
    - {type: "complete", sent, failed, total, results}
    - {type: "cancelled", sent, failed, remaining}

    PROTECTED: Requires X-Marketing-Pin header.
    """
    recipients = [{"name": c.name, "phone": c.phone} for c in body.recipients]
    message_template = body.message
    batch_id = str(uuid.uuid4())

    cancel_event = asyncio.Event()
    _active_batches[batch_id] = cancel_event
    await register_batch(batch_id)

    async def _poll_cross_instance_cancel():
        """Bridge Firestore → local event so a cancel on another instance stops us."""
        while not cancel_event.is_set():
            try:
                if await is_batch_cancelled(batch_id):
                    cancel_event.set()
                    return
            except Exception:
                pass
            await asyncio.sleep(_CANCEL_POLL_INTERVAL_SEC)

    poll_task = asyncio.create_task(_poll_cross_instance_cancel())

    # Fetch opt-outs once before streaming. Fail LOUD (no silent empty filter).
    try:
        bad_numbers = await fetch_opt_outs()
    except OptOutStoreUnavailable as e:
        logger.error(f"[send-batch-stream] Opt-out fetch failed: {e}")
        poll_task.cancel()
        _active_batches.pop(batch_id, None)
        await clear_batch(batch_id)
        raise HTTPException(
            status_code=503,
            detail="Opt-out list is temporarily unavailable. Please try again shortly.",
        )

    async def event_generator():
        total = len(recipients)
        sent = 0
        failed = 0
        results = []
        seen_phones = set()
        processed = 0

        try:
            yield f"data: {json.dumps({'type': 'start', 'batch_id': batch_id, 'total': total})}\n\n"

            # Phase 1: Filter (sequential, fast)
            to_send = []
            for recipient in recipients:
                if cancel_event.is_set():
                    yield f"data: {json.dumps({'type': 'cancelled', 'sent': sent, 'failed': failed, 'remaining': total - processed})}\n\n"
                    return

                name = recipient.get("name", "")
                phone = recipient.get("phone", "")
                phone_stripped = phone.lstrip("+")
                result = {"name": name, "phone": phone, "status": "pending"}

                skip_reason = None
                if phone_stripped in seen_phones:
                    skip_reason = "Duplicate phone number (skipped)"
                elif phone_stripped in bad_numbers:
                    skip_reason = "Opted out or previously failed (skipped)"
                elif await _is_recently_sent(phone_stripped):
                    skip_reason = "Already sent to within last 30 minutes (skipped)"

                if skip_reason:
                    result["status"] = "failed"
                    result["error"] = skip_reason
                    failed += 1
                    processed += 1
                    results.append(result)
                    yield f"data: {json.dumps({'type': 'progress', 'current': processed, 'total': total, 'sent': sent, 'failed': failed, 'last_phone': phone[-4:], 'last_status': 'skipped'})}\n\n"
                else:
                    seen_phones.add(phone_stripped)
                    to_send.append(result)

            # Phase 2: Send in parallel with progress via queue
            if to_send and not cancel_event.is_set():
                from app.services.twilio_service import _SEND_CONCURRENCY
                sem = asyncio.Semaphore(_SEND_CONCURRENCY)
                progress_queue = asyncio.Queue()

                async def _send_one(result_dict):
                    async with sem:
                        if cancel_event.is_set():
                            result_dict["status"] = "failed"
                            result_dict["error"] = "Cancelled"
                            await progress_queue.put(result_dict)
                            return
                        phone = result_dict["phone"]
                        name = result_dict["name"]
                        phone_stripped = phone.lstrip("+")
                        try:
                            sid = await send_sms(phone, message_template, name)
                            await _mark_sent(phone_stripped)
                            result_dict["status"] = "sent"
                            result_dict["sid"] = sid
                        except Exception as e:
                            result_dict["status"] = "failed"
                            result_dict["error"] = str(e)
                        await progress_queue.put(result_dict)

                tasks = [asyncio.create_task(_send_one(r)) for r in to_send]

                for _ in range(len(to_send)):
                    result = await progress_queue.get()
                    results.append(result)
                    if result["status"] == "sent":
                        sent += 1
                    else:
                        failed += 1
                    processed += 1
                    phone = result["phone"]
                    yield f"data: {json.dumps({'type': 'progress', 'current': processed, 'total': total, 'sent': sent, 'failed': failed, 'last_phone': phone[-4:], 'last_status': result['status']})}\n\n"

                    if cancel_event.is_set():
                        remaining = total - processed
                        yield f"data: {json.dumps({'type': 'cancelled', 'sent': sent, 'failed': failed, 'remaining': remaining})}\n\n"
                        for t in tasks:
                            t.cancel()
                        return

                await asyncio.gather(*tasks)

            yield f"data: {json.dumps({'type': 'complete', 'sent': sent, 'failed': failed, 'total': total, 'results': results})}\n\n"
            logger.info(f"Batch {batch_id}: sent={sent}, failed={failed}, total={total}")
        finally:
            poll_task.cancel()
            _active_batches.pop(batch_id, None)
            await clear_batch(batch_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/cancel-batch/{batch_id}")
async def cancel_batch(batch_id: str, _: bool = Depends(verify_pin)):
    """Cancel a running batch send.

    Writes to Firestore so the cancel is visible to any Cloud Run instance
    that is currently streaming this batch. Also flips the local asyncio.Event
    as a fast-path when we happen to be on the same instance as the sender.
    """
    local_event = _active_batches.get(batch_id)
    if local_event:
        local_event.set()

    wrote = await mark_batch_cancelled(batch_id)

    if not local_event and not wrote:
        # We have no record of this batch locally and couldn't persist the flag.
        raise HTTPException(status_code=404, detail="Batch not found or already completed")

    return {"cancelled": True}


# --- Twilio Webhook ---


def _verify_twilio_signature(request: Request, form: dict[str, str]) -> bool:
    """Verify Twilio signed this webhook request.

    Returns True on match, False on missing/invalid signature.
    Respects TWILIO_WEBHOOK_SKIP_AUTH=1 as a local-dev escape hatch (never set in prod).
    """
    if os.environ.get("TWILIO_WEBHOOK_SKIP_AUTH") == "1":
        logger.warning("Twilio webhook signature check bypassed (TWILIO_WEBHOOK_SKIP_AUTH=1)")
        return True

    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not auth_token:
        logger.error("TWILIO_AUTH_TOKEN not configured — cannot verify webhook signature")
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    # Twilio signs the full URL as the client sees it. Behind a proxy (Cloud Run),
    # honor X-Forwarded-Proto so the scheme matches what Twilio posted to.
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    url = str(request.url)
    if forwarded_proto and url.startswith("http://"):
        url = forwarded_proto + url[len("http"):]

    validator = RequestValidator(auth_token)
    return validator.validate(url, form, signature)


@router.post("/twilio-webhook")
async def twilio_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(default=""),
):
    """
    Twilio incoming message webhook.

    Called by Twilio when an inbound SMS is received.
    Records opt-outs (STOP, UNSUBSCRIBE, etc.) to Firestore instantly.

    PUBLIC (no PIN) but authenticated by X-Twilio-Signature. An unsigned or
    mismatched request is rejected with 403 — without this, anyone who finds
    the URL could mass-opt-out arbitrary numbers.

    Configure in Twilio console → Messaging Service → Integration →
    Incoming Messages → Send a webhook → https://your-domain/marketing/twilio-webhook
    """
    # Twilio signs the exact form-encoded body, so re-collect it as a flat dict.
    form = await request.form()
    form_dict = {k: str(v) for k, v in form.items()}
    if not _verify_twilio_signature(request, form_dict):
        logger.warning(f"Rejected unsigned Twilio webhook from {request.client.host if request.client else 'unknown'}")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    body_lower = Body.strip().lower()
    phone_stripped = From.lstrip("+")

    if body_lower in STOP_WORDS:
        try:
            await add_opt_out(phone_stripped, reason="inbound_stop")
            logger.info(f"Opt-out via webhook: {phone_stripped} sent '{Body.strip()}'")
        except OptOutStoreUnavailable as e:
            # Return 5xx so Twilio retries — silently 200'ing here means the opt-out
            # is permanently lost and the customer gets the next blast.
            logger.error(f"Webhook opt-out write failed for {phone_stripped}: {e}")
            raise HTTPException(status_code=503, detail="Opt-out store unavailable")

    # Return empty TwiML — Twilio expects XML response
    return Response(content="<Response/>", media_type="text/xml")


@router.post("/seed-opt-outs")
async def seed_opt_outs_endpoint(_: bool = Depends(verify_pin)):
    """
    One-time migration: scan Twilio history and populate Firestore opt_outs.

    Scans the last 10,000 messages for opt-outs and permanent failures,
    then writes them to Firestore. Safe to run multiple times.

    PROTECTED: Requires X-Marketing-Pin header.
    """
    count = await seed_opt_outs()
    return {"seeded": count, "message": f"Seeded {count} opt-outs from Twilio history"}
