"""
Global User Context System for Dynamic User Management
Eliminates hardcoded user references and provides consistent user context across all backend modules.
"""

import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from contextvars import ContextVar
from fastapi import Request, HTTPException
import jwt
from src.infrastructure.credentials_database import CredentialsDatabase
from src.infrastructure.auth_database import AuthDatabase

logger = logging.getLogger(__name__)

# Global context variable for current user
current_user_context: ContextVar[Optional['UserContext']] = ContextVar('current_user_context', default=None)

@dataclass
class UserContext:
    """Complete user context with all necessary information"""
    user_id: int
    username: str
    email: str
    binance_api_key: Optional[str] = None
    binance_secret_key: Optional[str] = None
    testnet_api_key: Optional[str] = None
    testnet_secret_key: Optional[str] = None
    is_mainnet: bool = True
    has_credentials: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'binance_api_key': self.binance_api_key,
            'binance_secret_key': self.binance_secret_key,
            'testnet_api_key': self.testnet_api_key,
            'testnet_secret_key': self.testnet_secret_key,
            'is_mainnet': self.is_mainnet,
            'has_credentials': self.has_credentials
        }

class UserContextManager:
    """Manages user context extraction and database operations"""
    
    def __init__(self):
        self.credentials_db = CredentialsDatabase()
        self.auth_db = AuthDatabase()
        self.logger = logging.getLogger(__name__)
    
    async def extract_user_from_token(self, token: str) -> Optional[UserContext]:
        """Extract user context from JWT token"""
        try:
            # Decode JWT token (adjust secret key as needed)
            from src.infrastructure.auth_database import SECRET_KEY
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = int(payload.get("sub"))
            
            if not user_id:
                self.logger.error("No user ID found in JWT token")
                return None
            
            # Get user details from auth database
            user_details = await self.auth_db.get_user_by_id(user_id)
            if not user_details:
                self.logger.error(f"User {user_id} not found in auth database")
                return None
            
            # Create user context
            user_context = UserContext(
                user_id=user_id,
                username=user_details.get('username', ''),
                email=user_details.get('email', '')
            )
            
            # Load credentials
            await self._load_user_credentials(user_context)
            
            self.logger.info(f"✅ User context created for user {user_id} ({user_context.email})")
            return user_context
            
        except jwt.ExpiredSignatureError:
            self.logger.error("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            self.logger.error(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to extract user from token: {e}")
            return None
    
    async def extract_user_from_request(self, request: Request) -> Optional[UserContext]:
        """Extract user context from FastAPI request"""
        try:
            # Get authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                self.logger.warning("No valid authorization header found")
                return None
            
            token = auth_header.split(" ")[1]
            return await self.extract_user_from_token(token)
            
        except Exception as e:
            self.logger.error(f"Failed to extract user from request: {e}")
            return None
    
    async def _load_user_credentials(self, user_context: UserContext):
        """Load user credentials from database"""
        try:
            # Try to get mainnet credentials first
            mainnet_creds = await self.credentials_db.get_binance_credentials(user_context.user_id, is_mainnet=True)
            if mainnet_creds:
                user_context.binance_api_key = mainnet_creds['api_key']
                user_context.binance_secret_key = mainnet_creds['secret_key']
                user_context.is_mainnet = True
                user_context.has_credentials = True
                self.logger.info(f"✅ Loaded mainnet credentials for user {user_context.user_id}")
            else:
                # Try testnet credentials
                testnet_creds = await self.credentials_db.get_binance_credentials(user_context.user_id, is_mainnet=False)
                if testnet_creds:
                    user_context.testnet_api_key = testnet_creds['api_key']
                    user_context.testnet_secret_key = testnet_creds['secret_key']
                    user_context.is_mainnet = False
                    user_context.has_credentials = True
                    self.logger.info(f"✅ Loaded testnet credentials for user {user_context.user_id}")
                else:
                    self.logger.warning(f"⚠️ No credentials found for user {user_context.user_id}")
                    user_context.has_credentials = False
                    
        except Exception as e:
            self.logger.error(f"Failed to load credentials for user {user_context.user_id}: {e}")
            user_context.has_credentials = False

# Global instance
user_context_manager = UserContextManager()

def set_current_user_context(user_context: UserContext):
    """Set the current user context"""
    current_user_context.set(user_context)
    logger.info(f"🔧 Set user context for user {user_context.user_id} ({user_context.email})")

def get_current_user_context() -> Optional[UserContext]:
    """Get the current user context"""
    return current_user_context.get()

def require_user_context() -> UserContext:
    """Get current user context or raise exception if not available"""
    user_context = get_current_user_context()
    if not user_context:
        raise HTTPException(status_code=401, detail="User context not available")
    return user_context

async def extract_and_set_user_context(request: Request) -> Optional[UserContext]:
    """Extract user context from request and set it globally"""
    user_context = await user_context_manager.extract_user_from_request(request)
    if user_context:
        set_current_user_context(user_context)
    return user_context

# Utility functions for backward compatibility
def get_current_user_id() -> Optional[int]:
    """Get current user ID"""
    context = get_current_user_context()
    return context.user_id if context else None

def get_current_user_credentials() -> Optional[Dict[str, str]]:
    """Get current user's Binance credentials"""
    context = get_current_user_context()
    if not context or not context.has_credentials:
        return None
    
    if context.is_mainnet:
        return {
            'api_key': context.binance_api_key,
            'secret_key': context.binance_secret_key,
            'is_mainnet': True
        }
    else:
        return {
            'api_key': context.testnet_api_key,
            'secret_key': context.testnet_secret_key,
            'is_mainnet': False
        }

def get_current_user_email() -> Optional[str]:
    """Get current user email"""
    context = get_current_user_context()
    return context.email if context else None

def get_current_username() -> Optional[str]:
    """Get current username"""
    context = get_current_user_context()
    return context.username if context else None
