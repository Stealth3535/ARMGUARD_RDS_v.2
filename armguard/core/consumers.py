"""
WebSocket consumers for real-time features
Handles WebSocket connections and broadcasts messages
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Real-time notification consumer
    Sends notifications to connected users
    """
    
    async def connect(self):
        """Handle WebSocket connection with improved error handling"""
        try:
            self.user = self.scope['user']
            
            # Reject anonymous users
            if isinstance(self.user, AnonymousUser):
                await self.close(code=4001)  # Unauthorized
                return
            
            # Create user-specific channel group
            self.group_name = f'notifications_{self.user.id}'
            
            # Join group with error handling
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to notification stream',
                'user_id': self.user.id
            }))
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"WebSocket connection error: {e}")
            await self.close(code=4000)  # Server error
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection with proper cleanup"""
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Notification WebSocket disconnect error: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages with improved error handling"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to ping to keep connection alive
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
                
        except json.JSONDecodeError as e:
            # Invalid JSON - send error response
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"WebSocket receive error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def notification_message(self, event):
        """
        Handler for notification messages from channel layer
        Called when notification is sent to this user's group
        """
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message'],
            'level': event.get('level', 'info'),
            'timestamp': event.get('timestamp'),
            'data': event.get('data', {})
        }))


class TransactionConsumer(AsyncWebsocketConsumer):
    """
    Live transaction feed consumer
    Broadcasts new transactions to all connected users
    """
    
    async def connect(self):
        """Handle WebSocket connection with improved error handling"""
        try:
            self.user = self.scope['user']
            
            if isinstance(self.user, AnonymousUser):
                await self.close(code=4001)  # Unauthorized
                return
            
            # All authenticated users join the global transaction feed
            self.group_name = 'transactions_feed'
            
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            await self.accept()
            
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to live transaction feed'
            }))
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Transaction WebSocket connection error: {e}")
            await self.close(code=4000)  # Server error
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection with proper cleanup"""
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
                
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Transaction WebSocket disconnect error: {e}")
    
    async def transaction_created(self, event):
        """
        Handler for new transaction events
        """
        await self.send(text_data=json.dumps({
            'type': 'transaction_created',
            'transaction': event['transaction'],
            'timestamp': event['timestamp']
        }))
    
    async def transaction_returned(self, event):
        """
        Handler for transaction return events
        """
        await self.send(text_data=json.dumps({
            'type': 'transaction_returned',
            'transaction': event['transaction'],
            'timestamp': event['timestamp']
        }))


class InventoryConsumer(AsyncWebsocketConsumer):
    """
    Real-time inventory status updates
    Notifies when item status changes
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        self.group_name = 'inventory_updates'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def inventory_updated(self, event):
        """
        Handler for inventory updates
        """
        await self.send(text_data=json.dumps({
            'type': 'inventory_updated',
            'item_id': event['item_id'],
            'status': event['status'],
            'previous_status': event.get('previous_status'),
            'timestamp': event['timestamp']
        }))


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    User presence tracking
    Shows who's online and active
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        self.group_name = 'user_presence'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Notify others that this user came online
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_online',
                'user_id': self.user.id,
                'username': self.user.username
            }
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            # Notify others that this user went offline
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_offline',
                    'user_id': self.user.id,
                    'username': self.user.username
                }
            )
            
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def user_online(self, event):
        """Handler for user coming online"""
        await self.send(text_data=json.dumps({
            'type': 'user_online',
            'user_id': event['user_id'],
            'username': event['username']
        }))
    
    async def user_offline(self, event):
        """Handler for user going offline"""
        await self.send(text_data=json.dumps({
            'type': 'user_offline',
            'user_id': event['user_id'],
            'username': event['username']
        }))
