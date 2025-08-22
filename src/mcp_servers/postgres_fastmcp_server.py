#!/usr/bin/env python3
"""
PostgreSQL FastMCP Server for FluxTrader
Provides comprehensive database operations using FastMCP framework

Features:
- Database health monitoring
- Table listing and schema inspection
- CRUD operations (Create, Read, Update, Delete)
- Query execution with safety checks
- Connection pooling and management
- Transaction support
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import asyncpg

# Pydantic imports for input validation
from pydantic import BaseModel, Field

# Load configuration from AWS Secrets Manager
try:
    # Add parent directory to path to import config_loader
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))

    from infrastructure.config_loader import initialize_config

    initialize_config()
    print("✅ PostgreSQL FastMCP Server: Configuration initialized successfully")
except ImportError:
    print(
        "⚠️ PostgreSQL FastMCP Server: Configuration system not available, using system environment variables only"
    )
except Exception as e:
    print(f"⚠️ PostgreSQL FastMCP Server: Failed to initialize configuration: {e}")
    print("⚠️ PostgreSQL FastMCP Server: Using system environment variables only")


# FastMCP imports
try:
    from fastmcp import FastMCP

    MCP_AVAILABLE = True
except ImportError:
    print("⚠️  FastMCP not available - server will run in mock mode")
    MCP_AVAILABLE = False

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("PostgreSQL FastMCP Server")


# Load configuration from config.json and environment variables
def load_database_config():
    """Load database configuration from environment variables and config.json."""
    try:
        # Load non-sensitive config from config.json
        config_path = Path(__file__).parent.parent.parent / "config.json"
        with open(config_path, "r") as f:
            config = json.load(f)
        db_config_file = config.get("database", {})

        # Import centralized configuration
        try:
            from infrastructure.config_loader import get_config_value

            get_env = get_config_value
        except ImportError:
            get_env = os.getenv

        # Build configuration with centralized configuration system
        db_config = {
            # Sensitive credentials from centralized configuration
            "host": get_env("DB_HOST", "localhost"),
            "port": int(get_env("DB_PORT", "5432")),
            "database": get_env("DB_NAME", "kamikaze"),
            "user": get_env("DB_USER", "postgres"),
            "password": get_env("DB_PASSWORD"),  # No default for security
            # Non-sensitive config from config.json with config override
            "min_size": int(
                get_env("DB_MIN_SIZE", str(db_config_file.get("min_size", 5)))
            ),
            "max_size": int(
                get_env("DB_MAX_SIZE", str(db_config_file.get("max_size", 20)))
            ),
            "command_timeout": int(
                get_env("DB_TIMEOUT", str(db_config_file.get("command_timeout", 60)))
            ),
            "ssl": os.getenv("DB_SSL", "false").lower() == "true"
            or db_config_file.get("ssl", False),
            "pool_recycle": int(
                os.getenv(
                    "DB_POOL_RECYCLE", str(db_config_file.get("pool_recycle", 3600))
                )
            ),
        }

        # Validate that password is provided
        if not db_config["password"]:
            logger.error("❌ DB_PASSWORD environment variable is required but not set!")
            raise ValueError("Database password not provided in environment variables")

        logger.info(
            f"📋 Database config loaded: {db_config['host']}:{db_config['port']}/{db_config['database']} (user: {db_config['user']})"
        )
        return db_config

    except Exception as e:
        logger.error(f"Failed to load database config: {e}")
        raise


# Load database configuration
DATABASE_CONFIG = load_database_config()

# Global connection pool
connection_pool: Optional[asyncpg.Pool] = None


class PostgreSQLManager:
    """PostgreSQL database manager with connection pooling."""

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connected = False
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Establish connection pool to PostgreSQL database."""
        try:
            async with self._connection_lock:
                if self.connected and self.pool:
                    return True

                try:
                    # Close existing pool if any
                    if self.pool:
                        try:
                            await self.pool.close()
                        except Exception as e:
                            logger.warning(f"Error closing existing pool: {e}")

                    self.pool = await asyncpg.create_pool(
                        host=DATABASE_CONFIG["host"],
                        port=DATABASE_CONFIG["port"],
                        database=DATABASE_CONFIG["database"],
                        user=DATABASE_CONFIG["user"],
                        password=DATABASE_CONFIG["password"],
                        min_size=DATABASE_CONFIG["min_size"],
                        max_size=DATABASE_CONFIG["max_size"],
                        command_timeout=DATABASE_CONFIG["command_timeout"],
                    )

                    # Test connection
                    async with self.pool.acquire() as conn:
                        await conn.fetchval("SELECT 1")

                    self.connected = True
                    logger.info(
                        f"✅ Connected to PostgreSQL database: {DATABASE_CONFIG['database']}"
                    )
                    return True

                except Exception as e:
                    logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
                    self.connected = False
                    self.pool = None
                    return False
        except Exception as e:
            logger.error(f"❌ Connection lock error: {e}")
            return False

    async def disconnect(self):
        """Close connection pool."""
        try:
            async with self._connection_lock:
                if self.pool:
                    await self.pool.close()
                    self.pool = None
                self.connected = False
                logger.info("🔌 Disconnected from PostgreSQL database")
        except Exception as e:
            logger.warning(f"Error during disconnect: {e}")
            # Force cleanup even if there's an error
            self.pool = None
            self.connected = False

    async def ensure_connected(self) -> bool:
        """Ensure database connection is available."""
        if not self.connected or not self.pool:
            return await self.connect()

        try:
            # Simple connection test without timeout to avoid event loop issues
            if self.pool and not self.pool._closed:
                # Just check if pool exists and is not closed
                return True
            else:
                logger.warning("Connection pool is closed, reconnecting...")
                self.connected = False
                return await self.connect()
        except Exception as e:
            # Check if it's an event loop issue
            if "Event loop is closed" in str(
                e
            ) or "another operation is in progress" in str(e):
                logger.warning(f"Connection pool issue detected: {e}")
                # Don't try to reconnect immediately, just mark as disconnected
                self.connected = False
                return False
            else:
                logger.warning(f"Connection test failed, reconnecting: {e}")
                self.connected = False
                return await self.connect()

    async def execute_query(
        self, query: str, params: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results."""
        if not await self.ensure_connected():
            raise Exception("Failed to establish database connection")

        try:
            async with self.pool.acquire() as conn:
                if params:
                    rows = await conn.fetch(query, *params)
                else:
                    rows = await conn.fetch(query)

                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            # Try to reconnect for next operation
            self.connected = False
            raise

    async def execute_command(self, command: str, params: Optional[List] = None) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status."""
        if not await self.ensure_connected():
            raise Exception("Failed to establish database connection")

        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.execute(command, *params)
                else:
                    result = await conn.execute(command)

                return result
        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            # Try to reconnect for next operation
            self.connected = False
            raise


# Initialize database manager
db_manager = PostgreSQLManager()

# ============================================================================
# Pydantic Models for Input Validation
# ============================================================================


class TableNameInput(BaseModel):
    """Input model for table name operations."""

    table_name: str = Field(description="Name of the database table")


class QueryInput(BaseModel):
    """Input model for query execution."""

    query: str = Field(description="SQL query to execute")
    params: Optional[List] = Field(default=None, description="Query parameters")
    limit: int = Field(default=100, description="Maximum number of rows to return")


class InsertRecordInput(BaseModel):
    """Input model for record insertion."""

    table_name: str = Field(description="Name of the database table")
    data: Dict[str, Any] = Field(description="Data to insert as key-value pairs")


class UpdateRecordInput(BaseModel):
    """Input model for record updates."""

    table_name: str = Field(description="Name of the database table")
    data: Dict[str, Any] = Field(description="Data to update as key-value pairs")
    where_clause: str = Field(description="WHERE clause for the update")
    where_params: Optional[List] = Field(
        default=None, description="Parameters for WHERE clause"
    )


class DeleteRecordInput(BaseModel):
    """Input model for record deletion."""

    table_name: str = Field(description="Name of the database table")
    where_clause: str = Field(description="WHERE clause for the deletion")
    where_params: Optional[List] = Field(
        default=None, description="Parameters for WHERE clause"
    )


@mcp.tool()
async def ping() -> Dict[str, Any]:
    """Simple ping tool to test PostgreSQL MCP server connectivity"""
    return {
        "status": "pong",
        "server": "PostgreSQL FastMCP Server",
        "timestamp": time.time(),
        "version": "1.0.0",
        "database_connected": db_manager.connected,
    }


@mcp.tool()
async def get_database_health() -> Dict[str, Any]:
    """Get comprehensive database health information"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        # Get database version
        version_result = await db_manager.execute_query("SELECT version()")
        version = version_result[0]["version"] if version_result else "Unknown"

        # Get database size
        db_size_query = "SELECT pg_size_pretty(pg_database_size($1)) as size"
        size_result = await db_manager.execute_query(
            db_size_query, [DATABASE_CONFIG["database"]]
        )
        db_size = size_result[0]["size"] if size_result else "Unknown"

        # Get connection count
        connection_query = """
            SELECT count(*) as count FROM pg_stat_activity
            WHERE datname = $1
        """
        conn_result = await db_manager.execute_query(
            connection_query, [DATABASE_CONFIG["database"]]
        )
        connection_count = conn_result[0]["count"] if conn_result else 0

        # Get uptime
        uptime_query = "SELECT now() - pg_postmaster_start_time() as uptime"
        uptime_result = await db_manager.execute_query(uptime_query)
        uptime = str(uptime_result[0]["uptime"]) if uptime_result else "Unknown"

        return {
            "success": True,
            "database": DATABASE_CONFIG["database"],
            "host": DATABASE_CONFIG["host"],
            "port": DATABASE_CONFIG["port"],
            "version": version,
            "size": db_size,
            "connections": connection_count,
            "uptime": uptime,
            "pool_size": db_manager.pool._queue.qsize() if db_manager.pool else 0,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"success": False, "error": f"Health check failed: {str(e)}"}


@mcp.tool()
async def list_tables() -> Dict[str, Any]:
    """List all tables in the database with their details"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        query = """
            SELECT
                schemaname,
                tablename,
                tableowner,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables pt
            WHERE schemaname NOT IN ('information_schema', 'pg_catalog')
            ORDER BY schemaname, tablename
        """

        tables = await db_manager.execute_query(query)

        return {
            "success": True,
            "tables": tables,
            "count": len(tables),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        return {"success": False, "error": f"Failed to list tables: {str(e)}"}


@mcp.tool()
async def get_table_schema(input: TableNameInput) -> Dict[str, Any]:
    """Get detailed schema information for a specific table"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_name = $1
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """

        columns = await db_manager.execute_query(query, [input.table_name])

        if not columns:
            return {"success": False, "error": f"Table '{input.table_name}' not found"}

        return {
            "success": True,
            "table_name": input.table_name,
            "columns": columns,
            "column_count": len(columns),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get table schema: {e}")
        return {"success": False, "error": f"Failed to get table schema: {str(e)}"}


@mcp.tool()
async def execute_select_query(input: QueryInput) -> Dict[str, Any]:
    """Execute a SELECT query with optional parameters and limit"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        # Safety check - only allow SELECT queries
        query_lower = input.query.lower().strip()
        if not query_lower.startswith("select"):
            return {"success": False, "error": "Only SELECT queries are allowed"}

        # Add limit if not present
        query = input.query
        if "limit" not in query_lower:
            query += f" LIMIT {input.limit}"

        results = await db_manager.execute_query(query, input.params)

        return {
            "success": True,
            "query": query,
            "results": results,
            "row_count": len(results),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        return {"success": False, "error": f"Query execution failed: {str(e)}"}


@mcp.tool()
async def insert_record(input: InsertRecordInput) -> Dict[str, Any]:
    """Insert a new record into the specified table"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        # Build INSERT query
        columns = list(input.data.keys())
        placeholders = [f"${i+1}" for i in range(len(columns))]
        values = list(input.data.values())

        query = f"""
            INSERT INTO {input.table_name} ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            RETURNING *
        """

        result = await db_manager.execute_query(query, values)

        return {
            "success": True,
            "table": input.table_name,
            "inserted_record": result[0] if result else None,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to insert record: {e}")
        return {"success": False, "error": f"Insert failed: {str(e)}"}


@mcp.tool()
async def update_record(input: UpdateRecordInput) -> Dict[str, Any]:
    """Update records in the specified table"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        # Build UPDATE query
        set_clauses = []
        values = []
        param_counter = 1

        for column, value in input.data.items():
            set_clauses.append(f"{column} = ${param_counter}")
            values.append(value)
            param_counter += 1

        # Add where parameters
        if input.where_params:
            values.extend(input.where_params)

        query = f"""
            UPDATE {input.table_name}
            SET {', '.join(set_clauses)}
            WHERE {input.where_clause}
            RETURNING *
        """

        results = await db_manager.execute_query(query, values)

        return {
            "success": True,
            "table": input.table_name,
            "updated_records": results,
            "affected_rows": len(results),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        return {"success": False, "error": f"Update failed: {str(e)}"}


@mcp.tool()
async def delete_record(input: DeleteRecordInput) -> Dict[str, Any]:
    """Delete records from the specified table"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        query = f"DELETE FROM {input.table_name} WHERE {input.where_clause}"

        result = await db_manager.execute_command(query, input.where_params)

        # Extract affected rows count from result
        affected_rows = int(result.split()[-1]) if result.startswith("DELETE") else 0

        return {
            "success": True,
            "table": input.table_name,
            "affected_rows": affected_rows,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to delete record: {e}")
        return {"success": False, "error": f"Delete failed: {str(e)}"}


@mcp.tool()
async def get_table_stats(input: TableNameInput) -> Dict[str, Any]:
    """Get statistics for a specific table"""
    try:
        if not await db_manager.ensure_connected():
            return {
                "success": False,
                "error": "Failed to establish database connection",
            }

        # Get row count
        count_query = f"SELECT COUNT(*) as count FROM {input.table_name}"
        row_count = await db_manager.execute_query(count_query)

        # Get table size
        size_query = """
            SELECT pg_size_pretty(pg_total_relation_size($1)) as total_size,
                   pg_size_pretty(pg_relation_size($1)) as table_size,
                   pg_size_pretty(pg_total_relation_size($1) - pg_relation_size($1)) as index_size
        """
        size_info = await db_manager.execute_query(size_query, [input.table_name])

        return {
            "success": True,
            "table_name": input.table_name,
            "row_count": row_count[0]["count"] if row_count else 0,
            "total_size": size_info[0]["total_size"] if size_info else "0 bytes",
            "table_size": size_info[0]["table_size"] if size_info else "0 bytes",
            "index_size": size_info[0]["index_size"] if size_info else "0 bytes",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to get table stats: {e}")
        return {"success": False, "error": f"Failed to get table stats: {str(e)}"}


async def initialize_database():
    """Initialize database connection."""
    logger.info("🚀 Starting PostgreSQL FastMCP Server...")

    # Connect to database
    if await db_manager.connect():
        logger.info("✅ PostgreSQL FastMCP Server ready")

        # Test basic functionality
        try:
            health = await get_database_health()
            if health.get("success"):
                logger.info(
                    f"✅ Database health check passed: {health['data']['database']}"
                )
            else:
                logger.warning(f"⚠️ Database health check failed: {health.get('error')}")
        except Exception as e:
            logger.warning(f"⚠️ Database health check error: {e}")

        return True
    else:
        logger.error("❌ Failed to connect to database")
        return False


if __name__ == "__main__":
    # Global flag to track if we should cleanup
    cleanup_needed = False

    try:
        # Initialize database connection
        if asyncio.run(initialize_database()):
            cleanup_needed = True
            logger.info(
                "✅ All PostgreSQL database functionality integrated with FastMCP protocol"
            )
            logger.info("🌐 Starting FastMCP server...")

            # Run the FastMCP server (this is a blocking call)
            mcp.run()
        else:
            logger.error("❌ Failed to start PostgreSQL FastMCP Server")
            exit(1)

    except KeyboardInterrupt:
        logger.info("👋 PostgreSQL FastMCP Server terminated by user")
    except Exception as e:
        logger.error(f"💥 Server error: {e}")
        exit(1)
    finally:
        # Cleanup database connection if it was initialized
        if cleanup_needed:
            try:
                # Create a new event loop for cleanup if needed
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Run cleanup
                loop.run_until_complete(db_manager.disconnect())

            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
            finally:
                try:
                    if not loop.is_closed():
                        loop.close()
                except Exception:
                    pass
