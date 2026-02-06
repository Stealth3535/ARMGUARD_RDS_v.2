"""
ASGI config for core project with WebSocket support.

It exposes the ASGI callable as a module-level variable named ``application``.
Supports both HTTP and WebSocket connections for real-time features.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Initialize Django before importing routing
django.setup()

# Import after django.setup()
from core.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
