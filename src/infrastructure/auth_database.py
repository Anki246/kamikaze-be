"""
Direct Database Connection for Authentication
Provides reliable, high-performance database operations for authentication system
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg

from .database_config import DatabaseConfig

logger = logging.getLogger(__name__)

# Lazy-loaded database configuration
_db_config = None


def get_db_config():
    """Get database configuration (lazy-loaded)."""
    global _db_config
    if _db_config is None:
        _db_config = DatabaseConfig()
    return _db_config


class AuthDatabase:
    """
    Direct PostgreSQL connection manager specifically for authentication operations.
    Provides reliable, high-performance database access without FastMCP overhead.
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.connected = False
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> bool:
        """Establish connection pool to PostgreSQL database."""
        async with self._connection_lock:
            if self.connected and self.pool:
                return True

            try:
                # Close existing pool if any
                if self.pool:
                    await self.pool.close()

                # Create connection pool with optimized settings for auth
                config = get_db_config()
                self.pool = await asyncpg.create_pool(
                    host=config.host,
                    port=config.port,
                    database=config.database,
                    user=config.user,
                    password=config.password,
                    # Optimized for auth operations
                    min_size=2,  # Keep minimum connections for auth
                    max_size=10,  # Reasonable max for auth load
                    command_timeout=10,  # Shorter timeout for auth operations
                    server_settings={
                        "application_name": "kamikaze_auth",
                        "search_path": "public",
                    },
                )

                # Test connection
                async with self.pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")

                self.connected = True
                logger.info(f"✅ Auth database connected: {config.database}")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to connect auth database: {e}")
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
            logger.info("🔌 Auth database disconnected")

    async def ensure_connected(self) -> bool:
        """Ensure database connection is available."""
        if not self.connected or not self.pool:
            return await self.connect()

        try:
            # Quick connection test
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Auth DB connection test failed, reconnecting: {e}")
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
    # User Management Operations
    # ============================================================================

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new user in the database."""
        try:
            async with self.get_connection() as conn:
                # Insert user and return the created record
                query = """
                    INSERT INTO users (
                        uuid, username, email, full_name, hashed_password,
                        is_active, is_verified, is_superuser, role,
                        trading_experience, risk_tolerance, timezone,
                        created_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                    ) RETURNING *
                """

                result = await conn.fetchrow(
                    query,
                    user_data["uuid"],
                    user_data["username"],
                    user_data["email"],
                    user_data["full_name"],
                    user_data["hashed_password"],
                    user_data["is_active"],
                    user_data["is_verified"],
                    user_data["is_superuser"],
                    user_data["role"],
                    user_data["trading_experience"],
                    user_data["risk_tolerance"],
                    user_data["timezone"],
                    user_data["created_at"],
                    user_data["updated_at"],
                )

                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email address."""
        try:
            async with self.get_connection() as conn:
                query = "SELECT * FROM users WHERE email = $1 AND is_active = true"
                result = await conn.fetchrow(query, email)
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            async with self.get_connection() as conn:
                query = "SELECT * FROM users WHERE id = $1 AND is_active = true"
                result = await conn.fetchrow(query, user_id)
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None

    async def update_user_login(self, user_id: int, last_login: Any) -> bool:
        """Update user's last login timestamp."""
        try:
            async with self.get_connection() as conn:
                query = "UPDATE users SET last_login = $1 WHERE id = $2"
                await conn.execute(query, last_login, user_id)
                return True

        except Exception as e:
            logger.error(f"Failed to update user login: {e}")
            return False

    # ============================================================================
    # Session Management Operations
    # ============================================================================

    async def create_session(self, session_data: Dict[str, Any]) -> bool:
        """Create a new user session."""
        try:
            async with self.get_connection() as conn:
                query = """
                    INSERT INTO user_sessions (
                        session_id, user_id, access_token, refresh_token,
                        token_type, ip_address, user_agent, device_info,
                        location, is_active, is_revoked, created_at,
                        last_activity, expires_at
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
                    )
                    RETURNING id
                """

                result = await conn.fetchrow(
                    query,
                    session_data["session_id"],
                    session_data["user_id"],
                    session_data["access_token"],
                    session_data["refresh_token"],
                    session_data["token_type"],
                    session_data.get("ip_address"),
                    session_data.get("user_agent"),
                    session_data.get("device_info"),
                    session_data.get("location"),
                    session_data["is_active"],
                    session_data["is_revoked"],
                    session_data["created_at"],
                    session_data["last_activity"],
                    session_data["expires_at"],
                )
                logger.info(f"✅ Created session with ID: {result['id']}")
                return True

        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            return False

    async def get_session_by_token(
        self, refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get session by refresh token."""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT * FROM user_sessions 
                    WHERE refresh_token = $1 AND is_active = true AND is_revoked = false
                """
                result = await conn.fetchrow(query, refresh_token)
                return dict(result) if result else None

        except Exception as e:
            logger.error(f"Failed to get session by token: {e}")
            return None

    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all active sessions for a user."""
        try:
            async with self.get_connection() as conn:
                query = """
                    SELECT session_id, ip_address, user_agent, device_info,
                           location, is_active, created_at, last_activity, expires_at
                    FROM user_sessions 
                    WHERE user_id = $1 AND is_revoked = false
                    ORDER BY last_activity DESC
                """
                results = await conn.fetch(query, user_id)
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []

    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data."""
        try:
            async with self.get_connection() as conn:
                # Build dynamic update query
                set_clauses = []
                values = []
                param_count = 1

                for key, value in updates.items():
                    set_clauses.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1

                values.append(session_id)  # For WHERE clause

                query = f"""
                    UPDATE user_sessions 
                    SET {', '.join(set_clauses)}
                    WHERE session_id = ${param_count}
                """

                await conn.execute(query, *values)
                return True

        except Exception as e:
            logger.error(f"Failed to update session: {e}")
            return False

    async def revoke_session(
        self, session_id: str, reason: str = "user_revoked"
    ) -> bool:
        """Revoke a specific session."""
        try:
            async with self.get_connection() as conn:
                query = """
                    UPDATE user_sessions 
                    SET is_active = false, is_revoked = true, 
                        revoked_reason = $1, revoked_at = NOW()
                    WHERE session_id = $2
                """
                await conn.execute(query, reason, session_id)
                return True

        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")
            return False

    async def revoke_user_sessions(
        self, user_id: int, reason: str = "user_logout"
    ) -> bool:
        """Revoke all sessions for a user."""
        try:
            async with self.get_connection() as conn:
                query = """
                    UPDATE user_sessions 
                    SET is_active = false, is_revoked = true,
                        revoked_reason = $1, revoked_at = NOW()
                    WHERE user_id = $2 AND is_active = true
                """
                await conn.execute(query, reason, user_id)
                return True

        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")
            return False

    async def cleanup_expired_sessions(self, user_id: int) -> bool:
        """Clean up expired sessions for a user."""
        try:
            async with self.get_connection() as conn:
                query = """
                    DELETE FROM user_sessions
                    WHERE user_id = $1 AND (expires_at < NOW() OR is_revoked = true)
                """
                result = await conn.execute(query, user_id)
                logger.info(f"🧹 Cleaned up expired sessions for user {user_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return False


# Global auth database instance
auth_db = AuthDatabase()
