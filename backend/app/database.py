"""
Database Module - Firestore persistence for Salon Turn Manager.

Provides async Firestore database operations for storing technician data
persistently. Compatible with Google Cloud Run automatic authentication.
"""

from google.cloud import firestore
from google.cloud.firestore_v1 import AsyncClient
from typing import List, Optional
from datetime import datetime

# Firestore client (initialized lazily)
_db: Optional[AsyncClient] = None

# Collection name for technicians
COLLECTION_NAME = "technicians"


def _get_db() -> AsyncClient:
    """Get or create the Firestore async client."""
    global _db
    if _db is None:
        _db = firestore.AsyncClient()
    return _db


async def init_db():
    """Initialize the database connection.
    
    For Firestore, this simply verifies the connection works.
    Collections are created automatically when documents are added.
    """
    db = _get_db()
    print(f"🔥 Firestore initialized - using collection: {COLLECTION_NAME}")


async def load_technicians() -> List[dict]:
    """Load all technicians from Firestore, ordered by queue_position."""
    db = _get_db()
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
    
    return technicians


async def save_technician(tech: dict, update_status_time: bool = False) -> int:
    """Save or update a technician in Firestore. Returns the technician ID.
    
    Args:
        tech: Technician data dictionary
        update_status_time: If True, set status_start_time to SERVER_TIMESTAMP
    """
    db = _get_db()
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
        # Generate new ID - find max existing ID and increment
        existing = await load_technicians()
        new_id = max((t["id"] for t in existing), default=0) + 1
        
        # New technicians always get SERVER_TIMESTAMP
        doc_data["status_start_time"] = firestore.SERVER_TIMESTAMP
        
        doc_ref = collection.document(str(new_id))
        await doc_ref.set(doc_data)
        return new_id


async def delete_technician(tech_id: int):
    """Delete a technician from Firestore."""
    db = _get_db()
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    await doc_ref.delete()


async def save_all_technicians(technicians: List[dict]):
    """Save all technicians to Firestore (batch update)."""
    db = _get_db()
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
    doc_ref = db.collection(COLLECTION_NAME).document(str(tech_id))
    await doc_ref.update({
        "status": status,
        "status_start_time": firestore.SERVER_TIMESTAMP
    })
