"""
Minimal test server for Marketing SMS Module - No Firestore dependency
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.marketing import router as marketing_router

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Salon Growth OS - Marketing Test API",
    description="Test API for Marketing SMS Module",
    version="1.0.0"
)

# CORS configuration - allow all origins for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include marketing router
app.include_router(marketing_router)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "marketing-test"}

if __name__ == "____main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
