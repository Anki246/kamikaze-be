#!/usr/bin/env python3
"""
Configuration Loader for Kamikaze AI
AWS Secrets Manager integration with environment variable fallback.

This module provides:
- Centralized configuration loading using AWS Secrets Manager
- Environment variable fallback for system-level configuration
- Comprehensive error handling and logging
- Caching for performance optimization

Usage:
    from infrastructure.config_loader import load_configuration
    await load_configuration()

    # Or for synchronous contexts:
    from infrastructure.config_loader import initialize_config
    initialize_config()
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Setup logging
logger = logging.getLogger(__name__)

# Global configuration state
_config_initialized = False
_config_data = {}

try:
    from .aws_secrets_manager import ConfigManager, config_manager

    AWS_SECRETS_AVAILABLE = True
except ImportError:
    AWS_SECRETS_AVAILABLE = False
    config_manager = None

# No dotenv fallback - system uses AWS Secrets Manager and environment variables only


async def load_configuration(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from AWS Secrets Manager with environment variable fallback.

    Args:
        force_reload: Force reload configuration even if already loaded

    Returns:
        Dictionary containing all configuration values
    """
    global _config_initialized, _config_data

    if _config_initialized and not force_reload:
        return _config_data

    logger.info("🔧 Loading Kamikaze AI configuration...")

    # Determine environment and configuration strategy
    environment = os.getenv("ENVIRONMENT", "development")
    use_aws_secrets = (
        environment == "production"
        or os.getenv("USE_AWS_SECRETS", "false").lower() == "true"
    )

    config_data = {}

    if use_aws_secrets and AWS_SECRETS_AVAILABLE:
        logger.info("🔐 Loading configuration from AWS Secrets Manager")
        aws_errors = []

        try:
            # Load database configuration
            try:
                db_config = await config_manager.get_database_config()
                config_data.update(
                    {
                        "DB_HOST": db_config.host,
                        "DB_PORT": str(db_config.port),
                        "DB_NAME": db_config.database,
                        "DB_USER": db_config.username,
                        "DB_PASSWORD": db_config.password,
                        "DB_SSL_MODE": db_config.ssl_mode,
                        "DB_MIN_SIZE": str(db_config.min_size),
                        "DB_MAX_SIZE": str(db_config.max_size),
                        "DB_TIMEOUT": str(db_config.timeout),
                    }
                )
                logger.debug(
                    "✅ Database configuration loaded from AWS Secrets Manager"
                )
            except Exception as e:
                aws_errors.append(f"Database config: {e}")
                logger.warning(
                    f"⚠️ Failed to load database config from AWS Secrets Manager: {e}"
                )

            # Load API keys
            try:
                api_keys = await config_manager.get_api_keys()
                config_data.update(
                    {
                        "BINANCE_API_KEY": api_keys.binance_api_key or "",
                        "BINANCE_SECRET_KEY": api_keys.binance_secret_key or "",
                        "GROQ_API_KEY": api_keys.groq_api_key or "",
                        "OPENAI_API_KEY": api_keys.openai_api_key or "",
                    }
                )
                logger.debug("✅ API keys loaded from AWS Secrets Manager")
            except Exception as e:
                aws_errors.append(f"API keys: {e}")
                logger.warning(
                    f"⚠️ Failed to load API keys from AWS Secrets Manager: {e}"
                )

            # Load application secrets
            try:
                app_secrets = await config_manager.get_application_secrets()
                config_data.update(
                    {
                        "JWT_SECRET": app_secrets.jwt_secret,
                        "ENCRYPTION_KEY": app_secrets.encryption_key,
                        "CREDENTIALS_ENCRYPTION_KEY": app_secrets.credentials_encryption_key,
                        "WEBHOOK_SECRET": app_secrets.webhook_secret or "",
                    }
                )
                logger.debug("✅ Application secrets loaded from AWS Secrets Manager")
            except Exception as e:
                aws_errors.append(f"Application secrets: {e}")
                logger.warning(
                    f"⚠️ Failed to load application secrets from AWS Secrets Manager: {e}"
                )

            # Load AWS credentials
            try:
                aws_creds = await config_manager.get_aws_credentials()
                config_data.update(
                    {
                        "AWS_ACCESS_KEY_ID": aws_creds.access_key_id,
                        "AWS_SECRET_ACCESS_KEY": aws_creds.secret_access_key,
                        "AWS_REGION": aws_creds.region,
                        "AWS_SESSION_TOKEN": aws_creds.session_token or "",
                    }
                )
                logger.debug("✅ AWS credentials loaded from AWS Secrets Manager")
            except Exception as e:
                aws_errors.append(f"AWS credentials: {e}")
                logger.warning(
                    f"⚠️ Failed to load AWS credentials from AWS Secrets Manager: {e}"
                )

            if config_data:
                logger.info(
                    f"✅ Partial configuration loaded from AWS Secrets Manager ({len(config_data)} settings)"
                )
                if aws_errors:
                    logger.warning(
                        f"⚠️ Some secrets failed to load: {len(aws_errors)} errors"
                    )
                    for error in aws_errors:
                        logger.debug(f"   - {error}")
            else:
                logger.error("❌ No configuration loaded from AWS Secrets Manager")
                use_aws_secrets = False

        except Exception as e:
            logger.error(f"❌ Critical error loading from AWS Secrets Manager: {e}")
            logger.info("🔄 Falling back to environment variables")
            use_aws_secrets = False

    if not use_aws_secrets:
        # Fallback to environment variables only
        logger.info("📝 Loading configuration from system environment variables")

        # Populate config_data with environment variables
        env_vars = [
            # Database
            "DB_HOST",
            "DB_PORT",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "DB_SSL_MODE",
            "DB_MIN_SIZE",
            "DB_MAX_SIZE",
            "DB_TIMEOUT",
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DATABASE",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            # API Keys
            "BINANCE_API_KEY",
            "BINANCE_SECRET_KEY",
            "GROQ_API_KEY",
            "OPENAI_API_KEY",
            # Application secrets
            "JWT_SECRET",
            "ENCRYPTION_KEY",
            "CREDENTIALS_ENCRYPTION_KEY",
            "WEBHOOK_SECRET",
            # AWS
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_REGION",
            "AWS_DEFAULT_REGION",
            "AWS_SESSION_TOKEN",
            # Environment
            "ENVIRONMENT",
            "USE_AWS_SECRETS",
            # Trading configuration
            "LEVERAGE",
            "TRADE_AMOUNT_USDT",
            "MAX_POSITION_SIZE_PCT",
            "PUMP_THRESHOLD",
            "DUMP_THRESHOLD",
            "MIN_CONFIDENCE",
            "SIGNAL_STRENGTH_THRESHOLD",
            "MIN_24H_CHANGE",
            "MAX_CYCLES",
            "ALLOCATION_STRATEGY",
            "MIN_TRADE_AMOUNT",
        ]

        for var in env_vars:
            value = os.getenv(var)
            if value is not None:
                config_data[var] = value

    # Store configuration globally
    _config_data = config_data
    _config_initialized = True

    logger.info(f"🎯 Configuration loaded successfully ({len(config_data)} settings)")
    return config_data


def initialize_config() -> None:
    """
    Synchronous configuration initialization for use in non-async contexts.

    Marks configuration as initialized for synchronous contexts.
    """
    global _config_initialized

    if _config_initialized:
        return

    logger.info("✅ Configuration system initialized (synchronous mode)")
    _config_initialized = True


def get_config_value(key: str, default: Any = None, type_func: callable = str) -> Any:
    """
    Get a configuration value with type conversion.

    This function replaces os.getenv() calls throughout the codebase.

    Args:
        key: Configuration key
        default: Default value if not found
        type_func: Type conversion function (str, int, float, bool)

    Returns:
        Configuration value with proper type conversion
    """
    # Ensure configuration is initialized
    if not _config_initialized:
        initialize_config()

    # First check cached configuration
    if key in _config_data:
        value = _config_data[key]
    else:
        # Fallback to environment variable
        value = os.getenv(key)

    if value is None:
        return default

    # Type conversion
    try:
        if type_func == bool:
            return value.lower() in ("true", "1", "yes", "on")
        return type_func(value)
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Invalid configuration value {key}={value}, using default")
        return default


def is_production() -> bool:
    """Check if running in production environment."""
    return get_config_value("ENVIRONMENT", "development") == "production"


def should_use_aws_secrets() -> bool:
    """Check if AWS Secrets Manager should be used."""
    return is_production() or get_config_value("USE_AWS_SECRETS", "false", bool)


def clear_config_cache() -> None:
    """Clear configuration cache to force reload."""
    global _config_initialized
    _config_initialized = False
    _config_data.clear()

    if AWS_SECRETS_AVAILABLE and config_manager:
        config_manager.clear_cache()

    logger.info("🧹 Configuration cache cleared")
