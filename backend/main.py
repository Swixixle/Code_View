"""
Code View - Evidence-backed code dissection engine
Main FastAPI application with live monitoring capabilities
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from analysis.scheduler import AnalysisScheduler
from api.dossier import dossier_router
from api.monitoring import monitoring_router
from api.routes import analysis_router
from api.websocket import WebSocketManager
from database import init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ws_manager = WebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and start monitoring services."""
    await init_database()
    logger.info("Database initialized")

    scheduler = AnalysisScheduler(ws_manager)
    app.state.scheduler = scheduler

    asyncio.create_task(start_monitoring_scheduler(scheduler))
    logger.info("Monitoring scheduler started")

    yield

    logger.info("Shutting down Code View")


app = FastAPI(
    title="Code View API",
    description="Evidence-backed code dissection with live monitoring",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router, prefix="/api/analysis", tags=["analysis"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(dossier_router, prefix="/api/dossier", tags=["dossier"])


@app.get("/")
async def root():
    return {
        "service": "Code View API",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "features": ["analysis", "dossiers", "live_monitoring", "evidence_trails"],
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "monitoring": "active",
        "websocket_connections": len(ws_manager.active_connections),
    }


@app.websocket("/ws/live-feed")
async def websocket_live_feed(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("subscribe:"):
                target = data.split(":", 1)[1]
                await ws_manager.subscribe(websocket, target)
                await websocket.send_text(f"subscribed:{target}")

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)


async def start_monitoring_scheduler(scheduler: AnalysisScheduler):
    while True:
        try:
            await scheduler.process_pending_tasks()
            await scheduler.check_repository_changes()
            await ws_manager.broadcast_heartbeat()
        except Exception as e:  # noqa: BLE001
            logger.error("Monitoring scheduler error: %s", e)

        await asyncio.sleep(30)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
