"""
Production settings for ArmGuard
Inherits from base settings.py and overrides for production security
"""
from .settings import *
from decouple import config
import os

# CRITICAL: Never use DEBUG=True in production
DEBUG = False

# Set your domain/IP (comma-separated, no spaces)
ALLOWED_HOSTS = config('DJANGO_ALLOWED_HOSTS', cast=Csv())

# Security Headers - HTTPS/SSL
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CSRF Protection
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_SAMESITE = 'Strict'
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())

# Additional Security Headers
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Session Security
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=3600, cast=int)  # 1 hour default
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

# Enhanced Password Validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,  # Stronger minimum
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Database - PostgreSQL for production
if config('USE_POSTGRESQL', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
            'CONN_MAX_AGE': 600,  # Connection pooling
        }
    }
else:
    # Keep SQLite for local testing
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Static and Media Files (served by Nginx in production)
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('SECURITY_LOG_PATH', default=str(BASE_DIR / 'logs' / 'security.log')),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('ERROR_LOG_PATH', default=str(BASE_DIR / 'logs' / 'errors.log')),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'django_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('DJANGO_LOG_PATH', default=str(BASE_DIR / 'logs' / 'django.log')),
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'django_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'axes': {
            'handlers': ['security_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Email Configuration (for error notifications)
if config('EMAIL_BACKEND', default=''):
    EMAIL_BACKEND = config('EMAIL_BACKEND')
    EMAIL_HOST = config('EMAIL_HOST', default='localhost')
    EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
    DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@armguard.local')
    SERVER_EMAIL = config('SERVER_EMAIL', default='noreply@armguard.local')
    ADMINS = [(config('ADMIN_NAME', default='Admin'), config('ADMIN_EMAIL', default=''))]

# Cache Configuration (for rate limiting)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'armguard-cache',
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# Rate Limiting Configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_VIEW = 'core.views.ratelimit_error'  # Custom rate limit error page

# Django Axes Configuration (Brute-force Protection)
AXES_ENABLED = True
AXES_FAILURE_LIMIT = config('AXES_FAILURE_LIMIT', default=5, cast=int)  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = config('AXES_COOLOFF_TIME', default=1, cast=int)  # Hours
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]  # Lock by username AND IP
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = 'registration/account_locked.html'
AXES_LOCKOUT_URL = '/account-locked/'
AXES_ONLY_ADMIN_SITE = False  # Protect all login views
AXES_ENABLE_ACCESS_FAILURE_LOG = True
AXES_FAILURE_LOG_LEVEL = 'warning'

# Content Security Policy (basic - adjust for your needs)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Remove unsafe-inline in strict production
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)

# Admin Site Customization
ADMIN_SITE_HEADER = config('ADMIN_SITE_HEADER', default='ArmGuard Administration')
ADMIN_SITE_TITLE = config('ADMIN_SITE_TITLE', default='ArmGuard Admin')
ADMIN_INDEX_TITLE = config('ADMIN_INDEX_TITLE', default='ArmGuard Dashboard')
