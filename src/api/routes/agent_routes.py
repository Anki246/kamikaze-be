"""
Agent Management API Routes for FluxTrader
Provides REST API endpoints for trading agent management
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
import logging
from .auth_routes import get_current_user

# Note: Model imports temporarily removed to avoid import issues
# from ..models.agent_models import (
#     AgentCreateRequest,
#     AgentResponse,
#     AgentStatusResponse,
#     AgentConfigResponse,
#     TradingMetricsResponse
# )

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/agents", tags=["Trading Agents"])

# Global agent manager (will be injected)
agent_manager = None
websocket_manager = None

def set_managers(agent_mgr, ws_mgr):
    """Set the global managers."""
    global agent_manager, websocket_manager
    agent_manager = agent_mgr
    websocket_manager = ws_mgr

@router.get("/")
async def list_agents():
    """List all available trading agents."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    agents = await agent_manager.list_agents()
    return {
        "status": "success",
        "agents": agents,
        "count": len(agents) if agents else 0
    }

@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get specific agent details."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    agent = await agent_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "status": "success",
        "agent": agent
    }

@router.post("/{agent_id}/start")
async def start_agent(agent_id: str, current_user: Dict = Depends(get_current_user)):
    """Start a trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        # Get user ID from authenticated user context
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication context")

        logger.info(f"🚀 Starting agent {agent_id} for user {user_id} (authenticated user: {current_user.get('email', 'unknown')})")

        result = await agent_manager.start_agent(agent_id, user_id)

        # Notify WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_agent_update(agent_id, "started")

        return {
            "status": "success",
            "message": f"Agent {agent_id} started successfully",
            "agent_id": agent_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to start agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/stop")
async def stop_agent(agent_id: str, current_user: Dict = Depends(get_current_user)):
    """Stop a trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        # Get user ID from authenticated user context
        user_id = current_user.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID not found in authentication context")

        logger.info(f"🛑 Stopping agent {agent_id} for user {user_id} (authenticated user: {current_user.get('email', 'unknown')})")

        result = await agent_manager.stop_agent(agent_id)

        # Notify WebSocket clients
        if websocket_manager:
            await websocket_manager.broadcast_agent_update(agent_id, "stopped")

        return {
            "status": "success",
            "message": f"Agent {agent_id} stopped successfully",
            "agent_id": agent_id,
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to stop agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str, current_user: Dict = Depends(get_current_user)):
    """Get agent status and metrics."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    # Get user ID from authenticated user context
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in authentication context")

    status = await agent_manager.get_agent_status(agent_id)
    if not status:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "status": "success",
        "agent_id": agent_id,
        "data": status
    }

@router.get("/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str, current_user: Dict = Depends(get_current_user)):
    """Get agent trading metrics."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    # Get user ID from authenticated user context
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in authentication context")

    metrics = await agent_manager.get_agent_metrics(agent_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Agent metrics not found")

    return {
        "status": "success",
        "agent_id": agent_id,
        "metrics": metrics
    }

@router.get("/{agent_id}/config")
async def get_agent_config(agent_id: str, current_user: Dict = Depends(get_current_user)):
    """Get agent configuration."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    # Get user ID from authenticated user context
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found in authentication context")

    config = await agent_manager.get_agent_config(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail="Agent configuration not found")

    return {
        "status": "success",
        "agent_id": agent_id,
        "config": config
    }

@router.put("/{agent_id}/config")
async def update_agent_config(agent_id: str, config: Dict):
    """Update agent configuration."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        result = await agent_manager.update_agent_config(agent_id, config)
        return {
            "status": "success",
            "message": f"Agent {agent_id} configuration updated",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id} config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create")
async def create_agent(agent_request: Dict, current_user: Dict[str, Any] = Depends(get_current_user)):
    """Create a new trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        # Add user_id to the agent request
        agent_request["user_id"] = current_user["id"]
        agent = await agent_manager.create_agent(agent_request)
        return {
            "status": "success",
            "message": f"Agent created successfully",
            "agent": agent
        }
    except Exception as e:
        logger.error(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete a trading agent."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        result = await agent_manager.delete_agent(agent_id)
        return {
            "status": "success",
            "message": f"Agent {agent_id} deleted successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/types/available")
async def get_available_agent_types():
    """Get available agent types and their configurations."""
    if not agent_manager:
        raise HTTPException(status_code=503, detail="Agent manager not initialized")

    try:
        types = await agent_manager.get_available_agent_types()
        return {
            "status": "success",
            "agent_types": types
        }
    except Exception as e:
        logger.error(f"Failed to get agent types: {e}")
        raise HTTPException(status_code=500, detail=str(e))
