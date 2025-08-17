"""
Configuration Management for FluxTrader
Handles JSON configuration files, environment variables, and application settings.
Priority: config.json > .env file > environment variables > defaults
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️  python-dotenv not available - using system environment variables")


@dataclass
class TradingConfig:
    """Trading configuration parameters."""

    # Core trading parameters
    leverage: int = 20
    trade_amount_usdt: float = 4.0
    max_position_size_pct: float = 2.0
    pump_threshold: float = 0.03
    dump_threshold: float = -0.03
    min_confidence: int = 35
    signal_strength_threshold: float = 0.4
    min_24h_change: float = 0.01
    max_cycles: int = 100
    allocation_strategy: str = "FIXED_AMOUNT"
    min_trade_amount: float = 5.0

    # Legacy parameters for backward compatibility
    trade_amount: float = 4.0  # Same as trade_amount_usdt
    signal_threshold: float = 0.03  # Same as pump_threshold
    momentum_threshold: float = 0.02


@dataclass
class RiskManagementConfig:
    """Risk management configuration."""

    # Multi-level trailing stop loss
    trailing_stop_loss_1: float = 1.5
    trailing_stop_loss_2: float = 2.5
    trailing_stop_loss_3: float = 4.0

    # Multi-level trailing take profit
    trailing_take_profit_1: float = 2.0
    trailing_take_profit_2: float = 3.5
    trailing_take_profit_3: float = 6.0


@dataclass
class TradingModeConfig:
    """Trading mode configuration."""

    mode: str = "REAL"
    enable_real_trades: bool = True
    simulation_mode: bool = False


@dataclass
class AIConfig:
    """AI and LLM configuration."""

    min_confidence_threshold: int = 35
    temperature: float = 0.1
    max_tokens: int = 400
    model: str = "llama3-8b-8192"


@dataclass
class MarketAnalysisConfig:
    """Market analysis configuration."""

    signal_strength_threshold: float = 0.4
    momentum_threshold: float = 0.02
    volume_threshold: int = 100000
    volatility_threshold: float = 0.5


@dataclass
class LoggingConfig:
    """Logging configuration."""

    log_level: str = "INFO"
    enable_file_logging: bool = True
    enable_console_logging: bool = True
    log_rotation: bool = True
    max_log_files: int = 10


@dataclass
class MCPConfig:
    """MCP server configuration."""

    enabled: bool = True
    timeout_seconds: int = 10
    retry_attempts: int = 3
    health_check_interval: int = 30


@dataclass
class APIConfig:
    """API server configuration."""

    port: int = 8000
    host: str = "0.0.0.0"
    enable_cors: bool = True
    request_timeout: int = 30

    # API Keys
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    alpha_vantage_key: Optional[str] = None

    def __post_init__(self):
        """Load API keys from environment variables (Binance credentials now retrieved from database)."""
        # Binance credentials are now primarily retrieved from database
        # Environment variables are kept for backward compatibility only
        self.binance_api_key = os.getenv("BINANCE_API_KEY")
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY")

        # Log warning if Binance credentials are found in environment
        if self.binance_api_key or self.binance_secret_key:
            print("⚠️ Binance credentials found in environment variables. Consider using database storage for better security.")

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")


@dataclass
class AppConfig:
    """Application configuration."""

    debug: bool = False
    real_trading: bool = True
    trading_pairs: list = field(
        default_factory=lambda: [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "XRPUSDT",
            "SOLUSDT",
            "DOTUSDT",
            "DOGEUSDT",
            "AVAXUSDT",
            "LINKUSDT",
        ]
    )

    def __post_init__(self):
        """Load app config from environment variables."""
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.real_trading = os.getenv("REAL_TRADING", "true").lower() == "true"


class ConfigManager:
    """Centralized configuration manager with JSON and environment variable support."""

    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file

        # Initialize with defaults
        self.trading = TradingConfig()
        self.risk_management = RiskManagementConfig()
        self.trading_mode = TradingModeConfig()
        self.ai = AIConfig()
        self.market_analysis = MarketAnalysisConfig()
        self.logging = LoggingConfig()
        self.mcp = MCPConfig()
        self.api = APIConfig()
        self.app = AppConfig()

        # Load configuration from JSON file if it exists
        self.load_from_json()

        # Override with environment variables
        self.load_from_env()

        print("✅ FluxTrader configuration loaded successfully")

    def load_from_json(self) -> None:
        """Load configuration from JSON file."""
        config_path = Path(self.config_file)
        # Try to find config.json in the project root
        if not config_path.exists():
            # Look for config.json in parent directories
            current_dir = Path(__file__).parent
            for _ in range(5):  # Search up to 5 levels up
                potential_config = current_dir / self.config_file
                if potential_config.exists():
                    config_path = potential_config
                    break
                current_dir = current_dir.parent

        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    json_config = json.load(f)

                # Update trading config
                if "trading" in json_config:
                    for key, value in json_config["trading"].items():
                        if hasattr(self.trading, key):
                            setattr(self.trading, key, value)

                # Update risk management config
                if "risk_management" in json_config:
                    risk_config = json_config["risk_management"]
                    if "trailing_stop_loss" in risk_config:
                        tsl = risk_config["trailing_stop_loss"]
                        self.risk_management.trailing_stop_loss_1 = tsl.get(
                            "level_1", 1.5
                        )
                        self.risk_management.trailing_stop_loss_2 = tsl.get(
                            "level_2", 2.5
                        )
                        self.risk_management.trailing_stop_loss_3 = tsl.get(
                            "level_3", 4.0
                        )

                    if "trailing_take_profit" in risk_config:
                        ttp = risk_config["trailing_take_profit"]
                        self.risk_management.trailing_take_profit_1 = ttp.get(
                            "level_1", 2.0
                        )
                        self.risk_management.trailing_take_profit_2 = ttp.get(
                            "level_2", 3.5
                        )
                        self.risk_management.trailing_take_profit_3 = ttp.get(
                            "level_3", 6.0
                        )

                # Update other configs
                config_mappings = {
                    "trading_mode": self.trading_mode,
                    "ai_settings": self.ai,
                    "market_analysis": self.market_analysis,
                    "logging": self.logging,
                    "mcp_settings": self.mcp,
                    "api_settings": self.api,
                }

                for section, config_obj in config_mappings.items():
                    if section in json_config:
                        for key, value in json_config[section].items():
                            if hasattr(config_obj, key):
                                setattr(config_obj, key, value)

                # Update trading pairs
                if "trading_pairs" in json_config:
                    self.app.trading_pairs = json_config["trading_pairs"]

                print(f"✅ Loaded configuration from {self.config_file}")

            except Exception as e:
                print(f"⚠️  Error loading config from {self.config_file}: {e}")
                print("Using default configuration values")
        else:
            print(f"⚠️  Config file {self.config_file} not found, using defaults")

    def load_from_env(self) -> None:
        """Load configuration from environment variables (overrides JSON)."""
        env_mappings = {
            "LEVERAGE": ("trading", "leverage", int),
            "TRADE_AMOUNT_USDT": ("trading", "trade_amount_usdt", float),
            "TRADING_MODE": ("trading_mode", "mode", str),
            "MAX_POSITION_SIZE_PCT": ("trading", "max_position_size_pct", float),
            "PUMP_THRESHOLD": ("trading", "pump_threshold", float),
            "DUMP_THRESHOLD": ("trading", "dump_threshold", float),
            "MIN_CONFIDENCE": ("trading", "min_confidence", int),
            "SIGNAL_STRENGTH_THRESHOLD": (
                "trading",
                "signal_strength_threshold",
                float,
            ),
            "MIN_24H_CHANGE": ("trading", "min_24h_change", float),
            "MAX_CYCLES": ("trading", "max_cycles", int),
            "ALLOCATION_STRATEGY": ("trading", "allocation_strategy", str),
            "MIN_TRADE_AMOUNT": ("trading", "min_trade_amount", float),
            "TRAILING_STOP_LOSS_1": ("risk_management", "trailing_stop_loss_1", float),
            "TRAILING_STOP_LOSS_2": ("risk_management", "trailing_stop_loss_2", float),
            "TRAILING_STOP_LOSS_3": ("risk_management", "trailing_stop_loss_3", float),
            "TRAILING_TAKE_PROFIT_1": (
                "risk_management",
                "trailing_take_profit_1",
                float,
            ),
            "TRAILING_TAKE_PROFIT_2": (
                "risk_management",
                "trailing_take_profit_2",
                float,
            ),
            "TRAILING_TAKE_PROFIT_3": (
                "risk_management",
                "trailing_take_profit_3",
                float,
            ),
        }

        for env_var, (section, attr, type_func) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config_obj = getattr(self, section)
                    setattr(config_obj, attr, type_func(value))
                except (ValueError, TypeError, AttributeError) as e:
                    print(f"⚠️  Invalid environment variable {env_var}={value}: {e}")

    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration and return status."""
        validation_results = {
            "binance_api_key": bool(self.api.binance_api_key),  # Optional - can be retrieved from database
            "binance_secret_key": bool(self.api.binance_secret_key),  # Optional - can be retrieved from database
            "groq_api_key": bool(self.api.groq_api_key),
            "trading_params": all(
                [
                    self.trading.trade_amount_usdt > 0,
                    self.trading.leverage > 0,
                    self.trading.max_position_size_pct > 0,
                    self.trading.min_trade_amount > 0,
                ]
            ),
            "risk_management": all(
                [
                    self.risk_management.trailing_stop_loss_1 > 0,
                    self.risk_management.trailing_take_profit_1 > 0,
                ]
            ),
        }

        # Log information about Binance credentials
        if not validation_results["binance_api_key"] or not validation_results["binance_secret_key"]:
            print("ℹ️ Binance credentials not found in environment variables. Will retrieve from database when needed.")

        return validation_results

    def get_trading_params(self) -> Dict[str, Any]:
        """Get all trading parameters as dictionary."""
        return {
            # Core trading parameters
            "leverage": self.trading.leverage,
            "trade_amount_usdt": self.trading.trade_amount_usdt,
            "trade_amount": self.trading.trade_amount_usdt,  # Legacy compatibility
            "max_position_size_pct": self.trading.max_position_size_pct,
            "pump_threshold": self.trading.pump_threshold,
            "dump_threshold": self.trading.dump_threshold,
            "min_confidence": self.trading.min_confidence,
            "signal_strength_threshold": self.trading.signal_strength_threshold,
            "min_24h_change": self.trading.min_24h_change,
            "max_cycles": self.trading.max_cycles,
            "allocation_strategy": self.trading.allocation_strategy,
            "min_trade_amount": self.trading.min_trade_amount,
            # Risk management
            "trailing_stop_loss_1": self.risk_management.trailing_stop_loss_1,
            "trailing_stop_loss_2": self.risk_management.trailing_stop_loss_2,
            "trailing_stop_loss_3": self.risk_management.trailing_stop_loss_3,
            "trailing_take_profit_1": self.risk_management.trailing_take_profit_1,
            "trailing_take_profit_2": self.risk_management.trailing_take_profit_2,
            "trailing_take_profit_3": self.risk_management.trailing_take_profit_3,
            # Legacy compatibility
            "signal_threshold": self.trading.pump_threshold,
            "momentum_threshold": self.trading.min_24h_change,
        }

    def save_to_json(self, filename: Optional[str] = None) -> None:
        """Save current configuration to JSON file."""
        if filename is None:
            filename = self.config_file

        config_dict = {
            "trading": {
                "leverage": self.trading.leverage,
                "trade_amount_usdt": self.trading.trade_amount_usdt,
                "max_position_size_pct": self.trading.max_position_size_pct,
                "pump_threshold": self.trading.pump_threshold,
                "dump_threshold": self.trading.dump_threshold,
                "min_confidence": self.trading.min_confidence,
                "signal_strength_threshold": self.trading.signal_strength_threshold,
                "min_24h_change": self.trading.min_24h_change,
                "max_cycles": self.trading.max_cycles,
                "allocation_strategy": self.trading.allocation_strategy,
                "min_trade_amount": self.trading.min_trade_amount,
            },
            "risk_management": {
                "trailing_stop_loss": {
                    "level_1": self.risk_management.trailing_stop_loss_1,
                    "level_2": self.risk_management.trailing_stop_loss_2,
                    "level_3": self.risk_management.trailing_stop_loss_3,
                },
                "trailing_take_profit": {
                    "level_1": self.risk_management.trailing_take_profit_1,
                    "level_2": self.risk_management.trailing_take_profit_2,
                    "level_3": self.risk_management.trailing_take_profit_3,
                },
            },
            "trading_mode": {
                "mode": self.trading_mode.mode,
                "enable_real_trades": self.trading_mode.enable_real_trades,
                "simulation_mode": self.trading_mode.simulation_mode,
            },
            "ai_settings": {
                "min_confidence_threshold": self.ai.min_confidence_threshold,
                "temperature": self.ai.temperature,
                "max_tokens": self.ai.max_tokens,
                "model": self.ai.model,
            },
            "market_analysis": {
                "signal_strength_threshold": self.market_analysis.signal_strength_threshold,
                "momentum_threshold": self.market_analysis.momentum_threshold,
                "volume_threshold": self.market_analysis.volume_threshold,
                "volatility_threshold": self.market_analysis.volatility_threshold,
            },
            "trading_pairs": self.app.trading_pairs,
            "logging": {
                "log_level": self.logging.log_level,
                "enable_file_logging": self.logging.enable_file_logging,
                "enable_console_logging": self.logging.enable_console_logging,
                "log_rotation": self.logging.log_rotation,
                "max_log_files": self.logging.max_log_files,
            },
            "mcp_settings": {
                "enabled": self.mcp.enabled,
                "timeout_seconds": self.mcp.timeout_seconds,
                "retry_attempts": self.mcp.retry_attempts,
                "health_check_interval": self.mcp.health_check_interval,
            },
            "api_settings": {
                "port": self.api.port,
                "host": self.api.host,
                "enable_cors": self.api.enable_cors,
                "request_timeout": self.api.request_timeout,
            },
        }

        try:
            with open(filename, "w") as f:
                json.dump(config_dict, f, indent=2)
            print(f"✅ Configuration saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving configuration to {filename}: {e}")


# Global configuration instance
config = ConfigManager()
