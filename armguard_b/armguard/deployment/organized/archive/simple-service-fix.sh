#!/bin/bash

echo "🚨 Basic Service Recovery"
echo ""

# Stop the service
sudo systemctl stop armguard

echo "📝 Testing basic Django manually..."
cd /opt/armguard
source venv/bin/activate

# Test basic Django startup
echo "Testing Django startup..."
timeout 10s python manage.py runserver 127.0.0.1:8001 &
DJANGO_PID=$!
sleep 3

# Test if Django responds
HTTP_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001 2>/dev/null || echo "000")
echo "Django manual test: HTTP $HTTP_TEST"

# Kill the test server
kill $DJANGO_PID 2>/dev/null

if [ "$HTTP_TEST" = "200" ]; then
    echo "✅ Django works manually"
    
    echo "🔧 Checking Gunicorn service file..."
    
    # Show the service file
    echo "Current service configuration:"
    cat /etc/systemd/system/armguard.service
    
    echo ""
    echo "🔄 Reloading and starting service..."
    sudo systemctl daemon-reload
    sudo systemctl start armguard
    
    # Wait and test
    sleep 15
    
    SERVICE_STATUS=$(sudo systemctl is-active armguard)
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
    
    echo ""
    echo "📊 Final Status:"
    echo "  • Service: $SERVICE_STATUS"
    echo "  • HTTP: $HTTP_CODE" 
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ SUCCESS! Service is running"
        echo "🌐 Access: http://192.168.0.177"
    else
        echo "❌ Service issue - showing logs:"
        sudo journalctl -u armguard --no-pager -n 15
    fi
    
else
    echo "❌ Django has basic configuration issues"
    echo "🧪 Checking Python environment..."
    
    # Check Python and packages
    which python
    python --version
    pip list | grep -E "(django|gunicorn)"
    
    echo ""
    echo "🔧 Try manual server:"
    echo "cd /opt/armguard && source venv/bin/activate && python manage.py runserver 0.0.0.0:8000"
fi