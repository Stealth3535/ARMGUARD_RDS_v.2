# Real-time Features Deployment Guide

## Overview
This guide covers deploying ArmGuard with real-time WebSocket support using Django Channels and Daphne.

## Architecture Changes

### Before (HTTP Only)
```
Client → Nginx → Gunicorn → Django
```

### After (HTTP + WebSocket)
```
Client → Nginx → Daphne → Django Channels → Redis
                    ↓
                  Django
```

## Prerequisites

1. **Redis Server** - Required for Django Channels channel layer
2. **Daphne** - ASGI server (replaces Gunicorn for WebSocket support)
3. **Updated Python packages** - See requirements.txt

## Installation Steps

### 1. Install Redis

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis

# Verify Redis is running
redis-cli ping
# Should respond: PONG
```

### 2. Update Python Packages

```bash
# Activate virtual environment
cd /opt/armguard
source venv/bin/activate

# Install new packages
cd armguard
pip install -r requirements.txt

# Verify installations
python -c "import channels; print(channels.__version__)"
python -c "import daphne; print(daphne.__version__)"
```

### 3. Run Django Migrations

```bash
# No new migrations required, but good practice
python manage.py migrate
```

### 4. Collect Static Files

```bash
# Collect static files including new JavaScript/CSS
python manage.py collectstatic --noinput
```

### 5. Update Nginx Configuration

```bash
# Backup existing config
sudo cp /etc/nginx/sites-available/armguard /etc/nginx/sites-available/armguard.backup

# Copy new WebSocket-enabled config
sudo cp deployment/nginx-websocket.conf /etc/nginx/sites-available/armguard

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### 6. Start Daphne Server

```bash
# Stop Gunicorn if running
sudo systemctl stop gunicorn

# Run Daphne
chmod +x deployment/run-daphne.sh
./deployment/run-daphne.sh

# Or create systemd service (see below)
```

## Systemd Service for Daphne

Create `/etc/systemd/system/daphne.service`:

```ini
[Unit]
Description=Daphne ASGI Server for ArmGuard
After=network.target redis.service
Requires=redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/armguard/armguard
Environment="PATH=/opt/armguard/venv/bin"
ExecStart=/opt/armguard/venv/bin/daphne \
    --bind 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --proxy-headers \
    --verbosity 2 \
    --access-log /opt/armguard/logs/daphne.log \
    core.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable daphne
sudo systemctl start daphne
sudo systemctl status daphne
```

## Configuration Files Updated

1. **requirements.txt** - Added channels, channels-redis, daphne
2. **core/settings.py** - Added INSTALLED_APPS and CHANNEL_LAYERS config
3. **core/asgi.py** - Replaced with ProtocolTypeRouter for WebSocket support
4. **core/routing.py** - NEW: WebSocket URL routing
5. **core/consumers.py** - NEW: WebSocket consumers
6. **core/notifications.py** - NEW: Notification helper functions

## Testing Real-time Features

### 1. Access Test Page

Navigate to: `https://your-domain.com/test-realtime/`

This page provides:
- Connection status for all WebSocket channels
- Test buttons for each channel type
- Live transaction feed
- Event logging

### 2. Manual Testing

#### Test Notifications
```bash
# In Django shell
python manage.py shell

from core.notifications import send_user_notification
send_user_notification(1, "Test", "This is a test notification", "info")
```

#### Test Transaction Broadcast
```bash
# Create a transaction through the UI
# All connected users should see it in real-time
```

#### Test Inventory Updates
```bash
# Change item status through the UI
# Connected users should see the update
```

### 3. WebSocket Endpoints

- `ws://your-domain.com/ws/notifications/` - User-specific notifications
- `ws://your-domain.com/ws/transactions/` - Transaction feed
- `ws://your-domain.com/ws/inventory/` - Inventory updates
- `ws://your-domain.com/ws/presence/` - User presence tracking

## Monitoring

### Check Daphne Status
```bash
sudo systemctl status daphne
tail -f /opt/armguard/logs/daphne.log
```

### Check Redis Status
```bash
sudo systemctl status redis
redis-cli INFO
redis-cli MONITOR  # Watch commands in real-time
```

### Check Nginx Logs
```bash
tail -f /var/log/nginx/armguard_access.log
tail -f /var/log/nginx/armguard_error.log
```

### Check WebSocket Connections
```bash
# Show active connections
netstat -an | grep :8000
ss -tn | grep :8000
```

## Troubleshooting

### WebSocket Connection Fails

1. **Check Redis is running**
   ```bash
   redis-cli ping
   ```

2. **Check Daphne is running**
   ```bash
   ps aux | grep daphne
   ```

3. **Check Nginx WebSocket config**
   ```bash
   sudo nginx -t
   grep -A 10 "location /ws/" /etc/nginx/sites-available/armguard
   ```

4. **Check firewall rules**
   ```bash
   sudo ufw status
   # Port 8000 should be allowed from localhost
   ```

### Notifications Not Appearing

1. **Check browser console** (F12) for WebSocket errors
2. **Verify user is authenticated**
3. **Check notification channel connection** in test page
4. **Verify Redis channel layer** in Django settings

### High Memory Usage

1. **Reduce Daphne workers**
   ```bash
   # In daphne.service, change --workers 4 to --workers 2
   ```

2. **Configure Redis memory limit**
   ```bash
   # In /etc/redis/redis.conf
   maxmemory 256mb
   maxmemory-policy allkeys-lru
   ```

### Slow WebSocket Performance

1. **Check Redis latency**
   ```bash
   redis-cli --latency
   redis-cli --latency-history
   ```

2. **Increase Nginx timeouts** (already set to 86400s for WebSockets)

3. **Monitor Daphne workers**
   ```bash
   htop  # Look for daphne processes
   ```

## Security Considerations

1. **WebSocket Origin Validation** - Already configured in asgi.py
2. **Authentication Required** - All consumers reject anonymous users
3. **SSL/TLS Required** - Nginx forces HTTPS
4. **Redis Security** - Bind to localhost only
5. **Rate Limiting** - Consider adding per-user message limits

## Performance Tuning

### Redis Configuration
```ini
# /etc/redis/redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
tcp-keepalive 60
timeout 300
```

### Daphne Scaling
```bash
# For high traffic, run multiple Daphne instances
# Use supervisor or systemd to manage multiple workers
```

### Nginx Tuning
```nginx
# Increase worker connections
worker_connections 4096;

# Enable caching for static files (already configured)
```

## Rollback Procedure

If you need to roll back to HTTP-only:

1. **Stop Daphne**
   ```bash
   sudo systemctl stop daphne
   ```

2. **Start Gunicorn**
   ```bash
   sudo systemctl start gunicorn
   ```

3. **Restore Nginx config**
   ```bash
   sudo cp /etc/nginx/sites-available/armguard.backup /etc/nginx/sites-available/armguard
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Comment out real-time features** in base.html

## Maintenance

### Daily Tasks
- Monitor logs for errors
- Check Redis memory usage
- Verify WebSocket connections

### Weekly Tasks
- Review Daphne performance metrics
- Check for package updates
- Test real-time features

### Monthly Tasks
- Analyze Redis memory patterns
- Review and optimize channel layer settings
- Update documentation if needed

## Support

For issues or questions:
1. Check logs: `/opt/armguard/logs/daphne.log`
2. Review Django logs: `python manage.py check --deploy`
3. Test page: `/test-realtime/`
4. Redis monitor: `redis-cli MONITOR`

## References

- Django Channels: https://channels.readthedocs.io/
- Daphne Server: https://github.com/django/daphne
- Redis Channel Layer: https://github.com/django/channels_redis
