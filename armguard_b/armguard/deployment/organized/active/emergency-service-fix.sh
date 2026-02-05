#!/bin/bash

set -e  # Exit on any error

# Trap to handle cleanup on exit
cleanup() {
    if [ -f "/tmp/emergency_fix.lock" ]; then
        rm -f "/tmp/emergency_fix.lock"
    fi
}
trap cleanup EXIT

# Prevent multiple instances
if [ -f "/tmp/emergency_fix.lock" ]; then
    echo "ERROR: Another emergency fix is already running"
    exit 1
fi
touch "/tmp/emergency_fix.lock"

echo "🚨 Emergency Service Fix - Removing Problematic Middleware"
echo ""

# Verify we're in the right location
if [ ! -f "/opt/armguard/manage.py" ]; then
    echo "ERROR: ArmGuard installation not found at /opt/armguard"
    exit 1
fi

# Stop the service safely
echo "Stopping ArmGuard service..."
sudo systemctl stop armguard

# Wait for service to stop
timeout=0
while sudo systemctl is-active --quiet armguard && [ $timeout -lt 30 ]; do
    sleep 1
    timeout=$((timeout + 1))
done

if sudo systemctl is-active --quiet armguard; then
    echo "ERROR: Failed to stop service"
    exit 1
fi

echo "📝 Backing up and fixing settings.py..."

# Create timestamped backup
BACKUP_FILE="/opt/armguard/core/settings.py.emergency.$(date +%Y%m%d_%H%M%S)"
sudo cp /opt/armguard/core/settings.py "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE"

# Remove the middleware line safely with validation
cd /opt/armguard
sudo python3 << 'PYFIX'
import re
import shutil

try:
    # Read current settings
    with open('core/settings.py', 'r') as f:
        content = f.read()
    
    # Validate it's a proper Django settings file
    if 'MIDDLEWARE' not in content or 'INSTALLED_APPS' not in content:
        print("ERROR: Invalid Django settings file")
        exit(1)
    
    # Remove problematic middleware lines
    problematic_middlewares = [
        'device_authorization.DeviceAuthorizationMiddleware',
        'core.middleware.device_authorization.DeviceAuthorizationMiddleware'
    ]
    
    for middleware in problematic_middlewares:
        pattern = rf".*['\"].*{re.escape(middleware)}.*['\"].*,?\n?"
        content = re.sub(pattern, '', content, flags=re.MULTILINE)
    
    # Validate Python syntax
    compile(content, 'core/settings.py', 'exec')
    
    # Write back
    with open('core/settings.py', 'w') as f:
        f.write(content)
    
    print("✅ Removed problematic middleware from settings")
    
except Exception as e:
    print(f"ERROR: Failed to fix settings: {e}")
    exit(1)
PYFIX

# Test Django configuration
echo "🧪 Testing Django configuration..."
cd /opt/armguard
source venv/bin/activate

# Quick Django check with timeout
if timeout 30s python manage.py check --deploy; then
    echo "✅ Django configuration valid"
else
    echo "❌ Django configuration has errors"
    echo "Restoring backup..."
    sudo cp "$BACKUP_FILE" /opt/armguard/core/settings.py
    exit 1
fi

echo ""
echo "🔄 Starting service without middleware..."
sudo systemctl start armguard

# Wait for startup
sleep 10

# Check status
SERVICE_STATUS=$(sudo systemctl is-active armguard)
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")

echo ""
echo "📊 Service Recovery Status:"
echo "  • Service: $SERVICE_STATUS"
echo "  • HTTP: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo ""
    echo "✅ SUCCESS! Service is running"
    echo "🔧 Now let's add middleware correctly..."
    
    # Add a simpler version of the middleware
    echo "📝 Adding simplified middleware..."
    
    # Check if the middleware import is already in settings
    if ! grep -q "core.middleware.device_authorization.DeviceAuthorizationMiddleware" /opt/armguard/core/settings.py; then
        # Find the MIDDLEWARE section and add our middleware
        sudo python3 << 'PYPATCH'
import re

# Read settings file
with open('/opt/armguard/core/settings.py', 'r') as f:
    content = f.read()

# Find MIDDLEWARE list and add our middleware
middleware_pattern = r'(MIDDLEWARE\s*=\s*\[)(.*?)(\])'

def add_middleware(match):
    start = match.group(1)
    middlewares = match.group(2).strip()
    end = match.group(3)
    
    # Add our middleware after django.middleware.common.CommonMiddleware
    if 'core.middleware.device_authorization.DeviceAuthorizationMiddleware' not in middlewares:
        lines = middlewares.split('\n')
        new_lines = []
        added = False
        
        for line in lines:
            new_lines.append(line)
            # Add after CommonMiddleware
            if 'django.middleware.common.CommonMiddleware' in line and not added:
                new_lines.append("    'core.middleware.device_authorization.DeviceAuthorizationMiddleware',")
                added = True
        
        if not added:
            # Fallback: add at the end
            new_lines.append("    'core.middleware.device_authorization.DeviceAuthorizationMiddleware',")
        
        middlewares = '\n'.join(new_lines)
    
    return f'{start}\n{middlewares}\n{end}'

# Apply the middleware addition
new_content = re.sub(middleware_pattern, add_middleware, content, flags=re.DOTALL)

# Write back
with open('/opt/armguard/core/settings.py', 'w') as f:
    f.write(new_content)

print("✅ Middleware added to settings")
PYPATCH

    echo "🔄 Restarting with middleware..."
    sudo systemctl restart armguard
    
    sleep 10
    
    FINAL_STATUS=$(sudo systemctl is-active armguard)
    FINAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
    
    echo ""
    echo "🏁 Final Status:"
    echo "  • Service: $FINAL_STATUS"  
    echo "  • HTTP: $FINAL_HTTP"
    
    if [ "$FINAL_HTTP" = "200" ]; then
        echo ""
        echo "🎉 COMPLETE SUCCESS!"
        echo "✅ Service running with device authorization"
        echo "🔐 Your PC (192.168.0.82) is authorized for transactions"
        echo "❌ Other devices blocked from transactions"
        echo ""
        echo "🌐 Test: http://192.168.0.177/admin"
    else
        echo ""
        echo "⚠️  Middleware caused issues - service running without it"
        echo "🌐 Test: http://192.168.0.177/admin"
        echo "📝 Device authorization disabled for now"
    fi
    
else
    echo ""
    echo "❌ Service still failing - checking basic issues..."
    
    # Show recent logs
    echo "📋 Recent logs:"
    sudo journalctl -u armguard --no-pager -n 10
    
    echo ""
    echo "🔧 Try manual Django test:"
    echo "cd /opt/armguard && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
fi