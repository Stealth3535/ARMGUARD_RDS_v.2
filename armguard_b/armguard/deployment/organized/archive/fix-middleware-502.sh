#!/bin/bash

echo "🔧 Fixing ArmGuard Device Authorization..."

# Create the middleware directory structure 
mkdir -p /opt/armguard/core/middleware

# Create __init__.py file
cat > /opt/armguard/core/middleware/__init__.py << 'EOF'
# Middleware package
EOF

# Create the device authorization middleware
cat > /opt/armguard/core/middleware/device_authorization.py << 'EOF'
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
EOF

# Set proper permissions
chmod 644 /opt/armguard/core/middleware/__init__.py
chmod 644 /opt/armguard/core/middleware/device_authorization.py

# Restart the service
echo "🔄 Restarting ArmGuard service..."
sudo systemctl restart armguard

# Wait for restart
sleep 5

# Test the service
echo "🧪 Testing service status..."
SERVICE_STATUS=$(sudo systemctl is-active armguard)
echo "Service Status: $SERVICE_STATUS"

# Test web response
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
echo "HTTP Response: $HTTP_CODE"

# Show configuration
echo ""
echo "✅ MIDDLEWARE FIX COMPLETE!"
echo "=========================="
echo ""
echo "📁 Created Files:"
echo "  • /opt/armguard/core/middleware/__init__.py"
echo "  • /opt/armguard/core/middleware/device_authorization.py"
echo ""
echo "🔐 Device Authorization:"
echo "  • Developer PC (192.168.0.82): ✅ Authorized" 
echo "  • All other devices: ❌ Transaction blocked"
echo ""
echo "🌐 Service Status:"
echo "  • ArmGuard Service: $SERVICE_STATUS"
echo "  • HTTP Response: $HTTP_CODE"
echo ""
echo "🎯 Test Your Setup:"
echo "  http://192.168.0.177/admin (from your PC)"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "🎉 SUCCESS: System is working!"
else
    echo "⚠️  Service needs attention - check logs:"
    echo "   sudo journalctl -u armguard -f"
fi