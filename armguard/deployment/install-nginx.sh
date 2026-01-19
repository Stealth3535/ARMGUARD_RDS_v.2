#!/bin/bash

#############################################################################
# ArmGuard - Nginx Installation and Configuration Script
# For Ubuntu Server (Raspberry Pi 5)
#############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="armguard"
APP_DIR="/var/www/armguard"
DOMAIN_NAME="${1:-armguard.local}"  # Default or first argument
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}   ArmGuard - Nginx Installation & Configuration Script    ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}[1/7]${NC} Updating system packages..."
apt-get update -qq

echo -e "${BLUE}[2/7]${NC} Installing Nginx..."
if ! command -v nginx &> /dev/null; then
    apt-get install -y nginx
    echo -e "${GREEN}✓ Nginx installed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Nginx already installed${NC}"
fi

echo -e "${BLUE}[3/7]${NC} Configuring firewall (UFW)..."
if command -v ufw &> /dev/null; then
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    echo -e "${GREEN}✓ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠ UFW not installed, skipping firewall configuration${NC}"
fi

echo -e "${BLUE}[4/7]${NC} Creating Nginx configuration..."

# Backup existing config if it exists
if [ -f "/etc/nginx/sites-available/${APP_NAME}" ]; then
    cp "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-available/${APP_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}⚠ Backed up existing configuration${NC}"
fi

# Create Nginx configuration
cat > "/etc/nginx/sites-available/${APP_NAME}" << 'NGINX_CONFIG'
upstream armguard_app {
    server unix:/var/www/armguard/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    
    server_name DOMAIN_NAME_PLACEHOLDER SERVER_IP_PLACEHOLDER;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Client body size limit (for file uploads)
    client_max_body_size 10M;
    
    # Logging
    access_log /var/log/nginx/armguard_access.log;
    error_log /var/log/nginx/armguard_error.log;
    
    # Static files
    location /static/ {
        alias /var/www/armguard/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /var/www/armguard/core/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://armguard_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Deny access to sensitive files
    location ~ /\.(?!well-known) {
        deny all;
    }
    
    location ~ /\.env {
        deny all;
    }
    
    location ~ /\.git {
        deny all;
    }
}
NGINX_CONFIG

# Replace placeholders
sed -i "s/DOMAIN_NAME_PLACEHOLDER/${DOMAIN_NAME}/g" "/etc/nginx/sites-available/${APP_NAME}"
sed -i "s/SERVER_IP_PLACEHOLDER/${SERVER_IP}/g" "/etc/nginx/sites-available/${APP_NAME}"

echo -e "${GREEN}✓ Nginx configuration created${NC}"

echo -e "${BLUE}[5/7]${NC} Enabling site configuration..."
# Remove existing symlink if it exists
if [ -L "/etc/nginx/sites-enabled/${APP_NAME}" ]; then
    rm "/etc/nginx/sites-enabled/${APP_NAME}"
fi

# Create symlink
ln -s "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/"

# Remove default site if it exists
if [ -L "/etc/nginx/sites-enabled/default" ]; then
    rm "/etc/nginx/sites-enabled/default"
    echo -e "${YELLOW}⚠ Removed default Nginx site${NC}"
fi

echo -e "${GREEN}✓ Site enabled${NC}"

echo -e "${BLUE}[6/7]${NC} Testing Nginx configuration..."
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed${NC}"
    exit 1
fi

echo -e "${BLUE}[7/7]${NC} Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx is running${NC}"
else
    echo -e "${RED}✗ Nginx failed to start${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}              Nginx Installation Complete!                  ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Configuration Details:${NC}"
echo -e "  • Domain: ${DOMAIN_NAME}"
echo -e "  • Server IP: ${SERVER_IP}"
echo -e "  • Config file: /etc/nginx/sites-available/${APP_NAME}"
echo -e "  • Access logs: /var/log/nginx/armguard_access.log"
echo -e "  • Error logs: /var/log/nginx/armguard_error.log"
echo ""
echo -e "${YELLOW}Access your application:${NC}"
echo -e "  • HTTP: http://${SERVER_IP}"
echo -e "  • HTTP: http://${DOMAIN_NAME} (if DNS configured)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Make sure Gunicorn is running: sudo systemctl status gunicorn"
echo -e "  2. Test the application in your browser"
echo -e "  3. Optional: Run install-mkcert-ssl.sh for HTTPS support"
echo ""
echo -e "${GREEN}✓ Nginx is ready to serve ArmGuard!${NC}"
