#!/bin/bash

################################################################################
# ArmGuard Redis WebSocket Performance Installation Script
# 
# This script installs and configures Redis server for optimal WebSocket 
# performance in ArmGuard applications. Works across multiple platforms
# including Ubuntu, Debian, CentOS, RHEL, Fedora, Arch Linux, and macOS.
#
# Usage: 
#   sudo bash install-redis-websocket.sh
#   bash install-redis-websocket.sh --dry-run
#   bash install-redis-websocket.sh --test-only
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration variables
SCRIPT_NAME="ArmGuard Redis WebSocket Installer"
SCRIPT_VERSION="1.0.0"
REDIS_CONFIG_PATH="/etc/redis/redis.conf"
REDIS_PASSWORD="armguard_redis_2026"
REDIS_PORT="6379"
REDIS_HOST="127.0.0.1"

# Command line options
DRY_RUN=false
TEST_ONLY=false
VERBOSE=false

# Print banner
print_banner() {
    clear
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║       ArmGuard Redis WebSocket Performance Installer      ║"
    echo "║                                                            ║"
    echo "║  Optimizes WebSocket performance by installing Redis:     ║"
    echo "║  • High-capacity channel layer                            ║"
    echo "║  • Real-time notification delivery                        ║"
    echo "║  • Concurrent user connection handling                    ║"
    echo "║  • Memory-efficient message queuing                       ║"
    echo "║  • Cross-platform compatibility                           ║"
    echo "╚════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# Logging functions
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { [ "$VERBOSE" = true ] && echo -e "${PURPLE}[DEBUG]${NC} $1"; }
log_step() { echo -e "${CYAN}[STEP]${NC} $1"; }

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                log_info "Dry run mode enabled - no changes will be made"
                shift
                ;;
            --test-only)
                TEST_ONLY=true
                log_info "Test-only mode - will only test existing Redis installation"
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                log_info "Verbose mode enabled"
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Show help information
show_help() {
    cat << EOF
$SCRIPT_NAME v$SCRIPT_VERSION

USAGE:
    sudo $0 [OPTIONS]

OPTIONS:
    --dry-run       Show what would be done without making changes
    --test-only     Only test existing Redis installation 
    --verbose, -v   Enable verbose output
    --help, -h      Show this help message

EXAMPLES:
    sudo $0                    # Full Redis installation
    $0 --dry-run              # Preview installation steps
    $0 --test-only            # Test current Redis setup
    sudo $0 --verbose         # Install with detailed output

SUPPORTED PLATFORMS:
    • Ubuntu/Debian (apt)
    • RHEL/CentOS/Fedora (dnf/yum)
    • Arch Linux (pacman)
    • macOS (Homebrew)
EOF
}

# Detect the operating system and package manager
detect_platform() {
    log_step "Detecting platform..."
    
    if [ -f /etc/debian_version ]; then
        PLATFORM="debian"
        PKG_MANAGER="apt"
        PKG_INSTALL="apt install -y"
        PKG_UPDATE="apt update -qq"
        REDIS_PACKAGE="redis-server"
        REDIS_SERVICE="redis-server"
    elif [ -f /etc/redhat-release ]; then
        PLATFORM="redhat"
        if command -v dnf >/dev/null 2>&1; then
            PKG_MANAGER="dnf"
            PKG_INSTALL="dnf install -y"
        else
            PKG_MANAGER="yum"
            PKG_INSTALL="yum install -y"
        fi
        PKG_UPDATE="$PKG_MANAGER makecache"
        REDIS_PACKAGE="redis"
        REDIS_SERVICE="redis"
    elif [ -f /etc/arch-release ]; then
        PLATFORM="arch"
        PKG_MANAGER="pacman"
        PKG_INSTALL="pacman -Sy --noconfirm"
        PKG_UPDATE="pacman -Sy"
        REDIS_PACKAGE="redis"
        REDIS_SERVICE="redis"
    elif [ "$(uname)" = "Darwin" ]; then
        PLATFORM="macos"
        if command -v brew >/dev/null 2>&1; then
            PKG_MANAGER="brew"
            PKG_INSTALL="brew install"
            PKG_UPDATE="brew update"
            REDIS_PACKAGE="redis"
            REDIS_SERVICE="redis"
            REDIS_CONFIG_PATH="/usr/local/etc/redis.conf"
        else
            log_error "macOS detected but Homebrew not found - please install Homebrew first"
            exit 1
        fi
    else
        PLATFORM="unknown"
        log_warn "Unknown platform - will attempt generic installation"
    fi
    
    log_info "Platform: $PLATFORM using $PKG_MANAGER"
    log_debug "Redis package: $REDIS_PACKAGE, Service: $REDIS_SERVICE"
}

# Check system requirements
check_requirements() {
    log_step "Checking system requirements..."
    
    # Check if running as root (except for test-only mode)
    if [ "$TEST_ONLY" != true ] && [ "$EUID" -ne 0 ] && [ "$PLATFORM" != "macos" ]; then
        log_error "This script needs root privileges for installation"
        log_info "Please run: sudo $0"
        exit 1
    fi
    
    # Check available disk space (need at least 100MB)
    available_space=$(df /tmp | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt 102400 ]; then
        log_warn "Low disk space detected - Redis installation may fail"
    fi
    
    # Check if Redis is already installed
    if command -v redis-server >/dev/null 2>&1 || command -v redis-cli >/dev/null 2>&1; then
        log_info "Redis is already installed"
        REDIS_ALREADY_INSTALLED=true
    else
        log_info "Redis not detected - fresh installation required"
        REDIS_ALREADY_INSTALLED=false
    fi
    
    log_info "System requirements check completed"
}

# Install Redis server
install_redis() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would install Redis using: $PKG_INSTALL $REDIS_PACKAGE"
        return 0
    fi
    
    if [ "$REDIS_ALREADY_INSTALLED" = true ]; then
        log_info "Redis already installed - skipping installation"
        return 0
    fi
    
    log_step "Installing Redis server..."
    
    # Update package lists
    log_info "Updating package lists..."
    $PKG_UPDATE || {
        log_warn "Package update failed - continuing with installation"
    }
    
    # Install Redis
    log_info "Installing Redis package: $REDIS_PACKAGE"
    if $PKG_INSTALL $REDIS_PACKAGE; then
        log_info "✅ Redis installation completed successfully"
    else
        log_error "Redis installation failed"
        exit 1
    fi
}

# Configure Redis for WebSocket optimization
configure_redis() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would configure Redis at: $REDIS_CONFIG_PATH"
        return 0
    fi
    
    log_step "Configuring Redis for WebSocket optimization..."
    
    # Backup existing configuration
    if [ -f "$REDIS_CONFIG_PATH" ]; then
        backup_file="$REDIS_CONFIG_PATH.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$REDIS_CONFIG_PATH" "$backup_file"
        log_info "Backed up existing config to: $backup_file"
    fi
    
    # Create optimized Redis configuration
    log_info "Creating WebSocket-optimized configuration..."
    
    cat > "$REDIS_CONFIG_PATH" << EOF
# Redis WebSocket Optimization Configuration for ArmGuard
# Generated by: $SCRIPT_NAME v$SCRIPT_VERSION
# Date: $(date)

# Network configuration
bind $REDIS_HOST
port $REDIS_PORT
tcp-backlog 511
timeout 300
tcp-keepalive 300

# Memory optimization for WebSocket workloads
maxmemory 512mb
maxmemory-policy allkeys-lru
maxmemory-samples 5

# Persistence settings (balanced for real-time performance)
save 900 1
save 300 10
save 60 10000
stop-writes-on-bgsave-error yes
rdbcompression yes
rdbchecksum yes

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security
requirepass $REDIS_PASSWORD
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""

# WebSocket-specific optimizations
notify-keyspace-events Ex
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
list-compress-depth 0
set-max-intset-entries 512
zset-max-ziplist-entries 128
zset-max-ziplist-value 64

# Client connection limits
maxclients 10000

# Slow log configuration
slowlog-log-slower-than 10000
slowlog-max-len 128

# Advanced tuning
hz 10
dynamic-hz yes
EOF

    # Create log directory
    mkdir -p /var/log/redis
    
    # Set proper permissions
    if id "redis" >/dev/null 2>&1; then
        chown redis:redis /var/log/redis
        chown redis:redis "$REDIS_CONFIG_PATH" 2>/dev/null || true
    elif [ "$PLATFORM" = "macos" ]; then
        chown $(whoami) "$REDIS_CONFIG_PATH" 2>/dev/null || true
    fi
    
    log_info "✅ Redis configuration optimized for WebSocket performance"
}

# Start and enable Redis service
start_redis() {
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would start and enable Redis service"
        return 0
    fi
    
    log_step "Starting Redis service..."
    
    case "$PLATFORM" in
        "debian"|"redhat"|"arch")
            # Enable service to start on boot
            if command -v systemctl >/dev/null 2>&1; then
                systemctl enable $REDIS_SERVICE 2>/dev/null || log_warn "Could not enable $REDIS_SERVICE service"
                systemctl start $REDIS_SERVICE || systemctl restart $REDIS_SERVICE
                log_info "✅ Redis service started via systemctl"
            elif command -v service >/dev/null 2>&1; then
                service $REDIS_SERVICE start || service $REDIS_SERVICE restart
                log_info "✅ Redis service started via service command"
            else
                log_warn "No service manager found - starting Redis manually"
                redis-server "$REDIS_CONFIG_PATH" --daemonize yes
            fi
            ;;
        "macos")
            brew services start redis
            log_info "✅ Redis service started via Homebrew"
            ;;
        *)
            # Fallback for unknown platforms
            if command -v systemctl >/dev/null 2>&1; then
                systemctl start $REDIS_SERVICE
            elif command -v service >/dev/null 2>&1; then
                service $REDIS_SERVICE start
            else
                redis-server "$REDIS_CONFIG_PATH" --daemonize yes
            fi
            log_info "✅ Redis service started (fallback method)"
            ;;
    esac
    
    # Wait for Redis to start
    sleep 3
}

# Test Redis installation and WebSocket functionality
test_redis() {
    log_step "Testing Redis installation..."
    
    local test_passed=true
    
    # Test basic connectivity
    log_info "Testing Redis connectivity..."
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
        log_info "✅ Redis PING test passed"
    elif redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping >/dev/null 2>&1; then
        log_info "✅ Redis PING test passed (with authentication)"
    else
        log_error "❌ Redis PING test failed"
        test_passed=false
    fi
    
    # Test WebSocket-relevant operations
    if [ "$test_passed" = true ]; then
        log_info "Testing WebSocket operations..."
        
        # Test key operations
        test_key="armguard_test_$(date +%s)"
        test_value="websocket_test_value"
        
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" set "$test_key" "$test_value" >/dev/null 2>&1; then
            log_debug "Key set operation successful"
        else
            log_warn "Key set operation failed"
            test_passed=false
        fi
        
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" get "$test_key" >/dev/null 2>&1; then
            log_debug "Key get operation successful"
        else
            log_warn "Key get operation failed"
            test_passed=false
        fi
        
        if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" expire "$test_key" 30 >/dev/null 2>&1; then
            log_debug "Key expiration operation successful"
        else
            log_warn "Key expiration operation failed"
            test_passed=false
        fi
        
        # Clean up test key
        redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" del "$test_key" >/dev/null 2>&1
        
        if [ "$test_passed" = true ]; then
            log_info "✅ WebSocket operations test passed"
        else
            log_warn "⚠️  Some WebSocket operations failed but Redis is functional"
        fi
    fi
    
    # Display Redis info
    if [ "$VERBOSE" = true ] && [ "$test_passed" = true ]; then
        log_info "Redis server information:"
        redis_version=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" info server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r')
        memory_usage=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" info memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r')
        connected_clients=$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" info clients 2>/dev/null | grep connected_clients | cut -d: -f2 | tr -d '\r')
        
        echo "  • Version: $redis_version"
        echo "  • Memory Usage: $memory_usage"
        echo "  • Connected Clients: $connected_clients"
    fi
    
    return $([ "$test_passed" = true ] && echo 0 || echo 1)
}

# Display final instructions
show_final_instructions() {
    echo
    echo -e "${GREEN}🎉 Redis WebSocket Installation Completed Successfully!${NC}"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Next Steps:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    echo "1. 🔄 Restart your ArmGuard Django application:"
    echo "   python manage.py runserver"
    echo
    echo "2. ✅ You should now see this message at startup:"
    echo "   \"✅ Using Redis for WebSocket channel layer\""
    echo
    echo "3. 🚀 Your WebSocket performance is now optimized for:"
    echo "   • Higher concurrent user capacity"
    echo "   • Faster real-time notifications"
    echo "   • Better channel layer reliability"
    echo "   • Improved memory management"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Redis Service Management:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
    case "$PLATFORM" in
        "debian"|"redhat"|"arch")
            echo "• Start:   sudo systemctl start $REDIS_SERVICE"
            echo "• Stop:    sudo systemctl stop $REDIS_SERVICE"
            echo "• Restart: sudo systemctl restart $REDIS_SERVICE"
            echo "• Status:  sudo systemctl status $REDIS_SERVICE"
            ;;
        "macos")
            echo "• Start:   brew services start redis"
            echo "• Stop:    brew services stop redis"
            echo "• Restart: brew services restart redis"
            echo "• Status:  brew services list | grep redis"
            ;;
    esac
    echo
    echo "• Test Connection: redis-cli -a $REDIS_PASSWORD ping"
    echo "• Configuration:   $REDIS_CONFIG_PATH"
    echo
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo
}

# Main installation function
main() {
    print_banner
    
    parse_args "$@"
    
    # If test-only mode, just run tests
    if [ "$TEST_ONLY" = true ]; then
        log_info "Running Redis connectivity tests..."
        if test_redis; then
            log_info "✅ All Redis tests passed"
            exit 0
        else
            log_error "❌ Redis tests failed"
            exit 1
        fi
    fi
    
    detect_platform
    check_requirements
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Dry run mode - showing what would be done:"
        echo "1. Install Redis package: $REDIS_PACKAGE"
        echo "2. Configure Redis at: $REDIS_CONFIG_PATH"
        echo "3. Start Redis service: $REDIS_SERVICE"
        echo "4. Test Redis connectivity"
        echo
        log_info "To perform actual installation, run without --dry-run"
        exit 0
    fi
    
    # Main installation steps
    install_redis
    configure_redis
    start_redis
    
    # Test installation
    if test_redis; then
        show_final_instructions
        exit 0
    else
        log_error "Redis installation completed but tests failed"
        log_info "Redis may still be functional - check service status manually"
        exit 1
    fi
}

# Run main function with all arguments
main "$@"