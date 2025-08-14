#!/usr/bin/env python3
"""
Database Initialization Script for FluxTrader
Creates tables, indexes, and initial data for the PostgreSQL database
"""

import asyncio
import asyncpg
import logging
from typing import Optional

from .database_config import db_config, SCHEMA_DEFINITIONS, INDEX_DEFINITIONS

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseInitializer:
    """Database initialization and schema management."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> bool:
        """Connect to PostgreSQL database."""
        try:
            self.pool = await asyncpg.create_pool(**db_config.connection_params)
            
            # Test connection
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info(f"✅ Connected to database: {db_config.database}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            return False
    
    async def disconnect(self):
        """Close database connection."""
        if self.pool:
            await self.pool.close()
            logger.info("🔌 Disconnected from database")
    
    async def create_tables(self) -> bool:
        """Create all required tables."""
        try:
            if not self.pool:
                raise Exception("Database not connected")
            
            async with self.pool.acquire() as conn:
                for table_name, schema_sql in SCHEMA_DEFINITIONS.items():
                    logger.info(f"Creating table: {table_name}")
                    await conn.execute(schema_sql)
                    logger.info(f"✅ Table {table_name} created successfully")
            
            logger.info("✅ All tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            return False
    
    async def create_indexes(self) -> bool:
        """Create all required indexes."""
        try:
            if not self.pool:
                raise Exception("Database not connected")
            
            async with self.pool.acquire() as conn:
                for index_sql in INDEX_DEFINITIONS:
                    logger.info(f"Creating index: {index_sql}")
                    await conn.execute(index_sql)
            
            logger.info("✅ All indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create indexes: {e}")
            return False
    
    async def insert_sample_data(self) -> bool:
        """Insert sample data for testing."""
        try:
            if not self.pool:
                raise Exception("Database not connected")
            
            async with self.pool.acquire() as conn:
                # Insert sample user
                await conn.execute("""
                    INSERT INTO users (username, email, password_hash, full_name, role)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (email) DO NOTHING
                """, "demo_user", "demo@kamikaze.com", "hashed_password", "Demo User", "trader")
                
                # Insert sample trading agent
                user_id = await conn.fetchval("SELECT id FROM users WHERE email = $1", "demo@kamikaze.com")
                if user_id:
                    await conn.execute("""
                        INSERT INTO trading_agents (user_id, agent_name, strategy_type, configuration)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT DO NOTHING
                    """, user_id, "Demo Agent", "pump_dump", '{"leverage": 20, "trade_amount": 4.0}')
            
            logger.info("✅ Sample data inserted successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert sample data: {e}")
            return False
    
    async def check_database_health(self) -> dict:
        """Check database health and return status."""
        try:
            if not self.pool:
                return {"status": "disconnected", "error": "No database connection"}
            
            async with self.pool.acquire() as conn:
                # Check database version
                version = await conn.fetchval("SELECT version()")
                
                # Check table count
                table_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                
                # Check connection count
                connection_count = await conn.fetchval("""
                    SELECT count(*) FROM pg_stat_activity 
                    WHERE datname = $1
                """, db_config.database)
                
                return {
                    "status": "healthy",
                    "version": version,
                    "tables": table_count,
                    "connections": connection_count,
                    "database": db_config.database
                }
                
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def initialize_database(self) -> bool:
        """Complete database initialization."""
        logger.info("🚀 Starting database initialization...")
        
        if not await self.connect():
            return False
        
        try:
            # Create tables
            if not await self.create_tables():
                return False
            
            # Create indexes
            if not await self.create_indexes():
                return False
            
            # Insert sample data
            if not await self.insert_sample_data():
                logger.warning("⚠️ Failed to insert sample data, continuing...")
            
            logger.info("✅ Database initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
        finally:
            await self.disconnect()

async def main():
    """Main function to run database initialization."""
    initializer = DatabaseInitializer()
    success = await initializer.initialize_database()
    
    if success:
        print("✅ Database initialization completed successfully!")
    else:
        print("❌ Database initialization failed!")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
