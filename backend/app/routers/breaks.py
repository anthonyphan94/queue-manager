"""
Break Management Router - Endpoints for technician break handling.
"""

from fastapi import APIRouter, HTTPException

from app.schemas import BreakRequest, BreakResponse
from app.services.turn_rules import TechnicianNotFoundError

router = APIRouter(prefix="/techs", tags=["breaks"])


def get_dependencies():
    """Get shared dependencies (turn_service, database functions, broadcast).

    This is imported at runtime to avoid circular imports.
    """
    from main import turn_service, HAS_DATABASE, broadcast_update
    try:
        from app.database import (
            save_technician as db_save_tech,
            update_technician_status,
        )
    except ImportError:
        db_save_tech = None
        update_technician_status = None

    return {
        "turn_service": turn_service,
        "HAS_DATABASE": HAS_DATABASE,
        "broadcast_update": broadcast_update,
        "db_save_tech": db_save_tech,
        "update_technician_status": update_technician_status,
    }


@router.post("/break", response_model=BreakResponse)
async def take_break(req: BreakRequest):
    """Put a technician on break."""
    deps = get_dependencies()

    try:
        tech = deps["turn_service"].take_break(req.tech_id)

        if deps["HAS_DATABASE"] and deps["update_technician_status"]:
            await deps["update_technician_status"](tech.id, tech.status)

        await deps["broadcast_update"]()

        return BreakResponse(
            tech_id=tech.id,
            status=tech.status,
            status_start_time=None
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/return", response_model=BreakResponse)
async def return_from_break(req: BreakRequest):
    """Return a technician from break to the queue."""
    deps = get_dependencies()

    try:
        tech = deps["turn_service"].return_from_break(req.tech_id)

        if deps["HAS_DATABASE"] and deps["db_save_tech"]:
            await deps["db_save_tech"]({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=True)

        await deps["broadcast_update"]()

        return BreakResponse(
            tech_id=tech.id,
            status=tech.status,
            status_start_time=None
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
