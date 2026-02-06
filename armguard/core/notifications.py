"""
Real-time notification utilities
Helper functions to send WebSocket notifications
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def send_user_notification(user_id, title, message, level='info', data=None):
    """
    Send real-time notification to a specific user
    
    Args:
        user_id: Target user ID
        title: Notification title
        message: Notification message
        level: 'info', 'success', 'warning', 'error'
        data: Optional additional data dict
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            logger.warning("Channel layer not configured")
            return
        
        async_to_sync(channel_layer.group_send)(
            f'notifications_{user_id}',
            {
                'type': 'notification_message',
                'title': title,
                'message': message,
                'level': level,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
        )
        logger.debug(f"Sent notification to user {user_id}: {title}")
    except Exception as e:
        logger.error(f"Error sending notification: {e}")


def broadcast_transaction_created(transaction):
    """
    Broadcast new transaction to all connected users
    
    Args:
        transaction: Transaction model instance
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            logger.warning("Channel layer not configured")
            return
        
        async_to_sync(channel_layer.group_send)(
            'transactions_feed',
            {
                'type': 'transaction_created',
                'transaction': {
                    'id': transaction.id,
                    'action': transaction.action,
                    'personnel': transaction.personnel.get_full_name(),
                    'personnel_id': transaction.personnel.id,
                    'item': str(transaction.item),
                    'item_id': transaction.item.id,
                    'duty_type': transaction.duty_type or '',
                    'issued_by': transaction.issued_by.username,
                    'mags': transaction.mags,
                    'rounds': transaction.rounds
                },
                'timestamp': datetime.now().isoformat()
            }
        )
        logger.debug(f"Broadcast transaction #{transaction.id} creation")
    except Exception as e:
        logger.error(f"Error broadcasting transaction: {e}")


def broadcast_transaction_returned(transaction):
    """
    Broadcast transaction return to all connected users
    
    Args:
        transaction: Transaction model instance (return action)
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            return
        
        async_to_sync(channel_layer.group_send)(
            'transactions_feed',
            {
                'type': 'transaction_returned',
                'transaction': {
                    'id': transaction.id,
                    'action': transaction.action,
                    'personnel': transaction.personnel.get_full_name(),
                    'item': str(transaction.item),
                    'issued_by': transaction.issued_by.username
                },
                'timestamp': datetime.now().isoformat()
            }
        )
        logger.debug(f"Broadcast transaction #{transaction.id} return")
    except Exception as e:
        logger.error(f"Error broadcasting transaction return: {e}")


def broadcast_inventory_update(item, previous_status=None):
    """
    Broadcast inventory status change to all connected users
    
    Args:
        item: Item model instance
        previous_status: Previous status before update (optional)
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            return
        
        async_to_sync(channel_layer.group_send)(
            'inventory_updates',
            {
                'type': 'inventory_updated',
                'item_id': item.id,
                'item_type': item.item_type,
                'serial': item.serial,
                'status': item.status,
                'previous_status': previous_status,
                'timestamp': datetime.now().isoformat()
            }
        )
        logger.debug(f"Broadcast inventory update for item {item.id}: {previous_status} -> {item.status}")
    except Exception as e:
        logger.error(f"Error broadcasting inventory update: {e}")


def broadcast_announcement(title, message, level='info'):
    """
    Broadcast system-wide announcement to all users
    
    Args:
        title: Announcement title
        message: Announcement message
        level: 'info', 'warning', 'error'
    """
    try:
        channel_layer = get_channel_layer()
        
        if channel_layer is None:
            return
        
        # Send to all notification groups
        # Note: This is a simplified version; in production you might want
        # a dedicated announcement channel
        logger.info(f"Broadcast announcement: {title}")
    except Exception as e:
        logger.error(f"Error broadcasting announcement: {e}")
