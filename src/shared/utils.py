"""
Shared Utility Functions for Enhanced Billa Trading Bot
Contains common helper functions used across the application.
"""

import time
import hmac
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union


def format_currency(amount: float, currency: str = "USDT", decimals: int = 2) -> str:
    """Format currency amount with proper decimals and symbol."""
    return f"{amount:.{decimals}f} {currency}"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def generate_binance_signature(query_string: str, secret_key: str) -> str:
    """Generate HMAC SHA256 signature for Binance API."""
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def get_timestamp() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def format_timestamp(timestamp: int) -> str:
    """Format timestamp to readable datetime string."""
    return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")


def validate_trading_pair(symbol: str) -> bool:
    """Validate if trading pair format is correct."""
    return len(symbol) >= 6 and symbol.isupper() and symbol.endswith("USDT")


def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """Calculate position size based on risk management."""
    risk_amount = account_balance * (risk_percentage / 100)
    price_difference = abs(entry_price - stop_loss_price)
    
    if price_difference == 0:
        return 0.0
    
    return risk_amount / price_difference


def round_to_precision(value: float, precision: int) -> float:
    """Round value to specified precision."""
    return round(value, precision)


def safe_float_conversion(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float with default fallback."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def format_log_message(level: str, message: str, **kwargs) -> str:
    """Format log message with timestamp and additional context."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = " | ".join([f"{k}={v}" for k, v in kwargs.items()]) if kwargs else ""
    context_str = f" | {context}" if context else ""
    return f"[{timestamp}] {level}: {message}{context_str}"


def validate_environment_variables(required_vars: List[str]) -> Dict[str, bool]:
    """Validate that required environment variables are set."""
    import os
    return {var: bool(os.getenv(var)) for var in required_vars}


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """Merge multiple dictionaries, with later ones taking precedence."""
    result = {}
    for d in dicts:
        result.update(d)
    return result
