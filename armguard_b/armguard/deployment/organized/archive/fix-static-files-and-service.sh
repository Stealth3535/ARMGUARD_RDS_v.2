#!/bin/bash

echo "🚨 Emergency Fix: Static Files & Service Recovery"
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📝 Step 1: Fix Django static files settings..."

# Fix the static files settings in Django
python << 'PYFIX'
import os

# Read settings.py
with open('core/settings.py', 'r') as f:
    content = f.read()

# Static files configuration block
static_config = '''
# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = '/opt/armguard/staticfiles'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'core', 'static'),
]
'''

# Check if STATIC_URL is already configured
if 'STATIC_URL' not in content:
    # Add static configuration before the end of the file
    content = content.rstrip() + '\n' + static_config + '\n'
elif 'STATIC_ROOT' not in content:
    # Replace existing static URL config with complete config
    import re
    # Find and replace the STATIC_URL line
    content = re.sub(r"STATIC_URL\s*=\s*['\"][^'\"]*['\"]", 
                    static_config.strip(), content)

# Write back
with open('core/settings.py', 'w') as f:
    f.write(content)

print("✅ Fixed Django static files settings")
PYFIX

echo ""
echo "📁 Step 2: Create proper static files directory structure..."

# Create the staticfiles directory if it doesn't exist
sudo mkdir -p /opt/armguard/staticfiles
sudo chown -R www-data:www-data /opt/armguard/staticfiles

# Set DJANGO_SETTINGS_MODULE properly
export DJANGO_SETTINGS_MODULE=core.settings

echo ""
echo "📦 Step 3: Collect static files with proper configuration..."

# Collect static files again with the correct settings
python manage.py collectstatic --noinput --clear --verbosity=2

echo ""
echo "🔧 Step 4: Fix nginx static files path..."

# Update nginx to use the correct static files path
sudo tee /etc/nginx/sites-available/armguard > /dev/null << 'NGINXCONF'
server {
    listen 80;
    server_name 192.168.0.177 localhost;

    # Static files - Point to Django's collected static files
    location /static/ {
        alias /opt/armguard/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # Handle missing files gracefully
        try_files $uri $uri/ =404;
    }

    # Media files
    location /media/ {
        alias /opt/armguard/core/media/;
        expires 7d;
    }

    # Favicon
    location /favicon.ico {
        alias /opt/armguard/staticfiles/admin/img/favicon.ico;
        expires 30d;
    }

    # Main application - Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Handle connection failures
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Custom error pages
    error_page 404 /static/404.html;
    error_page 500 502 503 504 /static/50x.html;
}
NGINXCONF

echo "✅ Updated nginx configuration"

echo ""
echo "🔄 Step 5: Check and restart ArmGuard service..."

# Check if service is running
SERVICE_STATUS=$(sudo systemctl is-active armguard)
echo "Current ArmGuard service status: $SERVICE_STATUS"

# Stop and start the service properly
sudo systemctl stop armguard
sleep 3

# Check if the service file exists and is valid
if [ -f "/etc/systemd/system/armguard.service" ]; then
    echo "✅ Service file exists"
    echo "Service file contents:"
    sudo cat /etc/systemd/system/armguard.service
else
    echo "❌ Service file missing - recreating..."
    
    # Create the service file
    sudo tee /etc/systemd/system/armguard.service > /dev/null << 'SERVICECONF'
[Unit]
Description=ArmGuard Military Inventory System
After=network.target postgresql.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/opt/armguard
Environment=DJANGO_SETTINGS_MODULE=core.settings
ExecStart=/opt/armguard/venv/bin/gunicorn --daemon --workers 3 --bind 127.0.0.1:8000 --pid /run/armguard/armguard.pid core.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile=/run/armguard/armguard.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICECONF

    # Create PID directory
    sudo mkdir -p /run/armguard
    sudo chown www-data:www-data /run/armguard
    
    echo "✅ Created service file"
fi

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable armguard
sudo systemctl start armguard

echo ""
echo "🔄 Step 6: Restart nginx..."
sudo systemctl reload nginx

echo ""
echo "⏳ Step 7: Wait for services to start..."
sleep 15

echo ""
echo "🧪 Step 8: Test services..."

# Check service statuses
NGINX_STATUS=$(sudo systemctl is-active nginx)
ARMGUARD_STATUS=$(sudo systemctl is-active armguard)
echo "Nginx status: $NGINX_STATUS"
echo "ArmGuard status: $ARMGUARD_STATUS"

# Test static files
STATIC_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
echo "Static files test: HTTP $STATIC_TEST"

# Test main application
MAIN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
echo "Main application test: HTTP $MAIN_TEST"

# List static files to verify they exist
echo ""
echo "📁 Static files structure:"
ls -la /opt/armguard/staticfiles/ | head -10

if [ -d "/opt/armguard/staticfiles/admin" ]; then
    echo "Admin static files:"
    ls -la /opt/armguard/staticfiles/admin/css/ | head -5
fi

echo ""
echo "🎉 FINAL RESULTS:"
echo "================"

if [ "$MAIN_TEST" = "200" ] || [ "$MAIN_TEST" = "302" ]; then
    echo "✅ SUCCESS! ArmGuard is working!"
    echo ""
    echo "🌐 Your ArmGuard System:"
    echo "  • Main: http://192.168.0.177"
    echo "  • Admin: http://192.168.0.177/admin"
    echo "  • Super Admin: http://192.168.0.177/superadmin"
    echo ""
    echo "📊 Service Status:"
    echo "  • Nginx: $NGINX_STATUS"
    echo "  • ArmGuard: $ARMGUARD_STATUS"
    echo "  • Main App: HTTP $MAIN_TEST"
    echo "  • Static Files: HTTP $STATIC_TEST"
    
    if [ "$STATIC_TEST" = "200" ]; then
        echo ""
        echo "🎨 Styling Status: ✅ FIXED!"
        echo "  • CSS files serving correctly"
        echo "  • Admin interface styled properly"
        echo "  • Static files path configured"
        echo ""
        echo "🔄 Clear your browser cache and refresh!"
    else
        echo ""
        echo "⚠️  Static files still need attention but main app works"
    fi
    
else
    echo "❌ Still having issues:"
    echo "  • Main App: HTTP $MAIN_TEST" 
    echo "  • Static Files: HTTP $STATIC_TEST"
    echo ""
    echo "📋 Recent logs:"
    echo "ArmGuard service:"
    sudo journalctl -u armguard --no-pager -n 5
    echo ""
    echo "Nginx errors:"
    sudo tail -n 5 /var/log/nginx/error.log
    
    echo ""
    echo "🔍 Manual debugging:"
    echo "Check if gunicorn is running:"
    ps aux | grep gunicorn
    echo ""
    echo "Test direct gunicorn access:"
    echo "curl http://127.0.0.1:8000"
fi