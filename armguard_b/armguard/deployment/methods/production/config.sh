#!/bin/bash

################################################################################
# ArmGuard Deployment Configuration File
# 
# Centralized configuration for all deployment scripts
# Source this file in other scripts: source deployment/config.sh
################################################################################

# Project Configuration
export PROJECT_NAME="armguard"
export PROJECT_DIR="${ARMGUARD_PROJECT_DIR:-/var/www/armguard}"
export VENV_DIR="${PROJECT_DIR}/.venv"

# Service Configuration
export SERVICE_NAME="gunicorn-armguard"
export SOCKET_PATH="${ARMGUARD_SOCKET_PATH:-/run/gunicorn-armguard.sock}"
export RUN_USER="${ARMGUARD_RUN_USER:-www-data}"
export RUN_GROUP="${ARMGUARD_RUN_GROUP:-www-data}"

# Network Configuration
export DEFAULT_DOMAIN="${ARMGUARD_DOMAIN:-armguard.local}"
export DEFAULT_PORT="${ARMGUARD_PORT:-8000}"

# Network Interfaces (for hybrid setup)
export LAN_INTERFACE="${ARMGUARD_LAN_INTERFACE:-eth1}"
export WAN_INTERFACE="${ARMGUARD_WAN_INTERFACE:-eth0}"
export LAN_SUBNET="${ARMGUARD_LAN_SUBNET:-192.168.10.0/24}"
export SERVER_LAN_IP="${ARMGUARD_LAN_IP:-192.168.10.1}"
export ARMORY_PC_IP="${ARMGUARD_ARMORY_IP:-192.168.10.2}"

# Directory Configuration
export LOG_DIR="/var/log/armguard"
export BACKUP_DIR="${PROJECT_DIR}/backups"
export CERT_DIR="/etc/ssl/armguard"
export LAN_CERT_DIR="${CERT_DIR}/lan"
export WAN_CERT_DIR="/etc/letsencrypt/live"
export MEDIA_DIR="${PROJECT_DIR}/core/media"
export STATIC_DIR="${PROJECT_DIR}/staticfiles"

# Database Configuration
export DB_ENGINE="${ARMGUARD_DB_ENGINE:-sqlite}"
export DB_FILE="${PROJECT_DIR}/db.sqlite3"
export DB_BACKUP_RETENTION="${ARMGUARD_BACKUP_RETENTION:-5}"

# PostgreSQL Configuration (when DB_ENGINE=postgresql)
export POSTGRES_DB="${ARMGUARD_DB_NAME:-armguard}"
export POSTGRES_USER="${ARMGUARD_DB_USER:-armguard}"
export POSTGRES_PASSWORD="${ARMGUARD_DB_PASSWORD:-}"
export POSTGRES_HOST="${ARMGUARD_DB_HOST:-localhost}"
export POSTGRES_PORT="${ARMGUARD_DB_PORT:-5432}"
export POSTGRES_SSL_MODE="${ARMGUARD_DB_SSL_MODE:-prefer}"

# Database Pool Configuration
export DB_CONN_POOL_SIZE="${ARMGUARD_DB_POOL_SIZE:-20}"
export DB_CONN_MAX_OVERFLOW="${ARMGUARD_DB_OVERFLOW:-30}"
export DB_CONN_TIMEOUT="${ARMGUARD_DB_TIMEOUT:-30}"

# Backup Configuration
export BACKUP_ENCRYPTION="${ARMGUARD_BACKUP_ENCRYPTION:-yes}"
export BACKUP_PASSWORD_FILE="${ARMGUARD_BACKUP_PASSWORD_FILE:-${PROJECT_DIR}/.backup_key}"
export BACKUP_COMPRESSION="${ARMGUARD_BACKUP_COMPRESSION:-yes}"
export BACKUP_VERIFICATION="${ARMGUARD_BACKUP_VERIFICATION:-yes}"

# Gunicorn Configuration
export GUNICORN_WORKERS="${ARMGUARD_WORKERS:-auto}"
export GUNICORN_TIMEOUT="${ARMGUARD_TIMEOUT:-60}"
export GUNICORN_MAX_REQUESTS="${ARMGUARD_MAX_REQUESTS:-1000}"
export GUNICORN_MAX_REQUESTS_JITTER="${ARMGUARD_MAX_REQUESTS_JITTER:-50}"

# Secrets Management Configuration
export SECRETS_BACKEND="${ARMGUARD_SECRETS_BACKEND:-file}"
export SECRETS_FILE_PATH="${ARMGUARD_SECRETS_FILE:-${PROJECT_DIR}/.secrets}"
export VAULT_ADDR="${ARMGUARD_VAULT_ADDR:-}"
export VAULT_TOKEN="${ARMGUARD_VAULT_TOKEN:-}"
export VAULT_PATH="${ARMGUARD_VAULT_PATH:-secret/armguard}"
export AWS_SECRETS_REGION="${ARMGUARD_AWS_REGION:-us-west-2}"
export AZURE_KEY_VAULT_URL="${ARMGUARD_AZURE_VAULT_URL:-}"

# Nginx Configuration
export NGINX_CLIENT_MAX_BODY_SIZE="${ARMGUARD_CLIENT_MAX_BODY_SIZE:-10M}"
export NGINX_RATE_LIMIT_ZONE="${ARMGUARD_RATE_LIMIT_ZONE:-10m}"
export NGINX_RATE_LIMIT="${ARMGUARD_RATE_LIMIT:-10r/s}"
export NGINX_SITES_AVAILABLE="/etc/nginx/sites-available"
export NGINX_SITES_ENABLED="/etc/nginx/sites-enabled"

# Security Configuration
export ENABLE_FIREWALL="${ARMGUARD_ENABLE_FIREWALL:-yes}"
export ENABLE_FAIL2BAN="${ARMGUARD_ENABLE_FAIL2BAN:-yes}"
export SSL_TYPE="${ARMGUARD_SSL_TYPE:-mkcert}"

# Update Configuration
export UPDATE_BACKUP_BEFORE="${ARMGUARD_UPDATE_BACKUP:-yes}"
export UPDATE_RUN_MIGRATIONS="${ARMGUARD_UPDATE_MIGRATIONS:-yes}"
export UPDATE_COLLECT_STATIC="${ARMGUARD_UPDATE_STATIC:-yes}"
export UPDATE_HEALTH_CHECK="${ARMGUARD_UPDATE_HEALTH_CHECK:-yes}"

# Colors for terminal output
export RED='\033[0;31m'
export GREEN='\033[0;32m'
export YELLOW='\033[1;33m'
export BLUE='\033[0;34m'
export CYAN='\033[0;36m'
export MAGENTA='\033[0;35m'
export NC='\033[0m' # No Color

# Helper Functions
calculate_workers() {
    if [ "$GUNICORN_WORKERS" = "auto" ]; then
        CPU_CORES=$(nproc)
        echo $((2 * CPU_CORES + 1))
    else
        echo "$GUNICORN_WORKERS"
    fi
}

detect_architecture() {
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)
            echo "amd64"
            ;;
        aarch64|arm64)
            echo "arm64"
            ;;
        armv7l)
            echo "armv7"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

detect_platform() {
    # Detect if running on Raspberry Pi
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(cat /proc/device-tree/model)
        if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
            echo "raspberry-pi"
            return
        fi
    fi
    
    # Check for virtual machine
    if systemd-detect-virt &>/dev/null; then
        VIRT=$(systemd-detect-virt)
        if [ "$VIRT" != "none" ]; then
            echo "virtual-machine ($VIRT)"
            return
        fi
    fi
    
    echo "physical"
}

get_server_ip() {
    hostname -I | awk '{print $1}'
}

check_required_commands() {
    local missing_cmds=()
    
    for cmd in "$@"; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_cmds+=("$cmd")
        fi
    done
    
    if [ ${#missing_cmds[@]} -ne 0 ]; then
        echo -e "${RED}ERROR: Missing required commands: ${missing_cmds[*]}${NC}" >&2
        return 1
    fi
    
    return 0
}

is_service_running() {
    systemctl is-active --quiet "$1"
}

is_port_listening() {
    netstat -tuln | grep -q ":$1 "
}

# Print configuration (for debugging)
print_config() {
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Deployment Configuration${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Project:${NC}"
    echo "  Name:           $PROJECT_NAME"
    echo "  Directory:      $PROJECT_DIR"
    echo "  Virtual Env:    $VENV_DIR"
    echo ""
    echo -e "${CYAN}Service:${NC}"
    echo "  Name:           $SERVICE_NAME"
    echo "  Socket:         $SOCKET_PATH"
    echo "  User:           $RUN_USER"
    echo "  Group:          $RUN_GROUP"
    echo "  Workers:        $(calculate_workers)"
    echo ""
    echo -e "${CYAN}Directories:${NC}"
    echo "  Logs:           $LOG_DIR"
    echo "  Backups:        $BACKUP_DIR"
    echo "  Static:         $STATIC_DIR"
    echo "  Media:          $MEDIA_DIR"
    echo ""
    echo -e "${CYAN}Platform:${NC}"
    echo "  Architecture:   $(detect_architecture)"
    echo "  Type:           $(detect_platform)"
    echo "  IP Address:     $(get_server_ip)"
    echo ""
}

# Export functions
export -f calculate_workers
export -f detect_architecture
export -f detect_platform
export -f get_server_ip
export -f check_required_commands
export -f is_service_running
export -f is_port_listening
export -f print_config
