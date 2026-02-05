#!/bin/bash

# =============================================================================
# ArmGuard Master Configuration
# Unified configuration for all deployment methods
# =============================================================================

# Version and metadata
export ARMGUARD_VERSION="2.0.0"
export DEPLOYMENT_DATE=$(date '+%Y-%m-%d %H:%M:%S')
export DEPLOYMENT_USER=$(whoami)

# =============================================================================
# Environment Detection
# =============================================================================

# Detect environment type
if [ -d "/mnt/hgfs" ] || [ "$VM_ENVIRONMENT" = "true" ]; then
    export ENVIRONMENT="test-vm"
elif [ -f "/.dockerenv" ]; then
    export ENVIRONMENT="docker-testing"
elif [ -f "/etc/systemd/system/armguard.service" ] || [ "$PRODUCTION" = "true" ]; then
    export ENVIRONMENT="production"
else
    export ENVIRONMENT="development"
fi

echo "Detected environment: $ENVIRONMENT"

# =============================================================================
# Common Configuration
# =============================================================================

# Application settings
export APP_NAME="armguard"
export APP_USER="armguard"
export APP_GROUP="armguard"

# Python settings
export PYTHON_VERSION="3.11"
export VENV_PATH="venv"

# =============================================================================
# Environment-Specific Paths
# =============================================================================

case $ENVIRONMENT in
    "test-vm")
        export BASE_DIR="/mnt/hgfs/Armguard"
        export PROJECT_DIR="$BASE_DIR/armguard"
        export STATIC_DIR="$PROJECT_DIR/staticfiles"
        export MEDIA_DIR="$PROJECT_DIR/media"
        export LOG_DIR="$PROJECT_DIR/logs"
        export BACKUP_DIR="$BASE_DIR/backups"
        ;;
    
    "docker-testing")
        export BASE_DIR="/app"
        export PROJECT_DIR="$BASE_DIR"
        export STATIC_DIR="/var/www/armguard/staticfiles"
        export MEDIA_DIR="/var/www/armguard/media"
        export LOG_DIR="/var/log/armguard"
        export BACKUP_DIR="/var/backups/armguard"
        ;;
    
    "production")
        export BASE_DIR="/opt/armguard"
        export PROJECT_DIR="$BASE_DIR/armguard"
        export STATIC_DIR="/var/www/armguard/static"
        export MEDIA_DIR="/var/www/armguard/media"
        export LOG_DIR="/var/log/armguard"
        export BACKUP_DIR="/var/backups/armguard"
        ;;
    
    *)
        export BASE_DIR="$(pwd)"
        export PROJECT_DIR="$BASE_DIR"
        export STATIC_DIR="$PROJECT_DIR/staticfiles"
        export MEDIA_DIR="$PROJECT_DIR/media"
        export LOG_DIR="$PROJECT_DIR/logs"
        export BACKUP_DIR="$PROJECT_DIR/backups"
        ;;
esac

# =============================================================================
# Database Configuration
# =============================================================================

case $ENVIRONMENT in
    "test-vm")
        export DB_ENGINE="postgresql"
        export DB_NAME="armguard_test"
        export DB_USER="armguard_test"
        export DB_PASS="test_password123"
        export DB_HOST="localhost"
        export DB_PORT="5432"
        export TEST_DB_NAME="armguard_test"
        export TEST_DB_USER="armguard_test"
        export TEST_DB_PASS="test_password123"
        ;;
    
    "docker-testing")
        export DB_ENGINE="postgresql"
        export DB_NAME="armguard_test"
        export DB_USER="armguard"
        export DB_PASS="testpass123"
        export DB_HOST="postgres"
        export DB_PORT="5432"
        ;;
    
    "production")
        export DB_ENGINE="postgresql"
        export DB_NAME="armguard_prod"
        export DB_USER="armguard"
        export DB_PASS="${DB_PASSWORD:-$(openssl rand -base64 32)}"
        export DB_HOST="localhost"
        export DB_PORT="5432"
        ;;
    
    *)
        export DB_ENGINE="sqlite3"
        export DB_NAME="db.sqlite3"
        ;;
esac

# =============================================================================
# Redis Configuration
# =============================================================================

case $ENVIRONMENT in
    "test-vm")
        export REDIS_URL="redis://localhost:6379/1"
        ;;
    
    "docker-testing")
        export REDIS_URL="redis://redis:6379/0"
        ;;
    
    "production")
        export REDIS_URL="redis://localhost:6379/0"
        ;;
    
    *)
        export REDIS_URL="redis://localhost:6379/0"
        ;;
esac

# =============================================================================
# Web Server Configuration
# =============================================================================

case $ENVIRONMENT in
    "test-vm")
        export WEB_SERVER="nginx"
        export HTTP_PORT="80"
        export HTTPS_PORT="443"
        export DOMAIN="localhost"
        export SSL_ENABLED="false"
        ;;
    
    "docker-testing")
        export WEB_SERVER="nginx"
        export HTTP_PORT="80"
        export HTTPS_PORT="443"
        export DOMAIN="localhost"
        export SSL_ENABLED="false"
        ;;
    
    "production")
        export WEB_SERVER="nginx"
        export HTTP_PORT="80"
        export HTTPS_PORT="443"
        export DOMAIN="${DOMAIN:-armguard.local}"
        export SSL_ENABLED="${SSL_ENABLED:-true}"
        ;;
    
    *)
        export WEB_SERVER="development"
        export HTTP_PORT="8000"
        export HTTPS_PORT="8443"
        export DOMAIN="localhost"
        export SSL_ENABLED="false"
        ;;
esac

# =============================================================================
# Security Configuration
# =============================================================================

case $ENVIRONMENT in
    "test-vm")
        export DEBUG="true"
        export SECRET_KEY="test-secret-key-for-vm-development-only"
        export ALLOWED_HOSTS="localhost,127.0.0.1,*"
        export CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
        ;;
    
    "docker-testing")
        export DEBUG="false"
        export SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 50)}"
        export ALLOWED_HOSTS="localhost,127.0.0.1,nginx,app"
        export CORS_ALLOWED_ORIGINS="http://localhost,https://localhost"
        ;;
    
    "production")
        export DEBUG="false"
        export SECRET_KEY="${SECRET_KEY:-$(openssl rand -base64 50)}"
        export ALLOWED_HOSTS="${DOMAIN},www.${DOMAIN}"
        export CORS_ALLOWED_ORIGINS="https://${DOMAIN},https://www.${DOMAIN}"
        ;;
    
    *)
        export DEBUG="true"
        export SECRET_KEY="dev-secret-key-change-in-production"
        export ALLOWED_HOSTS="localhost,127.0.0.1"
        export CORS_ALLOWED_ORIGINS="http://localhost:3000"
        ;;
esac

# =============================================================================
# Monitoring and Logging
# =============================================================================

case $ENVIRONMENT in
    "production")
        export LOG_LEVEL="INFO"
        export ENABLE_MONITORING="true"
        export SENTRY_ENABLED="${SENTRY_ENABLED:-false}"
        export PROMETHEUS_ENABLED="true"
        ;;
    
    "docker-testing")
        export LOG_LEVEL="DEBUG"
        export ENABLE_MONITORING="true"
        export SENTRY_ENABLED="false"
        export PROMETHEUS_ENABLED="true"
        ;;
    
    *)
        export LOG_LEVEL="DEBUG"
        export ENABLE_MONITORING="false"
        export SENTRY_ENABLED="false"
        export PROMETHEUS_ENABLED="false"
        ;;
esac

# =============================================================================
# Backup Configuration
# =============================================================================

case $ENVIRONMENT in
    "production")
        export BACKUP_ENABLED="true"
        export BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
        export BACKUP_RETENTION_DAYS="30"
        export BACKUP_ENCRYPTION="true"
        ;;
    
    "test-vm")
        export BACKUP_ENABLED="false"
        export BACKUP_SCHEDULE="0 4 * * 0"  # Weekly on Sunday at 4 AM
        export BACKUP_RETENTION_DAYS="7"
        export BACKUP_ENCRYPTION="false"
        ;;
    
    *)
        export BACKUP_ENABLED="false"
        export BACKUP_RETENTION_DAYS="7"
        export BACKUP_ENCRYPTION="false"
        ;;
esac

# =============================================================================
# Feature Flags
# =============================================================================

case $ENVIRONMENT in
    "production")
        export ENABLE_API="true"
        export ENABLE_ADMIN="true"
        export ENABLE_DEBUG_TOOLBAR="false"
        export ENABLE_SILK_PROFILING="false"
        ;;
    
    "test-vm")
        export ENABLE_API="true"
        export ENABLE_ADMIN="true"
        export ENABLE_DEBUG_TOOLBAR="true"
        export ENABLE_SILK_PROFILING="true"
        ;;
    
    "docker-testing")
        export ENABLE_API="true"
        export ENABLE_ADMIN="true"
        export ENABLE_DEBUG_TOOLBAR="false"
        export ENABLE_SILK_PROFILING="false"
        ;;
    
    *)
        export ENABLE_API="true"
        export ENABLE_ADMIN="true"
        export ENABLE_DEBUG_TOOLBAR="true"
        export ENABLE_SILK_PROFILING="true"
        ;;
esac

# =============================================================================
# Network Configuration
# =============================================================================

# Auto-detect network settings
if command -v hostname &> /dev/null; then
    export HOST_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "127.0.0.1")
    export HOSTNAME=$(hostname 2>/dev/null || echo "localhost")
else
    export HOST_IP="127.0.0.1"
    export HOSTNAME="localhost"
fi

# Environment-specific network settings
case $ENVIRONMENT in
    "production")
        export BIND_IP="0.0.0.0"
        export PUBLIC_IP="${PUBLIC_IP:-$HOST_IP}"
        ;;
    
    "test-vm")
        export BIND_IP="0.0.0.0"
        export PUBLIC_IP="$HOST_IP"
        ;;
    
    *)
        export BIND_IP="127.0.0.1"
        export PUBLIC_IP="127.0.0.1"
        ;;
esac

# =============================================================================
# Utility Functions
# =============================================================================

# Color codes for output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "ERROR")
            echo -e "${RED}[$timestamp] ERROR: $message${NC}" >&2
            ;;
        "WARN")
            echo -e "${YELLOW}[$timestamp] WARN: $message${NC}"
            ;;
        "INFO")
            echo -e "${GREEN}[$timestamp] INFO: $message${NC}"
            ;;
        "DEBUG")
            if [ "$LOG_LEVEL" = "DEBUG" ]; then
                echo -e "${CYAN}[$timestamp] DEBUG: $message${NC}"
            fi
            ;;
        *)
            echo -e "${BLUE}[$timestamp] $level: $message${NC}"
            ;;
    esac
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local service_url=$1
    local service_name=$2
    local max_attempts=${3:-30}
    local attempt=0
    
    log "INFO" "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$service_url" | grep -qE "^(200|301|302)$"; then
            log "INFO" "$service_name is ready!"
            return 0
        fi
        
        attempt=$((attempt + 1))
        log "DEBUG" "Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
    done
    
    log "ERROR" "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Create directory with proper permissions
create_dir() {
    local dir_path=$1
    local owner=${2:-$APP_USER}
    local group=${3:-$APP_GROUP}
    local permissions=${4:-755}
    
    if [ ! -d "$dir_path" ]; then
        mkdir -p "$dir_path"
        
        if [ "$ENVIRONMENT" != "test-vm" ] && [ "$ENVIRONMENT" != "development" ]; then
            chown "$owner:$group" "$dir_path"
            chmod "$permissions" "$dir_path"
        fi
        
        log "INFO" "Created directory: $dir_path"
    fi
}

# Export all functions
export -f log command_exists wait_for_service create_dir

# =============================================================================
# Configuration Summary
# =============================================================================

log "INFO" "ArmGuard Configuration Loaded"
log "INFO" "Environment: $ENVIRONMENT"
log "INFO" "Project Dir: $PROJECT_DIR"
log "INFO" "Database: $DB_ENGINE ($DB_NAME)"
log "INFO" "Web Server: $WEB_SERVER ($DOMAIN)"
log "DEBUG" "Host IP: $HOST_IP"
log "DEBUG" "Debug Mode: $DEBUG"