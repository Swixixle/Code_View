"""WebSocket connection manager for live updates."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info("WebSocket connected. Total connections: %s", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info("WebSocket disconnected. Total connections: %s", len(self.active_connections))

    async def subscribe(self, websocket: WebSocket, target: str) -> None:
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(target)
            logger.info("WebSocket subscribed to %s", target)

    async def broadcast_to_subscribers(self, target: str, message: dict) -> None:
        message_json = json.dumps(message)
        disconnected: List[WebSocket] = []

        for websocket, subscriptions in self.subscriptions.items():
            if target in subscriptions:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to send message to WebSocket: %s", e)
                    disconnected.append(websocket)

        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_heartbeat(self) -> None:
        message = {
            "type": "heartbeat",
            "timestamp": datetime.now().isoformat(),
            "active_connections": len(self.active_connections),
        }
        await self.broadcast_to_all(message)

    async def broadcast_to_all(self, message: dict) -> None:
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected: List[WebSocket] = []

        for websocket in self.active_connections:
            try:
                await websocket.send_text(message_json)
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to broadcast to WebSocket: %s", e)
                disconnected.append(websocket)

        for websocket in disconnected:
            await self.disconnect(websocket)
