"""
Turn Rules Service - Core business logic for salon turn management.

This module contains all business logic for managing technician turns.
It does NOT depend on FastAPI, only on data models.
"""

from typing import List, Optional
from dataclasses import dataclass, field


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
    Used by the TurnRulesService for business logic operations.
    """
    id: int
    name: str
    status: str = "AVAILABLE"  # "AVAILABLE" or "BUSY"
    queue_position: int = 0
    is_active: bool = False  # False = Offline, True = Online (checked-in)


class TurnRulesService:
    """
    Service class containing all business logic for turn management.
    
    This class is framework-agnostic and does not depend on FastAPI.
    All methods operate on a list of TechnicianEntity objects.
    """

    def __init__(self, technicians: List[TechnicianEntity] = None):
        """Initialize the service with an optional list of technicians."""
        self.technicians = technicians if technicians is not None else []

    # --- Query Methods ---

    def get_next_tech(self) -> Optional[TechnicianEntity]:
        """
        Get the next available technician based on queue position.
        
        Returns:
            The technician with the lowest queue_position who is AVAILABLE and active,
            or None if no technicians are available.
        """
        available_techs = [
            t for t in self.technicians 
            if t.status == "AVAILABLE" and t.is_active
        ]
        if not available_techs:
            return None
        
        # Sort by queue_position ascending
        available_techs.sort(key=lambda t: t.queue_position)
        return available_techs[0]

    def get_tech_by_id(self, tech_id: int) -> Optional[TechnicianEntity]:
        """
        Find a technician by their ID.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The technician if found, None otherwise.
        """
        return next((t for t in self.technicians if t.id == tech_id), None)

    def get_tech_by_id_or_raise(self, tech_id: int) -> TechnicianEntity:
        """
        Find a technician by ID or raise an error if not found.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The technician entity.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        tech = self.get_tech_by_id(tech_id)
        if not tech:
            raise TechnicianNotFoundError(tech_id)
        return tech

    # --- Position Calculation Methods ---

    def calculate_new_queue_position(self) -> int:
        """
        Calculate the queue position for a new technician (bottom of queue).
        
        Returns:
            The next available queue position.
        """
        if not self.technicians:
            return 1
        return max(t.queue_position for t in self.technicians) + 1

    def calculate_bottom_position(self) -> int:
        """
        Calculate the position at the bottom of the queue.
        
        Returns:
            The position value for the bottom of the queue.
        """
        if not self.technicians:
            return 1
        return max(t.queue_position for t in self.technicians) + 1

    # --- State Mutation Methods ---

    def add_technician(self, name: str) -> TechnicianEntity:
        """
        Add a new technician to the roster.
        
        Args:
            name: The technician's display name.
            
        Returns:
            The newly created technician entity.
        """
        new_id = max((t.id for t in self.technicians), default=0) + 1
        new_position = self.calculate_new_queue_position()
        
        new_tech = TechnicianEntity(
            id=new_id,
            name=name,
            status="AVAILABLE",
            queue_position=new_position,
            is_active=False
        )
        self.technicians.append(new_tech)
        return new_tech

    def remove_technician(self, tech_id: int) -> None:
        """
        Remove a technician from the roster.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        tech = self.get_tech_by_id_or_raise(tech_id)
        self.technicians.remove(tech)

    def assign_tech(self, tech_id: int) -> TechnicianEntity:
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
        tech = self.get_tech_by_id_or_raise(tech_id)
        
        if tech.status != "AVAILABLE":
            raise TechnicianNotAvailableError(tech_id, tech.status)
        
        tech.status = "BUSY"
        return tech

    def assign_next_available(self) -> TechnicianEntity:
        """
        Assign the next available technician in the queue.
        
        Returns:
            The assigned technician.
            
        Raises:
            NoAvailableTechniciansError: If no technicians are available.
        """
        tech = self.get_next_tech()
        if not tech:
            raise NoAvailableTechniciansError()
        
        tech.status = "BUSY"
        return tech

    def handle_tech_completion(self, tech_id: int, is_request: bool = False) -> TechnicianEntity:
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
        tech = self.get_tech_by_id_or_raise(tech_id)
        
        # Mark as available
        tech.status = "AVAILABLE"
        
        # Move to bottom of queue
        tech.queue_position = self.calculate_bottom_position()
        
        return tech

    def toggle_active_status(self, tech_id: int) -> TechnicianEntity:
        """
        Toggle a technician's active (checked-in) status.
        
        Args:
            tech_id: The technician's unique identifier.
            
        Returns:
            The updated technician.
            
        Raises:
            TechnicianNotFoundError: If technician is not found.
        """
        tech = self.get_tech_by_id_or_raise(tech_id)
        tech.is_active = not tech.is_active
        return tech

    def reorder_queue(self, tech_ids: List[int]) -> None:
        """
        Reorder the queue based on a new ordering of technician IDs.
        
        Args:
            tech_ids: List of technician IDs in the desired order.
        """
        for index, tech_id in enumerate(tech_ids):
            tech = self.get_tech_by_id(tech_id)
            if tech:
                tech.queue_position = index + 1

    # --- Serialization Methods ---

    def get_all_techs_sorted(self) -> List[dict]:
        """
        Get all technicians sorted by queue position.
        
        Returns:
            List of technician dictionaries ready for API response.
        """
        sorted_techs = sorted(self.technicians, key=lambda t: t.queue_position)
        return [
            {
                "id": t.id,
                "name": t.name,
                "status": t.status,
                "queue_position": t.queue_position,
                "is_active": t.is_active
            }
            for t in sorted_techs
        ]
