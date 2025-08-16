"""
User Context Middleware
Provides dynamic user context across all backend modules using direct database connection.
"""

import logging
from typing import Any, Dict, Optional

import jwt
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ...infrastructure.auth_database import auth_db
from ...infrastructure.user_context import current_user_context
from ..routes.auth_routes import JWT_ALGORITHM, JWT_SECRET

logger = logging.getLogger(__name__)


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract and set user context for all authenticated requests.
    Uses direct database connection for optimal performance.
    """

    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer(auto_error=False)

        # Routes that don't require authentication
        self.public_routes = {
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/signin",
            "/api/v1/auth/signup",
            "/api/v1/auth/refresh",
            "/api/v1/market/status",  # Public market data
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and set user context if authenticated."""

        # Skip authentication for public routes
        if self._is_public_route(request.url.path):
            return await call_next(request)

        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        try:
            # Extract and validate JWT token
            user_context = await self._extract_user_context(request)

            if user_context:
                # Set user context for this request
                token = current_user_context.set(user_context)

                try:
                    # Process the request with user context
                    response = await call_next(request)
                    return response
                finally:
                    # Clean up context
                    current_user_context.set(None)
            else:
                # No valid authentication for protected route
                return JSONResponse(
                    status_code=401, content={"detail": "Authentication required"}
                )

        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
        except Exception as e:
            logger.error(f"User context middleware error: {e}")
            return JSONResponse(
                status_code=500, content={"detail": "Internal server error"}
            )

    def _is_public_route(self, path: str) -> bool:
        """Check if route is public and doesn't require authentication."""
        # Exact match
        if path in self.public_routes:
            return True

        # Pattern matching for public routes
        public_patterns = [
            "/static/",
            "/favicon.ico",
            "/api/v1/market/",  # Public market data endpoints
        ]

        for pattern in public_patterns:
            if path.startswith(pattern):
                return True

        return False

    async def _extract_user_context(self, request: Request) -> Optional[Any]:
        """Extract user context from JWT token using direct database."""
        try:
            # Get Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                return None

            # Extract token
            if not authorization.startswith("Bearer "):
                return None

            token = authorization.split(" ")[1]

            # Decode JWT token
            try:
                payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                user_id = int(payload.get("sub"))

                if not user_id:
                    logger.warning("No user ID in JWT token")
                    return None

            except jwt.ExpiredSignatureError:
                logger.warning("JWT token expired")
                return None
            except jwt.InvalidTokenError as e:
                logger.warning(f"Invalid JWT token: {e}")
                return None

            # Get user from database using direct connection
            if not await auth_db.ensure_connected():
                logger.error("Failed to connect to auth database")
                return None

            user = await auth_db.get_user_by_id(user_id)
            if not user:
                logger.warning(f"User {user_id} not found in database")
                return None

            if not user.get("is_active", False):
                logger.warning(f"User {user_id} is not active")
                return None

            # Create user context directly (simplified approach)
            from ...infrastructure.user_context import UserContext

            user_context = UserContext(
                user_id=user_id,
                email=user.get("email"),
                username=user.get("username", ""),
            )

            logger.debug(
                f"✅ User context created for user {user_id} ({user.get('email')})"
            )
            return user_context

        except Exception as e:
            logger.error(f"Error extracting user context: {e}")
            return None
