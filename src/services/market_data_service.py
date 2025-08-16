#!/usr/bin/env python3
"""
24/7 Market Data Ingestion Service
Continuously ingests market data from Binance and publishes to Redis event bus
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import aiohttp
import websockets

from infrastructure.event_bus import (BaseEvent, EventType, event_bus,
                                      publish_market_data)
from shared.logging_config import setup_logging

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class MarketDataService:
    """
    24/7 Market data ingestion service.

    Features:
    - Real-time WebSocket data from Binance
    - REST API fallback
    - Automatic reconnection
    - Data validation and filtering
    - Event publishing to Redis
    - Health monitoring
    """

    def __init__(self, symbols: List[str] = None):
        self.logger = setup_logging("market_data_service")
        self.symbols = symbols or [
            "BTCUSDT",
            "ETHUSDT",
            "BNBUSDT",
            "ADAUSDT",
            "XRPUSDT",
            "SOLUSDT",
            "DOTUSDT",
            "LINKUSDT",
            "LTCUSDT",
            "BCHUSDT",
        ]

        # WebSocket connections
        self.ws_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 300

        # Data storage
        self.latest_prices: Dict[str, Dict] = {}
        self.price_history: Dict[str, List] = {}

        # Health monitoring
        self.last_data_time: Dict[str, datetime] = {}
        self.error_count = 0
        self.max_errors = 10

        # Binance WebSocket URLs
        self.binance_ws_url = "wss://stream.binance.com:9443/ws"
        self.binance_api_url = "https://api.binance.com/api/v3"

    async def start(self):
        """Start the market data service."""
        try:
            self.logger.info("🚀 Starting 24/7 Market Data Service...")

            # Connect to event bus
            if not await event_bus.connect():
                raise Exception("Failed to connect to event bus")

            self.running = True

            # Start WebSocket connections for each symbol
            tasks = []
            for symbol in self.symbols:
                task = asyncio.create_task(self._start_symbol_stream(symbol))
                tasks.append(task)

            # Start health monitor
            tasks.append(asyncio.create_task(self._health_monitor()))

            # Start price change detector
            tasks.append(asyncio.create_task(self._price_change_detector()))

            self.logger.info(
                f"✅ Market Data Service started for {len(self.symbols)} symbols"
            )

            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"❌ Failed to start Market Data Service: {e}")
            raise

    async def stop(self):
        """Stop the market data service."""
        self.logger.info("🛑 Stopping Market Data Service...")
        self.running = False

        # Close WebSocket connections
        for symbol, ws in self.ws_connections.items():
            try:
                await ws.close()
            except:
                pass

        # Disconnect from event bus
        await event_bus.disconnect()

        self.logger.info("✅ Market Data Service stopped")

    async def _start_symbol_stream(self, symbol: str):
        """Start WebSocket stream for a specific symbol."""
        stream_name = f"{symbol.lower()}@ticker"
        url = f"{self.binance_ws_url}/{stream_name}"

        reconnect_delay = self.reconnect_delay

        while self.running:
            try:
                self.logger.info(f"🔌 Connecting to {symbol} stream...")

                async with websockets.connect(url) as websocket:
                    self.ws_connections[symbol] = websocket
                    reconnect_delay = (
                        self.reconnect_delay
                    )  # Reset delay on successful connection

                    self.logger.info(f"✅ Connected to {symbol} stream")

                    async for message in websocket:
                        if not self.running:
                            break

                        try:
                            await self._process_ticker_data(symbol, json.loads(message))
                        except Exception as e:
                            self.logger.error(f"❌ Error processing {symbol} data: {e}")
                            self.error_count += 1

                            if self.error_count > self.max_errors:
                                self.logger.error("❌ Too many errors, stopping service")
                                self.running = False
                                break

            except Exception as e:
                self.logger.error(f"❌ WebSocket error for {symbol}: {e}")

                if symbol in self.ws_connections:
                    del self.ws_connections[symbol]

                if self.running:
                    self.logger.info(
                        f"🔄 Reconnecting to {symbol} in {reconnect_delay}s..."
                    )
                    await asyncio.sleep(reconnect_delay)

                    # Exponential backoff
                    reconnect_delay = min(reconnect_delay * 2, self.max_reconnect_delay)

    async def _process_ticker_data(self, symbol: str, data: Dict):
        """Process ticker data from Binance."""
        try:
            # Extract relevant data
            price = float(data.get("c", 0))  # Current price
            volume = float(data.get("v", 0))  # 24h volume
            change_24h = float(data.get("P", 0))  # 24h price change percentage
            high_24h = float(data.get("h", 0))  # 24h high
            low_24h = float(data.get("l", 0))  # 24h low

            # Update latest prices
            price_data = {
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "change_24h": change_24h / 100,  # Convert percentage to decimal
                "high_24h": high_24h,
                "low_24h": low_24h,
                "timestamp": datetime.utcnow(),
            }

            self.latest_prices[symbol] = price_data
            self.last_data_time[symbol] = datetime.utcnow()

            # Store price history (keep last 1000 prices)
            if symbol not in self.price_history:
                self.price_history[symbol] = []

            self.price_history[symbol].append(
                {"price": price, "timestamp": datetime.utcnow(), "volume": volume}
            )

            # Keep only last 1000 entries
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]

            # Publish market data event
            await publish_market_data(
                symbol=symbol, price=price, volume=volume, change_24h=change_24h / 100
            )

            # Check for significant price changes
            await self._check_price_alerts(symbol, price_data)

            self.logger.debug(f"📊 {symbol}: ${price:.4f} ({change_24h:+.2f}%)")

        except Exception as e:
            self.logger.error(f"❌ Error processing ticker data for {symbol}: {e}")

    async def _check_price_alerts(self, symbol: str, price_data: Dict):
        """Check for significant price changes and publish alerts."""
        try:
            change_24h = abs(price_data["change_24h"])

            # Alert thresholds
            if change_24h > 0.10:  # 10% change
                alert_event = BaseEvent(
                    event_type=EventType.ALERT,
                    timestamp=datetime.utcnow(),
                    source="market_data_service",
                    data={
                        "alert_type": "SIGNIFICANT_PRICE_CHANGE",
                        "symbol": symbol,
                        "price": price_data["price"],
                        "change_24h": price_data["change_24h"],
                        "severity": "HIGH" if change_24h > 0.20 else "MEDIUM",
                    },
                )
                await event_bus.publish(f"trading:alerts:{symbol}", alert_event)

            # Volume spike detection
            if len(self.price_history[symbol]) > 10:
                recent_volumes = [p["volume"] for p in self.price_history[symbol][-10:]]
                avg_volume = sum(recent_volumes) / len(recent_volumes)

                if price_data["volume"] > avg_volume * 3:  # 3x average volume
                    volume_alert = BaseEvent(
                        event_type=EventType.VOLUME_SPIKE,
                        timestamp=datetime.utcnow(),
                        source="market_data_service",
                        data={
                            "symbol": symbol,
                            "current_volume": price_data["volume"],
                            "average_volume": avg_volume,
                            "multiplier": price_data["volume"] / avg_volume,
                        },
                    )
                    await event_bus.publish(f"trading:alerts:{symbol}", volume_alert)

        except Exception as e:
            self.logger.error(f"❌ Error checking price alerts for {symbol}: {e}")

    async def _price_change_detector(self):
        """Detect rapid price changes and publish events."""
        while self.running:
            try:
                await asyncio.sleep(1)  # Check every second

                for symbol, price_data in self.latest_prices.items():
                    if (
                        symbol in self.price_history
                        and len(self.price_history[symbol]) > 5
                    ):
                        # Get price from 5 seconds ago
                        recent_prices = self.price_history[symbol][-5:]
                        if len(recent_prices) >= 2:
                            old_price = recent_prices[0]["price"]
                            current_price = price_data["price"]

                            # Calculate short-term change
                            if old_price > 0:
                                short_change = (current_price - old_price) / old_price

                                # Detect rapid changes (>1% in 5 seconds)
                                if abs(short_change) > 0.01:
                                    change_event = BaseEvent(
                                        event_type=EventType.PRICE_CHANGE,
                                        timestamp=datetime.utcnow(),
                                        source="market_data_service",
                                        data={
                                            "symbol": symbol,
                                            "old_price": old_price,
                                            "new_price": current_price,
                                            "change_percent": short_change,
                                            "timeframe": "5s",
                                        },
                                    )
                                    await event_bus.publish(
                                        f"trading:market_data:{symbol}", change_event
                                    )

            except Exception as e:
                self.logger.error(f"❌ Error in price change detector: {e}")

    async def _health_monitor(self):
        """Monitor service health and publish health events."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                current_time = datetime.utcnow()
                unhealthy_symbols = []

                # Check for stale data
                for symbol in self.symbols:
                    if symbol in self.last_data_time:
                        time_diff = current_time - self.last_data_time[symbol]
                        if time_diff > timedelta(minutes=2):  # No data for 2 minutes
                            unhealthy_symbols.append(symbol)
                    else:
                        unhealthy_symbols.append(symbol)

                # Publish health status
                health_event = BaseEvent(
                    event_type=EventType.HEALTH_CHECK,
                    timestamp=current_time,
                    source="market_data_service",
                    data={
                        "service": "market_data_service",
                        "status": "unhealthy" if unhealthy_symbols else "healthy",
                        "connected_symbols": len(self.ws_connections),
                        "total_symbols": len(self.symbols),
                        "unhealthy_symbols": unhealthy_symbols,
                        "error_count": self.error_count,
                    },
                )
                await event_bus.publish("trading:system:health", health_event)

                # Reset error count periodically
                if self.error_count > 0:
                    self.error_count = max(0, self.error_count - 1)

            except Exception as e:
                self.logger.error(f"❌ Error in health monitor: {e}")

    async def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """Get latest price data for a symbol."""
        return self.latest_prices.get(symbol)

    async def get_price_history(self, symbol: str, limit: int = 100) -> List[Dict]:
        """Get price history for a symbol."""
        if symbol in self.price_history:
            return self.price_history[symbol][-limit:]
        return []


# Main function for running as standalone service
async def main():
    """Main function for running market data service."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and start service
    service = MarketDataService()

    try:
        await service.start()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
