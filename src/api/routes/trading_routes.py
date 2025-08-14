"""
Trading API Routes for FluxTrader
Provides REST API endpoints for trading operations via Binance MCP server
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional, Any
import logging
from pydantic import BaseModel, Field
from .auth_routes import get_current_user

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/trading", tags=["Trading Operations"])

# Global market data API (will be injected)
market_data_api = None

def set_market_data_api(market_api):
    """Set the global market data API."""
    global market_data_api
    market_data_api = market_api

# Pydantic models for trading requests
class OrderRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol (e.g., BTCUSDT)")
    side: str = Field(..., description="Order side: BUY or SELL")
    type: str = Field(default="MARKET", description="Order type: MARKET, LIMIT, etc.")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (for LIMIT orders)")
    timeInForce: Optional[str] = Field(default="GTC", description="Time in force")
    stopPrice: Optional[float] = Field(None, description="Stop price for stop orders")

class LeverageRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")
    leverage: int = Field(..., description="Leverage value (1-125)")

class PositionRequest(BaseModel):
    symbol: str = Field(..., description="Trading symbol")

@router.get("/account/balance")
async def get_account_balance(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get account balance and positions for the authenticated user."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        user_id = current_user["id"]
        balance = await market_data_api.get_account_balance(user_id=user_id)
        return {
            "success": balance.get("success", False),
            "data": {
                "total_balance": balance.get("total_balance", 0.0),
                "available_balance": balance.get("available_balance", 0.0),
                "futures_balance": balance.get("futures_balance", 0.0)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get balance: {str(e)}")

@router.post("/orders/place")
async def place_order(order: OrderRequest):
    """Place a trading order."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        result = await market_data_api.place_order(
            symbol=order.symbol.upper(),
            side=order.side.upper(),
            order_type=order.type.upper(),
            quantity=order.quantity,
            price=order.price,
            time_in_force=order.timeInForce,
            stop_price=order.stopPrice
        )
        return {
            "status": "success",
            "message": "Order placed successfully",
            "order": result
        }
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")

@router.get("/orders/{symbol}")
async def get_open_orders(symbol: str):
    """Get open orders for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        orders = await market_data_api.get_open_orders(symbol.upper())
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "orders": orders,
            "count": len(orders)
        }
    except Exception as e:
        logger.error(f"Failed to get open orders for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get orders: {str(e)}")

@router.delete("/orders/{order_id}")
async def cancel_order(order_id: str, symbol: str = Query(..., description="Trading symbol")):
    """Cancel an open order."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        result = await market_data_api.cancel_order(symbol.upper(), order_id)
        return {
            "status": "success",
            "message": f"Order {order_id} cancelled successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to cancel order {order_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel order: {str(e)}")

@router.post("/leverage/set")
async def set_leverage(leverage_req: LeverageRequest):
    """Set leverage for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        result = await market_data_api.set_leverage(leverage_req.symbol.upper(), leverage_req.leverage)
        return {
            "status": "success",
            "message": f"Leverage set to {leverage_req.leverage}x for {leverage_req.symbol}",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to set leverage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set leverage: {str(e)}")

@router.get("/positions")
async def get_positions():
    """Get all open positions."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        positions = await market_data_api.get_positions()
        return {
            "status": "success",
            "positions": positions,
            "count": len(positions)
        }
    except Exception as e:
        logger.error(f"Failed to get positions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")

@router.get("/positions/{symbol}")
async def get_position(symbol: str):
    """Get position for a specific symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        position = await market_data_api.get_position(symbol.upper())
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "position": position
        }
    except Exception as e:
        logger.error(f"Failed to get position for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get position: {str(e)}")

@router.get("/history/orders")
async def get_order_history(
    symbol: Optional[str] = Query(None, description="Trading symbol (optional)"),
    limit: int = Query(default=100, description="Number of orders to return")
):
    """Get order history."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        history = await market_data_api.get_order_history(
            symbol=symbol.upper() if symbol else None,
            limit=limit
        )
        return {
            "status": "success",
            "symbol": symbol.upper() if symbol else "ALL",
            "orders": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to get order history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order history: {str(e)}")

@router.get("/history/trades")
async def get_trade_history(
    symbol: Optional[str] = Query(None, description="Trading symbol (optional)"),
    limit: int = Query(default=100, description="Number of trades to return")
):
    """Get trade history."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        history = await market_data_api.get_trade_history(
            symbol=symbol.upper() if symbol else None,
            limit=limit
        )
        return {
            "status": "success",
            "symbol": symbol.upper() if symbol else "ALL",
            "trades": history,
            "count": len(history)
        }
    except Exception as e:
        logger.error(f"Failed to get trade history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trade history: {str(e)}")

@router.get("/pnl")
async def get_pnl():
    """Get profit and loss summary."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        pnl = await market_data_api.get_pnl()
        return {
            "status": "success",
            "pnl": pnl
        }
    except Exception as e:
        logger.error(f"Failed to get PnL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get PnL: {str(e)}")

@router.get("/risk/assessment")
async def get_risk_assessment():
    """Get risk assessment for current positions."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        risk = await market_data_api.get_risk_assessment()
        return {
            "status": "success",
            "risk_assessment": risk
        }
    except Exception as e:
        logger.error(f"Failed to get risk assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get risk assessment: {str(e)}")

@router.get("/symbols/info")
async def get_symbol_info(symbol: str = Query(..., description="Trading symbol")):
    """Get detailed information about a trading symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Trading service not available")

    try:
        info = await market_data_api.get_symbol_info(symbol.upper())
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "info": info
        }
    except Exception as e:
        logger.error(f"Failed to get symbol info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get symbol info: {str(e)}")
