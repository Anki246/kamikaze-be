#!/usr/bin/env python3
"""
Database Migration Script: Localhost PostgreSQL to AWS RDS
Migrates schema, tables, and data from local PostgreSQL to AWS RDS instance
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import asyncpg

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infrastructure.database_config import (
    INDEX_DEFINITIONS,
    SCHEMA_DEFINITIONS,
    DatabaseConfig,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        ),
    ],
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from localhost PostgreSQL to AWS RDS."""

    def __init__(self):
        self.source_pool: Optional[asyncpg.Pool] = None
        self.target_pool: Optional[asyncpg.Pool] = None
        self.migration_stats = {
            "tables_migrated": 0,
            "rows_migrated": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
        }

    async def connect_databases(self) -> bool:
        """Connect to both source (localhost) and target (RDS) databases."""
        try:
            # Source database (localhost)
            logger.info("🔌 Connecting to source database (localhost)...")
            source_config = DatabaseConfig()
            # Force localhost configuration
            source_config.host = "localhost"
            source_config.port = 5432
            source_config.database = os.getenv("LOCAL_DB_NAME", "kamikaze")
            source_config.user = os.getenv("LOCAL_DB_USER", "postgres")
            source_config.password = os.getenv("LOCAL_DB_PASSWORD", "admin2025")

            self.source_pool = await asyncpg.create_pool(
                **source_config.connection_params
            )

            # Test source connection
            async with self.source_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.info("✅ Connected to source database")

            # Target database (RDS)
            logger.info("🔌 Connecting to target database (RDS)...")
            target_config = DatabaseConfig()
            # Force RDS configuration from environment variables
            target_config.host = os.getenv("DB_HOST")
            target_config.port = int(os.getenv("DB_PORT", "5432"))
            target_config.database = os.getenv("DB_NAME", "kamikaze")
            target_config.user = os.getenv("DB_USER")
            target_config.password = os.getenv("DB_PASSWORD")
            target_config.ssl_mode = "require"

            if not all(
                [target_config.host, target_config.user, target_config.password]
            ):
                raise ValueError(
                    "RDS credentials not provided. Set DB_HOST, DB_USER, DB_PASSWORD environment variables."
                )

            self.target_pool = await asyncpg.create_pool(
                **target_config.connection_params
            )

            # Test target connection
            async with self.target_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            logger.info("✅ Connected to target database (RDS)")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect to databases: {e}")
            return False

    async def get_table_list(self) -> List[str]:
        """Get list of tables from source database."""
        try:
            async with self.source_pool.acquire() as conn:
                tables = await conn.fetch(
                    """
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY tablename
                """
                )
                return [table["tablename"] for table in tables]
        except Exception as e:
            logger.error(f"❌ Failed to get table list: {e}")
            return []

    async def create_schema(self) -> bool:
        """Create schema and tables in target database."""
        try:
            logger.info("🏗️  Creating schema in target database...")

            async with self.target_pool.acquire() as conn:
                # Create tables
                for table_name, schema_sql in SCHEMA_DEFINITIONS.items():
                    logger.info(f"📋 Creating table: {table_name}")
                    await conn.execute(schema_sql)

                # Create indexes
                for index_sql in INDEX_DEFINITIONS:
                    logger.info(f"🔍 Creating index...")
                    await conn.execute(index_sql)

            logger.info("✅ Schema created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create schema: {e}")
            self.migration_stats["errors"].append(f"Schema creation: {e}")
            return False

    async def migrate_table_data(self, table_name: str) -> bool:
        """Migrate data for a specific table."""
        try:
            logger.info(f"📦 Migrating table: {table_name}")

            # Get data from source
            async with self.source_pool.acquire() as source_conn:
                # Get column names
                columns = await source_conn.fetch(
                    """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = $1 AND table_schema = 'public'
                    ORDER BY ordinal_position
                """,
                    table_name,
                )

                if not columns:
                    logger.warning(f"⚠️  No columns found for table {table_name}")
                    return True

                column_names = [col["column_name"] for col in columns]
                column_list = ", ".join(column_names)

                # Get all data
                rows = await source_conn.fetch(
                    f"SELECT {column_list} FROM {table_name}"
                )

                if not rows:
                    logger.info(f"📭 Table {table_name} is empty")
                    return True

                logger.info(f"📊 Found {len(rows)} rows in {table_name}")

            # Insert data into target
            async with self.target_pool.acquire() as target_conn:
                # Clear existing data
                await target_conn.execute(
                    f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"
                )

                # Prepare insert statement
                placeholders = ", ".join([f"${i+1}" for i in range(len(column_names))])
                insert_sql = (
                    f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                )

                # Insert data in batches
                batch_size = 1000
                for i in range(0, len(rows), batch_size):
                    batch = rows[i : i + batch_size]
                    batch_data = [tuple(row.values()) for row in batch]

                    await target_conn.executemany(insert_sql, batch_data)
                    logger.info(
                        f"📥 Inserted batch {i//batch_size + 1} ({len(batch)} rows)"
                    )

                # Update sequence if table has serial columns
                await self.reset_sequences(target_conn, table_name)

            self.migration_stats["tables_migrated"] += 1
            self.migration_stats["rows_migrated"] += len(rows)
            logger.info(f"✅ Successfully migrated {table_name} ({len(rows)} rows)")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to migrate table {table_name}: {e}")
            self.migration_stats["errors"].append(f"Table {table_name}: {e}")
            return False

    async def reset_sequences(self, conn: asyncpg.Connection, table_name: str):
        """Reset sequences for tables with serial columns."""
        try:
            # Find sequences for this table
            sequences = await conn.fetch(
                """
                SELECT c.column_name, s.sequence_name
                FROM information_schema.columns c
                JOIN information_schema.sequences s ON s.sequence_name = c.table_name || '_' || c.column_name || '_seq'
                WHERE c.table_name = $1 AND c.column_default LIKE 'nextval%'
            """,
                table_name,
            )

            for seq in sequences:
                sequence_name = seq["sequence_name"]
                column_name = seq["column_name"]

                # Get max value from table
                max_val = await conn.fetchval(
                    f"SELECT COALESCE(MAX({column_name}), 0) FROM {table_name}"
                )

                # Reset sequence
                await conn.execute(f"SELECT setval('{sequence_name}', {max_val + 1})")
                logger.info(f"🔄 Reset sequence {sequence_name} to {max_val + 1}")

        except Exception as e:
            logger.warning(f"⚠️  Failed to reset sequences for {table_name}: {e}")

    async def verify_migration(self) -> bool:
        """Verify that migration was successful."""
        try:
            logger.info("🔍 Verifying migration...")

            tables = await self.get_table_list()
            verification_passed = True

            for table_name in tables:
                # Count rows in both databases
                async with self.source_pool.acquire() as source_conn:
                    source_count = await source_conn.fetchval(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )

                async with self.target_pool.acquire() as target_conn:
                    target_count = await target_conn.fetchval(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )

                if source_count == target_count:
                    logger.info(f"✅ {table_name}: {source_count} rows (verified)")
                else:
                    logger.error(
                        f"❌ {table_name}: source={source_count}, target={target_count}"
                    )
                    verification_passed = False

            return verification_passed

        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False

    async def run_migration(self) -> bool:
        """Run the complete migration process."""
        self.migration_stats["start_time"] = datetime.now()

        try:
            logger.info("🚀 Starting database migration from localhost to RDS")

            # Connect to databases
            if not await self.connect_databases():
                return False

            # Get table list
            tables = await self.get_table_list()
            if not tables:
                logger.warning("⚠️  No tables found to migrate")
                return True

            logger.info(f"📋 Found {len(tables)} tables to migrate: {', '.join(tables)}")

            # Create schema in target
            if not await self.create_schema():
                return False

            # Migrate each table
            for table_name in tables:
                if not await self.migrate_table_data(table_name):
                    logger.error(f"❌ Migration failed for table: {table_name}")
                    # Continue with other tables

            # Verify migration
            if await self.verify_migration():
                logger.info("✅ Migration verification passed")
            else:
                logger.warning("⚠️  Migration verification failed")

            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

        finally:
            self.migration_stats["end_time"] = datetime.now()
            await self.cleanup()
            self.print_summary()

    async def cleanup(self):
        """Close database connections."""
        if self.source_pool:
            await self.source_pool.close()
        if self.target_pool:
            await self.target_pool.close()

    def print_summary(self):
        """Print migration summary."""
        duration = self.migration_stats["end_time"] - self.migration_stats["start_time"]

        logger.info("📊 Migration Summary:")
        logger.info(f"   Tables migrated: {self.migration_stats['tables_migrated']}")
        logger.info(f"   Rows migrated: {self.migration_stats['rows_migrated']}")
        logger.info(f"   Duration: {duration}")
        logger.info(f"   Errors: {len(self.migration_stats['errors'])}")

        if self.migration_stats["errors"]:
            logger.error("❌ Errors encountered:")
            for error in self.migration_stats["errors"]:
                logger.error(f"   - {error}")


async def main():
    """Main migration function."""
    migrator = DatabaseMigrator()
    success = await migrator.run_migration()

    if success:
        logger.info("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
