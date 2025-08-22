"""
Database Configuration for Kamikaze AI
Handles PostgreSQL database configuration and connection management
Supports both local environment variables and AWS Secrets Manager
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Load configuration from centralized system
try:
    from .config_loader import get_config_value, initialize_config

    initialize_config()

    # Use centralized configuration function
    def get_db_config_value(
        key: str, default: Any = None, type_func: callable = str
    ) -> Any:
        return get_config_value(key, default, type_func)

except ImportError:
    # Fallback function for direct environment variable access
    def get_db_config_value(
        key: str, default: Any = None, type_func: callable = str
    ) -> Any:
        value = os.getenv(key, default)
        if value is None or value == default:
            return default
        try:
            if type_func == bool:
                return str(value).lower() in ("true", "1", "yes", "on")
            return type_func(value)
        except (ValueError, TypeError):
            return default


# Import AWS Secrets Manager integration
try:
    from .aws_secrets_manager import AWSSecretsManager

    AWS_SECRETS_AVAILABLE = True
except ImportError:
    AWS_SECRETS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """PostgreSQL database configuration."""

    host: str = "localhost"
    port: int = 5432
    database: str = "kamikaze"
    user: str = "postgres"
    password: Optional[str] = None  # Must be provided via environment variable
    min_pool_size: int = 1
    max_pool_size: int = 10
    command_timeout: int = 30
    ssl_mode: str = "prefer"

    def __post_init__(self):
        """Load configuration from AWS Secrets Manager or environment variables."""
        # PRIORITY 1: Always try AWS Secrets Manager first
        if self._should_use_aws_secrets():
            logger.info(
                "🔐 Priority 1: Attempting to load database configuration from AWS Secrets Manager"
            )
            if self._load_from_aws_secrets():
                logger.info(
                    "✅ Successfully loaded database configuration from AWS Secrets Manager"
                )
                return
            else:
                logger.info(
                    "🔄 AWS Secrets Manager failed, falling back to localhost database"
                )

        # PRIORITY 2: Fallback to localhost database with environment variables
        logger.info(
            "🔧 Priority 2: Loading localhost database configuration from environment variables"
        )
        self._load_from_environment()

    def _should_use_aws_secrets(self) -> bool:
        """Determine if AWS Secrets Manager should be used."""
        # PRIORITY: Always try AWS Secrets Manager first if available
        # Fall back to localhost only if AWS Secrets Manager fails
        return AWS_SECRETS_AVAILABLE

    def _load_from_aws_secrets(self) -> bool:
        """Load database configuration from AWS Secrets Manager."""
        try:
            import asyncio
            import concurrent.futures

            secrets_manager = AWSSecretsManager()

            # Use thread pool to run async function
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_async_secrets_fetch, secrets_manager)
                db_credentials = future.result(timeout=30)  # 30 second timeout

            if db_credentials:
                self.host = db_credentials.host
                self.port = db_credentials.port
                self.database = db_credentials.database
                self.user = db_credentials.username
                self.password = db_credentials.password
                self.ssl_mode = db_credentials.ssl_mode

                logger.info(
                    f"✅ Loaded AWS RDS config: {self.host}:{self.port}/{self.database}"
                )
                return True
        except Exception as e:
            logger.error(f"❌ Error loading from AWS Secrets Manager: {e}")

        return False

    def _run_async_secrets_fetch(self, secrets_manager):
        """Run async secrets fetch in a new event loop."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(secrets_manager.get_database_credentials())
        finally:
            loop.close()

    def _load_from_environment(self):
        """Load configuration from centralized configuration system."""
        # Use DB_ prefix for consistency with FastMCP server
        self.host = get_db_config_value("DB_HOST") or get_db_config_value(
            "POSTGRES_HOST", self.host
        )
        self.port = get_db_config_value("DB_PORT", None, int) or get_db_config_value(
            "POSTGRES_PORT", self.port, int
        )
        self.database = get_db_config_value("DB_NAME") or get_db_config_value(
            "POSTGRES_DATABASE", self.database
        )
        self.user = get_db_config_value("DB_USER") or get_db_config_value(
            "POSTGRES_USER", self.user
        )
        self.password = get_db_config_value("DB_PASSWORD") or get_db_config_value(
            "POSTGRES_PASSWORD", self.password
        )

        # Configure SSL for RDS connections
        if self.host and ".rds.amazonaws.com" in self.host:
            self.ssl_mode = "require"
            logger.info(f"🔐 Detected RDS host, enabling SSL: {self.host}")
        elif self.host != "localhost":
            self.ssl_mode = "prefer"
        self.min_pool_size = get_db_config_value(
            "DB_MIN_SIZE", None, int
        ) or get_db_config_value("POSTGRES_MIN_POOL_SIZE", self.min_pool_size, int)
        self.max_pool_size = get_db_config_value(
            "DB_MAX_SIZE", None, int
        ) or get_db_config_value("POSTGRES_MAX_POOL_SIZE", self.max_pool_size, int)
        self.command_timeout = get_db_config_value(
            "DB_TIMEOUT", None, int
        ) or get_db_config_value("POSTGRES_COMMAND_TIMEOUT", self.command_timeout, int)
        self.ssl_mode = get_db_config_value("DB_SSL_MODE") or get_db_config_value(
            "POSTGRES_SSL_MODE", self.ssl_mode
        )

        # Handle password for localhost vs production
        environment = get_db_config_value("ENVIRONMENT", "development")

        if not self.password:
            if self.host == "localhost":
                # For localhost, use the known password for development
                logger.info(
                    "🔧 Localhost database detected - using development password"
                )
                self.password = "admin2025"  # Known localhost password
            elif environment == "production":
                raise ValueError(
                    "Database password must be provided via DB_PASSWORD environment variable in production"
                )
            else:
                logger.warning(
                    "⚠️  No database password provided - using empty password for development"
                )
                self.password = ""

    def get_password_for_connection(self) -> str:
        """Get password for database connection, prompting if needed for localhost."""
        if self.password is not None:
            return self.password

        if self.host == "localhost":
            try:
                import getpass

                password = getpass.getpass(
                    f"🔐 Enter password for PostgreSQL user '{self.user}' on localhost: "
                )
                return password
            except (ImportError, KeyboardInterrupt):
                logger.warning("⚠️ Password prompt failed, using empty password")
                return ""

        return ""

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        password = self.get_password_for_connection()
        return f"postgresql://{self.user}:{password}@{self.host}:{self.port}/{self.database}"

    @property
    def connection_params(self) -> dict:
        """Get connection parameters for asyncpg."""
        password = self.get_password_for_connection()
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": password,
            "min_size": self.min_pool_size,
            "max_size": self.max_pool_size,
            "command_timeout": self.command_timeout,
        }


# Note: Database configuration is now lazy-loaded to avoid early initialization
# Use DatabaseConfig() directly in your code instead of the global instance

# Database schema definitions for Kamikaze AI
SCHEMA_DEFINITIONS = {
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            role VARCHAR(20) DEFAULT 'trader',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "testnet_credentials": """
        CREATE TABLE IF NOT EXISTS testnet_credentials (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            exchange VARCHAR(20) NOT NULL,
            api_key VARCHAR(255) NOT NULL,
            secret_key VARCHAR(255) NOT NULL,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, exchange)
        )
    """,
    "binance_credentials": """
        CREATE TABLE IF NOT EXISTS binance_credentials (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            api_key VARCHAR(255) NOT NULL,
            secret_key VARCHAR(255) NOT NULL,
            is_mainnet BOOLEAN DEFAULT false,
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, is_mainnet)
        )
    """,
    "trading_agents": """
        CREATE TABLE IF NOT EXISTS trading_agents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            agent_name VARCHAR(100) NOT NULL,
            strategy_type VARCHAR(50) NOT NULL,
            configuration JSONB NOT NULL,
            is_active BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "trading_sessions": """
        CREATE TABLE IF NOT EXISTS trading_sessions (
            id SERIAL PRIMARY KEY,
            agent_id INTEGER REFERENCES trading_agents(id) ON DELETE CASCADE,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_end TIMESTAMP,
            total_trades INTEGER DEFAULT 0,
            profit_loss DECIMAL(15,8) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'active'
        )
    """,
    "trades": """
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES trading_sessions(id) ON DELETE CASCADE,
            symbol VARCHAR(20) NOT NULL,
            side VARCHAR(10) NOT NULL,
            quantity DECIMAL(15,8) NOT NULL,
            price DECIMAL(15,8) NOT NULL,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            profit_loss DECIMAL(15,8),
            fees DECIMAL(15,8) DEFAULT 0
        )
    """,
    "market_data": """
        CREATE TABLE IF NOT EXISTS market_data (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            price DECIMAL(15,8) NOT NULL,
            volume DECIMAL(15,8) NOT NULL,
            change_24h DECIMAL(10,4),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "system_logs": """
        CREATE TABLE IF NOT EXISTS system_logs (
            id SERIAL PRIMARY KEY,
            level VARCHAR(10) NOT NULL,
            message TEXT NOT NULL,
            component VARCHAR(50),
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

# Indexes for better performance
INDEX_DEFINITIONS = [
    "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
    "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
    "CREATE INDEX IF NOT EXISTS idx_testnet_credentials_user_id ON testnet_credentials(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_binance_credentials_user_id ON binance_credentials(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_trading_agents_user_id ON trading_agents(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_trading_sessions_agent_id ON trading_sessions(agent_id)",
    "CREATE INDEX IF NOT EXISTS idx_trades_session_id ON trades(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp ON market_data(symbol, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)",
    "CREATE INDEX IF NOT EXISTS idx_system_logs_component ON system_logs(component)",
    "CREATE INDEX IF NOT EXISTS idx_system_logs_created_at ON system_logs(created_at)",
]
