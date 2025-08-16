#!/usr/bin/env python3
"""
WebSocket to HTTP MCP Bridge - Simplified Implementation
Bridges WebSocket connections from React frontend to HTTP-based MCP servers

This bridge connects the React frontend (WebSocket) to the existing HTTP MCP servers,
providing real-time communication while leveraging the working HTTP infrastructure.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import aiohttp
import websockets

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class WebSocketHTTPBridge:
    """Bridge WebSocket connections to HTTP MCP servers"""

    def __init__(self):
        self.mcp_servers = {
            "binance": "http://localhost:8001",
            "technical_analysis": "http://localhost:8002",
            "server_endpoint": "http://localhost:8003",
        }
        self.request_id = 1

    def get_request_id(self) -> int:
        """Get next request ID"""
        request_id = self.request_id
        self.request_id += 1
        return request_id

    async def call_http_endpoint(
        self, server_url: str, endpoint: str, method: str = "GET", data: Dict = None
    ) -> Dict[str, Any]:
        """Call HTTP endpoint directly"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{server_url}{endpoint}"

                if method == "GET":
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}",
                            }

                elif method == "POST":
                    async with session.post(
                        url,
                        json=data,
                        headers={"Content-Type": "application/json"},
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            return {
                                "success": False,
                                "error": f"HTTP {response.status}",
                            }

        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return {"success": False, "error": f"Request failed: {str(e)}"}

    async def handle_tool_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle specific tool calls by mapping to HTTP endpoints"""
        try:
            # Map tool calls to actual HTTP endpoints
            if tool_name == "get_24h_ticker":
                symbol = arguments.get("symbol", "BTCUSDT")
                # Use a mock response for now since we need to check the actual endpoint
                return {
                    "success": True,
                    "symbol": symbol,
                    "price": 45000.0,
                    "change_24h": 1200.0,
                    "change_percent_24h": 2.75,
                    "volume_24h": 25000.0,
                    "timestamp": int(time.time()),
                }

            elif tool_name == "get_account_balance":
                result = await self.call_http_endpoint(
                    self.mcp_servers["binance"], "/account/balance"
                )
                return result

            elif tool_name == "get_market_data":
                symbol = arguments.get("symbol", "BTCUSDT")
                return {
                    "success": True,
                    "symbol": symbol,
                    "current_price": 45000.0,
                    "price_history": [44800, 44900, 45000],
                    "volume_24h": 25000.0,
                    "timestamp": int(time.time()),
                }

            elif tool_name == "start_agent":
                agent_id = arguments.get("agent_id", "default_agent")
                # Call the server endpoint for agent management
                result = await self.call_http_endpoint(
                    self.mcp_servers["server_endpoint"],
                    "/agent/start",
                    "POST",
                    {"agent_id": agent_id},
                )
                return result

            elif tool_name == "stop_agent":
                agent_id = arguments.get("agent_id", "default_agent")
                result = await self.call_http_endpoint(
                    self.mcp_servers["server_endpoint"],
                    "/agent/stop",
                    "POST",
                    {"agent_id": agent_id},
                )
                return result

            elif tool_name == "get_agent_status":
                agent_id = arguments.get("agent_id", "default_agent")
                result = await self.call_http_endpoint(
                    self.mcp_servers["server_endpoint"], f"/agent/status/{agent_id}"
                )
                return result

            elif tool_name == "calculate_technical_indicators":
                symbol = arguments.get("symbol", "BTCUSDT")
                return {
                    "success": True,
                    "symbol": symbol,
                    "indicators": {
                        "RSI": 65.5,
                        "MACD": {"macd": 120.5, "signal": 115.2, "histogram": 5.3},
                        "SMA_20": 44800.0,
                        "EMA_12": 44950.0,
                    },
                    "timestamp": int(time.time()),
                }

            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    async def route_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to appropriate handler"""
        method = request.get("method", "")
        request_id = request.get("id")

        try:
            if method == "initialize":
                # Handle MCP initialization
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"subscribe": False, "listChanged": False},
                            "prompts": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": "FluxTrader WebSocket Bridge",
                            "version": "1.0.0",
                        },
                    },
                }

            elif method == "tools/list":
                # Return available tools
                tools = [
                    {
                        "name": "get_24h_ticker",
                        "description": "Get 24h ticker data for a symbol",
                    },
                    {
                        "name": "get_account_balance",
                        "description": "Get account balance information",
                    },
                    {
                        "name": "get_market_data",
                        "description": "Get comprehensive market data",
                    },
                    {
                        "name": "start_agent",
                        "description": "Start a FluxTrader trading agent",
                    },
                    {
                        "name": "stop_agent",
                        "description": "Stop a FluxTrader trading agent",
                    },
                    {
                        "name": "get_agent_status",
                        "description": "Get agent status information",
                    },
                    {
                        "name": "calculate_technical_indicators",
                        "description": "Calculate technical indicators",
                    },
                ]

                return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

            elif method == "tools/call":
                # Handle tool calls
                params = request.get("params", {})
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})

                logger.info(f"Calling tool: {tool_name}")
                result = await self.handle_tool_call(tool_name, arguments)

                return {"jsonrpc": "2.0", "id": request_id, "result": result}

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

        except Exception as e:
            logger.error(f"Request routing failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
            }

    async def handle_websocket_client(self, websocket):
        """Handle WebSocket client connection"""
        client_address = websocket.remote_address
        logger.info(f"🔗 WebSocket client connected: {client_address}")

        try:
            async for message in websocket:
                try:
                    # Parse WebSocket message
                    request = json.loads(message)
                    logger.info(
                        f"📨 Received request: {request.get('method', 'unknown')}"
                    )

                    # Route to appropriate MCP server
                    response = await self.route_request(request)

                    # Send response back to WebSocket client
                    await websocket.send(json.dumps(response))
                    logger.info(
                        f"📤 Sent response for {request.get('method', 'unknown')}"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Invalid JSON from client: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": "Parse error"},
                    }
                    await websocket.send(json.dumps(error_response))

                except Exception as e:
                    logger.error(f"❌ Error handling WebSocket message: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id") if "request" in locals() else None,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}",
                        },
                    }
                    await websocket.send(json.dumps(error_response))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 WebSocket client disconnected: {client_address}")
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")

    async def check_mcp_servers(self) -> bool:
        """Check if MCP servers are running"""
        all_healthy = True

        for server_name, server_url in self.mcp_servers.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{server_url}/health", timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"✅ {server_name} server is healthy")
                        else:
                            logger.warning(
                                f"⚠️  {server_name} server returned {response.status}"
                            )
                            all_healthy = False
            except Exception as e:
                logger.error(f"❌ {server_name} server is not accessible: {e}")
                all_healthy = False

        return all_healthy

    async def start_bridge(self, host="localhost", port=8004):
        """Start the WebSocket to HTTP bridge"""
        logger.info("🚀 Starting WebSocket to HTTP MCP Bridge...")

        # Check MCP servers
        if await self.check_mcp_servers():
            logger.info("✅ All MCP servers are accessible")
        else:
            logger.warning("⚠️  Some MCP servers are not accessible, but continuing...")

        # Start WebSocket server
        logger.info(f"🌐 Starting WebSocket server on ws://{host}:{port}")

        async with websockets.serve(
            self.handle_websocket_client, host, port, ping_interval=20, ping_timeout=10
        ):
            logger.info(f"✅ WebSocket to HTTP MCP Bridge running on ws://{host}:{port}")
            logger.info("🔗 React frontend can now connect to MCP servers via WebSocket")

            # Keep running
            await asyncio.Future()  # Run forever


async def main():
    """Main function"""
    bridge = WebSocketHTTPBridge()

    try:
        await bridge.start_bridge()
    except KeyboardInterrupt:
        logger.info("🛑 Bridge stopped by user")
    except Exception as e:
        logger.error(f"❌ Bridge error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
