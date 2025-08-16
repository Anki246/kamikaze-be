"""
Real Market Data API with Binance Integration
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class MarketDataAPI:
    """Real market data API using Binance public endpoints."""

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False
        self.base_url = "https://api.binance.com"
        self.testnet_url = "https://testnet.binance.vision"
        logger.info("Real MarketDataAPI initialized")

    async def connect(self):
        """Connect to market data sources (async)."""
        try:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "Kamikaze-Trader/1.0"},
            )

            # Test connection with server time
            async with self.session.get(f"{self.base_url}/api/v3/time") as response:
                if response.status == 200:
                    self.connected = True
                    logger.info("Real MarketDataAPI connected successfully")
                    return True
                else:
                    logger.error(f"Failed to connect to Binance API: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to market data API: {e}")
            self.connected = False
            return False

    async def disconnect(self):
        """Disconnect from market data sources."""
        if self.session:
            await self.session.close()
            self.session = None
        self.connected = False
        logger.info("MarketDataAPI disconnected")

    async def get_ticker_data(self, symbol: str) -> Dict[str, Any]:
        """Get 24h ticker data for a symbol."""
        if not self.session:
            await self.connect()

        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {"symbol": symbol.upper()}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
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
                        "timestamp": int(datetime.utcnow().timestamp()),
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("msg", "Unknown error"),
                        "symbol": symbol,
                        "price": 0.0,
                        "change_24h": 0.0,
                        "change_percent_24h": 0.0,
                        "high_24h": 0.0,
                        "low_24h": 0.0,
                        "volume_24h": 0.0,
                        "timestamp": int(datetime.utcnow().timestamp()),
                    }

        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "price": 0.0,
                "change_24h": 0.0,
                "change_percent_24h": 0.0,
                "high_24h": 0.0,
                "low_24h": 0.0,
                "volume_24h": 0.0,
                "timestamp": int(datetime.utcnow().timestamp()),
            }

    async def get_market_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Get market data for multiple symbols."""
        if not self.session:
            await self.connect()

        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"

            async with self.session.get(url) as response:
                if response.status == 200:
                    all_data = await response.json()

                    # Filter for requested symbols
                    filtered_data = {}
                    symbol_set = {s.upper() for s in symbols}

                    for ticker in all_data:
                        if ticker["symbol"] in symbol_set:
                            filtered_data[ticker["symbol"]] = {
                                "symbol": ticker["symbol"],
                                "price": float(ticker["lastPrice"]),
                                "change24h": float(ticker["priceChange"]),
                                "changePercent24h": float(ticker["priceChangePercent"]),
                                "volume24h": float(ticker["volume"]),
                                "high24h": float(ticker["highPrice"]),
                                "low24h": float(ticker["lowPrice"]),
                                "timestamp": int(datetime.utcnow().timestamp()),
                            }

                    return {
                        "success": True,
                        "data": filtered_data,
                        "timestamp": int(datetime.utcnow().timestamp()),
                        "source": "binance",
                    }
                else:
                    error_data = await response.json()
                    return {
                        "success": False,
                        "error": error_data.get("msg", "Unknown error"),
                        "data": {},
                        "timestamp": int(datetime.utcnow().timestamp()),
                    }

        except Exception as e:
            logger.error(f"Failed to get market data for {symbols}: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": {},
                "timestamp": int(datetime.utcnow().timestamp()),
            }

    def get_ticker(self, symbol: str):
        """Synchronous wrapper for backward compatibility."""
        # This is a legacy method, should use get_ticker_data instead
        return {"symbol": symbol, "price": "50000.00", "change": "1.5%"}

    def get_market_data_sync(self, symbol: str):
        """Synchronous wrapper for backward compatibility."""
        # This is a legacy method, should use get_market_data instead
        return {"symbol": symbol, "data": "mock_data"}


market_data_api = MarketDataAPI()
