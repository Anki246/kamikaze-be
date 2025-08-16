#!/usr/bin/env python3
"""
Professional Technical Analysis MCP Server - TRUE MCP Protocol Implementation
Provides professional-grade technical analysis tools for FluxTrader

Features:
- Multi-timeframe Support/Resistance levels using pivot points, Fibonacci retracements, and volume profile
- Comprehensive market correlation analysis across multiple assets (BTC, ETH, major indices)
- Real multi-timeframe analysis (1m, 5m, 15m, 1h, 4h, 1d)
- Professional technical indicators (RSI, MACD, Bollinger Bands, Moving Averages)
- Market sentiment assessment (Fear/Greed index, funding rates, open interest)
- TRUE MCP protocol with JSON-RPC 2.0 communication
- Professional-grade error handling and retry logic
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import numpy as np
import pandas as pd

# Optional MCP Protocol imports - gracefully handle if not available
try:
    import mcp.types as types
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.types import (
        EmbeddedResource,
        ImageContent,
        LoggingLevel,
        Resource,
        TextContent,
        Tool,
    )

    MCP_AVAILABLE = True
except ImportError:
    # Mock MCP classes if not available
    class InitializationOptions:
        pass

    class NotificationOptions:
        pass

    class Server:
        pass

    class Resource:
        pass

    class Tool:
        pass

    class TextContent:
        pass

    class ImageContent:
        pass

    class EmbeddedResource:
        pass

    class LoggingLevel:
        pass

    class types:
        pass

    MCP_AVAILABLE = False
    print("⚠️  MCP package not available - using mock classes")

# Technical Analysis Libraries
try:
    import talib

    TALIB_AVAILABLE = True
    print("✅ TA-Lib loaded successfully")
except ImportError:
    TALIB_AVAILABLE = False
    print("⚠️  TA-Lib not available - using manual technical analysis calculations")

# Note: Removed 'ta' library dependency - using TA-Lib as primary and manual calculations as fallback

# Market data sources
try:
    import ccxt
    import yfinance as yf

    MARKET_DATA_AVAILABLE = True
except ImportError:
    MARKET_DATA_AVAILABLE = False
    print("⚠️  Market data libraries not available")

# Web scraping for sentiment
try:
    import requests
    from bs4 import BeautifulSoup

    WEB_SCRAPING_AVAILABLE = True
except ImportError:
    WEB_SCRAPING_AVAILABLE = False
    print("⚠️  Web scraping libraries not available")

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalAnalysisMCPServer:
    """
    Professional Technical Analysis MCP Server
    Implements TRUE MCP protocol with JSON-RPC 2.0 communication
    """

    def __init__(self):
        self.server = Server("technical-analysis-mcp-server")
        self.binance_api_key = os.getenv("BINANCE_API_KEY")
        self.binance_secret_key = os.getenv("BINANCE_SECRET_KEY")
        self.alpha_vantage_key = os.getenv("ALPHA_VANTAGE_API_KEY")

        # Market data cache
        self.price_cache = {}
        self.cache_expiry = {}
        self.cache_duration = 60  # 1 minute cache

        # Setup MCP tools
        self._setup_tools()

        logger.info("🔧 Technical Analysis MCP Server initialized")

    def _setup_tools(self):
        """Setup all MCP tools for professional technical analysis."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List all available Technical Analysis MCP tools."""
            return [
                Tool(
                    name="calculate_support_resistance_levels",
                    description="Calculate multi-timeframe support and resistance levels using pivot points, Fibonacci retracements, and volume profile",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTCUSDT)",
                            },
                            "timeframes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of timeframes to analyze (e.g., ['1h', '4h', '1d'])",
                                "default": ["1h", "4h", "1d"],
                            },
                            "lookback_periods": {
                                "type": "integer",
                                "description": "Number of periods to look back for analysis",
                                "default": 100,
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
                Tool(
                    name="analyze_market_correlation",
                    description="Comprehensive correlation analysis across multiple assets (BTC, ETH, major indices)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "primary_symbol": {
                                "type": "string",
                                "description": "Primary trading pair to analyze (e.g., BTCUSDT)",
                            },
                            "correlation_assets": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Assets to correlate against",
                                "default": ["ETHUSDT", "BNBUSDT", "SPY", "QQQ", "DXY"],
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Timeframe for correlation analysis",
                                "default": "1d",
                            },
                            "periods": {
                                "type": "integer",
                                "description": "Number of periods for correlation calculation",
                                "default": 30,
                            },
                        },
                        "required": ["primary_symbol"],
                    },
                ),
                Tool(
                    name="get_multi_timeframe_data",
                    description="Real multi-timeframe analysis (1m, 5m, 15m, 1h, 4h, 1d) with OHLCV data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTCUSDT)",
                            },
                            "timeframes": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of timeframes to fetch",
                                "default": ["1m", "5m", "15m", "1h", "4h", "1d"],
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of candles per timeframe",
                                "default": 100,
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
                Tool(
                    name="calculate_technical_indicators",
                    description="Calculate professional technical indicators (RSI, MACD, Bollinger Bands, Moving Averages) across timeframes",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTCUSDT)",
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Timeframe for indicator calculation",
                                "default": "1h",
                            },
                            "indicators": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of indicators to calculate",
                                "default": ["RSI", "MACD", "BB", "SMA", "EMA", "STOCH"],
                            },
                            "periods": {
                                "type": "integer",
                                "description": "Number of periods for calculation",
                                "default": 100,
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
                Tool(
                    name="assess_market_sentiment",
                    description="Assess market sentiment using Fear/Greed index, funding rates, and open interest analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading pair symbol (e.g., BTCUSDT)",
                            },
                            "include_fear_greed": {
                                "type": "boolean",
                                "description": "Include Fear & Greed index",
                                "default": True,
                            },
                            "include_funding_rates": {
                                "type": "boolean",
                                "description": "Include funding rates analysis",
                                "default": True,
                            },
                            "include_open_interest": {
                                "type": "boolean",
                                "description": "Include open interest analysis",
                                "default": True,
                            },
                        },
                        "required": ["symbol"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict
        ) -> list[types.TextContent]:
            """Handle MCP tool calls with proper JSON-RPC 2.0 response."""
            try:
                logger.info(f"🔧 Technical Analysis MCP Tool Called: {name}")

                if name == "calculate_support_resistance_levels":
                    result = await self._calculate_support_resistance_levels(
                        arguments["symbol"],
                        arguments.get("timeframes", ["1h", "4h", "1d"]),
                        arguments.get("lookback_periods", 100),
                    )
                elif name == "analyze_market_correlation":
                    result = await self._analyze_market_correlation(
                        arguments["primary_symbol"],
                        arguments.get(
                            "correlation_assets",
                            ["ETHUSDT", "BNBUSDT", "SPY", "QQQ", "DXY"],
                        ),
                        arguments.get("timeframe", "1d"),
                        arguments.get("periods", 30),
                    )
                elif name == "get_multi_timeframe_data":
                    result = await self._get_multi_timeframe_data(
                        arguments["symbol"],
                        arguments.get(
                            "timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"]
                        ),
                        arguments.get("limit", 100),
                    )
                elif name == "calculate_technical_indicators":
                    result = await self._calculate_technical_indicators(
                        arguments["symbol"],
                        arguments.get("timeframe", "1h"),
                        arguments.get(
                            "indicators", ["RSI", "MACD", "BB", "SMA", "EMA", "STOCH"]
                        ),
                        arguments.get("periods", 100),
                    )
                elif name == "assess_market_sentiment":
                    result = await self._assess_market_sentiment(
                        arguments["symbol"],
                        arguments.get("include_fear_greed", True),
                        arguments.get("include_funding_rates", True),
                        arguments.get("include_open_interest", True),
                    )
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown tool: {name}",
                        "tool_name": name,
                    }

                return [
                    types.TextContent(type="text", text=json.dumps(result, indent=2))
                ]

            except Exception as e:
                logger.error(f"❌ Technical Analysis MCP Tool Error: {str(e)}")
                error_result = {
                    "success": False,
                    "error": str(e),
                    "tool_name": name,
                    "timestamp": datetime.now().isoformat(),
                }
                return [
                    types.TextContent(
                        type="text", text=json.dumps(error_result, indent=2)
                    )
                ]

    async def _get_binance_klines(
        self, symbol: str, interval: str, limit: int = 100
    ) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Binance API."""
        try:
            url = "https://api.binance.com/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Convert to DataFrame
                        df = pd.DataFrame(
                            data,
                            columns=[
                                "timestamp",
                                "open",
                                "high",
                                "low",
                                "close",
                                "volume",
                                "close_time",
                                "quote_asset_volume",
                                "number_of_trades",
                                "taker_buy_base_asset_volume",
                                "taker_buy_quote_asset_volume",
                                "ignore",
                            ],
                        )

                        # Convert to proper types
                        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                        for col in ["open", "high", "low", "close", "volume"]:
                            df[col] = pd.to_numeric(df[col])

                        return df
                    else:
                        logger.error(f"❌ Binance API error: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"❌ Error fetching Binance data: {str(e)}")
            return None

    async def _calculate_support_resistance_levels(
        self, symbol: str, timeframes: List[str], lookback_periods: int
    ) -> Dict[str, Any]:
        """Calculate multi-timeframe support and resistance levels."""
        try:
            logger.info(f"📊 Calculating S/R levels for {symbol} across {timeframes}")

            results = {
                "success": True,
                "symbol": symbol,
                "timeframes": {},
                "consolidated_levels": [],
                "timestamp": datetime.now().isoformat(),
            }

            all_levels = []

            for timeframe in timeframes:
                # Get OHLCV data
                df = await self._get_binance_klines(symbol, timeframe, lookback_periods)
                if df is None:
                    continue

                # Calculate pivot points
                pivot_levels = self._calculate_pivot_points(df)

                # Calculate Fibonacci retracements
                fib_levels = self._calculate_fibonacci_levels(df)

                # Calculate volume profile levels
                volume_levels = self._calculate_volume_profile(df)

                # Combine all levels for this timeframe
                timeframe_levels = {
                    "pivot_points": pivot_levels,
                    "fibonacci_levels": fib_levels,
                    "volume_profile": volume_levels,
                    "current_price": float(df["close"].iloc[-1]),
                }

                results["timeframes"][timeframe] = timeframe_levels

                # Add to consolidated levels with weights
                weight = {"1m": 1, "5m": 2, "15m": 3, "1h": 4, "4h": 5, "1d": 6}.get(
                    timeframe, 3
                )
                for level_type, levels in timeframe_levels.items():
                    if isinstance(levels, list):
                        for level in levels:
                            all_levels.append(
                                {
                                    "price": level,
                                    "type": level_type,
                                    "timeframe": timeframe,
                                    "weight": weight,
                                }
                            )

            # Consolidate levels by clustering nearby prices
            results["consolidated_levels"] = self._consolidate_levels(all_levels)

            return results

        except Exception as e:
            logger.error(f"❌ Error calculating S/R levels: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

    def _calculate_pivot_points(self, df: pd.DataFrame) -> List[float]:
        """Calculate pivot points from OHLC data."""
        try:
            high = df["high"].iloc[-1]
            low = df["low"].iloc[-1]
            close = df["close"].iloc[-1]

            # Standard pivot point
            pivot = (high + low + close) / 3

            # Support and resistance levels
            r1 = 2 * pivot - low
            s1 = 2 * pivot - high
            r2 = pivot + (high - low)
            s2 = pivot - (high - low)
            r3 = high + 2 * (pivot - low)
            s3 = low - 2 * (high - pivot)

            return [float(level) for level in [s3, s2, s1, pivot, r1, r2, r3]]

        except Exception as e:
            logger.error(f"❌ Error calculating pivot points: {str(e)}")
            return []

    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> List[float]:
        """Calculate Fibonacci retracement levels."""
        try:
            # Find recent swing high and low
            high_idx = df["high"].rolling(window=20).max().idxmax()
            low_idx = df["low"].rolling(window=20).min().idxmin()

            swing_high = df.loc[high_idx, "high"]
            swing_low = df.loc[low_idx, "low"]

            # Fibonacci ratios
            fib_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]

            # Calculate levels
            diff = swing_high - swing_low
            levels = []

            for ratio in fib_ratios:
                level = swing_low + (diff * ratio)
                levels.append(float(level))

            return levels

        except Exception as e:
            logger.error(f"❌ Error calculating Fibonacci levels: {str(e)}")
            return []

    def _calculate_volume_profile(self, df: pd.DataFrame) -> List[float]:
        """Calculate volume profile levels."""
        try:
            # Create price bins
            price_range = df["high"].max() - df["low"].min()
            num_bins = 20
            bin_size = price_range / num_bins

            # Calculate volume at each price level
            volume_profile = {}

            for _, row in df.iterrows():
                # Distribute volume across the price range of the candle
                candle_range = row["high"] - row["low"]
                if candle_range > 0:
                    volume_per_price = row["volume"] / candle_range

                    # Add volume to each price bin this candle touches
                    start_bin = int((row["low"] - df["low"].min()) / bin_size)
                    end_bin = int((row["high"] - df["low"].min()) / bin_size)

                    for bin_idx in range(start_bin, end_bin + 1):
                        price_level = df["low"].min() + (bin_idx * bin_size)
                        if price_level not in volume_profile:
                            volume_profile[price_level] = 0
                        volume_profile[price_level] += volume_per_price

            # Get top volume levels
            sorted_levels = sorted(
                volume_profile.items(), key=lambda x: x[1], reverse=True
            )
            top_levels = [float(level[0]) for level in sorted_levels[:10]]

            return top_levels

        except Exception as e:
            logger.error(f"❌ Error calculating volume profile: {str(e)}")
            return []

    def _consolidate_levels(self, all_levels: List[Dict]) -> List[Dict]:
        """Consolidate nearby support/resistance levels."""
        try:
            if not all_levels:
                return []

            # Sort by price
            sorted_levels = sorted(all_levels, key=lambda x: x["price"])

            consolidated = []
            current_cluster = [sorted_levels[0]]

            for level in sorted_levels[1:]:
                # If price is within 0.5% of the current cluster, add to cluster
                cluster_avg = sum(l["price"] for l in current_cluster) / len(
                    current_cluster
                )
                if abs(level["price"] - cluster_avg) / cluster_avg < 0.005:
                    current_cluster.append(level)
                else:
                    # Finalize current cluster
                    if current_cluster:
                        consolidated.append(self._finalize_cluster(current_cluster))
                    current_cluster = [level]

            # Don't forget the last cluster
            if current_cluster:
                consolidated.append(self._finalize_cluster(current_cluster))

            # Sort by strength (weight)
            consolidated.sort(key=lambda x: x["strength"], reverse=True)

            return consolidated[:15]  # Return top 15 levels

        except Exception as e:
            logger.error(f"❌ Error consolidating levels: {str(e)}")
            return []

    def _finalize_cluster(self, cluster: List[Dict]) -> Dict:
        """Finalize a cluster of support/resistance levels."""
        avg_price = sum(l["price"] for l in cluster) / len(cluster)
        total_weight = sum(l["weight"] for l in cluster)

        # Determine if it's support or resistance based on current price context
        level_types = [l["type"] for l in cluster]
        timeframes = list(set(l["timeframe"] for l in cluster))

        return {
            "price": round(avg_price, 8),
            "strength": total_weight,
            "count": len(cluster),
            "types": level_types,
            "timeframes": timeframes,
            "confidence": min(100, total_weight * 10),  # Scale to 0-100
        }

    async def _analyze_market_correlation(
        self,
        primary_symbol: str,
        correlation_assets: List[str],
        timeframe: str,
        periods: int,
    ) -> Dict[str, Any]:
        """Analyze market correlation across multiple assets."""
        try:
            logger.info(
                f"📈 Analyzing correlation for {primary_symbol} vs {correlation_assets}"
            )

            results = {
                "success": True,
                "primary_symbol": primary_symbol,
                "timeframe": timeframe,
                "periods": periods,
                "correlations": {},
                "market_regime": "UNKNOWN",
                "timestamp": datetime.now().isoformat(),
            }

            # Get primary asset data
            primary_df = await self._get_binance_klines(
                primary_symbol, timeframe, periods
            )
            if primary_df is None:
                raise Exception(f"Failed to fetch data for {primary_symbol}")

            primary_returns = primary_df["close"].pct_change().dropna()

            correlations = []

            for asset in correlation_assets:
                try:
                    # Handle different asset types
                    if asset.endswith("USDT"):
                        # Crypto asset - use Binance
                        asset_df = await self._get_binance_klines(
                            asset, timeframe, periods
                        )
                        if asset_df is not None:
                            asset_returns = asset_df["close"].pct_change().dropna()
                        else:
                            continue
                    else:
                        # Traditional asset - use yfinance if available
                        if MARKET_DATA_AVAILABLE:
                            asset_data = await self._get_traditional_asset_data(
                                asset, periods
                            )
                            if asset_data is not None:
                                asset_returns = asset_data.pct_change().dropna()
                            else:
                                continue
                        else:
                            continue

                    # Calculate correlation
                    if len(primary_returns) > 0 and len(asset_returns) > 0:
                        # Align the series
                        min_length = min(len(primary_returns), len(asset_returns))
                        correlation = np.corrcoef(
                            primary_returns.tail(min_length),
                            asset_returns.tail(min_length),
                        )[0, 1]

                        if not np.isnan(correlation):
                            correlations.append(correlation)
                            results["correlations"][asset] = {
                                "correlation": round(float(correlation), 4),
                                "strength": self._interpret_correlation_strength(
                                    correlation
                                ),
                                "direction": "positive"
                                if correlation > 0
                                else "negative",
                            }

                except Exception as e:
                    logger.warning(
                        f"⚠️  Failed to analyze correlation with {asset}: {str(e)}"
                    )
                    continue

            # Determine market regime
            if correlations:
                avg_correlation = np.mean([abs(c) for c in correlations])
                if avg_correlation > 0.7:
                    results["market_regime"] = "HIGH_CORRELATION"
                elif avg_correlation > 0.4:
                    results["market_regime"] = "MODERATE_CORRELATION"
                else:
                    results["market_regime"] = "LOW_CORRELATION"

            return results

        except Exception as e:
            logger.error(f"❌ Error analyzing market correlation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "primary_symbol": primary_symbol,
                "timestamp": datetime.now().isoformat(),
            }

    def _interpret_correlation_strength(self, correlation: float) -> str:
        """Interpret correlation strength."""
        abs_corr = abs(correlation)
        if abs_corr >= 0.8:
            return "VERY_STRONG"
        elif abs_corr >= 0.6:
            return "STRONG"
        elif abs_corr >= 0.4:
            return "MODERATE"
        elif abs_corr >= 0.2:
            return "WEAK"
        else:
            return "VERY_WEAK"

    async def _get_traditional_asset_data(
        self, symbol: str, periods: int
    ) -> Optional[pd.Series]:
        """Get traditional asset data using yfinance."""
        try:
            if not MARKET_DATA_AVAILABLE:
                return None

            # Map common symbols
            symbol_map = {
                "SPY": "SPY",
                "QQQ": "QQQ",
                "DXY": "DX-Y.NYB",
                "GOLD": "GC=F",
                "OIL": "CL=F",
            }

            yf_symbol = symbol_map.get(symbol, symbol)
            ticker = yf.Ticker(yf_symbol)

            # Get historical data
            hist = ticker.history(period=f"{periods}d")
            if not hist.empty:
                return hist["Close"]

            return None

        except Exception as e:
            logger.error(
                f"❌ Error fetching traditional asset data for {symbol}: {str(e)}"
            )
            return None

    async def _get_multi_timeframe_data(
        self, symbol: str, timeframes: List[str], limit: int
    ) -> Dict[str, Any]:
        """Get real multi-timeframe OHLCV data."""
        try:
            logger.info(f"📊 Fetching multi-timeframe data for {symbol}: {timeframes}")

            results = {
                "success": True,
                "symbol": symbol,
                "timeframes": {},
                "timestamp": datetime.now().isoformat(),
            }

            for timeframe in timeframes:
                df = await self._get_binance_klines(symbol, timeframe, limit)
                if df is not None:
                    # Convert DataFrame to dict for JSON serialization
                    timeframe_data = {
                        "candles": df.tail(limit).to_dict("records"),
                        "current_price": float(df["close"].iloc[-1]),
                        "24h_change": float(
                            (df["close"].iloc[-1] - df["close"].iloc[-25])
                            / df["close"].iloc[-25]
                            * 100
                        )
                        if len(df) >= 25
                        else 0,
                        "volume_24h": float(df["volume"].tail(24).sum())
                        if len(df) >= 24
                        else float(df["volume"].sum()),
                        "high_24h": float(df["high"].tail(24).max())
                        if len(df) >= 24
                        else float(df["high"].max()),
                        "low_24h": float(df["low"].tail(24).min())
                        if len(df) >= 24
                        else float(df["low"].min()),
                    }

                    # Convert timestamps to ISO format
                    for candle in timeframe_data["candles"]:
                        if "timestamp" in candle:
                            candle["timestamp"] = candle["timestamp"].isoformat()

                    results["timeframes"][timeframe] = timeframe_data
                else:
                    logger.warning(f"⚠️  Failed to fetch {timeframe} data for {symbol}")

            return results

        except Exception as e:
            logger.error(f"❌ Error fetching multi-timeframe data: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

    async def _calculate_technical_indicators(
        self, symbol: str, timeframe: str, indicators: List[str], periods: int
    ) -> Dict[str, Any]:
        """Calculate professional technical indicators."""
        try:
            logger.info(
                f"📊 Calculating technical indicators for {symbol} ({timeframe}): {indicators}"
            )

            results = {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": {},
                "signals": {},
                "timestamp": datetime.now().isoformat(),
            }

            # Get OHLCV data
            df = await self._get_binance_klines(symbol, timeframe, periods)
            if df is None:
                raise Exception(f"Failed to fetch data for {symbol}")

            # Calculate each requested indicator
            for indicator in indicators:
                try:
                    if indicator.upper() == "RSI":
                        rsi_values = self._calculate_rsi(df)
                        if rsi_values is not None:
                            current_rsi = float(rsi_values.iloc[-1])
                            results["indicators"]["RSI"] = {
                                "current": current_rsi,
                                "values": rsi_values.tail(20).tolist(),
                                "overbought": current_rsi > 70,
                                "oversold": current_rsi < 30,
                                "signal": "BUY"
                                if current_rsi < 30
                                else "SELL"
                                if current_rsi > 70
                                else "NEUTRAL",
                            }

                    elif indicator.upper() == "MACD":
                        macd_data = self._calculate_macd(df)
                        if macd_data is not None:
                            results["indicators"]["MACD"] = macd_data

                    elif indicator.upper() == "BB":
                        bb_data = self._calculate_bollinger_bands(df)
                        if bb_data is not None:
                            results["indicators"]["BOLLINGER_BANDS"] = bb_data

                    elif indicator.upper() in ["SMA", "EMA"]:
                        ma_data = self._calculate_moving_averages(df, indicator.upper())
                        if ma_data is not None:
                            results["indicators"][f"{indicator.upper()}_20"] = ma_data[
                                "20"
                            ]
                            results["indicators"][f"{indicator.upper()}_50"] = ma_data[
                                "50"
                            ]

                    elif indicator.upper() == "STOCH":
                        stoch_data = self._calculate_stochastic(df)
                        if stoch_data is not None:
                            results["indicators"]["STOCHASTIC"] = stoch_data

                except Exception as e:
                    logger.warning(f"⚠️  Failed to calculate {indicator}: {str(e)}")
                    continue

            # Generate overall signal
            results["signals"]["overall"] = self._generate_overall_signal(
                results["indicators"]
            )

            return results

        except Exception as e:
            logger.error(f"❌ Error calculating technical indicators: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[pd.Series]:
        """Calculate RSI using TA-Lib or manual calculation."""
        try:
            if TALIB_AVAILABLE:
                return pd.Series(
                    talib.RSI(df["close"].values, timeperiod=period), index=df.index
                )
            else:
                # Manual RSI calculation
                delta = df["close"].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
                rs = gain / loss
                return 100 - (100 / (1 + rs))
        except Exception as e:
            logger.error(f"❌ Error calculating RSI: {str(e)}")
            return None

    def _calculate_macd(self, df: pd.DataFrame) -> Optional[Dict]:
        """Calculate MACD indicator using TA-Lib or manual calculation."""
        try:
            if TALIB_AVAILABLE:
                macd, macd_signal, macd_hist = talib.MACD(df["close"].values)
                current_macd = float(macd[-1]) if not np.isnan(macd[-1]) else 0
                current_signal = (
                    float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else 0
                )
                current_hist = (
                    float(macd_hist[-1]) if not np.isnan(macd_hist[-1]) else 0
                )
            else:
                # Manual MACD calculation
                ema12 = df["close"].ewm(span=12).mean()
                ema26 = df["close"].ewm(span=26).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9).mean()
                histogram = macd_line - signal_line

                current_macd = float(macd_line.iloc[-1])
                current_signal = float(signal_line.iloc[-1])
                current_hist = float(histogram.iloc[-1])

            return {
                "macd": current_macd,
                "signal": current_signal,
                "histogram": current_hist,
                "bullish_crossover": current_macd > current_signal and current_hist > 0,
                "bearish_crossover": current_macd < current_signal and current_hist < 0,
                "signal_type": "BUY" if current_macd > current_signal else "SELL",
            }

        except Exception as e:
            logger.error(f"❌ Error calculating MACD: {str(e)}")
            return None

    def _calculate_bollinger_bands(
        self, df: pd.DataFrame, period: int = 20, std_dev: int = 2
    ) -> Optional[Dict]:
        """Calculate Bollinger Bands."""
        try:
            if TALIB_AVAILABLE:
                upper, middle, lower = talib.BBANDS(
                    df["close"].values,
                    timeperiod=period,
                    nbdevup=std_dev,
                    nbdevdn=std_dev,
                )
                current_upper = float(upper[-1])
                current_middle = float(middle[-1])
                current_lower = float(lower[-1])
            else:
                # Manual calculation
                sma = df["close"].rolling(window=period).mean()
                std = df["close"].rolling(window=period).std()
                upper = sma + (std * std_dev)
                lower = sma - (std * std_dev)

                current_upper = float(upper.iloc[-1])
                current_middle = float(sma.iloc[-1])
                current_lower = float(lower.iloc[-1])

            current_price = float(df["close"].iloc[-1])
            bb_position = (current_price - current_lower) / (
                current_upper - current_lower
            )

            return {
                "upper": current_upper,
                "middle": current_middle,
                "lower": current_lower,
                "current_price": current_price,
                "bb_position": bb_position,
                "squeeze": (current_upper - current_lower) / current_middle < 0.1,
                "signal": "SELL"
                if current_price > current_upper
                else "BUY"
                if current_price < current_lower
                else "NEUTRAL",
            }

        except Exception as e:
            logger.error(f"❌ Error calculating Bollinger Bands: {str(e)}")
            return None

    def _calculate_moving_averages(
        self, df: pd.DataFrame, ma_type: str
    ) -> Optional[Dict]:
        """Calculate moving averages (SMA or EMA)."""
        try:
            results = {}
            periods = [20, 50]

            for period in periods:
                if ma_type == "SMA":
                    if TALIB_AVAILABLE:
                        ma_values = talib.SMA(df["close"].values, timeperiod=period)
                        current_ma = (
                            float(ma_values[-1]) if not np.isnan(ma_values[-1]) else 0
                        )
                    else:
                        ma_series = df["close"].rolling(window=period).mean()
                        current_ma = float(ma_series.iloc[-1])
                else:  # EMA
                    if TALIB_AVAILABLE:
                        ma_values = talib.EMA(df["close"].values, timeperiod=period)
                        current_ma = (
                            float(ma_values[-1]) if not np.isnan(ma_values[-1]) else 0
                        )
                    else:
                        ma_series = df["close"].ewm(span=period).mean()
                        current_ma = float(ma_series.iloc[-1])

                current_price = float(df["close"].iloc[-1])

                results[str(period)] = {
                    "value": current_ma,
                    "current_price": current_price,
                    "above_ma": current_price > current_ma,
                    "distance_pct": ((current_price - current_ma) / current_ma) * 100,
                    "signal": "BUY" if current_price > current_ma else "SELL",
                }

            return results

        except Exception as e:
            logger.error(f"❌ Error calculating {ma_type}: {str(e)}")
            return None

    def _calculate_stochastic(
        self, df: pd.DataFrame, k_period: int = 14, d_period: int = 3
    ) -> Optional[Dict]:
        """Calculate Stochastic oscillator."""
        try:
            if TALIB_AVAILABLE:
                slowk, slowd = talib.STOCH(
                    df["high"].values,
                    df["low"].values,
                    df["close"].values,
                    fastk_period=k_period,
                    slowk_period=d_period,
                    slowd_period=d_period,
                )
                current_k = float(slowk[-1]) if not np.isnan(slowk[-1]) else 0
                current_d = float(slowd[-1]) if not np.isnan(slowd[-1]) else 0
            else:
                # Manual calculation
                lowest_low = df["low"].rolling(window=k_period).min()
                highest_high = df["high"].rolling(window=k_period).max()
                k_percent = 100 * (
                    (df["close"] - lowest_low) / (highest_high - lowest_low)
                )
                d_percent = k_percent.rolling(window=d_period).mean()

                current_k = float(k_percent.iloc[-1])
                current_d = float(d_percent.iloc[-1])

            return {
                "k": current_k,
                "d": current_d,
                "overbought": current_k > 80 and current_d > 80,
                "oversold": current_k < 20 and current_d < 20,
                "bullish_crossover": current_k > current_d,
                "signal": (
                    "BUY"
                    if current_k < 20 and current_d < 20
                    else "SELL"
                    if current_k > 80 and current_d > 80
                    else "NEUTRAL"
                ),
            }

        except Exception as e:
            logger.error(f"❌ Error calculating Stochastic: {str(e)}")
            return None

    def _generate_overall_signal(self, indicators: Dict) -> Dict:
        """Generate overall signal from all indicators."""
        try:
            signals = []

            # Collect individual signals
            for indicator, data in indicators.items():
                if isinstance(data, dict) and "signal" in data:
                    signals.append(data["signal"])
                elif isinstance(data, dict) and "signal_type" in data:
                    signals.append(data["signal_type"])

            # Count signals
            buy_signals = signals.count("BUY")
            sell_signals = signals.count("SELL")
            neutral_signals = signals.count("NEUTRAL")

            total_signals = len(signals)
            if total_signals == 0:
                return {"signal": "NEUTRAL", "confidence": 0, "breakdown": {}}

            # Determine overall signal
            buy_pct = buy_signals / total_signals
            sell_pct = sell_signals / total_signals

            if buy_pct >= 0.6:
                overall_signal = "STRONG_BUY"
                confidence = buy_pct * 100
            elif buy_pct >= 0.4:
                overall_signal = "BUY"
                confidence = buy_pct * 80
            elif sell_pct >= 0.6:
                overall_signal = "STRONG_SELL"
                confidence = sell_pct * 100
            elif sell_pct >= 0.4:
                overall_signal = "SELL"
                confidence = sell_pct * 80
            else:
                overall_signal = "NEUTRAL"
                confidence = 50

            return {
                "signal": overall_signal,
                "confidence": round(confidence, 1),
                "breakdown": {
                    "buy_signals": buy_signals,
                    "sell_signals": sell_signals,
                    "neutral_signals": neutral_signals,
                    "total_signals": total_signals,
                },
            }

        except Exception as e:
            logger.error(f"❌ Error generating overall signal: {str(e)}")
            return {"signal": "NEUTRAL", "confidence": 0, "breakdown": {}}

    async def _assess_market_sentiment(
        self,
        symbol: str,
        include_fear_greed: bool,
        include_funding_rates: bool,
        include_open_interest: bool,
    ) -> Dict[str, Any]:
        """Assess market sentiment using multiple indicators."""
        try:
            logger.info(f"😱 Assessing market sentiment for {symbol}")

            results = {
                "success": True,
                "symbol": symbol,
                "sentiment_score": 50,  # Neutral baseline
                "sentiment_level": "NEUTRAL",
                "components": {},
                "timestamp": datetime.now().isoformat(),
            }

            sentiment_scores = []

            # Fear & Greed Index
            if include_fear_greed and WEB_SCRAPING_AVAILABLE:
                fear_greed = await self._get_fear_greed_index()
                if fear_greed:
                    results["components"]["fear_greed"] = fear_greed
                    sentiment_scores.append(fear_greed["value"])

            # Funding Rates
            if include_funding_rates:
                funding_data = await self._get_funding_rates(symbol)
                if funding_data:
                    results["components"]["funding_rates"] = funding_data
                    # Convert funding rate to sentiment score (0-100)
                    funding_sentiment = 50 + (
                        funding_data["funding_rate"] * 10000
                    )  # Scale funding rate
                    funding_sentiment = max(0, min(100, funding_sentiment))
                    sentiment_scores.append(funding_sentiment)

            # Open Interest
            if include_open_interest:
                oi_data = await self._get_open_interest(symbol)
                if oi_data:
                    results["components"]["open_interest"] = oi_data
                    # Convert OI change to sentiment
                    oi_sentiment = 50 + (oi_data["change_24h"] * 2)  # Scale OI change
                    oi_sentiment = max(0, min(100, oi_sentiment))
                    sentiment_scores.append(oi_sentiment)

            # Calculate overall sentiment
            if sentiment_scores:
                results["sentiment_score"] = round(
                    sum(sentiment_scores) / len(sentiment_scores), 1
                )

            # Determine sentiment level
            score = results["sentiment_score"]
            if score >= 80:
                results["sentiment_level"] = "EXTREME_GREED"
            elif score >= 65:
                results["sentiment_level"] = "GREED"
            elif score >= 55:
                results["sentiment_level"] = "MILD_GREED"
            elif score >= 45:
                results["sentiment_level"] = "NEUTRAL"
            elif score >= 35:
                results["sentiment_level"] = "MILD_FEAR"
            elif score >= 20:
                results["sentiment_level"] = "FEAR"
            else:
                results["sentiment_level"] = "EXTREME_FEAR"

            return results

        except Exception as e:
            logger.error(f"❌ Error assessing market sentiment: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
            }

    async def _get_fear_greed_index(self) -> Optional[Dict]:
        """Get Fear & Greed Index from alternative.me."""
        try:
            if not WEB_SCRAPING_AVAILABLE:
                return None

            url = "https://api.alternative.me/fng/"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "data" in data and len(data["data"]) > 0:
                            fng_data = data["data"][0]
                            return {
                                "value": int(fng_data["value"]),
                                "classification": fng_data["value_classification"],
                                "timestamp": fng_data["timestamp"],
                            }
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching Fear & Greed Index: {str(e)}")
            return None

    async def _get_funding_rates(self, symbol: str) -> Optional[Dict]:
        """Get funding rates from Binance."""
        try:
            url = "https://fapi.binance.com/fapi/v1/fundingRate"
            params = {"symbol": symbol, "limit": 1}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            latest = data[0]
                            return {
                                "funding_rate": float(latest["fundingRate"]),
                                "funding_time": latest["fundingTime"],
                                "mark_price": float(latest.get("markPrice", 0)),
                            }
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching funding rates: {str(e)}")
            return None

    async def _get_open_interest(self, symbol: str) -> Optional[Dict]:
        """Get open interest data from Binance."""
        try:
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            params = {"symbol": symbol}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            current_oi = float(data["openInterest"])

                            # Get historical OI for comparison
                            hist_url = (
                                "https://fapi.binance.com/futures/data/openInterestHist"
                            )
                            hist_params = {"symbol": symbol, "period": "1d", "limit": 2}

                            async with session.get(
                                hist_url, params=hist_params
                            ) as hist_response:
                                if hist_response.status == 200:
                                    hist_data = await hist_response.json()
                                    if len(hist_data) >= 2:
                                        prev_oi = float(
                                            hist_data[-2]["sumOpenInterest"]
                                        )
                                        change_24h = (
                                            (current_oi - prev_oi) / prev_oi
                                        ) * 100
                                    else:
                                        change_24h = 0
                                else:
                                    change_24h = 0

                            return {
                                "open_interest": current_oi,
                                "change_24h": change_24h,
                                "timestamp": data.get("time", int(time.time() * 1000)),
                            }
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching open interest: {str(e)}")
            return None


async def main():
    """Run the Technical Analysis MCP Server."""
    server_instance = TechnicalAnalysisMCPServer()

    logger.info("🚀 Starting Technical Analysis MCP Server...")

    # Run the server with proper MCP protocol
    async with server_instance.server.run_stdio() as streams:
        await server_instance.server.run(
            streams[0],
            streams[1],
            InitializationOptions(
                server_name="technical-analysis-mcp-server",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
