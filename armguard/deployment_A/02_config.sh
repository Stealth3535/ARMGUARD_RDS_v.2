#!/bin/bash

# =============================================================================
# 02_CONFIG.SH - CONFIGURATION FILES AND APPLICATION SETUP
# =============================================================================
# PURPOSE: Environment variables, app configs, SSL certificates, database setup
# INTEGRATED: SSL management from deployment + DB config from deployment_A
# VERSION: 4.0.0 - Modular Deployment System
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_DIR="/var/log/armguard-deploy"
readonly LOG_FILE="$LOG_DIR/02-config-$(date +%Y%m%d-%H%M%S).log"
readonly ARMGUARD_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Configuration defaults (can be overridden)
PROJECT_NAME="${PROJECT_NAME:-armguard}"
PROJECT_DIR="${PROJECT_DIR:-$ARMGUARD_ROOT}"
DEFAULT_DOMAIN="${DEFAULT_DOMAIN:-armguard.local}"
SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.1.100}"
NETWORK_TYPE="${NETWORK_TYPE:-lan}"

# =============================================================================
# LOGGING SYSTEM
# =============================================================================

log_info() {
    echo -e "${GREEN}[CONFIG-INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[CONFIG-WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[CONFIG-ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${CYAN}[CONFIG-SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

# =============================================================================
# ADVANCED NETWORK CONFIGURATION (FROM network_setup/)
# =============================================================================

configure_lan_network() {
    log_info "Configuring LAN-only network (192.168.10.x subnet)..."
    
    # LAN Network Configuration
    export LAN_INTERFACE="${LAN_INTERFACE:-eth1}"
    export SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.10.1}"
    export ARMORY_PC_IP="${ARMORY_PC_IP:-192.168.10.2}"
    export LAN_SUBNET="${LAN_SUBNET:-192.168.10.0/24}"
    
    echo ""
    echo -e "${WHITE}LAN Network Settings:${NC}"
    read -p "LAN Interface [$LAN_INTERFACE]: " user_lan_interface
    if [ -n "$user_lan_interface" ]; then
        export LAN_INTERFACE="$user_lan_interface"
    fi
    
    read -p "Server LAN IP [$SERVER_LAN_IP]: " user_server_ip
    if [ -n "$user_server_ip" ]; then
        export SERVER_LAN_IP="$user_server_ip"
    fi
    
    read -p "Armory PC IP [$ARMORY_PC_IP]: " user_armory_ip  
    if [ -n "$user_armory_ip" ]; then
        export ARMORY_PC_IP="$user_armory_ip"
    fi
    
    # SSL Method
    SSL_METHOD="mkcert"  # LAN uses mkcert for internal certificates
    log_info "LAN network will use mkcert SSL certificates (self-signed)"
    
    echo ""
}

configure_hybrid_network() {
    log_info "Configuring hybrid network (LAN + WAN with isolation)..."
    
    # Configure both LAN and WAN
    configure_lan_network
    configure_wan_network
    
    echo -e "${YELLOW}Hybrid Network Information:${NC}"
    echo "- LAN Network: $LAN_SUBNET (eth1) - Armory PC access"
    echo "- WAN Network: Public IP (eth0) - Personnel portal"  
    echo "- Complete isolation between networks maintained"
    echo ""
}

configure_wan_network() {
    log_info "Configuring WAN network settings..."
    
    export WAN_INTERFACE="${WAN_INTERFACE:-eth0}"
    
    echo ""
    echo -e "${WHITE}WAN Network Settings:${NC}"
    read -p "WAN Interface [$WAN_INTERFACE]: " user_wan_interface
    if [ -n "$user_wan_interface" ]; then
        export WAN_INTERFACE="$user_wan_interface"
    fi
    
    # Domain configuration for WAN
    echo -e "${WHITE}🔗 Public Domain Configuration:${NC}"
    read -p "Enter your public domain name [login.yourdomain.com]: " wan_domain  
    if [ -n "$wan_domain" ]; then
        DEFAULT_DOMAIN="$wan_domain"
    else
        DEFAULT_DOMAIN="login.yourdomain.com"
    fi
    
    # ACME/ZeroSSL configuration 
    echo -e "${WHITE}🔐 SSL Certificate Authority:${NC}"
    echo "1. Let's Encrypt (free, recommended)"
    echo "2. ZeroSSL (free, alternative)"
    echo ""
    
    while true; do
        read -p "Select certificate authority (1-2): " ca_choice
        case $ca_choice in
            1)
                ACME_SERVER="letsencrypt"
                SSL_METHOD="acme"
                log_info "Let's Encrypt selected for WAN SSL"
                break
                ;;
            2)
                ACME_SERVER="zerossl"  
                SSL_METHOD="acme"
                log_info "ZeroSSL selected for WAN SSL"
                break
                ;;
            *)
                echo "Invalid choice. Please select 1 or 2."
                ;;
        esac
    done
    
    # Email for ACME registration
    read -p "Enter email for SSL certificate notifications [admin@$DEFAULT_DOMAIN]: " acme_email
    if [ -n "$acme_email" ]; then
        export ACME_EMAIL="$acme_email"
    else
        export ACME_EMAIL="admin@$DEFAULT_DOMAIN"
    fi
    
    echo ""
}

# =============================================================================
# INTERACTIVE CONFIGURATION (FROM deployment/unified-deployment.sh)  
# =============================================================================

interactive_config() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}║              ${WHITE}🔧 ARMGUARD CONFIGURATION SETUP${BLUE}                            ║${NC}"
    echo -e "${BLUE}║                    ${CYAN}Phase 2: Application Configuration${BLUE}                     ║${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log_info "Starting interactive configuration..."
    
    # Network Configuration
    echo -e "${WHITE}🌐 Network Configuration:${NC}"
    echo "1. LAN-only deployment (secure internal - 192.168.10.x subnet)"
    echo "2. LAN/WAN hybrid deployment (complete network isolation)"  
    echo "3. WAN deployment (internet accessible)"
    echo ""
    
    while true; do
        read -p "Select network type (1-3): " network_choice
        case $network_choice in
            1) 
                NETWORK_TYPE="lan"
                configure_lan_network
                log_info "LAN-only deployment configured"
                break
                ;;
            2)
                NETWORK_TYPE="hybrid" 
                configure_hybrid_network
                log_info "LAN/WAN hybrid deployment configured"
                break
                ;;
            3)
                NETWORK_TYPE="wan"
                configure_wan_network
                log_info "WAN deployment configured"
                break
                ;;
            *)
                echo "Invalid choice. Please select 1, 2, or 3."
                ;;
        esac
    done
    
    echo ""
    
    # Additional Domain Configuration (for non-WAN deployments)
    if [ "$NETWORK_TYPE" != "wan" ]; then
        echo -e "${WHITE}🔗 Additional Domain Configuration:${NC}"
        read -p "Enter domain name [${DEFAULT_DOMAIN:-armguard.local}]: " user_domain
        if [ -n "$user_domain" ]; then
            DEFAULT_DOMAIN="$user_domain"
        elif [ -z "$DEFAULT_DOMAIN" ]; then
            DEFAULT_DOMAIN="armguard.local"
        fi
        log_info "Domain set to: $DEFAULT_DOMAIN"
    fi
    
    echo ""
    
    # SSL Configuration (only if not already configured by network setup) 
    if [ -z "$SSL_METHOD" ]; then
        echo -e "${WHITE}🔐 SSL Certificate Configuration:${NC}"
        echo "1. Self-signed certificates (quick setup)"
        echo "2. mkcert certificates (development/internal)"
        echo "3. Let's Encrypt certificates (production)"
        echo ""
        
        while true; do
            read -p "Select SSL method (1-3): " ssl_choice
            case $ssl_choice in
                1)
                    SSL_METHOD="self-signed"
                    log_info "Self-signed SSL certificates selected"
                    break
                    ;;
                2)
                    SSL_METHOD="mkcert"
                    log_info "mkcert SSL certificates selected"
                    break
                    ;;
                3)
                    SSL_METHOD="letsencrypt"
                    log_info "Let's Encrypt SSL certificates selected"
                    break
                    ;;
                *)
                    echo "Invalid choice. Please select 1, 2, or 3."
                    ;;
            esac
        done
    else
        log_info "SSL method already configured: $SSL_METHOD"
    fi
    
    echo ""
}

# =============================================================================
# DATABASE CONFIGURATION (FROM deployment_A/methods/production)
# =============================================================================

configure_database() {
    log_info "Configuring PostgreSQL database..."
    
    local db_name="${PROJECT_NAME}_db"
    local db_user="${PROJECT_NAME}_user"  
    local db_password
    
    # Generate secure database password
    db_password=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    # Create database and user
    sudo -u postgres psql << EOF
-- Check if database exists, create if not
SELECT 'CREATE DATABASE ${db_name}' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${db_name}')\\gexec

-- Check if user exists, create if not  
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '${db_user}') THEN
        CREATE USER ${db_user} WITH PASSWORD '${db_password}';
    END IF;
END
\$\$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ${db_name} TO ${db_user};
ALTER USER ${db_user} CREATEDB;
EOF
    
    if [ $? -eq 0 ]; then
        log_success "Database created: $db_name"
        log_success "Database user created: $db_user"
        
        # Store database credentials securely
        local db_config_file="$SCRIPT_DIR/.db_config"
        cat > "$db_config_file" << EOF
DB_NAME=${db_name}
DB_USER=${db_user}
DB_PASSWORD=${db_password}
DB_HOST=localhost
DB_PORT=5432
EOF
        chmod 600 "$db_config_file"
        log_success "Database credentials stored in $db_config_file"
    else
        log_error "Database configuration failed"
        return 1
    fi
}

# =============================================================================
# SSL CERTIFICATE MANAGEMENT (FROM deployment/unified-ssl-port-manager.sh)
# =============================================================================

configure_ssl_certificates() {
    log_info "Configuring SSL certificates for $NETWORK_TYPE deployment..."
    
    local ssl_dir="/etc/ssl/armguard"
    sudo mkdir -p "$ssl_dir"
    
    case "$NETWORK_TYPE" in
        "lan")
            log_info "Setting up LAN certificates with mkcert..."
            create_lan_mkcert_certificates
            ;;
        "hybrid")
            log_info "Setting up hybrid certificates (mkcert for LAN + ACME for WAN)..."
            create_lan_mkcert_certificates
            create_wan_acme_certificates
            ;;
        "wan")
            log_info "Setting up WAN certificates with ACME..."
            create_wan_acme_certificates
            ;;
        *)
            # Fallback to original SSL method
            case "$SSL_METHOD" in
                "self-signed")
                    create_self_signed_certificates
                    ;;
                "mkcert")
                    create_mkcert_certificates
                    ;;
                "letsencrypt")
                    create_letsencrypt_certificates
            ;;
        *)
            log_error "Unknown SSL method: $SSL_METHOD"
            return 1
            ;;
    esac
}

create_self_signed_certificates() {
    log_info "Creating self-signed SSL certificates..."
    
    local ssl_dir="/etc/ssl/armguard"
    local cert_file="$ssl_dir/cert.pem"
    local key_file="$ssl_dir/key.pem"
    
    # Create self-signed certificate
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -subj "/C=US/ST=Military/L=Base/O=ArmGuard/OU=IT/CN=$DEFAULT_DOMAIN"
    
    if [ $? -eq 0 ]; then
        sudo chmod 644 "$cert_file"
        sudo chmod 600 "$key_file"
        log_success "Self-signed SSL certificates created"
        log_warn "Self-signed certificates will show browser warnings"
    else
        log_error "Failed to create self-signed certificates"
        return 1
    fi
}

create_mkcert_certificates() {
    log_info "Creating mkcert SSL certificates..."
    
    # Install mkcert if not available
    if ! command -v mkcert >/dev/null 2>&1; then
        log_info "Installing mkcert..."
        
        case "$(uname -m)" in
            x86_64)
                curl -JLO "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64"
                sudo mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
                ;;
            aarch64)
                curl -JLO "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-arm64"
                sudo mv mkcert-v1.4.4-linux-arm64 /usr/local/bin/mkcert
                ;;
            *)
                log_error "Unsupported architecture for mkcert"
                return 1
                ;;
        esac
        
        sudo chmod +x /usr/local/bin/mkcert
    fi
    
    # Install local CA
    mkcert -install
    
    # Create certificates  
    local ssl_dir="/etc/ssl/armguard"
    cd "$ssl_dir"
    sudo mkcert -key-file key.pem -cert-file cert.pem "$DEFAULT_DOMAIN" "localhost" "127.0.0.1" "::1"
    
    if [ $? -eq 0 ]; then
        sudo chmod 644 "$ssl_dir/cert.pem"
        sudo chmod 600 "$ssl_dir/key.pem"
        log_success "mkcert SSL certificates created"
    else
        log_error "Failed to create mkcert certificates"
        return 1
    fi
}

create_letsencrypt_certificates() {
    log_info "Creating Let's Encrypt SSL certificates..."
    
    if [ "$NETWORK_TYPE" = "lan" ]; then
        log_error "Let's Encrypt requires WAN access for domain validation"
        log_info "Consider using self-signed or mkcert for LAN deployments"
        return 1
    fi
    
    # Stop nginx temporarily for standalone authentication
    sudo systemctl stop nginx
    
    # Request certificate
    sudo certbot certonly --standalone \
        --email "admin@$DEFAULT_DOMAIN" \
        --agree-tos \
        --no-eff-email \
        -d "$DEFAULT_DOMAIN"
    
    if [ $? -eq 0 ]; then
        # Create symlinks to expected location
        local ssl_dir="/etc/ssl/armguard"
        sudo ln -sf "/etc/letsencrypt/live/$DEFAULT_DOMAIN/fullchain.pem" "$ssl_dir/cert.pem"
        sudo ln -sf "/etc/letsencrypt/live/$DEFAULT_DOMAIN/privkey.pem" "$ssl_dir/key.pem"
        
        # Setup automatic renewal
        sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet"; } | sudo crontab -
        
        log_success "Let's Encrypt SSL certificates created"
        log_success "Automatic renewal configured"
    else
        log_error "Failed to create Let's Encrypt certificates"
        return 1
    fi
    
    # Restart nginx
    sudo systemctl start nginx
}

# =============================================================================
# ADVANCED SSL CERTIFICATE MANAGEMENT (FROM network_setup/)
# =============================================================================

create_lan_mkcert_certificates() {
    log_info "Creating LAN mkcert certificates for internal network..."
    
    # Install mkcert if not available
    if ! command -v mkcert >/dev/null 2>&1; then
        log_info "Installing mkcert..."
        
        case "$(uname -m)" in
            x86_64)
                curl -JLO "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-amd64"
                sudo mv mkcert-v1.4.4-linux-amd64 /usr/local/bin/mkcert
                ;;
            aarch64)
                curl -JLO "https://github.com/FiloSottile/mkcert/releases/download/v1.4.4/mkcert-v1.4.4-linux-arm64"
                sudo mv mkcert-v1.4.4-linux-arm64 /usr/local/bin/mkcert
                ;;
            *)
                log_error "Unsupported architecture for mkcert"
                return 1
                ;;
        esac
        
        sudo chmod +x /usr/local/bin/mkcert
    fi
    
    # Install local CA
    mkcert -install
    
    # Create LAN-specific certificates  
    local lan_ssl_dir="/etc/ssl/armguard/lan"
    sudo mkdir -p "$lan_ssl_dir"
    cd "$lan_ssl_dir"
    
    # Generate certificates for LAN network
    sudo mkcert -key-file key.pem -cert-file cert.pem \
        "$DEFAULT_DOMAIN" \
        "localhost" \
        "127.0.0.1" \
        "$SERVER_LAN_IP" \
        "armguard.lan" \
        "*.armguard.lan"
    
    if [ $? -eq 0 ]; then
        sudo chmod 644 "$lan_ssl_dir/cert.pem"
        sudo chmod 600 "$lan_ssl_dir/key.pem"
        log_success "LAN mkcert SSL certificates created in $lan_ssl_dir"
        
        # Create main symlinks for compatibility
        local ssl_dir="/etc/ssl/armguard"
        sudo ln -sf "$lan_ssl_dir/cert.pem" "$ssl_dir/cert.pem"
        sudo ln -sf "$lan_ssl_dir/key.pem" "$ssl_dir/key.pem"
    else
        log_error "Failed to create LAN mkcert certificates"
        return 1
    fi
}

create_wan_acme_certificates() {
    log_info "Creating WAN ACME certificates for public access..."
    
    # Determine ACME client and server
    local acme_server_url=""
    local acme_client="${ACME_CLIENT:-acme.sh}"
    
    case "${ACME_SERVER:-letsencrypt}" in
        "letsencrypt")
            acme_server_url="https://acme-v02.api.letsencrypt.org/directory"
            ;;
        "zerossl")
            acme_server_url="https://acme.zerossl.com/v2/DV90"
            ;;
        *)
            acme_server_url="https://acme-v02.api.letsencrypt.org/directory"
            ;;
    esac
    
    # Create WAN-specific SSL directory
    local wan_ssl_dir="/etc/ssl/armguard/wan"
    sudo mkdir -p "$wan_ssl_dir"
    
    case "$acme_client" in
        "acme.sh")
            create_wan_acme_sh_certificates "$wan_ssl_dir" "$acme_server_url"
            ;;
        "certbot")
            create_wan_certbot_certificates "$wan_ssl_dir"
            ;;
        *)
            log_warn "Unknown ACME client, defaulting to acme.sh"
            create_wan_acme_sh_certificates "$wan_ssl_dir" "$acme_server_url"
            ;;
    esac
}

create_wan_acme_sh_certificates() {
    local wan_ssl_dir="$1"
    local server_url="$2"
    
    log_info "Using acme.sh for WAN certificate generation..."
    
    # Install acme.sh if not available
    if [ ! -f ~/.acme.sh/acme.sh ]; then
        log_info "Installing acme.sh..."
        curl https://get.acme.sh | sh -s email="$ACME_EMAIL"
        source ~/.bashrc
    fi
    
    # Stop nginx for standalone validation
    sudo systemctl stop nginx 2>/dev/null || true
    
    # Issue certificate
    ~/.acme.sh/acme.sh --issue \
        --server "$server_url" \
        --standalone \
        --email "$ACME_EMAIL" \
        -d "$DEFAULT_DOMAIN"
    
    if [ $? -eq 0 ]; then
        # Install certificate to our directory
        ~/.acme.sh/acme.sh --install-cert \
            -d "$DEFAULT_DOMAIN" \
            --key-file "$wan_ssl_dir/key.pem" \
            --fullchain-file "$wan_ssl_dir/cert.pem"
        
        sudo chmod 644 "$wan_ssl_dir/cert.pem"
        sudo chmod 600 "$wan_ssl_dir/key.pem"
        
        log_success "WAN ACME SSL certificates created in $wan_ssl_dir"
        
        # For WAN-only deployments, create main symlinks
        if [ "$NETWORK_TYPE" = "wan" ]; then
            local ssl_dir="/etc/ssl/armguard"
            sudo ln -sf "$wan_ssl_dir/cert.pem" "$ssl_dir/cert.pem"
            sudo ln -sf "$wan_ssl_dir/key.pem" "$ssl_dir/key.pem"
        fi
    else
        log_error "Failed to create WAN ACME certificates"
        return 1
    fi
    
    # Restart nginx
    sudo systemctl start nginx 2>/dev/null || true
}

create_wan_certbot_certificates() {
    local wan_ssl_dir="$1"
    
    log_info "Using certbot for WAN certificate generation..."
    
    # Install certbot if not available
    if ! command -v certbot >/dev/null 2>&1; then
        log_info "Installing certbot..."
        sudo apt-get update -qq
        sudo apt-get install -y snapd
        sudo snap install core; sudo snap refresh core
        sudo snap install --classic certbot
        sudo ln -sf /snap/bin/certbot /usr/bin/certbot
    fi
    
    # Stop nginx temporarily for standalone authentication
    sudo systemctl stop nginx 2>/dev/null || true
    
    # Request certificate
    sudo certbot certonly --standalone \
        --email "$ACME_EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DEFAULT_DOMAIN"
    
    if [ $? -eq 0 ]; then
        # Copy certificates to our WAN directory
        sudo cp "/etc/letsencrypt/live/$DEFAULT_DOMAIN/fullchain.pem" "$wan_ssl_dir/cert.pem"
        sudo cp "/etc/letsencrypt/live/$DEFAULT_DOMAIN/privkey.pem" "$wan_ssl_dir/key.pem"
        
        sudo chmod 644 "$wan_ssl_dir/cert.pem"
        sudo chmod 600 "$wan_ssl_dir/key.pem"
        
        # Setup automatic renewal
        sudo crontab -l 2>/dev/null | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet && cp /etc/letsencrypt/live/$DEFAULT_DOMAIN/fullchain.pem $wan_ssl_dir/cert.pem && cp /etc/letsencrypt/live/$DEFAULT_DOMAIN/privkey.pem $wan_ssl_dir/key.pem && systemctl reload nginx"; } | sudo crontab -
        
        log_success "WAN certbot SSL certificates created in $wan_ssl_dir"
        log_success "Automatic renewal configured"
        
        # For WAN-only deployments, create main symlinks
        if [ "$NETWORK_TYPE" = "wan" ]; then
            local ssl_dir="/etc/ssl/armguard"
            sudo ln -sf "$wan_ssl_dir/cert.pem" "$ssl_dir/cert.pem"
            sudo ln -sf "$wan_ssl_dir/key.pem" "$ssl_dir/key.pem"
        fi
    else
        log_error "Failed to create WAN certbot certificates"
        return 1
    fi
    
    # Restart nginx
    sudo systemctl start nginx 2>/dev/null || true
}

# =============================================================================
# DJANGO APPLICATION CONFIGURATION
# =============================================================================

configure_django_application() {
    log_info "Configuring Django application..."
    
    # Load database configuration
    if [ -f "$SCRIPT_DIR/.db_config" ]; then
        source "$SCRIPT_DIR/.db_config"
    else
        log_error "Database configuration not found"
        return 1
    fi
    
    # Create Django settings for production
    local settings_file="$ARMGUARD_ROOT/core/settings_production.py"
    
    # Generate Django secret key
    local django_secret_key
    django_secret_key=$(python3 -c 'import secrets; import string; print("".join(secrets.choice(string.ascii_letters + string.digits + "!@#$%^&*(-_=+)") for _ in range(50)))')
    
    cat > "$settings_file" << EOF
# Production settings for ArmGuard
# Generated by 02_config.sh on $(date)

from .settings import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '${django_secret_key}'

# Production security settings  
DEBUG = False
ALLOWED_HOSTS = ['${DEFAULT_DOMAIN}', '${SERVER_LAN_IP}', 'localhost']

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': '${DB_NAME}',
        'USER': '${DB_USER}',
        'PASSWORD': '${DB_PASSWORD}',
        'HOST': '${DB_HOST}',
        'PORT': '${DB_PORT}',
    }
}

# Redis configuration (from deployment/unified-redis-manager.sh approach)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Channel layers for WebSocket (resolves WebSocket blocking issues)  
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = '${ARMGUARD_ROOT}/staticfiles/'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = '${ARMGUARD_ROOT}/media/'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/armguard/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Network security settings (from deployment_A comprehensive approach)
NETWORK_SECURITY_ENABLED = True
if '${NETWORK_TYPE}' == 'lan':
    LAN_ONLY = True
    WAN_PORTAL_ENABLED = False
elif '${NETWORK_TYPE}' == 'hybrid':
    LAN_ONLY = False  
    WAN_PORTAL_ENABLED = True
else:  # wan
    LAN_ONLY = False
    WAN_PORTAL_ENABLED = True
EOF
    
    log_success "Django production settings created"
    
    # Create directory for static and media files
    sudo mkdir -p ${ARMGUARD_ROOT}/staticfiles
    sudo mkdir -p ${ARMGUARD_ROOT}/media
    sudo mkdir -p /var/log/armguard
    sudo chown -R rds:rds ${ARMGUARD_ROOT}
    sudo chown -R rds:rds /var/log/armguard
    
    log_success "Django directories created with proper permissions"
}

# =============================================================================
# REDIS CONFIGURATION (FROM deployment/unified-redis-manager.sh)
# =============================================================================

configure_redis() {
    log_info "Configuring Redis for WebSocket optimization..."
    
    local redis_conf="/etc/redis/redis.conf"
    
    # Backup original configuration
    if [ -f "$redis_conf" ] && [ ! -f "$redis_conf.backup" ]; then
        sudo cp "$redis_conf" "$redis_conf.backup"
        log_info "Redis configuration backed up"
    fi
    
    # Optimize Redis for WebSocket performance
    sudo tee -a "$redis_conf" > /dev/null << EOF

# ArmGuard WebSocket optimization settings
# Added by 02_config.sh on $(date)

# Memory optimization
maxmemory 256mb
maxmemory-policy allkeys-lru

# Performance optimization
tcp-keepalive 60
timeout 300

# Persistence optimization for WebSocket data
save 900 1
save 300 10
save 60 10000

# Security
requirepass $(openssl rand -base64 32 | tr -d "=+/" | cut -c1-16)
EOF
    
    # Test configuration and restart
    if redis-server --test-config -f "$redis_conf"; then
        sudo systemctl restart redis-server 2>/dev/null || sudo systemctl restart redis
        log_success "Redis configuration optimized and restarted"
    else
        log_error "Invalid Redis configuration"
        sudo cp "$redis_conf.backup" "$redis_conf"
        return 1
    fi
}

# =============================================================================  
# NGINX CONFIGURATION (FROM deployment_A/methods/production)
# =============================================================================

configure_nginx() {
    log_info "Configuring Nginx for $NETWORK_TYPE deployment..."
    
    case "$NETWORK_TYPE" in
        "lan")
            configure_lan_nginx
            ;;
        "hybrid")
            configure_hybrid_nginx
            ;;
        "wan")
            configure_wan_nginx
            ;;
        *)
            log_warn "Unknown network type, using default configuration"
            configure_default_nginx
            ;;
    esac
}

configure_lan_nginx() {
    log_info "Setting up LAN-only Nginx configuration (port 8443)..."
    
    local nginx_config="/etc/nginx/sites-available/armguard-lan"
    local ssl_dir="/etc/ssl/armguard/lan"
    
    # Create LAN Nginx configuration
    sudo tee "$nginx_config" > /dev/null << EOF
# ArmGuard LAN-only Nginx configuration
# Generated by 02_config.sh on $(date)
# Network: LAN (192.168.10.x) - Armory PC Access Only
# Port: 8443 (HTTPS), 8080 (HTTP redirect) 

server {
    listen ${SERVER_LAN_IP}:8080;
    listen 127.0.0.1:8080;
    server_name ${DEFAULT_DOMAIN} ${SERVER_LAN_IP} armguard.lan localhost;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name:8443\$request_uri;
}

server {
    listen ${SERVER_LAN_IP}:8443 ssl http2;
    listen 127.0.0.1:8443 ssl http2;
    server_name ${DEFAULT_DOMAIN} ${SERVER_LAN_IP} armguard.lan localhost;
    
    # LAN SSL configuration (mkcert certificates)
    ssl_certificate ${ssl_dir}/cert.pem;
    ssl_certificate_key ${ssl_dir}/key.pem;

    # mTLS rollout (optional until certificate enrollment is complete)
    ssl_client_certificate /etc/ssl/certs/ca-certificates.crt;
    ssl_verify_client optional;
    ssl_verify_depth 2;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # LAN-specific security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options SAMEORIGIN;  # Allow iframe from same origin for LAN
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Restrict access to LAN subnet only
    allow ${LAN_SUBNET};
    allow 127.0.0.1;
    deny all;
    
    # Static files
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias ${PROJECT_DIR}/media/;
        expires 30d;
    }
    
    # Django application (Armory PC interface)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;  
        proxy_read_timeout 30s;
    }
    
    # WebSocket support for real-time inventory updates
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
EOF
    
    # Enable the LAN site
    sudo ln -sf /etc/nginx/sites-available/armguard-lan /etc/nginx/sites-enabled/
    log_success "LAN Nginx configuration created for ${SERVER_LAN_IP}:8443"
}

configure_wan_nginx() {
    log_info "Setting up WAN-only Nginx configuration (port 443)..."
    
    local nginx_config="/etc/nginx/sites-available/armguard-wan" 
    local ssl_dir="/etc/ssl/armguard/wan"
    
    # Create WAN Nginx configuration
    sudo tee "$nginx_config" > /dev/null << EOF
# ArmGuard WAN-only Nginx configuration
# Generated by 02_config.sh on $(date)
# Network: WAN (Public Internet) - Personnel Portal Only
# Port: 443 (HTTPS), 80 (HTTP redirect)

server {
    listen 80;
    server_name ${DEFAULT_DOMAIN};
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${DEFAULT_DOMAIN};
    
    # WAN SSL configuration (ACME certificates)
    ssl_certificate ${ssl_dir}/cert.pem;
    ssl_certificate_key ${ssl_dir}/key.pem;

    # mTLS rollout (optional until certificate enrollment is complete)
    ssl_client_certificate /etc/ssl/certs/ca-certificates.crt;
    ssl_verify_client optional;
    ssl_verify_depth 2;
    
    # Enhanced SSL security for public access
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # WAN-specific security headers (stricter for public access)
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'";
    
    # Rate limiting for public access
    limit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;
    limit_req zone=login burst=10 nodelay;
    
    # Static files
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias ${PROJECT_DIR}/media/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Django application (Personnel portal only)
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # WebSocket support for personnel notifications
    location /ws/ {  
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
EOF
    
    # Enable the WAN site
    sudo ln -sf /etc/nginx/sites-available/armguard-wan /etc/nginx/sites-enabled/
    log_success "WAN Nginx configuration created for $DEFAULT_DOMAIN:443"
}

configure_hybrid_nginx() {
    log_info "Setting up Hybrid Nginx configuration (LAN + WAN with isolation)..."
    
    # Configure both LAN and WAN configurations
    configure_lan_nginx
    configure_wan_nginx
    
    log_success "Hybrid network isolation configured:"
    log_success "- LAN: ${SERVER_LAN_IP}:8443 (Armory PC access)"
    log_success "- WAN: ${DEFAULT_DOMAIN}:443 (Personnel portal)"
}

configure_default_nginx() {
    log_info "Setting up default Nginx configuration..."
    
    local nginx_config="/etc/nginx/sites-available/armguard"
    local ssl_dir="/etc/ssl/armguard"
    
    # Determine ports based on network type
    local http_port=80
    local https_port=443
    if [ "$NETWORK_TYPE" = "lan" ]; then
        https_port=8443
    fi
    
    # Create default Nginx configuration
    sudo tee "$nginx_config" > /dev/null << EOF
# ArmGuard Default Nginx configuration
# Generated by 02_config.sh on $(date)
# Network type: ${NETWORK_TYPE}

server {
    listen ${http_port};
    server_name ${DEFAULT_DOMAIN};
    
    # Redirect HTTP to HTTPS
    return 301 https://\$server_name:\$server_port\$request_uri;
}

server {
    listen ${https_port} ssl http2;
    server_name ${DEFAULT_DOMAIN};
    
    # SSL configuration
    ssl_certificate ${ssl_dir}/cert.pem;
    ssl_certificate_key ${ssl_dir}/key.pem;

    # mTLS rollout (optional until certificate enrollment is complete)
    ssl_client_certificate /etc/ssl/certs/ca-certificates.crt;
    ssl_verify_client optional;
    ssl_verify_depth 2;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static/ {
        alias ${PROJECT_DIR}/staticfiles/;
        expires 30d;
    }
    
    location /media/ {
        alias ${PROJECT_DIR}/media/;
        expires 30d;
    }
    
    # Django application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;  
        proxy_read_timeout 30s;
    }
    
    # WebSocket support (resolves WebSocket issues)
    location /ws/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-SSL-Client-Verify \$ssl_client_verify;
        proxy_set_header X-SSL-Client-DN \$ssl_client_s_dn;
        proxy_set_header X-SSL-Client-Serial \$ssl_client_serial;
        proxy_set_header X-SSL-Client-Fingerprint \$ssl_client_fingerprint;
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }
}
EOF
    
    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
    
    # Remove default site
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test configuration
    if nginx -t; then
        sudo systemctl reload nginx
        log_success "Nginx configuration applied successfully"
    else
        log_error "Nginx configuration test failed"
        return 1
    fi
}

# =============================================================================
# FIREWALL CONFIGURATION (FROM deployment_A/network_setup)
# =============================================================================

configure_firewall() {
    log_info "Configuring advanced firewall rules for $NETWORK_TYPE deployment..."
    
    # Backup existing rules
    if command -v ufw &> /dev/null; then
        log_info "Backing up existing firewall rules..."
        sudo ufw status verbose > "/root/ufw-backup-$(date +%Y%m%d_%H%M%S).txt" 2>/dev/null || true
    fi
    
    # Install and configure UFW
    if ! command -v ufw &> /dev/null; then
        log_info "Installing UFW firewall..."
        sudo apt-get update -qq
        sudo apt-get install -y ufw
    fi
    
    # Install fail2ban for intrusion prevention
    if ! command -v fail2ban-server &> /dev/null; then
        log_info "Installing fail2ban..."
        sudo apt-get install -y fail2ban
    fi
    
    case "$NETWORK_TYPE" in
        "lan")
            configure_lan_firewall
            ;;
        "hybrid")
            configure_hybrid_firewall
            ;;
        "wan")
            configure_wan_firewall
            ;;
        *)
            log_warn "Unknown network type, applying default firewall rules"
            configure_default_firewall
            ;;
    esac
    
    # Configure fail2ban
    configure_fail2ban
    
    # Enable and start UFW
    echo 'y' | sudo ufw enable
    
    log_success "Advanced firewall configuration completed"
    sudo ufw status verbose | tee -a "$LOG_FILE"
}

configure_lan_firewall() {
    log_info "Configuring LAN-only firewall (192.168.10.x subnet protection)..."
    
    # Reset UFW to clean state
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH from LAN subnet only
    sudo ufw allow from ${LAN_SUBNET} to any port 22 proto tcp comment 'SSH from LAN only'
    
    # Allow HTTP redirect (port 8080) from LAN subnet
    sudo ufw allow from ${LAN_SUBNET} to any port 8080 proto tcp comment 'HTTP redirect from LAN'
    
    # Allow HTTPS (port 8443) from LAN subnet only
    sudo ufw allow from ${LAN_SUBNET} to any port 8443 proto tcp comment 'HTTPS from LAN only'
    
    # Allow localhost connections
    sudo ufw allow from 127.0.0.1 comment 'Localhost access'
    
    # Allow Django application (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8000 proto tcp comment 'Django app localhost'
    
    # Allow WebSocket (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8001 proto tcp comment 'WebSocket localhost'
    
    # Allow PostgreSQL (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 5432 proto tcp comment 'PostgreSQL localhost'
    
    # Allow Redis (localhost only)  
    sudo ufw allow from 127.0.0.1 to any port 6379 proto tcp comment 'Redis localhost'
    
    # Deny all other traffic
    sudo ufw deny from any to any comment 'Deny all other traffic'
    
    log_success "LAN firewall configured - Access restricted to ${LAN_SUBNET}"
}

configure_wan_firewall() {
    log_info "Configuring WAN firewall (public internet with security)..."
    
    # Reset UFW to clean state
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (with rate limiting via fail2ban)
    sudo ufw allow 22/tcp comment 'SSH access'
    
    # Allow HTTP (for redirects and ACME challenges)
    sudo ufw allow 80/tcp comment 'HTTP access'
    
    # Allow HTTPS (main service port)
    sudo ufw allow 443/tcp comment 'HTTPS access'
    
    # Allow localhost connections
    sudo ufw allow from 127.0.0.1 comment 'Localhost access'
    
    # Allow Django application (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8000 proto tcp comment 'Django app localhost'
    
    # Allow WebSocket (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8001 proto tcp comment 'WebSocket localhost'
    
    # Allow PostgreSQL (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 5432 proto tcp comment 'PostgreSQL localhost'
    
    # Allow Redis (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 6379 proto tcp comment 'Redis localhost'
    
    log_success "WAN firewall configured - Public access on ports 80/443"
}

configure_hybrid_firewall() {
    log_info "Configuring hybrid firewall (LAN + WAN with complete isolation)..."
    
    # Reset UFW to clean state
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # SSH access from both networks
    sudo ufw allow from ${LAN_SUBNET} to any port 22 proto tcp comment 'SSH from LAN'
    sudo ufw allow 22/tcp comment 'SSH from WAN'
    
    # LAN HTTP redirect (port 8080) - LAN subnet only
    sudo ufw allow from ${LAN_SUBNET} to any port 8080 proto tcp comment 'LAN HTTP redirect'
    
    # LAN HTTPS (port 8443) - LAN subnet only  
    sudo ufw allow from ${LAN_SUBNET} to any port 8443 proto tcp comment 'LAN HTTPS access'
    
    # WAN HTTP/HTTPS (ports 80/443) - public access
    sudo ufw allow 80/tcp comment 'WAN HTTP access'
    sudo ufw allow 443/tcp comment 'WAN HTTPS access'
    
    # Allow localhost connections
    sudo ufw allow from 127.0.0.1 comment 'Localhost access'
    
    # Allow Django application (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8000 proto tcp comment 'Django app localhost'
    
    # Allow WebSocket (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 8001 proto tcp comment 'WebSocket localhost'
    
    # Allow PostgreSQL (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 5432 proto tcp comment 'PostgreSQL localhost'
    
    # Allow Redis (localhost only)
    sudo ufw allow from 127.0.0.1 to any port 6379 proto tcp comment 'Redis localhost'
    
    log_success "Hybrid firewall configured:"
    log_success "- LAN: ${LAN_SUBNET} access to port 8443"
    log_success "- WAN: Public access to ports 80/443"
}

configure_default_firewall() {
    log_info "Configuring default firewall rules..."
    
    # Reset UFW to clean state
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH
    sudo ufw allow 22/tcp comment 'SSH access'
    
    # Allow HTTP/HTTPS based on network type
    sudo ufw allow 80/tcp comment 'HTTP access'
    if [ "$NETWORK_TYPE" = "lan" ]; then
        sudo ufw allow 8443/tcp comment 'HTTPS LAN access'
    else
        sudo ufw allow 443/tcp comment 'HTTPS access'
    fi
    
    # Allow localhost
    sudo ufw allow from 127.0.0.1 comment 'Localhost access'
}

configure_fail2ban() {
    log_info "Configuring fail2ban intrusion prevention..."
    
    # Create fail2ban configuration for SSH protection
    sudo tee /etc/fail2ban/jail.local > /dev/null << EOF
# ArmGuard fail2ban configuration
# Generated by 02_config.sh on $(date)

[DEFAULT]
# Ban duration (24 hours)
bantime = 86400

# Number of failures before ban
maxretry = 3

# Find time window (10 minutes)
findtime = 600

# Ignore local networks
ignoreip = 127.0.0.1/8 ${LAN_SUBNET:-192.168.0.0/16} ${SERVER_LAN_IP:-127.0.0.1}

[ssh]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 86400

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 600
bantime = 3600
EOF
    
    # Create custom nginx filters
    sudo tee /etc/fail2ban/filter.d/nginx-limit-req.conf > /dev/null << 'EOF'
# Fail2ban filter for nginx rate limiting
[Definition]
failregex = limiting requests, excess: .* by zone .*, client: <HOST>
ignoreregex =
EOF
    
    # Enable and start fail2ban
    sudo systemctl enable fail2ban
    sudo systemctl restart fail2ban
    
    # Verify fail2ban status
    if sudo systemctl is-active --quiet fail2ban; then
        log_success "fail2ban configured and running"
        sudo fail2ban-client status | tee -a "$LOG_FILE"
    else
        log_error "fail2ban failed to start"
        return 1
    fi
}

# =============================================================================
# NETWORK VERIFICATION (FROM network_setup/verify-network.sh)
# =============================================================================

verify_network_configuration() {
    log_info "Verifying network configuration..."
    
    local verification_passed=true
    
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Network Configuration Verification${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Verify network interfaces
    case "$NETWORK_TYPE" in
        "lan"|"hybrid")
            verify_lan_network
            if [ $? -ne 0 ]; then verification_passed=false; fi
            ;;
    esac
    
    case "$NETWORK_TYPE" in
        "wan"|"hybrid") 
            verify_wan_network
            if [ $? -ne 0 ]; then verification_passed=false; fi
            ;;
    esac
    
    # Verify SSL certificates
    verify_ssl_certificates
    if [ $? -ne 0 ]; then verification_passed=false; fi
    
    # Verify firewall rules
    verify_firewall_rules
    if [ $? -ne 0 ]; then verification_passed=false; fi
    
    # Verify services
    verify_services
    if [ $? -ne 0 ]; then verification_passed=false; fi
    
    echo ""
    if [ "$verification_passed" = true ]; then
        log_success "✅ All network verification checks passed"
        return 0
    else
        log_error "❌ Some network verification checks failed"
        return 1
    fi
}

verify_lan_network() {
    log_info "Verifying LAN network configuration..."
    
    # Check LAN interface
    if ip addr show "$LAN_INTERFACE" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ LAN interface ($LAN_INTERFACE) exists${NC}"
    else
        echo -e "${RED}✗ LAN interface ($LAN_INTERFACE) not found${NC}"
        return 1
    fi
    
    # Check LAN IP configuration
    if ip addr show "$LAN_INTERFACE" | grep -q "$SERVER_LAN_IP"; then
        echo -e "${GREEN}✓ LAN IP ($SERVER_LAN_IP) configured${NC}"
    else
        echo -e "${YELLOW}⚠ LAN IP ($SERVER_LAN_IP) not configured (may be DHCP)${NC}"
    fi
    
    # Check LAN SSL certificates
    if [ -f "/etc/ssl/armguard/lan/cert.pem" ] && [ -f "/etc/ssl/armguard/lan/key.pem" ]; then
        echo -e "${GREEN}✓ LAN SSL certificates exist${NC}"
    else
        echo -e "${RED}✗ LAN SSL certificates missing${NC}"
        return 1
    fi
    
    # Check LAN nginx configuration
    if [ -f "/etc/nginx/sites-available/armguard-lan" ]; then
        echo -e "${GREEN}✓ LAN nginx configuration exists${NC}"
        if nginx -t 2>/dev/null; then
            echo -e "${GREEN}✓ LAN nginx configuration is valid${NC}"
        else
            echo -e "${RED}✗ LAN nginx configuration has errors${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ LAN nginx configuration missing${NC}"
        return 1
    fi
    
    return 0
}

verify_wan_network() {
    log_info "Verifying WAN network configuration..."
    
    # Check WAN interface
    if ip addr show "$WAN_INTERFACE" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ WAN interface ($WAN_INTERFACE) exists${NC}"
    else
        echo -e "${RED}✗ WAN interface ($WAN_INTERFACE) not found${NC}"
        return 1
    fi
    
    # Check internet connectivity
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Internet connectivity available${NC}"
    else
        echo -e "${RED}✗ No internet connectivity${NC}"
        return 1  
    fi
    
    # Check domain resolution
    if nslookup "$DEFAULT_DOMAIN" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Domain ($DEFAULT_DOMAIN) resolves${NC}"
    else
        echo -e "${YELLOW}⚠ Domain ($DEFAULT_DOMAIN) does not resolve${NC}"
    fi
    
    # Check WAN SSL certificates
    if [ -f "/etc/ssl/armguard/wan/cert.pem" ] && [ -f "/etc/ssl/armguard/wan/key.pem" ]; then
        echo -e "${GREEN}✓ WAN SSL certificates exist${NC}"
    else
        echo -e "${RED}✗ WAN SSL certificates missing${NC}"
        return 1
    fi
    
    # Check WAN nginx configuration
    if [ -f "/etc/nginx/sites-available/armguard-wan" ]; then
        echo -e "${GREEN}✓ WAN nginx configuration exists${NC}"
        if nginx -t 2>/dev/null; then
            echo -e "${GREEN}✓ WAN nginx configuration is valid${NC}"
        else
            echo -e "${RED}✗ WAN nginx configuration has errors${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ WAN nginx configuration missing${NC}"
        return 1
    fi
    
    return 0
}

verify_ssl_certificates() {
    log_info "Verifying SSL certificates..."
    
    case "$NETWORK_TYPE" in
        "lan")
            if openssl x509 -in "/etc/ssl/armguard/lan/cert.pem" -text -noout >/dev/null 2>&1; then
                echo -e "${GREEN}✓ LAN SSL certificate is valid${NC}"
                local cert_domains=$(openssl x509 -in "/etc/ssl/armguard/lan/cert.pem" -text -noout | grep -A1 "Subject Alternative Name" | tail -1)
                echo -e "${WHITE}  Certificate domains: $cert_domains${NC}"
            else
                echo -e "${RED}✗ LAN SSL certificate is invalid${NC}"
                return 1
            fi
            ;;
        "wan")
            if openssl x509 -in "/etc/ssl/armguard/wan/cert.pem" -text -noout >/dev/null 2>&1; then
                echo -e "${GREEN}✓ WAN SSL certificate is valid${NC}"
                local cert_expiry=$(openssl x509 -in "/etc/ssl/armguard/wan/cert.pem" -text -noout | grep "Not After" | cut -d: -f2-)
                echo -e "${WHITE}  Certificate expires: $cert_expiry${NC}"
            else
                echo -e "${RED}✗ WAN SSL certificate is invalid${NC}"
                return 1
            fi
            ;;
        "hybrid")
            # Check both certificates
            local lan_valid=true
            local wan_valid=true
            
            if openssl x509 -in "/etc/ssl/armguard/lan/cert.pem" -text -noout >/dev/null 2>&1; then
                echo -e "${GREEN}✓ LAN SSL certificate is valid${NC}"
            else
                echo -e "${RED}✗ LAN SSL certificate is invalid${NC}"
                lan_valid=false
            fi
            
            if openssl x509 -in "/etc/ssl/armguard/wan/cert.pem" -text -noout >/dev/null 2>&1; then
                echo -e "${GREEN}✓ WAN SSL certificate is valid${NC}"
            else
                echo -e "${RED}✗ WAN SSL certificate is invalid${NC}"
                wan_valid=false
            fi
            
            if [ "$lan_valid" = false ] || [ "$wan_valid" = false ]; then
                return 1
            fi
            ;;
    esac
    
    return 0
}

verify_firewall_rules() {
    log_info "Verifying firewall configuration..."
    
    # Check UFW status
    if sudo ufw status | grep -q "Status: active"; then
        echo -e "${GREEN}✓ UFW firewall is active${NC}"
    else
        echo -e "${RED}✗ UFW firewall is not active${NC}"
        return 1
    fi
    
    # Check fail2ban status
    if sudo systemctl is-active --quiet fail2ban; then
        echo -e "${GREEN}✓ fail2ban is active${NC}"
        local ssh_jail_status=$(sudo fail2ban-client status ssh 2>/dev/null | grep "Currently banned" | awk '{print $3}')
        echo -e "${WHITE}  SSH currently banned IPs: ${ssh_jail_status:-0}${NC}"
    else
        echo -e "${RED}✗ fail2ban is not active${NC}"
        return 1
    fi
    
    # Verify network-specific rules
    case "$NETWORK_TYPE" in
        "lan")
            if sudo ufw status | grep -q "8443/tcp"; then
                echo -e "${GREEN}✓ LAN HTTPS port (8443) allowed${NC}"
            else
                echo -e "${RED}✗ LAN HTTPS port (8443) not allowed${NC}"  
                return 1
            fi
            ;;
        "wan")
            if sudo ufw status | grep -q "443/tcp"; then
                echo -e "${GREEN}✓ WAN HTTPS port (443) allowed${NC}"
            else
                echo -e "${RED}✗ WAN HTTPS port (443) not allowed${NC}"
                return 1
            fi
            ;;
        "hybrid")
            if sudo ufw status | grep -q "8443/tcp" && sudo ufw status | grep -q "443/tcp"; then
                echo -e "${GREEN}✓ Both LAN (8443) and WAN (443) ports allowed${NC}"
            else
                echo -e "${RED}✗ Missing LAN or WAN port configuration${NC}"
                return 1
            fi
            ;;
    esac
    
    return 0
}

verify_services() {
    log_info "Verifying system services..."
    
    # Check nginx
    if sudo systemctl is-active --quiet nginx; then
        echo -e "${GREEN}✓ Nginx is running${NC}"
    else
        echo -e "${RED}✗ Nginx is not running${NC}"
        return 1
    fi
    
    # Check PostgreSQL
    if sudo systemctl is-active --quiet postgresql; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not running${NC}"
        return 1
    fi
    
    # Check Redis
    if sudo systemctl is-active --quiet redis-server; then
        echo -e "${GREEN}✓ Redis is running${NC}"
    else
        echo -e "${YELLOW}⚠ Redis is not running (optional service)${NC}"
    fi
    
    return 0
}

# =============================================================================
# MAIN CONFIGURATION EXECUTION
# =============================================================================

main() {
    log_info "Starting ArmGuard configuration phase..."
    log_info "Logging to: $LOG_FILE"
    
    # Interactive configuration
    interactive_config
    
    echo -e "${YELLOW}🔧 Applying configurations...${NC}"
    echo ""
    
    # Database configuration
    configure_database
    
    # SSL certificate setup
    configure_ssl_certificates
    
    # Application configuration 
    configure_django_application
    
    # Service configuration
    configure_redis
    configure_nginx
    
    # Security configuration
    configure_firewall
    
    echo ""
    echo -e "${YELLOW}🔍 Verifying network configuration...${NC}"
    verify_network_configuration
    
    echo ""
    log_success "✅ Configuration phase completed successfully!"
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                       ${WHITE}CONFIGURATION PHASE COMPLETED${GREEN}                       ║${NC}"
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}║  Configuration Summary:                                                       ║${NC}"
    echo -e "${GREEN}║  • Network Type: ${WHITE}${NETWORK_TYPE}${GREEN}                                                    ║${NC}"
    
    case "$NETWORK_TYPE" in
        "lan")
            echo -e "${GREEN}║  • LAN Network: ${WHITE}${LAN_SUBNET}${GREEN}                                           ║${NC}"
            echo -e "${GREEN}║  • Server IP: ${WHITE}${SERVER_LAN_IP}${GREEN} (${LAN_INTERFACE})                                    ║${NC}"
            echo -e "${GREEN}║  • SSL: ${WHITE}mkcert (internal)${GREEN}                                             ║${NC}"
            echo -e "${GREEN}║  • Access: ${WHITE}https://${SERVER_LAN_IP}:8443${GREEN}                                    ║${NC}"
            ;;
        "wan")
            echo -e "${GREEN}║  • Domain: ${WHITE}${DEFAULT_DOMAIN}${GREEN}                                        ║${NC}"
            echo -e "${GREEN}║  • SSL: ${WHITE}ACME (${ACME_SERVER:-letsencrypt})${GREEN}                                        ║${NC}"
            echo -e "${GREEN}║  • Access: ${WHITE}https://${DEFAULT_DOMAIN}${GREEN}                                    ║${NC}"
            ;;
        "hybrid")
            echo -e "${GREEN}║  • LAN: ${WHITE}${SERVER_LAN_IP}:8443${GREEN} (Armory PC)                               ║${NC}"
            echo -e "${GREEN}║  • WAN: ${WHITE}${DEFAULT_DOMAIN}:443${GREEN} (Personnel)                               ║${NC}"
            echo -e "${GREEN}║  • SSL: ${WHITE}mkcert (LAN) + ACME (WAN)${GREEN}                                    ║${NC}"
            ;;
    esac
    
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}║  Network Features Integrated:                                                ║${NC}"
    echo -e "${GREEN}║  ✅ Advanced firewall with intrusion prevention                             ║${NC}"
    echo -e "${GREEN}║  ✅ Interface-specific SSL certificates                                     ║${NC}"
    echo -e "${GREEN}║  ✅ Network isolation and access control                                    ║${NC}"
    echo -e "${GREEN}║  ✅ Comprehensive security headers                                          ║${NC}"
    echo -e "${GREEN}║  ✅ Rate limiting and DDoS protection                                       ║${NC}"
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}║  Next: Run 03_services.sh to deploy application services                     ║${NC}"
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Execute main function
main "$@"