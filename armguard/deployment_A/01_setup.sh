#!/bin/bash

# =============================================================================
# 01_SETUP.SH - ENVIRONMENT SETUP AND PREREQUISITES
# =============================================================================
# PURPOSE: System updates, package installs, environment preparation
# INTEGRATED: Best practices from deployment_A + deployment folders
# VERSION: 4.0.0 - Modular Deployment System
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_DIR="/var/log/armguard-deploy"
readonly LOG_FILE="$LOG_DIR/01-setup-$(date +%Y%m%d-%H%M%S).log"

# Colors for output (unified from both systems)
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# =============================================================================
# LOGGING SYSTEM (UNIFIED FROM BOTH FOLDERS)
# =============================================================================

ensure_log_dir() {
    if [[ "$EUID" -eq 0 ]]; then
        mkdir -p "$LOG_DIR"
        chown -R www-data:www-data "$LOG_DIR" 2>/dev/null || true
    else
        mkdir -p "$HOME/.local/share/armguard-logs"
        LOG_FILE="$HOME/.local/share/armguard-logs/01-setup-$(date +%Y%m%d-%H%M%S).log"
    fi
}

log_info() {
    echo -e "${GREEN}[SETUP-INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[SETUP-WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[SETUP-ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${CYAN}[SETUP-SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

# =============================================================================
# ENVIRONMENT DETECTION (FROM DEPLOYMENT_A)
# =============================================================================

detect_system_info() {
    log_info "Detecting system information..."
    
    # Operating System Detection
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_NAME="$NAME"
        OS_VERSION="$VERSION"
        OS_ID="$ID"
    else
        OS_NAME="Unknown"
        OS_VERSION="Unknown"  
        OS_ID="unknown"
    fi
    
    # Architecture Detection
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64) ARCH_TYPE="amd64" ;;
        aarch64) ARCH_TYPE="arm64" ;;
        armv7l) ARCH_TYPE="armhf" ;;
        *) ARCH_TYPE="unknown" ;;
    esac
    
    # Environment Detection (from deployment_A/deploy-master.sh)
    if [ -d "/mnt/hgfs" ] && [ -d "/mnt/hgfs/Armguard" ]; then
        ENV_TYPE="vmware"
        log_info "VMware environment detected"
    elif [ -f "/.dockerenv" ]; then
        ENV_TYPE="docker"
        log_info "Docker environment detected"
    elif [ -f "/etc/systemd/system/armguard.service" ]; then
        ENV_TYPE="production"
        log_info "Production environment detected"
    else
        ENV_TYPE="development"
        log_info "Development environment assumed"
    fi
    
    log_info "System: $OS_NAME $OS_VERSION ($ARCH_TYPE)"
    log_info "Environment: $ENV_TYPE"
}

# =============================================================================
# SYSTEM CHECKS AND PREREQUISITES
# =============================================================================

check_prerequisites() {
    log_info "Checking system prerequisites..."
    
    local prereq_failed=false
    
    # Check if running as root for system-level operations
    if [ "$EUID" -ne 0 ]; then
        log_warn "Not running as root - some operations may require sudo"
    fi
    
    # Check available disk space
    local available_space=$(df / | awk 'NR==2 {print $4}')
    local required_space=5242880  # 5GB in KB
    
    if [ "$available_space" -lt "$required_space" ]; then
        log_error "Insufficient disk space. Available: ${available_space}KB, Required: ${required_space}KB"
        prereq_failed=true
    else
        log_success "Disk space check passed: ${available_space}KB available"
    fi
    
    # Check memory
    local available_memory=$(free -k | awk 'NR==2{print $2}')
    local required_memory=2097152  # 2GB in KB
    
    if [ "$available_memory" -lt "$required_memory" ]; then
        log_warn "Low memory detected. Available: ${available_memory}KB, Recommended: ${required_memory}KB"
    else
        log_success "Memory check passed: ${available_memory}KB available"
    fi
    
    # Check for essential commands
    local essential_commands=("curl" "wget" "git" "python3" "pip3")
    for cmd in "${essential_commands[@]}"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            log_warn "$cmd not found - will be installed"
        else
            log_success "$cmd available"
        fi
    done
    
    if [ "$prereq_failed" = true ]; then
        log_error "Prerequisites check failed - please resolve issues before continuing"
        exit 1
    fi
}

# =============================================================================
# PACKAGE MANAGEMENT (UNIFIED FROM BOTH SYSTEMS)
# =============================================================================

update_package_lists() {
    log_info "Updating package lists..."
    
    case "$OS_ID" in
        "ubuntu"|"debian")
            sudo apt update -qq
            log_success "APT package lists updated"
            ;;
        "centos"|"rhel"|"fedora")
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf check-update -q || true
            else
                sudo yum check-update -q || true
            fi
            log_success "YUM/DNF package lists updated"  
            ;;
        "arch")
            sudo pacman -Sy --noconfirm
            log_success "Pacman package lists updated"
            ;;
        *)
            log_warn "Unknown package manager - manual package management may be required"
            ;;
    esac
}

install_system_dependencies() {
    log_info "Installing system dependencies..."
    
    # Base packages needed for ArmGuard deployment
    local base_packages_apt=(
        "curl"
        "wget" 
        "git"
        "python3"
        "python3-pip"
        "python3-venv"
        "build-essential"
        "pkg-config"
        "libssl-dev"
        "libffi-dev"
        "nginx"
        "postgresql"
        "postgresql-contrib"
        "postgresql-client"
        "redis-server"
        "redis-tools"
        "supervisor"
        "ufw"
        "fail2ban"
        "logrotate"
        "certbot"
        "python3-certbot-nginx"
    )
    
    case "$OS_ID" in
        "ubuntu"|"debian")
            log_info "Installing packages for Ubuntu/Debian..."
            sudo apt install -y "${base_packages_apt[@]}"
            log_success "System dependencies installed via APT"
            ;;
        "centos"|"rhel"|"fedora")
            log_info "Installing packages for RHEL/CentOS/Fedora..."
            local base_packages_rpm=(
                "curl" "wget" "git" "python3" "python3-pip"
                "gcc" "openssl-devel" "libffi-devel" "nginx"
                "postgresql" "postgresql-server" "redis" "python3-certbot-nginx"
            )
            if command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y "${base_packages_rpm[@]}"
            else
                sudo yum install -y "${base_packages_rpm[@]}"
            fi
            log_success "System dependencies installed via YUM/DNF"
            ;;
        *)
            log_error "Unsupported operating system: $OS_ID"
            log_info "Please install dependencies manually:"
            log_info "- Python 3.8+"
            log_info "- Nginx"
            log_info "- PostgreSQL"
            log_info "- Redis"
            log_info "- SSL/TLS development libraries"
            exit 1
            ;;
    esac
}

# =============================================================================
# PYTHON ENVIRONMENT SETUP (INTEGRATED FROM DEPLOYMENT FOLDER)
# =============================================================================

setup_python_environment() {
    log_info "Setting up Python environment..."
    
    local python_version
    python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
    
    if [ "$(echo "$python_version < 3.8" | bc)" -eq 1 ] 2>/dev/null; then
        log_error "Python 3.8+ required, found: $python_version"
        exit 1
    fi
    
    log_success "Python version check passed: $python_version"
    
    # Create virtual environment if not in container
    if [ "$ENV_TYPE" != "docker" ]; then
        local venv_path="$SCRIPT_DIR/../venv"
        if [ ! -d "$venv_path" ]; then
            log_info "Creating Python virtual environment..."
            python3 -m venv "$venv_path"
            log_success "Virtual environment created at $venv_path"
        else
            log_info "Virtual environment already exists"
        fi
        
        # Activate virtual environment
        source "$venv_path/bin/activate"
        log_success "Virtual environment activated"
    fi
    
    # Upgrade pip and install core Python packages
    log_info "Installing/upgrading Python packages..."
    python3 -m pip install --upgrade pip
    python3 -m pip install --upgrade setuptools wheel
    
    log_success "Python environment setup completed"
}

# =============================================================================
# DATABASE SETUP (FROM DEPLOYMENT_A PRODUCTION METHOD)
# =============================================================================

setup_database_system() {
    log_info "Setting up database system..."
    
    # PostgreSQL setup (from deployment_A/methods/production/setup-database.sh)
    case "$OS_ID" in
        "ubuntu"|"debian")
            # Start and enable PostgreSQL
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            log_success "PostgreSQL service started and enabled"
            ;;
        "centos"|"rhel"|"fedora")
            # Initialize database if needed
            if [ ! -d "/var/lib/pgsql/data" ]; then
                sudo postgresql-setup initdb
            fi
            sudo systemctl start postgresql
            sudo systemctl enable postgresql
            log_success "PostgreSQL initialized and started"
            ;;
    esac
    
    # Create database and user (will be configured in 02_config.sh)
    log_info "Database system setup completed - configuration will be handled in config phase"
}

# =============================================================================
# REDIS SETUP (INTEGRATED FROM DEPLOYMENT UNIFIED-REDIS-MANAGER)
# =============================================================================

setup_redis_system() {
    log_info "Setting up Redis system..."
    
    # Start and enable Redis service
    if systemctl is-active --quiet redis-server 2>/dev/null; then
        log_info "Redis server already running"
    elif systemctl is-active --quiet redis 2>/dev/null; then
        log_info "Redis service already running"
    else
        # Try to start Redis with different service names
        if systemctl list-units --type=service | grep -q redis-server; then
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            log_success "Redis server started and enabled"
        elif systemctl list-units --type=service | grep -q redis; then
            sudo systemctl start redis
            sudo systemctl enable redis
            log_success "Redis service started and enabled"
        else
            log_error "Redis service not found after installation"
            exit 1
        fi
    fi
    
    # Test Redis connection
    if redis-cli ping >/dev/null 2>&1; then
        log_success "Redis connection test passed"
    else
        log_error "Redis connection test failed"
        exit 1
    fi
}

# =============================================================================
# NGINX SETUP (FROM DEPLOYMENT_A METHODS)
# =============================================================================

setup_nginx_system() {
    log_info "Setting up Nginx system..."
    
    # Start and enable Nginx
    sudo systemctl start nginx
    sudo systemctl enable nginx
    
    # Test Nginx configuration
    if nginx -t >/dev/null 2>&1; then
        log_success "Nginx configuration test passed"
    else
        log_warn "Nginx configuration has issues - will be configured in config phase"
    fi
    
    # Backup default configuration
    if [ -f "/etc/nginx/sites-available/default" ] && [ ! -f "/etc/nginx/sites-available/default.backup" ]; then
        sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup
        log_info "Default Nginx configuration backed up"
    fi
    
    log_success "Nginx system setup completed"
}

# =============================================================================
# FIREWALL SETUP (FROM DEPLOYMENT_A NETWORK_SETUP)
# =============================================================================

setup_basic_firewall() {
    log_info "Setting up basic firewall rules..."
    
    # Enable UFW if available
    if command -v ufw >/dev/null 2>&1; then
        # Reset UFW to defaults
        sudo ufw --force reset
        
        # Allow SSH (essential for remote management)
        sudo ufw allow 22/tcp
        
        # Allow HTTP and HTTPS
        sudo ufw allow 80/tcp
        sudo ufw allow 443/tcp
        
        # Allow custom HTTP port for ArmGuard
        sudo ufw allow 8443/tcp
        
        # Enable UFW 
        sudo ufw --force enable
        
        log_success "Basic firewall rules configured with UFW"
    else
        log_warn "UFW not available - manual firewall configuration may be needed"
    fi
}

# =============================================================================
# SYSTEM OPTIMIZATION (INTEGRATED BEST PRACTICES)
# =============================================================================

optimize_system() {
    log_info "Applying system optimizations..."
    
    # Set timezone to UTC for consistency (production best practice)
    sudo timedatectl set-timezone UTC
    log_success "Timezone set to UTC"
    
    # Enable automatic security updates (Ubuntu/Debian)
    if [ "$OS_ID" = "ubuntu" ] || [ "$OS_ID" = "debian" ]; then
        if [ ! -f "/etc/apt/apt.conf.d/20auto-upgrades" ]; then
            echo 'APT::Periodic::Update-Package-Lists "1";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
            echo 'APT::Periodic::Unattended-Upgrade "1";' | sudo tee -a /etc/apt/apt.conf.d/20auto-upgrades
            log_success "Automatic security updates enabled"
        fi
    fi
    
    # Optimize file limits for web applications
    if [ ! -f "/etc/security/limits.conf.armguard" ]; then
        echo "www-data soft nofile 65536" | sudo tee -a /etc/security/limits.conf
        echo "www-data hard nofile 65536" | sudo tee -a /etc/security/limits.conf
        sudo touch /etc/security/limits.conf.armguard
        log_success "File limits optimized for web applications"
    fi
    
    log_success "System optimization completed"
}

# =============================================================================
# MAIN SETUP EXECUTION
# =============================================================================

print_setup_header() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}║                    ${WHITE}🔧 ARMGUARD ENVIRONMENT SETUP${BLUE}                        ║${NC}"
    echo -e "${BLUE}║                          ${CYAN}Phase 1: System Preparation${BLUE}                       ║${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

main() {
    print_setup_header
    ensure_log_dir
    
    log_info "Starting ArmGuard environment setup..."
    log_info "Logging to: $LOG_FILE"
    
    # Phase 1: System Detection and Prerequisites  
    detect_system_info
    check_prerequisites
    
    # Phase 2: Package Management
    update_package_lists
    install_system_dependencies
    
    # Phase 3: Core Services Setup
    setup_python_environment
    setup_database_system
    setup_redis_system
    setup_nginx_system
    
    # Phase 4: Security and Optimization
    setup_basic_firewall
    setup_device_authorization_prerequisites
    verify_device_authorization_integration
    optimize_system
    
    echo ""
    log_success "✅ Environment setup completed successfully!"
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                        ${WHITE}SETUP PHASE COMPLETED${GREEN}                              ║${NC}"
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}║  Next: Run 02_config.sh to configure application settings                    ║${NC}"
    echo -e "${GREEN}║                                                                               ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    log_info "Setup log saved to: $LOG_FILE"
    log_info "Proceed to 02_config.sh for configuration phase"
}

# Execute main function
main "$@"