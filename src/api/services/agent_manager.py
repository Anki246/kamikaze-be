"""
Agent Manager Service
Centralized management of trading agents with lifecycle control and MCP integration
"""

import asyncio
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.base_agent import AgentStatus, BaseAgent
from agents.fluxtrader.agent import FluxTraderAgent
from api.models.agent_models import (
    AgentConfigResponse,
    AgentConfiguration,
    AgentMetadata,
    AgentPerformanceMetrics,
    AgentResponse,
    AgentRuntimeData,
    AgentStatusResponse,
    StrategyType,
    TradingMetricsResponse,
)
from infrastructure.credentials_database import CredentialsDatabase
from shared.logging_config import setup_logging

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class AgentManager:
    """
    Centralized agent management service.

    Handles:
    - Agent registration and discovery
    - Agent lifecycle management (start/stop/restart)
    - Agent status monitoring
    - Configuration management
    - MCP server coordination
    """

    def __init__(self):
        self.logger = setup_logging("agent_manager")
        self.agents: Dict[str, BaseAgent] = {}
        self.agent_configs: Dict[str, Dict[str, Any]] = {}
        self.agent_registry: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        self.credentials_db = CredentialsDatabase()
        self.websocket_manager = None

    def set_websocket_manager(self, websocket_manager):
        """Set the WebSocket manager for real-time event broadcasting."""
        self.websocket_manager = websocket_manager
        # Update existing agents
        for agent in self.agents.values():
            if hasattr(agent, "set_websocket_manager"):
                agent.set_websocket_manager(websocket_manager)

    async def initialize(self):
        """Initialize the agent manager."""
        try:
            self.logger.info("🔧 Initializing Agent Manager...")

            # Register available agent types
            await self._register_agent_types()

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())

            self._initialized = True
            self.logger.info("✅ Agent Manager initialized successfully")

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Agent Manager: {e}")
            raise

    async def shutdown(self):
        """Shutdown the agent manager."""
        self.logger.info("🛑 Shutting down Agent Manager...")

        # Stop all running agents
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id)

        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        self._initialized = False
        self.logger.info("✅ Agent Manager shutdown complete")

    def is_healthy(self) -> bool:
        """Check if agent manager is healthy."""
        return self._initialized

    async def _register_agent_types(self):
        """Register available agent types."""
        # Register FluxTrader agent
        self.agent_registry["fluxtrader"] = {
            "class": FluxTraderAgent,
            "strategy_type": StrategyType.PUMP_DUMP,
            "name": "FluxTrader",
            "description": "AI-powered pump/dump detection and trading agent",
            "version": "2.0.0",
            "supported_pairs": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"],
            "features": [
                "ai_analysis",
                "multi_level_stops",
                "real_time_trading",
                "mcp_integration",
            ],
        }

        self.logger.info(f"📋 Registered {len(self.agent_registry)} agent types")

    async def _get_user_credentials(self, user_id: int) -> Dict[str, Any]:
        """Retrieve user's trading credentials from database."""
        try:
            # Ensure credentials database is connected
            if not await self.credentials_db.ensure_connected():
                self.logger.error("Failed to connect to credentials database")
                return {}

            credentials = {}

            # Try to get mainnet credentials first
            mainnet_creds = await self.credentials_db.get_binance_credentials(
                user_id, is_mainnet=True
            )
            if mainnet_creds:
                credentials["binance_api_key"] = mainnet_creds[
                    "api_key"
                ]  # Already decrypted
                credentials["binance_secret_key"] = mainnet_creds[
                    "secret_key"
                ]  # Already decrypted
                credentials["is_mainnet"] = True
                self.logger.info(
                    f"✅ Retrieved mainnet Binance credentials for user {user_id}"
                )
                return credentials

            # Fallback to testnet credentials if mainnet not available
            testnet_creds = await self.credentials_db.get_testnet_credentials(
                user_id, "binance"
            )
            if testnet_creds:
                credentials["binance_api_key"] = testnet_creds[
                    "api_key"
                ]  # Already decrypted
                credentials["binance_secret_key"] = testnet_creds[
                    "secret_key"
                ]  # Already decrypted
                credentials["is_mainnet"] = False
                self.logger.info(
                    f"✅ Retrieved testnet Binance credentials for user {user_id}"
                )
                return credentials

            self.logger.warning(f"⚠️ No Binance credentials found for user {user_id}")
            return {}

        except Exception as e:
            self.logger.error(
                f"❌ Failed to retrieve credentials for user {user_id}: {e}"
            )
            return {}

    async def _health_monitor(self):
        """Monitor agent health periodically."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                for agent_id, agent in self.agents.items():
                    if agent.status == AgentStatus.RUNNING:
                        # Check if agent is still responsive
                        # This could include MCP health checks, etc.
                        pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Health monitor error: {e}")

    async def list_agents(self) -> List[AgentResponse]:
        """List all available agents."""
        agents = []

        # Add registered agent types (available for creation)
        for agent_type, info in self.agent_registry.items():
            agent_id = f"{agent_type}_default"

            # Check if instance exists
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                metadata = agent.get_metadata()

                agents.append(
                    AgentResponse(
                        id=agent_id,
                        metadata=AgentMetadata(
                            name=metadata.name,
                            version=metadata.version,
                            strategy_type=metadata.strategy_type.value,
                            description=metadata.description,
                            author=metadata.author,
                            supported_pairs=metadata.supported_pairs,
                            min_balance_required=metadata.min_balance_required,
                            risk_level=metadata.risk_level,
                            time_frame=metadata.time_frame,
                            requires_api_keys=metadata.requires_api_keys,
                            features=metadata.features,
                        ),
                        status=agent.status.value,
                        is_active=agent.status == AgentStatus.RUNNING,
                        configuration=AgentConfiguration(),  # Load from agent config
                        performance=AgentPerformanceMetrics(),  # Load from agent metrics
                        runtime=AgentRuntimeData(
                            uptime=agent.get_uptime()
                            if hasattr(agent, "get_uptime")
                            else None,
                            mcp_connected=self._check_agent_mcp_connection(agent),
                            binance_connected=self._check_agent_binance_connection(
                                agent
                            ),
                            groq_connected=self._check_agent_groq_connection(agent),
                        ),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
            else:
                # Agent type available but not instantiated
                agents.append(
                    AgentResponse(
                        id=agent_id,
                        metadata=AgentMetadata(
                            name=info["name"],
                            version=info["version"],
                            strategy_type=info["strategy_type"],
                            description=info["description"],
                            supported_pairs=info["supported_pairs"],
                            features=info["features"],
                        ),
                        status=AgentStatus.STOPPED,
                        is_active=False,
                        configuration=AgentConfiguration(),
                        performance=AgentPerformanceMetrics(),
                        runtime=AgentRuntimeData(),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )

        return agents

    async def get_agent(self, agent_id: str) -> Optional[AgentResponse]:
        """Get specific agent details."""
        agents = await self.list_agents()
        for agent in agents:
            if agent.id == agent_id:
                return agent
        return None

    async def start_agent(self, agent_id: str, user_id: int = None) -> Dict[str, Any]:
        """Start a trading agent - DYNAMIC USER CONTEXT."""
        try:
            # Use dynamic user context if available, otherwise use provided user_id
            if user_id is None:
                try:
                    from src.infrastructure.user_context import get_current_user_context

                    user_context = get_current_user_context()
                    if user_context:
                        user_id = user_context.user_id
                        self.logger.info(
                            f"🔧 Using user from context: {user_id} ({user_context.email})"
                        )
                    else:
                        self.logger.error(
                            "❌ No user_id provided and no user context available"
                        )
                        raise Exception("No user_id provided")
                except ImportError:
                    self.logger.error(
                        "❌ No user_id provided and user context not available"
                    )
                    raise Exception("No user_id provided")

            # Check if agent already exists
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                if agent.status == AgentStatus.RUNNING:
                    return {"message": "Agent already running", "status": "running"}

                # Start existing agent
                success = await agent.start_trading()
                if success:
                    self.logger.info(f"✅ Agent {agent_id} started successfully")
                    return {"message": "Agent started", "status": "running"}
                else:
                    raise Exception("Failed to start agent")

            # Create new agent instance
            agent_type = agent_id.split("_")[0]
            if agent_type not in self.agent_registry:
                raise Exception(f"Unknown agent type: {agent_type}")

            agent_class = self.agent_registry[agent_type]["class"]
            config = self.agent_configs.get(agent_id, {})

            # Get user credentials using dynamic context
            if user_id:
                self.logger.info(f"🔍 Getting credentials for user {user_id}...")
                user_credentials = await self._get_user_credentials(user_id)
                if user_credentials:
                    # Set environment variables for the FastMCP server to use
                    import os

                    os.environ["BINANCE_API_KEY"] = user_credentials["binance_api_key"]
                    os.environ["BINANCE_SECRET_KEY"] = user_credentials[
                        "binance_secret_key"
                    ]

                    config.update(user_credentials)
                    config["user_id"] = user_id
                    self.logger.info(
                        f"✅ Added user {user_id} credentials to agent {agent_id} config and environment"
                    )
                    self.logger.info(
                        f"🔍 Config now contains user_id: {config.get('user_id')}"
                    )
                else:
                    self.logger.error(
                        f"❌ No credentials found for user {user_id}, agent cannot function"
                    )
                    raise Exception(f"No Binance credentials found for user {user_id}")
            else:
                self.logger.error(f"❌ No user_id provided for agent {agent_id}")
                raise Exception("No user_id provided")

            # Create agent instance
            agent = agent_class(agent_id, config)

            # Inject WebSocket manager for real-time events
            if self.websocket_manager and hasattr(agent, "set_websocket_manager"):
                agent.set_websocket_manager(self.websocket_manager)

            # Initialize agent
            if not await agent.initialize():
                raise Exception("Failed to initialize agent")

            # Store agent
            self.agents[agent_id] = agent

            # Start trading
            success = await agent.start_trading()
            if success:
                self.logger.info(f"✅ Agent {agent_id} created and started successfully")
                return {"message": "Agent created and started", "status": "running"}
            else:
                raise Exception("Failed to start agent after creation")

        except Exception as e:
            self.logger.error(f"❌ Failed to start agent {agent_id}: {e}")
            raise

    async def stop_agent(self, agent_id: str) -> Dict[str, Any]:
        """Stop a trading agent."""
        try:
            if agent_id not in self.agents:
                return {"message": "Agent not found", "status": "stopped"}

            agent = self.agents[agent_id]

            if agent.status == AgentStatus.STOPPED:
                return {"message": "Agent already stopped", "status": "stopped"}

            # Stop the agent
            success = await agent.stop_trading()
            if success:
                self.logger.info(f"✅ Agent {agent_id} stopped successfully")
                return {"message": "Agent stopped", "status": "stopped"}
            else:
                raise Exception("Failed to stop agent")

        except Exception as e:
            self.logger.error(f"❌ Failed to stop agent {agent_id}: {e}")
            raise

    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatusResponse]:
        """Get agent status and runtime information."""
        # Check if agent is instantiated
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            return AgentStatusResponse(
                agent_id=agent_id,
                status=agent.status.value,
                is_running=agent.status == AgentStatus.RUNNING,
                uptime_seconds=agent.get_uptime()
                if hasattr(agent, "get_uptime")
                else 0,
                current_cycle=getattr(agent, "current_cycle", 0),
                max_cycles=getattr(agent, "max_cycles", 100),
                last_activity=getattr(agent, "last_activity", None)
                or datetime.utcnow(),
                mcp_connected=self._check_agent_mcp_connection(agent),
                binance_connected=self._check_agent_binance_connection(agent),
                groq_connected=self._check_agent_groq_connection(agent),
            )

        # Check if agent exists in registry (not instantiated)
        agent_type = agent_id.split("_")[0] if "_" in agent_id else agent_id
        if agent_type in self.agent_registry:
            return AgentStatusResponse(
                agent_id=agent_id,
                status="stopped",
                is_running=False,
                uptime_seconds=0,
                current_cycle=0,
                max_cycles=100,
                last_activity=datetime.utcnow(),
                mcp_connected=False,
                binance_connected=False,
                groq_connected=False,
                error_message=None,
            )

        return None

    def _check_agent_mcp_connection(self, agent) -> bool:
        """Check if agent's MCP connection is active"""
        try:
            # Check FluxTrader agent's binance_tools.mcp_connected property
            if hasattr(agent, "binance_tools") and hasattr(
                agent.binance_tools, "mcp_connected"
            ):
                return agent.binance_tools.mcp_connected
            # Check if agent has MCP client and it's connected
            elif hasattr(agent, "mcp_client") and hasattr(
                agent.mcp_client, "connected"
            ):
                return agent.mcp_client.connected
            elif (
                hasattr(agent, "binance_tools")
                and hasattr(agent.binance_tools, "mcp_client")
                and hasattr(agent.binance_tools.mcp_client, "connected")
            ):
                return agent.binance_tools.mcp_client.connected
            elif (
                hasattr(agent, "trading_bot")
                and hasattr(agent.trading_bot, "mcp_client")
                and hasattr(agent.trading_bot.mcp_client, "connected")
            ):
                return agent.trading_bot.mcp_client.connected
            return False
        except Exception as e:
            self.logger.warning(f"Failed to check MCP connection for agent: {e}")
            return False

    def _check_agent_binance_connection(self, agent) -> bool:
        """Check if agent's Binance connection is active"""
        try:
            # For FluxTrader agent, Binance connection is tied to MCP connection
            if hasattr(agent, "binance_tools") and hasattr(
                agent.binance_tools, "mcp_connected"
            ):
                return agent.binance_tools.mcp_connected
            # Check if agent has direct Binance connection
            elif hasattr(agent, "binance_tools") and hasattr(
                agent.binance_tools, "connected"
            ):
                return agent.binance_tools.connected
            elif (
                hasattr(agent, "trading_bot")
                and hasattr(agent.trading_bot, "binance_tools")
                and hasattr(agent.trading_bot.binance_tools, "connected")
            ):
                return agent.trading_bot.binance_tools.connected
            return False
        except Exception as e:
            self.logger.warning(f"Failed to check Binance connection for agent: {e}")
            return False

    def _check_agent_groq_connection(self, agent) -> bool:
        """Check if agent's Groq connection is active"""
        try:
            # Check if agent has Groq connection
            if hasattr(agent, "groq_client"):
                return getattr(
                    agent.groq_client, "connected", True
                )  # Assume connected if client exists
            elif hasattr(agent, "llm_client"):
                return getattr(
                    agent.llm_client, "connected", True
                )  # Assume connected if client exists
            return True  # Default to true for Groq as it's usually available
        except Exception as e:
            self.logger.warning(f"Failed to check Groq connection for agent: {e}")
            return False

    async def get_agent_metrics(
        self, agent_id: str
    ) -> Optional[TradingMetricsResponse]:
        """Get agent trading metrics."""
        # Check if agent is instantiated
        if agent_id in self.agents:
            agent = self.agents[agent_id]

            # Get metrics from agent
            performance = AgentPerformanceMetrics(
                total_pnl=getattr(agent, "total_pnl", 0.0),
                trades_executed=getattr(agent, "trades_executed", 0),
                signals_found=getattr(agent, "signals_detected", 0),
                current_balance=getattr(agent, "available_balance", 0.0),
            )

            return TradingMetricsResponse(
                agent_id=agent_id,
                performance=performance,
                balance={
                    "total": getattr(agent, "account_balance", 0.0),
                    "available": getattr(agent, "available_balance", 0.0),
                },
                timestamp=datetime.utcnow(),
            )

        # Check if agent exists in registry (not instantiated) - return default metrics
        agent_type = agent_id.split("_")[0] if "_" in agent_id else agent_id
        if agent_type in self.agent_registry:
            performance = AgentPerformanceMetrics(
                total_pnl=0.0, trades_executed=0, signals_found=0, current_balance=0.0
            )

            return TradingMetricsResponse(
                agent_id=agent_id,
                performance=performance,
                balance={"total": 0.0, "available": 0.0},
                active_positions=[],
                recent_trades=[],
                recent_signals=[],
                timestamp=datetime.utcnow(),
            )

        return None

    async def get_agent_config(self, agent_id: str) -> Optional[AgentConfigResponse]:
        """Get agent configuration."""
        try:
            # Extract agent type from agent_id (e.g., "fluxtrader_default" -> "fluxtrader")
            agent_type = agent_id.split("_")[0] if "_" in agent_id else agent_id

            # Always allow access if the agent type is registered, regardless of instantiation
            if agent_type not in self.agent_registry:
                self.logger.warning(f"Agent type {agent_type} not found in registry")
                return None

            # Get configuration with safe defaults
            config = self.agent_configs.get(agent_id, {})

            # Create configuration object with proper validation
            try:
                # Filter out any invalid keys that might cause validation errors
                valid_config_keys = AgentConfiguration.__fields__.keys()
                filtered_config = {
                    k: v for k, v in config.items() if k in valid_config_keys
                }
                configuration = AgentConfiguration(**filtered_config)
            except Exception as e:
                self.logger.warning(
                    f"Invalid config for agent {agent_id}, using defaults: {e}"
                )
                configuration = AgentConfiguration()

            # Get metadata from registry or agent
            if agent_id in self.agents:
                metadata = self.agents[agent_id].get_metadata()
            else:
                info = self.agent_registry.get(agent_type, {})
                metadata = AgentMetadata(
                    name=info.get("name", "Unknown"),
                    version=info.get("version", "1.0.0"),
                    strategy_type=info.get("strategy_type", StrategyType.PUMP_DUMP),
                    description=info.get("description", "No description available"),
                    author=info.get("author", "FluxTrader Team"),
                    supported_pairs=info.get("supported_pairs", []),
                    features=info.get("features", []),
                )

            return AgentConfigResponse(
                agent_id=agent_id,
                configuration=configuration,
                metadata=metadata,
                last_updated=datetime.utcnow(),
            )

        except Exception as e:
            self.logger.error(f"Error getting agent config for {agent_id}: {e}")
            return None

    async def update_agent_config(
        self, agent_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update agent configuration."""
        self.agent_configs[agent_id] = config

        # If agent is running, apply configuration changes
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            # Apply configuration to running agent
            # This would depend on the specific agent implementation
            pass

        self.logger.info(f"✅ Updated configuration for agent {agent_id}")
        return {"message": "Configuration updated", "agent_id": agent_id}
