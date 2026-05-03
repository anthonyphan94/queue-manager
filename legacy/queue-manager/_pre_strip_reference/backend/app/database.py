"""
Database Module - Firestore persistence for Salon Turn Manager.

Provides async Firestore database operations for storing technician data
persistently. Compatible with Google Cloud Run automatic authentication.
"""

from typing import List, Optional
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

# Collection names
COLLECTION_NAME = "technicians"
_COUNTERS_COLLECTION = "_counters"


def _convert_timestamp(ts):
    """Convert Firestore timestamp to ISO string or Unix timestamp.

    Handles both Python datetime objects and Firestore Timestamp objects.
    Returns None if input is None or not a recognized timestamp type.
    """
    if ts is None:
        return None
    if hasattr(ts, 'isoformat'):
        return ts.isoformat()
    if hasattr(ts, 'timestamp'):
        return ts.timestamp()
    return ts


def _doc_to_technician(doc, data: dict) -> dict:
    """Convert a Firestore document to a technician dict.

    Args:
        doc: Firestore document snapshot
        data: Document data from doc.to_dict()

    Returns:
        Technician dict with standardized fields
    """
    return {
        "id": int(doc.id),
        "name": data.get("name", ""),
        "status": data.get("status", "AVAILABLE"),
        "queue_position": data.get("queue_position", 0),
        "is_active": data.get("is_active", False),
        "status_start_time": _convert_timestamp(data.get("status_start_time"))
    }


def _technician_to_doc_data(tech: dict, include_status_time: bool = False) -> dict:
    """Convert a technician dict to Firestore document data.

    Args:
        tech: Technician dict
        include_status_time: If True, include status_start_time field

    Returns:
        Dict suitable for Firestore document
    """
    doc_data = {
        "name": tech["name"],
        "status": tech.get("status", "AVAILABLE"),
        "queue_position": tech.get("queue_position", 0),
        "is_active": tech.get("is_active", False),
    }
    if include_status_time and tech.get("status_start_time"):
        doc_data["status_start_time"] = tech["status_start_time"]
    return doc_data


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
            technicians.append(_doc_to_technician(doc, doc.to_dict()))

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

    doc_data = _technician_to_doc_data(tech)

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
    counter_ref = db.collection(_COUNTERS_COLLECTION).document("technicians")
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


async def get_technician(tech_id: int) -> Optional[dict]:
    """Get a single technician by ID from Firestore.
    
    Returns None if not found or Firestore unavailable.
    """
    db = _get_db()
    if not db:
        return None
    
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    doc = await doc_ref.get()
    
    if not doc.exists:
        return None

    return _doc_to_technician(doc, doc.to_dict())


async def get_next_available_technician() -> Optional[dict]:
    """Get the next available technician (AVAILABLE + is_active) with lowest queue_position.
    
    Returns None if no technicians are available.
    """
    db = _get_db()
    if not db:
        return None
    
    collection = db.collection(COLLECTION_NAME)
    
    # Query for AVAILABLE and active technicians, ordered by queue_position
    query = (collection
             .where("status", "==", "AVAILABLE")
             .where("is_active", "==", True)
             .order_by("queue_position")
             .limit(1))
    
    docs = query.stream()
    async for doc in docs:
        return _doc_to_technician(doc, doc.to_dict())

    return None


async def get_max_queue_position() -> int:
    """Get the maximum queue_position value across all technicians.
    
    Returns 0 if no technicians exist.
    """
    db = _get_db()
    if not db:
        return 0
    
    collection = db.collection(COLLECTION_NAME)
    query = collection.order_by("queue_position", direction=firestore.Query.DESCENDING).limit(1)
    
    docs = query.stream()
    async for doc in docs:
        data = doc.to_dict()
        return data.get("queue_position", 0)
    
    return 0


async def get_technician_count() -> int:
    """Get the count of all technicians.
    
    Returns 0 if no technicians exist or Firestore unavailable.
    """
    db = _get_db()
    if not db:
        return 0
    
    collection = db.collection(COLLECTION_NAME)
    docs = collection.stream()
    count = 0
    async for _ in docs:
        count += 1
    return count


async def update_technician_fields(tech_id: int, update_status_time: bool = False, **fields) -> bool:
    """Update specific fields on a technician document.
    
    Args:
        tech_id: The technician's ID
        update_status_time: If True, also set status_start_time to SERVER_TIMESTAMP
        **fields: Field names and values to update
        
    Returns:
        True if update succeeded, False if Firestore unavailable
    """
    db = _get_db()
    if not db:
        return False
    
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    
    update_data = dict(fields)
    if update_status_time:
        update_data["status_start_time"] = firestore.SERVER_TIMESTAMP
    
    await doc_ref.update(update_data)
    return True


async def repack_queue_positions() -> bool:
    """Re-pack all queue positions to contiguous 1..N values.
    
    Uses a transaction to ensure atomicity.
    
    Returns:
        True if successful, False if Firestore unavailable
    """
    db = _get_db()
    if not db:
        return False
    
    collection = db.collection(COLLECTION_NAME)
    
    # Get all technicians ordered by current queue_position
    query = collection.order_by("queue_position")
    docs = query.stream()
    
    # Collect all docs and their new positions
    updates = []
    position = 1
    async for doc in docs:
        updates.append((doc.reference, position))
        position += 1
    
    # Batch update all positions
    if updates:
        batch = db.batch()
        for doc_ref, new_pos in updates:
            batch.update(doc_ref, {"queue_position": new_pos})
        await batch.commit()
    
    return True


async def delete_all_technicians() -> int:
    """Delete ALL technicians from Firestore and reset the ID counter.
    
    Returns the number of deleted technicians.
    """
    db = _get_db()
    if not db:
        return 0
    
    collection = db.collection(COLLECTION_NAME)
    deleted_count = 0
    
    # Get all technician documents
    docs = collection.stream()
    async for doc in docs:
        await doc.reference.delete()
        deleted_count += 1
    
    # Reset the ID counter
    counter_ref = db.collection(_COUNTERS_COLLECTION).document("technicians")
    await counter_ref.set({"next_id": 1})
    
    print(f"[delete_all_technicians] Deleted {deleted_count} technicians, reset ID counter")
    return deleted_count


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
            doc_data = _technician_to_doc_data(tech, include_status_time=True)
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
