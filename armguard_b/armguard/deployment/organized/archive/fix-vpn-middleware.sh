#!/bin/bash

echo "🔧 Fixing VPN middleware and restarting services..."

# Copy the fixed file to production
cp /home/armguard/armguard/vpn_integration/core_integration/vpn_middleware.py /opt/armguard/vpn_integration/core_integration/vpn_middleware.py

# Restart the ArmGuard service to pick up the fix
systemctl restart armguard

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet armguard; then
    echo "✅ ArmGuard service restarted successfully"
    
    # Test web response
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
    if [ "$response" = "200" ]; then
        echo "✅ Web server responding with HTTP $response"
        echo "🎉 Your ArmGuard application is now working!"
        echo ""
        echo "Access your system at:"
        echo "  http://192.168.0.177"
        echo "  http://192.168.0.177/admin"
    else
        echo "❌ Web server issue - HTTP $response"
    fi
else
    echo "❌ Service failed to start. Checking logs..."
    journalctl -u armguard --no-pager -n 10
fi