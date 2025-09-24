import jwt
import json
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User

def jwt_required(view_func):
    """
    Decorator to require JWT authentication for API views
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return JsonResponse({'error': 'Missing or invalid authorization header'}, status=401)
        
        token = auth_header.split(' ')[1]
        
        try:
            # Use JWT_SECRET_KEY from settings or fallback to SECRET_KEY
            jwt_secret = getattr(settings, 'SIMPLE_JWT', {}).get('SIGNING_KEY', settings.SECRET_KEY)
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            user_id = payload.get('user_id')
            
            if not user_id:
                return JsonResponse({'error': 'Invalid token payload'}, status=401)
            
            # Get user from database
            try:
                user = User.objects.get(id=user_id)
                request.jwt_user = user
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=401)
            
            return view_func(request, *args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token has expired'}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({'error': 'Invalid token'}, status=401)
    
    return wrapper