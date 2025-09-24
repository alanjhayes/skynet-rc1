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
            
            # Validate token type (allow both user_token, service_token, and Django SimpleJWT tokens)
            token_type = payload.get('type')  # Custom tokens
            django_token_type = payload.get('token_type')  # Django SimpleJWT tokens
            
            # Accept custom tokens (user_token, service_token) or Django SimpleJWT tokens (access)
            valid_custom_token = token_type in ['user_token', 'service_token']
            valid_django_token = django_token_type == 'access'
            
            if not (valid_custom_token or valid_django_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token type. Got type='{token_type}', token_type='{django_token_type}'"
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
        
        # Handle Django SimpleJWT tokens vs custom tokens
        if payload.get('token_type') == 'access':
            # Django SimpleJWT token - fetch user info from frontend service
            try:
                headers = {'Authorization': f'Bearer {token}'}
                response = requests.get(f"{self.frontend_url}/api/auth/profile/", headers=headers, timeout=10)
                if response.status_code == 200:
                    user_data = response.json().get('user', {})
                    return {
                        'user_id': user_data.get('id'),
                        'username': user_data.get('username'),
                        'email': user_data.get('email', ''),
                        'is_staff': user_data.get('is_staff', False),
                        'is_superuser': user_data.get('is_superuser', False),
                        'groups': user_data.get('groups', []),
                        'auth_method': user_data.get('auth_method', 'local')
                    }
                else:
                    # Fallback to basic user info from token
                    return {
                        'user_id': payload.get('user_id'),
                        'username': 'unknown',
                        'email': '',
                        'is_staff': False,
                        'is_superuser': False,
                        'groups': [],
                        'auth_method': 'django_jwt'
                    }
            except Exception:
                # Fallback if frontend service is unavailable
                return {
                    'user_id': payload.get('user_id'),
                    'username': 'unknown',
                    'email': '',
                    'is_staff': False,
                    'is_superuser': False,
                    'groups': [],
                    'auth_method': 'django_jwt'
                }
        else:
            # Custom token with full user info
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