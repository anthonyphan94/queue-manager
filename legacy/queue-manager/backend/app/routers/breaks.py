"""
Break Management Router - Endpoints for technician break handling.

STATELESS: All operations use async TurnRulesService which queries Firestore directly.
"""

from fastapi import APIRouter, HTTPException

from app.schemas import BreakRequest, BreakResponse
from app.services.turn_rules import TechnicianNotFoundError

router = APIRouter(prefix="/techs", tags=["breaks"])


def get_dependencies():
    """Get shared dependencies (turn_service, broadcast).

    This is imported at runtime to avoid circular imports.
    """
    from main import turn_service, broadcast_update

    return {
        "turn_service": turn_service,
        "broadcast_update": broadcast_update,
    }


@router.post("/break", response_model=BreakResponse)
async def take_break(req: BreakRequest):
    """Put a technician on break."""
    deps = get_dependencies()

    try:
        tech = await deps["turn_service"].take_break(req.tech_id)
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
        tech = await deps["turn_service"].return_from_break(req.tech_id)
        await deps["broadcast_update"]()

        return BreakResponse(
            tech_id=tech.id,
            status=tech.status,
            status_start_time=None
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
