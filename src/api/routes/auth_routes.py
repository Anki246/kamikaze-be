"""
Authentication API Routes for FluxTrader
Provides REST API endpoints for user authentication and session management
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel, EmailStr, Field

from ...infrastructure.auth_database import auth_db

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Security scheme
security = HTTPBearer()

# Remove FastMCP dependency - using direct database connection
# database_client = None

# def set_database_client(db_client):
#     """Set the global database client."""
#     global database_client
#     database_client = db_client

# JWT Configuration
JWT_SECRET = "your-secret-key-change-in-production"  # Should be from environment
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


# Pydantic models
class SignUpRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50)


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


# Utility functions
def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    try:
        salt, password_hash = hashed_password.split(":")
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """Create JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except ExpiredSignatureError:
        return None
    except InvalidTokenError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Get current authenticated user."""
    try:
        # Ensure database connection
        if not await auth_db.ensure_connected():
            logger.error("Database connection failed in get_current_user")
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        token = credentials.credentials
        logger.debug(f"Verifying token for authentication: {token[:20]}...")

        payload = verify_token(token)

        if not payload or payload.get("type") != "access":
            logger.warning(f"Invalid token payload: {payload}")
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("No user ID found in token payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        # Get user from database
        logger.debug(f"Looking up user with ID: {user_id}")
        user = await auth_db.get_user_by_id(int(user_id))
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            raise HTTPException(status_code=401, detail="User not found")

        if not user.get("is_active", True):
            logger.warning(f"User account disabled for ID: {user_id}")
            raise HTTPException(status_code=401, detail="User account is disabled")

        # Remove sensitive information
        user.pop("hashed_password", None)
        logger.debug(f"Successfully authenticated user: {user.get('email', 'unknown')}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/signup", response_model=AuthResponse)
async def sign_up(request: SignUpRequest, req: Request):
    """Register a new user."""
    try:
        # Ensure database connection
        if not await auth_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        # Check if user already exists
        username = request.username or request.email.split("@")[0]
        existing_user = await auth_db.get_user_by_email(request.email)

        if existing_user:
            return AuthResponse(
                success=False, message="User with this email already exists"
            )

        # Hash password
        hashed_password = hash_password(request.password)

        # Generate UUID
        user_uuid = str(uuid.uuid4())

        # Insert new user
        user_data = {
            "uuid": user_uuid,
            "username": username,
            "email": request.email,
            "full_name": request.name,
            "hashed_password": hashed_password,
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
            "role": "trader",
            "trading_experience": "beginner",
            "risk_tolerance": "medium",
            "timezone": "UTC",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        new_user = await auth_db.create_user(user_data)

        if not new_user:
            logger.error("Failed to create user in database")
            return AuthResponse(success=False, message="Failed to create user account")

        user_id = new_user["id"]

        # Create tokens
        access_token = create_access_token(data={"sub": str(user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user_id)})

        # Create session record
        session_data = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "ip_address": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
            "device_info": None,
            "location": None,
            "is_active": True,
            "is_revoked": False,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        }

        session_created = await auth_db.create_session(session_data)
        if not session_created:
            logger.warning(
                "Failed to create session, but user was created successfully"
            )

        # Remove sensitive data from response
        new_user.pop("hashed_password", None)

        return AuthResponse(
            success=True,
            message="Account created successfully",
            user=new_user,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except Exception as e:
        logger.error(f"Signup error: {e}")
        return AuthResponse(
            success=False, message="An error occurred during registration"
        )


@router.post("/signin", response_model=AuthResponse)
async def sign_in(request: SignInRequest, req: Request):
    """Authenticate user and create session."""
    try:
        # Ensure database connection
        if not await auth_db.ensure_connected():
            raise HTTPException(
                status_code=503, detail="Database service not available"
            )

        # Get user by email
        logger.info(f"Looking up user with email: {request.email}")
        user = await auth_db.get_user_by_email(request.email)

        if not user:
            logger.warning(f"No user found with email: {request.email}")
            return AuthResponse(success=False, message="Invalid email or password")

        # Verify password
        stored_password = user.get("hashed_password")
        logger.info(
            f"Verifying password for user {user.get('id')}, stored password length: {len(stored_password) if stored_password else 0}"
        )

        password_valid = verify_password(request.password, stored_password)
        logger.info(f"Password verification result: {password_valid}")

        if not password_valid:
            logger.warning(f"Password verification failed for user: {request.email}")
            return AuthResponse(success=False, message="Invalid email or password")

        user_id = user["id"]

        # Update last login
        await auth_db.update_user_login(user_id, datetime.now(timezone.utc))

        # Create tokens
        access_token = create_access_token(data={"sub": str(user_id)})
        refresh_token = create_refresh_token(data={"sub": str(user_id)})

        # Create session record
        session_data = {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "ip_address": req.client.host if req.client else None,
            "user_agent": req.headers.get("user-agent"),
            "device_info": None,
            "location": None,
            "is_active": True,
            "is_revoked": False,
            "created_at": datetime.now(timezone.utc),
            "last_activity": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc)
            + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        }

        session_created = await auth_db.create_session(session_data)
        if not session_created:
            logger.warning("Failed to create session, but login was successful")

        # Remove sensitive data from response
        user.pop("hashed_password", None)

        return AuthResponse(
            success=True,
            message="Login successful",
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    except Exception as e:
        logger.error(f"Signin error: {e}")
        return AuthResponse(success=False, message="An error occurred during login")


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshTokenRequest):
    """Refresh access token using refresh token."""
    # Ensure database connection
    if not await auth_db.ensure_connected():
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        # Verify refresh token
        payload = verify_token(request.refresh_token)

        if not payload or payload.get("type") != "refresh":
            return AuthResponse(
                success=False, message="Invalid or expired refresh token"
            )

        user_id = payload.get("sub")
        if not user_id:
            return AuthResponse(success=False, message="Invalid token payload")

        # Get user from database
        user = await auth_db.get_user_by_id(int(user_id))
        if not user or not user.get("is_active", True):
            return AuthResponse(success=False, message="User not found or inactive")

        # Create new access token
        new_access_token = create_access_token(data={"sub": str(user_id)})

        # Remove sensitive data
        user.pop("hashed_password", None)

        return AuthResponse(
            success=True,
            message="Token refreshed successfully",
            user=user,
            access_token=new_access_token,
            refresh_token=request.refresh_token,
        )

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return AuthResponse(success=False, message="Failed to refresh token")


@router.post("/logout")
async def logout(
    current_user: Dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Logout user and revoke session."""
    if not database_client:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        access_token = credentials.credentials
        user_id = current_user["id"]

        # Revoke all active sessions for this user with this access token
        await database_client.call_tool(
            "update_record",
            {
                "table_name": "user_sessions",
                "data": {
                    "is_active": False,
                    "is_revoked": True,
                    "revoked_reason": "user_logout",
                    "revoked_at": datetime.utcnow(),
                },
                "where_clause": "user_id = $1 AND access_token = $2",
                "where_params": [user_id, access_token],
            },
        )

        return {"success": True, "message": "Logged out successfully"}

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"success": False, "message": "Failed to logout"}


@router.get("/me")
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """Get current authenticated user information."""
    return {"success": True, "user": current_user}


@router.get("/sessions")
async def get_user_sessions(current_user: Dict = Depends(get_current_user)):
    """Get user's active sessions."""
    if not database_client:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        user_id = current_user["id"]

        query = """
            SELECT session_id, ip_address, user_agent, device_info, location,
                   is_active, created_at, last_activity, expires_at
            FROM user_sessions
            WHERE user_id = $1 AND is_revoked = false
            ORDER BY last_activity DESC
        """

        result = await database_client.call_tool(
            "execute_select_query", {"query": query, "params": [user_id], "limit": 50}
        )

        if result.get("success"):
            sessions = result.get("data", {}).get("results", [])
            return {"success": True, "sessions": sessions, "count": len(sessions)}
        else:
            return {"success": False, "message": "Failed to retrieve sessions"}

    except Exception as e:
        logger.error(f"Get sessions error: {e}")
        return {"success": False, "message": "Failed to retrieve sessions"}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str, current_user: Dict = Depends(get_current_user)
):
    """Revoke a specific session."""
    if not database_client:
        raise HTTPException(status_code=503, detail="Database service not available")

    try:
        user_id = current_user["id"]

        # Revoke the specific session
        result = await database_client.call_tool(
            "update_record",
            {
                "table_name": "user_sessions",
                "data": {
                    "is_active": False,
                    "is_revoked": True,
                    "revoked_reason": "user_revoked",
                    "revoked_at": datetime.utcnow(),
                },
                "where_clause": "user_id = $1 AND session_id = $2",
                "where_params": [user_id, session_id],
            },
        )

        return {"success": True, "message": "Session revoked successfully"}

    except Exception as e:
        logger.error(f"Revoke session error: {e}")
        return {"success": False, "message": "Failed to revoke session"}
