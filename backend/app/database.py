"""
Database Module - Firestore persistence for Salon Turn Manager.

Provides async Firestore database operations for storing technician data
persistently. Compatible with Google Cloud Run automatic authentication.
"""

from typing import List, Optional
from datetime import datetime
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
        from google.cloud.firestore_v1 import AsyncClient
        firestore = _firestore
        FIRESTORE_AVAILABLE = True
    except ImportError:
        pass

# Collection name for technicians
COLLECTION_NAME = "technicians"


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
    """Initialize the database connection.
    
    For Firestore, this simply verifies the connection works.
    Collections are created automatically when documents are added.
    """
    db = _get_db()
    if db:
        print(f"[Firestore] Initialized - using collection: {COLLECTION_NAME}")
    else:
        print("[Warning] Running without Firestore - data will not persist")


async def load_technicians() -> List[dict]:
    """Load all technicians from Firestore, ordered by queue_position."""
    db = _get_db()
    if not db:
        print("[load_technicians] No database connection available")
        return []
    
    try:
        collection = db.collection(COLLECTION_NAME)
        
        # Query all documents ordered by queue_position
        query = collection.order_by("queue_position")
        docs = query.stream()
        
        technicians = []
        async for doc in docs:
            data = doc.to_dict()
            
            # Handle status_start_time - convert Firestore timestamp to ISO string
            status_start_time = data.get("status_start_time")
            if status_start_time and hasattr(status_start_time, 'isoformat'):
                status_start_time = status_start_time.isoformat()
            elif status_start_time and hasattr(status_start_time, 'timestamp'):
                # Firestore Timestamp object
                status_start_time = status_start_time.timestamp()
            
            technicians.append({
                "id": int(doc.id),  # Document ID is the technician ID
                "name": data.get("name", ""),
                "status": data.get("status", "AVAILABLE"),
                "queue_position": data.get("queue_position", 0),
                "is_active": data.get("is_active", False),
                "status_start_time": status_start_time
            })

        print(f"[load_technicians] Successfully loaded {len(technicians)} technicians from Firestore")
        return technicians
    except Exception as e:
        print(f"[load_technicians] Error loading technicians: {e}")
        return []


async def save_technician(tech: dict, update_status_time: bool = False) -> int:
    """Save or update a technician in Firestore. Returns the technician ID.
    
    Args:
        tech: Technician data dictionary
        update_status_time: If True, set status_start_time to SERVER_TIMESTAMP
    """
    db = _get_db()
    if not db:
        return tech.get("id", 1)  # Return existing ID or 1 for new
    
    collection = db.collection(COLLECTION_NAME)
    
    tech_id = tech.get("id")
    
    # Prepare document data (exclude 'id' as it's the document ID)
    doc_data = {
        "name": tech["name"],
        "status": tech.get("status", "AVAILABLE"),
        "queue_position": tech.get("queue_position", 0),
        "is_active": tech.get("is_active", False),
    }
    
    # Use SERVER_TIMESTAMP if updating status time, otherwise preserve existing
    if update_status_time:
        doc_data["status_start_time"] = firestore.SERVER_TIMESTAMP
    elif "status_start_time" in tech:
        doc_data["status_start_time"] = tech["status_start_time"]
    
    if tech_id:
        # Update existing document
        doc_ref = collection.document(str(tech_id))
        await doc_ref.set(doc_data, merge=True)
        return tech_id
    else:
        # Generate new ID efficiently - query only the max ID document
        new_id = await get_next_technician_id()

        # New technicians always get SERVER_TIMESTAMP
        doc_data["status_start_time"] = firestore.SERVER_TIMESTAMP

        doc_ref = collection.document(str(new_id))
        await doc_ref.set(doc_data)
        return new_id


async def get_next_technician_id() -> int:
    """Get the next available technician ID efficiently.

    Uses a descending query with limit(1) to find max ID,
    avoiding loading all technicians into memory.
    """
    db = _get_db()
    if not db:
        return 1
    
    collection = db.collection(COLLECTION_NAME)

    # Query for the document with the highest ID (document IDs are strings of integers)
    # We need to get all docs and find max since Firestore doesn't support ordering by doc ID
    # Use a counter document for O(1) performance
    counter_ref = db.collection("_counters").document("technicians")
    counter_doc = await counter_ref.get()

    if counter_doc.exists:
        current_max = counter_doc.to_dict().get("next_id", 1)
        new_id = current_max
        # Increment the counter
        await counter_ref.set({"next_id": current_max + 1})
        return new_id
    else:
        # First time - scan existing docs to find max (one-time migration)
        query = collection.stream()
        max_id = 0
        async for doc in query:
            try:
                doc_id = int(doc.id)
                if doc_id > max_id:
                    max_id = doc_id
            except ValueError:
                continue

        new_id = max_id + 1
        # Initialize counter for future use
        await counter_ref.set({"next_id": new_id + 1})
        return new_id


async def delete_technician(tech_id: int):
    """Delete a technician from Firestore."""
    db = _get_db()
    if not db:
        return
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    await doc_ref.delete()


async def save_all_technicians(technicians: List[dict]):
    """Save all technicians to Firestore (batch update)."""
    db = _get_db()
    if not db:
        return
    
    batch = db.batch()
    collection = db.collection(COLLECTION_NAME)
    
    for tech in technicians:
        if tech.get("id"):
            doc_ref = collection.document(str(tech["id"]))
            doc_data = {
                "name": tech["name"],
                "status": tech.get("status", "AVAILABLE"),
                "queue_position": tech.get("queue_position", 0),
                "is_active": tech.get("is_active", False),
            }
            # Preserve existing status_start_time (don't overwrite with batch)
            if tech.get("status_start_time"):
                doc_data["status_start_time"] = tech["status_start_time"]
            batch.set(doc_ref, doc_data, merge=True)
    
    await batch.commit()


async def update_technician_status(tech_id: int, status: str) -> None:
    """Update a technician's status and set status_start_time to SERVER_TIMESTAMP.

    This should be called whenever a technician's status changes.
    """
    db = _get_db()
    if not db:
        return
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    await doc_ref.update({
        "status": status,
        "status_start_time": firestore.SERVER_TIMESTAMP
    })


# --- Settings Collection (Marketing PIN, etc.) ---

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
