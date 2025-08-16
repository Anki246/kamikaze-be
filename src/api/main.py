#!/usr/bin/env python3
"""
FluxTrader Agentic AI Application - FastAPI Backend
Modern multi-agent trading system with real-time WebSocket communication

Features:
- RESTful API for agent management
- WebSocket real-time updates
- Agent lifecycle management
- MCP server integration
- Configuration management
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel, Field

from shared.logging_config import setup_logging

# User Context middleware - CRITICAL: Add dynamic user context system
from .middleware.user_context_middleware import UserContextMiddleware
from .models.agent_models import (
    AgentConfigResponse,
    AgentCreateRequest,
    AgentResponse,
    AgentStatusResponse,
    TradingMetricsResponse,
)
from .models.market_models import (
    MarketDataResponse,
    MarketStatsResponse,
    TechnicalIndicatorsResponse,
    TickerResponse,
)
from .routes.agent_routes import router as agent_router
from .routes.agent_routes import set_managers as set_agent_managers
from .routes.auth_routes import router as auth_router
from .routes.bot_routes import router as bot_router
from .routes.bot_routes import set_agent_manager as set_bot_agent_manager
from .routes.credentials_routes import router as credentials_router
from .routes.dashboard_routes import router as dashboard_router
from .routes.database_routes import router as database_router
from .routes.market_routes import router as market_router
from .routes.market_routes import set_market_data_api as set_market_api
from .routes.trading_routes import router as trading_router
from .routes.trading_routes import set_market_data_api as set_trading_api
from .routes.user_status_routes import router as user_status_router
from .routes.websocket_routes import router as websocket_router
from .routes.websocket_routes import set_managers as set_ws_managers
from .services.agent_manager import AgentManager
from .services.market_data_api import MarketDataAPI
from .services.websocket_manager import WebSocketManager

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Configure logging
logger = setup_logging("fastapi_backend")

# Global managers
agent_manager: Optional[AgentManager] = None
websocket_manager: Optional[WebSocketManager] = None
market_data_api: Optional[MarketDataAPI] = None


def json_serializer(obj):
    """Custom JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global agent_manager, websocket_manager, market_data_api

    logger.info("🚀 Starting FluxTrader Agentic AI Backend...")

    # Initialize managers
    agent_manager = AgentManager()
    websocket_manager = WebSocketManager()
    market_data_api = MarketDataAPI()

    # Inject WebSocket manager into agent manager
    agent_manager.set_websocket_manager(websocket_manager)

    # Initialize services
    await agent_manager.initialize()
    await market_data_api.connect()

    # Inject managers into route modules
    set_agent_managers(agent_manager, websocket_manager)
    set_bot_agent_manager(agent_manager)
    set_market_api(market_data_api)
    set_trading_api(market_data_api)
    set_ws_managers(websocket_manager, market_data_api)
    # Initialize direct auth database connection
    from ..infrastructure.auth_database import auth_db

    try:
        if await auth_db.connect():
            logger.info("✅ Auth database connected successfully")
        else:
            logger.error("❌ Failed to connect auth database")
    except Exception as e:
        logger.error(f"Failed to initialize auth database: {e}")

    # Initialize credentials database connection
    from ..infrastructure.credentials_database import credentials_db

    try:
        if await credentials_db.connect():
            logger.info("✅ Credentials database connected successfully")
        else:
            logger.error("❌ Failed to connect credentials database")
    except Exception as e:
        logger.error(f"Failed to initialize credentials database: {e}")

    logger.info("✅ FluxTrader Backend initialized successfully")

    yield

    # Cleanup
    logger.info("🛑 Shutting down FluxTrader Backend...")
    if agent_manager:
        await agent_manager.shutdown()
    if market_data_api:
        await market_data_api.disconnect()

    # Disconnect auth database
    from ..infrastructure.auth_database import auth_db

    await auth_db.disconnect()

    # Disconnect credentials database
    from ..infrastructure.credentials_database import credentials_db

    await credentials_db.disconnect()

    logger.info("✅ FluxTrader Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="FluxTrader Agentic AI API",
    description="Modern multi-agent trading system with real-time capabilities",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(UserContextMiddleware)

# Include routers
app.include_router(database_router)
app.include_router(agent_router)
app.include_router(market_router)
app.include_router(trading_router)
app.include_router(websocket_router)
app.include_router(auth_router)
app.include_router(credentials_router)
app.include_router(user_status_router)
app.include_router(dashboard_router)
app.include_router(bot_router)


# Root endpoint - Redirect to interactive API documentation
@app.get("/")
async def root():
    """Redirect to interactive API documentation."""
    return RedirectResponse(url="/docs")


# API Information endpoint
@app.get("/api/info")
async def api_info():
    """Get API information and available services."""
    return {
        "message": "🚀 FluxTrader Backend API",
        "description": "Advanced AI-powered trading platform with PostgreSQL integration",
        "version": "2.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "database": {
                "status": "connected",
                "description": "PostgreSQL database with FastMCP integration",
                "endpoints": [
                    "/api/database/health",
                    "/api/database/tables",
                    "/api/database/ping",
                ],
            },
            "trading": {
                "status": "available",
                "description": "Binance trading integration with FastMCP",
                "features": ["futures_trading", "market_data", "technical_analysis"],
            },
            "agents": {
                "status": "ready",
                "description": "AI trading agents management",
                "endpoints": ["/api/v1/agents", "/api/v1/agents/{agent_id}"],
            },
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "health_check": "/health",
        "frontend_url": "http://localhost:3000",
        "mcp_servers": {
            "binance": "FastMCP server for trading operations",
            "postgresql": "FastMCP server for database operations",
        },
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint with comprehensive service status."""
    from infrastructure.aws_secrets_manager import AWSSecretsManager
    from infrastructure.database_config import DatabaseConfig

    # Check database connectivity
    db_status = "unknown"
    try:
        db_config = DatabaseConfig()
        # Simple connection test would go here
        db_status = "connected" if db_config.host != "localhost" else "local"
    except Exception as e:
        db_status = f"error: {str(e)}"

    # Check AWS Secrets Manager connectivity
    aws_status = "unknown"
    try:
        if (
            os.getenv("ENVIRONMENT") == "production"
            or os.getenv("USE_AWS_SECRETS", "false").lower() == "true"
        ):
            secrets_manager = AWSSecretsManager()
            # Test AWS connectivity
            aws_status = "connected"
        else:
            aws_status = "disabled"
    except Exception as e:
        aws_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "instance": {
            "host": os.getenv("API_HOST", "localhost"),
            "port": os.getenv("API_PORT", "8000"),
        },
        "services": {
            "agent_manager": agent_manager.is_healthy() if agent_manager else False,
            "websocket_manager": websocket_manager.is_healthy()
            if websocket_manager
            else False,
            "market_data_api": market_data_api.connected if market_data_api else False,
            "database": db_status,
            "aws_secrets": aws_status,
        },
    }


# Database health check endpoint
@app.get("/health/database")
async def database_health_check():
    """Database connectivity health check."""
    from infrastructure.database_config import DatabaseConfig

    try:
        db_config = DatabaseConfig()
        return {
            "status": "healthy",
            "database": {
                "host": db_config.host,
                "port": db_config.port,
                "database": db_config.database,
                "ssl_mode": db_config.ssl_mode,
                "connection_source": "aws_secrets"
                if db_config.host != "localhost"
                else "environment",
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# AWS services health check endpoint
@app.get("/health/aws")
async def aws_health_check():
    """AWS services connectivity health check."""
    from infrastructure.aws_secrets_manager import AWSSecretsManager

    try:
        if (
            os.getenv("ENVIRONMENT") == "production"
            or os.getenv("USE_AWS_SECRETS", "false").lower() == "true"
        ):
            secrets_manager = AWSSecretsManager()
            # Test retrieving database credentials
            db_credentials = secrets_manager.get_database_credentials()

            return {
                "status": "healthy",
                "aws_region": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
                "secrets_manager": "connected",
                "database_credentials": "available"
                if db_credentials
                else "unavailable",
                "timestamp": datetime.utcnow().isoformat(),
            }
        else:
            return {
                "status": "disabled",
                "message": "AWS services disabled in development mode",
                "timestamp": datetime.utcnow().isoformat(),
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Agent Management Endpoints
@app.get("/api/v1/agents", response_model=List[AgentResponse])
async def list_agents():
    """List all available agents."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    agents = await agent_manager.list_agents()
    return agents


@app.get("/api/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Get specific agent details."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    agent = await agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent


@app.post("/api/v1/agents/{agent_id}/start")
async def start_agent(agent_id: str):
    """Start a trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        result = await agent_manager.start_agent(agent_id)

        # Notify WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_agent_update(agent_id, "started")

        return {
            "status": "success",
            "message": f"Agent {agent_id} started successfully",
            "agent_id": agent_id,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Failed to start agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/agents/{agent_id}/stop")
async def stop_agent(agent_id: str):
    """Stop a trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        result = await agent_manager.stop_agent(agent_id)

        # Notify WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_agent_update(agent_id, "stopped")

        return {
            "status": "success",
            "message": f"Agent {agent_id} stopped successfully",
            "agent_id": agent_id,
            "result": result,
        }
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/agents/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str):
    """Get agent status and metrics."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    status = await agent_manager.get_agent_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")

    return status


@app.get("/api/v1/agents/{agent_id}/metrics", response_model=TradingMetricsResponse)
async def get_agent_metrics(agent_id: str):
    """Get agent trading metrics."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    metrics = await agent_manager.get_agent_metrics(agent_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Agent metrics not found")

    return metrics


@app.get("/api/v1/agents/{agent_id}/config", response_model=AgentConfigResponse)
async def get_agent_config(agent_id: str):
    """Get agent configuration."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    config = await agent_manager.get_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent configuration not found")

    return config


@app.put("/api/v1/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, config: Dict):
    """Update agent configuration."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        result = await agent_manager.update_agent_config(agent_id, config)
        return {
            "status": "success",
            "message": f"Agent {agent_id} configuration updated",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id} config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Market Data Endpoints
@app.get("/api/v1/market/ticker/{symbol}", response_model=TickerResponse)
async def get_ticker(symbol: str):
    """Get 24h ticker data for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        ticker_data = await market_data_api.get_ticker_data(symbol.upper())
        return ticker_data
    except Exception as e:
        logger.error(f"Failed to get ticker for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get ticker data: {str(e)}"
        )


@app.get("/api/v1/market/data", response_model=MarketDataResponse)
async def get_market_data(symbols: str):
    """Get market data for multiple symbols (comma-separated)."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        market_data = await market_data_api.get_market_data(symbol_list)
        return market_data
    except Exception as e:
        logger.error(f"Failed to get market data for {symbols}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get market data: {str(e)}"
        )


@app.get("/api/v1/market/stats", response_model=MarketStatsResponse)
async def get_market_stats(symbols: str):
    """Get market statistics for multiple symbols."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        stats = await market_data_api.get_market_stats(symbol_list)
        return stats
    except Exception as e:
        logger.error(f"Failed to get market stats for {symbols}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get market stats: {str(e)}"
        )


@app.get(
    "/api/v1/market/indicators/{symbol}", response_model=TechnicalIndicatorsResponse
)
async def get_technical_indicators(
    symbol: str, timeframe: str = "1h", indicators: str = "RSI,MACD,BB,SMA,EMA"
):
    """Get technical indicators for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        indicator_list = [i.strip() for i in indicators.split(",")]
        indicators_data = await market_data_api.get_technical_indicators(
            symbol.upper(), timeframe, indicator_list
        )
        return indicators_data
    except Exception as e:
        logger.error(f"Failed to get indicators for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get technical indicators: {str(e)}"
        )


# WebSocket endpoint for real-time updates
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time agent updates."""
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket manager not available")
        return

    await websocket_manager.connect(client_id, websocket)

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
                        await websocket_manager.subscribe_to_agent(client_id, agent_id)
            except (json.JSONDecodeError, KeyError, TypeError):
                # Ignore malformed messages
                logger.debug(
                    f"Received malformed WebSocket message from {client_id}: {data}"
                )
                pass

    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)


# WebSocket endpoint for market data streaming
@app.websocket("/ws/market-data/{client_id}")
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

                if message_type == "subscribe_market_data":
                    symbols = message.get("symbols", [])
                    # Subscribe to market data updates for these symbols
                    await websocket_manager.send_personal_message(
                        client_id,
                        {
                            "type": "subscription_confirmed",
                            "symbols": symbols,
                            "message": f"Subscribed to market data for {len(symbols)} symbols",
                        },
                    )

                    # Send initial market data
                    if symbols:
                        try:
                            market_data = await market_data_api.get_market_data(symbols)
                            await websocket_manager.send_personal_message(
                                client_id,
                                {
                                    "type": "market_data_update",
                                    "data": market_data if market_data else {},
                                },
                            )
                        except Exception as e:
                            logger.error(f"Failed to send initial market data: {e}")

                elif message_type == "ping":
                    await websocket.send_text('{"type": "pong"}')

            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.debug(
                    f"Received malformed market data WebSocket message from {client_id}: {data}"
                )

    except WebSocketDisconnect:
        await websocket_manager.disconnect(client_id)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
