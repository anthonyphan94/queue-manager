"""
Turn Rules Service - Core business logic for salon turn management.

This module contains all business logic for managing technician turns.
It is fully STATELESS - all operations read/write directly to Firestore.
"""

from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


class TurnRulesError(Exception):
    """Base exception for turn rules errors."""
    pass


class TechnicianNotFoundError(TurnRulesError):
    """Raised when a technician is not found."""
    def __init__(self, tech_id: int):
        self.tech_id = tech_id
        super().__init__(f"Technician with ID {tech_id} not found.")


class TechnicianNotAvailableError(TurnRulesError):
    """Raised when a technician is not available for assignment."""
    def __init__(self, tech_id: int, current_status: str):
        self.tech_id = tech_id
        self.current_status = current_status
        super().__init__(f"Technician {tech_id} is not available. Current status: {current_status}")


class NoAvailableTechniciansError(TurnRulesError):
    """Raised when no technicians are available."""
    def __init__(self):
        super().__init__("No available technicians in the queue.")


@dataclass
class TechnicianEntity:
    """
    Internal representation of a Technician.
    Used for API responses and compatibility with existing code.
    """
    id: int
    name: str
    status: str = "AVAILABLE"  # "AVAILABLE", "BUSY", or "ON_BREAK"
    queue_position: int = 0
    is_active: bool = False  # False = Offline, True = Online (checked-in)
    status_start_time: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TechnicianEntity":
        """Create a TechnicianEntity from a dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            status=data.get("status", "AVAILABLE"),
            queue_position=data.get("queue_position", 0),
            is_active=data.get("is_active", False),
            status_start_time=data.get("status_start_time")
        )


class TurnRulesService:
    """
    Stateless service class for turn management.
    
    All methods query Firestore directly - no in-memory state.
    Each operation is self-contained: read -> process -> write.
    """

    def __init__(self):
        """Initialize the stateless service (no state to store)."""
        pass

    # --- Query Methods (Async - query Firestore directly) ---

    async def get_next_tech(self) -> Optional[TechnicianEntity]:
        """
        Get the next available technician based on queue position.
        
        Returns:
            The technician with the lowest queue_position who is AVAILABLE and active,
            or None if no technicians are available.
        """
        from app.database import get_next_available_technician
        
        tech_data = await get_next_available_technician()
        if not tech_data:
            return None
        return TechnicianEntity.from_dict(tech_data)

    async def get_tech_by_id(self, tech_id: int) -> Optional[TechnicianEntity]:
        """
        Find a technician by their ID.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The technician if found, None otherwise.
        """
        from app.database import get_technician
        
        tech_data = await get_technician(tech_id)
        if not tech_data:
            return None
        return TechnicianEntity.from_dict(tech_data)

    async def get_tech_by_id_or_raise(self, tech_id: int) -> TechnicianEntity:
        """
        Find a technician by ID or raise an error if not found.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The technician entity.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        tech = await self.get_tech_by_id(tech_id)
        if not tech:
            raise TechnicianNotFoundError(tech_id)
        return tech

    # --- State Mutation Methods (Async - read/write Firestore directly) ---

    async def add_technician(self, name: str) -> TechnicianEntity:
        """
        Add a new technician to the roster.
        
        Args:
            name: The technician's display name.
            
        Returns:
            The newly created technician entity.
        """
        from app.database import (
            get_next_technician_id,
            get_technician_count,
            save_technician
        )
        
        # Get next ID and position
        new_id = await get_next_technician_id()
        tech_count = await get_technician_count()
        new_position = tech_count + 1
        
        new_tech_data = {
            "id": new_id,
            "name": name,
            "status": "AVAILABLE",
            "queue_position": new_position,
            "is_active": False,
        }
        
        # Save to Firestore (with SERVER_TIMESTAMP for status_start_time)
        await save_technician(new_tech_data, update_status_time=True)
        
        return TechnicianEntity(
            id=new_id,
            name=name,
            status="AVAILABLE",
            queue_position=new_position,
            is_active=False,
            status_start_time=None
        )

    async def remove_technician(self, tech_id: int) -> None:
        """
        Remove a technician from the roster.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        from app.database import delete_technician, repack_queue_positions
        
        # Verify technician exists
        tech = await self.get_tech_by_id_or_raise(tech_id)
        
        # Delete from Firestore
        await delete_technician(tech_id)
        
        # Repack queue positions to fill the gap
        await repack_queue_positions()

    async def assign_tech(self, tech_id: int) -> TechnicianEntity:
        """
        Assign a specific technician to a client.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The assigned technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
            TechnicianNotAvailableError: If technician is not available.
        """
        from app.database import update_technician_fields
        
        tech = await self.get_tech_by_id_or_raise(tech_id)
        
        if tech.status != "AVAILABLE":
            raise TechnicianNotAvailableError(tech_id, tech.status)
        
        # Update status in Firestore
        await update_technician_fields(tech_id, update_status_time=True, status="BUSY")
        
        tech.status = "BUSY"
        return tech

    async def assign_next_available(self) -> TechnicianEntity:
        """
        Assign the next available technician in the queue.
        
        Returns:
            The assigned technician.
            
        Raises:
            NoAvailableTechniciansError: If no technicians are available.
        """
        from app.database import update_technician_fields
        
        tech = await self.get_next_tech()
        if not tech:
            raise NoAvailableTechniciansError()
        
        # Update status in Firestore
        await update_technician_fields(tech.id, update_status_time=True, status="BUSY")
        
        tech.status = "BUSY"
        return tech

    async def handle_tech_completion(self, tech_id: int, is_request: bool = False) -> TechnicianEntity:
        """
        Handle completion of a technician's turn.
        
        Business Rule: After completing a turn, the technician is moved to the
        bottom of the queue regardless of whether it was a request or walk-in.
        
        Args:
            tech_id: The technician's unique identifier.
            is_request: Whether this was a requested assignment (reserved for future rules).
            
        Returns:
            The updated technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        from app.database import (
            get_max_queue_position,
            update_technician_fields,
            repack_queue_positions
        )
        
        # Verify technician exists
        await self.get_tech_by_id_or_raise(tech_id)
        
        # Get new position (bottom of queue)
        max_pos = await get_max_queue_position()
        new_position = max_pos + 1
        
        # Update in Firestore
        await update_technician_fields(
            tech_id,
            update_status_time=True,
            status="AVAILABLE",
            queue_position=new_position
        )
        
        # Repack to maintain contiguous positions
        await repack_queue_positions()
        
        # Return updated tech
        tech = await self.get_tech_by_id_or_raise(tech_id)
        return tech

    async def toggle_active_status(self, tech_id: int) -> TechnicianEntity:
        """
        Toggle a technician's active (checked-in) status.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The updated technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        from app.database import update_technician_fields
        
        tech = await self.get_tech_by_id_or_raise(tech_id)
        new_active = not tech.is_active
        
        # Update in Firestore (update status time when checking in)
        await update_technician_fields(
            tech_id,
            update_status_time=new_active,
            is_active=new_active
        )
        
        tech.is_active = new_active
        return tech

    async def reorder_queue(self, tech_ids: List[int]) -> None:
        """
        Reorder the queue based on a new ordering of technician IDs.
        
        Args:
            tech_ids: List of technician IDs in the desired order.
        """
        from app.database import save_all_technicians, load_technicians
        
        # Load all technicians to get their full data
        all_techs = await load_technicians()
        tech_map = {t["id"]: t for t in all_techs}
        
        # Update queue positions based on new order
        for index, tech_id in enumerate(tech_ids):
            if tech_id in tech_map:
                tech_map[tech_id]["queue_position"] = index + 1
        
        # Save all back to Firestore
        await save_all_technicians(list(tech_map.values()))

    async def take_break(self, tech_id: int) -> TechnicianEntity:
        """
        Put a technician on break.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The updated technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        from app.database import update_technician_fields
        
        await self.get_tech_by_id_or_raise(tech_id)
        
        # Update status in Firestore
        await update_technician_fields(tech_id, update_status_time=True, status="ON_BREAK")
        
        tech = await self.get_tech_by_id_or_raise(tech_id)
        return tech

    async def return_from_break(self, tech_id: int) -> TechnicianEntity:
        """
        Return a technician from break to the bottom of the queue.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The updated technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        from app.database import (
            get_max_queue_position,
            update_technician_fields,
            repack_queue_positions
        )
        
        await self.get_tech_by_id_or_raise(tech_id)
        
        # Get new position (bottom of queue)
        max_pos = await get_max_queue_position()
        new_position = max_pos + 1
        
        # Update in Firestore
        await update_technician_fields(
            tech_id,
            update_status_time=True,
            status="AVAILABLE",
            queue_position=new_position
        )
        
        # Repack to maintain contiguous positions
        await repack_queue_positions()
        
        tech = await self.get_tech_by_id_or_raise(tech_id)
        return tech

    # --- Serialization Methods (Async - query Firestore directly) ---

    async def get_all_techs_sorted(self) -> List[dict]:
        """
        Get all technicians sorted by queue position.
        
        Returns:
            List of technician dictionaries ready for API response.
        """
        from app.database import load_technicians
        
        technicians = await load_technicians()
        
        # Sort by queue_position (already sorted from Firestore, but ensure)
        sorted_techs = sorted(technicians, key=lambda t: t["queue_position"])
        
        return [
            {
                "id": t["id"],
                "name": t["name"],
                "status": t["status"],
                "queue_position": t["queue_position"],
                "is_active": t["is_active"],
                "status_start_time": t.get("status_start_time")
            }
            for t in sorted_techs
        ]
