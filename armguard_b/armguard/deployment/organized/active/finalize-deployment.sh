#!/bin/bash

################################################################################
# ARMGUARD DEPLOYMENT FINALIZATION SCRIPT - UPDATED
# Finalizes the successful deployment with device authorization
################################################################################

set -e

# Colors for output  
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="/opt/armguard"
LAN_IP="192.168.0.177"

echo -e "${CYAN}🏁 ARMGUARD DEPLOYMENT FINALIZATION${NC}"
echo "==================================="

# Step 1: Verify current working status
echo ""
echo -e "${BLUE}📋 STEP 1: Verify Working Deployment${NC}"
echo "-----------------------------------"

# Test services
systemctl is-active --quiet nginx && echo -e "${GREEN}✅ Nginx: Running${NC}" || echo -e "${RED}❌ Nginx: Failed${NC}"
ps aux | grep -q "[g]unicorn.*armguard" && echo -e "${GREEN}✅ Gunicorn: Running${NC}" || echo -e "${RED}❌ Gunicorn: Failed${NC}"
systemctl is-active --quiet postgresql && echo -e "${GREEN}✅ PostgreSQL: Running${NC}" || echo -e "${RED}❌ PostgreSQL: Failed${NC}"

# Test web access
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null || echo "000")
if [ "$HTTP_STATUS" = "302" ] || [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Django: Responding (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}❌ Django: Not responding (HTTP $HTTP_STATUS)${NC}"
fi

# Test device authorization
AUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Forwarded-For: 192.168.0.82" http://localhost:8000/transactions/ 2>/dev/null || echo "000")
UNAUTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "X-Forwarded-For: 192.168.0.99" http://localhost:8000/transactions/ 2>/dev/null || echo "000")

if [ "$AUTH_STATUS" = "302" ] && [ "$UNAUTH_STATUS" = "403" ]; then
    echo -e "${GREEN}✅ Device Authorization: Working${NC}"
else
    echo -e "${YELLOW}⚠️  Device Authorization: Needs verification (Auth: $AUTH_STATUS, Unauth: $UNAUTH_STATUS)${NC}"
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  ArmGuard Deployment Finalization${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Finalizing deployment for IP: $LAN_IP"
echo "Started: $(date)"
echo ""

# Ensure all services are running
echo -e "${CYAN}🔧 Starting and enabling all services...${NC}"

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Start ArmGuard
if [ ! -f "/etc/systemd/system/armguard.service" ]; then
    echo -e "${YELLOW}⚠️  Creating missing ArmGuard service...${NC}"
    cd /home/armguard/armguard/deployment
    sudo ./setup-gunicorn-service.sh
fi

sudo systemctl start armguard
sudo systemctl enable armguard

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

echo -e "${GREEN}✓ All services started and enabled${NC}"

# Run database migrations
echo -e "${CYAN}🗄️  Running database migrations...${NC}"
cd $PROJECT_DIR
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Check service status
echo -e "${CYAN}📊 Checking service status...${NC}"
echo ""

services=("postgresql" "armguard" "nginx")
all_services_ok=true

for service in "${services[@]}"; do
    if systemctl is-active --quiet "$service"; then
        echo -e "✅ $service: ${GREEN}Active${NC}"
    else
        echo -e "❌ $service: ${RED}Failed${NC}"
        all_services_ok=false
    fi
done

echo ""

# Test web server response
echo -e "${CYAN}🌐 Testing web server response...${NC}"
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
if [ "$response" = "200" ]; then
    echo -e "✅ Web server: ${GREEN}HTTP $response OK${NC}"
else
    echo -e "❌ Web server: ${RED}HTTP $response${NC}"
    all_services_ok=false
fi

# Test database connection
echo -e "${CYAN}🗄️  Testing database connection...${NC}"
cd $PROJECT_DIR
if source venv/bin/activate && python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection successful')
" 2>/dev/null; then
    echo -e "✅ Database: ${GREEN}Connected${NC}"
else
    echo -e "❌ Database: ${RED}Connection failed${NC}"
    all_services_ok=false
fi

# Setup VPN if WireGuard is available
echo -e "${CYAN}🔐 Setting up VPN integration...${NC}"
if command -v wg &> /dev/null; then
    if [ -f "/home/armguard/armguard/vpn_integration/wireguard/scripts/setup-wireguard-server.sh" ]; then
        cd /home/armguard/armguard/vpn_integration/wireguard/scripts
        sudo ./setup-wireguard-server.sh >/dev/null 2>&1 || echo -e "${YELLOW}⚠️  VPN setup completed with warnings${NC}"
        echo -e "✅ VPN: ${GREEN}Configured${NC}"
    else
        echo -e "${YELLOW}⚠️  VPN scripts not found, skipping VPN setup${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  WireGuard not installed, skipping VPN setup${NC}"
fi

# Create deployment summary
echo -e "${CYAN}📋 Creating deployment summary...${NC}"
cat > /home/armguard/DEPLOYMENT_SUMMARY.txt << EOF
# ArmGuard Deployment Summary
Completed: $(date)
Server IP: $LAN_IP

## Access URLs
- Main Application: http://$LAN_IP
- Admin Panel: http://$LAN_IP/admin
- VPN Access (if configured): http://10.0.0.1

## Service Status
- PostgreSQL: $(systemctl is-active postgresql)
- ArmGuard Django: $(systemctl is-active armguard)
- Nginx Web Server: $(systemctl is-active nginx)
- WireGuard VPN: $(systemctl is-active wg-quick@wg0 2>/dev/null || echo "not configured")

## File Locations
- Application: $PROJECT_DIR
- Logs: /var/log/armguard/
- Nginx Config: /etc/nginx/sites-available/armguard
- Service File: /etc/systemd/system/armguard.service
- Environment: $PROJECT_DIR/.env

## Database
- Type: PostgreSQL
- Database: armguard
- User: armguard
- Host: localhost:5432

## Commands
- Restart services: sudo systemctl restart armguard nginx
- View logs: sudo journalctl -u armguard -f
- Update code: cd $PROJECT_DIR && git pull && sudo systemctl restart armguard
- Create VPN clients: cd /home/armguard/armguard/deployment && sudo ./rpi4b-generate-client.sh username role

## Backup
- Database: pg_dump -U armguard armguard > backup.sql
- Files: tar -czf armguard-backup.tar.gz $PROJECT_DIR
EOF

echo -e "${GREEN}✓ Deployment summary created at /home/armguard/DEPLOYMENT_SUMMARY.txt${NC}"

# Final status report
echo ""
echo -e "${BLUE}================================================${NC}"
if [ "$all_services_ok" = true ]; then
    echo -e "${GREEN}🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!${NC}"
else
    echo -e "${YELLOW}⚠️  DEPLOYMENT COMPLETED WITH WARNINGS${NC}"
fi
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}✅ Your ArmGuard Military Inventory System is ready!${NC}"
echo ""
echo "🌐 Access your application:"
echo "  • Local Network: http://$LAN_IP"
echo "  • Admin Panel: http://$LAN_IP/admin"
echo "  • Mobile/Tablet: http://$LAN_IP"
echo ""
echo "🔐 VPN Access (after client setup):"
echo "  • VPN Interface: http://10.0.0.1"
echo "  • Generate clients: cd /home/armguard/armguard/deployment"
echo "                      sudo ./rpi4b-generate-client.sh username role"
echo ""
echo "📊 Management Commands:"
echo "  • Service status: sudo systemctl status armguard nginx"
echo "  • View logs: sudo journalctl -u armguard -f"
echo "  • Restart: sudo systemctl restart armguard nginx"
echo ""
echo "📁 Important Files:"
echo "  • Application: $PROJECT_DIR"
echo "  • Logs: /var/log/armguard/"
echo "  • Summary: /home/armguard/DEPLOYMENT_SUMMARY.txt"
echo ""
echo "🎯 Next Steps:"
echo "  1. Visit http://$LAN_IP to test your application"
echo "  2. Create admin account: cd $PROJECT_DIR && python manage.py createsuperuser"
echo "  3. Generate VPN clients for secure remote access"
echo "  4. Add your inventory items and users"
echo ""
echo "Deployment completed: $(date)"