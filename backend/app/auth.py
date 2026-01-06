"""
Authentication middleware for Marketing module.

Simple PIN-based authentication. The PIN is stored in the
MARKETING_PIN environment variable.
"""

import os
from fastapi import HTTPException, Header
from functools import wraps

# Get PIN from environment (default for dev only)
MARKETING_PIN = os.getenv("MARKETING_PIN", "0112")


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
    
    if x_marketing_pin != MARKETING_PIN:
        raise HTTPException(
            status_code=403,
            detail="Invalid PIN."
        )
    
    return True


def verify_pin_endpoint(pin: str) -> bool:
    """
    Simple function to verify PIN for the /verify-pin endpoint.
    Returns True if PIN matches, False otherwise.
    """
    return pin == MARKETING_PIN
