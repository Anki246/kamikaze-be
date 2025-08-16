"""
Mock WebSocket Manager
"""

import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.connections = {}
        logger.info("Mock WebSocketManager initialized")

    async def connect(self, websocket, client_id: str):
        self.connections[client_id] = websocket

    async def disconnect(self, client_id: str):
        if client_id in self.connections:
            del self.connections[client_id]

    async def send_message(self, client_id: str, message: dict):
        pass

    async def broadcast(self, message: dict):
        pass


websocket_manager = WebSocketManager()
