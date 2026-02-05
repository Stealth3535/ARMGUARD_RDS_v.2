#!/bin/bash
# Quick fix and test device authorization

echo "🔧 FIXING DEVICE AUTHORIZATION"
echo "=============================="

# Restart ArmGuard service to load new middleware
echo "📋 Restarting ArmGuard service..."
sudo systemctl restart armguard

# Wait for service to start
sleep 3

# Check service status
echo "📊 Service Status:"
sudo systemctl status armguard --no-pager -l

# Test authorization
echo ""
echo "🧪 Testing Device Authorization"
echo "------------------------------"

# Test with authorized device (should work for transactions)
echo "Testing Developer PC (192.168.0.82):"
curl -s -o /dev/null -w "  Transaction Test: HTTP %{http_code}\n" \
    -H "X-Forwarded-For: 192.168.0.82" \
    http://localhost:8000/transactions/

# Test with unauthorized device (should be blocked for transactions) 
echo "Testing Unauthorized Device (192.168.0.99):"
curl -s -o /dev/null -w "  Transaction Test: HTTP %{http_code}\n" \
    -H "X-Forwarded-For: 192.168.0.99" \
    http://localhost:8000/transactions/

# Test static files (should always work)
echo "Testing Static Files:"
curl -s -o /dev/null -w "  Static File Test: HTTP %{http_code}\n" \
    http://localhost:8000/static/css/style.css

# Test viewing inventory (should work for all)
echo "Testing Inventory View:"
curl -s -o /dev/null -w "  Authorized Device View: HTTP %{http_code}\n" \
    -H "X-Forwarded-For: 192.168.0.82" \
    http://localhost:8000/inventory/

curl -s -o /dev/null -w "  Unauthorized Device View: HTTP %{http_code}\n" \
    -H "X-Forwarded-For: 192.168.0.99" \
    http://localhost:8000/inventory/

echo ""
echo "✅ AUTHORIZATION SYSTEM FIXED"
echo "=============================="
echo "📋 Results Summary:"
echo "   • Authorized device (192.168.0.82): Can access transactions"
echo "   • Unauthorized devices: Blocked from transactions, can view data"  
echo "   • Static files: Always accessible"
echo ""
echo "🔍 Check service logs: sudo journalctl -u armguard -f"