# Real-Time Features Implementation Guide
**Date:** February 6, 2026  
**Implementation Time:** 2-3 weeks  
**Complexity:** Medium  
**Status:** Ready to implement

---

## 🎯 **Overview**

This guide implements real-time features for ArmGuard using Django Channels, enabling:
- ✅ Live transaction notifications
- ✅ Real-time inventory status updates
- ✅ Active user presence indicators
- ✅ Live notification feed
- ✅ Auto-save draft forms
- ✅ Broadcast system announcements

---

## 📋 **Prerequisites**

**Current System:**
- ✅ Django 5.1.1 installed
- ✅ Redis 5.0.1 installed and running
- ✅ Gunicorn WSGI server configured
- ⚠️ Django Channels NOT installed (we'll add it)

**What You Need:**
- Redis server running (already configured)
- Basic understanding of WebSockets
- 2-3 hours for initial setup
- 1-2 weeks for full feature implementation

---

## 🚀 **Step-by-Step Implementation**

### **PHASE 1: Core Setup (2-3 hours)**

#### **Step 1.1: Install Dependencies**

Add to `requirements.txt`:
```bash
# Real-time features
channels==4.0.0
channels-redis==4.1.0
daphne==4.0.0
```

Install:
```bash
cd C:\Users\9533RDS\Desktop\Armguard\armguard
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0
```

#### **Step 1.2: Update Django Settings**

Add to `core/settings.py` INSTALLED_APPS:
```python
INSTALLED_APPS = [
    'daphne',  # Must be first for Channels
    'django.contrib.admin',
    'django.contrib.auth',
    # ... rest of your apps
    'channels',  # Add after your apps
]
```

Add Channel Layer configuration (before DATABASES):
```python
# ============================================================================
# Django Channels Configuration (Real-time WebSocket Support)
# ============================================================================

ASGI_APPLICATION = 'core.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(
                config('REDIS_HOST', default='127.0.0.1'),
                config('REDIS_PORT', default=6379, cast=int)
            )],
            "capacity": 1500,  # Max messages in channel
            "expiry": 60,      # Message expiry time (seconds)
        },
    },
}
```

#### **Step 1.3: Create ASGI Configuration**

Replace `core/asgi.py`:
```python
"""
ASGI config for core project with WebSocket support.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
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
```

#### **Step 1.4: Create WebSocket Routing**

Create `core/routing.py`:
```python
"""
WebSocket URL routing for Django Channels
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
    
    # User presence
    path('ws/presence/', consumers.PresenceConsumer.as_asgi()),
]
```

#### **Step 1.5: Create WebSocket Consumers**

Create `core/consumers.py`:
```python
"""
WebSocket consumers for real-time features
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
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        # Reject anonymous users
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Create user-specific channel group
        self.group_name = f'notifications_{self.user.id}'
        
        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notification stream'
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            # Respond to ping to keep connection alive
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': data.get('timestamp')
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
        """Handle WebSocket connection"""
        self.user = self.scope['user']
        
        if isinstance(self.user, AnonymousUser):
            await self.close()
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
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
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
```

---

### **PHASE 2: Backend Integration (1 week)**

#### **Step 2.1: Create Notification Utility**

Create `core/notifications.py`:
```python
"""
Real-time notification utilities
"""
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from datetime import datetime


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
    channel_layer = get_channel_layer()
    
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


def broadcast_transaction_created(transaction):
    """
    Broadcast new transaction to all connected users
    """
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        'transactions_feed',
        {
            'type': 'transaction_created',
            'transaction': {
                'id': transaction.id,
                'action': transaction.action,
                'personnel': transaction.personnel.get_full_name(),
                'item': str(transaction.item),
                'duty_type': transaction.duty_type,
                'issued_by': transaction.issued_by.username
            },
            'timestamp': datetime.now().isoformat()
        }
    )


def broadcast_inventory_update(item, previous_status=None):
    """
    Broadcast inventory status change
    """
    channel_layer = get_channel_layer()
    
    async_to_sync(channel_layer.group_send)(
        'inventory_updates',
        {
            'type': 'inventory_updated',
            'item_id': item.id,
            'status': item.status,
            'previous_status': previous_status,
            'timestamp': datetime.now().isoformat()
        }
    )
```

#### **Step 2.2: Update Transaction Views**

Modify `transactions/views.py` to send notifications:

```python
# Add at top
from core.notifications import (
    send_user_notification, 
    broadcast_transaction_created
)

# In create_qr_transaction function, after transaction is created:
def create_qr_transaction(request):
    # ... existing code ...
    
    if request.method == 'POST':
        # ... existing validation ...
        
        try:
            personnel = Personnel.objects.get(id=personnel_id)
            item = Item.objects.get(id=item_id)
            
            # Create transaction
            transaction = Transaction.objects.create(
                personnel=personnel,
                item=item,
                action=action,
                mags=mags,
                rounds=rounds,
                duty_type=duty_type,
                notes=notes,
                date_time=timezone.now(),
                issued_by=request.user
            )
            
            logger.info("Transaction #%d created by %s", transaction.id, request.user.username)
            
            # NEW: Send real-time notifications
            broadcast_transaction_created(transaction)
            
            # Notify the user who created the transaction
            send_user_notification(
                request.user.id,
                'Transaction Created',
                f'Successfully {action.lower()}ed {item.item_type} - {item.serial}',
                level='success',
                data={'transaction_id': transaction.id}
            )
            
            messages.success(request, f'✓ Transaction #{transaction.id} created')
            return redirect('transactions:qr_scanner')
            
        except Exception as e:
            logger.error("Error creating transaction: %s", str(e))
            messages.error(request, 'An error occurred')
        
        return redirect('transactions:qr_scanner')
```

#### **Step 2.3: Update Inventory Views**

Modify `inventory/views.py`:

```python
# Add at top
from core.notifications import broadcast_inventory_update

# In item edit view, track status changes:
def edit_item(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    previous_status = item.status  # Track original status
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            updated_item = form.save()
            
            # NEW: Broadcast if status changed
            if updated_item.status != previous_status:
                broadcast_inventory_update(updated_item, previous_status)
            
            messages.success(request, 'Item updated successfully')
            return redirect('inventory:item_detail', item_id=item.id)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'inventory/edit_item.html', {'form': form})
```

---

### **PHASE 3: Frontend Integration (1 week)**

#### **Step 3.1: Create WebSocket Manager**

Create `core/static/js/websocket-manager.js`:
```javascript
/**
 * WebSocket Manager for ArmGuard Real-time Features
 */

class WebSocketManager {
    constructor() {
        this.connections = {};
        this.reconnectAttempts = {};
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }

    /**
     * Connect to a WebSocket endpoint
     */
    connect(name, path, handlers = {}) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const url = `${protocol}//${host}${path}`;

        console.log(`[WebSocket] Connecting to ${name}: ${url}`);

        const socket = new WebSocket(url);

        socket.onopen = (event) => {
            console.log(`[WebSocket] ${name} connected`);
            this.reconnectAttempts[name] = 0;
            
            if (handlers.onOpen) {
                handlers.onOpen(event);
            }

            // Start heartbeat
            this.startHeartbeat(name, socket);
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(`[WebSocket] ${name} received:`, data);

            if (data.type === 'pong') {
                // Heartbeat response
                return;
            }

            if (handlers.onMessage) {
                handlers.onMessage(data);
            }
        };

        socket.onclose = (event) => {
            console.log(`[WebSocket] ${name} disconnected`);
            
            if (handlers.onClose) {
                handlers.onClose(event);
            }

            // Stop heartbeat
            this.stopHeartbeat(name);

            // Attempt reconnection
            this.attemptReconnect(name, path, handlers);
        };

        socket.onerror = (error) => {
            console.error(`[WebSocket] ${name} error:`, error);
            
            if (handlers.onError) {
                handlers.onError(error);
            }
        };

        this.connections[name] = socket;
        return socket;
    }

    /**
     * Disconnect from WebSocket
     */
    disconnect(name) {
        if (this.connections[name]) {
            this.stopHeartbeat(name);
            this.connections[name].close();
            delete this.connections[name];
        }
    }

    /**
     * Send message to WebSocket
     */
    send(name, data) {
        if (this.connections[name] && this.connections[name].readyState === WebSocket.OPEN) {
            this.connections[name].send(JSON.stringify(data));
        } else {
            console.warn(`[WebSocket] Cannot send to ${name}: not connected`);
        }
    }

    /**
     * Start heartbeat to keep connection alive
     */
    startHeartbeat(name, socket) {
        this.stopHeartbeat(name);
        
        this.connections[`${name}_heartbeat`] = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                }));
            }
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat(name) {
        if (this.connections[`${name}_heartbeat`]) {
            clearInterval(this.connections[`${name}_heartbeat`]);
            delete this.connections[`${name}_heartbeat`];
        }
    }

    /**
     * Attempt to reconnect
     */
    attemptReconnect(name, path, handlers) {
        if (!this.reconnectAttempts[name]) {
            this.reconnectAttempts[name] = 0;
        }

        if (this.reconnectAttempts[name] < this.maxReconnectAttempts) {
            this.reconnectAttempts[name]++;
            console.log(`[WebSocket] Reconnecting ${name} (attempt ${this.reconnectAttempts[name]}/${this.maxReconnectAttempts})`);

            setTimeout(() => {
                this.connect(name, path, handlers);
            }, this.reconnectDelay * this.reconnectAttempts[name]);
        } else {
            console.error(`[WebSocket] Max reconnection attempts reached for ${name}`);
        }
    }
}

// Global WebSocket manager instance
const wsManager = new WebSocketManager();
```

#### **Step 3.2: Create Notification System**

Create `core/static/js/notifications.js`:
```javascript
/**
 * Real-time Notification System
 */

class NotificationSystem {
    constructor() {
        this.container = null;
        this.init();
    }

    init() {
        // Create notification container
        this.container = document.createElement('div');
        this.container.id = 'notification-container';
        this.container.style.cssText = `
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
        `;
        document.body.appendChild(this.container);

        // Connect to notification WebSocket
        wsManager.connect('notifications', '/ws/notifications/', {
            onMessage: (data) => this.handleNotification(data)
        });
    }

    handleNotification(data) {
        if (data.type === 'notification') {
            this.show(data.title, data.message, data.level);
        }
    }

    show(title, message, level = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${level}`;
        notification.style.cssText = `
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 16px;
            margin-bottom: 12px;
            border-left: 4px solid ${this.getLevelColor(level)};
            animation: slideIn 0.3s ease-out;
            cursor: pointer;
        `;

        notification.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <strong style="display: block; margin-bottom: 4px; color: #2c3e50;">
                        ${this.getIcon(level)} ${title}
                    </strong>
                    <div style="color: #7f8c8d; font-size: 14px;">
                        ${message}
                    </div>
                </div>
                <button style="background: none; border: none; font-size: 20px; color: #95a5a6; cursor: pointer; padding: 0; margin-left: 12px;">
                    ×
                </button>
            </div>
        `;

        // Close button
        notification.querySelector('button').addEventListener('click', (e) => {
            e.stopPropagation();
            this.remove(notification);
        });

        // Click to dismiss
        notification.addEventListener('click', () => {
            this.remove(notification);
        });

        this.container.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                this.remove(notification);
            }
        }, 5000);
    }

    remove(notification) {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    getLevelColor(level) {
        const colors = {
            'info': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'error': '#c0392b'
        };
        return colors[level] || colors.info;
    }

    getIcon(level) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        };
        return icons[level] || icons.info;
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.notificationSystem = new NotificationSystem();
});
```

#### **Step 3.3: Create Live Transaction Feed**

Create `core/static/js/live-feed.js`:
```javascript
/**
 * Live Transaction Feed
 */

class LiveTransactionFeed {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.init();
    }

    init() {
        // Connect to transaction WebSocket
        wsManager.connect('transactions', '/ws/transactions/', {
            onMessage: (data) => this.handleTransaction(data)
        });
    }

    handleTransaction(data) {
        if (data.type === 'transaction_created') {
            this.addTransaction(data.transaction, 'created');
        } else if (data.type === 'transaction_returned') {
            this.addTransaction(data.transaction, 'returned');
        }
    }

    addTransaction(transaction, type) {
        const item = document.createElement('div');
        item.className = 'live-feed-item';
        item.style.cssText = `
            padding: 12px;
            border-left: 4px solid ${type === 'created' ? '#f39c12' : '#27ae60'};
            background: #f8f9fa;
            margin-bottom: 8px;
            border-radius: 4px;
            animation: fadeIn 0.5s ease-out;
        `;

        const icon = type === 'created' ? '📤' : '📥';
        const action = type === 'created' ? 'took' : 'returned';

        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${icon} ${transaction.personnel}</strong> ${action} 
                    <span style="color: #3498db;">${transaction.item}</span>
                </div>
                <div style="font-size: 12px; color: #95a5a6;">
                    Just now
                </div>
            </div>
            ${transaction.duty_type ? `<div style="font-size: 13px; color: #7f8c8d; margin-top: 4px;">Duty: ${transaction.duty_type}</div>` : ''}
        `;

        // Add to top of container
        this.container.insertBefore(item, this.container.firstChild);

        // Limit to 10 most recent
        while (this.container.children.length > 10) {
            this.container.removeChild(this.container.lastChild);
        }
    }
}

// Add fadeIn animation
const fadeStyle = document.createElement('style');
fadeStyle.textContent = `
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(fadeStyle);
```

#### **Step 3.4: Update Base Template**

Add to `core/templates/base.html` before closing `</body>`:
```html
<!-- Real-time Features -->
<script src="{% static 'js/websocket-manager.js' %}"></script>
<script src="{% static 'js/notifications.js' %}"></script>

{% block realtime_scripts %}
<!-- Page-specific real-time scripts -->
{% endblock %}
```

---

### **PHASE 4: Testing & Deployment (2-3 days)**

#### **Step 4.1: Test WebSocket Connection**

Create test page `core/templates/test_realtime.html`:
```html
{% extends "base.html" %}

{% block title %}Real-time Features Test{% endblock %}

{% block content %}
<div style="max-width: 800px; margin: 40px auto; padding: 20px;">
    <h1>Real-time Features Test Page</h1>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 30px;">
        <!-- Connection Status -->
        <div style="padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2>Connection Status</h2>
            <div id="connection-status">
                <p>Connecting...</p>
            </div>
        </div>
        
        <!-- Test Controls -->
        <div style="padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h2>Test Controls</h2>
            <button onclick="testNotification('info')" style="display: block; width: 100%; margin-bottom: 10px; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Test Info Notification
            </button>
            <button onclick="testNotification('success')" style="display: block; width: 100%; margin-bottom: 10px; padding: 10px; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Test Success Notification
            </button>
            <button onclick="testNotification('warning')" style="display: block; width: 100%; margin-bottom: 10px; padding: 10px; background: #f39c12; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Test Warning Notification
            </button>
            <button onclick="testNotification('error')" style="display: block; width: 100%; padding: 10px; background: #c0392b; color: white; border: none; border-radius: 4px; cursor: pointer;">
                Test Error Notification
            </button>
        </div>
    </div>
    
    <!-- Live Feed -->
    <div style="margin-top: 30px; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h2>Live Transaction Feed</h2>
        <div id="live-feed" style="min-height: 200px;">
            <p style="color: #95a5a6;">Waiting for transactions...</p>
        </div>
    </div>
</div>

<script>
function testNotification(level) {
    const titles = {
        'info': 'Information',
        'success': 'Success!',
        'warning': 'Warning',
        'error': 'Error Occurred'
    };
    
    const messages = {
        'info': 'This is an informational message',
        'success': 'Operation completed successfully',
        'warning': 'Please review this action',
        'error': 'Something went wrong'
    };
    
    window.notificationSystem.show(titles[level], messages[level], level);
}

// Initialize live feed
const liveFeed = new LiveTransactionFeed('live-feed');

// Update connection status
document.addEventListener('DOMContentLoaded', () => {
    const statusDiv = document.getElementById('connection-status');
    
    setTimeout(() => {
        const connections = Object.keys(wsManager.connections);
        if (connections.length > 0) {
            statusDiv.innerHTML = `
                <p style="color: #27ae60;"><strong>✅ Connected</strong></p>
                <ul style="margin-top: 10px; list-style: none; padding: 0;">
                    ${connections.filter(c => !c.includes('_heartbeat')).map(c => `
                        <li style="padding: 5px 0; color: #7f8c8d;">
                            <span style="color: #27ae60;">●</span> ${c}
                        </li>
                    `).join('')}
                </ul>
            `;
        } else {
            statusDiv.innerHTML = '<p style="color: #c0392b;"><strong>❌ Not Connected</strong></p>';
        }
    }, 1000);
});
</script>
{% endblock %}
```

#### **Step 4.2: Update Deployment Configuration**

For **production deployment with Daphne** (replaces Gunicorn for WebSocket support):

Create `deployment/run-daphne.sh`:
```bash
#!/bin/bash

# Activate virtual environment
source /path/to/venv/bin/activate

# Run Daphne ASGI server
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

Update Nginx configuration to proxy WebSocket:
```nginx
upstream armguard_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your_domain.com;

    # WebSocket upgrade support
    location /ws/ {
        proxy_pass http://armguard_app;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket timeout
        proxy_read_timeout 86400;
    }

    # Regular HTTP
    location / {
        proxy_pass http://armguard_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files
    location /static/ {
        alias /path/to/staticfiles/;
    }

    location /media/ {
        alias /path/to/media/;
    }
}
```

#### **Step 4.3: Test Checklist**

```
✅ Redis is running (redis-cli ping should return PONG)
✅ Django Channels installed (pip list | grep channels)
✅ ASGI application configured (core/asgi.py updated)
✅ WebSocket endpoints working (visit test page)
✅ Notifications appearing when triggered
✅ Transaction feed updates in real-time
✅ Reconnection works after disconnect
✅ Multiple users can connect simultaneously
✅ Performance acceptable (check Redis memory usage)
```

---

## 📊 **Expected Impact**

**Before Real-time:**
- Users manually refresh pages
- No immediate feedback on actions
- Delayed awareness of system changes
- No collaborative features

**After Real-time:**
- Instant notifications on all actions
- Live transaction feed updates
- Real-time inventory status changes
- Active user presence indicators
- Better operational coordination

**Performance:**
- WebSocket overhead: ~5-10MB RAM per 100 connections
- Network traffic: ~1-2KB per update
- User experience: Immediate (< 100ms latency)

---

## 🛡️ **Security Considerations**

✅ **Authentication Required:** All WebSocket connections check authentication  
✅ **AllowedHostsOriginValidator:** Prevents cross-origin WebSocket attacks  
✅ **AuthMiddlewareStack:** Django user authentication on WebSocket  
✅ **User-specific channels:** Each user only receives their own notifications  
✅ **Rate limiting:** Redis handles message capacity limits  
✅ **Secure WebSocket (wss://):** Use with SSL/TLS in production

---

## 🚀 **Quick Start Commands**

```bash
# Install dependencies
pip install channels==4.0.0 channels-redis==4.1.0 daphne==4.0.0

# Verify Redis is running
redis-cli ping
# Should return: PONG

# Test with development server (includes Channels support)
python manage.py runserver

# Or run with Daphne for production
daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

---

## 📝 **Next Steps**

1. ✅ **Phase 1:** Setup (2-3 hours) - Install and configure Channels
2. ✅ **Phase 2:** Backend integration (1 week) - Add notifications to views
3. ✅ **Phase 3:** Frontend integration (1 week) - Create UI components
4. ✅ **Phase 4:** Testing & deployment (2-3 days) - Verify everything works

**Total Time:** 2-3 weeks for full implementation  
**Complexity:** Medium (requires async programming knowledge)  
**Result:** Modern real-time web application with live updates

---

**Ready to start? Begin with Phase 1 and work through each step. The system is designed to work incrementally - you can test each phase before moving to the next!**
