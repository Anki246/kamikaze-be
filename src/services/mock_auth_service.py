"""
Mock authentication service for testing without database
"""

import logging
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class MockUser:
    """Mock user class."""
    
    def __init__(self, id: int, email: str, name: str, password_hash: str, role: str = 'trader'):
        self.id = id
        self.email = email
        self.name = name
        self.password_hash = password_hash
        self.role = role
        self.is_active = True
        self.is_verified = True
        self.created_at = datetime.utcnow()
        self.last_login = None
        self.avatar_url = None
        self.bio = None
        self.timezone = 'UTC'


class MockAuthService:
    """Mock service for handling authentication operations without database."""
    
    def __init__(self):
        """Initialize mock authentication service."""
        # In-memory user storage
        self.users = {}
        self.sessions = {}
        self.next_user_id = 1
        
        # Create demo user
        self._create_demo_user()
    
    def _create_demo_user(self):
        """Create the demo user."""
        demo_password_hash = hashlib.sha256("demo123".encode()).hexdigest()
        demo_user = MockUser(
            id=1,
            email="demo@kamikaze.com",
            name="Demo User",
            password_hash=demo_password_hash,
            role="trader"
        )
        self.users["demo@kamikaze.com"] = demo_user
        self.next_user_id = 2
        logger.info("Created demo user: demo@kamikaze.com")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return self._hash_password(password) == password_hash
    
    def _user_to_dict(self, user: MockUser) -> Dict[str, Any]:
        """Convert user object to dictionary."""
        return {
            'id': user.id,
            'email': user.email,
            'name': user.name,
            'role': user.role,
            'is_active': user.is_active,
            'is_verified': user.is_verified,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'avatar_url': user.avatar_url,
            'bio': user.bio,
            'timezone': user.timezone
        }
    
    def register_user(self, email: str, name: str, password: str, role: str = 'trader') -> Dict[str, Any]:
        """Register a new user.
        
        Args:
            email: User email
            name: User name
            password: Plain text password
            role: User role
            
        Returns:
            Dictionary with registration result
        """
        try:
            # Validate input
            if not email or not name or not password:
                return {
                    'success': False,
                    'error': 'Email, name, and password are required'
                }
            
            if len(password) < 6:
                return {
                    'success': False,
                    'error': 'Password must be at least 6 characters long'
                }
            
            # Check if user already exists
            if email in self.users:
                return {
                    'success': False,
                    'error': 'An account with this email already exists'
                }
            
            # Create user
            password_hash = self._hash_password(password)
            user = MockUser(
                id=self.next_user_id,
                email=email,
                name=name,
                password_hash=password_hash,
                role=role
            )
            
            self.users[email] = user
            self.next_user_id += 1
            
            logger.info(f"User registered successfully: {email}")
            return {
                'success': True,
                'user': self._user_to_dict(user)
            }
            
        except Exception as e:
            logger.error(f"Error in register_user: {e}")
            return {
                'success': False,
                'error': 'Registration failed'
            }
    
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Login a user.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Dictionary with login result and tokens
        """
        try:
            # Validate input
            if not email or not password:
                return {
                    'success': False,
                    'error': 'Email and password are required'
                }
            
            # Check if user exists
            user = self.users.get(email)
            if not user:
                return {
                    'success': False,
                    'error': 'Invalid email or password'
                }
            
            # Verify password
            if not self._verify_password(password, user.password_hash):
                return {
                    'success': False,
                    'error': 'Invalid email or password'
                }
            
            # Update last login
            user.last_login = datetime.utcnow()
            
            # Create session tokens
            access_token = secrets.token_urlsafe(32)
            refresh_token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=24)
            
            session_data = {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'token_type': 'bearer',
                'expires_in': 86400,  # 24 hours in seconds
                'expires_at': expires_at,
                'user_id': user.id
            }
            
            self.sessions[access_token] = session_data
            
            logger.info(f"User logged in successfully: {email}")
            return {
                'success': True,
                'user': self._user_to_dict(user),
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer',
                    'expires_in': 86400
                }
            }
            
        except Exception as e:
            logger.error(f"Error in login_user: {e}")
            return {
                'success': False,
                'error': 'Login failed'
            }
    
    def get_user_by_token(self, token: str) -> Optional[MockUser]:
        """Get user by access token.
        
        Args:
            token: Access token
            
        Returns:
            User object if token is valid, None otherwise
        """
        try:
            session = self.sessions.get(token)
            if not session:
                return None
            
            # Check if token is expired
            if datetime.utcnow() > session['expires_at']:
                del self.sessions[token]
                return None
            
            # Find user by ID
            user_id = session['user_id']
            for user in self.users.values():
                if user.id == user_id:
                    return user
            
            return None
            
        except Exception as e:
            logger.error(f"Error in get_user_by_token: {e}")
            return None
    
    def logout_user(self, token: str) -> bool:
        """Logout a user by invalidating their token.
        
        Args:
            token: Access token
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if token in self.sessions:
                del self.sessions[token]
                return True
            return False
        except Exception as e:
            logger.error(f"Error in logout_user: {e}")
            return False


# Global mock auth service instance
mock_auth_service = MockAuthService()
