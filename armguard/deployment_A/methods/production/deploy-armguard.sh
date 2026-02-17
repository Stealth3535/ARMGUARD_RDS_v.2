#!/bin/bash

################################################################################
# ArmGuard Complete Deployment Automation Script - Enhanced Security Edition
# 
# This script automates the entire deployment process with enhanced security:
# - System updates and package installation
# - Python environment setup
# - Database configuration (SQLite or PostgreSQL)
# - Gunicorn service installation
# - Nginx configuration with security headers
# - SSL setup (mkcert for LAN or Let's Encrypt for public)
# - Firewall configuration
# - Security hardening and rate limiting
# - Admin restriction system setup
# - Security logging configuration
#
# Usage: sudo bash deployment/deploy-armguard.sh
################################################################################

set -e  # Exit on any error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
PROJECT_NAME="armguard"
DEFAULT_PROJECT_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard"
DEFAULT_DOMAIN="armguard.local"
DEFAULT_RUN_USER="rds"
DEFAULT_RUN_GROUP="rds"
DEFAULT_USE_SSL="yes"
DEFAULT_SSL_TYPE="mkcert"  # or "letsencrypt"
DEFAULT_USE_POSTGRESQL="no"
DEFAULT_CONFIGURE_FIREWALL="yes"
REDIS_TUNE_MODE="${REDIS_TUNE_MODE:-idempotent}"
CREATE_SUPERUSER="${CREATE_SUPERUSER:-prompt}"

# Print banner
print_banner() {
    clear
    echo -e "${GREEN}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║      ArmGuard Enhanced Security Deployment Automation     ║"
    echo "║                                                            ║"
    echo "║  This script will automatically deploy ArmGuard with:     ║"
    echo "║  • Enhanced security middleware and headers               ║"
    echo "║  • Rate limiting and brute force protection              ║"
    echo "║  • Admin restriction system                              ║"
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
    
    # Auto-detect project directory from git repository
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DETECTED_PROJECT_DIR=""
    SEARCH_DIR="$SCRIPT_DIR"
    
    # Look for manage.py in parent directories (up to 5 levels)
    for i in {1..5}; do
        if [ -f "$SEARCH_DIR/manage.py" ]; then
            DETECTED_PROJECT_DIR="$SEARCH_DIR"
            break
        fi
        SEARCH_DIR="$(dirname "$SEARCH_DIR")"
    done
    
    # If project detected, check if it's a git repository
    if [ -n "$DETECTED_PROJECT_DIR" ]; then
        if [ -d "$DETECTED_PROJECT_DIR/.git" ] || git -C "$DETECTED_PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Git repository detected at: ${DETECTED_PROJECT_DIR}${NC}"
            echo -e "${CYAN}  Using existing repository (enables easy updates with 'git pull')${NC}"
            echo ""
            DEFAULT_PROJECT_DIR="$DETECTED_PROJECT_DIR"
        fi
    fi
    
    # Project directory
    read -p "Project directory [${DEFAULT_PROJECT_DIR}]: " PROJECT_DIR
    PROJECT_DIR=${PROJECT_DIR:-$DEFAULT_PROJECT_DIR}
    
    # Auto-detect run user based on project location
    # If project is in /home/username/, use that username instead of www-data
    if [[ "$PROJECT_DIR" =~ ^/home/([^/]+)/ ]]; then
        DETECTED_USER="${BASH_REMATCH[1]}"
        if id "$DETECTED_USER" >/dev/null 2>&1; then
            DEFAULT_RUN_USER="$DETECTED_USER"
            DEFAULT_RUN_GROUP="$DETECTED_USER"
            echo -e "${YELLOW}ℹ Project in home directory - using user: ${DETECTED_USER}${NC}"
        fi
    fi
    
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
    
    # Network Type Configuration
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Network Configuration${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Select your network deployment type:"
    echo ""
    echo "  1) LAN-only (local network - armory PC access)"
    echo "     • Secure internal transactions"
    echo "     • Uses: mkcert SSL (self-signed)"
    echo "     • Access: https://${SERVER_IP}"
    echo ""
    echo "  2) WAN-only (internet accessible - remote log viewing)"
    echo "     • Public domain access"
    echo "     • Uses: Let's Encrypt SSL"
    echo "     • Access: https://yourdomain.com"
    echo ""
    echo "  3) Hybrid (LAN + WAN with complete isolation)"
    echo "     • LAN: Secure transactions (${SERVER_IP})"
    echo "     • WAN: Remote log viewing (public domain)"
    echo "     • Dual SSL certificates"
    echo "     • Network isolation maintained"
    echo ""
    
    while true; do
        read -p "Choose network type (1-3) [1]: " NETWORK_CHOICE
        NETWORK_CHOICE=${NETWORK_CHOICE:-1}
        
        case $NETWORK_CHOICE in
            1)
                NETWORK_TYPE="lan"
                SSL_TYPE="mkcert"
                USE_SSL="yes"
                echo -e "${GREEN}✓ LAN-only deployment selected${NC}"
                break
                ;;
            2)
                NETWORK_TYPE="wan"
                SSL_TYPE="letsencrypt"
                USE_SSL="yes"
                echo ""
                echo -e "${YELLOW}WAN Configuration:${NC}"
                read -p "Enter your public domain name: " WAN_DOMAIN
                if [ -z "$WAN_DOMAIN" ]; then
                    echo -e "${RED}Error: Domain name required for WAN deployment${NC}"
                    continue
                fi
                DOMAIN="$WAN_DOMAIN"
                read -p "Email for Let's Encrypt [admin@${DOMAIN}]: " LETSENCRYPT_EMAIL
                LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-admin@${DOMAIN}}
                echo -e "${GREEN}✓ WAN deployment configured${NC}"
                break
                ;;
            3)
                NETWORK_TYPE="hybrid"
                USE_SSL="yes"
                echo ""
                echo -e "${YELLOW}Hybrid LAN + WAN Configuration:${NC}"
                echo ""
                echo -e "${CYAN}LAN Settings:${NC}"
                echo "  • IP: ${SERVER_IP}"
                echo "  • SSL: mkcert (self-signed)"
                echo "  • Purpose: Secure armory transactions"
                echo ""
                echo -e "${CYAN}WAN Settings:${NC}"
                read -p "Enter your public domain name: " WAN_DOMAIN
                if [ -z "$WAN_DOMAIN" ]; then
                    echo -e "${RED}Error: Domain name required for WAN access${NC}"
                    continue
                fi
                WAN_DOMAIN_NAME="$WAN_DOMAIN"
                read -p "Email for Let's Encrypt [admin@${WAN_DOMAIN}]: " LETSENCRYPT_EMAIL
                LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-admin@${WAN_DOMAIN}}
                
                # Set both SSL types for hybrid
                SSL_TYPE="hybrid"
                echo ""
                echo -e "${GREEN}✓ Hybrid deployment configured${NC}"
                echo "  • LAN: https://${SERVER_IP} (transactions)"
                echo "  • WAN: https://${WAN_DOMAIN} (log viewing)"
                break
                ;;
            *)
                echo -e "${RED}Invalid choice. Please select 1, 2, or 3.${NC}"
                ;;
        esac
    done
    
    echo ""
    
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
    echo "Database:             $([[ "$USE_POSTGRESQL" =~ ^[Yy] ]] && echo "PostgreSQL" || echo "SQLite")"
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
        fail2ban \
        redis-server

    echo -e "${YELLOW}Configuring Redis for WebSocket optimization...${NC}"
    # Start Redis service
    systemctl enable redis-server
    systemctl start redis-server
    
    # Configure Redis for WebSocket performance
    if [ -f /etc/redis/redis.conf ]; then
        cp /etc/redis/redis.conf /etc/redis/redis.conf.backup.$(date +%Y%m%d_%H%M%S)

        if [ "$REDIS_TUNE_MODE" = "append" ] || ! grep -q "# ArmGuard WebSocket Optimizations" /etc/redis/redis.conf; then
            cat >> /etc/redis/redis.conf << 'EOF'

# ArmGuard WebSocket Optimizations
maxmemory 256mb
maxmemory-policy allkeys-lru
timeout 300
tcp-keepalive 300
notify-keyspace-events Ex
EOF
            echo -e "${GREEN}✓ Redis optimization block applied${NC}"
        else
            echo -e "${CYAN}ℹ Redis optimization block already present; skipping append${NC}"
        fi

        systemctl restart redis-server
        echo -e "${GREEN}✓ Redis configured for WebSocket performance${NC}"
    fi
    
    # Test Redis connection
    if redis-cli ping >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis server is running and accessible${NC}"
    else
        echo -e "${YELLOW}⚠ Redis connection test failed, but service is installed${NC}"
    fi
    
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
    
    # Verify project directory exists and contains Django files
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${RED}ERROR: Project directory does not exist: ${PROJECT_DIR}${NC}"
        exit 1
    fi
    
    cd "$PROJECT_DIR"
    
    # Verify manage.py exists
    if [ ! -f "manage.py" ]; then
        echo -e "${RED}ERROR: manage.py not found in ${PROJECT_DIR}${NC}"
        echo -e "${YELLOW}Current directory contents:${NC}"
        ls -la
        exit 1
    fi
    
    echo -e "${GREEN}✓ Project directory verified: ${PROJECT_DIR}${NC}"
    
    # Show git status if it's a repository
    if git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
        echo -e "${CYAN}📦 Git repository - Future updates: cd ${PROJECT_DIR} && git pull${NC}"
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
    
    echo -e "${YELLOW}Installing Python packages (this may take 2-5 minutes)...${NC}"
    .venv/bin/pip install --upgrade pip --quiet
    
    # Detect environment and install appropriate requirements
    if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        echo -e "${GREEN}🥧 Raspberry Pi detected - installing full RPi requirements${NC}"
        if [ -f "requirements-rpi.txt" ]; then
            .venv/bin/pip install -r requirements-rpi.txt --progress-bar on
        else
            # Fallback to base requirements + psutil for RPi
            .venv/bin/pip install -r requirements.txt --progress-bar on
            echo -e "${YELLOW}Installing psutil for enhanced RPi monitoring...${NC}"
            .venv/bin/pip install psutil==5.9.8
        fi
    elif [[ $(uname -m) =~ ^(aarch64|arm64)$ ]]; then
        echo -e "${GREEN}🏗️ ARM64 architecture detected - installing ARM64 optimized requirements${NC}"
        if [ -f "requirements-rpi.txt" ]; then
            .venv/bin/pip install -r requirements-rpi.txt --progress-bar on
        else
            .venv/bin/pip install -r requirements.txt --progress-bar on
            .venv/bin/pip install psutil==5.9.8
        fi
    else
        echo -e "${BLUE}💻 Standard environment detected - installing base requirements${NC}"
        .venv/bin/pip install -r requirements.txt --progress-bar on
        echo -e "${YELLOW}📝 Note: psutil not installed - some monitoring features will use fallbacks${NC}"
    fi
    
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
# Security - Enhanced Features
RATELIMIT_ENABLE=True
RATELIMIT_REQUESTS_PER_MINUTE=60
AXES_ENABLED=True
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1
SESSION_COOKIE_AGE=3600

# Enhanced Security Middleware
SECURITY_HEADERS_ENABLED=True
REQUEST_LOGGING_ENABLED=True
SINGLE_SESSION_ENFORCEMENT=True

# Admin Restrictions
ADMIN_RESTRICTION_SYSTEM_ENABLED=True

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

# Logging - Enhanced Security Logging
SECURITY_LOG_PATH=${PROJECT_DIR}/logs/security.log
ERROR_LOG_PATH=${PROJECT_DIR}/logs/errors.log
DJANGO_LOG_PATH=${PROJECT_DIR}/logs/django.log
ADMIN_RESTRICTION_LOG_PATH=${PROJECT_DIR}/logs/admin_restrictions.log

# Static and Media Files
STATIC_ROOT=${PROJECT_DIR}/staticfiles
MEDIA_ROOT=${PROJECT_DIR}/media
STATIC_URL=/static/
MEDIA_URL=/media/
EOF
    
    chmod 600 .env
    chown ${RUN_USER}:${RUN_GROUP} .env
    echo -e "${GREEN}✓ Environment configured${NC}"
}

# Step 5: Database setup
setup_database() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 5: Setting Up Database${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    cd "$PROJECT_DIR"
    
    # Create necessary directories FIRST (before running any Django commands)
    echo -e "${YELLOW}Creating directories...${NC}"
    mkdir -p "${PROJECT_DIR}/logs"
    mkdir -p "${PROJECT_DIR}/staticfiles"
    mkdir -p "${PROJECT_DIR}/media"
    mkdir -p "/var/log/armguard"
    
    # Set ownership to the run user
    chown -R ${RUN_USER}:${RUN_GROUP} "${PROJECT_DIR}/logs"
    chown -R ${RUN_USER}:${RUN_GROUP} "${PROJECT_DIR}/staticfiles"
    chown -R ${RUN_USER}:${RUN_GROUP} "${PROJECT_DIR}/media"
    chown -R ${RUN_USER}:${RUN_GROUP} "/var/log/armguard"
    
    # Ensure the entire project directory has correct ownership
    chown -R ${RUN_USER}:${RUN_GROUP} "${PROJECT_DIR}"
    echo -e "${GREEN}✓ Directories created and permissions set${NC}"
    
    if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Setting up PostgreSQL database...${NC}"
        
        # Check if database exists
        DB_EXISTS=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'")
        
        if [ "$DB_EXISTS" = "1" ]; then
            echo -e "${YELLOW}Database ${DB_NAME} already exists${NC}"
            read -p "Drop and recreate database? (yes/no) [no]: " DROP_DB
            if [[ "$DROP_DB" =~ ^[Yy] ]]; then
                echo -e "${YELLOW}Dropping existing database and user...${NC}"
                sudo -u postgres psql <<EOF
-- Terminate existing connections
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}';
-- Drop database and user
DROP DATABASE IF EXISTS ${DB_NAME};
DROP USER IF EXISTS ${DB_USER};
EOF
                DB_EXISTS="0"
            else
                echo -e "${YELLOW}Keeping existing database, updating user password...${NC}"
                sudo -u postgres psql <<EOF
ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF
                echo -e "${GREEN}✓ User password updated${NC}"
            fi
        fi
        
        # Create database and user if they don't exist
        if [ "$DB_EXISTS" != "1" ]; then
            echo -e "${YELLOW}Creating database and user...${NC}"
            sudo -u postgres psql <<EOF
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
ALTER ROLE ${DB_USER} SET client_encoding TO 'utf8';
ALTER ROLE ${DB_USER} SET default_transaction_isolation TO 'read committed';
ALTER ROLE ${DB_USER} SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
EOF
            echo -e "${GREEN}✓ PostgreSQL database created${NC}"
        fi
        
        # Grant schema permissions (required for PostgreSQL 15+)
        echo -e "${YELLOW}Granting schema permissions...${NC}"
        sudo -u postgres psql -d ${DB_NAME} <<EOF
GRANT ALL ON SCHEMA public TO ${DB_USER};
GRANT CREATE ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
EOF
        echo -e "${GREEN}✓ Schema permissions granted${NC}"
    else
        echo -e "${YELLOW}Using SQLite database${NC}"
    fi
    
    echo -e "${YELLOW}Running migrations...${NC}"
    .venv/bin/python manage.py migrate --settings=core.settings_production
    
    case "${CREATE_SUPERUSER}" in
        never|skip|no)
            echo -e "${CYAN}Skipping superuser creation (CREATE_SUPERUSER=${CREATE_SUPERUSER})${NC}"
            ;;
        auto)
            if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
                echo -e "${YELLOW}Creating superuser non-interactively...${NC}"
                .venv/bin/python manage.py createsuperuser --noinput --settings=core.settings_production || true
            else
                echo -e "${YELLOW}CREATE_SUPERUSER=auto requested but DJANGO_SUPERUSER_* env vars are incomplete; skipping${NC}"
            fi
            ;;
        prompt|yes|*)
            echo -e "${YELLOW}Create a superuser now? [y/N]${NC}"
            read -r CREATE_SUPERUSER_CONFIRM
            if [[ "$CREATE_SUPERUSER_CONFIRM" =~ ^[Yy]$ ]]; then
                .venv/bin/python manage.py createsuperuser --settings=core.settings_production
            else
                echo -e "${CYAN}Superuser creation skipped by user${NC}"
            fi
            ;;
    esac
    
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
    Group=www-data
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=-${PROJECT_DIR}/.env
    RuntimeDirectory=gunicorn-armguard
    RuntimeDirectoryMode=0755

ExecStart=${PROJECT_DIR}/.venv/bin/gunicorn \\
          --workers ${WORKERS} \\
              --bind unix:/run/gunicorn-armguard/gunicorn.sock \
              --umask 007 \
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
    
    echo -e "${YELLOW}Creating Nginx configuration for ${NETWORK_TYPE} deployment...${NC}"
    
    if [ "$NETWORK_TYPE" == "hybrid" ]; then
        # Hybrid: Two separate server blocks - LAN and WAN
        cat > /etc/nginx/sites-available/armguard <<'EOF'
# =============================================================================
# HYBRID DEPLOYMENT: LAN + WAN with Complete Isolation
# =============================================================================

# LAN HTTP - Redirect to HTTPS
server {
    listen 80;
EOF
        echo "    server_name ${SERVER_IP};" >> /etc/nginx/sites-available/armguard
        cat >> /etc/nginx/sites-available/armguard <<'EOF'
    return 301 https://$server_name$request_uri;
}

# LAN HTTPS - Armory Transactions (mkcert SSL)
server {
    listen 443 ssl http2;
EOF
        echo "    server_name ${SERVER_IP};" >> /etc/nginx/sites-available/armguard
        cat >> /etc/nginx/sites-available/armguard <<'EOF'
    
    # mkcert SSL certificates (will be added by SSL setup)
    # ssl_certificate_lan will be configured
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # LAN-specific: Full access to all features
EOF
        
        cat >> /etc/nginx/sites-available/armguard <<EOF
    
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias ${PROJECT_DIR}/media/;
    }
    
    location / {
        proxy_pass http://unix:/run/gunicorn-armguard/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Network-Type "LAN";
    }
}

# WAN HTTP - Redirect to HTTPS
server {
    listen 80;
EOF
        echo "    server_name ${WAN_DOMAIN_NAME};" >> /etc/nginx/sites-available/armguard
        cat >> /etc/nginx/sites-available/armguard <<'EOF'
    return 301 https://$server_name$request_uri;
}

# WAN HTTPS - Personnel Log Viewing (Let's Encrypt SSL)
server {
    listen 443 ssl http2;
EOF
        echo "    server_name ${WAN_DOMAIN_NAME};" >> /etc/nginx/sites-available/armguard
        cat >> /etc/nginx/sites-available/armguard <<'EOF'
    
    # Let's Encrypt SSL certificates (will be added by certbot)
    # ssl_certificate_wan will be configured
    
    # Enhanced security for public access
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # WAN-specific: Limited to log viewing only
    # Transactions are BLOCKED on WAN
EOF
        
        cat >> /etc/nginx/sites-available/armguard <<EOF
    
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias ${PROJECT_DIR}/media/;
    }
    
    # Block transaction URLs on WAN for security
    location ~ ^/(transactions|inventory|qr_manager) {
        return 403 "Transaction operations only available on LAN";
    }
    
    location / {
        proxy_pass http://unix:/run/gunicorn-armguard/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Network-Type "WAN";
    }
    
    location = /robots.txt {
        return 200 "User-agent: *\nDisallow: /\n";
    }
}
EOF
    else
        # Single network (LAN or WAN)
        SERVER_NAME="${DOMAIN} ${SERVER_IP}"
        if [ "$NETWORK_TYPE" == "wan" ]; then
            SERVER_NAME="${DOMAIN}"
        fi
        
        cat > /etc/nginx/sites-available/armguard <<EOF
# HTTP Server
server {
    listen 80;
    server_name ${SERVER_NAME};
EOF

        if [[ "$USE_SSL" =~ ^[Yy] ]]; then
            cat >> /etc/nginx/sites-available/armguard <<EOF
    return 301 https://\$server_name\$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name ${SERVER_NAME};
    
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
        proxy_pass http://unix:/run/gunicorn-armguard/gunicorn.sock;
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
    fi
    
    # Enable site
    ln -sf /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration only when SSL is not enabled yet.
    # For SSL-enabled flows, certificate directives are injected in setup_ssl().
    if [[ "$USE_SSL" =~ ^[Yy] ]]; then
        echo -e "${CYAN}ℹ Nginx syntax check deferred until SSL certificates are configured${NC}"
    else
        nginx -t
    fi
    
    echo -e "${GREEN}✓ Nginx configured for ${NETWORK_TYPE} deployment${NC}"
}

# Step 9: SSL setup
setup_ssl() {
    if [[ ! "$USE_SSL" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Skipping SSL setup${NC}"
        nginx -t
        systemctl reload nginx
        return
    fi
    
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Step 8: Setting Up SSL/HTTPS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    
    if [ "$SSL_TYPE" == "hybrid" ]; then
        # Hybrid: Install both mkcert (LAN) and Let's Encrypt (WAN)
        echo -e "${CYAN}Setting up HYBRID SSL certificates...${NC}"
        echo ""
        
        # Part 1: mkcert for LAN
        echo -e "${YELLOW}[1/2] Installing mkcert for LAN (${SERVER_IP})...${NC}"
        wget -q https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64
        mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
        chmod +x /usr/local/bin/mkcert
        
        echo -e "${YELLOW}Creating local CA...${NC}"
        mkcert -install
        
        echo -e "${YELLOW}Generating LAN certificates...${NC}"
        mkdir -p /etc/ssl/armguard/lan
        cd /etc/ssl/armguard/lan
        mkcert ${SERVER_IP} localhost 127.0.0.1
        
        LAN_CERT=$(ls /etc/ssl/armguard/lan/*.pem | grep -v key)
        LAN_KEY=$(ls /etc/ssl/armguard/lan/*-key.pem)
        
        # Update LAN server block with mkcert certificates
        sed -i "/# ssl_certificate_lan/a\    ssl_certificate ${LAN_CERT};\n    ssl_certificate_key ${LAN_KEY};" \
            /etc/nginx/sites-available/armguard
        
        echo -e "${GREEN}✓ LAN SSL configured (mkcert)${NC}"
        echo ""
        
        # Part 2: Let's Encrypt for WAN
        echo -e "${YELLOW}[2/2] Installing Let's Encrypt for WAN (${WAN_DOMAIN_NAME})...${NC}"
        apt install -y -qq certbot python3-certbot-nginx
        
        echo -e "${YELLOW}Obtaining Let's Encrypt certificate for ${WAN_DOMAIN_NAME}...${NC}"
        certbot certonly --nginx -d ${WAN_DOMAIN_NAME} --non-interactive --agree-tos -m ${LETSENCRYPT_EMAIL}
        
        # Update WAN server block with Let's Encrypt certificates
        WAN_CERT="/etc/letsencrypt/live/${WAN_DOMAIN_NAME}/fullchain.pem"
        WAN_KEY="/etc/letsencrypt/live/${WAN_DOMAIN_NAME}/privkey.pem"
        
        sed -i "/# ssl_certificate_wan/a\    ssl_certificate ${WAN_CERT};\n    ssl_certificate_key ${WAN_KEY};" \
            /etc/nginx/sites-available/armguard
        
        echo -e "${GREEN}✓ WAN SSL configured (Let's Encrypt)${NC}"
        echo ""
        
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ Hybrid SSL Setup Complete${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}LAN Access:${NC}"
        echo -e "  • URL: https://${SERVER_IP}"
        echo -e "  • SSL: mkcert (self-signed)"
        echo -e "  • Purpose: Secure armory transactions"
        echo -e "  • CA cert: ~/.local/share/mkcert/rootCA.pem"
        echo -e "    ${BLUE}(Install on armory PC to trust certificate)${NC}"
        echo ""
        echo -e "${YELLOW}WAN Access:${NC}"
        echo -e "  • URL: https://${WAN_DOMAIN_NAME}"
        echo -e "  • SSL: Let's Encrypt (public CA)"
        echo -e "  • Purpose: Remote log viewing"
        echo -e "  • Auto-renewal: Enabled"
        echo ""
        
    elif [ "$SSL_TYPE" == "letsencrypt" ]; then
        echo -e "${YELLOW}Installing Certbot...${NC}"
        apt install -y -qq certbot python3-certbot-nginx
        
        echo -e "${YELLOW}Obtaining Let's Encrypt certificate...${NC}"
        certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m ${LETSENCRYPT_EMAIL}
        
        echo -e "${GREEN}✓ Let's Encrypt SSL configured${NC}"
        
    else
        # mkcert only (LAN)
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
    
    echo -e "${YELLOW}Validating Nginx configuration with SSL certificates...${NC}"
    nginx -t
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
    echo -e "${YELLOW}Deployment Summary - ${NETWORK_TYPE^^} Network${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if [ "$NETWORK_TYPE" == "hybrid" ]; then
        echo -e "${CYAN}LAN Access (Armory Transactions):${NC}"
        echo "  URL:                  https://${SERVER_IP}"
        echo "  SSL:                  mkcert (self-signed)"
        echo "  Purpose:              Secure armory inventory transactions"
        echo "  Features:             Full access to all transaction features"
        echo ""
        echo -e "${CYAN}WAN Access (Remote Log Viewing):${NC}"
        echo "  URL:                  https://${WAN_DOMAIN_NAME}"
        echo "  SSL:                  Let's Encrypt (public CA)"
        echo "  Purpose:              Remote log viewing and monitoring"
        echo "  Features:             View-only access (transactions blocked)"
        echo ""
        echo -e "${YELLOW}Network Isolation:${NC} Complete separation maintained between LAN/WAN"
        echo ""
    elif [ "$NETWORK_TYPE" == "wan" ]; then
        echo "Application URL:      https://${DOMAIN}"
        echo "SSL Type:             Let's Encrypt"
        echo "Access:               Public internet"
        echo ""
    else
        echo "Application URL:      https://${SERVER_IP}"
        echo "Alternate URL:        https://${DOMAIN}"
        echo "SSL Type:             mkcert (self-signed)"
        echo "Access:               LAN only"
        echo ""
    fi
    
    echo "Admin URL:            https://${DOMAIN}/${ADMIN_URL}/"
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
    
    if [ "$SSL_TYPE" == "mkcert" ] || [ "$SSL_TYPE" == "hybrid" ]; then
        echo -e "${YELLOW}Important: mkcert Certificate (LAN)${NC}"
        echo "CA Certificate:       ~/.local/share/mkcert/rootCA.pem"
        echo "Install this certificate on armory PC to trust HTTPS"
        echo ""
    fi
    
    if [ "$SSL_TYPE" == "hybrid" ]; then
        echo -e "${YELLOW}Let's Encrypt (WAN)${NC}"
        echo "Auto-renewal:         Enabled (certbot timer)"
        echo "Certificate expires:  90 days (auto-renews at 30 days)"
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

=========================================
Network Type: ${NETWORK_TYPE^^}
=========================================
EOF

    if [ "$NETWORK_TYPE" == "hybrid" ]; then
        cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF

LAN Access (Armory Transactions):
  URL: https://${SERVER_IP}
  SSL: mkcert (self-signed)
  Purpose: Secure armory inventory transactions
  
WAN Access (Remote Log Viewing):
  URL: https://${WAN_DOMAIN_NAME}
  SSL: Let's Encrypt
  Purpose: Remote log viewing and monitoring
  
Network Isolation: Complete separation maintained

EOF
    else
        # Build deployment info for non-hybrid deployments
        cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF

Application URLs:
- Main: http${USE_SSL:+s}://${DOMAIN}
- IP: http${USE_SSL:+s}://${SERVER_IP}
- Admin: http${USE_SSL:+s}://${DOMAIN}/${ADMIN_URL}/

Configuration:
- Project: ${PROJECT_DIR}
- .env file: ${PROJECT_DIR}/.env
- Django Secret Key: ${DJANGO_SECRET_KEY}
- Admin URL Path: /${ADMIN_URL}/

EOF

        # Add database configuration
        if [[ "$USE_POSTGRESQL" =~ ^[Yy] ]]; then
            cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
Database:
- Type: PostgreSQL
- Name: ${DB_NAME}
- User: ${DB_USER}
- Password: ${DB_PASSWORD}

EOF
        else
            cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
Database:
- Type: SQLite
- File: ${PROJECT_DIR}/db.sqlite3

EOF
        fi

        # Add services info
        cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
Services:
- Gunicorn: /etc/systemd/system/gunicorn-armguard.service
- Nginx: /etc/nginx/sites-available/armguard
- Logs: /var/log/armguard/

EOF

        # Add SSL configuration if mkcert
        if [ "$SSL_TYPE" == "mkcert" ]; then
            cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
SSL (mkcert):
- CA Certificate: ~/.local/share/mkcert/rootCA.pem
- Install CA on client devices for trusted HTTPS

EOF
        fi

        # Add security notice
        cat >> "${PROJECT_DIR}/DEPLOYMENT_INFO.txt" <<EOF
IMPORTANT: Keep this file secure! It contains sensitive credentials.
EOF
    fi
    
    chmod 600 "${PROJECT_DIR}/DEPLOYMENT_INFO.txt"
    echo -e "${YELLOW}Deployment info saved to: ${PROJECT_DIR}/DEPLOYMENT_INFO.txt${NC}"
}

# Cleanup function for failed deployments
cleanup_failed_deployment() {
    echo ""
    echo -e "${YELLOW}Cleaning up failed deployment...${NC}"
    
    # Stop and disable service if it exists
    systemctl stop gunicorn-armguard 2>/dev/null || true
    systemctl disable gunicorn-armguard 2>/dev/null || true
    
    # Remove service file
    rm -f /etc/systemd/system/gunicorn-armguard.service 2>/dev/null || true
    
    # Reload systemd
    systemctl daemon-reload
    
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Main execution
main() {
    print_banner
    check_root
    
    # Offer to cleanup if service already exists and is failed
    if systemctl list-unit-files | grep -q gunicorn-armguard.service; then
        if ! systemctl is-active --quiet gunicorn-armguard; then
            echo -e "${YELLOW}⚠ Detected existing failed gunicorn-armguard service${NC}"
            read -p "Clean up failed deployment before continuing? (yes/no) [yes]: " CLEANUP
            CLEANUP=${CLEANUP:-yes}
            if [[ "$CLEANUP" =~ ^[Yy] ]]; then
                cleanup_failed_deployment
            fi
        fi
    fi
    
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
