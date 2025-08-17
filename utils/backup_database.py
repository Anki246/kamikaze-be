#!/usr/bin/env python3
"""
Database Backup Utility
Creates secure backups of the local kamikaze PostgreSQL database

Usage:
    cd /path/to/kamikaze-be
    python utils/backup_database.py [--output-dir /path/to/backups] [--schema-only] [--data-only]
"""

import argparse
import getpass
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles secure local PostgreSQL database backup."""
    
    def __init__(self, output_dir: str = None):
        """Initialize backup handler."""
        project_root = Path(__file__).parent.parent
        self.output_dir = Path(output_dir) if output_dir else project_root / "backups"
        self.output_dir.mkdir(exist_ok=True)
        
        self.pg_dump_path = "/Library/PostgreSQL/16/bin/pg_dump"
        self.backup_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.db_password = None
        
    def get_password(self):
        """Get database password securely."""
        if not self.db_password:
            self.db_password = getpass.getpass("🔐 Enter PostgreSQL password: ")
        return self.db_password
        
    def create_backup(self) -> bool:
        """Create a complete backup of the kamikaze database."""
        try:
            logger.info("🗄️ Starting database backup...")
            
            # Check if pg_dump exists
            if not Path(self.pg_dump_path).exists():
                logger.error(f"❌ pg_dump not found at {self.pg_dump_path}")
                return False
            
            # Get database password securely
            password = self.get_password()
            
            # Create backup filename
            backup_file = self.output_dir / f"kamikaze_backup_{self.backup_timestamp}.sql"
            
            # Prepare pg_dump command
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            cmd = [
                self.pg_dump_path,
                '--host=localhost',
                '--port=5432',
                '--username=postgres',
                '--dbname=kamikaze',
                '--verbose',
                '--clean',
                '--create',
                '--if-exists',
                '--format=plain',
                '--file', str(backup_file)
            ]
            
            logger.info(f"📦 Creating backup: {backup_file}")
            
            # Run pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                file_size = backup_file.stat().st_size
                logger.info(f"✅ Backup created successfully!")
                logger.info(f"   📁 File: {backup_file}")
                logger.info(f"   📊 Size: {file_size / 1024 / 1024:.2f} MB")
                
                # Create a compressed version
                self.compress_backup(backup_file)
                
                return True
            else:
                logger.error(f"❌ Backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Backup error: {e}")
            return False
    
    def compress_backup(self, backup_file: Path) -> bool:
        """Compress the backup file."""
        try:
            import gzip
            
            compressed_file = backup_file.with_suffix('.sql.gz')
            
            logger.info(f"🗜️ Compressing backup to {compressed_file}")
            
            with open(backup_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Get sizes
            original_size = backup_file.stat().st_size
            compressed_size = compressed_file.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f"✅ Compression completed!")
            logger.info(f"   📊 Original: {original_size / 1024 / 1024:.2f} MB")
            logger.info(f"   📊 Compressed: {compressed_size / 1024 / 1024:.2f} MB")
            logger.info(f"   📊 Saved: {compression_ratio:.1f}%")
            
            # Remove original uncompressed file
            backup_file.unlink()
            logger.info("🗑️ Removed uncompressed backup file")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Compression failed: {e}")
            return False
    
    def create_schema_only_backup(self) -> bool:
        """Create a schema-only backup (no data)."""
        try:
            logger.info("📋 Creating schema-only backup...")
            
            password = self.get_password()
            backup_file = self.output_dir / f"kamikaze_schema_{self.backup_timestamp}.sql"
            
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            cmd = [
                self.pg_dump_path,
                '--host=localhost',
                '--port=5432',
                '--username=postgres',
                '--dbname=kamikaze',
                '--schema-only',
                '--verbose',
                '--clean',
                '--create',
                '--if-exists',
                '--format=plain',
                '--file', str(backup_file)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Schema backup created: {backup_file}")
                return True
            else:
                logger.error(f"❌ Schema backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Schema backup error: {e}")
            return False
    
    def create_data_only_backup(self) -> bool:
        """Create a data-only backup (no schema)."""
        try:
            logger.info("📊 Creating data-only backup...")
            
            password = self.get_password()
            backup_file = self.output_dir / f"kamikaze_data_{self.backup_timestamp}.sql"
            
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            cmd = [
                self.pg_dump_path,
                '--host=localhost',
                '--port=5432',
                '--username=postgres',
                '--dbname=kamikaze',
                '--data-only',
                '--verbose',
                '--format=plain',
                '--file', str(backup_file)
            ]
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Data backup created: {backup_file}")
                self.compress_backup(backup_file)
                return True
            else:
                logger.error(f"❌ Data backup failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Data backup error: {e}")
            return False


def main():
    """Main backup function."""
    parser = argparse.ArgumentParser(description='Backup kamikaze PostgreSQL database')
    parser.add_argument('--output-dir', type=str, default='./backups',
                       help='Output directory for backups (default: ./backups)')
    parser.add_argument('--schema-only', action='store_true',
                       help='Create schema-only backup')
    parser.add_argument('--data-only', action='store_true',
                       help='Create data-only backup')
    
    args = parser.parse_args()
    
    backup = DatabaseBackup(args.output_dir)
    
    success = True
    
    if args.schema_only:
        success = backup.create_schema_only_backup()
    elif args.data_only:
        success = backup.create_data_only_backup()
    else:
        # Create full backup by default
        success = backup.create_backup()
    
    if success:
        logger.info("🎉 Backup operation completed successfully!")
    else:
        logger.error("❌ Backup operation failed!")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
