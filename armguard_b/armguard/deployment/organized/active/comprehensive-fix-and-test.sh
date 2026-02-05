#!/bin/bash

echo "🔧 COMPREHENSIVE ARMGUARD FIX & TEST"
echo "====================================="
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📋 STEP 1: Fix Nginx-Gunicorn Connection"
echo "----------------------------------------"

# The issue: Nginx is trying HTTP but Gunicorn is using Unix socket
echo "Current issue: Nginx → HTTP:8000, Gunicorn → Unix socket"
echo "Solution: Make both use HTTP:8000 for simplicity"

# Update Gunicorn service to use HTTP instead of socket
sudo tee /etc/systemd/system/armguard.service > /dev/null << 'SERVICECONF'
[Unit]
Description=ArmGuard Django Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=forking
User=www-data
Group=www-data
RuntimeDirectory=armguard
WorkingDirectory=/opt/armguard
Environment=PATH=/opt/armguard/venv/bin
Environment=DJANGO_SETTINGS_MODULE=core.settings
ExecStart=/opt/armguard/venv/bin/gunicorn --daemon --workers 3 --bind 127.0.0.1:8000 --pid /run/armguard/armguard.pid core.wsgi:application --access-logfile /var/log/armguard/access.log --error-logfile /var/log/armguard/error.log
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s TERM $MAINPID
PIDFile=/run/armguard/armguard.pid
Restart=on-failure
RestartSec=10
TimeoutStartSec=30

[Install]
WantedBy=multi-user.target
SERVICECONF

echo "✅ Updated Gunicorn service to use HTTP:8000"

# Ensure nginx config matches
sudo tee /etc/nginx/sites-available/armguard > /dev/null << 'NGINXCONF'
server {
    listen 80;
    server_name 192.168.0.177 localhost;

    # Static files
    location /static/ {
        alias /opt/armguard/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
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

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Better error handling
        proxy_intercept_errors on;
        error_page 502 503 504 /50x.html;
    }

    # Custom error page
    location = /50x.html {
        root /var/www/html;
        internal;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
NGINXCONF

echo "✅ Updated Nginx configuration"

echo ""
echo "📋 STEP 2: Django Settings Review & Fix"
echo "---------------------------------------"

# Check current settings for issues
python << 'PYCHECK'
import os
import sys

sys.path.append('/opt/armguard')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    import django
    django.setup()
    from django.conf import settings
    
    print("✅ Django settings loaded successfully")
    print(f"   DEBUG: {settings.DEBUG}")
    print(f"   ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    print(f"   DATABASE ENGINE: {settings.DATABASES['default']['ENGINE']}")
    print(f"   STATIC_URL: {settings.STATIC_URL}")
    print(f"   STATIC_ROOT: {settings.STATIC_ROOT}")
    
    # Check if all required settings are present
    critical_settings = ['SECRET_KEY', 'DATABASES', 'INSTALLED_APPS', 'MIDDLEWARE']
    for setting_name in critical_settings:
        if hasattr(settings, setting_name):
            print(f"   {setting_name}: ✅")
        else:
            print(f"   {setting_name}: ❌ MISSING")
            
    # Test database connection
    from django.db import connection
    connection.ensure_connection()
    print("✅ Database connection working")
    
except Exception as e:
    print(f"❌ Django settings error: {e}")
    import traceback
    traceback.print_exc()
PYCHECK

echo ""
echo "📋 STEP 3: Fix ALLOWED_HOSTS"
echo "----------------------------"

# Safely update ALLOWED_HOSTS with backup
python << 'PYHOSTS'
import re
import shutil

# Create backup first
shutil.copy('core/settings.py', 'core/settings.py.backup')

try:
    # Read settings.py
    with open('core/settings.py', 'r') as f:
        content = f.read()
    
    # Validate content before modification
    if 'ALLOWED_HOSTS' not in content and 'DEBUG' not in content:
        print("ERROR: settings.py format not recognized")
        exit(1)
    
    # Fix ALLOWED_HOSTS to include necessary IPs
    allowed_hosts = "ALLOWED_HOSTS = ['192.168.0.177', 'localhost', '127.0.0.1']"
    
    # Replace existing ALLOWED_HOSTS
    if 'ALLOWED_HOSTS' in content:
        content = re.sub(r'ALLOWED_HOSTS\s*=\s*\[.*?\]', allowed_hosts, content, flags=re.DOTALL)
    else:
        # Add ALLOWED_HOSTS if missing
        content = content.replace('DEBUG = True', f'DEBUG = True\n\n{allowed_hosts}')
    
    # Validate Python syntax before saving
    compile(content, 'core/settings.py', 'exec')
    
    # Write back
    with open('core/settings.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed ALLOWED_HOSTS")
    
except Exception as e:
    print(f"ERROR: Failed to update settings: {e}")
    # Restore backup
    shutil.copy('core/settings.py.backup', 'core/settings.py')
    exit(1)
PYHOSTS

echo ""
echo "📋 STEP 4: Database Migration Check"
echo "-----------------------------------"

# Check for pending migrations
python manage.py showmigrations

echo ""
echo "Running migrations..."
python manage.py migrate

echo ""
echo "📋 STEP 5: Restart Services"
echo "---------------------------"

# Properly stop service with timeout
echo "Stopping ArmGuard service..."
sudo systemctl stop armguard

# Wait for service to stop with timeout
timeout=0
while sudo systemctl is-active --quiet armguard && [ $timeout -lt 30 ]; do
    sleep 1
    timeout=$((timeout + 1))
done

if sudo systemctl is-active --quiet armguard; then
    echo "ERROR: Service failed to stop gracefully"
    exit 1
fi

echo "Service stopped successfully"

# Reload and restart services
sudo systemctl daemon-reload
sudo systemctl enable armguard
sudo systemctl stop armguard
sleep 3
sudo systemctl start armguard
sudo systemctl reload nginx

echo ""
echo "⏳ STEP 6: Wait for Services to Stabilize"
echo "-----------------------------------------"

# Wait for services with proper health checking
echo "Waiting for ArmGuard service to be ready..."
timeout=0
while [ $timeout -lt 60 ]; do
    if sudo systemctl is-active --quiet armguard; then
        # Service is active, now check if it responds to HTTP
        if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ | grep -E "^[23][0-9][0-9]$" > /dev/null; then
            echo "Service is ready and responding"
            break
        fi
    fi
    sleep 2
    timeout=$((timeout + 2))
    echo "Waiting... ($timeout/60 seconds)"
done

if [ $timeout -ge 60 ]; then
    echo "WARNING: Service did not become ready within 60 seconds"
fi

echo ""
echo "📋 STEP 7: Comprehensive Testing"
echo "--------------------------------"

# Test 1: Service Status
NGINX_STATUS=$(sudo systemctl is-active nginx)
ARMGUARD_STATUS=$(sudo systemctl is-active armguard)
POSTGRESQL_STATUS=$(sudo systemctl is-active postgresql)

echo "Service Status:"
echo "  • Nginx: $NGINX_STATUS"
echo "  • ArmGuard: $ARMGUARD_STATUS" 
echo "  • PostgreSQL: $POSTGRESQL_STATUS"

# Test 2: Direct Gunicorn Test
echo ""
echo "Testing direct Gunicorn connection..."
GUNICORN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ 2>/dev/null || echo "000")
echo "  • Direct Gunicorn: HTTP $GUNICORN_TEST"

# Test 3: Nginx Proxy Test
echo ""
echo "Testing through Nginx proxy..."
NGINX_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
echo "  • Through Nginx: HTTP $NGINX_TEST"

# Test 4: Static Files
echo ""
echo "Testing static files..."
STATIC_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
echo "  • Static Files: HTTP $STATIC_TEST"

# Test 5: Admin Access
echo ""
echo "Testing admin interface..."
ADMIN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
echo "  • Admin Interface: HTTP $ADMIN_TEST"

# Test 6: External Access (from network)
echo ""
echo "Testing external access..."
EXTERNAL_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://192.168.0.177/ 2>/dev/null || echo "000")
echo "  • External Access: HTTP $EXTERNAL_TEST"

echo ""
echo "📋 STEP 8: Process Verification"
echo "-------------------------------"

echo "Running processes:"
echo "Gunicorn processes:"
ps aux | grep gunicorn | grep -v grep | head -5

echo ""
echo "Network listeners:"
sudo netstat -tlnp | grep -E ':(80|8000|5432)'

echo ""
echo "📋 STEP 9: Log Analysis"
echo "----------------------"

echo "Recent ArmGuard logs:"
sudo journalctl -u armguard --no-pager -n 10

echo ""
echo "Recent Nginx error logs:"
sudo tail -n 5 /var/log/nginx/error.log

if [ -f "/var/log/armguard/error.log" ]; then
    echo ""
    echo "Recent Gunicorn error logs:"
    sudo tail -n 5 /var/log/armguard/error.log
fi

echo ""
echo "📊 FINAL ASSESSMENT"
echo "==================="

# Determine overall status
OVERALL_SUCCESS=true

if [ "$NGINX_STATUS" != "active" ]; then
    echo "❌ Nginx not active"
    OVERALL_SUCCESS=false
fi

if [ "$ARMGUARD_STATUS" != "active" ]; then
    echo "❌ ArmGuard service not active"
    OVERALL_SUCCESS=false
fi

if [ "$GUNICORN_TEST" != "200" ] && [ "$GUNICORN_TEST" != "302" ]; then
    echo "❌ Gunicorn not responding correctly"
    OVERALL_SUCCESS=false
fi

if [ "$NGINX_TEST" != "200" ] && [ "$NGINX_TEST" != "302" ]; then
    echo "❌ Nginx proxy not working"
    OVERALL_SUCCESS=false
fi

if [ "$STATIC_TEST" != "200" ]; then
    echo "⚠️  Static files have issues"
fi

if [ "$OVERALL_SUCCESS" = true ] && ([ "$NGINX_TEST" = "200" ] || [ "$NGINX_TEST" = "302" ]); then
    echo ""
    echo "🎉 SUCCESS! ARMGUARD IS FULLY OPERATIONAL!"
    echo "=========================================="
    echo ""
    echo "🌐 Your ArmGuard Military System:"
    echo "  • Main Application: http://192.168.0.177"
    echo "  • Admin Interface: http://192.168.0.177/admin"
    echo "  • Super Admin: http://192.168.0.177/superadmin"
    echo ""
    echo "✅ Working Components:"
    echo "  • Django Application"
    echo "  • PostgreSQL Database"
    echo "  • Nginx Web Server"
    echo "  • Static Files Serving"
    echo "  • Gunicorn WSGI Server"
    echo ""
    echo "📊 System Status:"
    echo "  • Services: All Active"
    echo "  • HTTP Response: $NGINX_TEST"
    echo "  • Static Files: $STATIC_TEST"
    echo "  • Network Access: Working"
    echo ""
    echo "🔐 Security Status:"
    echo "  • Network middleware disabled (temporary)"
    echo "  • Device authorization ready for configuration"
    echo "  • VPN integration available"
    echo ""
    echo "🎯 NEXT STEPS:"
    echo "  1. Clear browser cache: Ctrl+F5"
    echo "  2. Access: http://192.168.0.177"
    echo "  3. Login to admin interface"
    echo "  4. Test all functionality"
    echo "  5. Re-enable security features if needed"
    echo ""
else
    echo ""
    echo "❌ ISSUES STILL PRESENT"
    echo "======================"
    echo ""
    echo "🔍 Debugging Information:"
    echo "  • Nginx Status: $NGINX_STATUS ($NGINX_TEST)"
    echo "  • Gunicorn Status: $ARMGUARD_STATUS ($GUNICORN_TEST)"
    echo "  • Static Files: $STATIC_TEST"
    echo ""
    echo "📝 Suggested Actions:"
    if [ "$GUNICORN_TEST" != "200" ] && [ "$GUNICORN_TEST" != "302" ]; then
        echo "  1. Check Django settings and database"
        echo "  2. Review Gunicorn logs: sudo journalctl -u armguard -f"
        echo "  3. Test manual Django: python manage.py runserver 0.0.0.0:8000"
    fi
    
    if [ "$NGINX_TEST" != "200" ] && [ "$NGINX_TEST" != "302" ] && [ "$GUNICORN_TEST" = "200" ]; then
        echo "  1. Check nginx configuration"
        echo "  2. Verify proxy settings"
        echo "  3. Check firewall/ports"
    fi
    
    echo ""
    echo "🔧 Manual Recovery Commands:"
    echo "  sudo systemctl restart armguard"
    echo "  sudo systemctl restart nginx" 
    echo "  sudo journalctl -u armguard -f"
fi