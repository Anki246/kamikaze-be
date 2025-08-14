"""
Database API Routes for FluxTrader
Provides REST API endpoints for database operations via PostgreSQL MCP server
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import logging
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.fluxtrader.fastmcp_client import FluxTraderMCPClient

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/database", tags=["Database"])

# Global PostgreSQL MCP client
postgres_client: Optional[FluxTraderMCPClient] = None

async def create_postgres_client(env_vars: Optional[Dict[str, str]] = None) -> FluxTraderMCPClient:
    """Create and connect to PostgreSQL FastMCP server"""
    server_path = str(Path(__file__).parent.parent.parent / "mcp_servers" / "postgres_fastmcp_server.py")
    client = FluxTraderMCPClient(server_path, "PostgreSQL FastMCP Server", env_vars)

    if await client.connect():
        logger.info("✅ Connected to PostgreSQL FastMCP Server")
        return client
    else:
        logger.error("❌ Failed to connect to PostgreSQL FastMCP Server")
        raise HTTPException(status_code=503, detail="PostgreSQL MCP server not available")

async def get_postgres_client() -> FluxTraderMCPClient:
    """Get or create PostgreSQL MCP client."""
    global postgres_client

    if postgres_client is None:
        try:
            postgres_client = await create_postgres_client()
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL FastMCP Server: {e}")
            raise HTTPException(status_code=503, detail="PostgreSQL MCP server not available")

    return postgres_client

@router.get("/health")
async def get_database_health() -> Dict[str, Any]:
    """Get database health information."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the health check tool
        result = await client.call_tool("get_database_health", {})

        return {
            "success": True,
            "data": result,
            "message": "Database health retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to get database health: {e}")
        raise HTTPException(status_code=500, detail=f"Database health check failed: {str(e)}")

@router.get("/tables")
async def list_tables() -> Dict[str, Any]:
    """List all tables in the database."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the list tables tool
        result = await client.call_tool("list_tables", {})

        return {
            "success": True,
            "data": result,
            "message": "Tables listed successfully"
        }

    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")

@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str) -> Dict[str, Any]:
    """Get schema information for a specific table."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the get table schema tool
        result = await client.call_tool("get_table_schema", {"table_name": table_name})

        return {
            "success": True,
            "data": result,
            "message": f"Schema for table '{table_name}' retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to get table schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table schema: {str(e)}")

@router.get("/tables/{table_name}/stats")
async def get_table_stats(table_name: str) -> Dict[str, Any]:
    """Get statistics for a specific table."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the get table stats tool
        result = await client.call_tool("get_table_stats", {"table_name": table_name})

        return {
            "success": True,
            "data": result,
            "message": f"Statistics for table '{table_name}' retrieved successfully"
        }

    except Exception as e:
        logger.error(f"Failed to get table stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get table stats: {str(e)}")

@router.post("/query")
async def execute_query(query_data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a SELECT query with optional parameters."""
    try:
        # Validate input
        if "query" not in query_data:
            raise HTTPException(status_code=400, detail="Query is required")

        query = query_data["query"]
        params = query_data.get("params", [])
        limit = query_data.get("limit", 100)

        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the execute query tool
        result = await client.call_tool("execute_select_query", {
            "query": query,
            "params": params,
            "limit": limit
        })

        return {
            "success": True,
            "data": result,
            "message": "Query executed successfully"
        }

    except Exception as e:
        logger.error(f"Failed to execute query: {e}")
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")

@router.post("/tables/{table_name}/insert")
async def insert_record(table_name: str, record_data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a new record into the specified table."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the insert record tool
        result = await client.call_tool("insert_record", {
            "table_name": table_name,
            "data": record_data
        })

        return {
            "success": True,
            "data": result,
            "message": f"Record inserted into '{table_name}' successfully"
        }

    except Exception as e:
        logger.error(f"Failed to insert record: {e}")
        raise HTTPException(status_code=500, detail=f"Record insertion failed: {str(e)}")

@router.put("/tables/{table_name}/update")
async def update_record(table_name: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update records in the specified table."""
    try:
        # Validate input
        if "data" not in update_data or "where_clause" not in update_data:
            raise HTTPException(status_code=400, detail="Both 'data' and 'where_clause' are required")

        data = update_data["data"]
        where_clause = update_data["where_clause"]
        where_params = update_data.get("where_params", [])

        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the update record tool
        result = await client.call_tool("update_record", {
            "table_name": table_name,
            "data": data,
            "where_clause": where_clause,
            "where_params": where_params
        })

        return {
            "success": True,
            "data": result,
            "message": f"Records in '{table_name}' updated successfully"
        }

    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        raise HTTPException(status_code=500, detail=f"Record update failed: {str(e)}")

@router.delete("/tables/{table_name}/delete")
async def delete_record(table_name: str, delete_data: Dict[str, Any]) -> Dict[str, Any]:
    """Delete records from the specified table."""
    try:
        # Validate input
        if "where_clause" not in delete_data:
            raise HTTPException(status_code=400, detail="'where_clause' is required")

        where_clause = delete_data["where_clause"]
        where_params = delete_data.get("where_params", [])

        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the delete record tool
        result = await client.call_tool("delete_record", {
            "table_name": table_name,
            "where_clause": where_clause,
            "where_params": where_params
        })

        return {
            "success": True,
            "data": result,
            "message": f"Records deleted from '{table_name}' successfully"
        }

    except Exception as e:
        logger.error(f"Failed to delete record: {e}")
        raise HTTPException(status_code=500, detail=f"Record deletion failed: {str(e)}")

@router.get("/ping")
async def ping_database() -> Dict[str, Any]:
    """Ping the PostgreSQL MCP server."""
    try:
        # Get PostgreSQL MCP client
        client = await get_postgres_client()

        # Call the ping tool
        result = await client.call_tool("ping", {})

        return {
            "success": True,
            "data": result,
            "message": "PostgreSQL MCP server is responding"
        }

    except Exception as e:
        logger.error(f"Failed to ping database: {e}")
        raise HTTPException(status_code=500, detail=f"Database ping failed: {str(e)}")
