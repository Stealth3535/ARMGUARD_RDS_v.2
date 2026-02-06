# Real-time Features - Quick Reference

## 📡 WebSocket Endpoints

| Endpoint | Purpose | Authentication |
|----------|---------|----------------|
| `/ws/notifications/` | User-specific notifications | Required |
| `/ws/transactions/` | Global transaction feed | Required |
| `/ws/inventory/` | Inventory status updates | Required |
| `/ws/presence/` | User online/offline tracking | Required |

## 🔔 Notification System

### JavaScript Usage

```javascript
// Show notification
notifications.info('Title', 'Message');
notifications.success('Title', 'Message');
notifications.warning('Title', 'Message');
notifications.error('Title', 'Message');

// Custom duration (milliseconds)
notifications.info('Title', 'Message', 10000);  // 10 seconds

// No auto-dismiss
notifications.info('Title', 'Message', 0);

// Clear all notifications
notifications.clearAll();
```

### Python Usage

```python
from core.notifications import send_user_notification

# Send to specific user
send_user_notification(
    user_id=1,
    title='Transaction Created',
    message='Weapon issued successfully',
    level='success',  # 'info', 'success', 'warning', 'error'
    data={'transaction_id': 123}  # Optional additional data
)
```

## 📊 Transaction Broadcasting

### Python Usage

```python
from core.notifications import broadcast_transaction_created, broadcast_transaction_returned

# Broadcast new transaction (Take action)
transaction = Transaction.objects.create(...)
broadcast_transaction_created(transaction)

# Broadcast return transaction
broadcast_transaction_returned(transaction)
```

### Received Data Format

```javascript
{
    type: 'transaction_created',
    transaction: {
        id: 123,
        action: 'Take',
        personnel: 'John Doe',
        personnel_id: 'PE-123456',
        item: 'M4 Rifle - 123456',
        item_id: 'ITM-654321',
        duty_type: 'Guard Duty',
        issued_by: 'admin',
        mags: 3,
        rounds: 90
    },
    timestamp: '2026-02-05T10:30:00Z'
}
```

## 📦 Inventory Updates

### Python Usage

```python
from core.notifications import broadcast_inventory_update

# Update item status
old_status = item.status
item.status = 'Maintenance'
item.save()

# Broadcast the change
broadcast_inventory_update(item, previous_status=old_status)
```

### Received Data Format

```javascript
{
    type: 'inventory_updated',
    item_id: 'ITM-123456',
    item_type: 'M4 Rifle',
    serial: '123456',
    status: 'Maintenance',
    previous_status: 'Available',
    timestamp: '2026-02-05T10:30:00Z'
}
```

## 👥 User Presence

### Connection Events

```javascript
// User comes online
{
    type: 'user_online',
    user_id: 5,
    username: 'johndoe',
    status: 'online',
    timestamp: '2026-02-05T10:30:00Z'
}

// User goes offline
{
    type: 'user_offline',
    user_id: 5,
    username: 'johndoe',
    status: 'offline',
    timestamp: '2026-02-05T10:35:00Z'
}
```

## 🔧 WebSocket Manager

### JavaScript API

```javascript
// Connect to endpoint
wsManager.connect('notifications', {
    onMessage: (data) => {
        console.log('Received:', data);
    },
    onOpen: () => {
        console.log('Connected');
    },
    onClose: () => {
        console.log('Disconnected');
    },
    onError: (error) => {
        console.error('Error:', error);
    }
});

// Check connection status
if (wsManager.isConnected('notifications')) {
    console.log('Connected to notifications');
}

// Send message
wsManager.send('notifications', {
    type: 'ping'
});

// Disconnect
wsManager.disconnect('notifications');

// Disconnect all
wsManager.disconnectAll();
```

## 🎨 CSS Classes

### Notification Styling

```css
.notification                  /* Base notification */
.notification-info             /* Info level (blue) */
.notification-success          /* Success level (green) */
.notification-warning          /* Warning level (yellow) */
.notification-error            /* Error level (red) */
.notification.show             /* Visible state */
.notification.hide             /* Hidden state */
```

### Live Feed Styling

```css
.feed-item                     /* Feed item container */
.feed-item-new                 /* Newly added item animation */
.action-take                   /* Take transaction */
.action-return                 /* Return transaction */
.feed-icon                     /* Transaction icon */
.feed-content                  /* Transaction details */
.status-connected              /* Connected indicator */
.status-disconnected           /* Disconnected indicator */
```

## 🧪 Testing

### Test Page

Navigate to `/test-realtime/` for comprehensive testing interface.

**Features:**
- Connection status for all channels
- Manual connect/disconnect controls
- Test notification buttons (all levels)
- Live transaction feed
- Real-time event logging

### Browser Console Testing

```javascript
// Test notification
notifications.success('Test', 'Hello World');

// Check WebSocket status
console.log(wsManager.connections);

// Monitor WebSocket messages
wsManager.connect('transactions', {
    onMessage: (data) => console.log('TX:', data)
});

// Simulate notification
wsManager.send('notifications', {
    type: 'notification',
    title: 'Test',
    message: 'Test message',
    level: 'info'
});
```

### Python Shell Testing

```python
# Django shell
python manage.py shell

# Test notification
from core.notifications import send_user_notification
send_user_notification(1, 'Test', 'Hello from shell', 'info')

# Test transaction broadcast
from transactions.models import Transaction
from core.notifications import broadcast_transaction_created
tx = Transaction.objects.first()
broadcast_transaction_created(tx)

# Test inventory broadcast
from inventory.models import Item
from core.notifications import broadcast_inventory_update
item = Item.objects.first()
broadcast_inventory_update(item, previous_status='Available')
```

## 🚀 Production Deployment

### 1. Install Redis

```bash
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis
redis-cli ping  # Should return PONG
```

### 2. Install Python Packages

```bash
pip install -r requirements.txt
```

### 3. Update Nginx

```bash
# Copy WebSocket config
sudo cp deployment/nginx-websocket.conf /etc/nginx/sites-available/armguard
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Start Daphne

```bash
# Using script
./deployment/run-daphne.sh

# Or using systemd (recommended)
sudo systemctl start daphne
sudo systemctl enable daphne
```

### 5. Verify

```bash
# Check Daphne
sudo systemctl status daphne

# Check Redis
redis-cli ping

# Check WebSocket
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: $(openssl rand -base64 16)" \
  http://localhost:8000/ws/notifications/
```

## 📊 Monitoring

### Check Connections

```bash
# Active WebSocket connections
ss -tn | grep :8000

# Daphne processes
ps aux | grep daphne

# Redis connections
redis-cli INFO clients
```

### View Logs

```bash
# Daphne logs
tail -f /opt/armguard/logs/daphne.log

# Nginx logs
tail -f /var/log/nginx/armguard_access.log

# Redis logs
tail -f /var/log/redis/redis-server.log
```

### Redis Monitoring

```bash
# Monitor all Redis commands
redis-cli MONITOR

# Check memory usage
redis-cli INFO memory

# List active channels
redis-cli PUBSUB CHANNELS
```

## 🔒 Security

### WebSocket Authentication

All WebSocket endpoints require authentication:

```python
# In consumer's connect method
if self.scope["user"].is_anonymous:
    await self.close()
    return
```

### Origin Validation

```python
# In asgi.py
from channels.security.websocket import AllowedHostsOriginValidator

application = ProtocolTypeRouter({
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns))
    ),
})
```

### SSL/TLS

For production, use secure WebSocket (wss://):

```javascript
// Automatically uses wss:// if page is https://
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
```

## 🐛 Troubleshooting

### WebSocket Won't Connect

1. Check Redis is running: `redis-cli ping`
2. Check Daphne is running: `systemctl status daphne`
3. Check browser console for errors
4. Verify Nginx WebSocket config
5. Check firewall rules

### Notifications Not Appearing

1. Check user is authenticated
2. Verify WebSocket connection in test page
3. Check browser console for JavaScript errors
4. Verify notification HTML container exists
5. Check CSS is loaded

### High Memory Usage

1. Reduce Daphne workers (default: 4)
2. Configure Redis memory limit
3. Set shorter channel layer expiry
4. Monitor with `htop` or `top`

### Slow Performance

1. Check Redis latency: `redis-cli --latency`
2. Monitor Daphne processes: `htop`
3. Check network bandwidth
4. Consider Redis clustering for high load

## 📚 Additional Resources

- [Django Channels Documentation](https://channels.readthedocs.io/)
- [Daphne Server Documentation](https://github.com/django/daphne)
- [Redis Documentation](https://redis.io/documentation)
- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**Last Updated:** February 5, 2026  
**Version:** 1.0
