#!/bin/bash

################################################################################
# ArmGuard Nginx Configuration Fix
# Fixes nginx configuration to properly serve ArmGuard Django application
################################################################################

set -e

echo "🔧 Fixing nginx configuration for ArmGuard..."

PROJECT_DIR="/opt/armguard"
LAN_IP=$(hostname -I | cut -d' ' -f1)
NGINX_AVAILABLE="/etc/nginx/sites-available/armguard"
NGINX_ENABLED="/etc/nginx/sites-enabled/armguard"

# Check if ArmGuard service is running
echo "📊 Checking ArmGuard service status..."
if systemctl is-active --quiet armguard; then
    echo "✅ ArmGuard service is running"
else
    echo "❌ ArmGuard service is not running. Starting it..."
    
    # Make sure the service exists first
    if [ ! -f "/etc/systemd/system/armguard.service" ]; then
        echo "Creating ArmGuard service file..."
        cat > /etc/systemd/system/armguard.service << EOF
[Unit]
Description=ArmGuard Django Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=armguard
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind unix:/run/armguard/armguard.sock core.wsgi:application --access-logfile /var/log/armguard/access.log --error-logfile /var/log/armguard/error.log
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStopSec=5
KillMode=mixed
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
        systemctl daemon-reload
    fi
    
    # Create necessary directories
    mkdir -p /var/log/armguard
    chown www-data:www-data /var/log/armguard
    mkdir -p /run/armguard
    chown www-data:www-data /run/armguard
    
    # Start the service
    systemctl enable armguard
    systemctl start armguard
    sleep 3
    
    if systemctl is-active --quiet armguard; then
        echo "✅ ArmGuard service started successfully"
    else
        echo "❌ Failed to start ArmGuard service. Checking logs..."
        journalctl -u armguard --no-pager -l
    fi
fi

# Create proper nginx configuration for ArmGuard
echo "🌐 Creating nginx configuration..."
cat > $NGINX_AVAILABLE << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $LAN_IP localhost *.local;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static/ {
        alias /var/www/armguard/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Media files
    location /media/ {
        alias /var/www/armguard/media/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Django application
    location / {
        proxy_pass http://unix:/run/armguard/armguard.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Increase timeout
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

echo "✅ Nginx configuration created"

# Remove default nginx site and enable ArmGuard site
echo "🔄 Configuring nginx sites..."
rm -f /etc/nginx/sites-enabled/default
ln -sf $NGINX_AVAILABLE $NGINX_ENABLED

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration is valid"
    
    # Reload nginx
    systemctl reload nginx
    echo "✅ Nginx reloaded"
else
    echo "❌ Nginx configuration error"
    nginx -t
    exit 1
fi

# Check if socket file exists
echo "🔍 Checking Gunicorn socket..."
if [ -S "/run/armguard/armguard.sock" ]; then
    echo "✅ Gunicorn socket exists"
    ls -la /run/armguard/armguard.sock
else
    echo "❌ Gunicorn socket missing. Restarting ArmGuard service..."
    systemctl restart armguard
    sleep 5
    
    if [ -S "/run/armguard/armguard.sock" ]; then
        echo "✅ Gunicorn socket created after restart"
    else
        echo "❌ Socket still missing. Check service logs:"
        journalctl -u armguard --no-pager -n 20
    fi
fi

# Final status check
echo ""
echo "📊 Final status check..."
echo "ArmGuard service: $(systemctl is-active armguard)"
echo "Nginx service: $(systemctl is-active nginx)"
echo "Socket file: $([ -S /run/armguard/armguard.sock ] && echo "exists" || echo "missing")"

# Test web response
echo ""
echo "🌐 Testing web response..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
if [ "$response" = "200" ]; then
    echo "✅ Web server responding with HTTP $response"
else
    echo "❌ Web server issue - HTTP $response"
    
    if [ "$response" = "502" ]; then
        echo "502 Bad Gateway - ArmGuard service is likely not responding"
        echo "Check service status: systemctl status armguard"
    elif [ "$response" = "404" ]; then
        echo "404 Not Found - Nginx configuration issue"
    fi
fi

echo ""
echo "🎉 Configuration fix completed!"
echo ""
echo "Your ArmGuard application should now be accessible at:"
echo "  http://$LAN_IP"
echo "  http://localhost (from the Pi)"
echo ""
echo "If you still see issues, check:"
echo "  sudo systemctl status armguard"
echo "  sudo journalctl -u armguard -f"
echo "  sudo nginx -t"