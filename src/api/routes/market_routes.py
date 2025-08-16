"""
Market Data API Routes for FluxTrader
Provides REST API endpoints for market data and trading operations
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/market", tags=["Market Data"])

# Global market data API (will be injected)
market_data_api = None


def set_market_data_api(market_api):
    """Set the global market data API."""
    global market_data_api
    market_data_api = market_api


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str):
    """Get 24h ticker data for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        ticker_data = await market_data_api.get_ticker_data(symbol.upper())
        return {"status": "success", "symbol": symbol.upper(), "data": ticker_data}
    except Exception as e:
        logger.error(f"Failed to get ticker for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get ticker data: {str(e)}"
        )


@router.get("/data")
async def get_market_data(
    symbols: str = Query(..., description="Comma-separated list of symbols")
):
    """Get market data for multiple symbols (comma-separated)."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        market_data = await market_data_api.get_market_data(symbol_list)
        return {"status": "success", "symbols": symbol_list, "data": market_data}
    except Exception as e:
        logger.error(f"Failed to get market data for {symbols}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get market data: {str(e)}"
        )


@router.get("/stats")
async def get_market_stats(
    symbols: str = Query(..., description="Comma-separated list of symbols")
):
    """Get market statistics for multiple symbols."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        stats = await market_data_api.get_market_stats(symbol_list)
        return {"status": "success", "symbols": symbol_list, "data": stats}
    except Exception as e:
        logger.error(f"Failed to get market stats for {symbols}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get market stats: {str(e)}"
        )


@router.get("/indicators/{symbol}")
async def get_technical_indicators(
    symbol: str,
    timeframe: str = Query(default="1h", description="Timeframe for indicators"),
    indicators: str = Query(
        default="RSI,MACD,BB,SMA,EMA", description="Comma-separated list of indicators"
    ),
):
    """Get technical indicators for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        indicator_list = [i.strip() for i in indicators.split(",")]
        indicators_data = await market_data_api.get_technical_indicators(
            symbol.upper(), timeframe, indicator_list
        )
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "timeframe": timeframe,
            "indicators": indicators_data,
        }
    except Exception as e:
        logger.error(f"Failed to get indicators for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get technical indicators: {str(e)}"
        )


@router.get("/symbols")
async def get_available_symbols():
    """Get list of available trading symbols."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbols = await market_data_api.get_available_symbols()
        return {"status": "success", "symbols": symbols, "count": len(symbols)}
    except Exception as e:
        logger.error(f"Failed to get available symbols: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get symbols: {str(e)}")


@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    interval: str = Query(default="1h", description="Kline interval"),
    limit: int = Query(default=100, description="Number of klines to return"),
):
    """Get kline/candlestick data for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        klines = await market_data_api.get_klines(symbol.upper(), interval, limit)
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "interval": interval,
            "klines": klines,
            "count": len(klines),
        }
    except Exception as e:
        logger.error(f"Failed to get klines for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get klines: {str(e)}")


@router.get("/orderbook/{symbol}")
async def get_order_book(
    symbol: str,
    limit: int = Query(default=100, description="Number of orders to return"),
):
    """Get order book data for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        orderbook = await market_data_api.get_order_book(symbol.upper(), limit)
        return {"status": "success", "symbol": symbol.upper(), "orderbook": orderbook}
    except Exception as e:
        logger.error(f"Failed to get order book for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get order book: {str(e)}"
        )


@router.get("/trades/{symbol}")
async def get_recent_trades(
    symbol: str,
    limit: int = Query(default=100, description="Number of trades to return"),
):
    """Get recent trades for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        trades = await market_data_api.get_recent_trades(symbol.upper(), limit)
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "trades": trades,
            "count": len(trades),
        }
    except Exception as e:
        logger.error(f"Failed to get recent trades for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")


@router.get("/analysis/{symbol}")
async def get_market_analysis(symbol: str):
    """Get comprehensive market analysis for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        analysis = await market_data_api.get_market_analysis(symbol.upper())
        return {"status": "success", "symbol": symbol.upper(), "analysis": analysis}
    except Exception as e:
        logger.error(f"Failed to get market analysis for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get market analysis: {str(e)}"
        )


@router.get("/sentiment/{symbol}")
async def get_market_sentiment(symbol: str):
    """Get market sentiment analysis for a symbol."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        sentiment = await market_data_api.get_market_sentiment(symbol.upper())
        return {"status": "success", "symbol": symbol.upper(), "sentiment": sentiment}
    except Exception as e:
        logger.error(f"Failed to get market sentiment for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get sentiment: {str(e)}"
        )


@router.get("/correlation")
async def get_market_correlation(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    timeframe: str = Query(
        default="1h", description="Timeframe for correlation analysis"
    ),
):
    """Get correlation analysis between multiple symbols."""
    if not market_data_api:
        raise HTTPException(status_code=503, detail="Market data service not available")

    try:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
        correlation = await market_data_api.get_market_correlation(
            symbol_list, timeframe
        )
        return {
            "status": "success",
            "symbols": symbol_list,
            "timeframe": timeframe,
            "correlation": correlation,
        }
    except Exception as e:
        logger.error(f"Failed to get correlation for {symbols}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get correlation: {str(e)}"
        )
