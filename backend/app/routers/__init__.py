"""API Routers package."""
from .technicians import router as technicians_router
from .breaks import router as breaks_router
from .marketing import router as marketing_router

__all__ = ["technicians_router", "breaks_router", "marketing_router"]
