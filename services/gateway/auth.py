"""
JWT Authentication middleware for the API Gateway
This module handles JWT token validation and user authentication
"""

import jwt
import os
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Header, Depends
from datetime import datetime, timedelta

# Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', os.environ.get('SECRET_KEY', 'your-super-secret-jwt-key-change-this-in-production'))
JWT_ALGORITHM = 'HS256'
FRONTEND_SERVICE_URL = os.environ.get('FRONTEND_SERVICE_URL', 'http://frontend:8000')

class JWTAuth:
    """JWT Authentication handler for the API Gateway"""
    
    def __init__(self):
        self.secret_key = JWT_SECRET_KEY
        self.algorithm = JWT_ALGORITHM
        self.frontend_url = FRONTEND_SERVICE_URL
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            if 'exp' in payload:
                exp_timestamp = payload['exp']
                if datetime.utcnow() > datetime.utcfromtimestamp(exp_timestamp):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )
            
            # Validate token type (allow both user_token and service_token)
            token_type = payload.get('type')
            if token_type not in ['user_token', 'service_token']:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def get_user_from_token(self, token: str) -> Dict[str, Any]:
        """
        Extract user information from JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Dict containing user information
        """
        payload = self.decode_token(token)
        
        return {
            'user_id': payload.get('user_id'),
            'username': payload.get('username'),
            'email': payload.get('email'),
            'is_staff': payload.get('is_staff', False),
            'is_superuser': payload.get('is_superuser', False),
            'groups': payload.get('groups', []),
            'auth_method': payload.get('auth_method', 'unknown')
        }
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """
        Refresh an access token using a refresh token
        
        Args:
            refresh_token: The refresh token string
            
        Returns:
            Dict with new tokens or None if refresh failed
        """
        try:
            response = requests.post(
                f"{self.frontend_url}/api/auth/refresh/",
                json={'refresh': refresh_token},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except requests.RequestException:
            return None

# Global auth instance
jwt_auth = JWTAuth()

async def get_current_user(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    FastAPI dependency to get current authenticated user from JWT token
    
    Args:
        authorization: Authorization header containing JWT token
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If authentication fails
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    try:
        user_info = jwt_auth.get_user_from_token(authorization)
        return user_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )

async def get_optional_user(authorization: str = Header(None)) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency to optionally get current user (for endpoints that work with or without auth)
    
    Args:
        authorization: Authorization header containing JWT token
        
    Returns:
        Dict containing user information or None if not authenticated
    """
    if not authorization:
        return None
    
    try:
        user_info = jwt_auth.get_user_from_token(authorization)
        return user_info
    except Exception:
        return None

def require_staff(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    FastAPI dependency that requires staff privileges
    
    Args:
        user: Current user information from get_current_user
        
    Returns:
        User information if they are staff
        
    Raises:
        HTTPException: If user is not staff
    """
    if not user.get('is_staff', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff privileges required"
        )
    return user

def require_superuser(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    FastAPI dependency that requires superuser privileges
    
    Args:
        user: Current user information from get_current_user
        
    Returns:
        User information if they are superuser
        
    Raises:
        HTTPException: If user is not superuser
    """
    if not user.get('is_superuser', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser privileges required"
        )
    return user