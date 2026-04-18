"""
SMS Marketing Tool — Main Entry Point

FastAPI application for SMS marketing via Twilio.
Uses Firestore for PIN storage.
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

# Must run before any app.* import — several modules read os.getenv() at import time.
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

from app.routers import marketing_router
from app.routers.marketing import limiter

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


# --- Security Headers Middleware ---

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# --- App Setup ---

app = FastAPI(
    title="SMS Marketing Tool",
    description="SMS marketing via Twilio with Google Sheets integration",
    version="3.0.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — in production, SPA and API share the same origin so CORS is not needed.
# In development, allow Vite dev server and backend.
allowed_origins = (
    ["http://localhost:5173", "http://localhost:8080"]
    if not IS_PRODUCTION
    else [os.getenv("CORS_ORIGIN", "")]
)
# Filter out empty strings
allowed_origins = [o for o in allowed_origins if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Marketing-Pin"],
)

# Security headers
app.add_middleware(SecurityHeadersMiddleware)

# Include routers
app.include_router(marketing_router)


# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    from fastapi import HTTPException
    # Let FastAPI handle its own HTTPExceptions normally
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


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
        if full_path.startswith(("marketing", "health", "docs", "openapi", "assets")):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Not found")

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
