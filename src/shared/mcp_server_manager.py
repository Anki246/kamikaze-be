"""
MCP Server Manager for Enhanced Billa AI Trading Bot
Manages the lifecycle of MCP servers including startup, shutdown, health checks, and status monitoring.
"""

import asyncio
import logging
import subprocess
import sys
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ServerStatus(Enum):
    """MCP Server status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    STOPPING = "stopping"


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    module_path: str
    port: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    status: ServerStatus = ServerStatus.STOPPED
    last_health_check: Optional[float] = None
    error_message: Optional[str] = None
    start_time: Optional[float] = None


class MCPServerManager:
    """
    Manages multiple MCP servers for FluxTrader.
    Provides server lifecycle management, health monitoring, and status tracking.
    """
    
    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Define available MCP servers
        self._initialize_server_definitions()
    
    def _initialize_server_definitions(self):
        """Initialize the available MCP server definitions."""
        src_path = Path(__file__).parent.parent
        
        self.servers = {
            "binance": MCPServerInfo(
                name="Binance MCP Server",
                module_path=str(src_path / "mcp_servers" / "binance_server.py"),
                port=8001
            ),
            "technical_analysis": MCPServerInfo(
                name="Technical Analysis MCP Server",
                module_path=str(src_path / "mcp_servers" / "technical_analysis_server.py"),
                port=8002
            ),
            "websocket_bridge": MCPServerInfo(
                name="WebSocket HTTP Bridge",
                module_path=str(src_path / "mcp_servers" / "websocket_http_bridge.py"),
                port=8004
            ),
            "postgresql": MCPServerInfo(
                name="PostgreSQL Database MCP Server",
                module_path=str(src_path / "mcp_servers" / "postgres_fastmcp_server.py"),
                port=8003
            )
        }
    
    async def start_server(self, server_id: str) -> bool:
        """Start a specific MCP server."""
        if server_id not in self.servers:
            logger.error(f"Unknown server ID: {server_id}")
            return False

        server = self.servers[server_id]

        if server.status == ServerStatus.RUNNING:
            logger.info(f"Server {server.name} is already running")
            return True

        # First check if server is already running on the port
        if await self._check_server_running(server.port):
            logger.info(f"✅ MCP server {server.name} detected running on port {server.port}")
            server.status = ServerStatus.RUNNING
            server.start_time = time.time()
            server.error_message = None
            return True

        try:
            logger.info(f"Starting MCP server: {server.name}")
            server.status = ServerStatus.STARTING

            # Start the server process
            server.process = await asyncio.create_subprocess_exec(
                sys.executable, server.module_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent
            )

            # Wait a moment for the server to start
            await asyncio.sleep(2)

            # Check if process is still running
            if server.process.returncode is None:
                server.status = ServerStatus.RUNNING
                server.start_time = time.time()
                server.error_message = None
                logger.info(f"✅ MCP server {server.name} started successfully")
                return True
            else:
                server.status = ServerStatus.ERROR
                server.error_message = "Process exited immediately"
                logger.error(f"❌ MCP server {server.name} failed to start")
                return False

        except Exception as e:
            server.status = ServerStatus.ERROR
            server.error_message = str(e)
            logger.error(f"❌ Failed to start MCP server {server.name}: {e}")
            return False
    
    async def stop_server(self, server_id: str) -> bool:
        """Stop a specific MCP server."""
        if server_id not in self.servers:
            logger.error(f"Unknown server ID: {server_id}")
            return False
        
        server = self.servers[server_id]
        
        if server.status == ServerStatus.STOPPED:
            logger.info(f"Server {server.name} is already stopped")
            return True
        
        try:
            logger.info(f"Stopping MCP server: {server.name}")
            server.status = ServerStatus.STOPPING
            
            if server.process:
                server.process.terminate()
                
                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(server.process.wait(), timeout=10)
                except asyncio.TimeoutError:
                    logger.warning(f"Force killing MCP server: {server.name}")
                    server.process.kill()
                    await server.process.wait()
                
                server.process = None
            
            server.status = ServerStatus.STOPPED
            server.start_time = None
            server.error_message = None
            logger.info(f"✅ MCP server {server.name} stopped successfully")
            return True
            
        except Exception as e:
            server.status = ServerStatus.ERROR
            server.error_message = str(e)
            logger.error(f"❌ Failed to stop MCP server {server.name}: {e}")
            return False
    
    async def start_all_servers(self) -> bool:
        """Start all MCP servers."""
        logger.info("Starting all MCP servers...")
        success = True
        
        for server_id in self.servers:
            if not await self.start_server(server_id):
                success = False
        
        if success:
            logger.info("✅ All MCP servers started successfully")
            self.running = True
            # Start health check monitoring
            self.health_check_task = asyncio.create_task(self._health_check_loop())
        else:
            logger.error("❌ Some MCP servers failed to start")
        
        return success
    
    async def stop_all_servers(self) -> bool:
        """Stop all MCP servers."""
        logger.info("Stopping all MCP servers...")
        self.running = False
        
        # Stop health check monitoring
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
        
        success = True
        for server_id in self.servers:
            if not await self.stop_server(server_id):
                success = False
        
        if success:
            logger.info("✅ All MCP servers stopped successfully")
        else:
            logger.error("❌ Some MCP servers failed to stop properly")
        
        return success
    
    async def get_server_status(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific server."""
        if server_id not in self.servers:
            return None
        
        server = self.servers[server_id]
        
        return {
            "name": server.name,
            "status": server.status.value,
            "port": server.port,
            "uptime": time.time() - server.start_time if server.start_time else 0,
            "last_health_check": server.last_health_check,
            "error_message": server.error_message,
            "process_id": server.process.pid if server.process else None
        }
    
    async def get_all_servers_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all servers."""
        status = {}
        for server_id in self.servers:
            status[server_id] = await self.get_server_status(server_id)
        return status

    def get_status(self) -> Dict[str, Any]:
        """Get overall status of the MCP server manager."""
        total_servers = len(self.servers)
        healthy_servers = sum(1 for server in self.servers.values()
                            if server.status == ServerStatus.RUNNING)

        return {
            "running": self.running,
            "total_servers": total_servers,
            "healthy_servers": healthy_servers,
            "failed_servers": total_servers - healthy_servers,
            "servers": {server_id: server.status.name for server_id, server in self.servers.items()}
        }
    
    async def health_check(self, server_id: str) -> bool:
        """Perform health check on a specific server."""
        if server_id not in self.servers:
            return False
        
        server = self.servers[server_id]
        
        if server.status != ServerStatus.RUNNING or not server.process:
            return False
        
        try:
            # Check if process is still alive
            if server.process.returncode is not None:
                server.status = ServerStatus.ERROR
                server.error_message = f"Process exited with code {server.process.returncode}"
                return False
            
            server.last_health_check = time.time()
            return True
            
        except Exception as e:
            server.status = ServerStatus.ERROR
            server.error_message = str(e)
            logger.error(f"Health check failed for {server.name}: {e}")
            return False
    
    async def _health_check_loop(self):
        """Background task for periodic health checks."""
        while self.running:
            try:
                for server_id in self.servers:
                    await self.health_check(server_id)
                
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)
    
    def is_all_servers_running(self) -> bool:
        """Check if all servers are running."""
        return all(
            server.status == ServerStatus.RUNNING 
            for server in self.servers.values()
        )
    
    def get_running_servers_count(self) -> int:
        """Get count of running servers."""
        return sum(
            1 for server in self.servers.values()
            if server.status == ServerStatus.RUNNING
        )

    async def _check_server_running(self, port: int) -> bool:
        """Check if a server is already running on the specified port."""
        try:
            import aiohttp
            timeout = aiohttp.ClientTimeout(total=2)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f"http://localhost:{port}/health") as response:
                    return response.status == 200
        except Exception:
            return False
