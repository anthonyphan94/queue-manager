"""
Salon Turn Manager API - Main Entry Point

This module sets up the FastAPI application and includes routers.
Business logic is contained in the services layer.

STATELESS ARCHITECTURE: No in-memory cache - Firestore is the single source of truth.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import technicians_router, breaks_router, marketing_router
from app.routers.technicians import assign_router
from app.services.turn_rules import TurnRulesService

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
        delete_all_technicians,
        FIRESTORE_AVAILABLE
    )
    HAS_DATABASE = True
except Exception as e:
    logger.warning(f"Database not available: {e}. Running without persistence.")
    HAS_DATABASE = False
    FIRESTORE_AVAILABLE = False


# --- Service Initialization (Stateless) ---

turn_service = TurnRulesService()  # Stateless - no in-memory cache


# --- Broadcast Helper ---

async def broadcast_update() -> None:
    """Placeholder for future real-time updates (e.g., Server-Sent Events)."""
    pass


# --- Lifespan (startup/shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database connection on startup.
    
    STATELESS: No cache loading - just verify Firestore connection.
    """
    if HAS_DATABASE:
        try:
            await init_db()
            # Quick verification that Firestore is accessible
            techs = await load_technicians()
            logger.info(f"Firestore connected - {len(techs)} technicians in database")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}", exc_info=True)
    else:
        logger.warning("HAS_DATABASE is False - running without persistence")

    yield

    # STATELESS: No need to save on shutdown - all writes are immediate


# --- App Setup ---

app = FastAPI(
    title="Salon Turn Manager API",
    description="API for managing salon technician turn queue",
    version="2.1.0",  # Version bump for stateless refactor
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
    tech_count = 0
    if HAS_DATABASE:
        try:
            techs = await load_technicians()
            tech_count = len(techs)
        except Exception:
            pass
    
    return {
        "status": "healthy",
        "version": "2.1.0",
        "architecture": "stateless",
        "debug": {
            "technician_count": tech_count,
            "has_database": HAS_DATABASE,
            "firestore_available": FIRESTORE_AVAILABLE
        }
    }


@app.post("/admin/reset-technicians")
async def reset_all_technicians():
    """ADMIN: Delete all technicians from Firestore.
    
    WARNING: This will delete ALL technicians permanently!
    """
    deleted_count = 0
    if HAS_DATABASE:
        deleted_count = await delete_all_technicians()
    
    logger.info(f"Reset technicians: deleted {deleted_count} from Firestore")
    
    return {
        "success": True,
        "deleted_from_firestore": deleted_count,
        "message": "All technicians deleted. Start fresh!"
    }



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
