"""
SQLite database connection for billa-agent (fallback when PostgreSQL is not available)
"""

import os
import sqlite3
from typing import Optional, List, Tuple, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SQLiteDatabaseConnection:
    """SQLite database connection manager (fallback for PostgreSQL)."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize SQLite database connection manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default to demo_users.db in the billa-agent directory
            self.db_path = Path(__file__).parent.parent.parent / "demo_users.db"
        else:
            self.db_path = Path(db_path)
        
        self.connection = None
    
    def initialize_pool(self) -> bool:
        """Initialize the database connection.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if database file exists
            if not self.db_path.exists():
                logger.error(f"SQLite database file not found: {self.db_path}")
                return False
            
            # Test connection
            test_conn = sqlite3.connect(str(self.db_path))
            test_conn.close()
            
            logger.info(f"SQLite Database Connection Established: {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing SQLite database connection: {e}")
            return False
    
    def get_connection(self):
        """Get a database connection.
        
        Returns:
            Database connection
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row  # Enable column access by name
            return conn
        except Exception as e:
            logger.error(f"Error getting SQLite connection: {e}")
            raise
    
    def release_connection(self, connection):
        """Release a connection (close it for SQLite).
        
        Args:
            connection: Database connection to release
        """
        if connection:
            connection.close()
    
    def close_all_connections(self):
        """Close all connections (no-op for SQLite)."""
        logger.info("SQLite connections closed")
    
    def execute_query(self, query: str, params=None):
        """Execute a query and return the results.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            Query results
        """
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            
            # Convert PostgreSQL-style placeholders (%s) to SQLite-style (?)
            sqlite_query = query.replace('%s', '?')
            
            cursor.execute(sqlite_query, params or ())
            connection.commit()
            
            try:
                results = cursor.fetchall()
                # Convert sqlite3.Row objects to tuples for compatibility
                return [tuple(row) for row in results] if results else None
            except Exception:
                # No results to fetch (e.g., for INSERT, UPDATE, DELETE)
                return None
                
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Error executing SQLite query: {e}")
            raise
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.release_connection(connection)
    
    def execute_query_one(self, query: str, params=None):
        """Execute a query and return the first result.
        
        Args:
            query: SQL query to execute
            params: Query parameters
            
        Returns:
            First query result or None
        """
        results = self.execute_query(query, params)
        return results[0] if results else None
    
    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.
        
        Args:
            table_name: Name of the table to check
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            check_query = """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name = ?;
            """
            result = self.execute_query_one(check_query, (table_name,))
            return result is not None
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False


# Global SQLite database connection instance
sqlite_db_connection = SQLiteDatabaseConnection()
