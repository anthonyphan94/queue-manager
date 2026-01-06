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

import io
import logging
from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.twilio_service import (
    clean_phone_number,
    send_sms,
    send_batch_sms
)
from app.auth import verify_pin, verify_pin_endpoint

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketing", tags=["marketing"])


# --- Pydantic Models ---

class VerifyPinRequest(BaseModel):
    """Request body for PIN verification."""
    pin: str = Field(..., min_length=1, description="PIN code")


class VerifyPinResponse(BaseModel):
    """Response from PIN verification."""
    valid: bool
    message: str


class Contact(BaseModel):
    """A single contact from CSV or manual entry."""
    name: str = Field(..., min_length=1, description="Customer name")
    phone: str = Field(..., min_length=10, description="Phone number")


class SingleSmsRequest(BaseModel):
    """Request body for sending a single SMS."""
    name: str = Field(..., min_length=1, description="Customer name")
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
    
    # Check if first row looks like headers
    first_row = df.iloc[0]
    has_headers = False
    
    # Detect headers by checking if first row contains common header names
    header_keywords = ['name', 'phone', 'number', 'customer', 'contact', 'mobile', 'cell']
    first_vals = [str(v).lower().strip() for v in first_row.values[:2]]
    if any(keyword in val for val in first_vals for keyword in header_keywords):
        has_headers = True
        df = df.iloc[1:]  # Skip header row
    
    # Process each row
    for idx, row in df.iterrows():
        row_num = idx + (2 if has_headers else 1)  # 1-indexed for user display
        
        name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        phone_raw = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        
        # Skip empty rows
        if not name and not phone_raw:
            continue
        
        if not name:
            errors.append(f"Row {row_num}: Missing name")
            continue
        
        if not phone_raw:
            errors.append(f"Row {row_num}: Missing phone number for '{name}'")
            continue
        
        # Clean phone number
        try:
            cleaned_phone = clean_phone_number(phone_raw)
            contacts.append(Contact(name=name, phone=cleaned_phone))
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
async def verify_pin_route(request: VerifyPinRequest):
    """
    Verify the marketing PIN.
    
    Returns whether the provided PIN is valid.
    This is a public endpoint - no authentication required.
    """
    is_valid = verify_pin_endpoint(request.pin)
    
    if is_valid:
        logger.info("Marketing PIN verified successfully")
        return VerifyPinResponse(valid=True, message="PIN verified successfully")
    else:
        logger.warning("Invalid marketing PIN attempt")
        return VerifyPinResponse(valid=False, message="Invalid PIN")


@router.post("/preview-csv", response_model=PreviewResponse)
async def preview_csv(file: UploadFile = File(...)):
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
        
        # Count results
        sent_count = sum(1 for r in results if r["status"] == "sent")
        failed_count = sum(1 for r in results if r["status"] == "failed")
        
        # TODO: Save all to Firestore sms_history
        logger.info(f"Batch SMS: {sent_count} sent, {failed_count} failed out of {len(results)}")
        
        return BatchSmsResponse(
            total=len(results),
            sent=sent_count,
            failed=failed_count,
            results=[SmsResult(**r) for r in results]
        )
    
    except Exception as e:
        logger.exception(f"Batch SMS error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process batch SMS request")
