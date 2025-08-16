"""
Market Data Models
Pydantic models for market data API responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MarketDataPoint(BaseModel):
    """Individual market data point for a symbol."""

    symbol: str
    price: float
    change24h: float
    changePercent24h: float
    volume24h: float
    high24h: float
    low24h: float
    timestamp: int

    # Add aliases for API compatibility
    change_24h: Optional[float] = None
    change_percent_24h: Optional[float] = None
    volume_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

    class Config:
        allow_population_by_field_name = True

    def __init__(self, **data):
        # Handle field mapping
        if "change_24h" in data and "change24h" not in data:
            data["change24h"] = data["change_24h"]
        if "change_percent_24h" in data and "changePercent24h" not in data:
            data["changePercent24h"] = data["change_percent_24h"]
        if "volume_24h" in data and "volume24h" not in data:
            data["volume24h"] = data["volume_24h"]
        if "high_24h" in data and "high24h" not in data:
            data["high24h"] = data["high_24h"]
        if "low_24h" in data and "low24h" not in data:
            data["low24h"] = data["low_24h"]
        super().__init__(**data)


class MarketDataResponse(BaseModel):
    """Response model for market data API."""

    success: bool
    data: Dict[str, MarketDataPoint]
    timestamp: int
    source: str = "binance"


class TickerResponse(BaseModel):
    """Response model for single ticker data."""

    success: bool
    symbol: str
    price: float
    change_24h: float
    change_percent_24h: float
    high_24h: float
    low_24h: float
    volume_24h: float
    quote_volume_24h: Optional[float] = 0
    open_price: Optional[float] = 0
    timestamp: int
    error: Optional[str] = None


class MarketStatsResponse(BaseModel):
    """Response model for market statistics."""

    success: bool
    total_volume: float
    avg_change: float
    gainers_count: int
    losers_count: int
    total_assets: int
    top_gainer: Optional[MarketDataPoint] = None
    top_loser: Optional[MarketDataPoint] = None
    timestamp: int


class TechnicalIndicator(BaseModel):
    """Technical indicator data."""

    name: str
    value: Optional[float] = None
    values: Optional[Dict[str, float]] = None
    signal: Optional[str] = None


class TechnicalIndicatorsResponse(BaseModel):
    """Response model for technical indicators."""

    success: bool
    symbol: str
    timeframe: str
    indicators: Dict[str, Any]
    timestamp: int


class PriceHistoryPoint(BaseModel):
    """Single price history data point."""

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class PriceHistoryResponse(BaseModel):
    """Response model for price history data."""

    success: bool
    symbol: str
    timeframe: str
    data: List[PriceHistoryPoint]
    timestamp: int


class OrderBookEntry(BaseModel):
    """Order book entry (bid/ask)."""

    price: float
    quantity: float


class OrderBookResponse(BaseModel):
    """Response model for order book data."""

    success: bool
    symbol: str
    bids: List[OrderBookEntry]
    asks: List[OrderBookEntry]
    timestamp: int


class TradeData(BaseModel):
    """Recent trade data."""

    id: int
    price: float
    quantity: float
    timestamp: int
    is_buyer_maker: bool


class RecentTradesResponse(BaseModel):
    """Response model for recent trades."""

    success: bool
    symbol: str
    trades: List[TradeData]
    timestamp: int


class MarketSentiment(BaseModel):
    """Market sentiment analysis."""

    symbol: str
    sentiment_score: float  # -1 to 1
    sentiment_label: str  # bearish, neutral, bullish
    confidence: float  # 0 to 1
    factors: Dict[str, Any]


class MarketSentimentResponse(BaseModel):
    """Response model for market sentiment."""

    success: bool
    symbol: str
    sentiment: MarketSentiment
    timestamp: int


class ExchangeInfo(BaseModel):
    """Exchange information."""

    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    base_precision: int
    quote_precision: int
    min_qty: float
    max_qty: float
    step_size: float
    min_notional: float


class ExchangeInfoResponse(BaseModel):
    """Response model for exchange information."""

    success: bool
    symbols: List[ExchangeInfo]
    timestamp: int


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str
    data: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = None
    symbols: Optional[List[str]] = None
    message: Optional[str] = None
    timestamp: Optional[int] = None


class SubscriptionRequest(BaseModel):
    """WebSocket subscription request."""

    type: str = "subscribe_market_data"
    symbols: List[str]
    client_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """WebSocket subscription response."""

    type: str = "subscription_confirmed"
    symbols: List[str]
    message: str
    timestamp: int


class MarketDataUpdate(BaseModel):
    """Real-time market data update."""

    type: str = "market_data_update"
    data: MarketDataResponse
    timestamp: int


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    error_code: Optional[str] = None
    timestamp: int


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: str
    version: str
    services: Dict[str, bool]
