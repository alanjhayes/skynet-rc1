import jwt
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User

class ServiceAuthManager:
    """Manage service-to-service authentication"""
    
    @staticmethod
    def generate_service_token(service_name: str, expires_minutes: int = 60) -> str:
        """
        Generate JWT token for service-to-service communication
        
        Args:
            service_name: Name of the calling service
            expires_minutes: Token expiration time in minutes
            
        Returns:
            str: JWT token for service authentication
        """
        payload = {
            'service': service_name,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
            'iss': 'skynet-frontend',
            'type': 'service_token'
        }
        
        secret_key = os.environ.get('JWT_SECRET_KEY', settings.SECRET_KEY)
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def verify_service_token(token: str, expected_service: str = None) -> dict:
        """
        Verify service-to-service JWT token
        
        Args:
            token: JWT token to verify
            expected_service: Expected service name (optional)
            
        Returns:
            dict: Decoded token payload
            
        Raises:
            jwt.InvalidTokenError: If token is invalid
        """
        secret_key = os.environ.get('JWT_SECRET_KEY', settings.SECRET_KEY)
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        
        # Verify token type
        if payload.get('type') != 'service_token':
            raise jwt.InvalidTokenError("Invalid token type")
        
        # Verify service name if specified
        if expected_service and payload.get('service') != expected_service:
            raise jwt.InvalidTokenError(f"Expected service {expected_service}, got {payload.get('service')}")
        
        return payload
    
    @staticmethod
    def get_service_headers(service_name: str) -> dict:
        """
        Get headers for service-to-service requests
        
        Args:
            service_name: Name of the calling service
            
        Returns:
            dict: Headers with service authentication
        """
        token = ServiceAuthManager.generate_service_token(service_name)
        return {
            'Authorization': f'Bearer {token}',
            'X-Service-Auth': service_name,
            'Content-Type': 'application/json'
        }
    
    @staticmethod
    def generate_user_token(user: User, expires_minutes: int = 60) -> str:
        """
        Generate JWT token for a specific user for gateway communication
        
        Args:
            user: Django User instance
            expires_minutes: Token expiration time in minutes
            
        Returns:
            str: JWT token for user authentication
        """
        payload = {
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'groups': [group.name for group in user.groups.all()],
            'auth_method': 'ldap' if getattr(settings, 'LDAP_ENABLED', False) else 'local',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=expires_minutes),
            'iss': 'skynet-frontend',
            'type': 'user_token'
        }
        
        secret_key = os.environ.get('JWT_SECRET_KEY', settings.SECRET_KEY)
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    @staticmethod
    def get_user_headers(user: User) -> dict:
        """
        Get headers for user requests to gateway
        
        Args:
            user: Django User instance
            
        Returns:
            dict: Headers with user authentication
        """
        token = ServiceAuthManager.generate_user_token(user)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }