"""
WebSocket Manager for FluxTrader API
Handles real-time WebSocket connections for live trading updates
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Store active connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Store client subscriptions
        self.client_subscriptions: Dict[str, Set[str]] = {}
        self.connection_count = 0

    async def connect(self, client_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            self.client_subscriptions[client_id] = set()
            self.connection_count += 1

            logger.info(
                f"WebSocket client {client_id} connected. Total connections: {self.connection_count}"
            )

            # Send welcome message
            await self.send_personal_message(
                client_id,
                {
                    "type": "connection_established",
                    "client_id": client_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": "Connected to FluxTrader WebSocket",
                },
            )

        except Exception as e:
            logger.error(f"Error connecting WebSocket client {client_id}: {e}")

    async def disconnect(self, client_id: str):
        """Remove a WebSocket connection."""
        try:
            if client_id in self.active_connections:
                del self.active_connections[client_id]

            if client_id in self.client_subscriptions:
                del self.client_subscriptions[client_id]

            self.connection_count -= 1
            logger.info(
                f"WebSocket client {client_id} disconnected. Total connections: {self.connection_count}"
            )

        except Exception as e:
            logger.error(f"Error disconnecting WebSocket client {client_id}: {e}")

    async def send_personal_message(self, client_id: str, message: Dict[str, Any]):
        """Send a message to a specific client."""
        try:
            if client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                await websocket.send_text(json.dumps(message))

        except WebSocketDisconnect:
            logger.info(f"Client {client_id} disconnected during message send")
            await self.disconnect(client_id)
        except Exception as e:
            logger.error(f"Error sending message to client {client_id}: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        # Add timestamp to message
        message["timestamp"] = datetime.utcnow().isoformat()

        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected_clients.append(client_id)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            await self.disconnect(client_id)

    async def broadcast_agent_update(
        self,
        agent_id: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[int] = None,
    ):
        """Broadcast agent-specific updates to subscribed clients with optional user filtering."""
        message = {
            "type": "agent_update",
            "agent_id": agent_id,
            "event": event_type,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,  # Include user_id for filtering
        }

        # Filter and send only to clients subscribed to this agent
        subscribed_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if agent_id in subscriptions:
                subscribed_clients.append(client_id)

        if subscribed_clients:
            logger.info(
                f"📡 Broadcasting agent update for {agent_id} to {len(subscribed_clients)} subscribed clients"
            )
            disconnected_clients = []

            for client_id in subscribed_clients:
                if client_id in self.active_connections:
                    try:
                        websocket = self.active_connections[client_id]
                        await websocket.send_text(json.dumps(message))
                        logger.debug(f"✅ Sent agent update to client {client_id}")
                    except WebSocketDisconnect:
                        disconnected_clients.append(client_id)
                    except Exception as e:
                        logger.error(
                            f"❌ Error sending agent update to client {client_id}: {e}"
                        )
                        disconnected_clients.append(client_id)

            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
        else:
            logger.debug(
                f"📡 No clients subscribed to agent {agent_id}, skipping broadcast"
            )

    async def broadcast_trading_update(self, update_data: Dict[str, Any]):
        """Broadcast trading-related updates."""
        message = {"type": "trading_update", "data": update_data}

        await self.broadcast(message)

    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status updates."""
        message = {"type": "system_status", "data": status_data}

        await self.broadcast(message)

    async def broadcast_cycle_analysis(
        self, agent_id: str, cycle_data: Dict[str, Any], user_id: Optional[int] = None
    ):
        """Broadcast detailed trading cycle analysis updates."""
        message = {
            "type": "cycle_analysis",
            "agent_id": agent_id,
            "data": cycle_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }

        # Filter and send only to clients subscribed to this agent
        subscribed_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if agent_id in subscriptions:
                subscribed_clients.append(client_id)

        if subscribed_clients:
            logger.info(
                f"📊 Broadcasting cycle analysis for {agent_id} to {len(subscribed_clients)} subscribed clients"
            )
            disconnected_clients = []

            for client_id in subscribed_clients:
                if client_id in self.active_connections:
                    try:
                        websocket = self.active_connections[client_id]
                        await websocket.send_text(json.dumps(message))
                        logger.debug(f"✅ Sent cycle analysis to client {client_id}")
                    except WebSocketDisconnect:
                        disconnected_clients.append(client_id)
                    except Exception as e:
                        logger.error(
                            f"❌ Error sending cycle analysis to client {client_id}: {e}"
                        )
                        disconnected_clients.append(client_id)

            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
        else:
            logger.debug(
                f"📊 No clients subscribed to agent {agent_id} for cycle analysis"
            )

    async def broadcast_trade_execution(
        self, agent_id: str, trade_data: Dict[str, Any], user_id: Optional[int] = None
    ):
        """Broadcast live trade execution updates."""
        message = {
            "type": "trade_execution",
            "agent_id": agent_id,
            "data": trade_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
        }

        # Filter and send only to clients subscribed to this agent
        subscribed_clients = []
        for client_id, subscriptions in self.client_subscriptions.items():
            if agent_id in subscriptions:
                subscribed_clients.append(client_id)

        if subscribed_clients:
            logger.info(
                f"💰 Broadcasting trade execution for {agent_id} to {len(subscribed_clients)} subscribed clients"
            )
            disconnected_clients = []

            for client_id in subscribed_clients:
                if client_id in self.active_connections:
                    try:
                        websocket = self.active_connections[client_id]
                        await websocket.send_text(json.dumps(message))
                        logger.debug(f"✅ Sent trade execution to client {client_id}")
                    except WebSocketDisconnect:
                        disconnected_clients.append(client_id)
                    except Exception as e:
                        logger.error(
                            f"❌ Error sending trade execution to client {client_id}: {e}"
                        )
                        disconnected_clients.append(client_id)

            # Clean up disconnected clients
            for client_id in disconnected_clients:
                await self.disconnect(client_id)
        else:
            logger.debug(
                f"💰 No clients subscribed to agent {agent_id} for trade execution"
            )

    async def subscribe_to_agent(self, client_id: str, agent_id: str):
        """Subscribe a client to agent-specific updates."""
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].add(agent_id)

            await self.send_personal_message(
                client_id,
                {
                    "type": "subscription_confirmed",
                    "agent_id": agent_id,
                    "message": f"Subscribed to updates for agent {agent_id}",
                },
            )

    async def unsubscribe_from_agent(self, client_id: str, agent_id: str):
        """Unsubscribe a client from agent-specific updates."""
        if client_id in self.client_subscriptions:
            self.client_subscriptions[client_id].discard(agent_id)

            await self.send_personal_message(
                client_id,
                {
                    "type": "subscription_cancelled",
                    "agent_id": agent_id,
                    "message": f"Unsubscribed from updates for agent {agent_id}",
                },
            )

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return self.connection_count

    def is_healthy(self) -> bool:
        """Check if the WebSocket manager is healthy."""
        return True  # Simple health check

    async def send_ping_to_all(self):
        """Send ping to all connected clients to keep connections alive."""
        ping_message = {"type": "ping", "message": "keepalive"}

        await self.broadcast(ping_message)

    def get_client_info(self) -> Dict[str, Any]:
        """Get information about connected clients."""
        return {
            "total_connections": self.connection_count,
            "active_clients": list(self.active_connections.keys()),
            "subscriptions": {
                client_id: list(subs)
                for client_id, subs in self.client_subscriptions.items()
            },
        }
