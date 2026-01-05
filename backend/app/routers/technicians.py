"""
Technician API Router - CRUD and action endpoints for technicians.
"""

from fastapi import APIRouter, HTTPException
from typing import List

from app.schemas import (
    TechnicianCreate,
    TechnicianResponse,
    AssignRequest,
    AssignResponse,
    CompleteRequest,
    CompleteResponse,
    ToggleActiveRequest,
    ToggleActiveResponse,
    ReorderRequest,
    ReorderResponse,
    RemoveResponse,
)
from app.services.turn_rules import (
    TechnicianNotFoundError,
    TechnicianNotAvailableError,
    NoAvailableTechniciansError,
)

router = APIRouter(prefix="/techs", tags=["technicians"])


def get_dependencies():
    """Get shared dependencies (turn_service, database functions, broadcast).

    This is imported at runtime to avoid circular imports.
    """
    from main import turn_service, HAS_DATABASE, broadcast_update
    try:
        from app.database import (
            save_technician as db_save_tech,
            delete_technician as db_delete_tech,
            save_all_technicians,
            update_technician_status,
        )
    except ImportError:
        db_save_tech = None
        db_delete_tech = None
        save_all_technicians = None
        update_technician_status = None

    return {
        "turn_service": turn_service,
        "HAS_DATABASE": HAS_DATABASE,
        "broadcast_update": broadcast_update,
        "db_save_tech": db_save_tech,
        "db_delete_tech": db_delete_tech,
        "save_all_technicians": save_all_technicians,
        "update_technician_status": update_technician_status,
    }


@router.get("", response_model=List[TechnicianResponse])
async def list_techs():
    """Get all technicians sorted by queue position."""
    deps = get_dependencies()
    return deps["turn_service"].get_all_techs_sorted()


@router.post("", response_model=TechnicianResponse)
async def add_tech(tech: TechnicianCreate):
    """Add a new technician to the roster."""
    deps = get_dependencies()
    turn_service = deps["turn_service"]

    new_tech = turn_service.add_technician(tech.name)

    if deps["HAS_DATABASE"] and deps["db_save_tech"]:
        await deps["db_save_tech"]({
            "id": new_tech.id,
            "name": new_tech.name,
            "status": new_tech.status,
            "queue_position": new_tech.queue_position,
            "is_active": new_tech.is_active,
        }, update_status_time=True)

    await deps["broadcast_update"]()

    return {
        "id": new_tech.id,
        "name": new_tech.name,
        "status": new_tech.status,
        "queue_position": new_tech.queue_position,
        "is_active": new_tech.is_active
    }


@router.delete("/{tech_id}", response_model=RemoveResponse)
async def remove_tech(tech_id: int):
    """Remove a technician from the roster permanently."""
    deps = get_dependencies()

    try:
        deps["turn_service"].remove_technician(tech_id)

        if deps["HAS_DATABASE"] and deps["db_delete_tech"]:
            await deps["db_delete_tech"](tech_id)

        await deps["broadcast_update"]()
        return RemoveResponse(tech_id=tech_id)
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/toggle-active", response_model=ToggleActiveResponse)
async def toggle_tech_active(req: ToggleActiveRequest):
    """Toggle a technician's active (checked-in) status."""
    deps = get_dependencies()

    try:
        tech = deps["turn_service"].toggle_active_status(req.tech_id)

        if deps["HAS_DATABASE"] and deps["db_save_tech"]:
            await deps["db_save_tech"]({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=tech.is_active)

        await deps["broadcast_update"]()
        return ToggleActiveResponse(tech_id=tech.id, is_active=tech.is_active)
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reorder", response_model=ReorderResponse)
async def reorder_techs(req: ReorderRequest):
    """Reorder the technician queue based on a new ordering."""
    deps = get_dependencies()

    deps["turn_service"].reorder_queue(req.tech_ids)

    if deps["HAS_DATABASE"] and deps["save_all_technicians"]:
        await deps["save_all_technicians"](deps["turn_service"].get_all_techs_sorted())

    await deps["broadcast_update"]()
    return ReorderResponse()


# --- Action Endpoints (outside /techs prefix) ---

assign_router = APIRouter(tags=["actions"])


@assign_router.post("/assign", response_model=AssignResponse)
async def assign_tech(req: AssignRequest):
    """Assign a technician to a client."""
    deps = get_dependencies()
    turn_service = deps["turn_service"]

    try:
        if req.request_tech_id:
            tech = turn_service.assign_tech(req.request_tech_id)
        else:
            tech = turn_service.assign_next_available()

        if deps["HAS_DATABASE"] and deps["update_technician_status"]:
            await deps["update_technician_status"](tech.id, tech.status)

        await deps["broadcast_update"]()

        return AssignResponse(
            assigned_tech_id=tech.id,
            assigned_tech_name=tech.name,
            client=req.client_name
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TechnicianNotAvailableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoAvailableTechniciansError as e:
        raise HTTPException(status_code=404, detail=str(e))


@assign_router.post("/complete", response_model=CompleteResponse)
async def complete_turn(req: CompleteRequest):
    """Complete a technician's turn and move them to the bottom of the queue."""
    deps = get_dependencies()

    try:
        tech = deps["turn_service"].handle_tech_completion(req.tech_id, req.is_request)

        if deps["HAS_DATABASE"] and deps["db_save_tech"]:
            await deps["db_save_tech"]({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=True)

        await deps["broadcast_update"]()

        return CompleteResponse(
            completed_tech_id=tech.id,
            new_queue_position=tech.queue_position
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
