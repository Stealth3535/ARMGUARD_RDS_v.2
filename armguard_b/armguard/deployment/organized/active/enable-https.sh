#!/bin/bash

################################################################################
# ArmGuard HTTPS Setup Script
# Enables HTTPS/SSL for your ArmGuard system on Raspberry Pi
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LAN_IP="192.168.0.177"

echo -e "${CYAN}🔒 ARMGUARD HTTPS/SSL SETUP${NC}"
echo "============================"
echo ""

echo -e "${BLUE}📋 SSL Certificate Options:${NC}"
echo "1. 🔧 Self-signed certificate (Quick setup, browser warning)"
echo "2. 🏠 mkcert (Trusted local certificates)" 
echo "3. 🌐 Let's Encrypt (Production, requires domain name)"
echo ""

read -p "Choose option (1-3): " ssl_option

case $ssl_option in
    1)
        echo -e "${YELLOW}🔧 Setting up self-signed SSL certificate...${NC}"
        
        # Create SSL directory
        sudo mkdir -p /etc/ssl/armguard
        
        # Generate self-signed certificate
        sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout /etc/ssl/armguard/armguard.key \
            -out /etc/ssl/armguard/armguard.crt \
            -subj "/C=US/ST=State/L=City/O=ArmGuard/CN=$LAN_IP"
            
        echo -e "${GREEN}✅ Self-signed certificate created${NC}"
        ;;
        
    2)
        echo -e "${YELLOW}🏠 Setting up mkcert for trusted local certificates...${NC}"
        
        # Install mkcert
        if ! command -v mkcert &> /dev/null; then
            echo "Installing mkcert..."
            curl -JLO "https://dl.filippo.io/mkcert/latest?for=linux/arm64"
            chmod +x mkcert-v*-linux-arm64
            sudo mv mkcert-v*-linux-arm64 /usr/local/bin/mkcert
        fi
        
        # Create CA and certificates
        sudo mkdir -p /etc/ssl/armguard
        cd /tmp
        mkcert -install
        mkcert $LAN_IP localhost armguard.local
        
        # Move certificates to proper location
        sudo mv ./$LAN_IP+2.pem /etc/ssl/armguard/armguard.crt
        sudo mv ./$LAN_IP+2-key.pem /etc/ssl/armguard/armguard.key
        
        echo -e "${GREEN}✅ mkcert certificates created and trusted${NC}"
        ;;
        
    3)
        echo -e "${RED}❌ Let's Encrypt requires a domain name pointing to your Pi${NC}"
        echo "Please set up a domain first, then use certbot for Let's Encrypt"
        exit 1
        ;;
        
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}📝 Configuring Nginx for HTTPS...${NC}"

# Backup existing nginx config
sudo cp /etc/nginx/sites-available/armguard /etc/nginx/sites-available/armguard.http-backup

# Create HTTPS Nginx configuration
sudo tee /etc/nginx/sites-available/armguard > /dev/null << 'NGINXHTTPS'
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name 192.168.0.177 localhost;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name 192.168.0.177 localhost;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/armguard/armguard.crt;
    ssl_certificate_key /etc/ssl/armguard/armguard.key;
    
    # Strong SSL Security
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Increase proxy timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Static files
    location /static/ {
        alias /opt/armguard/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /opt/armguard/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Security
    location = /robots.txt {
        return 200 "User-agent: *\nDisallow: /admin/\nDisallow: /api/\n";
        add_header Content-Type text/plain;
    }
}
NGINXHTTPS

echo -e "${GREEN}✅ Nginx HTTPS configuration created${NC}"

echo ""
echo -e "${BLUE}🔧 Updating Django settings for HTTPS...${NC}"

# Update Django settings for HTTPS
cd /opt/armguard
source venv/bin/activate

python << 'PYHTTPS'
import re

# Read settings file
with open('core/settings.py', 'r') as f:
    content = f.read()

# Add HTTPS settings
https_settings = """

# HTTPS/SSL Configuration
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
"""

# Check if HTTPS settings already exist
if 'SECURE_SSL_REDIRECT' not in content:
    content = content.rstrip() + https_settings
    print("✅ Added HTTPS security settings to Django")
else:
    print("✅ HTTPS settings already present")

# Write back
with open('core/settings.py', 'w') as f:
    f.write(content)
PYHTTPS

echo -e "${GREEN}✅ Django HTTPS settings updated${NC}"

echo ""
echo -e "${BLUE}🔄 Restarting services...${NC}"

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx

# Restart armguard
sudo systemctl restart armguard

echo -e "${GREEN}✅ Services restarted${NC}"

# Wait for services to start
sleep 10

echo ""
echo -e "${BLUE}🧪 Testing HTTPS setup...${NC}"

# Test HTTPS
HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost 2>/dev/null || echo "000")
HTTP_REDIRECT=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")

echo "HTTPS test: HTTP $HTTPS_STATUS"
echo "HTTP redirect test: HTTP $HTTP_REDIRECT"

echo ""
if [ "$HTTPS_STATUS" = "200" ] || [ "$HTTPS_STATUS" = "302" ]; then
    echo -e "${GREEN}🎉 SUCCESS! HTTPS is now enabled${NC}"
    echo ""
    echo -e "${CYAN}🔒 Your ArmGuard system is now secured with HTTPS:${NC}"
    echo ""
    echo "🌐 HTTPS Access: https://$LAN_IP"
    echo "🔐 Admin Panel: https://$LAN_IP/admin/"
    echo "📱 Mobile Access: https://$LAN_IP"
    echo ""
    if [ "$ssl_option" = "1" ]; then
        echo -e "${YELLOW}⚠️  Note: Self-signed certificate will show browser warning${NC}"
        echo "   Click 'Advanced' → 'Proceed to site' to access"
    fi
    echo ""
    echo -e "${GREEN}✅ HTTP traffic automatically redirects to HTTPS${NC}"
    echo -e "${GREEN}✅ Strong SSL security headers enabled${NC}"
    echo -e "${GREEN}✅ All cookies secured for HTTPS${NC}"
    
else
    echo -e "${RED}❌ HTTPS setup may have issues${NC}"
    echo ""
    echo "🔍 Troubleshooting:"
    echo "  • Check nginx: sudo nginx -t"
    echo "  • Check logs: sudo journalctl -u nginx -f"
    echo "  • Check service: sudo systemctl status nginx armguard"
    echo ""
    echo "🔄 Rollback if needed:"
    echo "  sudo cp /etc/nginx/sites-available/armguard.http-backup /etc/nginx/sites-available/armguard"
    echo "  sudo systemctl restart nginx"
fi

echo ""
echo -e "${BLUE}📋 HTTPS Setup Complete!${NC}"
echo "Configuration files:"
echo "  • Nginx HTTPS config: /etc/nginx/sites-available/armguard"
echo "  • SSL certificates: /etc/ssl/armguard/"
echo "  • Backup HTTP config: /etc/nginx/sites-available/armguard.http-backup"