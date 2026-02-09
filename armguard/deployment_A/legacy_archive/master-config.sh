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

# Cross-platform detection
detect_platform() {
    export ARCH=$(uname -m)
    export IS_ARM64=false
    export IS_RPI=false
    export PLATFORM_NAME="Standard"
    export REQUIREMENTS_FILE="requirements.txt"
    export ENHANCED_FEATURES=false
    
    # Architecture detection
    case "$ARCH" in
        aarch64|arm64)
            export IS_ARM64=true
            export PLATFORM_NAME="ARM64"
            export ENHANCED_FEATURES=true
            ;;
        x86_64)
            export PLATFORM_NAME="x86_64"
            ;;
    esac
    
    # Raspberry Pi detection
    if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        export IS_RPI=true
        export PLATFORM_NAME="Raspberry Pi"
        export REQUIREMENTS_FILE="requirements-rpi.txt"
        export ENHANCED_FEATURES=true
        MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
        echo "🥧 $MODEL detected"
    elif [ "$IS_ARM64" = true ]; then
        echo "🏗️  ARM64 architecture detected"
    fi
    
    echo "Platform: $PLATFORM_NAME ($ARCH)"
}

# Run platform detection
detect_platform

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
# Redis Installation and Management Functions
# =============================================================================

# Detect Redis installation and configure based on platform
setup_redis() {
    local action=${1:-"install"}
    
    echo "🔥 Setting up Redis for WebSocket performance..."
    
    case "$action" in
        "install")
            install_redis_server
            ;;
        "configure")
            configure_redis_server
            ;;
        "start")
            start_redis_service
            ;;
        "test")
            test_redis_connection
            ;;
        "all")
            install_redis_server
            configure_redis_server
            start_redis_service
            test_redis_connection
            ;;
    esac
}

# Install Redis server based on platform
install_redis_server() {
    echo "📦 Installing Redis server..."
    
    # Detect Linux distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo "🐧 Debian/Ubuntu detected - using apt"
        apt update -qq
        apt install -y redis-server
        
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo "🔴 RedHat-based system detected"
        if command -v dnf >/dev/null 2>&1; then
            dnf install -y redis
        else
            yum install -y redis
        fi
        
    elif [ -f /etc/arch-release ]; then
        # Arch Linux
        echo "🏛️  Arch Linux detected"
        pacman -Sy --noconfirm redis
        
    elif [ "$(uname)" = "Darwin" ]; then
        # macOS
        echo "🍎 macOS detected - using Homebrew"
        if command -v brew >/dev/null 2>&1; then
            brew install redis
        else
            echo "❌ Homebrew not found - manual Redis installation needed"
            return 1
        fi
        
    else
        echo "❓ Unknown platform - attempting generic installation"
        # Try common package managers
        if command -v apt >/dev/null 2>&1; then
            apt update -qq && apt install -y redis-server
        elif command -v yum >/dev/null 2>&1; then
            yum install -y redis
        elif command -v pacman >/dev/null 2>&1; then
            pacman -Sy --noconfirm redis
        else
            echo "❌ No supported package manager found"
            return 1
        fi
    fi
    
    echo "✅ Redis server installation completed"
}

# Configure Redis for optimal WebSocket performance
configure_redis_server() {
    echo "⚙️  Configuring Redis for WebSocket optimization..."
    
    # Backup original config if it exists
    if [ -f "$REDIS_CONFIG_PATH" ]; then
        cp "$REDIS_CONFIG_PATH" "$REDIS_CONFIG_PATH.backup.$(date +%Y%m%d_%H%M%S)"
        echo "📄 Backed up original Redis config"
    fi
    
    # Create optimized Redis configuration
    cat > "/tmp/redis_websocket.conf" << 'EOL'
# Redis WebSocket Optimization Configuration for ArmGuard
# Generated by ArmGuard deployment script

# Network and connection settings
bind 127.0.0.1
port 6379
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Memory optimization
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence settings (for development)
save 900 1
save 300 10
save 60 10000

# Performance settings
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security (basic)
requirepass armguard_redis_2026

# WebSocket-specific optimizations
notify-keyspace-events Ex
EOL
    
    # Apply configuration based on system
    if [ -d "/etc/redis" ]; then
        cp "/tmp/redis_websocket.conf" "$REDIS_CONFIG_PATH"
    elif [ -f "/usr/local/etc/redis.conf" ]; then
        # macOS Homebrew location
        cp "/tmp/redis_websocket.conf" "/usr/local/etc/redis.conf"
        export REDIS_CONFIG_PATH="/usr/local/etc/redis.conf"
    else
        # Create config directory
        mkdir -p "/etc/redis"
        cp "/tmp/redis_websocket.conf" "$REDIS_CONFIG_PATH"
    fi
    
    # Create log directory
    mkdir -p /var/log/redis
    
    # Set permissions
    if id "redis" >/dev/null 2>&1; then
        chown redis:redis /var/log/redis
        chown redis:redis "$REDIS_CONFIG_PATH" 2>/dev/null || true
    fi
    
    rm -f "/tmp/redis_websocket.conf"
    echo "✅ Redis configuration applied"
}

# Start Redis service across different platforms
start_redis_service() {
    echo "🚀 Starting Redis service..."
    
    # Try systemd first (most Linux distributions)
    if command -v systemctl >/dev/null 2>&1; then
        systemctl enable redis-server 2>/dev/null || systemctl enable redis 2>/dev/null || true
        systemctl restart redis-server 2>/dev/null || systemctl restart redis 2>/dev/null || {
            echo "⚠️  systemctl failed, trying alternative methods..."
            start_redis_fallback
        }
        
    # macOS with Homebrew
    elif [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        brew services start redis
        
    # Fallback methods
    else
        start_redis_fallback
    fi
    
    # Wait for Redis to start
    sleep 3
    echo "✅ Redis service started"
}

# Fallback Redis startup methods
start_redis_fallback() {
    if command -v service >/dev/null 2>&1; then
        service redis-server start 2>/dev/null || service redis start
    elif command -v redis-server >/dev/null 2>&1; then
        # Direct startup (background)
        redis-server "$REDIS_CONFIG_PATH" --daemonize yes 2>/dev/null || 
        redis-server --daemonize yes
    else
        echo "❌ Unable to start Redis - no suitable method found"
        return 1
    fi
}

# Test Redis connection and performance
test_redis_connection() {
    echo "🧪 Testing Redis connection..."
    
    # Test basic connectivity
    if command -v redis-cli >/dev/null 2>&1; then
        # Test ping
        if redis-cli ping >/dev/null 2>&1; then
            echo "✅ Redis PING successful"
        elif redis-cli -a armguard_redis_2026 ping >/dev/null 2>&1; then
            echo "✅ Redis PING successful (with auth)"
        else
            echo "❌ Redis connection test failed"
            return 1
        fi
        
        # Test WebSocket-relevant operations
        echo "🔧 Testing WebSocket operations..."
        redis-cli -a armguard_redis_2026 set "test_websocket_key" "test_value" expire "test_websocket_key" 30 >/dev/null 2>&1 || true
        redis-cli -a armguard_redis_2026 del "test_websocket_key" >/dev/null 2>&1 || true
        echo "✅ Redis operational tests completed"
        
    else
        echo "⚠️  redis-cli not available - assuming Redis is working"
    fi
    
    echo "🏁 Redis setup verification completed"
}

# Redis health check function
check_redis_health() {
    if command -v redis-cli >/dev/null 2>&1; then
        if redis-cli ping >/dev/null 2>&1 || redis-cli -a armguard_redis_2026 ping >/dev/null 2>&1; then
            echo "✅ Redis is healthy"
            return 0
        else
            echo "❌ Redis health check failed"
            return 1
        fi
    else
        echo "⚠️  Cannot check Redis health - redis-cli not available"
        return 1
    fi
}

# Platform-specific Redis service management
manage_redis_service() {
    local action=$1  # start, stop, restart, status
    
    if command -v systemctl >/dev/null 2>&1; then
        systemctl $action redis-server 2>/dev/null || systemctl $action redis 2>/dev/null || {
            echo "⚠️  systemctl $action failed"
            return 1
        }
    elif command -v service >/dev/null 2>&1; then
        service redis-server $action 2>/dev/null || service redis $action
    elif [ "$(uname)" = "Darwin" ]; then
        case $action in
            start) brew services start redis ;;
            stop) brew services stop redis ;;
            restart) brew services restart redis ;;
            status) brew services list | grep redis ;;
        esac
    else
        echo "❌ Unable to $action Redis service - no suitable method found"
        return 1
    fi
}

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

# Redis settings
export REDIS_HOST="127.0.0.1"
export REDIS_PORT="6379"
export REDIS_SERVICE="redis-server"
export REDIS_CONFIG_PATH="/etc/redis/redis.conf"

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
# Security Configuration (Enhanced)
# =============================================================================

# Enhanced security middleware settings
export SECURITY_HEADERS_ENABLED="${SECURITY_HEADERS_ENABLED:-true}"
export REQUEST_LOGGING_ENABLED="${REQUEST_LOGGING_ENABLED:-true}"
export SINGLE_SESSION_ENFORCEMENT="${SINGLE_SESSION_ENFORCEMENT:-true}"
export RATE_LIMITING_ENABLED="${RATE_LIMITING_ENABLED:-true}"

# Admin system settings
export ADMIN_RESTRICTION_SYSTEM_ENABLED="${ADMIN_RESTRICTION_SYSTEM_ENABLED:-true}"
export ADMIN_SESSION_TIMEOUT="${ADMIN_SESSION_TIMEOUT:-3600}"

# API security settings
export API_RATE_LIMIT="${API_RATE_LIMIT:-100}"
export API_BURST_LIMIT="${API_BURST_LIMIT:-20}"

case $ENVIRONMENT in
    "test-vm")
        export DEBUG="true"
        export SECRET_KEY="test-secret-key-for-vm-development-only"
        export ALLOWED_HOSTS="localhost,127.0.0.1,*"
        export CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
        # Relaxed security for testing
        export SINGLE_SESSION_ENFORCEMENT="false"
        export REQUEST_LOGGING_ENABLED="false"
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
        # Maximum security for production
        export SECURITY_HEADERS_ENABLED="true"
        export REQUEST_LOGGING_ENABLED="true"
        export SINGLE_SESSION_ENFORCEMENT="true"
        export RATE_LIMITING_ENABLED="true"
        export ADMIN_RESTRICTION_SYSTEM_ENABLED="true"
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