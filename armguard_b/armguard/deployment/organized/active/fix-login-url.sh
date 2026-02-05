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
print('Available URL patterns from your error show login/ is available')
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
login_redirect_pattern = r'LOGIN_REDIRECT_URL\s*=.*'

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
echo "🔄 Restarting Django service to apply changes..."
sudo systemctl restart armguard

echo ""
echo "⏳ Waiting for service to restart..."
sleep 10

echo ""
echo "🧪 Testing the fix..."

# Test the admin page now
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
echo "Admin page test: HTTP $HTTP_STATUS"

# Check if login page is accessible
LOGIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/login/ 2>/dev/null || echo "000")
echo "Login page test: HTTP $LOGIN_STATUS"

if [ "$HTTP_STATUS" = "302" ] && [ "$LOGIN_STATUS" = "200" ]; then
    echo ""
    echo "✅ SUCCESS! Login URL issue fixed"
    echo "🌐 Admin panel: http://192.168.0.177/admin/"
    echo "🔑 Login page: http://192.168.0.177/login/"
    echo ""
    echo "The /admin/ page should now redirect to /login/ instead of /accounts/login/"
elif [ "$LOGIN_STATUS" = "200" ]; then
    echo ""
    echo "✅ Login page is accessible at /login/"
    echo "⚠️  Admin redirect might need additional checking"
    echo ""
    echo "🌐 Try accessing: http://192.168.0.177/admin/"
else
    echo ""
    echo "❌ Service may need additional troubleshooting"
    echo "📋 Check service status: sudo systemctl status armguard"
    echo "📋 Check logs: sudo journalctl -u armguard --no-pager -n 20"
fi

echo ""
echo "🔍 If you still have issues, check these URLs:"
echo "  • Main app: http://192.168.0.177/"
echo "  • Login: http://192.168.0.177/login/"  
echo "  • Admin: http://192.168.0.177/admin/"
echo ""
echo "The 404 for /accounts/login/ should now be resolved!"