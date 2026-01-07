"""
Authentication middleware for Marketing module.

PIN-based authentication with bcrypt hashing.
PIN is stored in Firestore settings collection.
"""

import os
import bcrypt
from fastapi import HTTPException, Header

from app.database import get_marketing_pin_hash, set_marketing_pin_hash

# Fallback PIN for development when Firestore is unavailable
DEFAULT_DEV_PIN = os.getenv("MARKETING_PIN", "0112")


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
        # Verify against bcrypt hash
        if bcrypt.checkpw(x_marketing_pin.encode('utf-8'), stored_hash.encode('utf-8')):
            return True
        raise HTTPException(status_code=403, detail="Invalid PIN.")
    else:
        # Fallback to env var for development/first-time setup
        if x_marketing_pin == DEFAULT_DEV_PIN:
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
        # Verify against bcrypt hash
        return bcrypt.checkpw(pin.encode('utf-8'), stored_hash.encode('utf-8'))
    else:
        # Fallback to env var for development/first-time setup
        return pin == DEFAULT_DEV_PIN


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

    # Hash and store new PIN
    new_hash = bcrypt.hashpw(new_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    success = await set_marketing_pin_hash(new_hash)

    if success:
        return True, "PIN changed successfully"
    else:
        return False, "Failed to save new PIN. Database may be unavailable."
