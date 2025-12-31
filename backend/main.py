"""
Salon Turn Manager API - Main Entry Point

This module defines FastAPI endpoints that delegate to the TurnRulesService.
All business logic is contained in the services layer.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List
from contextlib import asynccontextmanager
import json
import os

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
    BreakRequest,
    BreakResponse,
)
from app.services.turn_rules import (
    TurnRulesService,
    TechnicianEntity,
    TechnicianNotFoundError,
    TechnicianNotAvailableError,
    NoAvailableTechniciansError,
)


# --- Configuration ---

IS_PRODUCTION = os.getenv("PORT") is not None  # Cloud Run sets PORT
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


# --- Database Import (optional persistence) ---

try:
    from app.database import (
        init_db, 
        load_technicians, 
        save_all_technicians, 
        save_technician as db_save_tech, 
        delete_technician as db_delete_tech,
        update_technician_status
    )
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    # Provide a no-op fallback if database module not available
    async def update_technician_status(tech_id: int, status: str) -> None:
        pass


# --- Lifespan (startup/shutdown) ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and load data on startup."""
    global technicians, turn_service
    
    if HAS_DATABASE:
        await init_db()
        loaded = await load_technicians()
        for t in loaded:
            technicians.append(TechnicianEntity(
                id=t["id"],
                name=t["name"],
                status=t["status"],
                queue_position=t["queue_position"],
                is_active=t["is_active"],
                status_start_time=None  # Will be parsed from Firestore if needed
            ))
        print(f"📦 Loaded {len(technicians)} technicians from database")
    
    yield  # App runs here
    
    # Cleanup (optional)
    if HAS_DATABASE and technicians:
        await save_all_technicians(turn_service.get_all_techs_sorted())
        print("💾 Saved technicians to database on shutdown")


# --- App Setup ---

app = FastAPI(
    title="Salon Turn Manager API",
    description="API for managing salon technician turn queue",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - restrict in production
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


# --- Service Initialization ---

# In-memory storage - list of TechnicianEntity objects
technicians: List[TechnicianEntity] = []

# Initialize the service with the technicians list
turn_service = TurnRulesService(technicians)


# --- WebSocket Connection Manager ---

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# --- Helper Functions ---

async def broadcast_update() -> None:
    """Broadcast the current state to all WebSocket clients."""
    data = json.dumps({
        "type": "update",
        "technicians": turn_service.get_all_techs_sorted()
    })
    await manager.broadcast(data)


# --- REST Endpoints ---

@app.get("/techs", response_model=List[TechnicianResponse])
def list_techs():
    """Get all technicians sorted by queue position."""
    return turn_service.get_all_techs_sorted()


@app.post("/techs", response_model=TechnicianResponse)
async def add_tech(tech: TechnicianCreate):
    """Add a new technician to the roster."""
    new_tech = turn_service.add_technician(tech.name)
    # Save the new technician to Firestore with SERVER_TIMESTAMP
    if HAS_DATABASE:
        await db_save_tech({
            "id": new_tech.id,
            "name": new_tech.name,
            "status": new_tech.status,
            "queue_position": new_tech.queue_position,
            "is_active": new_tech.is_active,
        }, update_status_time=True)
    await broadcast_update()
    return {
        "id": new_tech.id,
        "name": new_tech.name,
        "status": new_tech.status,
        "queue_position": new_tech.queue_position,
        "is_active": new_tech.is_active
    }


@app.post("/assign", response_model=AssignResponse)
async def assign_tech(req: AssignRequest):
    """Assign a technician to a client."""
    try:
        if req.request_tech_id:
            # Specific technician requested
            tech = turn_service.assign_tech(req.request_tech_id)
        else:
            # Get next available
            tech = turn_service.assign_next_available()
        
        # Set status_start_time using Firestore SERVER_TIMESTAMP
        if HAS_DATABASE:
            await update_technician_status(tech.id, tech.status)
        await broadcast_update()
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


@app.post("/complete", response_model=CompleteResponse)
async def complete_turn(req: CompleteRequest):
    """Complete a technician's turn and move them to the bottom of the queue."""
    try:
        tech = turn_service.handle_tech_completion(req.tech_id, req.is_request)
        # Save full state to Firestore (status + queue_position changed)
        if HAS_DATABASE:
            await db_save_tech({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=True)
        await broadcast_update()
        return CompleteResponse(
            completed_tech_id=tech.id,
            new_queue_position=tech.queue_position
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/techs/toggle-active", response_model=ToggleActiveResponse)
async def toggle_tech_active(req: ToggleActiveRequest):
    """Toggle a technician's active (checked-in) status."""
    try:
        tech = turn_service.toggle_active_status(req.tech_id)
        # Save is_active change to Firestore
        # Reset status_start_time when checking back in (is_active becomes True)
        if HAS_DATABASE:
            await db_save_tech({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=tech.is_active)  # Reset timer when checking in
        await broadcast_update()
        return ToggleActiveResponse(
            tech_id=tech.id,
            is_active=tech.is_active
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/techs/{tech_id}", response_model=RemoveResponse)
async def remove_tech(tech_id: int):
    """Remove a technician from the roster permanently."""
    try:
        turn_service.remove_technician(tech_id)
        # Delete from Firestore
        if HAS_DATABASE:
            await db_delete_tech(tech_id)
        await broadcast_update()
        return RemoveResponse(tech_id=tech_id)
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/techs/reorder", response_model=ReorderResponse)
async def reorder_techs(req: ReorderRequest):
    """Reorder the technician queue based on a new ordering."""
    turn_service.reorder_queue(req.tech_ids)
    # Save all queue positions to Firestore
    if HAS_DATABASE:
        await save_all_technicians(turn_service.get_all_techs_sorted())
    await broadcast_update()
    return ReorderResponse()


@app.post("/techs/break", response_model=BreakResponse)
async def take_break(req: BreakRequest):
    """Put a technician on break."""
    try:
        tech = turn_service.take_break(req.tech_id)
        # Set status_start_time using Firestore SERVER_TIMESTAMP
        if HAS_DATABASE:
            await update_technician_status(tech.id, tech.status)
        await broadcast_update()
        return BreakResponse(
            tech_id=tech.id,
            status=tech.status,
            status_start_time=None  # Will be fetched from Firestore on next load
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/techs/return", response_model=BreakResponse)
async def return_from_break(req: BreakRequest):
    """Return a technician from break to the queue."""
    try:
        tech = turn_service.return_from_break(req.tech_id)
        # Save full state to Firestore (status + queue_position changed)
        if HAS_DATABASE:
            await db_save_tech({
                "id": tech.id,
                "name": tech.name,
                "status": tech.status,
                "queue_position": tech.queue_position,
                "is_active": tech.is_active,
            }, update_status_time=True)
        await broadcast_update()
        return BreakResponse(
            tech_id=tech.id,
            status=tech.status,
            status_start_time=None  # Will be fetched from Firestore on next load
        )
    except TechnicianNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- WebSocket Endpoint ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    # Send current state on connect
    init_data = json.dumps({
        "type": "init",
        "technicians": turn_service.get_all_techs_sorted()
    })
    await websocket.send_text(init_data)
    
    try:
        while True:
            # Keep connection alive, listen for messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# --- Health Check Endpoint ---

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "version": "2.0.0"}


# --- Static File Serving (Production) ---

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": f"Không tìm thấy index.html tại {index_path}"}

if os.path.isdir(STATIC_DIR):
    # 1. Phục vụ các file assets (JS, CSS, Images)
    # Các file này thường nằm trong backend/static/assets
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    # 2. Route trang chủ (Tránh lỗi "Not Found" khi vào link gốc)
    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(STATIC_DIR, "index.html"))

    # 3. Catch-all route cho SPA (React Router)
    # Phải đặt ở CUỐI CÙNG sau tất cả các API khác
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Nếu path bắt đầu bằng 'api' hoặc các route backend, trả về 404 thật
        if full_path.startswith(("techs", "ws", "health", "docs", "openapi")):
            raise HTTPException(status_code=404, detail="API route not found")
        
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Frontend build files not found")
else:
    print(f"Cảnh báo: Không tìm thấy thư mục static tại {STATIC_DIR}")


# --- Entry Point ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)

