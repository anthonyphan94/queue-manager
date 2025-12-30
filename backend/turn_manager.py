from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

class TechnicianStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"

@dataclass
class Technician:
    id: int
    name: str
    status: TechnicianStatus
    queue_position: int
    is_active: bool = False  # False = Offline, True = Online (checked-in)

class TurnEngine:
    def __init__(self, technicians: List[Technician] = None):
        if technicians is None:
            technicians = []
        self.technicians = technicians

    def get_next_tech(self) -> Optional[Technician]:
        # Only consider techs that are both AVAILABLE and is_active (checked-in)
        available_techs = [t for t in self.technicians if t.status == TechnicianStatus.AVAILABLE and t.is_active]
        if not available_techs:
            return None
        # Sort by queue_position ascending
        available_techs.sort(key=lambda t: t.queue_position)
        return available_techs[0]

    def complete_turn(self, tech_id: int, is_request: bool) -> None:
        tech = next((t for t in self.technicians if t.id == tech_id), None)
        if not tech:
            raise ValueError(f"Technician with ID {tech_id} not found.")

        # Find current max queue_position
        # We need to consider all technicians to find the absolute bottom
        if not self.technicians:
            max_pos = 0
        else:
            max_pos = max(t.queue_position for t in self.technicians)
        
        # Rule 3: Always move to bottom (max + 1)
        tech.queue_position = max_pos + 1
