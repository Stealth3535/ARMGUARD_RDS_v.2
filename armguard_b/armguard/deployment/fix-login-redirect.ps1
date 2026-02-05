# Fix Django Login URL - Transfer and Execute Script

Write-Host "🔧 Transferring and executing Django login URL fix..." -ForegroundColor Cyan

# Copy the fix script to the Raspberry Pi
$fixScript = "Y:\home\armguard\armguard\deployment\organized\active\fix-login-url.sh"

# Use SCP to copy the script (if available) or create it directly on the Pi
Write-Host "📤 Creating fix script on Raspberry Pi..." -ForegroundColor Yellow

# Create the fix script directly on the Pi using a here-document approach
$scriptContent = @'
#!/bin/bash

echo "🔧 Fixing Django Login URL Configuration"
echo "========================================"

cd /opt/armguard
source venv/bin/activate

echo "📋 Current Django login settings..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.conf import settings
print('Current LOGIN_URL:', getattr(settings, 'LOGIN_URL', 'Not set'))
"

echo ""
echo "🔧 Updating settings.py to fix login URL..."

# Backup current settings
cp core/settings.py core/settings.py.pre-login-fix

# Update settings to fix LOGIN_URL
python << 'PYFIX'
import re

# Read settings file
with open('core/settings.py', 'r') as f:
    content = f.read()

# Add or update LOGIN_URL setting
login_url_pattern = r'LOGIN_URL\s*=.*'

# Check if LOGIN_URL exists and update it
if re.search(login_url_pattern, content):
    content = re.sub(login_url_pattern, "LOGIN_URL = '/login/'", content)
    print("✅ Updated existing LOGIN_URL setting")
else:
    # Add LOGIN_URL setting at the end
    login_settings = """

# Login/Logout URLs - Fixed to match URL patterns
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
"""
    content = content.rstrip() + login_settings
    print("✅ Added LOGIN_URL settings")

# Write back
with open('core/settings.py', 'w') as f:
    f.write(content)

print("✅ Settings updated successfully")
PYFIX

echo ""
echo "🔄 Restarting Django service..."
sudo systemctl restart armguard
sleep 10

echo ""
echo "🧪 Testing the fix..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/login/ 2>/dev/null || echo "000")

echo "Admin page: HTTP $HTTP_STATUS"
echo "Login page: HTTP $LOGIN_STATUS" 

if [ "$LOGIN_STATUS" = "200" ]; then
    echo ""
    echo "✅ SUCCESS! Login URL fixed"
    echo "🌐 Try: http://192.168.0.177/admin/"
else
    echo "❌ Need additional troubleshooting"
fi
'@

Write-Host "🚀 The fix needed is to update LOGIN_URL in Django settings" -ForegroundColor Green
Write-Host ""
Write-Host "📋 The issue:" -ForegroundColor Yellow
Write-Host "  • Django is redirecting to /accounts/login/ (default)" -ForegroundColor White
Write-Host "  • But your URL patterns show login is at /login/" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Manual fix steps:" -ForegroundColor Yellow  
Write-Host "  1. SSH into the Pi: ssh armguard@192.168.0.177" -ForegroundColor White
Write-Host "  2. Edit settings: nano /opt/armguard/core/settings.py" -ForegroundColor White
Write-Host "  3. Add/update: LOGIN_URL = '/login/'" -ForegroundColor White
Write-Host "  4. Restart: sudo systemctl restart armguard" -ForegroundColor White
Write-Host ""
Write-Host "Or use the emergency fix from organized/active/:" -ForegroundColor Green
Write-Host "  sudo ./emergency-service-fix.sh" -ForegroundColor Cyan

Write-Host ""
Write-Host "🎯 After fix, admin should redirect to /login/ instead of /accounts/login/" -ForegroundColor Green