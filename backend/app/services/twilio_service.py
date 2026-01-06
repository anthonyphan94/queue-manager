"""
Twilio SMS Service Module

Encapsulates Twilio client initialization, phone number cleaning,
and SMS sending logic for the Marketing SMS Module.
"""

import os
import re
import logging
from typing import Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

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
    
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone.strip())
    
    # If it starts with +, keep it; otherwise process as US number
    if cleaned.startswith('+'):
        # Already has country code
        digits_only = re.sub(r'\D', '', cleaned)
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
        message = client.messages.create(
            messaging_service_sid=messaging_service_sid,
            to=cleaned_phone,
            body=final_message
        )
        logger.info(f"SMS sent to {cleaned_phone}. SID: {message.sid}")
        return message.sid
    
    except TwilioRestException as e:
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
    Send SMS messages to multiple recipients.
    
    Args:
        recipients: List of dicts with 'name' and 'phone' keys.
        message_template: Message template (may contain [name] placeholder).
    
    Returns:
        List of result dicts with 'name', 'phone', 'status', 'sid'/'error' keys.
    """
    results = []
    
    for recipient in recipients:
        name = recipient.get("name", "")
        phone = recipient.get("phone", "")
        
        result = {
            "name": name,
            "phone": phone,
            "status": "pending"
        }
        
        try:
            sid = await send_sms(phone, message_template, name)
            result["status"] = "sent"
            result["sid"] = sid
        except ValueError as e:
            result["status"] = "failed"
            result["error"] = str(e)
            logger.warning(f"Failed to send to {phone}: {e}")
        except TwilioRestException as e:
            result["status"] = "failed"
            result["error"] = f"Twilio error: {e.msg}"
            logger.error(f"Twilio error for {phone}: {e}")
        except Exception as e:
            result["status"] = "failed"
            result["error"] = "Unexpected error occurred"
            logger.exception(f"Unexpected error sending to {phone}: {e}")
        
        results.append(result)
    
    return results
