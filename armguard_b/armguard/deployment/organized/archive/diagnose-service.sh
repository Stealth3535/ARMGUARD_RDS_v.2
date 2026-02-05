#!/bin/bash

echo "🔍 Diagnosing ArmGuard Service Issues..."
echo ""

# Check service logs
echo "📋 Service Logs (last 20 lines):"
sudo journalctl -u armguard --no-pager -n 20

echo ""
echo "🧪 Testing Django manually..."

# Test Django manually
cd /opt/armguard
source venv/bin/activate

echo "Testing basic Django import..."
python -c "
try:
    import django
    print('✅ Django imports OK')
except Exception as e:
    print(f'❌ Django import error: {e}')
"

echo ""
echo "Testing settings import..."
python -c "
try:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from django.conf import settings
    print('✅ Settings import OK')
    print(f'   BASE_DIR: {settings.BASE_DIR}')
except Exception as e:
    print(f'❌ Settings import error: {e}')
"

echo ""
echo "Testing middleware import..."
python -c "
try:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    import django
    django.setup()
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware
    print('✅ Middleware import OK')
except Exception as e:
    print(f'❌ Middleware import error: {e}')
"

echo ""
echo "📁 File System Check:"
echo "Middleware directory:"
ls -la /opt/armguard/core/middleware/

echo ""
echo "Settings file check:"
if grep -q "device_authorization" /opt/armguard/core/settings.py; then
    echo "✅ Middleware found in settings"
    echo "Middleware in settings:"
    grep -A 10 -B 2 "device_authorization" /opt/armguard/core/settings.py
else
    echo "❌ Middleware not found in settings"
fi

echo ""
echo "🔧 Service Configuration:"
sudo systemctl status armguard --no-pager

echo ""
echo "📝 Django Check:"
cd /opt/armguard
source venv/bin/activate
python manage.py check