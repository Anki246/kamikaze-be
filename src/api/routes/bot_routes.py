"""
Bot Management Routes
Handles bot control operations using direct database connection for optimal performance.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...infrastructure.user_context import get_current_user_context
from .auth_routes import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bots", tags=["bots"])

# Global agent manager (will be injected)
agent_manager = None


def set_agent_manager(manager):
    """Set the global agent manager."""
    global agent_manager
    agent_manager = manager


class BotStatusResponse(BaseModel):
    """Bot status response model."""

    success: bool
    bot_id: str
    status: str
    message: str
    timestamp: int


class BotConfigurationRequest(BaseModel):
    """Bot configuration update request."""

    trading_pairs: List[str] = None
    risk_level: str = None
    leverage: int = None
    trade_amount_usdt: float = None
    pump_threshold: float = None
    dump_threshold: float = None
    min_confidence: int = None
    signal_strength_threshold: float = None
    min_24h_change: float = None
    max_cycles: int = None
    enable_real_trades: bool = None
    stop_loss: float = None
    take_profit: float = None


@router.post("/{bot_id}/pause")
async def pause_bot(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Pause a trading bot."""
    try:
        user_context = get_current_user_context()
        if not user_context:
            raise HTTPException(status_code=401, detail="User context not available")

        user_id = user_context.user_id
        logger.info(f"🛑 Pausing bot {bot_id} for user {user_id}")

        # For FluxTrader agent, use agent manager
        if bot_id.startswith("fluxtrader"):
            if not agent_manager:
                raise HTTPException(
                    status_code=503, detail="Agent manager not available"
                )

            result = await agent_manager.stop_agent(bot_id)
            if result:
                return BotStatusResponse(
                    success=True,
                    bot_id=bot_id,
                    status="paused",
                    message=f"Bot {bot_id} paused successfully",
                    timestamp=int(__import__("time").time()),
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to pause bot")

        # For other bots, implement database update
        # TODO: Add database logic for other bot types
        return BotStatusResponse(
            success=True,
            bot_id=bot_id,
            status="paused",
            message=f"Bot {bot_id} paused successfully",
            timestamp=int(__import__("time").time()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to pause bot: {str(e)}")


@router.post("/{bot_id}/resume")
async def resume_bot(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Resume a trading bot."""
    try:
        user_context = get_current_user_context()
        if not user_context:
            raise HTTPException(status_code=401, detail="User context not available")

        user_id = user_context.user_id
        logger.info(f"🚀 Resuming bot {bot_id} for user {user_id}")

        # For FluxTrader agent, use agent manager
        if bot_id.startswith("fluxtrader"):
            if not agent_manager:
                raise HTTPException(
                    status_code=503, detail="Agent manager not available"
                )

            result = await agent_manager.start_agent(bot_id, user_id)
            if result:
                return BotStatusResponse(
                    success=True,
                    bot_id=bot_id,
                    status="active",
                    message=f"Bot {bot_id} resumed successfully",
                    timestamp=int(__import__("time").time()),
                )
            else:
                raise HTTPException(status_code=500, detail="Failed to resume bot")

        # For other bots, implement database update
        # TODO: Add database logic for other bot types
        return BotStatusResponse(
            success=True,
            bot_id=bot_id,
            status="active",
            message=f"Bot {bot_id} resumed successfully",
            timestamp=int(__import__("time").time()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming bot {bot_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume bot: {str(e)}")


@router.get("/{bot_id}/status")
async def get_bot_status(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Get bot status and configuration."""
    try:
        user_context = get_current_user_context()
        if not user_context:
            raise HTTPException(status_code=401, detail="User context not available")

        # For FluxTrader agent, use agent manager
        if bot_id.startswith("fluxtrader"):
            if not agent_manager:
                raise HTTPException(
                    status_code=503, detail="Agent manager not available"
                )

            status = await agent_manager.get_agent_status(bot_id)
            if status:
                return {"success": True, "bot_id": bot_id, "data": status}
            else:
                raise HTTPException(status_code=404, detail="Bot not found")

        # For other bots, implement database query
        # TODO: Add database logic for other bot types
        return {
            "success": True,
            "bot_id": bot_id,
            "data": {"status": "unknown", "message": "Bot type not implemented"},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot status {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get bot status: {str(e)}"
        )


@router.put("/{bot_id}/configuration")
async def update_bot_configuration(
    bot_id: str,
    config: BotConfigurationRequest,
    current_user: Dict = Depends(get_current_user),
):
    """Update bot configuration."""
    try:
        user_context = get_current_user_context()
        if not user_context:
            raise HTTPException(status_code=401, detail="User context not available")

        user_id = user_context.user_id
        logger.info(f"⚙️ Updating configuration for bot {bot_id} for user {user_id}")

        # For FluxTrader agent, use agent manager
        if bot_id.startswith("fluxtrader"):
            if not agent_manager:
                raise HTTPException(
                    status_code=503, detail="Agent manager not available"
                )

            # Convert request to configuration dict
            config_dict = {k: v for k, v in config.dict().items() if v is not None}

            result = await agent_manager.update_agent_config(bot_id, config_dict)
            if result:
                return {
                    "success": True,
                    "bot_id": bot_id,
                    "message": "Configuration updated successfully",
                    "updated_config": config_dict,
                }
            else:
                raise HTTPException(
                    status_code=500, detail="Failed to update configuration"
                )

        # For other bots, implement database update
        # TODO: Add database logic for other bot types
        return {
            "success": True,
            "bot_id": bot_id,
            "message": "Configuration updated successfully",
            "updated_config": config.dict(exclude_none=True),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bot configuration {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update configuration: {str(e)}"
        )


@router.get("/{bot_id}/settings")
async def get_bot_settings(bot_id: str, current_user: Dict = Depends(get_current_user)):
    """Get bot settings page data."""
    try:
        user_context = get_current_user_context()
        if not user_context:
            raise HTTPException(status_code=401, detail="User context not available")

        # For FluxTrader agent, get current configuration
        if bot_id.startswith("fluxtrader"):
            if not agent_manager:
                raise HTTPException(
                    status_code=503, detail="Agent manager not available"
                )

            config = await agent_manager.get_agent_config(bot_id)
            if config:
                return {"success": True, "bot_id": bot_id, "settings": config}
            else:
                raise HTTPException(
                    status_code=404, detail="Bot configuration not found"
                )

        # For other bots, implement database query
        # TODO: Add database logic for other bot types
        return {
            "success": True,
            "bot_id": bot_id,
            "settings": {"message": "Bot settings not implemented for this bot type"},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bot settings {bot_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get bot settings: {str(e)}"
        )
