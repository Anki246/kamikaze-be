#!/usr/bin/env python3
"""
24/7 Trading System Service Orchestrator
Manages all microservices for the event-driven trading system
"""

import asyncio
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional

from infrastructure.event_bus import BaseEvent, EventType, event_bus
from services.market_data_service import MarketDataService
from services.order_manager import OrderManager
from services.strategy_engine import StrategyEngine
from shared.logging_config import setup_logging

# Add src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))



class HealthMonitor:
    """Health monitoring service for all components."""

    def __init__(self):
        self.logger = setup_logging("health_monitor")
        self.running = False
        self.service_health: Dict[str, Dict] = {}
        self.alert_thresholds = {
            "max_errors": 10,
            "max_downtime": 300,  # 5 minutes
            "min_data_rate": 1,  # 1 update per minute
        }

    async def start(self):
        """Start health monitoring."""
        self.logger.info("🏥 Starting Health Monitor...")

        # Connect to event bus
        if not await event_bus.connect():
            raise Exception("Failed to connect to event bus")

        # Subscribe to health events
        await event_bus.subscribe("trading:system:*", self._handle_health_event)

        self.running = True

        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._health_checker()),
            asyncio.create_task(self._alert_manager()),
        ]

        self.logger.info("✅ Health Monitor started")

        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop health monitoring."""
        self.logger.info("🛑 Stopping Health Monitor...")
        self.running = False
        await event_bus.disconnect()
        self.logger.info("✅ Health Monitor stopped")

    async def _handle_health_event(self, event: BaseEvent):
        """Handle health events from services."""
        try:
            if event.event_type == EventType.HEALTH_CHECK:
                service_name = event.data.get("service", event.source)
                self.service_health[service_name] = {
                    "status": event.data.get("status", "unknown"),
                    "last_update": event.timestamp,
                    "data": event.data,
                }

                self.logger.debug(
                    f"📊 Health update from {service_name}: {event.data.get('status')}"
                )

        except Exception as e:
            self.logger.error(f"❌ Error handling health event: {e}")

    async def _health_checker(self):
        """Periodic health checks."""
        while self.running:
            try:
                await asyncio.sleep(60)  # Check every minute

                current_time = datetime.utcnow()
                unhealthy_services = []

                # Check each service health
                for service_name, health_data in self.service_health.items():
                    last_update = health_data.get("last_update")
                    if last_update:
                        time_diff = (current_time - last_update).total_seconds()
                        if time_diff > self.alert_thresholds["max_downtime"]:
                            unhealthy_services.append(
                                f"{service_name} (no update for {time_diff:.0f}s)"
                            )

                # Publish system health status
                system_health = BaseEvent(
                    event_type=EventType.HEALTH_CHECK,
                    timestamp=current_time,
                    source="health_monitor",
                    data={
                        "service": "system_health",
                        "status": "unhealthy" if unhealthy_services else "healthy",
                        "unhealthy_services": unhealthy_services,
                        "total_services": len(self.service_health),
                        "healthy_services": len(self.service_health)
                        - len(unhealthy_services),
                    },
                )
                await event_bus.publish("trading:system:health", system_health)

                if unhealthy_services:
                    self.logger.warning(f"⚠️ Unhealthy services: {unhealthy_services}")

            except Exception as e:
                self.logger.error(f"❌ Error in health checker: {e}")

    async def _alert_manager(self):
        """Manage alerts and notifications."""
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                # Check for critical conditions and send alerts
                for service_name, health_data in self.service_health.items():
                    status = health_data.get("status")
                    data = health_data.get("data", {})

                    # Check error rates
                    error_count = data.get("error_count", 0)
                    if error_count > self.alert_thresholds["max_errors"]:
                        await self._send_alert(
                            "HIGH_ERROR_RATE",
                            f"{service_name} has {error_count} errors",
                            "HIGH",
                        )

            except Exception as e:
                self.logger.error(f"❌ Error in alert manager: {e}")

    async def _send_alert(self, alert_type: str, message: str, severity: str):
        """Send alert notification."""
        try:
            alert_event = BaseEvent(
                event_type=EventType.ALERT,
                timestamp=datetime.utcnow(),
                source="health_monitor",
                data={
                    "alert_type": alert_type,
                    "message": message,
                    "severity": severity,
                },
            )
            await event_bus.publish("trading:alerts:system", alert_event)

            self.logger.warning(f"🚨 ALERT [{severity}]: {message}")

        except Exception as e:
            self.logger.error(f"❌ Error sending alert: {e}")


class ServiceOrchestrator:
    """
    Main orchestrator for the 24/7 trading system.

    Manages:
    - Market Data Service
    - Strategy Engine
    - Order Manager
    - Health Monitor
    - MCP Server
    """

    def __init__(self):
        self.logger = setup_logging("service_orchestrator")
        self.running = False
        self.services = {}
        self.mcp_server_process = None

        # Service instances
        self.market_data_service = MarketDataService()
        self.strategy_engine = StrategyEngine()
        self.order_manager = OrderManager()
        self.health_monitor = HealthMonitor()

    async def start(self):
        """Start all services."""
        try:
            self.logger.info("🚀 Starting 24/7 Trading System...")

            # Start Redis (if not running)
            await self._ensure_redis_running()

            # Start MCP Server
            await self._start_mcp_server()

            # Start all services
            self.running = True

            tasks = [
                asyncio.create_task(
                    self._run_service("market_data", self.market_data_service)
                ),
                asyncio.create_task(
                    self._run_service("strategy_engine", self.strategy_engine)
                ),
                asyncio.create_task(
                    self._run_service("order_manager", self.order_manager)
                ),
                asyncio.create_task(
                    self._run_service("health_monitor", self.health_monitor)
                ),
            ]

            self.logger.info("✅ All services started successfully")
            self.logger.info("🎯 24/7 Trading System is now LIVE!")

            # Wait for all services
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            self.logger.error(f"❌ Failed to start trading system: {e}")
            raise

    async def stop(self):
        """Stop all services gracefully."""
        self.logger.info("🛑 Stopping 24/7 Trading System...")
        self.running = False

        # Stop all services
        stop_tasks = []
        for service_name, service in self.services.items():
            if hasattr(service, "stop"):
                stop_tasks.append(asyncio.create_task(service.stop()))

        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)

        # Stop MCP server
        if self.mcp_server_process:
            self.mcp_server_process.terminate()
            try:
                await asyncio.wait_for(self.mcp_server_process.wait(), timeout=10)
            except asyncio.TimeoutError:
                self.mcp_server_process.kill()

        self.logger.info("✅ 24/7 Trading System stopped")

    async def _run_service(self, name: str, service):
        """Run a service with error handling and restart logic."""
        self.services[name] = service
        restart_count = 0
        max_restarts = 5

        while self.running and restart_count < max_restarts:
            try:
                self.logger.info(f"🔄 Starting service: {name}")
                await service.start()

            except Exception as e:
                restart_count += 1
                self.logger.error(f"❌ Service {name} failed: {e}")

                if restart_count < max_restarts and self.running:
                    wait_time = min(
                        restart_count * 10, 60
                    )  # Exponential backoff, max 60s
                    self.logger.info(
                        f"🔄 Restarting {name} in {wait_time}s (attempt {restart_count}/{max_restarts})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Service {name} exceeded max restarts")
                    break

    async def _ensure_redis_running(self):
        """Ensure Redis is running."""
        try:
            # Try to connect to Redis
            import aioredis

            redis = aioredis.from_url("redis://localhost:6379")
            await redis.ping()
            await redis.close()
            self.logger.info("✅ Redis is running")

        except Exception as e:
            self.logger.error(f"❌ Redis not available: {e}")
            self.logger.info("💡 Please start Redis server: redis-server")
            raise Exception("Redis server is required but not running")

    async def _start_mcp_server(self):
        """Start the Binance MCP server."""
        try:
            mcp_server_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "mcp_servers",
                "binance_fastmcp_server.py",
            )

            if os.path.exists(mcp_server_path):
                self.mcp_server_process = await asyncio.create_subprocess_exec(
                    sys.executable,
                    mcp_server_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Wait a moment for server to start
                await asyncio.sleep(2)

                if self.mcp_server_process.returncode is None:
                    self.logger.info("✅ MCP Server started")
                else:
                    raise Exception("MCP Server failed to start")
            else:
                self.logger.warning("⚠️ MCP Server not found, continuing without it")

        except Exception as e:
            self.logger.error(f"❌ Failed to start MCP Server: {e}")
            # Continue without MCP server for now

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            self.logger.info(f"📡 Received signal {signum}")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler("trading_system.log")],
    )

    # Create orchestrator
    orchestrator = ServiceOrchestrator()
    orchestrator.setup_signal_handlers()

    try:
        await orchestrator.start()
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    except Exception as e:
        logging.error(f"❌ System error: {e}")
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    print("🚀 FluxTrader 24/7 Trading System")
    print("=" * 50)
    print("Starting event-driven microservices architecture...")
    print("Press Ctrl+C to stop")
    print("=" * 50)

    asyncio.run(main())
