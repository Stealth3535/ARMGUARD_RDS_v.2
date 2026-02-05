#!/bin/bash

#############################################################################
# ArmGuard - Enhanced Nginx Installation with Security Features
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
DOMAIN_NAME="${1:-armguard.local}"
SERVER_IP=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   ArmGuard - Enhanced Nginx Installation & Configuration  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}[1/8]${NC} Updating system packages..."
apt-get update -qq

echo -e "${BLUE}[2/8]${NC} Installing Nginx..."
if ! command -v nginx &> /dev/null; then
    apt-get install -y nginx
    echo -e "${GREEN}✓ Nginx installed successfully${NC}"
else
    echo -e "${YELLOW}⚠ Nginx already installed${NC}"
fi

echo -e "${BLUE}[3/8]${NC} Configuring firewall (UFW)..."
if command -v ufw &> /dev/null; then
    ufw allow 'Nginx Full'
    ufw allow OpenSSH
    echo -e "${GREEN}✓ Firewall configured${NC}"
else
    echo -e "${YELLOW}⚠ UFW not installed, skipping firewall configuration${NC}"
fi

echo -e "${BLUE}[4/8]${NC} Creating rate limiting zones..."
# Create rate limiting configuration directory
mkdir -p /etc/nginx/conf.d

echo -e "${BLUE}[5/8]${NC} Creating enhanced Nginx configuration..."

# Backup existing config if it exists
if [ -f "/etc/nginx/sites-available/${APP_NAME}" ]; then
    cp "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-available/${APP_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}⚠ Backed up existing configuration${NC}"
fi

# Create enhanced Nginx configuration with security features
cat > "/etc/nginx/sites-available/${APP_NAME}" << 'NGINX_CONFIG'
# Rate limiting zones
limit_req_zone $binary_remote_addr zone=armguard_general:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=armguard_login:10m rate=5r/m;
limit_req_zone $binary_remote_addr zone=armguard_api:10m rate=20r/s;

# Connection limiting
limit_conn_zone $binary_remote_addr zone=armguard_conn:10m;

upstream armguard_app {
    server unix:/run/gunicorn-armguard.sock fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    
    server_name DOMAIN_NAME_PLACEHOLDER SERVER_IP_PLACEHOLDER;
    
    # Security headers (MEDIUM-6 fix: Comprehensive security headers)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=(), payment=(), usb=()" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'self';" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Cross-Origin-Opener-Policy "same-origin" always;
    add_header Cross-Origin-Resource-Policy "same-origin" always;
    
    # Hide server version
    server_tokens off;
    
    # Client settings
    client_max_body_size 10M;
    client_body_timeout 30s;
    client_header_timeout 30s;
    
    # Connection limit: max 10 connections per IP
    limit_conn armguard_conn 10;
    
    # Logging
    access_log /var/log/nginx/armguard_access.log;
    error_log /var/log/nginx/armguard_error.log;
    
    # Block common exploits
    location ~* (\.php|\.asp|\.aspx|\.jsp)$ {
        return 444;  # Close connection without response
    }
    
    # Block access to hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Static files with caching
    location /static/ {
        alias /var/www/armguard/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # Security headers for static files
        add_header X-Content-Type-Options "nosniff" always;
        
        # Rate limit static files (generous)
        limit_req zone=armguard_general burst=50 nodelay;
    }
    
    # Media files with caching
    location /media/ {
        alias /var/www/armguard/core/media/;
        expires 7d;
        add_header Cache-Control "public";
        
        # Security headers for media files
        add_header X-Content-Type-Options "nosniff" always;
        
        # Rate limit media files
        limit_req zone=armguard_general burst=30 nodelay;
    }
    
    # Admin panel - stricter rate limiting
    location ~* ^/admin.*$ {
        # Very strict rate limiting for admin
        limit_req zone=armguard_login burst=5 nodelay;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://armguard_app;
    }
    
    # Authentication endpoints - strict rate limiting
    location ~* ^/(login|logout|password_reset|register).*$ {
        limit_req zone=armguard_login burst=3 nodelay;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://armguard_app;
    }
    
    # API endpoints - moderate rate limiting
    location /api/ {
        limit_req zone=armguard_api burst=10 nodelay;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://armguard_app;
    }
    
    # Main application
    location / {
        # General rate limiting
        limit_req zone=armguard_general burst=20 nodelay;
        
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://armguard_app;
    }
    
    # Health check endpoint (no rate limiting)
    location /health/ {
        access_log off;
        proxy_pass http://armguard_app;
    }
}
NGINX_CONFIG

# Replace placeholders
sed -i "s/DOMAIN_NAME_PLACEHOLDER/${DOMAIN_NAME}/g" "/etc/nginx/sites-available/${APP_NAME}"
sed -i "s/SERVER_IP_PLACEHOLDER/${SERVER_IP}/g" "/etc/nginx/sites-available/${APP_NAME}"

echo -e "${GREEN}✓ Enhanced configuration created${NC}"

echo -e "${BLUE}[6/8]${NC} Enabling site configuration..."
ln -sf "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-enabled/${APP_NAME}"
echo -e "${GREEN}✓ Site enabled${NC}"

echo -e "${BLUE}[7/8]${NC} Testing Nginx configuration..."
if nginx -t; then
    echo -e "${GREEN}✓ Configuration test passed${NC}"
else
    echo -e "${RED}✗ Configuration test failed${NC}"
    exit 1
fi

echo -e "${BLUE}[8/8]${NC} Restarting Nginx..."
systemctl restart nginx
systemctl enable nginx
echo -e "${GREEN}✓ Nginx restarted and enabled${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          Nginx Installation Complete                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${BLUE}Security Features Enabled:${NC}"
echo "  ${GREEN}✓${NC} Rate limiting (general, login, API)"
echo "  ${GREEN}✓${NC} Connection limiting (10 per IP)"
echo "  ${GREEN}✓${NC} Security headers (XSS, CSRF, Frame protection)"
echo "  ${GREEN}✓${NC} Common exploit blocking"
echo "  ${GREEN}✓${NC} Hidden file protection"
echo "  ${GREEN}✓${NC} Strict admin panel rate limiting"
echo ""

echo -e "${BLUE}Rate Limits:${NC}"
echo "  General pages:     10 requests/second (burst: 20)"
echo "  Login/Auth:        5 requests/minute (burst: 3)"
echo "  API endpoints:     20 requests/second (burst: 10)"
echo "  Admin panel:       5 requests/minute (burst: 5)"
echo "  Max connections:   10 per IP"
echo ""

echo -e "${BLUE}Access URLs:${NC}"
echo "  HTTP:  http://${DOMAIN_NAME}"
echo "  HTTP:  http://${SERVER_IP}"
echo ""

echo -e "${BLUE}Service Commands:${NC}"
echo "  Status:    sudo systemctl status nginx"
echo "  Restart:   sudo systemctl restart nginx"
echo "  Logs:      sudo tail -f /var/log/nginx/armguard_error.log"
echo "  Test:      sudo nginx -t"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Test HTTP access: curl http://${SERVER_IP}"
echo "  2. Install SSL: sudo bash deployment/install-mkcert-ssl.sh"
echo "  3. Monitor logs: sudo tail -f /var/log/nginx/armguard_access.log"
echo ""
