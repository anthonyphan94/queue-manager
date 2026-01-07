"""
Salon Turn Manager API - Main Entry Point

This module sets up the FastAPI application and includes routers.
Business logic is contained in the services layer.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import technicians_router, breaks_router, marketing_router
from app.routers.technicians import assign_router
from app.services.turn_rules import TurnRulesService, TechnicianEntity

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv("PORT") is not None
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# --- Database Import (optional persistence) ---

try:
    from app.database import (
        init_db,
        load_technicians,
        save_all_technicians,
        save_technician as db_save_tech,
        delete_technician as db_delete_tech,
        update_technician_status,
        FIRESTORE_AVAILABLE
    )
    HAS_DATABASE = True
except Exception as e:
    logger.warning(f"Database not available: {e}. Running without persistence.")
    HAS_DATABASE = False

    async def update_technician_status(tech_id: int, status: str) -> None:
        pass


# --- Service Initialization ---

technicians: List[TechnicianEntity] = []
turn_service = TurnRulesService(technicians)


# --- Broadcast Helper ---

async def broadcast_update() -> None:
    """Placeholder for future real-time updates (e.g., Server-Sent Events)."""
    pass


# --- Lifespan (startup/shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and load data on startup."""
    global technicians, turn_service

    if HAS_DATABASE:
        try:
            await init_db()
            loaded = await load_technicians()
            logger.info(f"load_technicians returned {len(loaded)} technicians")
            for t in loaded:
                technicians.append(TechnicianEntity(
                    id=t["id"],
                    name=t["name"],
                    status=t["status"],
                    queue_position=t["queue_position"],
                    is_active=t["is_active"],
                    status_start_time=None
                ))
            logger.info(f"Loaded {len(technicians)} technicians from database")
        except Exception as e:
            logger.error(f"Failed to load technicians from database: {e}", exc_info=True)
    else:
        logger.warning("HAS_DATABASE is False - running without persistence")

    yield

    if HAS_DATABASE and technicians:
        try:
            await save_all_technicians(turn_service.get_all_techs_sorted())
            logger.info("Saved technicians to database on shutdown")
        except Exception as e:
            logger.error(f"Failed to save technicians on shutdown: {e}", exc_info=True)


# --- App Setup ---

app = FastAPI(
    title="Salon Turn Manager API",
    description="API for managing salon technician turn queue",
    version="2.0.0",
    lifespan=lifespan
)

# CORS configuration
allowed_origins = ["*"] if not IS_PRODUCTION else [
    "https://*.run.app",
    "https://salon-turn-manager-*.run.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(technicians_router)
app.include_router(breaks_router)
app.include_router(assign_router)
app.include_router(marketing_router)


# --- Health Check ---

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run with debug info."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "debug": {
            "technician_count": len(technicians),
            "has_database": HAS_DATABASE,
            "firestore_available": FIRESTORE_AVAILABLE
        }
    }


# --- Static File Serving (Production) ---

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve the frontend index.html."""
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve SPA for client-side routing."""
        if full_path.startswith(("techs", "health", "docs", "openapi", "assign", "complete")):
            raise HTTPException(status_code=404, detail="API route not found")

        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build files not found")


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
