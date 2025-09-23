from django.urls import path
from . import views
from . import auth_views
from django.conf import settings

# Conditional imports for JWT
if getattr(settings, 'JWT_AVAILABLE', False):
    from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Frontend views
    path('', views.index, name='index'),
    path('chat/', views.chat, name='chat'),
    path('documents/', views.documents, name='documents'),
    
    # API endpoints (using frontend/ prefix to avoid nginx conflicts)
    path('frontend/upload/', views.upload_document, name='upload_document'),
    path('frontend/chat/', views.chat_api, name='chat_api'),
    path('frontend/documents/', views.documents_api, name='documents_api'),
    path('frontend/sessions/', views.sessions_api, name='sessions_api'),
    path('frontend/sessions/<int:session_id>/', views.session_detail_api, name='session_detail_api'),
    
    # Universal Authentication (works with both local users and LDAP)
    path('auth/login/', views.universal_login_page, name='universal_login_page'),
    path('api/auth/login/', auth_views.login_view, name='universal_login'),
    path('api/auth/logout/', auth_views.logout_view, name='universal_logout'),
    path('api/auth/profile/', auth_views.user_profile_view, name='user_profile'),
    
    # Legacy Authentication (keep for compatibility)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]

# Add JWT refresh route if JWT is available
if getattr(settings, 'JWT_AVAILABLE', False):
    urlpatterns.append(
        path('api/auth/refresh/', TokenRefreshView.as_view(), name='jwt_refresh')
    )