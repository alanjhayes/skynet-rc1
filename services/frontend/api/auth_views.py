from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# Import JWT modules conditionally
if getattr(settings, 'JWT_AVAILABLE', False):
    from rest_framework import status
    from rest_framework.decorators import api_view, permission_classes
    from rest_framework.permissions import AllowAny
    from rest_framework.response import Response
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
    from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
else:
    # Fallback for when JWT is not available
    def api_view(methods):
        def decorator(func):
            return func
        return decorator
    
    def permission_classes(perms):
        def decorator(func):
            return func
        return decorator
    
    class AllowAny:
        pass

# JWT-dependent classes (only available if JWT is enabled)
if getattr(settings, 'JWT_AVAILABLE', False):
    class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
        def validate(self, attrs):
            data = super().validate(attrs)
            
            # Add custom claims
            data['user'] = {
                'id': self.user.id,
                'username': self.user.username,
                'email': self.user.email,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'is_staff': self.user.is_staff,
                'is_superuser': self.user.is_superuser,
                'groups': [group.name for group in self.user.groups.all()],
                'auth_method': 'ldap' if getattr(settings, 'LDAP_ENABLED', False) else 'local'
            }
            
            return data

    class CustomTokenObtainPairView(TokenObtainPairView):
        serializer_class = CustomTokenObtainPairSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Universal Login endpoint - supports both local users and LDAP"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            error_response = {'error': 'Username and password are required'}
            if getattr(settings, 'JWT_AVAILABLE', False):
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
            else:
                return JsonResponse(error_response, status=400)
        
        # Authenticate (will try LDAP first if enabled, then local users)
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            user_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'groups': [group.name for group in user.groups.all()],
                'auth_method': 'ldap' if getattr(settings, 'LDAP_ENABLED', False) else 'local'
            }
            
            if getattr(settings, 'JWT_AVAILABLE', False):
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                return Response({
                    'access': str(access_token),
                    'refresh': str(refresh),
                    'user': user_data
                })
            else:
                # Fallback to session authentication
                from django.contrib.auth import login
                login(request, user)
                
                # Create response and ensure session cookie is set
                response = JsonResponse({
                    'success': True,
                    'user': user_data,
                    'message': 'Logged in successfully (session mode)'
                })
                
                # Ensure session is saved and cookie is set
                request.session.save()
                response.set_cookie(
                    'sessionid', 
                    request.session.session_key,
                    max_age=request.session.get_expiry_age(),
                    domain=None,  # Use default domain
                    secure=False,  # Set to True in production with HTTPS
                    httponly=True,
                    samesite='Lax'
                )
                
                return response
        else:
            error_response = {'error': 'Invalid credentials'}
            if getattr(settings, 'JWT_AVAILABLE', False):
                return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return JsonResponse(error_response, status=401)
            
    except json.JSONDecodeError:
        error_response = {'error': 'Invalid JSON'}
        if getattr(settings, 'JWT_AVAILABLE', False):
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse(error_response, status=400)
    except Exception as e:
        error_response = {'error': str(e)}
        if getattr(settings, 'JWT_AVAILABLE', False):
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return JsonResponse(error_response, status=500)

@api_view(['POST'])
def logout_view(request):
    """Logout endpoint - supports both JWT and session logout"""
    try:
        if getattr(settings, 'JWT_AVAILABLE', False):
            data = json.loads(request.body)
            refresh_token = data.get('refresh')
            
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
                
            return Response({
                'message': 'Successfully logged out (JWT)'
            })
        else:
            # Session logout
            from django.contrib.auth import logout
            logout(request)
            return JsonResponse({
                'message': 'Successfully logged out (session)'
            })
    except Exception as e:
        error_response = {'error': str(e)}
        if getattr(settings, 'JWT_AVAILABLE', False):
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        else:
            return JsonResponse(error_response, status=400)

@api_view(['GET'])
def user_profile_view(request):
    """Get current user profile"""
    if not request.user.is_authenticated:
        error_response = {'error': 'Not authenticated'}
        if getattr(settings, 'JWT_AVAILABLE', False):
            return Response(error_response, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return JsonResponse(error_response, status=401)
    
    user_data = {
        'id': request.user.id,
        'username': request.user.username,
        'email': request.user.email,
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'is_staff': request.user.is_staff,
        'is_superuser': request.user.is_superuser,
        'groups': [group.name for group in request.user.groups.all()],
        'auth_method': 'ldap' if getattr(settings, 'LDAP_ENABLED', False) else 'local'
    }
    
    if getattr(settings, 'JWT_AVAILABLE', False):
        return Response({'user': user_data})
    else:
        return JsonResponse({'user': user_data})