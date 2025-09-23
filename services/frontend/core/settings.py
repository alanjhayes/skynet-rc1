import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-in-production')

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

import ipaddress

# Custom ALLOWED_HOSTS validation for IP ranges
def validate_host(host):
    # Allow specific hostnames
    allowed_hosts = ['localhost', '127.0.0.1', '0.0.0.0', 'frontend', 'skynet-rc1-frontend', 'nginx']
    if host in allowed_hosts:
        return True
    
    # Allow 172.16.0.0/12 range (172.16.0.0 - 172.31.255.255)
    try:
        ip = ipaddress.ip_address(host)
        private_range = ipaddress.ip_network('172.16.0.0/12')
        if ip in private_range:
            return True
    except ValueError:
        pass
    
    return False

class CustomAllowedHostsValidator:
    def __call__(self, host):
        return validate_host(host)

# Use wildcard for now and implement custom validation in middleware
ALLOWED_HOSTS = ['*']  # We'll validate in custom middleware

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'api',
]

# JWT Support - always enabled for both local and LDAP users
JWT_ENABLED = os.environ.get('JWT_ENABLED', 'True').lower() == 'true'

if JWT_ENABLED:
    try:
        import rest_framework
        import rest_framework_simplejwt
        INSTALLED_APPS.extend([
            'rest_framework',
            'rest_framework_simplejwt',
        ])
        JWT_AVAILABLE = True
    except ImportError:
        JWT_AVAILABLE = False
        print("Warning: JWT packages not installed. JWT authentication disabled.")
else:
    JWT_AVAILABLE = False

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'core.middleware.CustomAllowedHostsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Database
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'skynet_rc1',
            'USER': 'skynet',
            'PASSWORD': 'skynet_password',
            'HOST': 'localhost',
            'PORT': '5432',
        }
    }

# Redis Cache
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'data' / 'uploads'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# AI Configuration
OLLAMA_URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')

# Vector settings
VECTOR_DIMENSIONS = int(os.environ.get('VECTOR_DIMENSIONS', '384'))

# File upload settings
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO' if not DEBUG else 'DEBUG',
            'propagate': False,
        },
    },
}

# LDAP Configuration - can be enabled/disabled via environment variable
LDAP_ENABLED = os.environ.get('LDAP_ENABLED', 'False').lower() == 'true'

if LDAP_ENABLED:
    try:
        import ldap
        from django_auth_ldap.config import LDAPSearch, GroupOfNamesType
        LDAP_AVAILABLE = True
    except ImportError:
        LDAP_AVAILABLE = False
        print("Warning: LDAP packages not installed. Falling back to local authentication.")
else:
    LDAP_AVAILABLE = False

# Authentication backends - LDAP optional
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Always include local authentication
]

if LDAP_ENABLED and LDAP_AVAILABLE:
    AUTHENTICATION_BACKENDS.insert(0, 'django_auth_ldap.backend.LDAPBackend')

# LDAP Configuration (only if LDAP is enabled and available)
if LDAP_ENABLED and LDAP_AVAILABLE:
    AUTH_LDAP_SERVER_URI = os.environ.get('LDAP_SERVER_URI', 'ldap://ldap.company.com:389')
    AUTH_LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN', 'cn=service,ou=users,dc=company,dc=com')
    AUTH_LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')

    # User search
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        os.environ.get('LDAP_USER_BASE', 'ou=users,dc=company,dc=com'),
        ldap.SCOPE_SUBTREE,
        os.environ.get('LDAP_USER_FILTER', '(sAMAccountName=%(user)s)')
    )

    # Group search
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
        os.environ.get('LDAP_GROUP_BASE', 'ou=groups,dc=company,dc=com'),
        ldap.SCOPE_SUBTREE,
        '(objectClass=groupOfNames)'
    )
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()

    # User attribute mapping
    AUTH_LDAP_USER_ATTR_MAP = {
        'first_name': 'givenName',
        'last_name': 'sn',
        'email': 'mail'
    }

    # Group to permission mapping
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        'is_staff': os.environ.get('LDAP_STAFF_GROUP', 'cn=skynet-staff,ou=groups,dc=company,dc=com'),
        'is_superuser': os.environ.get('LDAP_ADMIN_GROUP', 'cn=skynet-admin,ou=groups,dc=company,dc=com'),
    }

    # Cache groups for 1 hour
    AUTH_LDAP_CACHE_GROUPS = True
    AUTH_LDAP_GROUP_CACHE_TIMEOUT = 3600

# JWT Configuration (conditional based on availability)
if JWT_AVAILABLE:
    from datetime import timedelta
    
    REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': [
            'rest_framework_simplejwt.authentication.JWTAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ],
        'DEFAULT_PERMISSION_CLASSES': [
            'rest_framework.permissions.IsAuthenticated',
        ],
    }

    SIMPLE_JWT = {
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
        'ROTATE_REFRESH_TOKENS': True,
        'BLACKLIST_AFTER_ROTATION': True,
        'ALGORITHM': 'HS256',
        'SIGNING_KEY': os.environ.get('JWT_SECRET_KEY', SECRET_KEY),
        'VERIFYING_KEY': None,
        'AUTH_HEADER_TYPES': ('Bearer',),
        'USER_ID_FIELD': 'id',
        'USER_ID_CLAIM': 'user_id',
        'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
        'TOKEN_TYPE_CLAIM': 'token_type',
    }

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'