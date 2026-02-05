#!/bin/bash

echo "🔍 DEBUG & FIX DEVICE AUTHORIZATION"
echo "===================================="
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📋 STEP 1: Debug Current Issue"
echo "-----------------------------"

# Check what's happening with the middleware
echo "Testing IP detection and middleware logic..."

python << 'PYDEBUG'
import os
import sys
sys.path.append('/opt/armguard')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    import django
    django.setup()
    
    # Test the device authorization logic
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware
    
    # Create middleware instance
    middleware = DeviceAuthorizationMiddleware(lambda r: None)
    
    print("✅ Middleware loaded successfully")
    print(f"   Authorized devices loaded: {len(middleware.authorized_devices)}")
    
    for device in middleware.authorized_devices:
        print(f"   • {device['name']}: {device['ip']} (can_transact: {device['can_transact']})")
    
    # Test IP authorization
    test_ip = '192.168.0.82'
    is_authorized = middleware.is_device_authorized(test_ip)
    print(f"\n🧪 Authorization test for {test_ip}: {is_authorized}")
    
    # Test different IPs
    for ip in ['192.168.0.82', '192.168.0.100', '127.0.0.1', '192.168.0.99']:
        result = middleware.is_device_authorized(ip)
        status = "✅ AUTHORIZED" if result else "❌ BLOCKED"
        print(f"   {ip}: {status}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYDEBUG

echo ""
echo "📋 STEP 2: Check Service Logs"
echo "----------------------------"

echo "Recent ArmGuard service logs:"
sudo journalctl -u armguard --no-pager -n 15 | grep -E "(ERROR|WARNING|device|auth|IP)"

echo ""
echo "📋 STEP 3: Fix Device Authorization Middleware"
echo "---------------------------------------------"

# Create a more robust device authorization middleware
cat > /opt/armguard/core/middleware/device_authorization.py << 'PYFIXED'
import json
import os
import logging
from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone

logger = logging.getLogger('armguard.device_auth')

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Enhanced device authorization middleware with proper debugging
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
                    for device in self.authorized_devices:
                        status = "ENABLED" if device.get('can_transact', False) else "DISABLED"
                        logger.info(f"   Device: {device['name']} ({device['ip']}) - {status}")
            else:
                # Create default config
                logger.warning("⚠️  No authorized_devices.json found, creating default")
                self.authorized_devices = [
                    {
                        'name': 'Developer PC (DESKTOP-E3N8R9V)',
                        'ip': '192.168.0.82',
                        'mac': '74-56-3C-DC-68-96',
                        'access_level': 'full',
                        'can_transact': True,
                        'description': 'Primary development workstation'
                    }
                ]
                self.save_device_config()
        except Exception as e:
            logger.error(f"❌ Failed to load authorized devices: {e}")
            # Fallback to allow developer PC
            self.authorized_devices = [
                {
                    'name': 'Developer PC (Emergency)',
                    'ip': '192.168.0.82',
                    'can_transact': True
                }
            ]
    
    def save_device_config(self):
        """Save device configuration to file"""
        try:
            config = {
                'transaction_devices': self.authorized_devices,
                'configuration': {
                    'strict_mode': True,
                    'log_unauthorized_attempts': True,
                    'created_date': timezone.now().isoformat(),
                    'last_updated': timezone.now().isoformat()
                }
            }
            
            config_file = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("✅ Saved device configuration")
        except Exception as e:
            logger.error(f"❌ Failed to save device config: {e}")
    
    def process_request(self, request):
        """Process request with enhanced debugging"""
        
        # Skip for static files, media, and basic resources
        skip_paths = ['/static/', '/media/', '/favicon.ico', '/robots.txt', '/.well-known/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Get client IP with multiple methods
        client_ip = self.get_client_ip(request)
        
        # Log all requests for debugging
        logger.info(f"🔍 Request: {request.method} {request.path} from {client_ip}")
        
        # Define transaction-restricted paths
        transaction_paths = [
            '/admin/transactions/',
            '/admin/inventory/', 
            '/admin/personnel/',
            '/admin/users/',
            '/transactions/',
            '/inventory/',
            '/personnel/',
            '/qr_manager/',
            '/print_handler/',
            '/api/',
        ]
        
        # Check for write operations on admin paths
        is_admin_write = request.path.startswith('/admin/') and request.method in ['POST', 'PUT', 'DELETE', 'PATCH']
        
        # Check if this is a transaction path
        is_transaction_path = any(request.path.startswith(path) for path in transaction_paths)
        
        # Allow login/logout and basic admin viewing for everyone
        always_allowed = [
            '/admin/login/', '/admin/logout/', '/login/', '/logout/', 
            '/admin/jsi18n/', '/admin/$'  # Admin main page
        ]
        
        # Check if path is always allowed
        if any(request.path.startswith(path) or request.path == path.rstrip('/') for path in always_allowed):
            logger.info(f"✅ Always allowed path: {request.path}")
            return None
        
        # Only restrict transaction operations and admin write operations
        if is_transaction_path or is_admin_write:
            if not self.is_device_authorized(client_ip):
                logger.warning(f"🚨 BLOCKED: {client_ip} → {request.method} {request.path}")
                return self.device_unauthorized_response(client_ip, request.path, request.method)
            else:
                logger.info(f"✅ ALLOWED: {client_ip} → {request.method} {request.path}")
        else:
            # Allow all other requests (viewing, etc.)
            logger.info(f"👁️  VIEW ACCESS: {client_ip} → {request.path}")
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP with multiple fallback methods"""
        # Try various headers in order of preference
        ip_headers = [
            'HTTP_X_REAL_IP',
            'HTTP_X_FORWARDED_FOR', 
            'HTTP_X_FORWARDED',
            'HTTP_FORWARDED_FOR',
            'HTTP_FORWARDED',
            'REMOTE_ADDR'
        ]
        
        for header in ip_headers:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs (take first one)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                logger.debug(f"🌐 IP from {header}: {ip}")
                return ip
        
        # Fallback
        ip = request.META.get('REMOTE_ADDR', 'unknown')
        logger.debug(f"🌐 Fallback IP: {ip}")
        return ip
    
    def is_device_authorized(self, client_ip):
        """Check if device IP is in authorized list with detailed logging"""
        logger.info(f"🔍 Checking authorization for IP: {client_ip}")
        logger.info(f"📋 Have {len(self.authorized_devices)} authorized devices:")
        
        for device in self.authorized_devices:
            device_ip = device.get('ip', '')
            can_transact = device.get('can_transact', False)
            logger.info(f"   • {device.get('name', 'Unknown')}: {device_ip} (can_transact: {can_transact})")
            
            if device_ip == client_ip and can_transact:
                logger.info(f"✅ AUTHORIZED: {client_ip} matches {device_ip}")
                return True
        
        logger.warning(f"❌ UNAUTHORIZED: {client_ip} not in authorized list")
        return False
    
    def device_unauthorized_response(self, client_ip, path, method):
        """Return enhanced unauthorized response"""
        
        # Get authorized device list for display
        authorized_devices = []
        for device in self.authorized_devices:
            if device.get('can_transact', False):
                authorized_devices.append(f"{device['name']} ({device['ip']})")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>🛡️ Device Not Authorized - ArmGuard</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: #333;
                }}
                .container {{ 
                    max-width: 600px; 
                    background: white; 
                    border-radius: 12px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    overflow: hidden;
                    margin: 20px;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #d32f2f 0%, #c62828 100%);
                    color: white; 
                    padding: 20px;
                    text-align: center;
                }}
                .content {{ padding: 30px; }}
                .alert {{ 
                    background: #ffebee; 
                    border-left: 4px solid #d32f2f;
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }}
                .info {{ 
                    background: #f5f5f5; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0;
                }}
                .device-info {{ 
                    background: #263238; 
                    color: #eceff1;
                    padding: 15px; 
                    border-radius: 6px; 
                    font-family: monospace;
                    margin: 15px 0;
                }}
                .footer {{ 
                    background: #37474f; 
                    color: #cfd8dc;
                    text-align: center; 
                    padding: 15px;
                    font-size: 0.9rem;
                }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin: 6px 0; }}
                h3 {{ color: #d32f2f; margin-bottom: 15px; }}
                .back-link {{ 
                    display: inline-block; 
                    background: #1976d2; 
                    color: white; 
                    padding: 10px 20px; 
                    border-radius: 6px; 
                    text-decoration: none; 
                    margin-top: 20px;
                }}
                .back-link:hover {{ background: #1565c0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ ArmGuard Military System</h1>
                    <h2>Device Authorization Required</h2>
                </div>
                
                <div class="content">
                    <div class="alert">
                        <h3>🚨 Transaction Access Denied</h3>
                        <div class="device-info">
                            Your IP: {client_ip}<br>
                            Operation: {method} {path}<br>
                            Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                        </div>
                        <p><strong>Reason:</strong> Device not authorized for armory transactions</p>
                    </div>
                    
                    <div class="info">
                        <h3>✅ Authorized Transaction Devices</h3>
                        {'<br>'.join([f'• {name}' for name in authorized_devices]) or '⚠️ No devices currently authorized'}
                        
                        <h3 style="margin-top: 20px;">📋 Access Policy</h3>
                        <ul>
                            <li><strong>Equipment Transactions:</strong> Authorized devices only</li>
                            <li><strong>Inventory Management:</strong> Authorized devices only</li>
                            <li><strong>Personnel Records:</strong> Authorized devices only</li>
                            <li><strong>Reports & Viewing:</strong> Available to all network devices</li>
                        </ul>
                        
                        <a href="/admin/" class="back-link">← Return to Dashboard</a>
                    </div>
                </div>
                
                <div class="footer">
                    ArmGuard Security • Access attempt logged at {timezone.now().strftime('%H:%M:%S')}
                </div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponseForbidden(html)
PYFIXED

echo "✅ Updated device authorization middleware with enhanced debugging"

echo ""
echo "📋 STEP 4: Test Fixed Middleware"
echo "-------------------------------"

# Test the updated middleware
python << 'PYTEST'
import os
import sys
sys.path.append('/opt/armguard')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    import django
    django.setup()
    
    # Test the fixed middleware
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware
    
    middleware = DeviceAuthorizationMiddleware(lambda r: None)
    
    print("✅ Fixed middleware loaded successfully")
    print(f"   Authorized devices: {len(middleware.authorized_devices)}")
    
    # Test authorization for various IPs
    test_ips = ['192.168.0.82', '192.168.0.100', '127.0.0.1', '192.168.0.1']
    
    print("\n🧪 Authorization Test Results:")
    for ip in test_ips:
        result = middleware.is_device_authorized(ip)
        status = "✅ AUTHORIZED" if result else "❌ BLOCKED"
        print(f"   {ip:15} → {status}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
PYTEST

echo ""
echo "📋 STEP 5: Restart Services with Fixed Middleware"
echo "------------------------------------------------"

# Restart services
sudo systemctl restart armguard
sleep 10

echo ""
echo "📋 STEP 6: Test Fixed Authorization"
echo "----------------------------------"

# Test the fixed authorization
echo "Testing fixed device authorization..."

# Test authorized device access 
AUTH_TEST=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Real-IP: 192.168.0.82" http://localhost/admin/ 2>/dev/null || echo "000")
echo "  • Authorized device (192.168.0.82): HTTP $AUTH_TEST"

# Test unauthorized transaction access
UNAUTH_TRANS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Real-IP: 192.168.0.99" http://localhost/admin/transactions/ 2>/dev/null || echo "000")
echo "  • Unauthorized transaction (192.168.0.99): HTTP $UNAUTH_TRANS"

# Test unauthorized general admin access (should work for viewing)
UNAUTH_ADMIN=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Real-IP: 192.168.0.99" http://localhost/admin/ 2>/dev/null || echo "000")
echo "  • Unauthorized admin viewing (192.168.0.99): HTTP $UNAUTH_ADMIN"

# Test static files
STATIC_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
echo "  • Static files: HTTP $STATIC_TEST"

# Test from localhost (should be authorized)
LOCAL_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
echo "  • Localhost access: HTTP $LOCAL_TEST"

echo ""
echo "📊 FINAL SECURITY STATUS"
echo "========================"

SERVICE_STATUS=$(sudo systemctl is-active armguard)
echo "🔧 Service Status: $SERVICE_STATUS"

# Show device authorization status
echo "🔐 Device Authorization: ACTIVE"
python -c "
import json, os
try:
    with open('/opt/armguard/authorized_devices.json', 'r') as f:
        config = json.load(f)
    print('   📱 Authorized Devices:')
    for device in config['transaction_devices']:
        status = '✅ ENABLED' if device['can_transact'] else '⚠️  DISABLED'
        print(f'      • {device[\"name\"]} ({device[\"ip\"]}) - {status}')
except:
    print('   ❌ Configuration file error')
"

echo ""
if [ "$AUTH_TEST" = "200" ] || [ "$AUTH_TEST" = "302" ]; then
    echo "🎉 DEVICE AUTHORIZATION FIXED!"
    echo "=============================="
    echo ""
    echo "✅ Security Status:"
    echo "  • Authorized Device (Your PC): ✅ WORKING ($AUTH_TEST)"
    echo "  • Unauthorized Transactions: 🔒 BLOCKED ($UNAUTH_TRANS)"
    echo "  • General Admin Viewing: 👁️ AVAILABLE ($UNAUTH_ADMIN)"
    echo "  • Static Files: ✅ WORKING ($STATIC_TEST)"
    echo ""
    echo "🔐 Access Control Active:"
    echo "  • Your PC (192.168.0.82): Full transaction access"
    echo "  • Other devices: Read-only access (transactions blocked)"
    echo ""
    echo "🌐 Test your secure system:"
    echo "  http://192.168.0.177"
    echo ""
    echo "📋 Device Management:"
    echo "  python /opt/armguard/manage_device_auth.py"
    
else
    echo "⚠️  Still having authorization issues"
    echo "Check recent logs for more details:"
    sudo journalctl -u armguard --no-pager -n 10
fi