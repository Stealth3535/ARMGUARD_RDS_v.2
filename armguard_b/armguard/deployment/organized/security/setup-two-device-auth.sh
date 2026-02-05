#!/bin/bash

################################################################################
# ArmGuard Two-Device Authorization Setup
# Restricts transactions to only Developer PC and Armory PC
################################################################################

echo "🔐 Setting up two-device transaction authorization..."
echo "Only Developer PC and Armory PC will be allowed to perform transactions."
echo ""

# Get current network info
LAN_IP=$(hostname -I | cut -d' ' -f1)

echo "📋 Current System:"
echo "  • ArmGuard Server IP: $LAN_IP"
echo "  • Admin Panel: http://$LAN_IP/admin"
echo ""

echo "🔍 Step 1: Identify your authorized devices"
echo "=========================================="
echo ""
echo "I need to identify your two authorized devices:"
echo "1. Developer PC (your current device)"
echo "2. Armory PC (the armory workstation)"
echo ""

echo "To get device information, run these commands on each PC:"
echo ""
echo "On Windows:"
echo "  ipconfig /all"
echo "  Look for 'Physical Address' (MAC) and 'IPv4 Address'"
echo ""
echo "On Linux:"
echo "  ip addr show"
echo "  Look for 'link/ether' (MAC) and 'inet' (IP)"
echo ""

echo "📝 Please provide the following information:"
echo ""
echo "DEVELOPER PC:"
echo "  IP Address: ___________________"
echo "  MAC Address: _________________"
echo ""
echo "ARMORY PC:"
echo "  IP Address: ___________________" 
echo "  MAC Address: _________________"
echo ""

# Create a configuration script that will be filled in
cat > /home/armguard/armguard/deployment/configure-authorized-devices.sh << 'EOF'
#!/bin/bash

################################################################################
# Configure Authorized Devices for ArmGuard
# Run this script after filling in the device information
################################################################################

# FILL IN YOUR DEVICE INFORMATION HERE:
DEVELOPER_PC_IP=""      # Example: "192.168.0.82"
DEVELOPER_PC_MAC=""     # Example: "AA:BB:CC:DD:EE:FF"
DEVELOPER_PC_NAME="Developer PC"

ARMORY_PC_IP=""         # Example: "192.168.0.100" 
ARMORY_PC_MAC=""        # Example: "11:22:33:44:55:66"
ARMORY_PC_NAME="Armory PC"

# Validation
if [ -z "$DEVELOPER_PC_IP" ] || [ -z "$DEVELOPER_PC_MAC" ] || [ -z "$ARMORY_PC_IP" ] || [ -z "$ARMORY_PC_MAC" ]; then
    echo "❌ Error: Please fill in all device information first"
    echo "Edit this file and add the IP and MAC addresses for both devices"
    exit 1
fi

echo "🔐 Configuring authorized devices..."
echo "Developer PC: $DEVELOPER_PC_IP ($DEVELOPER_PC_MAC)"
echo "Armory PC: $ARMORY_PC_IP ($ARMORY_PC_MAC)"
echo ""

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
                    'can_transact': True
                },
                {
                    'name': '${ARMORY_PC_NAME}',
                    'ip': '${ARMORY_PC_IP}',
                    'mac': '${ARMORY_PC_MAC}',
                    'access_level': 'full', 
                    'can_transact': True
                }
            ],
            'read_only_devices': [
                # Other devices will be read-only by default
            ]
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
PYEOF

# Create enhanced middleware for device checking
cat > /opt/armguard/core/middleware/device_authorization.py << 'PYEOF'
import json
import os
from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Middleware to check device authorization for transactions
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
        except:
            self.authorized_devices = []
    
    def process_request(self, request):
        """Check if device is authorized for the requested action"""
        
        # Skip for non-transaction paths
        transaction_paths = [
            '/transactions/qr-scanner/',
            '/transactions/create/', 
            '/transactions/edit/',
            '/transactions/delete/',
            '/inventory/add/',
            '/inventory/edit/',
            '/inventory/delete/',
            '/admin/transactions/',
            '/admin/inventory/'
        ]
        
        # Check if this is a transaction path
        is_transaction_path = any(request.path.startswith(path) for path in transaction_paths)
        
        if not is_transaction_path:
            return None
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Check if device is authorized
        if not self.is_device_authorized(client_ip):
            return self.device_unauthorized_response(client_ip, request.path)
        
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
        
        authorized_ips = [device['ip'] for device in self.authorized_devices]
        authorized_names = [f"{device['name']} ({device['ip']})" for device in self.authorized_devices]
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Device Not Authorized - ArmGuard</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ color: #d32f2f; border-bottom: 2px solid #d32f2f; padding-bottom: 10px; margin-bottom: 20px; }}
                .error {{ background: #ffebee; padding: 15px; border-radius: 4px; margin: 20px 0; border-left: 4px solid #d32f2f; }}
                .info {{ background: #e8f5e8; padding: 15px; border-radius: 4px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛡️ ArmGuard Device Authorization</h1>
                </div>
                
                <div class="error">
                    <h3>❌ Device Not Authorized for Transactions</h3>
                    <p><strong>Your device IP:</strong> {client_ip}</p>
                    <p><strong>Requested path:</strong> {path}</p>
                </div>
                
                <div class="info">
                    <h3>🔐 Authorized Transaction Devices:</h3>
                    <ul>
                        {' '.join([f'<li>{name}</li>' for name in authorized_names])}
                    </ul>
                    
                    <h3>📋 Access Policy:</h3>
                    <ul>
                        <li>Only authorized devices can perform armory transactions</li>
                        <li>All other devices have read-only access</li>
                        <li>Contact your administrator to authorize additional devices</li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HttpResponseForbidden(html)
PYEOF

# Run the Django management command
echo "🔧 Setting up Django configuration..."
cd /opt/armguard
source venv/bin/activate
python manage.py setup_authorized_devices

# Add middleware to settings if not already present
if ! grep -q "device_authorization.DeviceAuthorizationMiddleware" core/settings.py; then
    echo "📝 Adding device authorization middleware to settings..."
    
    # Backup settings
    cp core/settings.py core/settings.py.backup
    
    # Add middleware
    sed -i "/MIDDLEWARE = \[/,/\]/ s/]/    'core.middleware.device_authorization.DeviceAuthorizationMiddleware',\n]/" core/settings.py
    
    echo "✅ Middleware added to settings.py"
else
    echo "✅ Device authorization middleware already configured"
fi

# Restart services
echo "🔄 Restarting ArmGuard service..."
systemctl restart armguard

echo ""
echo "✅ DEVICE AUTHORIZATION CONFIGURED!"
echo "=================================="
echo ""
echo "Authorized devices for transactions:"
echo "  1. ${DEVELOPER_PC_NAME}: ${DEVELOPER_PC_IP}"
echo "  2. ${ARMORY_PC_NAME}: ${ARMORY_PC_IP}"
echo ""
echo "🔒 Security Policy Active:"
echo "  • Only these 2 devices can perform armory transactions"
echo "  • All other devices will get 'Device Not Authorized' message"
echo "  • Read-only access still available from other devices"
echo ""
echo "To modify authorized devices later:"
echo "  Edit: /opt/armguard/authorized_devices.json"
echo "  Restart: sudo systemctl restart armguard"
echo ""
EOF

chmod +x /home/armguard/armguard/deployment/configure-authorized-devices.sh

echo ""
echo "✅ Two-device authorization system created!"
echo ""
echo "📋 NEXT STEPS:"
echo "=============="
echo ""
echo "1. Get device information from both PCs:"
echo "   • Developer PC: Run 'ipconfig /all' (Windows) or 'ip addr' (Linux)"
echo "   • Armory PC: Run the same command"
echo ""
echo "2. Edit the configuration file:"
echo "   nano /home/armguard/armguard/deployment/configure-authorized-devices.sh"
echo ""
echo "3. Fill in the device information (IP and MAC addresses)"
echo ""
echo "4. Run the configuration:"
echo "   sudo /home/armguard/armguard/deployment/configure-authorized-devices.sh"
echo ""
echo "🔐 After setup:"
echo "  ✅ Developer PC ($YOUR_CURRENT_IP) → Full transaction access"
echo "  ✅ Armory PC (specify IP) → Full transaction access" 
echo "  ❌ All other devices → Read-only access only"
echo ""
echo "Would you like help getting your current device IP address now?"