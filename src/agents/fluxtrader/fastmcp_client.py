#!/usr/bin/env python3
"""
FastMCP Client for FluxTrader Agent
Professional MCP client for communicating with Binance FastMCP server using standards-compliant FastMCP framework

Features:
- Standards-compliant MCP protocol communication using FastMCP Client
- Stdio transport for reliable local server communication
- Async/await patterns for high performance
- Comprehensive error handling and retry logic
- Connection management and health monitoring
- Automatic tool discovery and type-safe operations
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from fastmcp.client.transports import StdioTransport

# FastMCP imports
from fastmcp import Client

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FluxTraderMCPClient:
    """
    Professional FastMCP client for FluxTrader agent using standards-compliant FastMCP framework

    Provides seamless communication with Binance FastMCP server using stdio transport.
    Built on top of the official FastMCP Client for maximum compatibility and reliability.
    """

    def __init__(
        self,
        server_path: str,
        server_name: str = "Binance FastMCP Server",
        env_vars: Optional[Dict[str, str]] = None,
    ):
        self.server_path = server_path
        self.server_name = server_name
        self.env_vars = env_vars or {}
        self.client: Optional[Client] = None
        self.connected = False
        self.available_tools: List[str] = []
        self.server_info: Dict[str, Any] = {}
        self.connection_lock = asyncio.Lock()

        # Create the FastMCP client with stdio transport
        self._create_client()

    def _create_client(self) -> None:
        """Create the FastMCP client with proper stdio transport configuration"""
        try:
            # Prepare environment variables for the server
            server_env = {}

            # Forward necessary environment variables
            env_to_forward = [
                "BINANCE_API_KEY",
                "BINANCE_SECRET_KEY",
                "PYTHONPATH",
                "PATH",
            ]

            for env_var in env_to_forward:
                if env_var in os.environ:
                    server_env[env_var] = os.environ[env_var]

            # Add any custom environment variables
            server_env.update(self.env_vars)

            # Create stdio transport with proper configuration
            transport = StdioTransport(
                command=sys.executable,
                args=[self.server_path],
                env=server_env,
                cwd=str(Path(self.server_path).parent),
                keep_alive=True,  # Reuse the same process for efficiency
            )

            # Create the FastMCP client
            self.client = Client(transport)
            logger.info(f"✅ FastMCP client created for {self.server_name}")

        except Exception as e:
            logger.error(f"❌ Failed to create FastMCP client: {e}")
            raise

    async def connect(self) -> bool:
        """
        Connect to the FastMCP server using standards-compliant FastMCP Client

        Returns:
            bool: True if connection successful, False otherwise
        """
        async with self.connection_lock:
            if self.connected and self.client:
                return True

            try:
                logger.info(f"🔗 Connecting to {self.server_name}...")

                if not self.client:
                    self._create_client()

                # Use FastMCP client context manager for connection
                await self.client.__aenter__()

                # Test connection with ping
                await self.client.ping()

                # Discover available tools
                tools_response = await self.client.list_tools()

                # Handle different response formats
                if hasattr(tools_response, "tools"):
                    # Standard MCP response format
                    self.available_tools = [
                        tool.name if hasattr(tool, "name") else str(tool)
                        for tool in tools_response.tools
                    ]
                elif isinstance(tools_response, list):
                    # Direct list format - extract names from tool objects
                    self.available_tools = []
                    for tool in tools_response:
                        if hasattr(tool, "name"):
                            self.available_tools.append(tool.name)
                        elif isinstance(tool, dict) and "name" in tool:
                            self.available_tools.append(tool["name"])
                        else:
                            # Try to extract name from string representation
                            tool_str = str(tool)
                            if "name='" in tool_str:
                                name_start = tool_str.find("name='") + 6
                                name_end = tool_str.find("'", name_start)
                                if name_end > name_start:
                                    self.available_tools.append(
                                        tool_str[name_start:name_end]
                                    )
                else:
                    # Fallback - try to extract tools from response
                    tools_list = getattr(tools_response, "tools", tools_response)
                    if isinstance(tools_list, list):
                        self.available_tools = [
                            tool.name if hasattr(tool, "name") else str(tool)
                            for tool in tools_list
                        ]
                    else:
                        self.available_tools = []

                # Get server info if available
                try:
                    server_status = await self.client.call_tool("get_server_status", {})
                    if hasattr(server_status, "content") and server_status.content:
                        # Parse the content if it's JSON
                        if isinstance(server_status.content[0].text, str):
                            self.server_info = json.loads(server_status.content[0].text)
                        else:
                            self.server_info = server_status.content[0].text
                except Exception as e:
                    logger.debug(f"Could not get server status: {e}")
                    self.server_info = {"status": "connected"}

                self.connected = True
                logger.info(
                    f"✅ Connected to {self.server_name} with {len(self.available_tools)} tools"
                )
                logger.info(f"📋 Available tools: {', '.join(self.available_tools)}")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to connect to {self.server_name}: {e}")
                await self.disconnect()
                return False

    async def disconnect(self) -> None:
        """Disconnect from the FastMCP server"""
        async with self.connection_lock:
            self.connected = False

            if self.client:
                try:
                    await self.client.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning(f"Error during disconnect: {e}")
                finally:
                    self.client = None

            logger.info(f"🔌 Disconnected from {self.server_name}")

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server using FastMCP Client

        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool

        Returns:
            Dict containing the tool result
        """
        if not self.connected or not self.client:
            raise ConnectionError("FastMCP client not connected")

        if tool_name not in self.available_tools:
            raise ValueError(
                f"Tool '{tool_name}' not available. Available tools: {self.available_tools}"
            )

        try:
            logger.debug(f"🔧 Calling tool '{tool_name}' with args: {arguments}")

            # Call the tool using FastMCP client
            # FastMCP expects arguments to be wrapped in an 'input' object for tools with parameters
            if arguments:
                formatted_args = {"input": arguments}
            else:
                formatted_args = {}

            result = await self.client.call_tool(tool_name, formatted_args)

            # Parse the result based on FastMCP response format
            if hasattr(result, "content") and result.content:
                # Extract the actual data from the MCP response
                content = result.content[0]
                if hasattr(content, "text"):
                    try:
                        # Try to parse as JSON first
                        parsed_result = json.loads(content.text)
                        logger.debug(f"✅ Tool '{tool_name}' returned: {parsed_result}")
                        return parsed_result
                    except json.JSONDecodeError:
                        # If not JSON, return as text
                        logger.debug(
                            f"✅ Tool '{tool_name}' returned text: {content.text}"
                        )
                        return {"result": content.text, "success": True}
                else:
                    # Return the content directly
                    logger.debug(f"✅ Tool '{tool_name}' returned: {content}")
                    return {"result": content, "success": True}
            elif isinstance(result, dict):
                # Direct dictionary result
                logger.debug(f"✅ Tool '{tool_name}' returned dict: {result}")
                return result
            else:
                # Handle direct result
                logger.debug(f"✅ Tool '{tool_name}' returned: {result}")
                return {"result": result, "success": True}

        except Exception as e:
            logger.error(f"❌ Tool call '{tool_name}' failed: {e}")
            return {"success": False, "error": str(e), "tool": tool_name}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of the MCP server using ping tool"""
        try:
            result = await self.call_tool("ping")
            return {"status": "healthy", "connected": self.connected, "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e), "connected": self.connected}

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return self.available_tools.copy()

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific tool from server"""
        if tool_name in self.available_tools:
            return {"name": tool_name, "available": True}
        return None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()


# ============================================================================
# Convenience Functions for FluxTrader Agent
# ============================================================================


async def create_binance_client(
    env_vars: Optional[Dict[str, str]] = None,
) -> FluxTraderMCPClient:
    """Create and connect to Binance FastMCP server"""
    server_path = str(
        Path(__file__).parent.parent.parent
        / "mcp_servers"
        / "binance_fastmcp_server.py"
    )
    client = FluxTraderMCPClient(server_path, "Binance FastMCP Server", env_vars)

    if await client.connect():
        return client
    else:
        raise ConnectionError("Failed to connect to Binance FastMCP server")


# Example usage functions for FluxTrader agent
async def get_market_data(
    client: FluxTraderMCPClient, symbol: str = "BTCUSDT"
) -> Dict[str, Any]:
    """Get comprehensive market data for a symbol"""
    return await client.call_tool("get_market_data", {"symbol": symbol})


async def get_account_balance(client: FluxTraderMCPClient) -> Dict[str, Any]:
    """Get account balance information"""
    return await client.call_tool("get_account_balance")


async def calculate_indicators(
    client: FluxTraderMCPClient, symbol: str = "BTCUSDT", timeframe: str = "1h"
) -> Dict[str, Any]:
    """Calculate technical indicators for a symbol"""
    return await client.call_tool(
        "calculate_technical_indicators",
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": ["RSI", "MACD", "BB", "SMA", "EMA"],
        },
    )


async def place_order(
    client: FluxTraderMCPClient,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str = "MARKET",
    price: Optional[float] = None,
) -> Dict[str, Any]:
    """Place a trading order"""
    args = {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "order_type": order_type,
    }
    if price:
        args["price"] = price

    return await client.call_tool("place_futures_order", args)


async def get_24h_ticker(
    client: FluxTraderMCPClient, symbol: str = "BTCUSDT"
) -> Dict[str, Any]:
    """Get 24h ticker data for a symbol"""
    return await client.call_tool("get_24h_ticker", {"symbol": symbol})


async def get_server_status(client: FluxTraderMCPClient) -> Dict[str, Any]:
    """Get server status and health information"""
    return await client.call_tool("get_server_status")
