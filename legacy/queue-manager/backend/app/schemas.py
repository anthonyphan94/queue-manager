"""
Pydantic schemas and data models for the Salon Turn Manager.
These models define the structure of data used throughout the application.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import datetime


class TechnicianStatus(str, Enum):
    """Status of a technician in the turn queue."""
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    ON_BREAK = "ON_BREAK"


class TechnicianBase(BaseModel):
    """Base technician model with common fields."""
    name: str = Field(..., min_length=1, description="Technician's display name")


class TechnicianCreate(TechnicianBase):
    """Request model for creating a new technician."""
    pass


class Technician(TechnicianBase):
    """Full technician model with all fields."""
    id: int
    status: TechnicianStatus = TechnicianStatus.AVAILABLE
    queue_position: int = 0
    is_active: bool = False  # False = Offline, True = Online (checked-in)
    status_start_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class TechnicianResponse(BaseModel):
    """Response model for technician data."""
    id: int
    name: str
    status: str
    queue_position: int
    is_active: bool
    status_start_time: Optional[str] = None


# --- Request Models ---

class AssignRequest(BaseModel):
    """Request to assign a technician to a client."""
    client_name: str = "Walk-in"
    request_tech_id: Optional[int] = None


class CompleteRequest(BaseModel):
    """Request to complete a technician's turn."""
    tech_id: int
    is_request: bool = False


class ToggleActiveRequest(BaseModel):
    """Request to toggle a technician's active status."""
    tech_id: int


class ReorderRequest(BaseModel):
    """Request to reorder the technician queue."""
    tech_ids: List[int]


# --- Response Models ---

class AssignResponse(BaseModel):
    """Response after assigning a technician."""
    assigned_tech_id: int
    assigned_tech_name: str
    client: str


class CompleteResponse(BaseModel):
    """Response after completing a turn."""
    completed_tech_id: int
    new_queue_position: int


class ToggleActiveResponse(BaseModel):
    """Response after toggling active status."""
    tech_id: int
    is_active: bool


class RemoveResponse(BaseModel):
    """Response after removing a technician."""
    status: str = "removed"
    tech_id: int


class ReorderResponse(BaseModel):
    """Response after reordering the queue."""
    status: str = "ok"


class BreakRequest(BaseModel):
    """Request to take or return from break."""
    tech_id: int


class BreakResponse(BaseModel):
    """Response after break action."""
    tech_id: int
    status: str
    status_start_time: Optional[str] = None
