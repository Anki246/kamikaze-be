"""
Shared Constants for Kamikaze AI
Contains common constants used across the application.
"""

# Trading pairs and symbols
TRADING_PAIRS = [
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

# API endpoints
API_ENDPOINTS = {
    "binance_spot": "https://api.binance.com",
    "binance_futures": "https://fapi.binance.com",
    "binance_websocket": "wss://stream.binance.com:9443/ws/",
    "binance_futures_websocket": "wss://fstream.binance.com/ws/",
}

# Default configuration
DEFAULT_CONFIG = {
    "trade_amount": 50.0,
    "leverage": 10,
    "trailing_take_profit": 0.5,
    "trailing_stop_loss_1": 0.3,
    "trailing_stop_loss_2": 0.5,
    "trailing_stop_loss_3": 0.8,
    "allocation_btc": 0.4,
    "allocation_eth": 0.3,
    "allocation_alt": 0.3,
    "signal_threshold": 0.03,
    "momentum_threshold": 0.02,
}

# Technical analysis parameters
TA_PARAMS = {
    "rsi_period": 14,
    "rsi_overbought": 70,
    "rsi_oversold": 30,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2,
    "sma_short": 10,
    "sma_long": 50,
}

# Timeframes for analysis
TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

# Risk management
RISK_PARAMS = {
    "max_position_size": 1000.0,
    "max_daily_loss": 100.0,
    "max_drawdown": 0.1,
    "position_sizing": "fixed",
}
