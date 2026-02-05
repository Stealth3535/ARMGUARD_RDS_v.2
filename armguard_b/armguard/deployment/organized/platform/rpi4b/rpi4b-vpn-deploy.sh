#!/bin/bash

################################################################################
# ArmGuard Raspberry Pi 4B + VPN Integration Deployment Script
# 
# Deploys ArmGuard Django application on Raspberry Pi 4B with WireGuard VPN
# for secure remote access to local development server
#
# Usage: sudo ./rpi4b-vpn-deploy.sh
# Requirements: Raspberry Pi 4B, Raspberry Pi OS or Ubuntu Server
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
PROJECT_NAME="armguard"
PROJECT_DIR="/opt/armguard"
VENV_DIR="$PROJECT_DIR/venv"
LOG_FILE="/var/log/armguard/deployment.log"
NGINX_AVAILABLE="/etc/nginx/sites-available/$PROJECT_NAME"
NGINX_ENABLED="/etc/nginx/sites-enabled/$PROJECT_NAME"

# VPN Configuration
VPN_NET="10.0.0.0/24"
VPN_SERVER_IP="10.0.0.1"
VPN_PORT="51820"
VPN_INTERFACE="wg0"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Logging setup
mkdir -p /var/log/armguard
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  ArmGuard Raspberry Pi 4B + VPN Deployment${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Started: $(date)"
echo "Source: $SOURCE_DIR"
echo "Target: $PROJECT_DIR"
echo "Log: $LOG_FILE"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Detect Raspberry Pi
echo -e "${CYAN}🔍 Checking Raspberry Pi hardware...${NC}"
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo -e "${YELLOW}⚠️  Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    PI_MODEL=$(grep "Model" /proc/cpuinfo | cut -d: -f2 | xargs)
    echo -e "${GREEN}✓ Detected: $PI_MODEL${NC}"
fi

# Check memory
MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
if [ "$MEMORY_GB" -lt 2 ]; then
    echo -e "${YELLOW}⚠️  Warning: Low memory detected (${MEMORY_GB}GB). 4GB+ recommended.${NC}"
fi

echo ""

# Update system
echo -e "${CYAN}📦 Updating system packages...${NC}"
apt update
apt upgrade -y

# Install system dependencies in phases to avoid conflicts
echo -e "${CYAN}🔧 Installing system dependencies...${NC}"

# Phase 1: Core system packages
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    htop

# Phase 2: Development packages  
apt install -y \
    build-essential \
    python3-dev \
    libpython3-dev

# Phase 3: Web server packages
apt install -y \
    nginx-core \
    nginx-common

# Phase 4: Database and cache
apt install -y \
    postgresql-common \
    postgresql-client-common
apt install -y \
    postgresql \
    postgresql-contrib \
    redis-server

# Phase 5: Security tools (skip iptables-persistent due to ufw conflict)
apt install -y \
    fail2ban \
    supervisor

# Phase 6: VPN tools
apt install -y \
    wireguard \
    wireguard-tools \
    libqrencode4 \
    qrencode

echo -e "${GREEN}✓ System dependencies installed${NC}"

echo -e "${GREEN}✓ System dependencies installed${NC}"

# Create project directories
echo -e "${CYAN}📁 Creating project directories...${NC}"
mkdir -p $PROJECT_DIR/{logs,backups,static,media}
mkdir -p /var/www/armguard/{static,media}

# Copy project files
echo -e "${CYAN}📋 Copying project files...${NC}"
cp -r $SOURCE_DIR/* $PROJECT_DIR/
chown -R www-data:www-data $PROJECT_DIR
chown -R www-data:www-data /var/www/armguard

# Create Python virtual environment
echo -e "${CYAN}🐍 Setting up Python virtual environment...${NC}"
cd $PROJECT_DIR
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Install Python dependencies
echo -e "${CYAN}📚 Installing Python dependencies...${NC}"
$VENV_DIR/bin/pip install --upgrade pip
$VENV_DIR/bin/pip install -r requirements.txt
$VENV_DIR/bin/pip install gunicorn

# Setup environment file
echo -e "${CYAN}⚙️  Setting up environment configuration...${NC}"
if [ ! -f "$PROJECT_DIR/.env" ]; then
    SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    LAN_IP=$(hostname -I | cut -d' ' -f1)
    
    cat > $PROJECT_DIR/.env << EOF
# Django Configuration
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$LAN_IP,*.local,10.0.0.*

# Database Configuration (SQLite for development)
DATABASE_URL=sqlite:///$PROJECT_DIR/db.sqlite3
DB_NAME=armguard
DB_USER=armguard
DB_PASSWORD=armguard_secure_password
DB_HOST=localhost
DB_PORT=5432

# VPN Integration
WIREGUARD_ENABLED=True
VPN_NETWORK=$VPN_NET
VPN_SERVER_IP=$VPN_SERVER_IP

# Network Security
ENFORCE_LAN_TRANSACTIONS=True
LAN_SUBNET=192.168.0.0/16

# Additional Django settings
USE_SQLITE=True
DEBUG_TOOLBAR=False
EOF

    echo -e "${GREEN}✓ Created .env file with secure defaults${NC}"
else
    echo -e "${YELLOW}⚠️  .env file already exists, skipping...${NC}"
fi

# Setup database
echo -e "${CYAN}🗄️  Setting up database...${NC}"
cd $PROJECT_DIR
$VENV_DIR/bin/python manage.py migrate
echo -e "${GREEN}✓ Database migrations completed${NC}"

# Create superuser (interactive)
echo -e "${CYAN}👤 Creating superuser account...${NC}"
echo "Please create a superuser account for Django admin:"
$VENV_DIR/bin/python manage.py createsuperuser || echo "Superuser creation skipped"

# Collect static files
echo -e "${CYAN}📁 Collecting static files...${NC}"
$VENV_DIR/bin/python manage.py collectstatic --noinput
echo -e "${GREEN}✓ Static files collected${NC}"

# Setup Gunicorn service
echo -e "${CYAN}🔧 Setting up Gunicorn service...${NC}"
cat > /etc/systemd/system/armguard.service << EOF
[Unit]
Description=ArmGuard Django Application
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=armguard
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$VENV_DIR/bin
ExecStart=$VENV_DIR/bin/gunicorn --workers 3 --bind unix:/run/armguard/armguard.sock core.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStopSec=5
KillMode=mixed
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable armguard
systemctl start armguard
echo -e "${GREEN}✓ Gunicorn service configured and started${NC}"

# Setup Nginx configuration
echo -e "${CYAN}🌐 Setting up Nginx configuration...${NC}"
cat > $NGINX_AVAILABLE << EOF
server {
    listen 80;
    listen [::]:80;
    server_name localhost $LAN_IP *.local;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static/ {
        alias /var/www/armguard/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Media files
    location /media/ {
        alias /var/www/armguard/media/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }
    
    # Django application
    location / {
        proxy_pass http://unix:/run/armguard/armguard.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Increase timeout for development
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
EOF

# Enable Nginx site
ln -sf $NGINX_AVAILABLE $NGINX_ENABLED
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl restart nginx
echo -e "${GREEN}✓ Nginx configured and started${NC}"

# Setup VPN Integration
echo -e "${CYAN}🔐 Setting up VPN integration...${NC}"
if [ -f "$PROJECT_DIR/vpn_integration/wireguard/scripts/setup-wireguard-server.sh" ]; then
    cd $PROJECT_DIR/vpn_integration/wireguard/scripts
    chmod +x setup-wireguard-server.sh
    ./setup-wireguard-server.sh
    echo -e "${GREEN}✓ VPN server configured${NC}"
else
    echo -e "${YELLOW}⚠️  VPN scripts not found, skipping VPN setup${NC}"
fi

# Configure firewall (UFW is already installed and active)
echo -e "${CYAN}🛡️  Configuring firewall...${NC}"

# Check if UFW is active
if ufw status | grep -q "Status: active"; then
    echo "UFW is already active, updating rules..."
    ufw --force reset
fi

ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow $VPN_PORT/udp

# Enable UFW if not already enabled
if ! ufw status | grep -q "Status: active"; then
    ufw --force enable
fi

echo -e "${GREEN}✓ Firewall configured${NC}"

# Final status check
echo -e "${CYAN}🔍 Checking service status...${NC}"
echo ""
echo "Service Status:"
systemctl is-active armguard && echo -e "✅ ArmGuard: ${GREEN}Active${NC}" || echo -e "❌ ArmGuard: ${RED}Failed${NC}"
systemctl is-active nginx && echo -e "✅ Nginx: ${GREEN}Active${NC}" || echo -e "❌ Nginx: ${RED}Failed${NC}"
systemctl is-active wg-quick@wg0 && echo -e "✅ VPN: ${GREEN}Active${NC}" || echo -e "❌ VPN: ${RED}Not configured${NC}"

echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "🌐 Access URLs:"
echo "  Local:     http://localhost"
echo "  LAN:       http://$LAN_IP"
echo "  Admin:     http://$LAN_IP/admin"
echo ""
echo "📁 Project locations:"
echo "  Code:      $PROJECT_DIR"
echo "  Logs:      /var/log/armguard/"
echo "  Static:    /var/www/armguard/static/"
echo ""
echo "🔐 VPN Configuration:"
echo "  Network:   $VPN_NET"
echo "  Port:      $VPN_PORT"
echo "  Generate clients: cd $PROJECT_DIR/vpn_integration/wireguard/scripts"
echo ""
echo "🛠️  Next steps:"
echo "  1. Generate VPN client configs: ./generate-client-config.sh username role"
echo "  2. Access Django admin: http://$LAN_IP/admin"
echo "  3. Test VPN connection from remote device"
echo "  4. Review logs: tail -f /var/log/armguard/deployment.log"
echo ""
echo "Deployment completed: $(date)"