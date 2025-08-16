"""
Market Data API Service
Handles market data requests via MCP servers and provides unified API responses
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.fluxtrader.fastmcp_client import FluxTraderMCPClient, create_binance_client

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


logger = logging.getLogger(__name__)


class MarketDataAPI:
    """
    Market Data API service that connects to MCP servers for real-time market data.
    Provides a unified interface for market data operations.
    """

    def __init__(self):
        self.binance_client: Optional[FluxTraderMCPClient] = None
        self.connected = False
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 30  # seconds

    async def connect(self):
        """Connect to MCP servers."""
        try:
            logger.info("🔗 Connecting to Binance FastMCP server...")
            self.binance_client = await create_binance_client()
            self.connected = True
            logger.info("✅ Market Data API connected successfully")
        except Exception as e:
            logger.error(f"❌ Failed to connect Market Data API: {e}")
            self.connected = False
            raise

    async def disconnect(self):
        """Disconnect from MCP servers."""
        try:
            if self.binance_client:
                await self.binance_client.disconnect()
            self.connected = False
            logger.info("✅ Market Data API disconnected")
        except Exception as e:
            logger.error(f"❌ Error disconnecting Market Data API: {e}")

    def _get_cache_key(self, operation: str, **kwargs) -> str:
        """Generate cache key for operation."""
        key_parts = [operation]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return "_".join(key_parts)

    def _get_cache(self, key: str) -> Optional[Any]:
        """Get cached data if still valid."""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.cache_ttl:
                return data
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        """Set cache data with timestamp."""
        self.cache[key] = (data, time.time())

    async def get_ticker_data(self, symbol: str) -> Dict[str, Any]:
        """Get 24h ticker data for a symbol."""
        if not self.connected or not self.binance_client:
            raise Exception("Market Data API not connected")

        cache_key = self._get_cache_key("ticker", symbol=symbol)
        cached_data = self._get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            result = await self.binance_client.call_tool(
                "get_24h_ticker", {"symbol": symbol}
            )

            if result.get("success"):
                response = {
                    "success": True,
                    "symbol": result["symbol"],
                    "price": result["price"],
                    "change_24h": result["change_24h"],
                    "change_percent_24h": result["change_percent_24h"],
                    "high_24h": result["high_24h"],
                    "low_24h": result["low_24h"],
                    "volume_24h": result["volume_24h"],
                    "quote_volume_24h": result.get("quote_volume_24h", 0),
                    "open_price": result.get("open_price", 0),
                    "timestamp": result.get("timestamp", int(time.time())),
                }
            else:
                response = {
                    "success": False,
                    "symbol": symbol,
                    "price": 0,
                    "change_24h": 0,
                    "change_percent_24h": 0,
                    "high_24h": 0,
                    "low_24h": 0,
                    "volume_24h": 0,
                    "quote_volume_24h": 0,
                    "open_price": 0,
                    "timestamp": int(time.time()),
                    "error": result.get("error", "Unknown error"),
                }

            self._set_cache(cache_key, response)
            return response

        except Exception as e:
            logger.error(f"❌ Failed to get ticker data for {symbol}: {e}")
            raise

    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get market data for multiple symbols."""
        if not self.connected or not self.binance_client:
            raise Exception("Market Data API not connected")

        cache_key = self._get_cache_key(
            "market_data", symbols=",".join(sorted(symbols))
        )
        cached_data = self._get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            # Fetch data for all symbols concurrently
            tasks = []
            for symbol in symbols:
                task = self.get_ticker_data(symbol)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            market_data = {}
            for i, result in enumerate(results):
                symbol = symbols[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ Failed to get data for {symbol}: {result}")
                    continue

                if result.get("success"):
                    market_data[symbol] = {
                        "symbol": result["symbol"],
                        "price": result["price"],
                        "change24h": result["change_24h"],
                        "changePercent24h": result["change_percent_24h"],
                        "volume24h": result["volume_24h"],
                        "high24h": result["high_24h"],
                        "low24h": result["low_24h"],
                        "timestamp": result["timestamp"],
                        # Add API-compatible field names
                        "change_24h": result["change_24h"],
                        "change_percent_24h": result["change_percent_24h"],
                        "volume_24h": result["volume_24h"],
                        "high_24h": result["high_24h"],
                        "low_24h": result["low_24h"],
                    }

            response = {
                "success": True,
                "data": market_data,
                "timestamp": int(time.time()),
                "source": "binance",
            }

            self._set_cache(cache_key, response)
            return response

        except Exception as e:
            logger.error(f"❌ Failed to get market data: {e}")
            raise

    async def get_market_stats(self, symbols: List[str]) -> Dict[str, Any]:
        """Calculate market statistics from symbol data."""
        try:
            market_data_response = await self.get_market_data(symbols)

            if not market_data_response.get("success") or not market_data_response.get(
                "data"
            ):
                return {
                    "success": False,
                    "total_volume": 0,
                    "avg_change": 0,
                    "gainers_count": 0,
                    "losers_count": 0,
                    "total_assets": 0,
                    "timestamp": int(time.time()),
                }

            data = market_data_response["data"]
            prices = list(data.values())

            if not prices:
                return {
                    "success": False,
                    "total_volume": 0,
                    "avg_change": 0,
                    "gainers_count": 0,
                    "losers_count": 0,
                    "total_assets": 0,
                    "timestamp": int(time.time()),
                }

            # Calculate statistics
            total_volume = sum(p.get("volume24h", 0) for p in prices)
            avg_change = sum(p.get("changePercent24h", 0) for p in prices) / len(prices)
            gainers = [p for p in prices if p.get("changePercent24h", 0) > 0]
            losers = [p for p in prices if p.get("changePercent24h", 0) < 0]

            # Find top gainer and loser
            top_gainer = (
                max(prices, key=lambda x: x.get("changePercent24h", 0))
                if prices
                else None
            )
            top_loser = (
                min(prices, key=lambda x: x.get("changePercent24h", 0))
                if prices
                else None
            )

            return {
                "success": True,
                "total_volume": total_volume,
                "avg_change": avg_change,
                "gainers_count": len(gainers),
                "losers_count": len(losers),
                "total_assets": len(prices),
                "top_gainer": top_gainer,
                "top_loser": top_loser,
                "timestamp": int(time.time()),
            }

        except Exception as e:
            logger.error(f"❌ Failed to get market stats: {e}")
            raise

    async def get_technical_indicators(
        self, symbol: str, timeframe: str = "1h", indicators: List[str] = None
    ) -> Dict[str, Any]:
        """Get technical indicators for a symbol."""
        if not self.connected or not self.binance_client:
            raise Exception("Market Data API not connected")

        if indicators is None:
            indicators = ["RSI", "MACD", "BB", "SMA", "EMA"]

        cache_key = self._get_cache_key(
            "indicators",
            symbol=symbol,
            timeframe=timeframe,
            indicators=",".join(indicators),
        )
        cached_data = self._get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            # Call technical analysis MCP server
            result = await self.binance_client.call_tool(
                "calculate_technical_indicators",
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "indicators": indicators,
                    "periods": 100,
                },
            )

            response = {
                "success": result.get("success", False),
                "symbol": symbol,
                "timeframe": timeframe,
                "indicators": result.get("indicators", {}),
                "timestamp": int(time.time()),
            }

            self._set_cache(cache_key, response)
            return response

        except Exception as e:
            logger.error(f"❌ Failed to get technical indicators for {symbol}: {e}")
            raise

    async def get_account_balance(self, user_id: int = None) -> Dict[str, Any]:
        """Get account balance from Binance for trading interface - DYNAMIC USER CONTEXT."""
        if not self.connected or not self.binance_client:
            raise Exception("Market Data API not connected")

        # Use dynamic user context if available, otherwise use provided user_id
        if user_id is None:
            try:
                from src.infrastructure.user_context import get_current_user_context

                user_context = get_current_user_context()
                if user_context:
                    user_id = user_context.user_id
                    logger.info(
                        f"🔧 Using user from context: {user_id} ({user_context.email})"
                    )
                else:
                    logger.error("❌ No user_id provided and no user context available")
                    raise Exception("No user_id provided")
            except ImportError:
                logger.error("❌ No user_id provided and user context not available")
                raise Exception("No user_id provided")

        cache_key = self._get_cache_key("account_balance", user_id=user_id)
        cached_data = self._get_cache(cache_key)
        if cached_data:
            return cached_data

        try:
            logger.info(
                f"Getting account balance for user {user_id} (type: {type(user_id)})"
            )

            # Set user credentials first - always call if we have a user_id
            if user_id is not None:
                # Call the tool with user_id parameter (FastMCP with Pydantic models expects arguments as dict)
                user_id_int = int(user_id)
                logger.info(
                    f"🔧 Calling set_user_credentials_tool with user_id={user_id_int}"
                )
                creds_result = await self.binance_client.call_tool(
                    "set_user_credentials_tool", {"user_id": user_id_int}
                )
                logger.info(f"Credentials setup result: {creds_result}")
            else:
                logger.error("❌ No user_id available for credentials setup")

            # Call account balance MCP tool
            result = await self.binance_client.call_tool("get_account_balance", {})

            # Debug logging to see the exact response format
            logger.info(f"MCP get_account_balance result: {result}")

            if result.get("success", False):
                # Check if data is nested in "data" field or at root level
                data = result.get("data", result)

                # Extract balance values with multiple fallback keys
                total_balance = float(
                    data.get(
                        "total_wallet_balance",
                        data.get("totalWalletBalance", data.get("total_balance", 0)),
                    )
                )

                available_balance = float(
                    data.get(
                        "available_balance",
                        data.get("availableBalance", data.get("futures_balance", 0)),
                    )
                )

                total_unrealized_pnl = float(
                    data.get("total_unrealized_pnl", data.get("totalUnrealizedPnl", 0))
                )

                response = {
                    "success": True,
                    "total_balance": total_balance,
                    "available_balance": available_balance,
                    "futures_balance": available_balance,  # For compatibility
                    "total_unrealized_pnl": total_unrealized_pnl,
                    "assets": data.get("assets", []),
                    "raw_data": data,  # Include raw data for debugging
                    "timestamp": int(time.time()),
                }

                self._set_cache(cache_key, response)
                return response
            else:
                raise Exception(result.get("error", "Failed to get account balance"))

        except Exception as e:
            logger.error(f"❌ Failed to get account balance: {e}")
            # Return default balance structure on error
            return {
                "success": False,
                "total_balance": 0.0,
                "available_balance": 0.0,
                "futures_balance": 0.0,
                "error": str(e),
                "timestamp": int(time.time()),
            }
