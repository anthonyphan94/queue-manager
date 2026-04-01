"""
Database Module - Firestore client for settings storage (PIN).
"""

import os

# Skip Firestore entirely if SKIP_FIRESTORE env var is set
SKIP_FIRESTORE = os.environ.get("SKIP_FIRESTORE", "0") == "1"

# Try to import Firestore, but allow the app to run without it
FIRESTORE_AVAILABLE = False
_db = None
firestore = None

if not SKIP_FIRESTORE:
    try:
        from google.cloud import firestore as _firestore
        firestore = _firestore
        FIRESTORE_AVAILABLE = True
    except ImportError:
        pass


def _get_db():
    """Get or create the Firestore async client."""
    global _db, FIRESTORE_AVAILABLE

    if SKIP_FIRESTORE or not FIRESTORE_AVAILABLE:
        return None

    if _db is None:
        try:
            _db = firestore.AsyncClient()
        except Exception as e:
            print(f"[Warning] Firestore not available: {e}")
            FIRESTORE_AVAILABLE = False
            return None
    return _db


async def init_db():
    """Initialize the database connection."""
    db = _get_db()
    if db:
        print("[Firestore] Initialized for settings storage")
    else:
        print("[Warning] Running without Firestore")
