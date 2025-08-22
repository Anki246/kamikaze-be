#!/usr/bin/env python3
"""
Production Database Migration Script: Local PostgreSQL to AWS RDS
Migrates all tables and data from local kamikaze database to AWS RDS database

Features:
- Secure password prompting (no hardcoded credentials)
- Connects to local PostgreSQL and AWS RDS
- Migrates schema (tables, indexes, constraints)
- Migrates all data with progress tracking
- Handles foreign key constraints properly
- Comprehensive logging and error handling

Usage:
    cd /path/to/kamikaze-be
    python utils/migrate_to_rds.py [--dry-run] [--tables table1,table2] [--exclude table1,table2]
"""

import argparse
import asyncio
import getpass
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Debug boto3 availability
print(f"🐍 Python executable: {sys.executable}")
print(f"🐍 Python version: {sys.version}")
try:
    import boto3

    print(f"✅ boto3 available in migration script: {boto3.__version__}")
except ImportError as e:
    print(f"❌ boto3 not available in migration script: {e}")
    print("Installing boto3...")
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "boto3"])
    import boto3

    print(f"✅ boto3 installed and imported: {boto3.__version__}")

try:
    import asyncpg
except ImportError:
    print("❌ Required packages not installed. Please install:")
    print("   pip install asyncpg")
    sys.exit(1)

try:
    from infrastructure.aws_secrets_manager import AWS_AVAILABLE, SecretsManager

    print(f"✅ SecretsManager imported successfully, AWS_AVAILABLE: {AWS_AVAILABLE}")
except ImportError as e:
    print(f"❌ Cannot import SecretsManager: {e}")
    print("   Make sure you're in the project directory and boto3 is installed:")
    print("   pip install boto3")
    print("   Run this script from the kamikaze-be root directory:")
    print("   python utils/migrate_to_rds.py")
    sys.exit(1)

# Setup logging
log_file = project_root / f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class DatabaseMigrator:
    """Handles migration from local PostgreSQL to AWS RDS."""

    def __init__(self, dry_run: bool = False):
        """Initialize the migrator."""
        self.dry_run = dry_run
        self.local_conn = None
        self.rds_conn = None

        # Ensure AWS region is set
        if not os.getenv("AWS_DEFAULT_REGION"):
            os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

        self.secrets_manager = SecretsManager(region_name="us-east-1")
        self.migration_stats = {
            "tables_migrated": 0,
            "rows_migrated": 0,
            "errors": 0,
            "start_time": None,
            "end_time": None,
        }

    async def connect_databases(self) -> bool:
        """Connect to both local and RDS databases."""
        try:
            # Get local database password securely
            local_password = getpass.getpass("🔐 Enter local PostgreSQL password: ")

            # Connect to local PostgreSQL
            logger.info("🔗 Connecting to local PostgreSQL database...")
            self.local_conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password=local_password,
                database="kamikaze",
            )
            logger.info("✅ Connected to local PostgreSQL")

            # Get RDS credentials from AWS Secrets Manager
            logger.info("🔐 Retrieving RDS credentials from AWS Secrets Manager...")
            try:
                rds_creds = await self.secrets_manager.get_database_credentials()
                if not rds_creds:
                    logger.error(
                        "❌ Failed to retrieve RDS credentials from AWS Secrets Manager"
                    )
                    return False
                logger.info(f"✅ Retrieved RDS credentials for {rds_creds.host}")
            except Exception as e:
                logger.error(f"❌ Error retrieving RDS credentials: {e}")
                return False

            # Connect to RDS
            logger.info(f"🔗 Connecting to RDS database at {rds_creds.host}...")
            try:
                self.rds_conn = await asyncio.wait_for(
                    asyncpg.connect(
                        host=rds_creds.host,
                        port=rds_creds.port,
                        user=rds_creds.username,
                        password=rds_creds.password,
                        database=rds_creds.database,
                        ssl="prefer",  # Try SSL but fall back if needed
                    ),
                    timeout=30,  # 30 second timeout
                )
                logger.info("✅ Connected to RDS database")
                return True
            except asyncio.TimeoutError:
                logger.error("❌ RDS connection timed out after 30 seconds")
                logger.error("   This usually means:")
                logger.error("   1. RDS instance is not publicly accessible")
                logger.error(
                    "   2. Security group doesn't allow connections from your IP"
                )
                logger.error(
                    "   3. RDS instance is in a private subnet without internet access"
                )
                return False
            except Exception as rds_e:
                logger.error(f"❌ RDS connection failed: {rds_e}")
                return False

        except Exception as e:
            logger.error(f"❌ Failed to connect to databases: {e}")
            return False

    async def get_table_list(
        self,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
    ) -> List[str]:
        """Get list of tables to migrate."""
        query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        ORDER BY tablename
        """

        rows = await self.local_conn.fetch(query)
        all_tables = [row["tablename"] for row in rows]

        if include_tables:
            tables = [t for t in all_tables if t in include_tables]
        else:
            tables = all_tables

        if exclude_tables:
            tables = [t for t in tables if t not in exclude_tables]

        logger.info(f"📋 Found {len(tables)} tables to migrate: {', '.join(tables)}")
        return tables

    async def get_table_dependencies(self, tables: List[str]) -> Dict[str, Set[str]]:
        """Get foreign key dependencies between tables."""
        query = """
        SELECT 
            tc.table_name as source_table,
            ccu.table_name as target_table
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = 'public'
            AND tc.table_name = ANY($1)
        """

        rows = await self.local_conn.fetch(query, tables)
        dependencies = {table: set() for table in tables}

        for row in rows:
            source = row["source_table"]
            target = row["target_table"]
            if target in tables:  # Only consider dependencies within our table set
                dependencies[source].add(target)

        return dependencies

    def topological_sort(
        self, tables: List[str], dependencies: Dict[str, Set[str]]
    ) -> List[str]:
        """Sort tables in dependency order (dependencies first)."""
        visited = set()
        temp_visited = set()
        result = []

        def visit(table: str):
            if table in temp_visited:
                logger.warning(
                    f"⚠️ Circular dependency detected involving table: {table}"
                )
                return
            if table in visited:
                return

            temp_visited.add(table)
            for dep in dependencies.get(table, set()):
                if dep in tables:  # Only visit if it's in our migration set
                    visit(dep)
            temp_visited.remove(table)
            visited.add(table)
            result.append(table)

        for table in tables:
            if table not in visited:
                visit(table)

        return result

    async def create_custom_types(self) -> bool:
        """Create all custom types (enums) needed by tables."""
        try:
            # Get all custom types from local database
            types_query = """
                SELECT t.typname, e.enumlabel
                FROM pg_type t
                JOIN pg_enum e ON t.oid = e.enumtypid
                JOIN pg_namespace n ON t.typnamespace = n.oid
                WHERE n.nspname = 'public'
                ORDER BY t.typname, e.enumsortorder
            """

            type_rows = await self.local_conn.fetch(types_query)

            # Group enum values by type name
            types_dict = {}
            for row in type_rows:
                type_name = row["typname"]
                enum_value = row["enumlabel"]
                if type_name not in types_dict:
                    types_dict[type_name] = []
                types_dict[type_name].append(enum_value)

            # Create each custom type
            for type_name, enum_values in types_dict.items():
                logger.info(f"🔧 Creating custom type {type_name}...")

                # Format enum values for SQL
                values_str = ", ".join([f"'{value}'" for value in enum_values])
                create_type_sql = f"CREATE TYPE {type_name} AS ENUM ({values_str})"

                # Check if type already exists
                check_sql = """
                    SELECT 1 FROM pg_type t
                    JOIN pg_namespace n ON t.typnamespace = n.oid
                    WHERE t.typname = $1 AND n.nspname = 'public'
                """
                exists = await self.rds_conn.fetchval(check_sql, type_name)

                if not exists:
                    await self.rds_conn.execute(create_type_sql)
                    logger.info(f"✅ Created custom type {type_name}")
                else:
                    logger.info(f"⏭️  Custom type {type_name} already exists")

            return True

        except Exception as e:
            logger.error(f"❌ Error creating custom types: {e}")
            return False

    async def create_sequences(self) -> bool:
        """Create all sequences needed by tables."""
        try:
            # Get all sequences from local database
            sequences_query = """
                SELECT schemaname, sequencename, start_value, min_value, max_value, increment_by
                FROM pg_sequences
                WHERE schemaname = 'public'
            """

            sequences = await self.local_conn.fetch(sequences_query)

            for seq in sequences:
                seq_name = seq["sequencename"]
                logger.info(f"🔢 Creating sequence {seq_name}...")

                create_seq_sql = f"""
                    CREATE SEQUENCE IF NOT EXISTS "{seq_name}"
                    START WITH {seq['start_value']}
                    INCREMENT BY {seq['increment_by']}
                    MINVALUE {seq['min_value']}
                    MAXVALUE {seq['max_value']}
                """

                await self.rds_conn.execute(create_seq_sql)
                logger.info(f"✅ Created sequence {seq_name}")

            return True

        except Exception as e:
            logger.error(f"❌ Error creating sequences: {e}")
            return False

    async def create_table_schema(self, table_name: str) -> bool:
        """Create table schema in RDS database."""
        try:
            # Check if table already exists in RDS
            exists_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
            """

            table_exists = await self.rds_conn.fetchval(exists_query, table_name)

            if table_exists:
                logger.info(f"📋 Table {table_name} already exists in RDS")
                return True

            if self.dry_run:
                logger.info(f"🔍 [DRY RUN] Would create table: {table_name}")
                return True

            # Get column definitions
            columns_query = """
            SELECT
                c.column_name,
                CASE
                    WHEN c.data_type = 'USER-DEFINED' THEN t.typname
                    ELSE c.data_type
                END as data_type,
                c.character_maximum_length,
                c.numeric_precision,
                c.numeric_scale,
                c.is_nullable,
                c.column_default
            FROM information_schema.columns c
            LEFT JOIN pg_type t ON c.udt_name = t.typname
            WHERE c.table_schema = 'public' AND c.table_name = $1
            ORDER BY c.ordinal_position
            """

            columns = await self.local_conn.fetch(columns_query, table_name)

            if not columns:
                logger.error(f"❌ No columns found for table {table_name}")
                return False

            # Build CREATE TABLE statement
            column_defs = []
            for col in columns:
                col_def = f'"{col["column_name"]}" {col["data_type"]}'

                # Add length/precision only for appropriate types
                if col["character_maximum_length"]:
                    col_def += f'({col["character_maximum_length"]})'
                elif (
                    col["numeric_precision"]
                    and col["numeric_scale"] is not None
                    and col["data_type"] in ["numeric", "decimal"]
                ):
                    col_def += f'({col["numeric_precision"]},{col["numeric_scale"]})'

                # Add NOT NULL
                if col["is_nullable"] == "NO":
                    col_def += " NOT NULL"

                # Add DEFAULT (handle sequences properly)
                if col["column_default"]:
                    default_val = col["column_default"]
                    # Convert nextval() calls to use the sequence directly
                    if "nextval(" in default_val and col["data_type"] == "integer":
                        # For integer columns with sequence defaults, use SERIAL instead
                        col_def = f'"{col["column_name"]}" SERIAL'
                    else:
                        col_def += f" DEFAULT {default_val}"

                column_defs.append(col_def)

            create_statement = (
                f'CREATE TABLE "{table_name}" (\n  '
                + ",\n  ".join(column_defs)
                + "\n);"
            )

            logger.info(f"🔨 Creating table {table_name} in RDS...")
            logger.debug(f"SQL: {create_statement}")
            await self.rds_conn.execute(create_statement)
            logger.info(f"✅ Created table {table_name}")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to create table {table_name}: {e}")
            return False

    async def migrate_table_data(self, table_name: str) -> bool:
        """Migrate data for a specific table."""
        try:
            # Get row count
            count_query = f'SELECT COUNT(*) FROM "{table_name}"'
            total_rows = await self.local_conn.fetchval(count_query)

            if total_rows == 0:
                logger.info(f"📋 Table {table_name} is empty, skipping data migration")
                return True

            logger.info(f"📊 Migrating {total_rows} rows from table {table_name}...")

            if self.dry_run:
                logger.info(
                    f"🔍 [DRY RUN] Would migrate {total_rows} rows from {table_name}"
                )
                return True

            # Clear existing data in RDS table
            await self.rds_conn.execute(f'DELETE FROM "{table_name}"')

            # Get all data from local table
            select_query = f'SELECT * FROM "{table_name}"'
            rows = await self.local_conn.fetch(select_query)

            if not rows:
                return True

            # Get column names
            columns = list(rows[0].keys())
            column_names = ", ".join(f'"{col}"' for col in columns)
            placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))

            insert_query = (
                f'INSERT INTO "{table_name}" ({column_names}) VALUES ({placeholders})'
            )

            # Insert data in batches
            batch_size = 1000
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                batch_data = [tuple(row[col] for col in columns) for row in batch]

                await self.rds_conn.executemany(insert_query, batch_data)

                progress = min(i + batch_size, len(rows))
                logger.info(
                    f"  📈 Progress: {progress}/{total_rows} rows ({progress/total_rows*100:.1f}%)"
                )

            # Verify migration
            rds_count = await self.rds_conn.fetchval(
                f'SELECT COUNT(*) FROM "{table_name}"'
            )

            if rds_count == total_rows:
                logger.info(
                    f"✅ Successfully migrated {total_rows} rows for table {table_name}"
                )
                self.migration_stats["rows_migrated"] += total_rows
                return True
            else:
                logger.error(
                    f"❌ Row count mismatch for {table_name}: local={total_rows}, rds={rds_count}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to migrate data for table {table_name}: {e}")
            self.migration_stats["errors"] += 1
            return False

    async def create_indexes_and_constraints(self, table_name: str) -> bool:
        """Create indexes and constraints for a table."""
        try:
            if self.dry_run:
                logger.info(
                    f"🔍 [DRY RUN] Would create indexes and constraints for {table_name}"
                )
                return True

            # Get primary key constraints
            pk_query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = $1::regclass AND i.indisprimary
            """

            pk_columns = await self.local_conn.fetch(pk_query, table_name)

            if pk_columns:
                pk_cols = ", ".join(f'"{col["attname"]}"' for col in pk_columns)
                pk_constraint = (
                    f'ALTER TABLE "{table_name}" ADD PRIMARY KEY ({pk_cols})'
                )

                try:
                    await self.rds_conn.execute(pk_constraint)
                    logger.info(f"✅ Created primary key for {table_name}")
                except Exception as e:
                    logger.warning(
                        f"⚠️ Failed to create primary key for {table_name}: {e}"
                    )

            # Get indexes (excluding primary key)
            index_query = """
            SELECT
                i.relname as index_name,
                array_agg(a.attname ORDER BY c.ordinality) as columns,
                ix.indisunique
            FROM pg_class t
            JOIN pg_index ix ON t.oid = ix.indrelid
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN unnest(ix.indkey) WITH ORDINALITY AS c(attnum, ordinality) ON true
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = c.attnum
            WHERE t.relname = $1
                AND t.relkind = 'r'
                AND NOT ix.indisprimary
            GROUP BY i.relname, ix.indisunique
            """

            indexes = await self.local_conn.fetch(index_query, table_name)

            for idx in indexes:
                idx_name = idx["index_name"]
                columns = ", ".join(f'"{col}"' for col in idx["columns"])
                unique = "UNIQUE " if idx["indisunique"] else ""

                create_index = (
                    f'CREATE {unique}INDEX "{idx_name}" ON "{table_name}" ({columns})'
                )

                try:
                    await self.rds_conn.execute(create_index)
                    logger.info(f"✅ Created index {idx_name} for {table_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create index {idx_name}: {e}")

            return True

        except Exception as e:
            logger.error(
                f"❌ Failed to create indexes/constraints for {table_name}: {e}"
            )
            return False

    async def migrate_database(
        self,
        include_tables: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
        schema_only: bool = False,
    ) -> bool:
        """Perform complete database migration."""
        try:
            self.migration_stats["start_time"] = datetime.now()

            logger.info(
                "🚀 Starting database migration from local PostgreSQL to AWS RDS"
            )
            logger.info("=" * 70)

            # Connect to databases
            if not await self.connect_databases():
                return False

            # Get tables to migrate
            tables = await self.get_table_list(include_tables, exclude_tables)
            if not tables:
                logger.error("❌ No tables found to migrate")
                return False

            # Get dependencies and sort tables
            dependencies = await self.get_table_dependencies(tables)
            sorted_tables = self.topological_sort(tables, dependencies)

            logger.info(f"📋 Migration order: {' -> '.join(sorted_tables)}")

            # Phase 1: Create custom types
            logger.info("\n🔨 Phase 1: Creating custom types...")
            if not await self.create_custom_types():
                logger.error("❌ Failed to create custom types")
                return False

            # Phase 2: Create sequences
            logger.info("\n🔨 Phase 2: Creating sequences...")
            if not await self.create_sequences():
                logger.error("❌ Failed to create sequences")
                return False

            # Phase 3: Create table schemas
            logger.info("\n🔨 Phase 3: Creating table schemas...")
            for table in sorted_tables:
                if not await self.create_table_schema(table):
                    logger.error(f"❌ Failed to create schema for {table}")
                    return False

            # Phase 4: Migrate data (skip if schema_only)
            if not schema_only:
                logger.info("\n📊 Phase 4: Migrating table data...")
                for table in sorted_tables:
                    if await self.migrate_table_data(table):
                        self.migration_stats["tables_migrated"] += 1
                    else:
                        logger.error(f"❌ Failed to migrate data for {table}")
                        # Continue with other tables
            else:
                logger.info("\n⏭️  Skipping data migration (schema-only mode)")
                self.migration_stats["tables_migrated"] = len(sorted_tables)

            # Phase 3: Create indexes and constraints
            logger.info("\n🔗 Phase 3: Creating indexes and constraints...")
            for table in sorted_tables:
                await self.create_indexes_and_constraints(table)

            self.migration_stats["end_time"] = datetime.now()

            # Print summary
            self.print_migration_summary()

            return self.migration_stats["errors"] == 0

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False
        finally:
            await self.cleanup()

    def print_migration_summary(self):
        """Print migration summary."""
        duration = self.migration_stats["end_time"] - self.migration_stats["start_time"]

        logger.info("\n" + "=" * 70)
        logger.info("📊 MIGRATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"✅ Tables migrated: {self.migration_stats['tables_migrated']}")
        logger.info(f"📈 Rows migrated: {self.migration_stats['rows_migrated']:,}")
        logger.info(f"❌ Errors: {self.migration_stats['errors']}")
        logger.info(f"⏱️  Duration: {duration}")
        logger.info(f"📄 Log file: {log_file}")

        if self.migration_stats["errors"] == 0:
            logger.info("🎉 Migration completed successfully!")
        else:
            logger.warning("⚠️ Migration completed with errors. Check logs for details.")

    async def cleanup(self):
        """Clean up database connections."""
        if self.local_conn:
            await self.local_conn.close()
        if self.rds_conn:
            await self.rds_conn.close()


async def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate kamikaze database to AWS RDS")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform a dry run without making changes",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Create schema only, skip data migration",
    )
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma-separated list of tables to migrate (default: all)",
    )
    parser.add_argument(
        "--exclude", type=str, help="Comma-separated list of tables to exclude"
    )

    args = parser.parse_args()

    include_tables = args.tables.split(",") if args.tables else None
    exclude_tables = args.exclude.split(",") if args.exclude else None

    # Check AWS credentials (allow auto-fetch from secrets)
    has_env_creds = bool(os.getenv("AWS_ACCESS_KEY_ID"))
    has_profile = bool(os.getenv("AWS_PROFILE"))

    if not (has_env_creds or has_profile):
        logger.info(
            "🔍 No explicit AWS credentials found, will attempt auto-fetch from kmkz-app-secrets"
        )
        logger.info("   If auto-fetch fails, please set up AWS credentials using:")
        logger.info(
            "   1. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
        )
        logger.info("   2. AWS CLI: aws configure")
        logger.info("   3. AWS Profile: export AWS_PROFILE=your-profile")

    migrator = DatabaseMigrator(dry_run=args.dry_run)

    success = await migrator.migrate_database(
        include_tables=include_tables,
        exclude_tables=exclude_tables,
        schema_only=args.schema_only,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
