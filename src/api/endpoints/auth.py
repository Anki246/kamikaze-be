"""
Authentication API endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Initialize services with fallback to mock
try:
    from services.auth_service import AuthService
    auth_service = AuthService()
    logger.info("Using real AuthService")
except Exception as e:
    logger.warning(f"Failed to initialize AuthService, using mock: {e}")
    from services.mock_auth_service import mock_auth_service
    auth_service = mock_auth_service

try:
    from services.exchange_service import ExchangeService
    exchange_service = ExchangeService()
    logger.info("Using real ExchangeService")
except Exception as e:
    logger.warning(f"Failed to initialize ExchangeService: {e}")
    exchange_service = None


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    name: str
    password: str
    role: str = 'trader'


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response."""
    id: int
    email: str
    name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: Optional[str]
    last_login: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    timezone: str


class ApiCredentialsRequest(BaseModel):
    """API credentials request."""
    exchange: str
    api_key: str
    api_secret: str
    testnet: bool = True


# Dependency to get current user from token
async def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Get current user from authorization header.
    
    Args:
        authorization: Authorization header
        
    Returns:
        Current user dictionary
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        # Extract token from "Bearer <token>"
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        user = auth_service.get_current_user(token)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return user
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest):
    """Register a new user.
    
    Args:
        request: Registration request
        
    Returns:
        Created user information
        
    Raises:
        HTTPException: If registration fails
    """
    try:
        result = auth_service.register_user(
            email=request.email,
            name=request.name,
            password=request.password,
            role=request.role
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return UserResponse(**result['user'])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in register endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login")
async def login(request: LoginRequest):
    """Login a user.
    
    Args:
        request: Login request
        
    Returns:
        User information and tokens
        
    Raises:
        HTTPException: If login fails
    """
    try:
        result = auth_service.login_user(
            email=request.email,
            password=request.password
        )
        
        if not result['success']:
            raise HTTPException(status_code=401, detail=result['error'])
        
        return {
            "user": UserResponse(**result['user']),
            "tokens": TokenResponse(**result['tokens'])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in login endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout a user.
    
    Args:
        authorization: Authorization header
        
    Returns:
        Logout confirmation
        
    Raises:
        HTTPException: If logout fails
    """
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        
        # Extract token
        token_type, token = authorization.split(" ")
        if token_type.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        result = auth_service.logout_user(token)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Logout failed'))
        
        return {"message": "Logged out successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in logout endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information
    """
    return UserResponse(**current_user)


@router.get("/profile")
async def get_user_profile(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user profile with statistics.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile with statistics
        
    Raises:
        HTTPException: If profile not found
    """
    try:
        profile = auth_service.get_user_profile(current_user['id'])
        
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        return profile
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/connect-exchange")
async def connect_exchange(
    request: ApiCredentialsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Connect user to an exchange.
    
    Args:
        request: API credentials request
        current_user: Current authenticated user
        
    Returns:
        Connection result
        
    Raises:
        HTTPException: If connection fails
    """
    try:
        result = exchange_service.connect_exchange(
            user_id=current_user['id'],
            exchange=request.exchange,
            api_key=request.api_key,
            api_secret=request.api_secret,
            testnet=request.testnet
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting exchange: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/disconnect-exchange")
async def disconnect_exchange(
    exchange: str,
    testnet: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Disconnect user from an exchange.
    
    Args:
        exchange: Exchange name
        testnet: Whether testnet credentials
        current_user: Current authenticated user
        
    Returns:
        Disconnection result
        
    Raises:
        HTTPException: If disconnection fails
    """
    try:
        result = exchange_service.disconnect_exchange(
            user_id=current_user['id'],
            exchange=exchange,
            testnet=testnet
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting exchange: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/exchanges")
async def get_user_exchanges(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get user's connected exchanges.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        List of connected exchanges
    """
    try:
        exchanges = exchange_service.get_user_exchanges(current_user['id'])
        return {"exchanges": exchanges}
        
    except Exception as e:
        logger.error(f"Error getting user exchanges: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/exchange/{exchange}/account")
async def get_exchange_account_info(
    exchange: str,
    testnet: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get exchange account information.
    
    Args:
        exchange: Exchange name
        testnet: Whether testnet account
        current_user: Current authenticated user
        
    Returns:
        Account information
        
    Raises:
        HTTPException: If account info cannot be retrieved
    """
    try:
        account_info = exchange_service.get_account_info(
            user_id=current_user['id'],
            exchange=exchange,
            testnet=testnet
        )
        
        if not account_info:
            raise HTTPException(status_code=404, detail="Account information not found")
        
        return account_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting exchange account info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/exchange/{exchange}/test-connection")
async def test_exchange_connection(
    exchange: str,
    testnet: bool = True,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Test exchange connection.
    
    Args:
        exchange: Exchange name
        testnet: Whether testnet connection
        current_user: Current authenticated user
        
    Returns:
        Connection test result
        
    Raises:
        HTTPException: If connection test fails
    """
    try:
        result = exchange_service.test_exchange_connection(
            user_id=current_user['id'],
            exchange=exchange,
            testnet=testnet
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing exchange connection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
