"""
Database connection and management for billa-agent
Migrated and enhanced from Kamikaze-Bot
"""

import os
import psycopg2
import psycopg2.pool
from typing import Optional, List, Tuple, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Import SQLite fallback
try:
    from .sqlite_database import SQLiteDatabaseConnection
except ImportError:
    SQLiteDatabaseConnection = None


class DatabaseConnection:
    """Database connection manager with connection pooling."""
    
    def __init__(self, min_connections: int = 1, max_connections: int = 10):
        """Initialize database connection manager.
        
        Args:
            min_connections: Minimum number of connections in pool
            max_connections: Maximum number of connections in pool
        """
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.connection_pool = None
    
    def initialize_pool(self) -> bool:
        """Initialize the database connection pool.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load environment variables
            load_dotenv()
            
            # Get database configuration from environment variables
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "5432")
            db_name = os.getenv("DB_NAME", "billa_agent")
            db_user = os.getenv("DB_USER", "postgres")
            db_password = os.getenv("DB_PASSWORD", "")
            
            # Create connection pool
            self.connection_pool = psycopg2.pool.ThreadedConnectionPool(
                self.min_connections,
                self.max_connections,
                host=db_host,
                port=db_port,
                dbname=db_name,
                user=db_user,
                password=db_password
            )
            
            # Log connection info without sensitive details
            logger.info("Database Connection Established")
            logger.info(f"Connected to database '{db_name}' with connection pool ({self.min_connections}-{self.max_connections})")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database connection pool: {e}")
            return False
    
    def get_connection(self):
        """Get a connection from the pool.
        
        Returns:
            Database connection
        """
        if not self.connection_pool:
            if not self.initialize_pool():
                raise Exception("Failed to initialize database connection pool")
        
        return self.connection_pool.getconn()
    
    def release_connection(self, connection):
        """Release a connection back to the pool.
        
        Args:
            connection: Database connection to release
        """
        if self.connection_pool:
            self.connection_pool.putconn(connection)
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Closed all database connections")
    
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
            
            cursor.execute(query, params or ())
            connection.commit()
            
            try:
                results = cursor.fetchall()
                return results
            except psycopg2.ProgrammingError:
                # No results to fetch (e.g., for INSERT, UPDATE, DELETE)
                return None
                
        except Exception as e:
            if connection:
                connection.rollback()
            logger.error(f"Error executing query: {e}")
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
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """
            result = self.execute_query_one(check_query, (table_name,))
            return result[0] if result else False
        except Exception as e:
            logger.error(f"Error checking if table {table_name} exists: {e}")
            return False


# Global database connection instance
db_connection = DatabaseConnection()
