#!/bin/bash

################################################################################
# ArmGuard Complete Deployment Automation Script
# 
# This script automates the entire deployment process:
# - System updates and package installation
# - Python environment setup
# - Database configuration (SQLite or PostgreSQL)
# - Gunicorn service installation
# - Nginx configuration
# - SSL setup (mkcert for LAN or Let's Encrypt for public)
# - Firewall configuration
# - Security hardening
#
# Usage: sudo bash deployment/deploy-armguard.sh
################################################################################

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_NAME="armguard"
DEFAULT_PROJECT_DIR="/var/www/armguard"
DEFAULT_DOMAIN="armguard.local"
DEFAULT_RUN_USER="www-data"
DEFAULT_RUN_GROUP="www-data"
DEFAULT_USE_SSL="yes"
DEFAULT_SSL_TYPE="mkcert"  # or "letsencrypt"
DEFAULT_USE_POSTGRESQL="no"
DEFAULT_CONFIGURE_FIREWALL="yes"

# Print banner
print_banner() {
    clear
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║         ArmGuard Complete Deployment Automation           ║"
    echo "║                                                            ║"
    echo "║  This script will automatically deploy ArmGuard with:     ║"
    echo "║  • System packages and dependencies                       ║"
    echo "║  • Python virtual environment                             ║"
    echo "║  • Database (SQLite or PostgreSQL)                        ║"
    echo "║  • Gunicorn WSGI server                                   ║"
    echo "║  • Nginx reverse proxy                                    ║"
    echo "║  • SSL/HTTPS (mkcert or Let's Encrypt)                    ║"
    echo "║  • Firewall configuration                                 ║"
    echo "║  • Security hardening                                     ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
        exit 1
    fi
}

# Prompt for configuration
get_configuration() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Configuration Setup${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Press ENTER to accept defaults shown in [brackets]"
    echo ""
    
    # Project directory
    read -p "Project directory [${DEFAULT_PROJECT_DIR}]: " PROJECT_DIR
    PROJECT_DIR=${PROJECT_DIR:-$DEFAULT_PROJECT_DIR}
    
    # Domain name
    read -p "Domain name [${DEFAULT_DOMAIN}]: " DOMAIN
    DOMAIN=${DOMAIN:-$DEFAULT_DOMAIN}
    
    # Server IP (detect automatically)
    SERVER_IP=$(hostname -I | awk '{print $1}')
    read -p "Server IP address [${SERVER_IP}]: " INPUT_IP
    SERVER_IP=${INPUT_IP:-$SERVER_IP}
    
    # Run user
    read -p "Run as user [${DEFAULT_RUN_USER}]: " RUN_USER
    RUN_USER=${RUN_USER:-$DEFAULT_RUN_USER}
    
    read -p "Run as group [${DEFAULT_RUN_GROUP}]: " RUN_GROUP
    RUN_GROUP=${RUN_GROUP:-$DEFAULT_RUN_GROUP}
    
    # SSL configuration
    read -p "Configure SSL/HTTPS? [${DEFAULT_USE_SSL}]: " USE_SSL
    USE_SSL=${USE_SSL:-$DEFAULT_USE_SSL}
    
    if [[ "$USE_SSL" =~ ^[Yy] ]]; then
        echo ""
        echo "SSL Options:"
        echo "  1) mkcert (for LAN/local networks)"
        echo "  2) letsencrypt (for public domains)"
        read -p "Choose SSL type [1]: " SSL_CHOICE
        SSL_CHOICE=${SSL_CHOICE:-1}
        
        if [ "$SSL_CHOICE" == "2" ]; then
            SSL_TYPE="letsencrypt"
            read -p "Email for Let's Encrypt [admin@${DOMAIN}]: " LETSENCRYPT_EMAIL
            LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}
        else
            SSL_TYPE="mkcert"
        fi
    fi
    
    # Database configuration
    read -p "Use PostgreSQL? (no=SQLite) [${DEFAULT_USE_POSTGRESQL}]: " USE_POSTGRESQL
    USE_POSTGRESQL=${USE_POSTGRESQL:-$DEFAULT_USE_POSTGRESQL}
    
    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        read -p "Database name [armguard_db]: " DB_NAME
        DB_NAME=${DB_NAME:-armguard_db}
        
        read -p "Database user [armguard_user]: " DB_USER
        DB_USER=${DB_USER:-armguard_user}
        
        # Generate random password
        DB_PASSWORD=$(openssl rand -base64 24)
        echo -e "${YELLOW}Generated database password: ${DB_PASSWORD}${NC}"
        read -p "Press ENTER to accept or type custom password: " CUSTOM_DB_PASSWORD
        if [ ! -z "$CUSTOM_DB_PASSWORD" ]; then
            DB_PASSWORD="$CUSTOM_DB_PASSWORD"
        fi
    fi
    
    # Firewall
    read -p "Configure firewall (UFW)? [${DEFAULT_CONFIGURE_FIREWALL}]: " CONFIGURE_FIREWALL
    CONFIGURE_FIREWALL=${CONFIGURE_FIREWALL:-$DEFAULT_CONFIGURE_FIREWALL}
    
    # Calculate workers
    CPU_CORES=$(nproc)
    WORKERS=$((2 * CPU_CORES + 1))
    
    # Generate Django secret key
    DJANGO_SECRET_KEY=$(openssl rand -base64 50)
    
    # Admin URL (random)
    ADMIN_URL="admin-$(openssl rand -hex 8)"
    
    echo ""
    echo -e "${GREEN}Configuration Summary:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Project Directory:    ${PROJECT_DIR}"
    echo "Domain:               ${DOMAIN}"
    echo "Server IP:            ${SERVER_IP}"
    echo "Run User:             ${RUN_USER}:${RUN_GROUP}"
    echo "SSL:                  ${USE_SSL} (${SSL_TYPE})"
    echo "Database:             $([ "$USE_POSTGRESQL" =~ ^[Yy] ] && echo "PostgreSQL" || echo "SQLite")"
    echo "Firewall:             ${CONFIGURE_FIREWALL}"
    echo "Workers:              ${WORKERS}"
    echo "Admin URL:            /${ADMIN_URL}/"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "Continue with this configuration? (yes/no): " CONFIRM
    
    if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Deployment cancelled.${NC}"
        exit 0
    fi
}

# Step 1: System updates and package installation
install_system_packages() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 1: Installing System Packages${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}Updating package lists...${NC}"
    apt update -qq
    
    echo -e "${YELLOW}Installing required packages...${NC}"
    DEBIAN_FRONTEND=noninteractive apt install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        git \
        nginx \
        wget \
        curl \
        libjpeg-dev \
        zlib1g-dev \
        libnss3-tools \
        openssl \
        ufw \
        fail2ban
    
    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Installing PostgreSQL...${NC}"
        DEBIAN_FRONTEND=noninteractive apt install -y -qq postgresql postgresql-contrib
    fi
    
    echo -e "${GREEN}✓ System packages installed${NC}"
}

# Step 2: Check and clone/copy project
setup_project_directory() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 2: Setting Up Project Directory${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    if [ -d "$PROJECT_DIR" ] && [ -f "$PROJECT_DIR/manage.py" ]; then
        echo -e "${YELLOW}Project directory exists: ${PROJECT_DIR}${NC}"
    else
        # If running from within project, copy files
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [ -f "$SCRIPT_DIR/../manage.py" ]; then
            echo -e "${YELLOW}Copying project files to ${PROJECT_DIR}...${NC}"
            mkdir -p "$(dirname "$PROJECT_DIR")"
            cp -r "$SCRIPT_DIR/.." "$PROJECT_DIR"
        else
            echo -e "${YELLOW}Creating project directory: ${PROJECT_DIR}${NC}"
            mkdir -p "$PROJECT_DIR"
            echo -e "${YELLOW}Please copy your project files to ${PROJECT_DIR}${NC}"
            read -p "Press ENTER when ready..."
        fi
    fi
    
    cd "$PROJECT_DIR"
    
    # Verify manage.py exists
    if [ ! -f "manage.py" ]; then
        echo -e "${RED}ERROR: manage.py not found in ${PROJECT_DIR}${NC}"
        echo -e "${YELLOW}Current directory contents:${NC}"
        ls -la
        exit 1
    fi
    
    echo -e "${GREEN}✓ Project directory ready: ${PROJECT_DIR}${NC}"
}

# Step 3: Python environment setup
setup_python_environment() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 3: Setting Up Python Environment${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    cd "$PROJECT_DIR"
    
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv .venv
    fi
    
    echo -e "${YELLOW}Installing Python packages...${NC}"
    .venv/bin/pip install --upgrade pip -q
    .venv/bin/pip install -r requirements.txt -q
    
    echo -e "${GREEN}✓ Python environment ready${NC}"
}

# Step 4: Configure environment variables
configure_environment() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 4: Configuring Environment Variables${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    cd "$PROJECT_DIR"
    
    echo -e "${YELLOW}Creating .env file...${NC}"
    
    cat > .env <<EOF
# Generated by ArmGuard deployment automation
# Date: $(date)

# Django Core
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DJANGO_DEBUG=False
DJANGO_SETTINGS_MODULE=core.settings_production
DJANGO_ALLOWED_HOSTS=${DOMAIN},${SERVER_IP},localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://${SERVER_IP}

# Security
DJANGO_ADMIN_URL=${ADMIN_URL}
PASSWORD_MIN_LENGTH=12
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
RATELIMIT_ENABLE=True
RATELIMIT_REQUESTS_PER_MINUTE=60
AXES_ENABLED=True
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1
SESSION_COOKIE_AGE=3600

# File Upload
FILE_UPLOAD_MAX_MEMORY_SIZE=5242880
DATA_UPLOAD_MAX_MEMORY_SIZE=5242880
EOF

    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        cat >> .env <<EOF

# Database
USE_POSTGRESQL=True
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432
EOF
    else
        cat >> .env <<EOF

# Database
USE_POSTGRESQL=False
EOF
    fi
    
    cat >> .env <<EOF

# Logging
SECURITY_LOG_PATH=${PROJECT_DIR}/logs/security.log
ERROR_LOG_PATH=${PROJECT_DIR}/logs/errors.log
DJANGO_LOG_PATH=${PROJECT_DIR}/logs/django.log
EOF
    
    chmod 600 .env
    echo -e "${GREEN}✓ Environment configured${NC}"
}

# Step 5: Database setup
setup_database() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 5: Setting Up Database${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    cd "$PROJECT_DIR"
    
    # Create log directories FIRST (before running any Django commands)
    echo -e "${YELLOW}Creating log directories...${NC}"
    mkdir -p "${PROJECT_DIR}/logs"
    mkdir -p "/var/log/armguard"
    chown -R ${RUN_USER}:${RUN_GROUP} "${PROJECT_DIR}/logs"
    chown -R ${RUN_USER}:${RUN_GROUP} "/var/log/armguard"
    echo -e "${GREEN}✓ Log directories created${NC}"
    
    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Creating PostgreSQL database...${NC}"
        sudo -u postgres psql <<EOF
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';
ALTER ROLE ${DB_USER} SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF
        echo -e "${GREEN}✓ PostgreSQL database created${NC}"
    else
        echo -e "${YELLOW}Using SQLite database${NC}"
    fi
    
    echo -e "${YELLOW}Running migrations...${NC}"
    .venv/bin/python manage.py migrate --settings=core.settings_production
    
    echo -e "${YELLOW}Creating superuser...${NC}"
    echo "Create a superuser account for admin access:"
    .venv/bin/python manage.py createsuperuser --settings=core.settings_production
    
    echo -e "${YELLOW}Collecting static files...${NC}"
    .venv/bin/python manage.py collectstatic --noinput --settings=core.settings_production
    
    echo -e "${GREEN}✓ Database ready${NC}"
}

# Step 6: Install Gunicorn service
install_gunicorn_service() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 6: Installing Gunicorn Service${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}Creating systemd service...${NC}"
    
    cat > /etc/systemd/system/gunicorn-armguard.service <<EOF
[Unit]
Description=Gunicorn daemon for ArmGuard
Documentation=https://github.com/Stealth3535/armguard
After=network.target

[Service]
Type=exec
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=-${PROJECT_DIR}/.env

ExecStart=${PROJECT_DIR}/.venv/bin/gunicorn \\
          --workers ${WORKERS} \\
          --bind unix:/run/gunicorn-armguard.sock \\
          --timeout 60 \\
          --access-logfile /var/log/armguard/access.log \\
          --error-logfile /var/log/armguard/error.log \\
          --log-level info \\
          core.wsgi:application

Restart=always
RestartSec=3
PrivateTmp=true
NoNewPrivileges=true
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${YELLOW}Setting permissions...${NC}"
    chown -R ${RUN_USER}:${RUN_GROUP} "$PROJECT_DIR"
    
    echo -e "${YELLOW}Starting Gunicorn service...${NC}"
    systemctl daemon-reload
    systemctl start gunicorn-armguard
    systemctl enable gunicorn-armguard
    
    sleep 2
    if systemctl is-active --quiet gunicorn-armguard; then
        echo -e "${GREEN}✓ Gunicorn service running${NC}"
    else
        echo -e "${RED}✗ Gunicorn service failed to start${NC}"
        journalctl -u gunicorn-armguard -n 20
        exit 1
    fi
}

# Step 8: Configure Nginx
configure_nginx() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 7: Configuring Nginx${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}Creating Nginx configuration...${NC}"
    
    # HTTP configuration (will redirect to HTTPS if SSL is enabled)
    cat > /etc/nginx/sites-available/armguard <<EOF
# HTTP Server
server {
    listen 80;
    server_name ${DOMAIN} ${SERVER_IP};
EOF

    if [[ "$USE_SSL" =~ ^[Yy] ]]; then
        cat >> /etc/nginx/sites-available/armguard <<EOF
    return 301 https://\$server_name\$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name ${DOMAIN} ${SERVER_IP};
    
    # SSL certificates (will be configured in next step)
    # ssl_certificate will be added by SSL setup
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
EOF
    fi
    
    cat >> /etc/nginx/sites-available/armguard <<EOF
    
    # Static files
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
    
    # Media files
    location /media/ {
        alias ${PROJECT_DIR}/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Block hidden files
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_pass http://unix:/run/gunicorn-armguard.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # robots.txt
    location = /robots.txt {
        return 200 "User-agent: *\nDisallow: /\n";
    }
}
EOF
    
    # Enable site
    ln -sf /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    nginx -t
    
    echo -e "${GREEN}✓ Nginx configured${NC}"
}

# Step 9: SSL setup
setup_ssl() {
    if [[ ! "$USE_SSL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Skipping SSL setup${NC}"
        systemctl reload nginx
        return
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 8: Setting Up SSL/HTTPS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    if [ "$SSL_TYPE" == "letsencrypt" ]; then
        echo -e "${YELLOW}Installing Certbot...${NC}"
        apt install -y -qq certbot python3-certbot-nginx
        
        echo -e "${YELLOW}Obtaining Let's Encrypt certificate...${NC}"
        certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m ${LETSENCRYPT_EMAIL}
        
        echo -e "${GREEN}✓ Let's Encrypt SSL configured${NC}"
    else
        echo -e "${YELLOW}Installing mkcert...${NC}"
        wget -q https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
        mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
        chmod +x /usr/local/bin/mkcert
        
        echo -e "${YELLOW}Creating local CA...${NC}"
        mkcert -install
        
        echo -e "${YELLOW}Generating certificates...${NC}"
        mkdir -p /etc/ssl/armguard
        cd /etc/ssl/armguard
        mkcert ${SERVER_IP} ${DOMAIN} localhost 127.0.0.1
        
        # Update Nginx config with cert paths
        CERT_FILE=$(ls /etc/ssl/armguard/*.pem | grep -v key)
        KEY_FILE=$(ls /etc/ssl/armguard/*-key.pem)
        
        sed -i "/# ssl_certificate will be added/c\    ssl_certificate ${CERT_FILE};\n    ssl_certificate_key ${KEY_FILE};" \
            /etc/nginx/sites-available/armguard
        
        echo -e "${GREEN}✓ mkcert SSL configured${NC}"
        echo -e "${YELLOW}CA certificate location: ~/.local/share/mkcert/rootCA.pem${NC}"
        echo -e "${YELLOW}Install this on client devices to trust the certificate${NC}"
    fi
    
    systemctl reload nginx
}

# Step 10: Configure firewall
configure_firewall() {
    if [[ ! "$CONFIGURE_FIREWALL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Skipping firewall configuration${NC}"
        return
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 9: Configuring Firewall${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}Configuring UFW...${NC}"
    ufw --force reset
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw --force enable
    
    echo -e "${GREEN}✓ Firewall configured${NC}"
    ufw status
}

# Step 11: Configure Fail2Ban
configure_fail2ban() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 10: Configuring Fail2Ban${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}Creating Fail2Ban configuration...${NC}"
    
    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = 22

[nginx-http-auth]
enabled = true
port = http,https

[nginx-limit-req]
enabled = true
port = http,https
logpath = /var/log/nginx/error.log
EOF
    
    systemctl enable fail2ban
    systemctl restart fail2ban
    
    echo -e "${GREEN}✓ Fail2Ban configured${NC}"
}

# Final steps and summary
final_summary() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          ArmGuard Deployment Complete!                    ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✓ All components installed and configured${NC}"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Deployment Summary${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Application URL:      http${USE_SSL:+s}://${DOMAIN}"
    echo "                      http${USE_SSL:+s}://${SERVER_IP}"
    echo "Admin URL:            http${USE_SSL:+s}://${DOMAIN}/${ADMIN_URL}/"
    echo ""
    echo "Project Directory:    ${PROJECT_DIR}"
    echo "Virtual Environment:  ${PROJECT_DIR}/.venv"
    echo "Configuration:        ${PROJECT_DIR}/.env"
    echo ""
    echo "Gunicorn Service:     systemctl status gunicorn-armguard"
    echo "Nginx Service:        systemctl status nginx"
    echo "Application Logs:     /var/log/armguard/"
    echo ""
    
    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        echo "Database Type:        PostgreSQL"
        echo "Database Name:        ${DB_NAME}"
        echo "Database User:        ${DB_USER}"
        echo "Database Password:    ${DB_PASSWORD}"
        echo ""
    else
        echo "Database Type:        SQLite"
        echo "Database File:        ${PROJECT_DIR}/db.sqlite3"
        echo ""
    fi
    
    if [ "$SSL_TYPE" == "mkcert" ]; then
        echo -e "${YELLOW}Important: mkcert Certificate${NC}"
        echo "CA Certificate:       ~/.local/share/mkcert/rootCA.pem"
        echo "Install this certificate on client devices to trust HTTPS"
        echo ""
    fi
    
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Useful Commands${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "# Check service status"
    echo "sudo systemctl status gunicorn-armguard"
    echo "sudo systemctl status nginx"
    echo ""
    echo "# View logs"
    echo "sudo journalctl -u gunicorn-armguard -f"
    echo "sudo tail -f /var/log/armguard/access.log"
    echo "sudo tail -f /var/log/armguard/error.log"
    echo ""
    echo "# Restart services"
    echo "sudo systemctl restart gunicorn-armguard"
    echo "sudo systemctl reload nginx"
    echo ""
    echo "# Update application"
    echo "cd ${PROJECT_DIR}"
    echo "git pull"
    echo "source .venv/bin/activate"
    echo "pip install -r requirements.txt"
    echo "python manage.py migrate --settings=core.settings_production"
    echo "python manage.py collectstatic --noinput --settings=core.settings_production"
    echo "sudo systemctl restart gunicorn-armguard"
    echo ""
    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo ""
    
    # Save credentials to file
    cat > "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
ArmGuard Deployment Information
Generated: $(date)

Application URLs:
- Main: http${USE_SSL:+s}://${DOMAIN}
- IP: http${USE_SSL:+s}://${SERVER_IP}
- Admin: http${USE_SSL:+s}://${DOMAIN}/${ADMIN_URL}/

Configuration:
- Project: ${PROJECT_DIR}
- .env file: ${PROJECT_DIR}/.env
- Django Secret Key: ${DJANGO_SECRET_KEY}
- Admin URL Path: /${ADMIN_URL}/

Database:
$(if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
    echo "- Type: PostgreSQL"
    echo "- Name: ${DB_NAME}"
    echo "- User: ${DB_USER}"
    echo "- Password: ${DB_PASSWORD}"
else
    echo "- Type: SQLite"
    echo "- File: ${PROJECT_DIR}/db.sqlite3"
fi)

Services:
- Gunicorn: /etc/systemd/system/gunicorn-armguard.service
- Nginx: /etc/nginx/sites-available/armguard
- Logs: /var/log/armguard/

$(if [ "$SSL_TYPE" == "mkcert" ]; then
    echo "SSL (mkcert):"
    echo "- CA Certificate: ~/.local/share/mkcert/rootCA.pem"
    echo "- Install CA on client devices for trusted HTTPS"
fi)

IMPORTANT: Keep this file secure! It contains sensitive credentials.
EOF
    
    chmod 600 "${PROJECT_DIR}/DEPLOYMENT_INFO.txt"
    echo -e "${YELLOW}Deployment info saved to: ${PROJECT_DIR}/DEPLOYMENT_INFO.txt${NC}"
}

# Main execution
main() {
    print_banner
    check_root
    get_configuration
    
    install_system_packages
    setup_project_directory
    setup_python_environment
    configure_environment
    setup_database
    install_gunicorn_service
    configure_nginx
    setup_ssl
    configure_firewall
    configure_fail2ban
    
    final_summary
}

# Run main function
main
