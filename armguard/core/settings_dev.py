# Quick Development Settings Override
# Place this at the END of settings.py or use: DJANGO_SETTINGS_MODULE=core.settings_dev

from .settings import *

# Disable problematic middleware for development
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Disable network access control in development
ENABLE_NETWORK_ACCESS_CONTROL = False

# Use simple cache backend
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Disable Redis in development
REDIS_ENABLED = False

print("=" * 70)
print("DEVELOPMENT SETTINGS LOADED")
print("Minimal middleware enabled for faster development")
print("Network controls disabled")
print("=" * 70)
