import jwt
import os
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional

security = HTTPBearer()

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'django-insecure-change-this-in-production')
JWT_ALGORITHM = 'HS256'

def verify_jwt_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Verify JWT token and extract user information
    """
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Extract user information
        user_id = payload.get('user_id')
        username = payload.get('username')  # Will be available if we add it to the token
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user_id"
            )
        
        return {
            'user_id': user_id,
            'username': username,
            'token_type': payload.get('token_type'),
            'exp': payload.get('exp'),
            'jti': payload.get('jti')
        }
        
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

def get_current_user(token_data: Dict = Depends(verify_jwt_token)) -> Dict:
    """
    Get current user from JWT token
    """
    return token_data

def get_user_collection_name(user_id: int, username: Optional[str] = None) -> str:
    """
    Generate user-specific collection name
    Use username if available for better security, fallback to user_id
    """
    if username:
        # Sanitize username for Qdrant collection name
        safe_username = ''.join(c for c in username if c.isalnum() or c in '-_').lower()
        return f"user_{safe_username}_documents"
    else:
        return f"user_{user_id}_documents"

# Service-to-service authentication
def verify_service_token(token: str, expected_service: str = None) -> Dict:
    """
    Verify service-to-service JWT tokens
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Check if it's a service token
        if payload.get('type') != 'service_token':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service token type"
            )
        
        # Verify service name if specified
        if expected_service and payload.get('service') != expected_service:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Expected service {expected_service}, got {payload.get('service')}"
            )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token"
        )

def get_service_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Get service information from service token
    """
    token = credentials.credentials
    return verify_service_token(token)