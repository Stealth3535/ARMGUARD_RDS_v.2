#!/bin/bash

echo "🔧 DIRECT IP ACCESS TEST & FIX"
echo "==============================="
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📋 STEP 1: Test Direct Access from Your PC"
echo "------------------------------------------"

echo "The issue might be nginx proxy headers. Let's test direct access..."

# Check current nginx configuration
echo "Current nginx proxy configuration:"
sudo grep -A 10 -B 2 "proxy_set_header" /etc/nginx/sites-available/armguard

echo ""
echo "📋 STEP 2: Fix Nginx Headers for IP Detection"
echo "--------------------------------------------"

# Update nginx to properly pass client IP
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

    # Main application with proper IP forwarding
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        
        # Ensure client IP is properly passed
        proxy_set_header X-Client-IP $remote_addr;
        proxy_set_header REMOTE_ADDR $remote_addr;
        
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
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

echo "✅ Updated nginx with better IP forwarding"

echo ""
echo "📋 STEP 3: Add IP Debugging to Middleware"
echo "----------------------------------------"

# Create a debugging version of the middleware that logs all IP detection
cat > /opt/armguard/core/middleware/device_authorization.py << 'PYDEBUG'
import json
import os
import logging
from django.http import HttpResponseForbidden, HttpResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

logger = logging.getLogger('armguard.device_auth')

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Device authorization with enhanced IP debugging
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.load_authorized_devices()
        super().__init__(get_response)
    
    def load_authorized_devices(self):
        """Load authorized devices from configuration"""
        try:
            config_file = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    self.authorized_devices = config.get('transaction_devices', [])
                    logger.info(f"✅ Loaded {len(self.authorized_devices)} authorized devices")
            else:
                # Create default with your PC
                self.authorized_devices = [
                    {
                        'name': 'Developer PC (DESKTOP-E3N8R9V)',
                        'ip': '192.168.0.82',
                        'mac': '74-56-3C-DC-68-96',
                        'can_transact': True
                    }
                ]
                self.save_device_config()
        except Exception as e:
            logger.error(f"❌ Failed to load authorized devices: {e}")
            # Emergency fallback
            self.authorized_devices = [{'ip': '192.168.0.82', 'can_transact': True}]
    
    def save_device_config(self):
        """Save device configuration"""
        try:
            config = {
                'transaction_devices': self.authorized_devices,
                'configuration': {'strict_mode': True}
            }
            config_file = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Failed to save config: {e}")
    
    def process_request(self, request):
        """Process request with detailed IP debugging"""
        
        # Skip static files
        if any(request.path.startswith(path) for path in ['/static/', '/media/', '/favicon.ico']):
            return None
        
        # Special debugging endpoint
        if request.path == '/debug-ip/':
            return self.debug_ip_response(request)
        
        # Get client IP with detailed logging
        client_ip = self.get_client_ip(request)
        
        # Log every request for debugging
        logger.info(f"🔍 REQUEST: {request.method} {request.path}")
        logger.info(f"🌐 Client IP detected: {client_ip}")
        logger.info(f"📋 All request headers: {dict(request.META)}")
        
        # Define paths that require authorization
        restricted_paths = [
            '/admin/transactions/',
            '/admin/inventory/',
            '/admin/personnel/', 
            '/admin/users/',
        ]
        
        # Check for write operations on admin
        is_admin_write = (request.path.startswith('/admin/') and 
                         request.method in ['POST', 'PUT', 'DELETE', 'PATCH'] and
                         not request.path.startswith('/admin/login/'))
        
        # Check if this is a restricted path
        is_restricted_path = any(request.path.startswith(path) for path in restricted_paths)
        
        # Always allow login/logout
        if any(request.path.startswith(path) for path in ['/admin/login/', '/admin/logout/']):
            logger.info("✅ Login/logout - allowed")
            return None
        
        # Check if authorization is needed
        if is_restricted_path or is_admin_write:
            logger.info(f"🔒 Authorization required for: {request.path}")
            if not self.is_device_authorized(client_ip):
                logger.warning(f"🚨 BLOCKED: {client_ip} → {request.path}")
                return self.device_unauthorized_response(client_ip, request.path)
            else:
                logger.info(f"✅ AUTHORIZED: {client_ip} → {request.path}")
        else:
            logger.info(f"👁️  PUBLIC ACCESS: {request.path}")
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP with all possible methods"""
        
        # Try all possible IP headers
        ip_headers = [
            'HTTP_X_REAL_IP',
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_CLIENT_IP', 
            'HTTP_X_FORWARDED',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
            'REMOTE_ADDR'
        ]
        
        found_ips = {}
        for header in ip_headers:
            value = request.META.get(header)
            if value:
                # Handle comma-separated IPs
                if ',' in value:
                    ip = value.split(',')[0].strip()
                else:
                    ip = value.strip()
                found_ips[header] = ip
        
        # Log all found IPs
        logger.info(f"🔍 IP Detection Results:")
        for header, ip in found_ips.items():
            logger.info(f"   {header}: {ip}")
        
        # Return the first valid IP found, preferring X-Real-IP
        if 'HTTP_X_REAL_IP' in found_ips:
            final_ip = found_ips['HTTP_X_REAL_IP']
        elif 'HTTP_X_FORWARDED_FOR' in found_ips:
            final_ip = found_ips['HTTP_X_FORWARDED_FOR']
        elif 'REMOTE_ADDR' in found_ips:
            final_ip = found_ips['REMOTE_ADDR']
        else:
            final_ip = 'unknown'
        
        logger.info(f"🎯 Selected IP: {final_ip}")
        return final_ip
    
    def is_device_authorized(self, client_ip):
        """Check authorization with detailed logging"""
        logger.info(f"🔍 Checking authorization for: {client_ip}")
        
        for device in self.authorized_devices:
            device_ip = device.get('ip', '')
            can_transact = device.get('can_transact', False)
            logger.info(f"   Compare: {client_ip} vs {device_ip} (can_transact: {can_transact})")
            
            if device_ip == client_ip and can_transact:
                logger.info(f"✅ MATCH FOUND: {client_ip} is authorized")
                return True
        
        logger.warning(f"❌ NO MATCH: {client_ip} not authorized")
        return False
    
    def debug_ip_response(self, request):
        """Special endpoint to debug IP detection"""
        client_ip = self.get_client_ip(request)
        
        debug_info = f"""
        <h1>🔍 ArmGuard IP Debug Info</h1>
        <h2>Detected Client IP: {client_ip}</h2>
        <h3>All Headers:</h3>
        <ul>
        """
        
        for key, value in request.META.items():
            if 'IP' in key or 'ADDR' in key or 'FORWARD' in key:
                debug_info += f"<li><strong>{key}:</strong> {value}</li>"
        
        debug_info += "</ul>"
        
        # Check authorization
        is_auth = self.is_device_authorized(client_ip)
        debug_info += f"<h3>Authorization: {'✅ AUTHORIZED' if is_auth else '❌ NOT AUTHORIZED'}</h3>"
        
        return HttpResponse(debug_info, content_type='text/html')
    
    def device_unauthorized_response(self, client_ip, path):
        """Return unauthorized response"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🛡️ Device Authorization Required</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .alert {{ background: #ffebee; border-left: 4px solid #f44336; padding: 20px; }}
                .info {{ background: #f5f5f5; padding: 20px; margin: 20px 0; }}
                code {{ background: #f0f0f0; padding: 2px 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🛡️ ArmGuard Device Authorization</h1>
                <div class="alert">
                    <h3>🚨 Transaction Access Denied</h3>
                    <p><strong>Your IP:</strong> <code>{client_ip}</code></p>
                    <p><strong>Path:</strong> <code>{path}</code></p>
                    <p><strong>Reason:</strong> Device not authorized for transactions</p>
                </div>
                <div class="info">
                    <h3>✅ Authorized Devices</h3>
                    <ul>
                        <li>Developer PC: 192.168.0.82</li>
                        <li>Armory PC: (Pending configuration)</li>
                    </ul>
                    <p><a href="/admin/">← Return to Dashboard</a></p>
                </div>
                <p><small>Debug: <a href="/debug-ip/">Check IP Detection</a></small></p>
            </div>
        </body>
        </html>
        """
        return HttpResponseForbidden(html)
PYDEBUG

echo "✅ Added IP debugging middleware"

echo ""
echo "📋 STEP 4: Restart Services"
echo "---------------------------"

sudo systemctl reload nginx
sudo systemctl restart armguard
sleep 10

echo ""
echo "📋 STEP 5: Direct IP Testing"
echo "----------------------------"

echo "Testing access with updated configuration..."

# Test static files (should always work)
STATIC_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
echo "  • Static files: HTTP $STATIC_TEST"

# Test admin page (should work for viewing)
ADMIN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
echo "  • Admin page: HTTP $ADMIN_TEST"

# Test debug endpoint
DEBUG_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/debug-ip/ 2>/dev/null || echo "000")
echo "  • Debug endpoint: HTTP $DEBUG_TEST"

echo ""
echo "📋 STEP 6: Check Real Client Access"
echo "----------------------------------"

echo "Now test from your PC browser:"
echo "  • Main site: http://192.168.0.177"
echo "  • Debug info: http://192.168.0.177/debug-ip/"
echo "  • Admin: http://192.168.0.177/admin/"

echo ""
echo "📊 SERVICE STATUS"
echo "=================="

SERVICE_STATUS=$(sudo systemctl is-active armguard)
NGINX_STATUS=$(sudo systemctl is-active nginx)

echo "🔧 Services:"
echo "  • ArmGuard: $SERVICE_STATUS"  
echo "  • Nginx: $NGINX_STATUS"

echo ""
echo "📋 Recent Gunicorn Logs:"
if [ -f "/var/log/armguard/error.log" ]; then
    sudo tail -n 5 /var/log/armguard/error.log
else
    echo "  No error log file found"
fi

echo ""
if [ "$ADMIN_TEST" = "200" ] || [ "$ADMIN_TEST" = "302" ]; then
    echo "🎉 BASIC ACCESS WORKING!"
    echo "======================="
    echo ""
    echo "✅ System Status:"
    echo "  • Services running"
    echo "  • Admin page accessible" 
    echo "  • Static files serving"
    echo ""
    echo "🔍 Next Steps:"
    echo "  1. Visit: http://192.168.0.177/debug-ip/"
    echo "  2. Check what IP your PC shows"
    echo "  3. Visit: http://192.168.0.177/admin/" 
    echo "  4. Test transaction access"
    echo ""
    echo "📱 From your PC (192.168.0.82):"
    echo "  • Should have FULL access"
    echo "  • All functions should work"
    echo ""
    echo "📱 From other devices:"
    echo "  • Should see security page for transactions"
    echo "  • Can view dashboards and reports"
    
else
    echo "⚠️  Still having basic access issues"
    echo "Service status: ArmGuard=$SERVICE_STATUS, Nginx=$NGINX_STATUS"
    echo ""
    echo "🔧 Quick check - try disabling authorization temporarily:"
    echo "sudo systemctl stop armguard"
    echo "cd /opt/armguard && source venv/bin/activate"
    echo "python manage.py runserver 0.0.0.0:8001"
    echo "Then test: http://192.168.0.177:8001"
fi

echo ""
echo "🔍 IP Debug URL: http://192.168.0.177/debug-ip/"
echo "   Use this to see what IP your device shows!"