"""
Credentials Database Manager for Exchange Integration
Provides secure storage and retrieval of exchange API credentials
"""

import asyncio
import asyncpg
import logging
import base64
import json
from typing import Optional, Dict, List, Any
from contextlib import asynccontextmanager
from cryptography.fernet import Fernet
from .database_config import db_config
import os

logger = logging.getLogger(__name__)

class CredentialsDatabase:
    """
    Direct PostgreSQL connection manager for exchange credentials.
    Provides secure, encrypted storage of API keys and secrets.
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connected = False
        self._connection_lock = asyncio.Lock()
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential storage."""
        key_env = os.getenv("CREDENTIALS_ENCRYPTION_KEY")
        if key_env:
            try:
                # Fernet expects the key as bytes (the base64-encoded string as bytes)
                return key_env.encode()
            except Exception:
                logger.warning("Invalid encryption key in environment, generating new one")

        # Generate new key
        key = Fernet.generate_key()
        logger.warning(f"Generated new encryption key. Set CREDENTIALS_ENCRYPTION_KEY={key.decode()} in environment")
        return key
    
    def _encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        return self._cipher.encrypt(data.encode()).decode()
    
    def _decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        return self._cipher.decrypt(encrypted_data.encode()).decode()
    
    async def connect(self) -> bool:
        """Establish connection pool to PostgreSQL database."""
        async with self._connection_lock:
            if self.connected and self.pool:
                return True
            
            try:
                if self.pool:
                    await self.pool.close()
                
                self.pool = await asyncpg.create_pool(
                    host=db_config.host,
                    port=db_config.port,
                    database=db_config.database,
                    user=db_config.user,
                    password=db_config.password,
                    min_size=2,
                    max_size=10,
                    command_timeout=10,
                    server_settings={
                        'application_name': 'kamikaze_credentials',
                        'search_path': 'public'
                    }
                )
                
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                
                self.connected = True
                logger.info(f"✅ Credentials database connected: {db_config.database}")
                return True
                
            except Exception as e:
                logger.error(f"❌ Failed to connect credentials database: {e}")
                self.connected = False
                self.pool = None
                return False
    
    async def disconnect(self):
        """Close connection pool."""
        async with self._connection_lock:
            if self.pool:
                await self.pool.close()
                self.pool = None
            self.connected = False
            logger.info("🔌 Credentials database disconnected")
    
    async def ensure_connected(self) -> bool:
        """Ensure database connection is available."""
        if not self.connected or not self.pool:
            return await self.connect()
        
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Credentials DB connection test failed, reconnecting: {e}")
            self.connected = False
            return await self.connect()
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a database connection from the pool."""
        if not await self.ensure_connected():
            raise ConnectionError("Failed to establish database connection")
        
        async with self.pool.acquire() as conn:
            yield conn
    
    # ============================================================================
    # Testnet Credentials Operations
    # ============================================================================
    
    async def save_testnet_credentials(self, user_id: int, exchange: str, api_key: str, secret_key: str) -> bool:
        """Save or update testnet credentials for a user."""
        try:
            async with self.get_connection() as conn:
                # Encrypt sensitive data for storage
                encrypted_api_key = self._encrypt_data(api_key)
                encrypted_secret_key = self._encrypt_data(secret_key)

                # Create masked versions for display (for backward compatibility)
                api_key_masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                secret_key_masked = secret_key[:8] + "..." + secret_key[-4:] if len(secret_key) > 12 else "***"

                # SECURITY: Only use encrypted columns, never store plain text
                query = """
                    INSERT INTO testnet_credentials (
                        user_id, exchange,
                        api_key_encrypted, api_secret_encrypted, api_key_masked, api_secret_masked,
                        is_active, created_at, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, true, NOW(), NOW())
                    ON CONFLICT (user_id, exchange)
                    DO UPDATE SET
                        api_key_encrypted = EXCLUDED.api_key_encrypted,
                        api_secret_encrypted = EXCLUDED.api_secret_encrypted,
                        api_key_masked = EXCLUDED.api_key_masked,
                        api_secret_masked = EXCLUDED.api_secret_masked,
                        is_active = true,
                        updated_at = NOW()
                """

                await conn.execute(query, user_id, exchange,
                                 encrypted_api_key, encrypted_secret_key, api_key_masked, secret_key_masked)
                logger.info(f"✅ Saved testnet credentials for user {user_id}, exchange {exchange}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to save testnet credentials for user {user_id}, exchange {exchange}: {e}")
            return False
    
    async def get_testnet_credentials(self, user_id: int, exchange: str) -> Optional[Dict[str, Any]]:
        """Get testnet credentials for a user and exchange."""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, user_id, exchange, api_key_encrypted, api_secret_encrypted,
                           api_key_masked, api_secret_masked, is_active, created_at, updated_at
                    FROM testnet_credentials
                    WHERE user_id = $1 AND exchange = $2 AND is_active = true
                """
                result = await conn.fetchrow(query, user_id, exchange)

                if result:
                    # Decrypt sensitive data and return
                    decrypted_result = {
                        'id': result['id'],
                        'user_id': result['user_id'],
                        'exchange': result['exchange'],
                        'api_key': self._decrypt_data(result['api_key_encrypted']),
                        'secret_key': self._decrypt_data(result['api_secret_encrypted']),
                        'api_key_masked': result['api_key_masked'],
                        'api_secret_masked': result['api_secret_masked'],
                        'is_active': result['is_active'],
                        'created_at': result['created_at'],
                        'updated_at': result['updated_at']
                    }
                    return decrypted_result

                return None

        except Exception as e:
            logger.error(f"❌ Failed to get testnet credentials for user {user_id}, exchange {exchange}: {e}")
            return None
    
    async def get_user_testnet_credentials(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all testnet credentials for a user."""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT id, user_id, exchange, is_active, created_at, updated_at
                    FROM testnet_credentials
                    WHERE user_id = $1 AND is_active = true
                """
                results = await conn.fetch(query, user_id)

                # Map to expected format
                mapped_results = []
                for row in results:
                    mapped_results.append({
                        'id': row['id'],
                        'user_id': row['user_id'],
                        'exchange': row['exchange'],
                        'is_active': row['is_active'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })

                return mapped_results

        except Exception as e:
            logger.error(f"❌ Failed to get user testnet credentials for user {user_id}: {e}")
            return []
    
    # ============================================================================
    # Binance Live Credentials Operations
    # ============================================================================
    
    async def save_binance_credentials(self, user_id: int, api_key: str, secret_key: str, is_mainnet: bool = True) -> bool:
        """Save or update Binance live credentials for a user."""
        try:
            async with self.get_connection() as conn:
                # Encrypt sensitive data
                encrypted_api_key = self._encrypt_data(api_key)
                encrypted_secret_key = self._encrypt_data(secret_key)

                # For mainnet, use the main binance_credentials table
                # For testnet, use testnet_credentials table
                if is_mainnet:
                    # Create masked versions for display
                    api_key_masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
                    secret_key_masked = secret_key[:8] + "..." + secret_key[-4:] if len(secret_key) > 12 else "***"

                    # SECURITY FIX: Only store encrypted credentials, never plain text
                    query = """
                        INSERT INTO binance_credentials (
                            user_id,
                            api_key_encrypted, api_secret_encrypted,
                            api_key_masked, api_secret_masked,
                            exchange, environment, is_mainnet,
                            is_active, can_trade, can_withdraw, can_deposit, account_type,
                            created_at, updated_at, last_used, last_validated
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true, false, false, false, 'SPOT', NOW(), NOW(), NOW(), NOW())
                        ON CONFLICT (user_id, is_mainnet)
                        DO UPDATE SET
                            api_key_encrypted = EXCLUDED.api_key_encrypted,
                            api_secret_encrypted = EXCLUDED.api_secret_encrypted,
                            api_key_masked = EXCLUDED.api_key_masked,
                            api_secret_masked = EXCLUDED.api_secret_masked,
                            is_active = true,
                            updated_at = NOW(),
                            last_used = NOW()
                    """
                    await conn.execute(query, user_id,
                                     encrypted_api_key, encrypted_secret_key,
                                     api_key_masked, secret_key_masked,
                                     'binance', 'live', is_mainnet)
                else:
                    # For testnet Binance, use testnet_credentials table
                    return await self.save_testnet_credentials(user_id, "binance", api_key, secret_key)

                env_type = "mainnet" if is_mainnet else "testnet"
                logger.info(f"✅ Saved Binance {env_type} credentials for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"❌ Failed to save Binance credentials for user {user_id}: {e}")
            return False
    
    async def get_binance_credentials(self, user_id: int, is_mainnet: bool = True) -> Optional[Dict[str, Any]]:
        """Get Binance credentials for a user."""
        try:
            async with self.get_connection() as conn:
                if is_mainnet:
                    query = """
                        SELECT id, user_id, api_key_encrypted, api_secret_encrypted,
                               exchange, environment, is_mainnet, is_active,
                               can_trade, can_withdraw, can_deposit, account_type,
                               created_at, updated_at, last_used, last_validated
                        FROM binance_credentials
                        WHERE user_id = $1 AND is_mainnet = $2 AND is_active = true
                    """
                    result = await conn.fetchrow(query, user_id, is_mainnet)

                    if result:
                        # SECURITY FIX: Decrypt from encrypted columns only
                        decrypted_result = {
                            'id': result['id'],
                            'user_id': result['user_id'],
                            'api_key': self._decrypt_data(result['api_key_encrypted']),
                            'secret_key': self._decrypt_data(result['api_secret_encrypted']),
                            'exchange': result['exchange'],
                            'environment': result['environment'],
                            'is_mainnet': result['is_mainnet'],
                            'is_active': result['is_active'],
                            'can_trade': result['can_trade'],
                            'can_withdraw': result['can_withdraw'],
                            'can_deposit': result['can_deposit'],
                            'account_type': result['account_type'],
                            'created_at': result['created_at'],
                            'updated_at': result['updated_at'],
                            'last_used': result['last_used'],
                            'last_validated': result['last_validated']
                        }
                        return decrypted_result
                else:
                    # For testnet, get from testnet_credentials table
                    return await self.get_testnet_credentials(user_id, "binance")

                return None

        except Exception as e:
            logger.error(f"❌ Failed to get Binance credentials for user {user_id}: {e}")
            return None
    
    async def get_user_binance_credentials(self, user_id: int) -> Dict[str, Any]:
        """Get both testnet and mainnet Binance credentials for a user."""
        try:
            async with self.get_connection() as conn:
                credentials = {
                    'mainnet': None,
                    'testnet': None
                }

                # Check mainnet credentials
                mainnet_query = """
                    SELECT id, user_id, exchange, environment, is_mainnet, is_active,
                           can_trade, can_withdraw, can_deposit, account_type,
                           created_at, updated_at, last_used, last_validated
                    FROM binance_credentials
                    WHERE user_id = $1 AND is_mainnet = true AND is_active = true
                """
                mainnet_result = await conn.fetchrow(mainnet_query, user_id)
                if mainnet_result:
                    credentials['mainnet'] = dict(mainnet_result)

                # Check testnet credentials
                testnet_query = """
                    SELECT id, user_id, exchange, is_active, created_at, updated_at
                    FROM testnet_credentials
                    WHERE user_id = $1 AND exchange = 'binance' AND is_active = true
                """
                testnet_result = await conn.fetchrow(testnet_query, user_id)
                if testnet_result:
                    credentials['testnet'] = dict(testnet_result)

                return credentials

        except Exception as e:
            logger.error(f"❌ Failed to get user Binance credentials for user {user_id}: {e}")
            return {'mainnet': None, 'testnet': None}
    
    # ============================================================================
    # Credential Management Operations
    # ============================================================================
    
    async def deactivate_credentials(self, user_id: int, credential_type: str, exchange: str = None) -> bool:
        """Deactivate credentials for a user."""
        try:
            async with self.get_connection() as conn:
                if credential_type == "testnet":
                    query = """
                        UPDATE testnet_credentials 
                        SET is_active = false, updated_at = NOW()
                        WHERE user_id = $1 AND exchange = $2
                    """
                    await conn.execute(query, user_id, exchange)
                elif credential_type == "binance":
                    query = """
                        UPDATE binance_credentials 
                        SET is_active = false, updated_at = NOW()
                        WHERE user_id = $1
                    """
                    await conn.execute(query, user_id)
                
                logger.info(f"✅ Deactivated {credential_type} credentials for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to deactivate credentials: {e}")
            return False
    
    async def delete_credentials(self, user_id: int, credential_type: str, exchange: str = None, is_mainnet: bool = None) -> bool:
        """Permanently delete credentials for a user."""
        try:
            async with self.get_connection() as conn:
                if credential_type == "testnet":
                    query = "DELETE FROM testnet_credentials WHERE user_id = $1 AND exchange = $2"
                    await conn.execute(query, user_id, exchange)
                elif credential_type == "binance":
                    if is_mainnet is not None:
                        query = "DELETE FROM binance_credentials WHERE user_id = $1 AND is_mainnet = $2"
                        await conn.execute(query, user_id, is_mainnet)
                    else:
                        query = "DELETE FROM binance_credentials WHERE user_id = $1"
                        await conn.execute(query, user_id)
                
                logger.info(f"✅ Deleted {credential_type} credentials for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete credentials: {e}")
            return False

# Global credentials database instance
credentials_db = CredentialsDatabase()
