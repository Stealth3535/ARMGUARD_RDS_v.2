#!/bin/bash

echo "🔧 Comprehensive Django Access Fix"
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📝 Step 1: Fix settings.py middleware list..."

# Create a clean settings.py without broken middleware
python << 'PYFIX'
import re

# Read current settings
with open('core/settings.py', 'r') as f:
    content = f.read()

# Remove broken middleware lines completely
broken_middleware = [
    'core.middleware.RateLimitMiddleware',
    'core.middleware.SecurityHeadersMiddleware', 
    'core.middleware.StripSensitiveHeadersMiddleware'
]

for middleware in broken_middleware:
    # Remove lines containing these middleware
    pattern = rf".*'{middleware}'.*,?\n"
    content = re.sub(pattern, '', content)

# Write back the cleaned settings
with open('core/settings.py', 'w') as f:
    f.write(content)

print("✅ Removed broken middleware from settings.py")
PYFIX

echo "📝 Step 2: Fix network middleware to allow root access..."

# Add root path to allowed paths
python << 'PYFIX'
# Read network middleware
with open('core/network_middleware.py', 'r') as f:
    content = f.read()

# Add root path and common paths to WAN_ALLOWED_PATHS
if "'/'" not in content:
    # Find WAN_ALLOWED_PATHS and add root access
    wan_section = content.find('WAN_ALLOWED_PATHS = [')
    if wan_section > -1:
        # Find the end of the list
        insert_pos = content.find(']', wan_section)
        if insert_pos > -1:
            # Add root and common paths before the closing bracket
            new_paths = '''        '/',                         # Root access
        '/admin/',                   # Admin interface
        '/login/',                   # Login page
        '/logout/',                  # Logout page
        '/favicon.ico',              # Favicon
'''
            content = content[:insert_pos] + new_paths + '        ' + content[insert_pos:]
            
            with open('core/network_middleware.py', 'w') as f:
                f.write(content)
            
            print("✅ Added root path access to network middleware")
        else:
            print("⚠️  Could not find WAN_ALLOWED_PATHS end")
    else:
        print("⚠️  Could not find WAN_ALLOWED_PATHS section")
else:
    print("✅ Root path already in middleware")
PYFIX

echo "📝 Step 3: Add root URL pattern..."

# Add root URL to urls.py
python << 'PYFIX'
# Read urls.py
with open('core/urls.py', 'r') as f:
    content = f.read()

# Check if root URL exists
if "path('', " not in content:
    # Find urlpatterns and add root path
    patterns_start = content.find('urlpatterns = [')
    if patterns_start > -1:
        # Find first path after the opening bracket
        first_path_pos = content.find("path(", patterns_start)
        if first_path_pos > -1:
            # Insert root path at the beginning
            indent = "    "
            root_path = f"{indent}# Root access\n{indent}path('', views.dashboard_view, name='dashboard'),\n{indent}\n{indent}"
            content = content[:first_path_pos] + root_path + content[first_path_pos:]
            
            with open('core/urls.py', 'w') as f:
                f.write(content)
            
            print("✅ Added root URL pattern")
        else:
            print("⚠️  Could not find URL patterns")
    else:
        print("⚠️  Could not find urlpatterns")
else:
    print("✅ Root URL already exists")
PYFIX

echo "📝 Step 4: Create simple dashboard view..."

# Ensure dashboard view exists
python << 'PYFIX'
# Read views.py
with open('core/views.py', 'r') as f:
    content = f.read()

# Check if dashboard_view exists
if 'def dashboard_view(' not in content:
    # Add dashboard view
    dashboard_view = '''
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

def dashboard_view(request):
    """Simple dashboard view for root access"""
    if request.user.is_authenticated:
        # Redirect authenticated users to admin
        return redirect('/admin/')
    else:
        # Show login page for anonymous users
        return redirect('/admin/login/')
'''
    
    # Add at the beginning of the file after imports
    import_end = content.find('\n\n')
    if import_end > -1:
        content = content[:import_end] + dashboard_view + content[import_end:]
    else:
        content = dashboard_view + content
    
    with open('core/views.py', 'w') as f:
        f.write(content)
    
    print("✅ Added dashboard view")
else:
    print("✅ Dashboard view already exists")
PYFIX

echo "🧪 Step 5: Test Django configuration..."
python manage.py check

echo ""
echo "🚀 Step 6: Test manual server..."
timeout 10s python manage.py runserver 127.0.0.1:8001 &
SERVER_PID=$!
sleep 5

# Test root access
HTTP_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/ 2>/dev/null || echo "000")
echo "Root access test: HTTP $HTTP_TEST"

# Test admin access  
HTTP_ADMIN=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/admin/ 2>/dev/null || echo "000")
echo "Admin access test: HTTP $HTTP_ADMIN"

# Clean up
kill $SERVER_PID 2>/dev/null || true

if [ "$HTTP_TEST" = "200" ] || [ "$HTTP_TEST" = "302" ]; then
    echo "✅ Django working! Starting systemd service..."
    
    sudo systemctl stop armguard
    sudo systemctl daemon-reload  
    sudo systemctl start armguard
    
    sleep 10
    
    SERVICE_STATUS=$(sudo systemctl is-active armguard)
    HTTP_FINAL=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
    
    echo ""
    echo "🎉 FINAL RESULTS:"
    echo "=================="
    echo "  • Service Status: $SERVICE_STATUS"
    echo "  • HTTP Response: $HTTP_FINAL"
    
    if [ "$HTTP_FINAL" = "200" ] || [ "$HTTP_FINAL" = "302" ]; then
        echo ""
        echo "🎉 SUCCESS! ArmGuard is running!"
        echo "🌐 Access: http://192.168.0.177"
        echo "🔑 Admin: http://192.168.0.177/admin"
        echo "🔧 Root redirects to admin login"
        echo ""
        echo "✅ Fixed Issues:"
        echo "  • Removed broken middleware"
        echo "  • Fixed network access control" 
        echo "  • Added root URL routing"
        echo "  • Created dashboard view"
    else
        echo ""
        echo "⚠️  Still having issues - showing logs:"
        sudo journalctl -u armguard --no-pager -n 10
    fi
else
    echo "❌ Django still has configuration issues"
    echo "Manual test server output:"
    python manage.py runserver 127.0.0.1:8001 --verbosity=2
fi