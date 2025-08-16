"""
Pydantic models for agent API responses and requests
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent status enumeration."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


class StrategyType(str, Enum):
    """Trading strategy types."""

    PUMP_DUMP = "pump_dump"
    ARBITRAGE = "arbitrage"
    DCA = "dca"
    GRID = "grid"
    MARKET_MAKING = "market_making"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"


class RiskLevel(str, Enum):
    """Risk level enumeration."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AgentMetadata(BaseModel):
    """Agent metadata information."""

    name: str
    version: str
    strategy_type: StrategyType
    description: str
    author: str = "FluxTrader Team"
    supported_pairs: List[str] = Field(default_factory=list)
    min_balance_required: float = 0.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    time_frame: str = "1m"
    requires_api_keys: List[str] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)


class AgentPerformanceMetrics(BaseModel):
    """Agent performance metrics."""

    total_pnl: float = 0.0
    roi: float = 0.0
    win_rate: float = 0.0
    trades_executed: int = 0
    signals_found: int = 0
    current_balance: float = 0.0
    daily_profit: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade_profit: float = 0.0


class AgentConfiguration(BaseModel):
    """Agent configuration settings."""

    trading_pairs: List[str] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    max_position_size: float = 100.0
    stop_loss: float = 2.0
    take_profit: float = 4.0
    leverage: int = 20
    trade_amount_usdt: float = 4.0
    pump_threshold: float = 0.03
    dump_threshold: float = -0.03
    min_confidence: int = 35
    signal_strength_threshold: float = 0.4
    min_24h_change: float = 0.01
    max_cycles: int = 100
    enable_real_trades: bool = True
    additional_config: Dict[str, Any] = Field(default_factory=dict)


class AgentRuntimeData(BaseModel):
    """Agent runtime information."""

    uptime: Optional[int] = None
    last_activity: Optional[datetime] = None
    current_cycle: Optional[int] = None
    max_cycles: Optional[int] = None
    mcp_connected: bool = False
    binance_connected: bool = False
    groq_connected: bool = False


class AgentCreateRequest(BaseModel):
    """Request model for creating a new agent."""

    agent_type: StrategyType
    agent_id: Optional[str] = None
    configuration: Optional[AgentConfiguration] = None


class AgentResponse(BaseModel):
    """Complete agent information response."""

    id: str
    metadata: AgentMetadata
    status: AgentStatus
    is_active: bool
    configuration: AgentConfiguration
    performance: AgentPerformanceMetrics
    runtime: AgentRuntimeData
    created_at: datetime
    updated_at: datetime


class AgentStatusResponse(BaseModel):
    """Agent status response."""

    agent_id: str
    status: AgentStatus
    is_running: bool
    uptime_seconds: int
    current_cycle: int
    max_cycles: int
    last_activity: Optional[datetime]
    mcp_connected: bool
    binance_connected: bool
    groq_connected: bool
    error_message: Optional[str] = None


class TradingMetricsResponse(BaseModel):
    """Trading metrics response."""

    agent_id: str
    performance: AgentPerformanceMetrics
    balance: Dict[str, float]
    active_positions: List[Dict[str, Any]] = Field(default_factory=list)
    recent_trades: List[Dict[str, Any]] = Field(default_factory=list)
    recent_signals: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: datetime


class AgentConfigResponse(BaseModel):
    """Agent configuration response."""

    agent_id: str
    configuration: AgentConfiguration
    metadata: AgentMetadata
    last_updated: datetime


class AgentLogEntry(BaseModel):
    """Agent log entry."""

    timestamp: datetime
    level: str
    message: str
    agent_id: str
    component: Optional[str] = None


class AgentLogsResponse(BaseModel):
    """Agent logs response."""

    agent_id: str
    logs: List[AgentLogEntry]
    total_count: int
    page: int
    page_size: int


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str
    agent_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentUpdateMessage(WebSocketMessage):
    """Agent update WebSocket message."""

    type: str = "agent_update"
    agent_id: str
    status: AgentStatus
    metrics: Optional[AgentPerformanceMetrics] = None


class TradingSignalMessage(WebSocketMessage):
    """Trading signal WebSocket message."""

    type: str = "trading_signal"
    agent_id: str
    signal_type: str
    symbol: str
    confidence: float
    action: str
    price: float


class TradeExecutionMessage(WebSocketMessage):
    """Trade execution WebSocket message."""

    type: str = "trade_execution"
    agent_id: str
    trade_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    status: str


class SystemHealthMessage(WebSocketMessage):
    """System health WebSocket message."""

    type: str = "system_health"
    services: Dict[str, bool]
    agent_count: int
    active_agents: int


class ErrorMessage(WebSocketMessage):
    """Error WebSocket message."""

    type: str = "error"
    error_code: str
    error_message: str
    agent_id: Optional[str] = None
