#!/bin/bash

#############################################################################
# ArmGuard - mkcert SSL/TLS Installation Script
# Installs mkcert and generates self-signed certificates for local development
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
DOMAIN_NAME="${1:-armguard.local}"
SERVER_IP=$(hostname -I | awk '{print $1}')
CERT_DIR="/etc/ssl/armguard"

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}      ArmGuard - mkcert SSL/TLS Installation Script        ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}[1/8]${NC} Checking prerequisites..."
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}✗ Nginx is not installed. Please run install-nginx.sh first.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Nginx detected${NC}"

echo -e "${BLUE}[2/8]${NC} Installing mkcert dependencies..."
apt-get update -qq
apt-get install -y wget libnss3-tools

echo -e "${BLUE}[3/8]${NC} Installing mkcert..."
if ! command -v mkcert &> /dev/null; then
    # Detect architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-arm64"
    elif [ "$ARCH" = "armv7l" ]; then
        MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-arm"
    else
        MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-amd64"
    fi
    
    wget -q "$MKCERT_URL" -O /usr/local/bin/mkcert
    chmod +x /usr/local/bin/mkcert
    echo -e "${GREEN}✓ mkcert installed successfully${NC}"
else
    echo -e "${YELLOW}⚠ mkcert already installed${NC}"
fi

echo -e "${BLUE}[4/8]${NC} Installing local Certificate Authority (CA)..."
mkcert -install
echo -e "${GREEN}✓ Local CA installed${NC}"

echo -e "${BLUE}[5/8]${NC} Creating certificate directory..."
mkdir -p "$CERT_DIR"
echo -e "${GREEN}✓ Certificate directory created: $CERT_DIR${NC}"

echo -e "${BLUE}[6/8]${NC} Generating SSL certificates..."
cd "$CERT_DIR"

# Generate certificates for domain and IP
mkcert -key-file "${CERT_DIR}/${APP_NAME}-key.pem" \
       -cert-file "${CERT_DIR}/${APP_NAME}-cert.pem" \
       "${DOMAIN_NAME}" \
       "localhost" \
       "127.0.0.1" \
       "${SERVER_IP}" \
       "::1"

# Set proper permissions
chmod 644 "${CERT_DIR}/${APP_NAME}-cert.pem"
chmod 600 "${CERT_DIR}/${APP_NAME}-key.pem"

echo -e "${GREEN}✓ SSL certificates generated${NC}"

echo -e "${BLUE}[7/8]${NC} Configuring Nginx for HTTPS..."

# Backup existing config
if [ -f "/etc/nginx/sites-available/${APP_NAME}" ]; then
    cp "/etc/nginx/sites-available/${APP_NAME}" "/etc/nginx/sites-available/${APP_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Create HTTPS-enabled Nginx configuration
cat > "/etc/nginx/sites-available/${APP_NAME}" << 'NGINX_SSL_CONFIG'
upstream armguard_app {
    server unix:/var/www/armguard/gunicorn.sock fail_timeout=0;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    
    server_name DOMAIN_NAME_PLACEHOLDER SERVER_IP_PLACEHOLDER;
    
    # Redirect all HTTP requests to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    
    server_name DOMAIN_NAME_PLACEHOLDER SERVER_IP_PLACEHOLDER;
    
    # SSL Configuration
    ssl_certificate /etc/ssl/armguard/armguard-cert.pem;
    ssl_certificate_key /etc/ssl/armguard/armguard-key.pem;
    
    # SSL Security Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_session_tickets off;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
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
NGINX_SSL_CONFIG

# Replace placeholders
sed -i "s/DOMAIN_NAME_PLACEHOLDER/${DOMAIN_NAME}/g" "/etc/nginx/sites-available/${APP_NAME}"
sed -i "s/SERVER_IP_PLACEHOLDER/${SERVER_IP}/g" "/etc/nginx/sites-available/${APP_NAME}"

echo -e "${GREEN}✓ Nginx HTTPS configuration created${NC}"

echo -e "${BLUE}[8/8]${NC} Testing and restarting Nginx..."
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    systemctl restart nginx
    echo -e "${GREEN}✓ Nginx restarted with HTTPS enabled${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed${NC}"
    echo -e "${YELLOW}⚠ Restoring backup configuration...${NC}"
    cp "/etc/nginx/sites-available/${APP_NAME}.backup.$(date +%Y%m%d)_"* "/etc/nginx/sites-available/${APP_NAME}" 2>/dev/null || true
    systemctl restart nginx
    exit 1
fi

# Get CA certificate location for client installation
CA_CERT_LOCATION=$(mkcert -CAROOT)

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}            mkcert SSL Installation Complete!               ${GREEN}║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Certificate Details:${NC}"
echo -e "  • Domain: ${DOMAIN_NAME}"
echo -e "  • Server IP: ${SERVER_IP}"
echo -e "  • Certificate: ${CERT_DIR}/${APP_NAME}-cert.pem"
echo -e "  • Private Key: ${CERT_DIR}/${APP_NAME}-key.pem"
echo -e "  • CA Root: ${CA_CERT_LOCATION}"
echo ""
echo -e "${YELLOW}Access your application with HTTPS:${NC}"
echo -e "  • HTTPS: https://${SERVER_IP}"
echo -e "  • HTTPS: https://${DOMAIN_NAME} (if DNS configured)"
echo -e "  • HTTP requests will automatically redirect to HTTPS"
echo ""
echo -e "${YELLOW}Client Device Setup (to trust the certificate):${NC}"
echo -e "  ${BLUE}For Desktop/Laptop:${NC}"
echo -e "    1. Copy CA certificate from: ${CA_CERT_LOCATION}/rootCA.pem"
echo -e "    2. Import it into your browser/system trust store"
echo ""
echo -e "  ${BLUE}For Mobile Devices:${NC}"
echo -e "    1. Copy ${CA_CERT_LOCATION}/rootCA.pem to your device"
echo -e "    2. Install it as a trusted certificate"
echo -e "    3. Android: Settings → Security → Install from storage"
echo -e "    4. iOS: Settings → General → VPN & Device Management"
echo ""
echo -e "  ${BLUE}Quick copy command:${NC}"
echo -e "    cat ${CA_CERT_LOCATION}/rootCA.pem"
echo ""
echo -e "${YELLOW}Django Configuration:${NC}"
echo -e "  Update your .env file with:"
echo -e "    SECURE_SSL_REDIRECT=True"
echo -e "    SESSION_COOKIE_SECURE=True"
echo -e "    CSRF_COOKIE_SECURE=True"
echo -e "    SECURE_HSTS_SECONDS=31536000"
echo ""
echo -e "${GREEN}✓ HTTPS is now enabled for ArmGuard!${NC}"
echo ""
echo -e "${YELLOW}Note: mkcert certificates are for local development only.${NC}"
echo -e "${YELLOW}For production, use Let's Encrypt (certbot) instead.${NC}"
