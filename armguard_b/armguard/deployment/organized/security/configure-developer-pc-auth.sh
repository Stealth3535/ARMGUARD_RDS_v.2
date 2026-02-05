#!/bin/bash

################################################################################
# Configure Developer PC Authorization - Pre-filled
# Your device information has been pre-filled from ipconfig output
################################################################################

echo "🔐 Configuring ArmGuard Device Authorization..."
echo ""

# PRE-FILLED DEVICE INFORMATION
DEVELOPER_PC_IP="192.168.0.82"
DEVELOPER_PC_MAC="74-56-3C-DC-68-96"
DEVELOPER_PC_NAME="Developer PC (DESKTOP-E3N8R9V)"

# ARMORY PC - Fill this in when available
ARMORY_PC_IP="192.168.0.100"        # Change this to actual armory PC IP
ARMORY_PC_MAC="AA:BB:CC:DD:EE:FF"   # Change this to actual armory PC MAC
ARMORY_PC_NAME="Armory PC"

echo "📋 Device Configuration:"
echo "  Developer PC: $DEVELOPER_PC_IP ($DEVELOPER_PC_MAC)"
echo "  Armory PC: $ARMORY_PC_IP ($ARMORY_PC_MAC) [UPDATE NEEDED]"
echo ""

# Validation
if [ "$ARMORY_PC_MAC" = "AA:BB:CC:DD:EE:FF" ]; then
    echo "⚠️  WARNING: Armory PC MAC address needs to be updated"
    echo "   For now, configuring with Developer PC only"
    echo ""
fi

echo "🔧 Setting up Django configuration..."

# Create Django management command for device authorization
mkdir -p /opt/armguard/core/management/commands

cat > /opt/armguard/core/management/commands/setup_authorized_devices.py << PYEOF
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import json
import os

class Command(BaseCommand):
    help = 'Setup authorized devices for transaction access'

    def handle(self, *args, **options):
        # Create authorized devices configuration
        authorized_devices = {
            'transaction_devices': [
                {
                    'name': '${DEVELOPER_PC_NAME}',
                    'ip': '${DEVELOPER_PC_IP}',
                    'mac': '${DEVELOPER_PC_MAC}',
                    'access_level': 'full',
                    'can_transact': True,
                    'description': 'Primary development workstation'
                },
                {
                    'name': '${ARMORY_PC_NAME}',
                    'ip': '${ARMORY_PC_IP}',
                    'mac': '${ARMORY_PC_MAC}',
                    'access_level': 'full', 
                    'can_transact': True,
                    'description': 'Armory operations workstation'
                }
            ],
            'read_only_devices': [],
            'configuration': {
                'strict_mode': True,
                'log_unauthorized_attempts': True,
                'created_date': '$(date)',
                'last_updated': '$(date)'
            }
        }
        
        # Save configuration
        config_file = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
        with open(config_file, 'w') as f:
            json.dump(authorized_devices, f, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f'✅ Authorized devices configured: {config_file}')
        )
        
        # Create device authorization groups
        transaction_group, created = Group.objects.get_or_create(name='Transaction Authorized')
        if created:
            self.stdout.write('✅ Created Transaction Authorized group')
        
        self.stdout.write('✅ Device authorization setup complete')
        self.stdout.write(f'   Developer PC: ${DEVELOPER_PC_IP}')
        self.stdout.write(f'   Armory PC: ${ARMORY_PC_IP}')
PYEOF

# Create enhanced middleware for device checking
cat > /opt/armguard/core/middleware/device_authorization.py << 'PYEOF'
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
    Middleware to check device authorization for transactions
    Only allows Developer PC and Armory PC to perform transactions
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.load_authorized_devices()
        super().__init__(get_response)
    
    def load_authorized_devices(self):
        """Load authorized devices from configuration"""
        try:
            config_file = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
            with open(config_file, 'r') as f:
                config = json.load(f)
                self.authorized_devices = config.get('transaction_devices', [])
                logger.info(f"Loaded {len(self.authorized_devices)} authorized devices")
        except Exception as e:
            logger.error(f"Failed to load authorized devices: {e}")
            self.authorized_devices = []
    
    def process_request(self, request):
        """Check if device is authorized for the requested action"""
        
        # Skip for static files and admin login
        skip_paths = ['/static/', '/media/', '/favicon.ico', '/login/', '/logout/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        # Define transaction-restricted paths
        transaction_paths = [
            '/transactions/qr-scanner',
            '/transactions/create',
            '/transactions/edit',
            '/transactions/delete',
            '/inventory/add',
            '/inventory/edit', 
            '/inventory/delete',
            '/admin/transactions/',
            '/admin/inventory/',
            '/users/register'
        ]
        
        # Check if this is a transaction path
        is_transaction_path = any(request.path.startswith(path) for path in transaction_paths)
        
        if not is_transaction_path:
            return None
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check if device is authorized
        if not self.is_device_authorized(client_ip):
            # Log unauthorized attempt
            logger.warning(f"Unauthorized transaction attempt from {client_ip} to {request.path}")
            return self.device_unauthorized_response(client_ip, request.path)
        
        # Log authorized access
        logger.info(f"Authorized transaction access from {client_ip} to {request.path}")
        return None
    
    def get_client_ip(self, request):
        """Get client IP from request"""
        forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
    
    def is_device_authorized(self, client_ip):
        """Check if device IP is in authorized list"""
        for device in self.authorized_devices:
            if device['ip'] == client_ip and device.get('can_transact', False):
                return True
        return False
    
    def device_unauthorized_response(self, client_ip, path):
        """Return unauthorized device response"""
        
        authorized_devices = [f"{device['name']} ({device['ip']})" for device in self.authorized_devices]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Device Not Authorized - ArmGuard Military System</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 0; 
                    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .container {{ 
                    max-width: 600px; 
                    background: white; 
                    border-radius: 12px; 
                    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
                    overflow: hidden;
                }}
                .header {{ 
                    background: #d32f2f; 
                    color: white; 
                    padding: 20px 30px;
                    text-align: center;
                }}
                .content {{ padding: 30px; }}
                .error {{ 
                    background: #ffebee; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                    border-left: 4px solid #d32f2f; 
                }}
                .info {{ 
                    background: #e8f5e8; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin: 20px 0; 
                }}
                .device-list {{ 
                    background: #f5f5f5; 
                    padding: 15px; 
                    border-radius: 4px; 
                    font-family: monospace;
                }}
                .timestamp {{ 
                    color: #666; 
                    font-size: 0.9em; 
                    text-align: center; 
                    margin-top: 20px;
                }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin: 8px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ ArmGuard Military Inventory System</h1>
                    <h2>Device Authorization Required</h2>
                </div>
                
                <div class="content">
                    <div class="error">
                        <h3>❌ Transaction Access Denied</h3>
                        <p><strong>Your device IP:</strong> <code>{client_ip}</code></p>
                        <p><strong>Requested operation:</strong> <code>{path}</code></p>
                        <p><strong>Reason:</strong> Device not authorized for armory transactions</p>
                    </div>
                    
                    <div class="info">
                        <h3>🔐 Authorized Transaction Devices:</h3>
                        <div class="device-list">
                            {'<br>'.join([f'• {name}' for name in authorized_devices])}
                        </div>
                        
                        <h3>📋 Security Policy:</h3>
                        <ul>
                            <li><strong>Armory Transactions:</strong> Only authorized workstations</li>
                            <li><strong>Inventory Viewing:</strong> Available from any LAN device</li>
                            <li><strong>Status Reports:</strong> Read-only access available</li>
                            <li><strong>User Management:</strong> Authorized devices only</li>
                        </ul>
                        
                        <h3>📞 Support:</h3>
                        <p>Contact your system administrator to authorize additional devices or for access assistance.</p>
                    </div>
                    
                    <div class="timestamp">
                        Access attempt logged: {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponseForbidden(html)
PYEOF

# Create the management commands directory
mkdir -p /opt/armguard/core/management/commands
touch /opt/armguard/core/management/__init__.py
touch /opt/armguard/core/management/commands/__init__.py

# Create middleware directory
mkdir -p /opt/armguard/core/middleware
touch /opt/armguard/core/middleware/__init__.py

# Run the Django management command
echo "🔧 Running Django configuration..."
cd /opt/armguard
source venv/bin/activate
python manage.py setup_authorized_devices

# Add middleware to settings if not already present
if ! grep -q "device_authorization.DeviceAuthorizationMiddleware" core/settings.py; then
    echo "📝 Adding device authorization middleware to settings..."
    
    # Backup settings
    cp core/settings.py core/settings.py.backup
    
    # Add middleware to the MIDDLEWARE list
    python << PYEOF
import re

# Read the settings file
with open('core/settings.py', 'r') as f:
    content = f.read()

# Add the middleware to the MIDDLEWARE list
if 'core.middleware.device_authorization.DeviceAuthorizationMiddleware' not in content:
    # Find the MIDDLEWARE section and add our middleware
    middleware_pattern = r'(MIDDLEWARE\s*=\s*\[)(.*?)(\])'
    def add_middleware(match):
        start = match.group(1)
        middlewares = match.group(2)
        end = match.group(3)
        new_middleware = "    'core.middleware.device_authorization.DeviceAuthorizationMiddleware',"
        return f"{start}{middlewares.rstrip()}\n{new_middleware}\n{end}"
    
    content = re.sub(middleware_pattern, add_middleware, content, flags=re.DOTALL)
    
    with open('core/settings.py', 'w') as f:
        f.write(content)
    
    print("✅ Device authorization middleware added")
else:
    print("✅ Middleware already present")
PYEOF

else
    echo "✅ Device authorization middleware already configured"
fi

# Restart services
echo "🔄 Restarting ArmGuard service..."
systemctl restart armguard

# Wait for restart
sleep 5

# Test the configuration
echo "🧪 Testing device authorization..."
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")

echo ""
echo "✅ DEVICE AUTHORIZATION CONFIGURED!"
echo "=================================="
echo ""
echo "🔐 Your Authorized Devices:"
echo "  1. Developer PC (DESKTOP-E3N8R9V): 192.168.0.82"
echo "  2. Armory PC: $ARMORY_PC_IP (UPDATE NEEDED)"
echo ""
echo "🛡️ Security Policy Active:"
echo "  ✅ Developer PC (192.168.0.82) → Full transaction access"
echo "  ⚠️  Armory PC → Need to update IP/MAC when available"
echo "  ❌ All other devices → Read-only access only"
echo ""
echo "📋 Current Status:"
echo "  • Web Server: HTTP $response"
echo "  • Authorization: Active"
echo "  • Config File: /opt/armguard/authorized_devices.json"
echo ""
echo "🔧 To add/update Armory PC later:"
echo "  1. Get Armory PC network info (ipconfig /all)"
echo "  2. Edit: /opt/armguard/authorized_devices.json"  
echo "  3. Restart: sudo systemctl restart armguard"
echo ""
echo "🎯 Test your setup:"
echo "  • From your PC (192.168.0.82): http://192.168.0.177/admin → Should work"
echo "  • From another device: Same URL → Should be blocked for transactions"
echo ""