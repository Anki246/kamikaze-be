"""
Dashboard Models
Pydantic models for dashboard API responses
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssetBalance(BaseModel):
    """Asset balance information."""

    asset: str
    balance: float
    usd_value: float
    btc_value: float
    percentage: float
    price_change_24h: Optional[float] = None


class PortfolioMetrics(BaseModel):
    """Portfolio metrics and performance data."""

    total_value_usd: float
    total_value_btc: float
    daily_pnl: float
    daily_pnl_percent: float
    asset_allocation: List[AssetBalance]
    btc_price_usd: float
    timestamp: int


class TradingBotMetrics(BaseModel):
    """Trading bot performance metrics."""

    id: str
    name: str
    status: str  # active, paused, stopped, error
    strategy: str
    profit: float
    profit_percentage: float
    trades: int
    win_rate: float
    last_trade: Optional[str] = None
    risk_level: str  # low, medium, high


class RecentTrade(BaseModel):
    """Recent trade information."""

    id: str
    symbol: str
    side: str  # BUY, SELL
    quantity: float
    price: float
    total: float
    timestamp: int
    pnl: float


class TopAsset(BaseModel):
    """Top performing asset."""

    symbol: str
    name: str
    price: float
    change_percent: float


class RiskMetrics(BaseModel):
    """Portfolio risk metrics."""

    max_drawdown: float
    sharpe_ratio: float
    volatility: float
    beta: float
    var_95: float  # Value at Risk 95%


class AIInsight(BaseModel):
    """AI-generated trading insight."""

    id: str
    type: str  # opportunity, warning, info
    title: str
    description: str
    confidence: float
    timestamp: str


class DashboardOverview(BaseModel):
    """Complete dashboard overview response."""

    portfolio: PortfolioMetrics
    trading_bots: List[TradingBotMetrics]
    recent_trades: List[RecentTrade]
    top_assets: List[TopAsset]
    risk_metrics: RiskMetrics
    ai_insights: List[AIInsight]
    timestamp: int
    environment: str  # live, testnet


class QuickStats(BaseModel):
    """Quick stats for dashboard header."""

    daily_pnl: float
    active_bots: int
    total_bots: int
    win_rate: float
    trades_today: int


class DashboardQuickStatsResponse(BaseModel):
    """Quick stats response."""

    stats: QuickStats
    timestamp: int


class PortfolioPerformancePoint(BaseModel):
    """Portfolio performance data point."""

    timestamp: int
    value_usd: float
    value_btc: float
    pnl: float
    pnl_percent: float


class PortfolioPerformanceResponse(BaseModel):
    """Portfolio performance over time."""

    period: str
    data_points: List[PortfolioPerformancePoint]
    total_return: float
    total_return_percent: float
    timestamp: int


class HealthCheckResponse(BaseModel):
    """Dashboard health check response."""

    services: Dict[str, bool]
    timestamp: int
    message: str


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    error_code: Optional[str] = None
    timestamp: int
