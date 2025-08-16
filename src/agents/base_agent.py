"""
Base Agent Class for Multi-Agent Trading Bot Architecture
Provides abstract interface and common functionality for all trading agents.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class AgentStatus(Enum):
    """Agent status enumeration."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    PAUSED = "paused"


class StrategyType(Enum):
    """Trading strategy types."""

    PUMP_DUMP = "pump_dump"
    ARBITRAGE = "arbitrage"
    DCA = "dca"
    GRID = "grid"
    MARKET_MAKING = "market_making"
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    SCALPING = "scalping"


@dataclass
class AgentMetadata:
    """Agent metadata and capabilities."""

    name: str
    version: str
    strategy_type: StrategyType
    description: str
    author: str = "FluxTrader Team"
    supported_pairs: List[str] = field(default_factory=list)
    min_balance_required: float = 0.0
    risk_level: str = "medium"  # low, medium, high
    time_frame: str = "1m"  # 1m, 5m, 15m, 1h, etc.
    requires_api_keys: List[str] = field(default_factory=lambda: ["binance"])
    features: List[str] = field(default_factory=list)


@dataclass
class AgentMetrics:
    """Agent performance metrics."""

    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    total_profit_loss: float = 0.0
    win_rate: float = 0.0
    average_profit: float = 0.0
    average_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    uptime_seconds: int = 0
    last_trade_time: Optional[datetime] = None
    current_positions: int = 0

    def update_win_rate(self):
        """Update win rate based on successful/total trades."""
        if self.total_trades > 0:
            self.win_rate = (self.successful_trades / self.total_trades) * 100


@dataclass
class AgentConfig:
    """Base agent configuration."""

    enabled: bool = True
    max_concurrent_trades: int = 1
    max_daily_trades: int = 100
    max_position_size: float = 100.0
    stop_loss_enabled: bool = True
    take_profit_enabled: bool = True
    logging_level: str = "INFO"
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "enabled": self.enabled,
            "max_concurrent_trades": self.max_concurrent_trades,
            "max_daily_trades": self.max_daily_trades,
            "max_position_size": self.max_position_size,
            "stop_loss_enabled": self.stop_loss_enabled,
            "take_profit_enabled": self.take_profit_enabled,
            "logging_level": self.logging_level,
            "dry_run": self.dry_run,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents.

    All trading agents must inherit from this class and implement the required methods.
    This ensures consistent interface and behavior across different trading strategies.
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier for this agent instance
            config: Agent-specific configuration dictionary
        """
        self.agent_id = agent_id
        self.config = config
        self.status = AgentStatus.STOPPED
        self.logger = self._setup_logging()
        self.metrics = AgentMetrics()
        self.start_time: Optional[datetime] = None
        self.stop_time: Optional[datetime] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

        # Initialize agent-specific configuration
        self.agent_config = self._load_agent_config(config)

        self.logger.info(
            f"Initialized {self.get_metadata().name} agent with ID: {agent_id}"
        )

    def _setup_logging(self) -> logging.Logger:
        """Setup agent-specific logging."""
        logger = logging.getLogger(f"agent.{self.agent_id}")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f"%(asctime)s - {self.agent_id} - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _load_agent_config(self, config: Dict[str, Any]) -> AgentConfig:
        """Load and validate agent configuration."""
        agent_config = AgentConfig()

        # Update with provided config
        for key, value in config.items():
            if hasattr(agent_config, key):
                setattr(agent_config, key, value)

        return agent_config

    @abstractmethod
    def get_metadata(self) -> AgentMetadata:
        """
        Return agent metadata and capabilities.

        Returns:
            AgentMetadata: Agent information and capabilities
        """
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the agent (setup connections, validate config, etc.).

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def start_trading(self) -> bool:
        """
        Start the trading agent.

        Returns:
            bool: True if started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def stop_trading(self) -> bool:
        """
        Stop the trading agent gracefully.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        pass

    @abstractmethod
    async def pause_trading(self) -> bool:
        """
        Pause the trading agent (can be resumed).

        Returns:
            bool: True if paused successfully, False otherwise
        """
        pass

    @abstractmethod
    async def resume_trading(self) -> bool:
        """
        Resume the trading agent from paused state.

        Returns:
            bool: True if resumed successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get current trading positions.

        Returns:
            List[Dict]: List of current positions
        """
        pass

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Get current account balance.

        Returns:
            Dict[str, float]: Balance information
        """
        pass

    def get_uptime(self) -> int:
        """
        Get agent uptime in seconds.

        Returns:
            int: Uptime in seconds since agent started
        """
        if self.start_time:
            return int((datetime.now() - self.start_time).total_seconds())
        return 0

    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and basic info.

        Returns:
            Dict: Agent status information
        """
        metadata = self.get_metadata()
        uptime = self.get_uptime()

        return {
            "agent_id": self.agent_id,
            "name": metadata.name,
            "status": self.status.value,
            "strategy_type": metadata.strategy_type.value,
            "uptime_seconds": uptime,
            "is_running": self._running,
            "config": self.agent_config.to_dict(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent performance metrics.

        Returns:
            Dict: Performance metrics
        """
        # Update uptime
        self.metrics.uptime_seconds = self.get_uptime()

        return {
            "total_trades": self.metrics.total_trades,
            "successful_trades": self.metrics.successful_trades,
            "failed_trades": self.metrics.failed_trades,
            "total_profit_loss": self.metrics.total_profit_loss,
            "win_rate": self.metrics.win_rate,
            "average_profit": self.metrics.average_profit,
            "average_loss": self.metrics.average_loss,
            "max_drawdown": self.metrics.max_drawdown,
            "sharpe_ratio": self.metrics.sharpe_ratio,
            "uptime_seconds": self.metrics.uptime_seconds,
            "last_trade_time": self.metrics.last_trade_time.isoformat()
            if self.metrics.last_trade_time
            else None,
            "current_positions": self.metrics.current_positions,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the agent.

        Returns:
            Dict: Health check results
        """
        try:
            # Basic health checks
            health_status = {
                "healthy": True,
                "checks": {
                    "status": self.status != AgentStatus.ERROR,
                    "config_valid": self.agent_config is not None,
                    "logger_active": self.logger is not None,
                    "metrics_available": self.metrics is not None,
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Check if all basic checks pass
            health_status["healthy"] = all(health_status["checks"].values())

            return health_status

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def update_metrics(self, trade_result: Dict[str, Any]):
        """
        Update agent metrics with trade result.

        Args:
            trade_result: Dictionary containing trade outcome information
        """
        self.metrics.total_trades += 1
        self.metrics.last_trade_time = datetime.now()

        if trade_result.get("success", False):
            self.metrics.successful_trades += 1
            profit = trade_result.get("profit", 0.0)
            self.metrics.total_profit_loss += profit
            if profit > 0:
                self.metrics.average_profit = (
                    self.metrics.average_profit * (self.metrics.successful_trades - 1)
                    + profit
                ) / self.metrics.successful_trades
        else:
            self.metrics.failed_trades += 1
            loss = trade_result.get("loss", 0.0)
            self.metrics.total_profit_loss -= loss
            if loss > 0:
                self.metrics.average_loss = (
                    self.metrics.average_loss * (self.metrics.failed_trades - 1) + loss
                ) / self.metrics.failed_trades

        # Update win rate
        self.metrics.update_win_rate()

        self.logger.info(
            f"Updated metrics: Total trades: {self.metrics.total_trades}, Win rate: {self.metrics.win_rate:.2f}%"
        )

    def _set_status(self, status: AgentStatus):
        """Set agent status and log the change."""
        old_status = self.status
        self.status = status
        self.logger.info(f"Status changed: {old_status.value} -> {status.value}")

        if status == AgentStatus.RUNNING and not self.start_time:
            self.start_time = datetime.now()
        elif status == AgentStatus.STOPPED:
            self.stop_time = datetime.now()
            self._running = False
