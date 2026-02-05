#!/bin/bash

echo "🔍 QUICK IP DEBUG TEST"
echo "====================="

# Temporarily disable middleware to test IP detection
echo "Temporarily disabling middleware..."
cd /opt/armguard
sudo mv core/middleware/device_authorization.py core/middleware/device_authorization.py.backup 2>/dev/null || true

# Restart service
sudo systemctl restart armguard
sleep 8

echo ""
echo "📋 TEST RESULTS:"
echo "---------------"

# Test basic access
ADMIN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
echo "Admin page (no auth): HTTP $ADMIN_TEST"

# Create a simple IP detection page
sudo tee /opt/armguard/core/ip_debug.py > /dev/null << 'EOF'
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def debug_ip(request):
    """Debug IP detection"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>🔍 IP Debug - ArmGuard</title></head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>🔍 ArmGuard IP Debug</h1>
        <h2>Request Details:</h2>
        <ul>
            <li><strong>REMOTE_ADDR:</strong> {request.META.get('REMOTE_ADDR', 'Not found')}</li>
            <li><strong>HTTP_X_REAL_IP:</strong> {request.META.get('HTTP_X_REAL_IP', 'Not found')}</li>
            <li><strong>HTTP_X_FORWARDED_FOR:</strong> {request.META.get('HTTP_X_FORWARDED_FOR', 'Not found')}</li>
            <li><strong>HTTP_X_CLIENT_IP:</strong> {request.META.get('HTTP_X_CLIENT_IP', 'Not found')}</li>
        </ul>
        
        <h2>All IP-related headers:</h2>
        <ul>
    """
    
    for key, value in request.META.items():
        if any(term in key.upper() for term in ['IP', 'ADDR', 'FORWARD', 'CLIENT']):
            html += f"<li><strong>{key}:</strong> {value}</li>"
    
    html += """
        </ul>
        <hr>
        <p>💡 Use this information to configure device authorization</p>
        <p><a href="/admin/">← Back to Admin</a></p>
    </body>
    </html>
    """
    
    return HttpResponse(html)
EOF

# Add URL for debug page
if ! grep -q "debug-ip" /opt/armguard/core/urls.py; then
    sudo cp /opt/armguard/core/urls.py /opt/armguard/core/urls.py.backup
    sudo sed -i '/from django.urls import/c\from django.urls import path, include' /opt/armguard/core/urls.py
    sudo sed -i '/from . import views/a\from . import ip_debug' /opt/armguard/core/urls.py
    sudo sed -i '/urlpatterns = \[/a\    path("debug-ip/", ip_debug.debug_ip, name="debug_ip"),' /opt/armguard/core/urls.py
fi

# Restart again to load the debug page
sudo systemctl restart armguard
sleep 8

echo ""
echo "✅ MIDDLEWARE TEMPORARILY DISABLED"
echo "================================="
echo ""
echo "🌐 Now access from your PC browser:"
echo "  • Main site: http://192.168.0.177"
echo "  • IP Debug: http://192.168.0.177/debug-ip/"
echo "  • Admin: http://192.168.0.177/admin/"
echo ""
echo "📋 Steps:"
echo "1. Open browser on your PC (192.168.0.82)"
echo "2. Visit: http://192.168.0.177/debug-ip/"
echo "3. Note what IP it shows for your device"
echo "4. Report back what IP was detected"
echo ""
echo "⚠️  Security is DISABLED until we fix IP detection!"
echo ""

FINAL_ADMIN=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/admin/ 2>/dev/null || echo "000")
FINAL_DEBUG=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/debug-ip/ 2>/dev/null || echo "000")

echo "Current Status:"
echo "  • Admin page: HTTP $FINAL_ADMIN" 
echo "  • Debug page: HTTP $FINAL_DEBUG"

if [ "$FINAL_DEBUG" = "200" ]; then
    echo ""
    echo "🎉 SUCCESS! Debug page is accessible"
    echo "Visit http://192.168.0.177/debug-ip/ from your PC now!"
else
    echo ""
    echo "❌ Still having issues. Let's check what's wrong:"
    sudo journalctl -u armguard -n 10 --no-pager
fi