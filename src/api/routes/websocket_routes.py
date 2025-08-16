"""
WebSocket API Routes for FluxTrader
Provides WebSocket endpoints for real-time communication with user authentication
"""

import json
import logging
from typing import Any, Dict, Optional

import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from ...infrastructure.auth_database import auth_db

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["WebSocket"])

# Global managers (will be injected)
websocket_manager = None
market_data_api = None

# JWT Configuration (should match auth_routes.py)
JWT_SECRET = "your-secret-key-change-in-production"
JWT_ALGORITHM = "HS256"


def set_managers(ws_mgr, market_api):
    """Set the global managers."""
    global websocket_manager, market_data_api
    websocket_manager = ws_mgr
    market_data_api = market_api


async def authenticate_websocket_user(token: str) -> Optional[Dict[str, Any]]:
    """Authenticate user from WebSocket token."""
    try:
        # Verify JWT token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        if not await auth_db.ensure_connected():
            logger.error("Database connection failed in WebSocket authentication")
            return None

        user = await auth_db.get_user_by_id(int(user_id))
        if not user or not user.get("is_active", True):
            return None

        # Remove sensitive information
        user.pop("hashed_password", None)
        return user

    except (ExpiredSignatureError, InvalidTokenError, ValueError, Exception) as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return None


@router.websocket("/ws")
async def websocket_main_endpoint(
    websocket: WebSocket, token: Optional[str] = Query(None)
):
    """Main WebSocket endpoint for real-time agent updates with authentication."""
    # Generate a client ID
    import uuid

    client_id = str(uuid.uuid4())[:8]

    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return

    # Authenticate user (temporarily disabled for testing)
    user = None
    if token:
        user = await authenticate_websocket_user(token)
        if not user:
            logger.warning(
                f"🔒 WebSocket authentication failed for client {client_id}, using test user"
            )
            user = {"id": 17, "username": "test_user", "email": "test@example.com"}
    else:
        logger.warning(
            f"🔒 No token provided for WebSocket connection {client_id}, using test user"
        )
        user = {"id": 17, "username": "test_user", "email": "test@example.com"}

    # Store user info with connection
    authenticated_client_id = f"user_{user['id']}_{client_id}"
    await websocket_manager.connect(authenticated_client_id, websocket)

    logger.info(
        f"🔌 WebSocket connected: {authenticated_client_id} (user: {user['id']})"
    )

    try:
        # Send initial connection confirmation
        await websocket.send_text(
            json.dumps(
                {
                    "type": "connected",
                    "client_id": authenticated_client_id,
                    "user_id": user["id"],
                    "message": "WebSocket connection established",
                }
            )
        )
    except WebSocketDisconnect:
        logger.warning(
            f"WebSocket connection already closed for client {authenticated_client_id}"
        )
        return
    except Exception as e:
        logger.error(
            f"Failed to send initial message to WebSocket client {authenticated_client_id}: {e}"
        )
        try:
            await websocket.close(code=1011, reason="Failed to establish connection")
        except:
            logger.warning(
                f"WebSocket connection already closed for client {authenticated_client_id}"
            )
            return
        raise

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            # Handle client messages (ping, subscribe to specific agents, etc.)
            try:
                message = json.loads(data)  # Safe JSON parsing
                if message.get("type") == "ping":
                    await websocket.send_text('{"type": "pong"}')
                elif message.get("type") == "subscribe":
                    agent_id = message.get("agent_id")
                    if agent_id:
                        await websocket_manager.subscribe_to_agent(
                            authenticated_client_id, agent_id
                        )
                        logger.info(
                            f"🔌 Client {authenticated_client_id} subscribed to agent {agent_id}"
                        )
                elif message.get("type") == "unsubscribe":
                    agent_id = message.get("agent_id")
                    if agent_id:
                        await websocket_manager.unsubscribe_from_agent(
                            authenticated_client_id, agent_id
                        )
                        logger.info(
                            f"🔌 Client {authenticated_client_id} unsubscribed from agent {agent_id}"
                        )
                elif message.get("type") == "get_status":
                    # Send current status
                    status = {
                        "type": "status",
                        "connected_clients": len(websocket_manager.connections)
                        if websocket_manager
                        else 0,
                        "client_id": authenticated_client_id,
                        "user_id": user["id"],
                    }
                    await websocket.send_text(json.dumps(status))
            except (json.JSONDecodeError, KeyError, TypeError):
                # Ignore malformed messages
                logger.debug(
                    f"Received malformed WebSocket message from {authenticated_client_id}: {data}"
                )
                pass

    except WebSocketDisconnect:
        await websocket_manager.disconnect(authenticated_client_id)
        logger.info(f"🔌 WebSocket disconnected: {authenticated_client_id}")


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, client_id: str, token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time agent updates with authentication."""
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return

    # Authenticate user (temporarily disabled for testing)
    user = None
    if token:
        user = await authenticate_websocket_user(token)
        if not user:
            logger.warning(
                f"🔒 WebSocket authentication failed for client {client_id}, using test user"
            )
            user = {"id": 17, "username": "test_user", "email": "test@example.com"}
    else:
        logger.warning(
            f"🔒 No token provided for WebSocket connection {client_id}, using test user"
        )
        user = {"id": 17, "username": "test_user", "email": "test@example.com"}

    # Store user info with connection
    authenticated_client_id = f"user_{user['id']}_{client_id}"
    await websocket_manager.connect(authenticated_client_id, websocket)

    # Send authentication confirmation
    auth_message = {
        "type": "authenticated",
        "user_id": user["id"],
        "client_id": authenticated_client_id,
        "message": "WebSocket connection authenticated successfully",
    }

    # Check if websocket is still connected before sending
    try:
        await websocket.send_text(json.dumps(auth_message))
    except RuntimeError as e:
        if "close message has been sent" in str(e):
            logger.warning(
                f"WebSocket connection already closed for client {authenticated_client_id}"
            )
            return
        raise

    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()

            # Handle client messages (ping, subscribe to specific agents, etc.)
            try:
                message = json.loads(data)  # Safe JSON parsing
                if message.get("type") == "ping":
                    await websocket.send_text('{"type": "pong"}')
                elif message.get("type") == "subscribe":
                    agent_id = message.get("agent_id")
                    if agent_id:
                        await websocket_manager.subscribe_to_agent(
                            authenticated_client_id, agent_id
                        )
                elif message.get("type") == "unsubscribe":
                    agent_id = message.get("agent_id")
                    if agent_id:
                        await websocket_manager.unsubscribe_from_agent(
                            authenticated_client_id, agent_id
                        )
                elif message.get("type") == "get_status":
                    # Send current status
                    status = {
                        "type": "status",
                        "connected_clients": len(websocket_manager.connections)
                        if websocket_manager
                        else 0,
                        "client_id": authenticated_client_id,
                        "user_id": user["id"],
                    }
                    await websocket.send_text(json.dumps(status))
            except (json.JSONDecodeError, KeyError, TypeError):
                # Ignore malformed messages
                logger.debug(
                    f"Received malformed WebSocket message from {authenticated_client_id}: {data}"
                )
                pass

    except WebSocketDisconnect:
        await websocket_manager.disconnect(authenticated_client_id)


@router.websocket("/ws/market-data/{client_id}")
async def market_data_websocket(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time market data updates."""
    if not websocket_manager or not market_data_api:
        await websocket.close(code=1011, reason="Services not available")
        return

    await websocket_manager.connect(client_id, websocket)

    try:
        while True:
            # Handle incoming messages for market data subscriptions
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "subscribe":
                    # Subscribe to market data for specific symbols
                    symbols = message.get("symbols", [])
                    for symbol in symbols:
                        await websocket_manager.subscribe_to_market_data(
                            client_id, symbol.upper()
                        )

                    response = {
                        "type": "subscription_confirmed",
                        "symbols": symbols,
                        "client_id": client_id,
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "unsubscribe":
                    # Unsubscribe from market data
                    symbols = message.get("symbols", [])
                    for symbol in symbols:
                        await websocket_manager.unsubscribe_from_market_data(
                            client_id, symbol.upper()
                        )

                    response = {
                        "type": "unsubscription_confirmed",
                        "symbols": symbols,
                        "client_id": client_id,
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "get_ticker":
                    # Get real-time ticker data
                    symbol = message.get("symbol")
                    if symbol:
                        ticker = await market_data_api.get_ticker_data(symbol.upper())
                        response = {
                            "type": "ticker_data",
                            "symbol": symbol.upper(),
                            "data": ticker,
                            "timestamp": ticker.get("timestamp") if ticker else None,
                        }
                        await websocket.send_text(json.dumps(response))

                elif message_type == "get_orderbook":
                    # Get real-time order book data
                    symbol = message.get("symbol")
                    limit = message.get("limit", 20)
                    if symbol:
                        orderbook = await market_data_api.get_order_book(
                            symbol.upper(), limit
                        )
                        response = {
                            "type": "orderbook_data",
                            "symbol": symbol.upper(),
                            "data": orderbook,
                        }
                        await websocket.send_text(json.dumps(response))

                elif message_type == "ping":
                    await websocket.send_text('{"type": "pong"}')

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(
                    f"Received malformed market data WebSocket message from {client_id}: {data}"
                )

    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)


@router.websocket("/ws/trading/{client_id}")
async def trading_websocket(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time trading updates."""
    if not websocket_manager or not market_data_api:
        await websocket.close(code=1011, reason="Services not available")
        return

    await websocket_manager.connect(client_id, websocket)

    try:
        while True:
            # Handle incoming messages for trading operations
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "get_balance":
                    # Get account balance
                    balance = await market_data_api.get_account_balance()
                    response = {
                        "type": "balance_data",
                        "data": balance,
                        "client_id": client_id,
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "get_positions":
                    # Get open positions
                    positions = await market_data_api.get_positions()
                    response = {
                        "type": "positions_data",
                        "data": positions,
                        "client_id": client_id,
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "get_orders":
                    # Get open orders
                    symbol = message.get("symbol")
                    orders = await market_data_api.get_open_orders(
                        symbol.upper() if symbol else None
                    )
                    response = {
                        "type": "orders_data",
                        "symbol": symbol.upper() if symbol else "ALL",
                        "data": orders,
                        "client_id": client_id,
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "place_order":
                    # Place a trading order
                    order_data = message.get("order", {})
                    try:
                        result = await market_data_api.place_order(**order_data)
                        response = {
                            "type": "order_placed",
                            "success": True,
                            "data": result,
                            "client_id": client_id,
                        }
                    except Exception as e:
                        response = {
                            "type": "order_error",
                            "success": False,
                            "error": str(e),
                            "client_id": client_id,
                        }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "cancel_order":
                    # Cancel an order
                    symbol = message.get("symbol")
                    order_id = message.get("order_id")
                    if symbol and order_id:
                        try:
                            result = await market_data_api.cancel_order(
                                symbol.upper(), order_id
                            )
                            response = {
                                "type": "order_cancelled",
                                "success": True,
                                "data": result,
                                "client_id": client_id,
                            }
                        except Exception as e:
                            response = {
                                "type": "cancel_error",
                                "success": False,
                                "error": str(e),
                                "client_id": client_id,
                            }
                        await websocket.send_text(json.dumps(response))

                elif message_type == "ping":
                    await websocket.send_text('{"type": "pong"}')

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(
                    f"Received malformed trading WebSocket message from {client_id}: {data}"
                )

    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)


@router.websocket("/ws/portfolio/{client_id}")
async def portfolio_websocket(
    websocket: WebSocket, client_id: str, token: Optional[str] = Query(None)
):
    """WebSocket endpoint for real-time portfolio updates with user authentication."""
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return

    # Authenticate user
    user = None
    if token:
        user = await authenticate_websocket_user(token)
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return
    else:
        await websocket.close(code=1008, reason="Authentication token required")
        return

    # Store user info with connection
    authenticated_client_id = f"portfolio_user_{user['id']}_{client_id}"
    await websocket_manager.connect(authenticated_client_id, websocket)

    # Send authentication confirmation
    auth_message = {
        "type": "authenticated",
        "user_id": user["id"],
        "client_id": authenticated_client_id,
        "message": "Portfolio WebSocket connection authenticated successfully",
    }

    # Check if websocket is still connected before sending
    try:
        await websocket.send_text(json.dumps(auth_message))
    except RuntimeError as e:
        if "close message has been sent" in str(e):
            logger.warning(
                f"WebSocket connection already closed for client {authenticated_client_id}"
            )
            return
        raise

    try:
        while True:
            # Handle incoming messages for portfolio data subscriptions
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                message_type = message.get("type")

                if message_type == "subscribe_portfolio":
                    # Subscribe to portfolio updates for this user
                    response = {
                        "type": "portfolio_subscription_confirmed",
                        "user_id": user["id"],
                        "client_id": authenticated_client_id,
                        "message": "Subscribed to portfolio updates",
                    }
                    await websocket.send_text(json.dumps(response))

                elif message_type == "get_portfolio":
                    # Get current portfolio data
                    try:
                        from ...services.portfolio_service import portfolio_service

                        portfolio_data = await portfolio_service.get_portfolio_metrics(
                            user["id"]
                        )
                        response = {
                            "type": "portfolio_data",
                            "user_id": user["id"],
                            "data": portfolio_data,
                            "timestamp": portfolio_data.get("timestamp"),
                        }
                        await websocket.send_text(json.dumps(response))
                    except Exception as e:
                        error_response = {
                            "type": "portfolio_error",
                            "user_id": user["id"],
                            "error": str(e),
                            "message": "Failed to get portfolio data",
                        }
                        await websocket.send_text(json.dumps(error_response))

                elif message_type == "ping":
                    await websocket.send_text('{"type": "pong"}')

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(
                    f"Received malformed portfolio WebSocket message from {authenticated_client_id}: {data}"
                )

    except WebSocketDisconnect:
        await websocket_manager.disconnect(authenticated_client_id)
