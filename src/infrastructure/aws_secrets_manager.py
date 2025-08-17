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
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

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


@dataclass
class AWSCredentials:
    """AWS credentials from secrets manager."""

    access_key_id: str
    secret_access_key: str
    region: str = "us-east-1"
    session_token: Optional[str] = None
    groq_api_key: Optional[str] = None
    credentials_encryption_key: Optional[str] = None


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
        self._use_mock = False
        self._mock_manager = None
        self._auto_credentials = None

        # Initialize AWS client if available
        if AWS_AVAILABLE:
            self.client = self._initialize_aws_client()
        else:
            logger.warning("⚠️ boto3 not installed, using environment variables only")
            self.client = None

    def _initialize_aws_client(self):
        """Initialize AWS client with multiple credential sources."""
        try:
            # Method 1: Try with existing credentials (env vars, profiles, IAM roles)
            client = boto3.client("secretsmanager", region_name=self.region_name)
            # Test the client with a simple operation
            client.list_secrets(MaxResults=1)
            logger.info(f"✅ AWS Secrets Manager client initialized for region: {self.region_name}")
            return client

        except (NoCredentialsError, Exception) as e:
            logger.debug(f"Standard AWS credentials not found: {e}")

            # Method 2: Try auto-fetch from kmkz-app-secrets
            try:
                if self._try_auto_credentials():
                    logger.info("✅ AWS credentials auto-fetched from kmkz-app-secrets")
                    return self.client
            except Exception as auto_e:
                logger.debug(f"Auto-credential fetch failed: {auto_e}")

            # Method 3: Check for AWS CLI configuration
            try:
                import os
                aws_config_dir = os.path.expanduser("~/.aws")
                if os.path.exists(os.path.join(aws_config_dir, "credentials")) or os.path.exists(os.path.join(aws_config_dir, "config")):
                    # Try again with default profile
                    session = boto3.Session()
                    client = session.client("secretsmanager", region_name=self.region_name)
                    client.list_secrets(MaxResults=1)
                    logger.info("✅ AWS Secrets Manager client initialized using AWS CLI configuration")
                    return client
            except Exception as cli_e:
                logger.debug(f"AWS CLI configuration failed: {cli_e}")

            logger.info("🔄 AWS credentials not available, will use environment variables for fallback")
            return None

    def _try_auto_credentials(self) -> bool:
        """Try to auto-fetch AWS credentials from kmkz-app-secrets."""
        try:
            # Check if we have any AWS credentials available through other means
            # (e.g., IAM role, instance profile, etc.)
            import boto3

            # Try to create a session with default credential chain
            session = boto3.Session()
            credentials = session.get_credentials()

            if credentials:
                # Create a temporary client to fetch app secrets
                temp_client = boto3.client(
                    "secretsmanager",
                    region_name=self.region_name,
                    aws_access_key_id=credentials.access_key,
                    aws_secret_access_key=credentials.secret_key,
                    aws_session_token=credentials.token
                )

                # Try to get kmkz-app-secrets
                response = temp_client.get_secret_value(SecretId="kmkz-app-secrets")
                secret_data = json.loads(response["SecretString"])

                # Extract AWS credentials from the secret
                aws_config = secret_data.get("aws", {})
                if aws_config.get("access_key_id") and aws_config.get("secret_access_key"):
                    # Store auto-fetched credentials
                    self._auto_credentials = {
                        "access_key_id": aws_config["access_key_id"],
                        "secret_access_key": aws_config["secret_access_key"],
                        "session_token": aws_config.get("session_token")
                    }

                    # Create new client with auto-fetched credentials
                    self.client = boto3.client(
                        "secretsmanager",
                        region_name=self.region_name,
                        aws_access_key_id=self._auto_credentials["access_key_id"],
                        aws_secret_access_key=self._auto_credentials["secret_access_key"],
                        aws_session_token=self._auto_credentials.get("session_token")
                    )

                    return True

        except Exception as e:
            logger.debug(f"Auto-credential fetch failed: {e}")

        return False

    def _get_credentials_from_env(self) -> Optional[Dict[str, Any]]:
        """Get AWS credentials from environment variables as fallback."""
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        session_token = os.getenv("AWS_SESSION_TOKEN")

        if access_key and secret_key:
            return {
                "access_key_id": access_key,
                "secret_access_key": secret_key,
                "session_token": session_token,
                "groq_api_key": os.getenv("GROQ_API_KEY"),
                "credentials_encryption_key": os.getenv("CREDENTIALS_ENCRYPTION_KEY", "dev-fallback-key")
            }
        return None

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
            # Use direct secret name for kamikaze-be secrets
            # Check if it's a direct AWS secret name or environment-specific
            if secret_name in ["kmkz-db-secrets", "kmkz-app-secrets", "main"]:
                full_secret_name = secret_name
            else:
                full_secret_name = f"kamikaze-be/{self.environment}/{secret_name}"

            logger.debug(f"🔍 Retrieving secret: {full_secret_name}")
            response = self.client.get_secret_value(SecretId=full_secret_name)

            secret_value = json.loads(response["SecretString"])

            # Cache the secret
            self._cache_secret(cache_key, secret_value)

            logger.info(f"✅ Retrieved secret: {secret_name}")
            return secret_value

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                logger.warning(f"⚠️ Secret not found: {full_secret_name}")
            elif error_code == "InvalidRequestException":
                logger.error(f"❌ Invalid request for secret: {full_secret_name}")
            elif error_code == "InvalidParameterException":
                logger.error(f"❌ Invalid parameter for secret: {full_secret_name}")
            else:
                logger.error(f"❌ Error retrieving secret {full_secret_name}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error retrieving secret {secret_name}: {e}")
            return None

    async def get_database_credentials(
        self, database_name: str = "main"
    ) -> DatabaseCredentials:
        """
        Get database credentials from AWS Secrets Manager or environment variables.

        Tries to retrieve credentials from kmkz-db-secrets first, then falls back
        to environment variables.

        Args:
            database_name: Name of the database configuration

        Returns:
            DatabaseCredentials object
        """
        # Try AWS Secrets Manager first using kmkz-db-secrets (RDS format)
        try:
            secret_value = await self._get_secret_value("kmkz-db-secrets")

            if secret_value:
                logger.info(
                    "✅ Using database credentials from AWS Secrets Manager (kmkz-db-secrets)"
                )
                # RDS secret format: username, password, engine, host, port, dbInstanceIdentifier
                return DatabaseCredentials(
                    host=secret_value.get("host", "localhost"),
                    port=int(secret_value.get("port", 5432)),
                    database=secret_value.get("dbname", secret_value.get("dbInstanceIdentifier", "kamikaze")),
                    username=secret_value.get("username", "postgres"),
                    password=secret_value.get("password", ""),
                    ssl_mode="require",  # Use SSL for RDS connections
                    min_size=5,  # Default pool settings for RDS
                    max_size=20,
                    timeout=60,
                )
        except Exception as e:
            logger.warning(
                f"Failed to get database credentials from kmkz-db-secrets: {e}"
            )

        # No fallback to kmkz-secrets - removed as requested

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
            timeout=int(os.getenv("DB_TIMEOUT", "60")),
        )

    async def get_trading_api_keys(self) -> TradingAPIKeys:
        """
        Get trading API keys from AWS Secrets Manager or environment variables.

        Returns:
            TradingAPIKeys object
        """
        # Try AWS Secrets Manager using kmkz-app-secrets
        try:
            secret_value = await self._get_secret_value("kmkz-app-secrets")

            if secret_value:
                trading_config = secret_value.get("trading", {}).get(
                    self.environment, {}
                )

                if trading_config:
                    logger.info(
                        f"✅ Using trading API keys from AWS Secrets Manager (kmkz-app-secrets/{self.environment})"
                    )
                    return TradingAPIKeys(
                        binance_api_key=trading_config.get("binance_api_key"),
                        binance_secret_key=trading_config.get("binance_secret_key"),
                        binance_testnet=trading_config.get("binance_testnet", True),
                        groq_api_key=trading_config.get("groq_api_key"),
                        openai_api_key=trading_config.get("openai_api_key"),
                    )
        except Exception as e:
            logger.warning(f"Failed to get trading API keys from kmkz-app-secrets: {e}")

        # Try to get Groq API key from AWS credentials as fallback
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            try:
                aws_creds = await self.get_aws_credentials()
                groq_api_key = aws_creds.groq_api_key
                if groq_api_key:
                    logger.info("✅ Using Groq API key from AWS credentials (kmkz-app-secrets)")
            except Exception as e:
                logger.debug(f"Could not retrieve Groq API key from AWS: {e}")

        # Fallback to environment variables (Binance credentials now retrieved from database)
        logger.info("📝 Using trading API keys from environment variables")
        logger.info("ℹ️ Binance API credentials should be stored in database, not environment variables")

        # Check if Binance credentials are in environment (for backward compatibility)
        binance_api_key = os.getenv("BINANCE_API_KEY")
        binance_secret_key = os.getenv("BINANCE_SECRET_KEY")

        if binance_api_key and binance_secret_key:
            logger.warning("⚠️ Binance credentials found in environment variables. Consider moving to database for better security.")
        else:
            logger.info("ℹ️ No Binance credentials in environment variables. Will retrieve from database when needed.")

        return TradingAPIKeys(
            binance_api_key=binance_api_key,
            binance_secret_key=binance_secret_key,
            binance_testnet=os.getenv("BINANCE_TESTNET", "true").lower() == "true",
            groq_api_key=groq_api_key,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

    async def get_application_secrets(self) -> ApplicationSecrets:
        """
        Get application secrets from AWS Secrets Manager or environment variables.

        Returns:
            ApplicationSecrets object
        """
        # Try AWS Secrets Manager first using kmkz-app-secrets
        try:
            secret_value = await self._get_secret_value("kmkz-app-secrets")

            if secret_value:
                app_config = secret_value.get("application", {}).get(
                    self.environment, {}
                )

                if app_config:
                    logger.info(
                        f"✅ Using application secrets from AWS Secrets Manager (kmkz-app-secrets/{self.environment})"
                    )
                    return ApplicationSecrets(
                        jwt_secret=app_config.get(
                            "jwt_secret", "default-jwt-secret-change-me"
                        ),
                        encryption_key=app_config.get(
                            "encryption_key", "default-encryption-key"
                        ),
                        credentials_encryption_key=app_config.get(
                            "credentials_encryption_key", ""
                        ),
                        webhook_secret=app_config.get("webhook_secret"),
                    )
        except Exception as e:
            logger.warning(f"Failed to get application secrets from kmkz-app-secrets: {e}")

        # Try to get credentials encryption key from AWS credentials as fallback
        credentials_encryption_key = os.getenv("CREDENTIALS_ENCRYPTION_KEY")
        if not credentials_encryption_key:
            try:
                aws_creds = await self.get_aws_credentials()
                credentials_encryption_key = aws_creds.credentials_encryption_key
                if credentials_encryption_key:
                    logger.info("✅ Using credentials encryption key from AWS credentials (kmkz-app-secrets)")
            except Exception as e:
                logger.debug(f"Could not retrieve credentials encryption key from AWS: {e}")

        # Fallback to environment variables
        logger.info("📝 Using application secrets from environment variables")
        return ApplicationSecrets(
            jwt_secret=os.getenv("JWT_SECRET", "your-secret-key-change-in-production"),
            encryption_key=os.getenv("ENCRYPTION_KEY", "default-encryption-key"),
            credentials_encryption_key=credentials_encryption_key or "",
            webhook_secret=os.getenv("WEBHOOK_SECRET"),
        )

    async def get_aws_credentials(self) -> AWSCredentials:
        """
        Get AWS credentials from AWS Secrets Manager or environment variables.

        Tries to retrieve credentials from kmkz-app-secrets first, then falls back
        to environment variables.

        Returns:
            AWSCredentials object
        """
        # Try AWS Secrets Manager first using kmkz-app-secrets
        try:
            secret_value = await self._get_secret_value("kmkz-app-secrets")

            if secret_value:
                logger.info(
                    "✅ Using AWS credentials from AWS Secrets Manager (kmkz-app-secrets)"
                )
                return AWSCredentials(
                    access_key_id=secret_value.get("AWS_ACCESS_KEY_ID", ""),
                    secret_access_key=secret_value.get("AWS_SECRET_ACCESS_KEY", ""),
                    region=secret_value.get("AWS_REGION", "us-east-1"),
                    session_token=secret_value.get("AWS_SESSION_TOKEN"),
                    groq_api_key=secret_value.get("GROQ_API_KEY"),
                    credentials_encryption_key=secret_value.get("CREDENTIALS_ENCRYPTION_KEY"),
                )
        except Exception as e:
            logger.warning(f"Failed to get AWS credentials from kmkz-app-secrets: {e}")

        # Fallback to environment variables
        logger.info("📝 Using AWS credentials from environment variables")
        return AWSCredentials(
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID", ""),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", ""),
            region=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
            groq_api_key=os.getenv("GROQ_API_KEY"),
            credentials_encryption_key=os.getenv("CREDENTIALS_ENCRYPTION_KEY"),
        )

    async def update_secret(
        self, secret_name: str, secret_value: Dict[str, Any]
    ) -> bool:
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
                SecretId=full_secret_name, SecretString=json.dumps(secret_value)
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

    async def create_secret(
        self, secret_name: str, secret_value: Dict[str, Any], description: str = ""
    ) -> bool:
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
                Description=description
                or f"FluxTrader {self.environment} - {secret_name}",
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


async def get_aws_credentials() -> AWSCredentials:
    """Get AWS credentials."""
    return await secrets_manager.get_aws_credentials()


# Simple test cases for AWS integration
async def test_aws_secrets():
    """Simple test for AWS Secrets Manager integration."""
    print("🧪 Testing AWS Secrets Manager Integration")
    print("=" * 50)

    try:
        # Test database credentials
        print("📊 Testing database credentials...")
        db_creds = await get_database_credentials()
        print(f"   ✅ Database: {db_creds.host}:{db_creds.port}/{db_creds.database}")

        # Test AWS credentials (includes GROQ_API_KEY)
        print("🔑 Testing AWS credentials...")
        aws_creds = await get_aws_credentials()
        print(f"   ✅ AWS Access Key: {'***' if aws_creds.access_key_id else 'Not set'}")
        print(f"   ✅ AWS Region: {aws_creds.region}")
        print(f"   ✅ Groq API Key: {'***' if aws_creds.groq_api_key else 'Not set'}")
        print(f"   ✅ Credentials Encryption Key: {'***' if aws_creds.credentials_encryption_key else 'Not set'}")

        # Test standalone functions
        print("🔧 Testing standalone functions...")
        try:
            db_secret = get_kmkz_db_secret()
            print(f"   ✅ DB Secret: {'Retrieved' if db_secret else 'Not found'}")
        except Exception as e:
            print(f"   ⚠️ DB Secret: {e}")

        try:
            app_secret = get_kmkz_app_secret()
            print(f"   ✅ App Secret: {'Retrieved' if app_secret else 'Not found'}")
        except Exception as e:
            print(f"   ⚠️ App Secret: {e}")

        print("✅ All tests completed!")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


# Example usage and testing
async def main():
    """Example usage of the SecretsManager."""
    await test_aws_secrets()


def get_kmkz_db_secret():
    """
    Standalone function to retrieve database credentials from kmkz-db-secrets.
    This follows the AWS-generated RDS secret format.

    Returns:
        dict: Database credentials with keys: username, password, engine, host, port, dbInstanceIdentifier
    """
    if not AWS_AVAILABLE:
        logger.error("❌ boto3 not available, cannot retrieve AWS secrets")
        return None

    secret_name = "kmkz-db-secrets"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )

        # Parse the secret string
        secret = json.loads(get_secret_value_response['SecretString'])

        logger.info(f"✅ Successfully retrieved {secret_name}")
        return secret

    except ClientError as e:
        logger.error(f"❌ Error retrieving secret {secret_name}: {e}")
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving secret {secret_name}: {e}")
        raise e


def get_kmkz_app_secret():
    """
    Standalone function to retrieve AWS credentials from kmkz-app-secrets.
    This contains AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, GROQ_API_KEY, and CREDENTIALS_ENCRYPTION_KEY.

    Returns:
        dict: AWS credentials with keys: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, GROQ_API_KEY, CREDENTIALS_ENCRYPTION_KEY
    """
    if not AWS_AVAILABLE:
        logger.error("❌ boto3 not available, cannot retrieve AWS secrets")
        return None

    secret_name = "kmkz-app-secrets"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )

        # Parse the secret string
        secret = json.loads(get_secret_value_response['SecretString'])

        logger.info(f"✅ Successfully retrieved {secret_name}")
        return secret

    except ClientError as e:
        logger.error(f"❌ Error retrieving secret {secret_name}: {e}")
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving secret {secret_name}: {e}")
        raise e


# Alias for backward compatibility
AWSSecretsManager = SecretsManager


if __name__ == "__main__":
    asyncio.run(main())
