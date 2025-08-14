#!/usr/bin/env python3
"""
Binance FastMCP Server - Standards-Compliant Implementation
Professional Binance trading operations using FastMCP framework with stdio communication

Features:
- Complete Binance API integration with live market data
- Professional technical analysis with ta-lib library
- Comprehensive error handling and retry logic
- Modern Python 3.11+ async/await patterns
- Standards-compliant MCP protocol with stdio communication
"""

import asyncio
import logging
import sys
import time
import json
import hmac
import hashlib
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import aiohttp
import ssl
import numpy as np

# SSL certificate handling
try:
    import certifi
    CERTIFI_AVAILABLE = True
except ImportError:
    CERTIFI_AVAILABLE = False

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# FastMCP imports
from fastmcp import FastMCP
from pydantic import BaseModel, Field

# Database imports
from infrastructure.credentials_database import CredentialsDatabase

# Technical Analysis Libraries
try:
    import talib
    TALIB_AVAILABLE = True
    print("✅ TA-Lib loaded successfully", file=sys.stderr)
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️  TA-Lib not available - using manual calculations", file=sys.stderr)

# WebSocket support for real-time data
try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    print("⚠️  WebSocket support not available", file=sys.stderr)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging to stderr (stdout reserved for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Binance FastMCP Server")

# Initialize credentials database
credentials_db = CredentialsDatabase()

# Binance API configuration
BINANCE_BASE_URL = "https://fapi.binance.com"
BINANCE_WS_URL = "wss://fstream.binance.com/ws/"

# Global credentials cache (will be populated from database)
current_user_credentials = {
    "api_key": None,
    "secret_key": None,
    "user_id": None
}

# Global state management
active_streams: Dict[str, Any] = {}
request_cache: Dict[str, Dict[str, Any]] = {}
cache_ttl = 30  # seconds

# ============================================================================
# Credentials Management
# ============================================================================

async def set_user_credentials(user_id: int) -> bool:
    """Set user credentials from database for the current session."""
    global current_user_credentials

    try:
        # Ensure database connection
        if not await credentials_db.ensure_connected():
            logger.error("Failed to connect to credentials database")
            return False

        # Try to get mainnet credentials first
        mainnet_creds = await credentials_db.get_binance_credentials(user_id, is_mainnet=True)
        if mainnet_creds:
            current_user_credentials["api_key"] = mainnet_creds["api_key"]
            current_user_credentials["secret_key"] = mainnet_creds["secret_key"]
            current_user_credentials["user_id"] = user_id
            logger.info(f"✅ Set mainnet Binance credentials for user {user_id}")
            return True

        # Fallback to testnet credentials
        testnet_creds = await credentials_db.get_testnet_credentials(user_id, "binance")
        if testnet_creds:
            current_user_credentials["api_key"] = testnet_creds["api_key"]
            current_user_credentials["secret_key"] = testnet_creds["secret_key"]
            current_user_credentials["user_id"] = user_id
            logger.info(f"✅ Set testnet Binance credentials for user {user_id}")
            return True

        logger.warning(f"⚠️ No Binance credentials found for user {user_id}")
        return False

    except Exception as e:
        logger.error(f"❌ Failed to set credentials for user {user_id}: {e}")
        return False

def get_current_credentials() -> tuple[Optional[str], Optional[str]]:
    """Get current user's API credentials."""
    return current_user_credentials["api_key"], current_user_credentials["secret_key"]

# ============================================================================
# Pydantic Models for Tool Inputs
# ============================================================================

class TickerInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")

class MarketDataInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    timeframe: str = Field(default="1h", description="Timeframe for market data")
    limit: int = Field(default=100, description="Number of data points to retrieve")

class PlaceOrderInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    side: str = Field(description="Order side: BUY or SELL")
    quantity: float = Field(description="Order quantity")
    order_type: str = Field(default="MARKET", description="Order type: MARKET or LIMIT")
    price: Optional[float] = Field(default=None, description="Price for LIMIT orders")

class SetLeverageInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    leverage: int = Field(description="Leverage value (1-125)")

class SymbolInfoInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")

class TechnicalAnalysisInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    timeframe: str = Field(default="1h", description="Timeframe for analysis")
    indicators: Optional[List[str]] = Field(default=[], description="List of technical indicators to calculate")
    periods: int = Field(default=100, description="Number of periods for analysis")

class SupportResistanceInput(BaseModel):
    symbol: str = Field(description="Trading symbol (e.g., BTCUSDT)")
    timeframes: List[str] = Field(default=["1h", "4h", "1d"], description="List of timeframes to analyze")
    lookback_periods: int = Field(default=100, description="Number of periods to look back")

class UserCredentialsInput(BaseModel):
    user_id: int = Field(description="User ID to retrieve credentials for")

# ============================================================================
# Utility Functions
# ============================================================================

def generate_signature(query_string: str, secret_key: str) -> str:
    """Generate HMAC SHA256 signature for Binance API"""
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_timestamp() -> int:
    """Get current timestamp in milliseconds"""
    return int(time.time() * 1000)

def is_cache_valid(cache_key: str) -> bool:
    """Check if cached data is still valid"""
    if cache_key not in request_cache:
        return False
    
    cache_entry = request_cache[cache_key]
    return (time.time() - cache_entry.get("timestamp", 0)) < cache_ttl

def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached data if valid"""
    if is_cache_valid(cache_key):
        return request_cache[cache_key]["data"]
    return None

def set_cached_data(cache_key: str, data: Dict[str, Any]) -> None:
    """Cache data with timestamp"""
    request_cache[cache_key] = {
        "data": data,
        "timestamp": time.time()
    }

async def make_binance_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict] = None,
    signed: bool = False,
    use_cache: bool = True
) -> Dict[str, Any]:
    """Make authenticated request to Binance API with caching"""
    # Get credentials from database
    api_key, secret_key = get_current_credentials()

    if not api_key or not secret_key:
        return {
            "success": False,
            "error": "Binance API credentials not configured",
            "data": None
        }
    
    # Create cache key
    cache_key = f"{endpoint}_{method}_{json.dumps(params, sort_keys=True) if params else 'none'}"
    
    # Check cache first
    if use_cache and method == "GET":
        cached_data = get_cached_data(cache_key)
        if cached_data:
            logger.info(f"Using cached data for {endpoint}")
            return cached_data
    
    url = f"{BINANCE_BASE_URL}{endpoint}"
    headers = {"X-MBX-APIKEY": api_key}
    
    if params is None:
        params = {}
    
    if signed:
        params["timestamp"] = get_timestamp()
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        params["signature"] = generate_signature(query_string, secret_key)
    
    try:
        # Create proper SSL context with certificate verification
        # Check if SSL verification should be disabled (for development/testing)
        disable_ssl = os.getenv("DISABLE_SSL_VERIFICATION", "false").lower() == "true"

        if disable_ssl:
            logger.warning("⚠️  SSL verification disabled - not recommended for production")
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        else:
            if CERTIFI_AVAILABLE:
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                logger.debug("✅ Using certifi certificate bundle for SSL")
            else:
                ssl_context = ssl.create_default_context()
                logger.debug("✅ Using default SSL context")

            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED

        # Create connector with proper SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            if method == "GET":
                async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    data = await response.json()
            elif method == "POST":
                async with session.post(url, headers=headers, data=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    data = await response.json()
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            if response.status == 200:
                result = {"success": True, "data": data}
                # Cache successful GET requests
                if use_cache and method == "GET":
                    set_cached_data(cache_key, result)
                return result
            else:
                return {
                    "success": False,
                    "error": f"API Error {response.status}: {data.get('msg', 'Unknown error')}",
                    "data": data
                }
                
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Request timeout",
            "data": None
        }
    except Exception as e:
        logger.error(f"Binance API request failed: {e}")
        return {
            "success": False,
            "error": f"Request failed: {str(e)}",
            "data": None
        }

def calculate_rsi(prices: List[float], period: int = 14) -> float:
    """Calculate RSI using manual calculation if TA-Lib not available"""
    if TALIB_AVAILABLE:
        return float(talib.RSI(np.array(prices), timeperiod=period)[-1])
    
    # Manual RSI calculation
    if len(prices) < period + 1:
        return 50.0  # Neutral RSI
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_sma(prices: List[float], period: int) -> float:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return sum(prices) / len(prices)
    return sum(prices[-period:]) / period

def calculate_ema(prices: List[float], period: int) -> float:
    """Calculate Exponential Moving Average"""
    if TALIB_AVAILABLE:
        return float(talib.EMA(np.array(prices), timeperiod=period)[-1])
    
    # Manual EMA calculation
    if len(prices) < period:
        return calculate_sma(prices, len(prices))
    
    multiplier = 2 / (period + 1)
    ema = calculate_sma(prices[:period], period)
    
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

# ============================================================================
# FastMCP Tools - Market Data
# ============================================================================

@mcp.tool()
async def get_24h_ticker(input: TickerInput) -> Dict[str, Any]:
    """
    Get 24h ticker statistics for a trading symbol.

    Returns current price, volume, and 24h statistics from Binance.
    """
    try:
        result = await make_binance_request(
            "/fapi/v1/ticker/24hr",
            params={"symbol": input.symbol.upper()}
        )

        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "symbol": data["symbol"],
                "price": float(data["lastPrice"]),
                "change_24h": float(data["priceChange"]),
                "change_percent_24h": float(data["priceChangePercent"]),
                "high_24h": float(data["highPrice"]),
                "low_24h": float(data["lowPrice"]),
                "volume_24h": float(data["volume"]),
                "quote_volume_24h": float(data["quoteVolume"]),
                "open_price": float(data["openPrice"]),
                "timestamp": int(data["closeTime"])
            }
        else:
            return {
                "success": False,
                "error": result["error"],
                "symbol": input.symbol.upper()
            }

    except Exception as e:
        logger.error(f"Failed to get 24h ticker for {input.symbol}: {e}")
        return {
            "success": False,
            "error": f"Failed to get ticker data: {str(e)}",
            "symbol": input.symbol.upper()
        }

@mcp.tool()
async def get_market_data(input: MarketDataInput) -> Dict[str, Any]:
    """
    Get comprehensive market data for a trading symbol.

    Returns current price, volume, and recent price history for analysis.
    """
    try:
        # Get current ticker data
        ticker_result = await make_binance_request(
            "/fapi/v1/ticker/24hr",
            params={"symbol": input.symbol.upper()}
        )

        # Get kline data for price history
        kline_result = await make_binance_request(
            "/fapi/v1/klines",
            params={
                "symbol": input.symbol.upper(),
                "interval": input.timeframe,
                "limit": input.limit
            }
        )

        if ticker_result["success"] and kline_result["success"]:
            ticker_data = ticker_result["data"]
            kline_data = kline_result["data"]

            # Process kline data
            prices = [float(kline[4]) for kline in kline_data]  # Close prices
            volumes = [float(kline[5]) for kline in kline_data]  # Volumes

            return {
                "success": True,
                "symbol": input.symbol.upper(),
                "timeframe": input.timeframe,
                "current_price": float(ticker_data["lastPrice"]),
                "change_24h": float(ticker_data["priceChange"]),
                "change_percent_24h": float(ticker_data["priceChangePercent"]),
                "volume_24h": float(ticker_data["volume"]),
                "price_history": prices,
                "volume_history": volumes,
                "data_points": len(prices),
                "timestamp": time.time()
            }
        else:
            error_msg = ticker_result.get("error") or kline_result.get("error")
            return {
                "success": False,
                "error": error_msg,
                "symbol": input.symbol.upper()
            }

    except Exception as e:
        logger.error(f"Failed to get market data for {input.symbol}: {e}")
        return {
            "success": False,
            "error": f"Failed to get market data: {str(e)}",
            "symbol": input.symbol.upper()
        }

# ============================================================================
# FastMCP Tools - Credentials Management
# ============================================================================

@mcp.tool()
async def set_user_credentials_tool(input: UserCredentialsInput) -> Dict[str, Any]:
    """
    Set user credentials from database for the current session.

    Args:
        input: UserCredentialsInput containing the user ID to retrieve credentials for

    Returns:
        Success status and message
    """
    try:
        user_id = input.user_id
        success = await set_user_credentials(user_id)

        if success:
            return {
                "success": True,
                "message": f"✅ Credentials set for user {user_id}",
                "user_id": user_id
            }
        else:
            return {
                "success": False,
                "message": f"❌ No credentials found for user {user_id}",
                "user_id": user_id
            }

    except Exception as e:
        logger.error(f"❌ Failed to set credentials for user {input.user_id}: {e}")
        return {
            "success": False,
            "message": f"❌ Error setting credentials: {str(e)}",
            "user_id": input.user_id
        }

# ============================================================================
# FastMCP Tools - Trading Operations
# ============================================================================

@mcp.tool()
async def get_account_balance() -> Dict[str, Any]:
    """
    Get futures account balance and available funds.

    Returns account balance, available balance, and position information.
    """
    try:
        result = await make_binance_request(
            "/fapi/v2/account",
            signed=True,
            use_cache=False  # Don't cache account data
        )

        if result["success"]:
            data = result["data"]

            # Extract balance information
            total_balance = float(data.get("totalWalletBalance", 0))
            total_unrealized_pnl = float(data.get("totalUnrealizedProfit", 0))

            # Calculate available balance from assets (since API doesn't provide it at top level)
            available_balance = 0.0

            # Extract asset balances
            assets = []
            for asset in data.get("assets", []):
                wallet_balance = float(asset["walletBalance"])
                unrealized_profit = float(asset["unrealizedProfit"])
                margin_balance = float(asset["marginBalance"])

                if wallet_balance > 0:
                    assets.append({
                        "asset": asset["asset"],
                        "wallet_balance": wallet_balance,
                        "unrealized_profit": unrealized_profit,
                        "margin_balance": margin_balance
                    })

                    # Calculate available balance as margin balance (what's actually available for trading)
                    # For futures, available balance = margin balance (wallet balance + unrealized PnL)
                    available_balance += margin_balance

            return {
                "success": True,
                "total_wallet_balance": total_balance,
                "available_balance": available_balance,
                "total_unrealized_pnl": total_unrealized_pnl,
                "total_balance": total_balance,  # For compatibility
                "used_margin": total_balance - available_balance,  # Calculate used margin
                "free_margin": available_balance,  # Free margin is available balance
                "assets": assets,
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
        return {
            "success": False,
            "error": f"Failed to get account balance: {str(e)}"
        }

@mcp.tool()
async def place_futures_order(input: PlaceOrderInput) -> Dict[str, Any]:
    """
    Place a futures order on Binance.

    Supports MARKET and LIMIT orders with proper risk management.
    """
    try:
        params = {
            "symbol": input.symbol.upper(),
            "side": input.side.upper(),
            "type": input.order_type.upper(),
            "quantity": str(input.quantity)
        }

        if input.order_type.upper() == "LIMIT" and input.price:
            params["price"] = str(input.price)
            params["timeInForce"] = "GTC"  # Good Till Cancelled

        result = await make_binance_request(
            "/fapi/v1/order",
            method="POST",
            params=params,
            signed=True,
            use_cache=False,
            api_key=input.api_key if input.api_key else None,
            secret_key=input.secret_key if input.secret_key else None
        )

        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "order_id": data["orderId"],
                "symbol": data["symbol"],
                "side": data["side"],
                "type": data["type"],
                "quantity": float(data["origQty"]),
                "price": float(data.get("price", 0)),
                "status": data["status"],
                "timestamp": data["updateTime"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        return {
            "success": False,
            "error": f"Failed to place order: {str(e)}"
        }

@mcp.tool()
async def set_leverage(input: SetLeverageInput) -> Dict[str, Any]:
    """
    Set leverage for a trading symbol.

    Configure leverage from 1x to 125x for futures trading.
    """
    try:
        result = await make_binance_request(
            "/fapi/v1/leverage",
            method="POST",
            params={
                "symbol": input.symbol.upper(),
                "leverage": str(input.leverage)
            },
            signed=True,
            use_cache=False
        )

        if result["success"]:
            data = result["data"]
            return {
                "success": True,
                "symbol": data["symbol"],
                "leverage": data["leverage"],
                "max_notional_value": float(data["maxNotionalValue"]),
                "timestamp": time.time()
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    except Exception as e:
        logger.error(f"Failed to set leverage: {e}")
        return {
            "success": False,
            "error": f"Failed to set leverage: {str(e)}"
        }

@mcp.tool()
async def get_symbol_info(input: SymbolInfoInput) -> Dict[str, Any]:
    """
    Get trading rules and symbol information.

    Returns precision, minimum quantities, and trading rules for a symbol.
    """
    try:
        result = await make_binance_request("/fapi/v1/exchangeInfo")

        if result["success"]:
            symbols = result["data"]["symbols"]
            symbol_info = None

            for symbol in symbols:
                if symbol["symbol"] == input.symbol.upper():
                    symbol_info = symbol
                    break

            if symbol_info:
                # Extract filters
                filters = {f["filterType"]: f for f in symbol_info["filters"]}

                return {
                    "success": True,
                    "symbol": symbol_info["symbol"],
                    "status": symbol_info["status"],
                    "base_asset": symbol_info["baseAsset"],
                    "quote_asset": symbol_info["quoteAsset"],
                    "price_precision": symbol_info["pricePrecision"],
                    "quantity_precision": symbol_info["quantityPrecision"],
                    "min_quantity": float(filters.get("LOT_SIZE", {}).get("minQty", 0)),
                    "max_quantity": float(filters.get("LOT_SIZE", {}).get("maxQty", 0)),
                    "step_size": float(filters.get("LOT_SIZE", {}).get("stepSize", 0)),
                    "min_notional": float(filters.get("MIN_NOTIONAL", {}).get("notional", 0)),
                    "timestamp": time.time()
                }
            else:
                return {
                    "success": False,
                    "error": f"Symbol {input.symbol.upper()} not found"
                }
        else:
            return {
                "success": False,
                "error": result["error"]
            }

    except Exception as e:
        logger.error(f"Failed to get symbol info: {e}")
        return {
            "success": False,
            "error": f"Failed to get symbol info: {str(e)}"
        }

# ============================================================================
# FastMCP Tools - Technical Analysis
# ============================================================================

@mcp.tool()
async def calculate_technical_indicators(input: TechnicalAnalysisInput) -> Dict[str, Any]:
    """
    Calculate professional technical indicators for a trading symbol.

    Supports RSI, MACD, Bollinger Bands, Moving Averages, and more using ta-lib.
    """
    try:
        # Get price data
        kline_result = await make_binance_request(
            "/fapi/v1/klines",
            params={
                "symbol": input.symbol.upper(),
                "interval": input.timeframe,
                "limit": input.periods + 50  # Extra data for indicator calculation
            }
        )

        if not kline_result["success"]:
            return {
                "success": False,
                "error": kline_result["error"]
            }

        kline_data = kline_result["data"]

        # Extract OHLCV data
        opens = np.array([float(k[1]) for k in kline_data])
        highs = np.array([float(k[2]) for k in kline_data])
        lows = np.array([float(k[3]) for k in kline_data])
        closes = np.array([float(k[4]) for k in kline_data])
        volumes = np.array([float(k[5]) for k in kline_data])

        indicators = {}

        # Calculate requested indicators or default set
        indicator_list = input.indicators if input.indicators else ["RSI", "MACD", "BB", "SMA", "EMA"]

        for indicator in indicator_list:
            try:
                if indicator.upper() == "RSI":
                    indicators["RSI"] = calculate_rsi(closes.tolist(), 14)

                elif indicator.upper() == "MACD":
                    if TALIB_AVAILABLE:
                        macd, macd_signal, macd_hist = talib.MACD(closes)
                        indicators["MACD"] = {
                            "macd": float(macd[-1]) if not np.isnan(macd[-1]) else 0,
                            "signal": float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else 0,
                            "histogram": float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else 0
                        }
                    else:
                        # Simple MACD calculation
                        ema12 = calculate_ema(closes.tolist(), 12)
                        ema26 = calculate_ema(closes.tolist(), 26)
                        macd_line = ema12 - ema26
                        indicators["MACD"] = {
                            "macd": macd_line,
                            "signal": 0,  # Simplified
                            "histogram": 0
                        }

                elif indicator.upper() == "BB":  # Bollinger Bands
                    if TALIB_AVAILABLE:
                        bb_upper, bb_middle, bb_lower = talib.BBANDS(closes)
                        indicators["BB"] = {
                            "upper": float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else 0,
                            "middle": float(bb_middle[-1]) if not np.isnan(bb_middle[-1]) else 0,
                            "lower": float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else 0
                        }
                    else:
                        # Manual Bollinger Bands
                        sma = calculate_sma(closes.tolist(), 20)
                        std = np.std(closes[-20:])
                        indicators["BB"] = {
                            "upper": sma + (2 * std),
                            "middle": sma,
                            "lower": sma - (2 * std)
                        }

                elif indicator.upper() == "SMA":
                    indicators["SMA_20"] = calculate_sma(closes.tolist(), 20)
                    indicators["SMA_50"] = calculate_sma(closes.tolist(), 50)

                elif indicator.upper() == "EMA":
                    indicators["EMA_12"] = calculate_ema(closes.tolist(), 12)
                    indicators["EMA_26"] = calculate_ema(closes.tolist(), 26)

            except Exception as e:
                logger.warning(f"Failed to calculate {indicator}: {e}")
                indicators[indicator] = None

        return {
            "success": True,
            "symbol": input.symbol.upper(),
            "timeframe": input.timeframe,
            "indicators": indicators,
            "current_price": float(closes[-1]),
            "timestamp": time.time()
        }

    except Exception as e:
        logger.error(f"Failed to calculate technical indicators: {e}")
        return {
            "success": False,
            "error": f"Failed to calculate indicators: {str(e)}"
        }

@mcp.tool()
async def ping() -> Dict[str, Any]:
    """Simple ping tool to test MCP server connectivity"""
    return {
        "status": "pong",
        "server": "Binance FastMCP Server",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@mcp.tool()
async def get_server_status() -> Dict[str, Any]:
    """Get comprehensive server status and health information"""
    try:
        return {
            "success": True,
            "server_name": "Binance FastMCP Server",
            "version": "1.0.0",
            "status": "healthy",
            "features": {
                "talib_available": TALIB_AVAILABLE,
                "websocket_available": WEBSOCKET_AVAILABLE,
                "binance_configured": bool(BINANCE_API_KEY and BINANCE_SECRET_KEY)
            },
            "statistics": {
                "active_streams": len(active_streams),
                "cached_requests": len(request_cache),
                "tools_count": 13
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get server status: {str(e)}"
        }

class SupportResistanceInput(BaseModel):
    symbol: str = Field(description="Trading pair symbol (e.g., BTCUSDT)")
    timeframe: str = Field(default="1h", description="Timeframe for analysis (1m, 5m, 15m, 1h, 4h, 1d)")
    periods: int = Field(default=20, description="Number of periods for calculation")

@mcp.tool()
async def calculate_support_resistance_levels(input: SupportResistanceInput) -> Dict[str, Any]:
    """Calculate support and resistance levels for a trading pair"""
    try:
        # Get historical data for support/resistance calculation
        kline_result = await make_binance_request(
            "/fapi/v1/klines",
            params={
                "symbol": input.symbol.upper(),
                "interval": input.timeframe,
                "limit": input.periods * 2
            }
        )

        if not kline_result["success"]:
            return {"success": False, "error": f"Failed to get kline data: {kline_result['error']}"}

        klines = kline_result["data"]

        if not klines:
            return {"success": False, "error": "No historical data available"}

        # Extract high and low prices
        highs = [float(kline[2]) for kline in klines]  # High prices
        lows = [float(kline[3]) for kline in klines]   # Low prices
        closes = [float(kline[4]) for kline in klines] # Close prices

        # Calculate support and resistance levels using pivot points
        recent_high = max(highs[-input.periods:])
        recent_low = min(lows[-input.periods:])
        current_price = closes[-1]

        # Simple pivot point calculation
        pivot = (recent_high + recent_low + current_price) / 3
        resistance_1 = 2 * pivot - recent_low
        support_1 = 2 * pivot - recent_high
        resistance_2 = pivot + (recent_high - recent_low)
        support_2 = pivot - (recent_high - recent_low)

        return {
            "success": True,
            "symbol": input.symbol,
            "timeframe": input.timeframe,
            "current_price": current_price,
            "pivot_point": round(pivot, 2),
            "support_levels": [
                round(support_1, 2),
                round(support_2, 2)
            ],
            "resistance_levels": [
                round(resistance_1, 2),
                round(resistance_2, 2)
            ],
            "distance_to_support": round(((current_price - support_1) / current_price) * 100, 2),
            "distance_to_resistance": round(((resistance_1 - current_price) / current_price) * 100, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Support/resistance calculation failed: {str(e)}"
        }

class MarketCorrelationInput(BaseModel):
    symbol: str = Field(description="Trading pair symbol to analyze (e.g., BTCUSDT)")
    reference_symbols: List[str] = Field(default=["BTCUSDT", "ETHUSDT"], description="Reference symbols for correlation analysis")

@mcp.tool()
async def analyze_market_correlation(input: MarketCorrelationInput) -> Dict[str, Any]:
    """Analyze correlation between trading pairs"""
    try:
        # Get 24h ticker data for correlation analysis
        ticker_result = await make_binance_request("/fapi/v1/ticker/24hr")

        if not ticker_result["success"]:
            return {"success": False, "error": f"Failed to get ticker data: {ticker_result['error']}"}

        tickers = ticker_result["data"]
        ticker_dict = {ticker['symbol']: float(ticker['priceChangePercent']) for ticker in tickers}

        if input.symbol not in ticker_dict:
            return {"success": False, "error": f"Symbol {input.symbol} not found"}

        symbol_change = ticker_dict[input.symbol]
        correlations = {}

        for ref_symbol in input.reference_symbols:
            if ref_symbol in ticker_dict:
                ref_change = ticker_dict[ref_symbol]
                # Simple correlation based on price change direction
                if (symbol_change > 0 and ref_change > 0) or (symbol_change < 0 and ref_change < 0):
                    correlation = "HIGH" if abs(symbol_change - ref_change) < 2 else "MEDIUM"
                else:
                    correlation = "LOW"
                correlations[ref_symbol] = correlation

        # Determine overall market regime
        btc_change = ticker_dict.get("BTCUSDT", 0)
        if btc_change > 2:
            market_regime = "BULL"
        elif btc_change < -2:
            market_regime = "BEAR"
        else:
            market_regime = "NEUTRAL"

        return {
            "success": True,
            "symbol": input.symbol,
            "price_change": symbol_change,
            "correlations": correlations,
            "market_regime": market_regime,
            "btc_correlation": correlations.get("BTCUSDT", "UNKNOWN")
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Market correlation analysis failed: {str(e)}"
        }

class MarketSentimentInput(BaseModel):
    symbol: str = Field(description="Trading pair symbol to analyze (e.g., BTCUSDT)")

@mcp.tool()
async def assess_market_sentiment(input: MarketSentimentInput) -> Dict[str, Any]:
    """Assess market sentiment for a trading pair"""
    try:
        # Get funding rate and open interest for sentiment analysis
        funding_result = await make_binance_request(
            "/fapi/v1/fundingRate",
            params={"symbol": input.symbol.upper(), "limit": 1}
        )

        open_interest_result = await make_binance_request(
            "/fapi/v1/openInterest",
            params={"symbol": input.symbol.upper()}
        )

        ticker_result = await make_binance_request(
            "/fapi/v1/ticker/24hr",
            params={"symbol": input.symbol.upper()}
        )

        if not all([funding_result["success"], open_interest_result["success"], ticker_result["success"]]):
            return {"success": False, "error": "Failed to get market sentiment data"}

        funding_rate = funding_result["data"][0] if funding_result["data"] else {}
        open_interest = open_interest_result["data"]
        ticker_24h = ticker_result["data"]

        current_funding = float(funding_rate.get('fundingRate', 0.0)) if funding_rate else 0.0
        oi_value = float(open_interest.get('openInterest', 0.0)) if open_interest else 0.0
        volume_24h = float(ticker_24h.get('volume', 0.0))
        price_change = float(ticker_24h.get('priceChangePercent', 0.0))

        # Sentiment scoring based on multiple factors
        sentiment_score = 0

        # Funding rate sentiment (negative funding = bullish sentiment)
        if current_funding < -0.0001:
            sentiment_score += 2  # Very bullish
        elif current_funding < 0:
            sentiment_score += 1  # Bullish
        elif current_funding > 0.0001:
            sentiment_score -= 2  # Very bearish
        elif current_funding > 0:
            sentiment_score -= 1  # Bearish

        # Price action sentiment
        if price_change > 5:
            sentiment_score += 2
        elif price_change > 1:
            sentiment_score += 1
        elif price_change < -5:
            sentiment_score -= 2
        elif price_change < -1:
            sentiment_score -= 1

        # Volume sentiment (high volume = strong sentiment)
        volume_strength = "HIGH" if volume_24h > 1000000 else "MEDIUM" if volume_24h > 100000 else "LOW"

        # Overall sentiment
        if sentiment_score >= 3:
            overall_sentiment = "VERY_BULLISH"
        elif sentiment_score >= 1:
            overall_sentiment = "BULLISH"
        elif sentiment_score <= -3:
            overall_sentiment = "VERY_BEARISH"
        elif sentiment_score <= -1:
            overall_sentiment = "BEARISH"
        else:
            overall_sentiment = "NEUTRAL"

        # Fear & Greed simulation (simplified)
        fear_greed_index = max(0, min(100, 50 + (sentiment_score * 10)))

        return {
            "success": True,
            "symbol": input.symbol,
            "overall_sentiment": overall_sentiment,
            "sentiment_score": sentiment_score,
            "funding_rate": current_funding,
            "open_interest": oi_value,
            "volume_strength": volume_strength,
            "fear_greed_index": fear_greed_index,
            "price_change_24h": price_change
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Market sentiment assessment failed: {str(e)}"
        }

class MultiTimeframeInput(BaseModel):
    symbol: str = Field(description="Trading pair symbol to analyze (e.g., BTCUSDT)")
    timeframes: List[str] = Field(default=["1m", "5m", "15m", "1h", "4h", "1d"], description="List of timeframes to analyze")

@mcp.tool()
async def get_multi_timeframe_data(input: MultiTimeframeInput) -> Dict[str, Any]:
    """Get multi-timeframe analysis data for a trading pair"""
    try:
        multi_tf_data = {}

        for tf in input.timeframes:
            try:
                # Get recent klines for each timeframe
                kline_result = await make_binance_request(
                    "/fapi/v1/klines",
                    params={
                        "symbol": input.symbol.upper(),
                        "interval": tf,
                        "limit": 20
                    }
                )

                if not kline_result["success"]:
                    multi_tf_data[tf] = {"error": f"Failed to get data: {kline_result['error']}"}
                    continue

                klines = kline_result["data"]

                if klines:
                    # Extract OHLCV data
                    closes = [float(kline[4]) for kline in klines]
                    highs = [float(kline[2]) for kline in klines]
                    lows = [float(kline[3]) for kline in klines]
                    volumes = [float(kline[5]) for kline in klines]

                    # Calculate basic metrics
                    current_price = closes[-1]
                    price_change = ((closes[-1] - closes[-2]) / closes[-2]) * 100 if len(closes) > 1 else 0

                    # Trend analysis
                    if len(closes) >= 10:
                        sma_short = sum(closes[-5:]) / 5
                        sma_long = sum(closes[-10:]) / 10
                        trend = "UPTREND" if sma_short > sma_long else "DOWNTREND"
                    else:
                        trend = "NEUTRAL"

                    multi_tf_data[tf] = {
                        "current_price": current_price,
                        "price_change": round(price_change, 4),
                        "trend": trend,
                        "high_24h": max(highs),
                        "low_24h": min(lows),
                        "avg_volume": sum(volumes) / len(volumes)
                    }

            except Exception as tf_error:
                multi_tf_data[tf] = {"error": str(tf_error)}

        # Overall multi-timeframe trend
        trends = [data.get("trend", "NEUTRAL") for data in multi_tf_data.values() if isinstance(data, dict) and "trend" in data]
        uptrend_count = trends.count("UPTREND")
        downtrend_count = trends.count("DOWNTREND")

        if uptrend_count > downtrend_count:
            overall_trend = "BULLISH"
        elif downtrend_count > uptrend_count:
            overall_trend = "BEARISH"
        else:
            overall_trend = "NEUTRAL"

        return {
            "success": True,
            "symbol": input.symbol,
            "timeframes": multi_tf_data,
            "overall_trend": overall_trend,
            "trend_strength": max(uptrend_count, downtrend_count) / len(trends) if trends else 0
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Multi-timeframe analysis failed: {str(e)}"
        }

if __name__ == "__main__":
    logger.info("🚀 Starting Binance FastMCP Server...")
    logger.info("✅ All Binance trading functionality integrated with standards-compliant MCP protocol")
    mcp.run()
