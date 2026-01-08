"""
Settings Database Module - Firestore persistence for application settings.

Handles storage and retrieval of application settings like marketing PIN.
"""

from typing import Optional

# Import shared database utilities
from app.database import _get_db, firestore, FIRESTORE_AVAILABLE

# Collection name for settings
SETTINGS_COLLECTION = "settings"


async def get_marketing_pin_hash() -> Optional[str]:
    """Get the hashed marketing PIN from Firestore.

    Returns None if no PIN is set or Firestore is unavailable.
    """
    db = _get_db()
    if not db:
        return None

    doc_ref = db.collection(SETTINGS_COLLECTION).document("marketing")
    doc = await doc_ref.get()

    if doc.exists:
        return doc.to_dict().get("pin_hash")
    return None


async def set_marketing_pin_hash(pin_hash: str) -> bool:
    """Set the hashed marketing PIN in Firestore.

    Args:
        pin_hash: The bcrypt-hashed PIN to store

    Returns:
        True if successful, False if Firestore unavailable
    """
    db = _get_db()
    if not db:
        return False

    doc_ref = db.collection(SETTINGS_COLLECTION).document("marketing")
    await doc_ref.set({
        "pin_hash": pin_hash,
        "updated_at": firestore.SERVER_TIMESTAMP
    }, merge=True)
    return True


async def initialize_marketing_pin(default_pin: str) -> bool:
    """Initialize the marketing PIN if not already set.

    Args:
        default_pin: The plaintext default PIN to hash and store

    Returns:
        True if initialized (or already exists), False if Firestore unavailable
    """
    import bcrypt

    db = _get_db()
    if not db:
        return False

    # Check if PIN already exists
    existing = await get_marketing_pin_hash()
    if existing:
        return True  # Already initialized

    # Hash and store the default PIN
    pin_hash = bcrypt.hashpw(default_pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return await set_marketing_pin_hash(pin_hash)
