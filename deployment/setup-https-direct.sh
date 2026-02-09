#!/bin/bash
# ===========================================
# ArmGuard HTTPS Direct Access Setup
# ⚠️ MODERATE RISK - Use only with proper security
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DOMAIN_OR_IP=""
HTTPS_PORT="8443"
HTTP_PORT="8000"
SSL_DIR="/etc/armguard/ssl"
NGINX_AVAILABLE="/etc/nginx/sites-available"
NGINX_ENABLED="/etc/nginx/sites-enabled"
ARMGUARD_DIR="/home/rds/ARMGUARD_RDS_v.2"

echo -e "${RED}⚠️ WARNING: HTTPS Direct Access Setup${NC}"
echo -e "${YELLOW}This exposes ArmGuard directly to the internet!${NC}"
echo -e "${BLUE}Recommended: Use VPN or SSH tunnel instead${NC}"
echo "=================================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Get domain or IP
if [ -z "$DOMAIN_OR_IP" ]; then
    echo -e "${YELLOW}🌐 Enter your public IP address or domain name:${NC}"
    read -p "Domain/IP: " DOMAIN_OR_IP
    
    if [ -z "$DOMAIN_OR_IP" ]; then
        echo -e "${RED}❌ Domain or IP is required${NC}"
        exit 1
    fi
fi

# Install required packages
echo -e "${YELLOW}📦 Installing required packages...${NC}"
apt update
apt install -y nginx certbot python3-certbot-nginx fail2ban ufw openssl

# Create SSL directory
echo -e "${YELLOW}🔐 Setting up SSL certificates...${NC}"
mkdir -p $SSL_DIR
chmod 700 $SSL_DIR

# Check if domain is provided for Let's Encrypt, otherwise use self-signed
if [[ "$DOMAIN_OR_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${YELLOW}📝 IP address detected, creating self-signed certificate...${NC}"
    
    # Generate self-signed certificate
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $SSL_DIR/armguard.key \
        -out $SSL_DIR/armguard.crt \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_OR_IP"
    
    SSL_CERT="$SSL_DIR/armguard.crt"
    SSL_KEY="$SSL_DIR/armguard.key"
    
    echo -e "${YELLOW}⚠️ Self-signed certificate created${NC}"
    echo -e "${BLUE}💡 Browsers will show security warning - this is normal${NC}"
else
    echo -e "${YELLOW}📝 Domain detected, attempting Let's Encrypt certificate...${NC}"
    
    # Try to get Let's Encrypt certificate
    if certbot certonly --standalone -d "$DOMAIN_OR_IP" --non-interactive --agree-tos --email admin@$DOMAIN_OR_IP; then
        SSL_CERT="/etc/letsencrypt/live/$DOMAIN_OR_IP/fullchain.pem"
        SSL_KEY="/etc/letsencrypt/live/$DOMAIN_OR_IP/privkey.pem"
        echo -e "${GREEN}✅ Let's Encrypt certificate obtained${NC}"
    else
        echo -e "${YELLOW}⚠️ Let's Encrypt failed, creating self-signed certificate...${NC}"
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout $SSL_DIR/armguard.key \
            -out $SSL_DIR/armguard.crt \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_OR_IP"
        
        SSL_CERT="$SSL_DIR/armguard.crt"
        SSL_KEY="$SSL_DIR/armguard.key"
    fi
fi

# Create Nginx configuration
echo -e "${YELLOW}🌐 Configuring Nginx reverse proxy...${NC}"
cat > $NGINX_AVAILABLE/armguard << EOF
# ArmGuard HTTPS Configuration
server {
    listen 80;
    server_name $DOMAIN_OR_IP;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen $HTTPS_PORT ssl http2;
    server_name $DOMAIN_OR_IP;

    # SSL Configuration
    ssl_certificate $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS (ngx_http_headers_module is required) (63072000 seconds)
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self';";

    # Rate limiting
    limit_req_zone \$binary_remote_addr zone=armguard:10m rate=10r/m;
    limit_req zone=armguard burst=5 nodelay;

    # Client max body size for file uploads
    client_max_body_size 10M;

    # Hide Nginx version
    server_tokens off;

    location / {
        proxy_pass http://127.0.0.1:$HTTP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support for Django Channels
    location /ws/ {
        proxy_pass http://127.0.0.1:$HTTP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket timeouts
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    # Static files
    location /static/ {
        alias $ARMGUARD_DIR/armguard/core/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias $ARMGUARD_DIR/armguard/core/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # Deny access to sensitive files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }

    location ~ \.(git|svn|env)$ {
        deny all;
        access_log off;
        log_not_found off;
    }
}
EOF

# Enable Nginx site
ln -sf $NGINX_AVAILABLE/armguard $NGINX_ENABLED/
rm -f $NGINX_ENABLED/default

# Test Nginx configuration
if nginx -t; then
    echo -e "${GREEN}✅ Nginx configuration valid${NC}"
else
    echo -e "${RED}❌ Nginx configuration error${NC}"
    exit 1
fi

# Configure firewall
echo -e "${YELLOW}🛡️ Configuring firewall...${NC}"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow $HTTPS_PORT/tcp
ufw --force enable

# Configure fail2ban
echo -e "${YELLOW}🚨 Setting up fail2ban protection...${NC}"
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
ignoreip = 127.0.0.1/8 ::1

[nginx-http-auth]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log

[nginx-noscript]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 6

[nginx-badbots]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2

[nginx-noproxy]
enabled = true
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

# Create Django production settings
echo -e "${YELLOW}⚙️ Updating Django security settings...${NC}"
cat >> $ARMGUARD_DIR/armguard/core/settings_production.py << 'EOF'

# HTTPS Security Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Additional Security Headers
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

EOF

# Create systemd service for ArmGuard
echo -e "${YELLOW}🚀 Creating ArmGuard systemd service...${NC}"
cat > /etc/systemd/system/armguard.service << EOF
[Unit]
Description=ArmGuard Application
After=network.target

[Service]
Type=simple
User=rds
Group=rds
WorkingDirectory=$ARMGUARD_DIR/armguard
Environment=PATH=$ARMGUARD_DIR/venv/bin
Environment=DJANGO_SETTINGS_MODULE=core.settings_production
ExecStart=$ARMGUARD_DIR/venv/bin/python manage.py runserver 127.0.0.1:$HTTP_PORT
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start services
echo -e "${YELLOW}🚀 Starting services...${NC}"
systemctl daemon-reload
systemctl enable armguard
systemctl start armguard
systemctl enable nginx
systemctl restart nginx
systemctl enable fail2ban
systemctl start fail2ban

# Wait for services to start
sleep 5

# Check service status
echo -e "${BLUE}🔍 Service Status Check:${NC}"
if systemctl is-active --quiet armguard; then
    echo -e "${GREEN}✅ ArmGuard service is running${NC}"
else
    echo -e "${RED}❌ ArmGuard service failed to start${NC}"
    systemctl status armguard --no-pager
fi

if systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Nginx service is running${NC}"
else
    echo -e "${RED}❌ Nginx service failed to start${NC}"
fi

if systemctl is-active --quiet fail2ban; then
    echo -e "${GREEN}✅ Fail2ban service is running${NC}"
else
    echo -e "${RED}❌ Fail2ban service failed to start${NC}"
fi

# Display setup completion
echo ""
echo -e "${GREEN}🎉 HTTPS Direct Access Setup Complete!${NC}"
echo "================================================="
echo -e "${BLUE}📋 Access Information:${NC}"
echo "   🌐 HTTPS URL: https://$DOMAIN_OR_IP:$HTTPS_PORT"
echo "   🔒 HTTP redirects to HTTPS automatically"
echo ""
echo -e "${YELLOW}⚠️ Next Steps:${NC}"
echo "1. Forward port $HTTPS_PORT (TCP) on your router to 192.168.0.10"
echo "2. Forward port 80 (TCP) for HTTP redirect"
echo "3. Test access from external network"
echo ""
echo -e "${RED}🛡️ Security Reminders:${NC}"
echo "• Monitor fail2ban logs: sudo fail2ban-client status"
echo "• Check Nginx logs: sudo tail -f /var/log/nginx/access.log"
echo "• Update SSL certificates before expiry"
echo "• Use strong passwords and enable 2FA"
echo "• Monitor system logs regularly"
echo "• Consider using VPN instead for maximum security"
echo ""
echo -e "${BLUE}🔧 Management Commands:${NC}"
echo "• Restart ArmGuard: sudo systemctl restart armguard"
echo "• Check logs: sudo journalctl -f -u armguard"
echo "• Reload Nginx: sudo systemctl reload nginx"