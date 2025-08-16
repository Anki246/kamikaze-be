"""
Database Configuration for FluxTrader
Handles PostgreSQL database configuration and connection management
Supports both local environment variables and AWS Secrets Manager
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

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
        # Try AWS Secrets Manager first if in production environment
        if self._should_use_aws_secrets():
            logger.info(
                "🔐 Attempting to load database configuration from AWS Secrets Manager"
            )
            if self._load_from_aws_secrets():
                logger.info(
                    "✅ Successfully loaded database configuration from AWS Secrets Manager"
                )
                return
            else:
                logger.warning(
                    "⚠️  Failed to load from AWS Secrets Manager, falling back to environment variables"
                )

        # Fallback to environment variables
        logger.info("🔧 Loading database configuration from environment variables")
        self._load_from_environment()

    def _should_use_aws_secrets(self) -> bool:
        """Determine if AWS Secrets Manager should be used."""
        # Only use AWS Secrets Manager if explicitly enabled and available
        # In CI/production, we may use environment variables instead
        return (
            AWS_SECRETS_AVAILABLE
            and os.getenv("USE_AWS_SECRETS", "false").lower() == "true"
        )

    def _load_from_aws_secrets(self) -> bool:
        """Load database configuration from AWS Secrets Manager."""
        try:
            secrets_manager = AWSSecretsManager()
            db_credentials = secrets_manager.get_database_credentials()

            if db_credentials:
                self.host = db_credentials.get("host", self.host)
                self.port = int(db_credentials.get("port", self.port))
                self.database = db_credentials.get("database", self.database)
                self.user = db_credentials.get("username", self.user)
                self.password = db_credentials.get("password", self.password)

                # Use SSL for RDS connections
                if self.host != "localhost":
                    self.ssl_mode = "require"

                return True
        except Exception as e:
            logger.error(f"❌ Error loading from AWS Secrets Manager: {e}")

        return False

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Use DB_ prefix for consistency with FastMCP server
        self.host = os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", self.host))
        self.port = int(
            os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", str(self.port)))
        )
        self.database = os.getenv(
            "DB_NAME", os.getenv("POSTGRES_DATABASE", self.database)
        )
        self.user = os.getenv("DB_USER", os.getenv("POSTGRES_USER", self.user))
        self.password = os.getenv(
            "DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", self.password)
        )
        self.min_pool_size = int(
            os.getenv(
                "DB_MIN_SIZE",
                os.getenv("POSTGRES_MIN_POOL_SIZE", str(self.min_pool_size)),
            )
        )
        self.max_pool_size = int(
            os.getenv(
                "DB_MAX_SIZE",
                os.getenv("POSTGRES_MAX_POOL_SIZE", str(self.max_pool_size)),
            )
        )
        self.command_timeout = int(
            os.getenv(
                "DB_TIMEOUT",
                os.getenv("POSTGRES_COMMAND_TIMEOUT", str(self.command_timeout)),
            )
        )
        self.ssl_mode = os.getenv(
            "DB_SSL_MODE", os.getenv("POSTGRES_SSL_MODE", self.ssl_mode)
        )

        # Validate that password is provided
        if not self.password:
            raise ValueError(
                "Database password must be provided via DB_PASSWORD environment variable"
            )

    @property
    def connection_string(self) -> str:
        """Get PostgreSQL connection string."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def connection_params(self) -> dict:
        """Get connection parameters for asyncpg."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "min_size": self.min_pool_size,
            "max_size": self.max_pool_size,
            "command_timeout": self.command_timeout,
        }


# Global database configuration instance
db_config = DatabaseConfig()

# Database schema definitions for FluxTrader
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
