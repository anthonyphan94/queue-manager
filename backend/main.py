"""
SMS Marketing Tool — Main Entry Point

FastAPI application for SMS marketing via Twilio.
Uses Firestore for PIN storage.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import marketing_router

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

IS_PRODUCTION = os.getenv("PORT") is not None
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# --- Database Import (for PIN storage) ---

try:
    from app.database import init_db, FIRESTORE_AVAILABLE
    HAS_DATABASE = True
except Exception as e:
    logger.warning(f"Database not available: {e}. Running without persistence.")
    HAS_DATABASE = False
    FIRESTORE_AVAILABLE = False


# --- Lifespan (startup/shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Firestore connection on startup (used for PIN storage)."""
    if HAS_DATABASE:
        try:
            await init_db()
            logger.info("Firestore connected for settings storage")
        except Exception as e:
            logger.error(f"Failed to connect to Firestore: {e}", exc_info=True)
    else:
        logger.warning("Running without Firestore — PIN will use env var fallback")

    yield


# --- App Setup ---

app = FastAPI(
    title="SMS Marketing Tool",
    description="SMS marketing via Twilio with Google Sheets integration",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = ["*"] if not IS_PRODUCTION else [
    "https://*.run.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(marketing_router)


# --- Health Check ---

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# --- Static Files & SPA ---

if os.path.isdir(STATIC_DIR):
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("marketing", "health", "docs", "openapi")):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="API route not found")

        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Frontend build files not found")


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
