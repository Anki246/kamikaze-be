"""
Pytest configuration and fixtures for Kamikaze AI tests.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
from httpx import AsyncClient

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_config():
    """Test configuration fixture."""
    return {
        "environment": "test",
        "use_aws_secrets": False,
        "log_level": "DEBUG",
        "database_url": "sqlite:///test.db",
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "ENVIRONMENT": "test",
        "USE_AWS_SECRETS": "false",
        "LOG_LEVEL": "DEBUG",
        "PYTHONPATH": "/app/src",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    async with AsyncClient() as client:
        yield client


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "trading": {
            "leverage": 10,
            "trade_amount_usdt": 50.0,
            "max_position_size_pct": 2.0,
            "pump_threshold": 0.03,
            "dump_threshold": -0.03,
            "min_confidence": 35,
        },
        "risk_management": {
            "trailing_stop_loss": {"level_1": 1.5, "level_2": 2.5, "level_3": 4.0}
        },
        "trading_mode": {
            "mode": "SIMULATION",
            "enable_real_trades": False,
            "simulation_mode": True,
        },
    }


@pytest.fixture
def mock_aws_secrets(monkeypatch):
    """Mock AWS Secrets Manager for testing."""

    def mock_get_secret(secret_name):
        secrets = {
            "kmkz-db-secrets": {
                "host": "localhost",
                "port": "5432",
                "database": "test_db",
                "username": "test_user",
                "password": "test_password",
            },
            "kmkz-app-secrets": {
                "groq_api_key": "test_groq_key",
                "aws_access_key_id": "test_access_key",
                "aws_secret_access_key": "test_secret_key",
            },
        }
        return secrets.get(secret_name, {})

    monkeypatch.setattr(
        "src.infrastructure.aws_secrets_manager.SecretsManager.get_secret",
        mock_get_secret,
    )
    return mock_get_secret


# Test data fixtures
@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        "symbol": "BTCUSDT",
        "price": "50000.00",
        "change_24h": "2.5",
        "volume_24h": "1000000.00",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_trade_signal():
    """Sample trade signal for testing."""
    return {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 85,
        "price": 50000.0,
        "quantity": 0.001,
        "timestamp": "2024-01-01T00:00:00Z",
    }
