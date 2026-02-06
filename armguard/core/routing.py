"""
WebSocket URL routing for Django Channels
Routes WebSocket connections to appropriate consumers
"""
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Real-time notifications
    path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
    
    # Live transaction feed
    path('ws/transactions/', consumers.TransactionConsumer.as_asgi()),
    
    # Inventory status updates
    path('ws/inventory/', consumers.InventoryConsumer.as_asgi()),
    
    # User presence tracking
    path('ws/presence/', consumers.PresenceConsumer.as_asgi()),
]
