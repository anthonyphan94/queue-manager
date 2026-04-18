"""
Authentication middleware for Marketing module.

PIN-based authentication with bcrypt hashing.
PIN is stored in Firestore settings collection.
"""

import asyncio
import hmac
import os
import bcrypt
from fastapi import HTTPException, Header

from app.settings_db import get_marketing_pin_hash, set_marketing_pin_hash

# Fallback PIN for development when Firestore is unavailable.
# No hardcoded default — must be explicitly set via env var.
DEFAULT_DEV_PIN = os.getenv("MARKETING_PIN")


async def verify_pin(x_marketing_pin: str = Header(None, alias="X-Marketing-Pin")):
    """
    Dependency that verifies the marketing PIN.

    Usage in router:
        @router.post("/send-single")
        async def send_single(request: Request, _: None = Depends(verify_pin)):
            ...
    """
    if not x_marketing_pin:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please provide PIN."
        )

    # Get stored hash from Firestore
    stored_hash = await get_marketing_pin_hash()

    if stored_hash:
        # bcrypt is CPU-bound (~200-300ms); run off the event loop
        is_match = await asyncio.to_thread(
            bcrypt.checkpw, x_marketing_pin.encode('utf-8'), stored_hash.encode('utf-8')
        )
        if is_match:
            return True
        raise HTTPException(status_code=403, detail="Invalid PIN.")
    else:
        # Fallback to env var for development/first-time setup
        if not DEFAULT_DEV_PIN:
            raise HTTPException(
                status_code=500,
                detail="PIN not configured. Set MARKETING_PIN env var or configure via Firestore.",
            )
        if hmac.compare_digest(x_marketing_pin, DEFAULT_DEV_PIN):
            return True
        raise HTTPException(status_code=403, detail="Invalid PIN.")


async def verify_pin_endpoint(pin: str) -> bool:
    """
    Verify PIN for the /verify-pin endpoint.
    Returns True if PIN matches, False otherwise.
    """
    # Get stored hash from Firestore
    stored_hash = await get_marketing_pin_hash()

    if stored_hash:
        return await asyncio.to_thread(
            bcrypt.checkpw, pin.encode('utf-8'), stored_hash.encode('utf-8')
        )
    else:
        # Fallback to env var for development/first-time setup
        if not DEFAULT_DEV_PIN:
            return False
        return hmac.compare_digest(pin, DEFAULT_DEV_PIN)


async def change_pin(current_pin: str, new_pin: str) -> tuple[bool, str]:
    """
    Change the marketing PIN.

    Args:
        current_pin: The current PIN for verification
        new_pin: The new PIN to set

    Returns:
        Tuple of (success, message)
    """
    # Validate new PIN
    if len(new_pin) < 4:
        return False, "New PIN must be at least 4 characters"

    if len(new_pin) > 20:
        return False, "New PIN must be at most 20 characters"

    # Verify current PIN
    is_valid = await verify_pin_endpoint(current_pin)
    if not is_valid:
        return False, "Current PIN is incorrect"

    # Hash and store new PIN (bcrypt is CPU-bound)
    new_hash_bytes = await asyncio.to_thread(
        bcrypt.hashpw, new_pin.encode('utf-8'), bcrypt.gensalt()
    )
    new_hash = new_hash_bytes.decode('utf-8')
    success = await set_marketing_pin_hash(new_hash)

    if success:
        return True, "PIN changed successfully"
    else:
        return False, "Failed to save new PIN. Database may be unavailable."
