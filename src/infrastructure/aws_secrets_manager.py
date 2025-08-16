#!/usr/bin/env python3
"""
AWS Secrets Manager Integration for FluxTrader
Secure credential management for database connections, API keys, and sensitive configuration.

This module provides:
- Secure retrieval of database credentials from AWS Secrets Manager
- API key management for trading platforms
- Environment-specific configuration management
- Automatic credential rotation support
- Fallback to environment variables for local development

Usage:
    from infrastructure.aws_secrets_manager import SecretsManager
    
    secrets = SecretsManager()
    db_creds = await secrets.get_database_credentials()
    api_keys = await secrets.get_trading_api_keys()
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    boto3 = None
    ClientError = Exception
    NoCredentialsError = Exception

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class DatabaseCredentials:
    """Database connection credentials."""
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"
    min_size: int = 5
    max_size: int = 20
    timeout: int = 60

@dataclass
class TradingAPIKeys:
    """Trading platform API keys."""
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    binance_testnet: bool = True
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

@dataclass
class ApplicationSecrets:
    """Application-level secrets."""
    jwt_secret: str
    encryption_key: str
    credentials_encryption_key: str
    webhook_secret: Optional[str] = None

class SecretsManager:
    """AWS Secrets Manager integration for secure credential management."""
    
    def __init__(self, region_name: str = None, environment: str = None):
        """
        Initialize Secrets Manager.
        
        Args:
            region_name: AWS region (defaults to AWS_DEFAULT_REGION env var)
            environment: Environment name (dev, staging, prod)
        """
        self.region_name = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        self.environment = environment or os.getenv("ENVIRONMENT", "dev")
        self.client = None
        self._cache = {}
        self._cache_ttl = {}
        self.cache_duration = timedelta(minutes=15)  # Cache secrets for 15 minutes
        
        # Initialize AWS client if available
        if AWS_AVAILABLE:
            try:
                self.client = boto3.client(
                    'secretsmanager',
                    region_name=self.region_name
                )
                logger.info(f"✅ AWS Secrets Manager client initialized for region: {self.region_name}")
            except (NoCredentialsError, Exception) as e:
                logger.warning(f"⚠️ AWS Secrets Manager not available: {e}")
                logger.info("📝 Falling back to environment variables")
                self.client = None
        else:
            logger.warning("⚠️ boto3 not installed, using environment variables only")
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached secret is still valid."""
        if key not in self._cache_ttl:
            return False
        return datetime.now() < self._cache_ttl[key]
    
    def _cache_secret(self, key: str, value: Any) -> None:
        """Cache secret with TTL."""
        self._cache[key] = value
        self._cache_ttl[key] = datetime.now() + self.cache_duration
    
    async def _get_secret_value(self, secret_name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve secret from AWS Secrets Manager with caching.
        
        Args:
            secret_name: Name of the secret in AWS Secrets Manager
            
        Returns:
            Secret value as dictionary or None if not found
        """
        # Check cache first
        cache_key = f"{self.environment}_{secret_name}"
        if self._is_cache_valid(cache_key):
            logger.debug(f"📋 Using cached secret: {secret_name}")
            return self._cache[cache_key]
        
        if not self.client:
            logger.debug(f"📝 AWS client not available, skipping secret: {secret_name}")
            return None
        
        try:
            # Construct environment-specific secret name
            full_secret_name = f"fluxtrader/{self.environment}/{secret_name}"
            
            logger.debug(f"🔍 Retrieving secret: {full_secret_name}")
            response = self.client.get_secret_value(SecretId=full_secret_name)
            
            secret_value = json.loads(response['SecretString'])
            
            # Cache the secret
            self._cache_secret(cache_key, secret_value)
            
            logger.info(f"✅ Retrieved secret: {secret_name}")
            return secret_value
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"⚠️ Secret not found: {full_secret_name}")
            elif error_code == 'InvalidRequestException':
                logger.error(f"❌ Invalid request for secret: {full_secret_name}")
            elif error_code == 'InvalidParameterException':
                logger.error(f"❌ Invalid parameter for secret: {full_secret_name}")
            else:
                logger.error(f"❌ Error retrieving secret {full_secret_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving secret {secret_name}: {e}")
            return None
    
    async def get_database_credentials(self, database_name: str = "main") -> DatabaseCredentials:
        """
        Get database credentials from AWS Secrets Manager or environment variables.
        
        Args:
            database_name: Name of the database configuration
            
        Returns:
            DatabaseCredentials object
        """
        # Try AWS Secrets Manager first
        secret_name = f"database/{database_name}"
        secret_value = await self._get_secret_value(secret_name)
        
        if secret_value:
            return DatabaseCredentials(
                host=secret_value.get("host", "localhost"),
                port=int(secret_value.get("port", 5432)),
                database=secret_value.get("database", "kamikaze"),
                username=secret_value.get("username", "postgres"),
                password=secret_value.get("password", ""),
                ssl_mode=secret_value.get("ssl_mode", "prefer"),
                min_size=int(secret_value.get("min_size", 5)),
                max_size=int(secret_value.get("max_size", 20)),
                timeout=int(secret_value.get("timeout", 60))
            )
        
        # Fallback to environment variables
        logger.info("📝 Using database credentials from environment variables")
        return DatabaseCredentials(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "kamikaze"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            ssl_mode=os.getenv("DB_SSL_MODE", "prefer"),
            min_size=int(os.getenv("DB_MIN_SIZE", "5")),
            max_size=int(os.getenv("DB_MAX_SIZE", "20")),
            timeout=int(os.getenv("DB_TIMEOUT", "60"))
        )
    
    async def get_trading_api_keys(self) -> TradingAPIKeys:
        """
        Get trading API keys from AWS Secrets Manager or environment variables.
        
        Returns:
            TradingAPIKeys object
        """
        # Try AWS Secrets Manager first
        secret_value = await self._get_secret_value("trading/api-keys")
        
        if secret_value:
            return TradingAPIKeys(
                binance_api_key=secret_value.get("binance_api_key"),
                binance_secret_key=secret_value.get("binance_secret_key"),
                binance_testnet=secret_value.get("binance_testnet", True),
                groq_api_key=secret_value.get("groq_api_key"),
                openai_api_key=secret_value.get("openai_api_key")
            )
        
        # Fallback to environment variables
        logger.info("📝 Using trading API keys from environment variables")
        return TradingAPIKeys(
            binance_api_key=os.getenv("BINANCE_API_KEY"),
            binance_secret_key=os.getenv("BINANCE_SECRET_KEY"),
            binance_testnet=os.getenv("BINANCE_TESTNET", "true").lower() == "true",
            groq_api_key=os.getenv("GROQ_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def get_application_secrets(self) -> ApplicationSecrets:
        """
        Get application secrets from AWS Secrets Manager or environment variables.
        
        Returns:
            ApplicationSecrets object
        """
        # Try AWS Secrets Manager first
        secret_value = await self._get_secret_value("application/secrets")
        
        if secret_value:
            return ApplicationSecrets(
                jwt_secret=secret_value.get("jwt_secret", "default-jwt-secret-change-me"),
                encryption_key=secret_value.get("encryption_key", "default-encryption-key"),
                credentials_encryption_key=secret_value.get("credentials_encryption_key", ""),
                webhook_secret=secret_value.get("webhook_secret")
            )
        
        # Fallback to environment variables
        logger.info("📝 Using application secrets from environment variables")
        return ApplicationSecrets(
            jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
            encryption_key=os.getenv("ENCRYPTION_KEY", "default-encryption-key"),
            credentials_encryption_key=os.getenv("CREDENTIALS_ENCRYPTION_KEY", ""),
            webhook_secret=os.getenv("WEBHOOK_SECRET")
        )
    
    async def update_secret(self, secret_name: str, secret_value: Dict[str, Any]) -> bool:
        """
        Update a secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret
            secret_value: New secret value as dictionary
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("⚠️ AWS client not available, cannot update secret")
            return False
        
        try:
            full_secret_name = f"fluxtrader/{self.environment}/{secret_name}"
            
            self.client.update_secret(
                SecretId=full_secret_name,
                SecretString=json.dumps(secret_value)
            )
            
            # Invalidate cache
            cache_key = f"{self.environment}_{secret_name}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                del self._cache_ttl[cache_key]
            
            logger.info(f"✅ Updated secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update secret {secret_name}: {e}")
            return False
    
    async def create_secret(self, secret_name: str, secret_value: Dict[str, Any], description: str = "") -> bool:
        """
        Create a new secret in AWS Secrets Manager.
        
        Args:
            secret_name: Name of the secret
            secret_value: Secret value as dictionary
            description: Description of the secret
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            logger.warning("⚠️ AWS client not available, cannot create secret")
            return False
        
        try:
            full_secret_name = f"fluxtrader/{self.environment}/{secret_name}"
            
            self.client.create_secret(
                Name=full_secret_name,
                SecretString=json.dumps(secret_value),
                Description=description or f"FluxTrader {self.environment} - {secret_name}"
            )
            
            logger.info(f"✅ Created secret: {secret_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create secret {secret_name}: {e}")
            return False
    
    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()
        self._cache_ttl.clear()
        logger.info("🧹 Secrets cache cleared")

# Global instance
secrets_manager = SecretsManager()

# Convenience functions
async def get_database_credentials(database_name: str = "main") -> DatabaseCredentials:
    """Get database credentials."""
    return await secrets_manager.get_database_credentials(database_name)

async def get_trading_api_keys() -> TradingAPIKeys:
    """Get trading API keys."""
    return await secrets_manager.get_trading_api_keys()

async def get_application_secrets() -> ApplicationSecrets:
    """Get application secrets."""
    return await secrets_manager.get_application_secrets()

# Example usage and testing
async def main():
    """Example usage of the SecretsManager."""
    print("🔐 Testing AWS Secrets Manager integration...")
    
    # Test database credentials
    db_creds = await get_database_credentials()
    print(f"📊 Database: {db_creds.host}:{db_creds.port}/{db_creds.database}")
    
    # Test trading API keys
    api_keys = await get_trading_api_keys()
    print(f"🔑 Binance API Key: {'***' if api_keys.binance_api_key else 'Not set'}")
    print(f"🔑 Groq API Key: {'***' if api_keys.groq_api_key else 'Not set'}")
    
    # Test application secrets
    app_secrets = await get_application_secrets()
    print(f"🔐 JWT Secret: {'***' if app_secrets.jwt_secret else 'Not set'}")

if __name__ == "__main__":
    asyncio.run(main())
