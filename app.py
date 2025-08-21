#!/usr/bin/env python3
"""
Kamikaze AI Backend Application
Entry point for starting the FastAPI backend with FluxTrader integration.

This application manages:
- FastAPI backend server on port 8000
- FluxTrader trading bot integration
- Agent management and trading operations
- Real-time WebSocket communication

Usage:
    python backend_app.py                # Start backend with FluxTrader integration
    python backend_app.py --port 8000    # Start with custom port
    python backend_app.py --host 0.0.0.0 # Start with custom host
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Load configuration from AWS Secrets Manager
try:
    from src.infrastructure.config_loader import initialize_config

    initialize_config()
    print("✅ Configuration initialized successfully")
except ImportError:
    print("⚠️ Configuration system not available, using system environment variables only")
except Exception as e:
    print(f"⚠️ Failed to initialize configuration: {e}")
    print("⚠️ Using system environment variables only")

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_requested = False
mcp_server_process = None
fastapi_process = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global shutdown_requested
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_requested = True


class KamikazeAIBackend:
    """Main backend application class."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        self.host = host
        self.port = port
        self.mcp_server_process = None
        self.postgres_mcp_process = None
        self.fastapi_process = None
        self.running = False

        # Setup signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        logger.info("Kamikaze AI Backend Application initialized")

    def start_binance_fastmcp_server(self):
        """Start the Binance FastMCP server in a separate process."""
        try:
            logger.info("🔧 Starting Binance FastMCP Server...")

            # Path to the Binance FastMCP server
            mcp_server_path = (
                Path(__file__).parent
                / "src"
                / "mcp_servers"
                / "binance_fastmcp_server.py"
            )

            if not mcp_server_path.exists():
                raise FileNotFoundError(
                    f"Binance FastMCP server not found at {mcp_server_path}"
                )

            # Start the MCP server process with environment variables
            env = os.environ.copy()  # Copy current environment variables
            src_path = str(Path(__file__).parent / "src")
            env["PYTHONPATH"] = src_path  # Add src to Python path
            self.mcp_server_process = subprocess.Popen(
                [sys.executable, str(mcp_server_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,  # Pass environment variables to subprocess
            )

            # Give the server a moment to start
            time.sleep(2)

            # Check if the process is still running
            if self.mcp_server_process.poll() is None:
                logger.info("✅ Binance FastMCP Server started successfully")
                return True
            else:
                # Process died, get error output
                stdout, stderr = self.mcp_server_process.communicate()
                logger.error(f"❌ Binance FastMCP Server failed to start")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to start Binance FastMCP Server: {e}")
            return False

    def start_postgres_fastmcp_server(self):
        """Start the PostgreSQL FastMCP server in a separate process."""
        try:
            logger.info("🔧 Starting PostgreSQL FastMCP Server...")

            # Path to the PostgreSQL FastMCP server
            postgres_mcp_server_path = (
                Path(__file__).parent
                / "src"
                / "mcp_servers"
                / "postgres_fastmcp_server.py"
            )

            if not postgres_mcp_server_path.exists():
                raise FileNotFoundError(
                    f"PostgreSQL FastMCP server not found at {postgres_mcp_server_path}"
                )

            # Start the PostgreSQL MCP server process with environment variables
            env = os.environ.copy()  # Copy current environment variables
            self.postgres_mcp_process = subprocess.Popen(
                [sys.executable, str(postgres_mcp_server_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env,  # Pass environment variables to subprocess
            )

            # Give the server a moment to start
            time.sleep(2)

            # Check if the process is still running
            if self.postgres_mcp_process.poll() is None:
                logger.info("✅ PostgreSQL FastMCP Server started successfully")
                return True
            else:
                # Process died, get error output
                stdout, stderr = self.postgres_mcp_process.communicate()
                logger.error(f"❌ PostgreSQL FastMCP Server failed to start")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to start PostgreSQL FastMCP Server: {e}")
            return False

    def start_fastapi_backend(self):
        """Start the FastAPI backend server."""
        try:
            logger.info("🚀 Starting FastAPI Backend Server...")

            # Path to the FastAPI main module
            fastapi_main_path = Path(__file__).parent / "src" / "api" / "main.py"

            if not fastapi_main_path.exists():
                raise FileNotFoundError(
                    f"FastAPI main module not found at {fastapi_main_path}"
                )

            # Start the FastAPI server using uvicorn with visible logs
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "src.api.main:app",
                "--host",
                self.host,
                "--port",
                str(self.port),
                "--reload",
                "--log-level",
                "info",
                "--access-log",
            ]

            # Start process without capturing output so logs are visible
            self.fastapi_process = subprocess.Popen(
                cmd, text=True, bufsize=1, universal_newlines=True
            )

            # Give the server a moment to start
            time.sleep(3)

            # Check if the process is still running
            if self.fastapi_process.poll() is None:
                logger.info(
                    f"✅ FastAPI Backend Server started successfully on {self.host}:{self.port}"
                )
                logger.info("📋 FastAPI logs will be displayed below:")
                return True
            else:
                logger.error(f"❌ FastAPI Backend Server failed to start")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to start FastAPI Backend Server: {e}")
            return False

    def monitor_processes(self):
        """Monitor all processes and restart if needed."""
        restart_count = {}  # Track restart attempts to prevent loops
        max_restarts = 3  # Maximum restarts per process

        while self.running and not shutdown_requested:
            try:
                # Check Binance MCP server - with longer intervals to prevent spam
                if (
                    self.mcp_server_process
                    and self.mcp_server_process.poll() is not None
                ):
                    process_name = "binance_mcp"
                    restart_count.setdefault(process_name, 0)

                    if restart_count[process_name] < max_restarts:
                        logger.warning(
                            f"⚠️ Binance FastMCP Server process died, restarting... (attempt {restart_count[process_name] + 1}/{max_restarts})"
                        )
                        # Wait longer between restart attempts to prevent spam
                        time.sleep(30)  # Wait 30 seconds before restart
                        if self.start_binance_fastmcp_server():
                            restart_count[process_name] += 1
                        else:
                            logger.error("❌ Failed to restart Binance FastMCP Server")
                            restart_count[process_name] = max_restarts  # Stop trying
                    else:
                        logger.error(
                            f"❌ Binance FastMCP Server exceeded maximum restart attempts ({max_restarts})"
                        )
                        # Set process to None to stop checking
                        self.mcp_server_process = None

                # Check PostgreSQL MCP server (disabled temporarily)
                # TODO: Re-enable when PostgreSQL connection issues are fixed
                # if self.postgres_mcp_process and self.postgres_mcp_process.poll() is not None:
                #     process_name = "postgres_mcp"
                #     restart_count.setdefault(process_name, 0)
                #
                #     if restart_count[process_name] < max_restarts:
                #         logger.warning(f"⚠️ PostgreSQL FastMCP Server process died, restarting... (attempt {restart_count[process_name] + 1}/{max_restarts})")
                #         if self.start_postgres_fastmcp_server():
                #             restart_count[process_name] += 1
                #         else:
                #             logger.error("❌ Failed to restart PostgreSQL FastMCP Server")
                #             restart_count[process_name] = max_restarts  # Stop trying
                #     else:
                #         logger.error(f"❌ PostgreSQL FastMCP Server exceeded maximum restart attempts ({max_restarts})")

                # Check FastAPI server (but don't restart it as uvicorn handles this)
                if self.fastapi_process and self.fastapi_process.poll() is not None:
                    logger.info(
                        "ℹ️ FastAPI Backend Server stopped (uvicorn handles restarts)"
                    )

                time.sleep(10)  # Check every 10 seconds (reduced frequency)

            except Exception as e:
                logger.error(f"Error in process monitoring: {e}")
                time.sleep(10)

    async def start(self):
        """Start the complete backend system."""
        try:
            logger.info("🚀 Starting Kamikaze AI Backend System")
            logger.info("=" * 60)

            # Start Binance FastMCP Server first
            if not self.start_binance_fastmcp_server():
                raise Exception("Failed to start Binance FastMCP Server")

            # PostgreSQL FastMCP Server - Using Hybrid Approach
            # DISABLED: Using direct database connections for critical operations
            # This provides better performance and stability for multi-agentic system
            # PostgreSQL MCP will be re-enabled later for analytics operations only
            logger.info(
                "📊 PostgreSQL FastMCP Server disabled - using direct database for critical operations"
            )
            logger.info(
                "🔄 Hybrid approach: Direct DB for performance, MCP for analytics (future)"
            )

            # Start FastAPI Backend Server
            if not self.start_fastapi_backend():
                raise Exception("Failed to start FastAPI Backend Server")

            self.running = True

            logger.info("✅ Kamikaze AI Backend System started successfully!")
            logger.info("=" * 60)
            logger.info(f"🌐 FastAPI Backend: http://{self.host}:{self.port}")
            logger.info(f"📡 Binance FastMCP Server: Running")
            logger.info(f"🗄️ PostgreSQL FastMCP Server: Disabled (temporarily)")
            logger.info(f"🎯 Frontend should connect to: http://localhost:{self.port}")
            logger.info("=" * 60)

            # Start process monitoring in a separate thread
            monitor_thread = threading.Thread(
                target=self.monitor_processes, daemon=True
            )
            monitor_thread.start()

            # Keep running until shutdown is requested
            while self.running and not shutdown_requested:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"❌ Failed to start FluxTrader Backend System: {e}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Shutdown the backend system."""
        if not self.running:
            return

        logger.info("🛑 Shutting down FluxTrader Backend System...")
        self.running = False

        try:
            # Stop FastAPI server
            if self.fastapi_process:
                logger.info("📡 Stopping FastAPI Backend Server...")
                self.fastapi_process.terminate()
                try:
                    self.fastapi_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("FastAPI server didn't stop gracefully, killing...")
                    self.fastapi_process.kill()

            # Stop Binance MCP server
            if self.mcp_server_process:
                logger.info("📡 Stopping Binance FastMCP Server...")
                self.mcp_server_process.terminate()
                try:
                    self.mcp_server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "Binance MCP server didn't stop gracefully, killing..."
                    )
                    self.mcp_server_process.kill()

            # Stop PostgreSQL MCP server
            if self.postgres_mcp_process:
                logger.info("🗄️ Stopping PostgreSQL FastMCP Server...")
                self.postgres_mcp_process.terminate()
                try:
                    self.postgres_mcp_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(
                        "PostgreSQL MCP server didn't stop gracefully, killing..."
                    )
                    self.postgres_mcp_process.kill()

            # Kill any remaining MCP server processes to prevent duplicates
            try:
                import subprocess

                logger.info("🧹 Cleaning up any remaining MCP server processes...")
                subprocess.run(
                    ["pkill", "-f", "binance_fastmcp_server.py"], check=False
                )
                subprocess.run(
                    ["pkill", "-f", "postgres_fastmcp_server.py"], check=False
                )
            except Exception as cleanup_error:
                logger.warning(f"Cleanup warning: {cleanup_error}")

            logger.info("✅ Kamikaze AI Backend System shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Kamikaze AI Backend System")
    parser.add_argument("--port", type=int, default=8000, help="FastAPI server port")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="FastAPI server host"
    )

    args = parser.parse_args()

    # Create and start backend application
    backend = KamikazeAIBackend(host=args.host, port=args.port)

    try:
        await backend.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Backend application error: {e}")
        sys.exit(1)
    finally:
        await backend.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 FluxTrader Backend terminated by user")
    except Exception as e:
        logger.error(f"\n❌ FluxTrader Backend failed: {e}")
        sys.exit(1)
