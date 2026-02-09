#!/bin/bash

################################################################################
# ArmGuard Cross-Compatible Installation Script
# 
# Automatically detects environment and installs appropriate dependencies
# Supports: VM development, ARM64 systems, Raspberry Pi, and standard servers
# Usage: bash install-cross-compatible.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Print banner
print_banner() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║        ArmGuard Cross-Compatible Installation              ║${NC}"
    echo -e "${CYAN}║                                                            ║${NC}"
    echo -e "${CYAN}║  Automatically detects your environment and installs      ║${NC}"
    echo -e "${CYAN}║  the optimal configuration for your system                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Environment detection
detect_environment() {
    echo -e "${BLUE}Detecting environment...${NC}"
    
    # Architecture detection
    ARCH=$(uname -m)
    IS_ARM64=false
    IS_RPI=false
    IS_VM=false
    PLATFORM_NAME="Standard"
    
    case "$ARCH" in
        aarch64|arm64)
            IS_ARM64=true
            PLATFORM_NAME="ARM64"
            ;;
        x86_64)
            PLATFORM_NAME="x86_64"
            ;;
    esac
    
    # Raspberry Pi detection
    if [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        IS_RPI=true
        PLATFORM_NAME="Raspberry Pi"
        MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
        echo -e "${GREEN}🥧 $MODEL detected${NC}"
    elif [ "$IS_ARM64" = true ]; then
        echo -e "${GREEN}🏗️  ARM64 architecture detected${NC}"
    fi
    
    # Virtual machine detection
    if command -v systemd-detect-virt &>/dev/null; then
        VIRT=$(systemd-detect-virt)
        if [ "$VIRT" != "none" ]; then
            IS_VM=true
            PLATFORM_NAME="$PLATFORM_NAME VM ($VIRT)"
            echo -e "${BLUE}💻 Virtual machine detected: $VIRT${NC}"
        fi
    fi
    
    # Docker detection
    if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
        IS_VM=true
        PLATFORM_NAME="Docker Container"
        echo -e "${BLUE}🐳 Docker container detected${NC}"
    fi
    
    echo -e "${CYAN}Platform: ${YELLOW}$PLATFORM_NAME${NC}"
}

# Install system dependencies
install_system_dependencies() {
    echo ""
    echo -e "${BLUE}Installing system dependencies...${NC}"
    
    # Detect package manager
    if command -v apt &>/dev/null; then
        PACKAGE_MANAGER="apt"
        PKG_UPDATE="apt update"
        PKG_INSTALL="apt install -y"
    elif command -v yum &>/dev/null; then
        PACKAGE_MANAGER="yum"
        PKG_UPDATE="yum check-update || true"
        PKG_INSTALL="yum install -y"
    elif command -v dnf &>/dev/null; then
        PACKAGE_MANAGER="dnf"
        PKG_UPDATE="dnf check-update || true"
        PKG_INSTALL="dnf install -y"
    else
        echo -e "${RED}❌ Unsupported package manager${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}Updating package lists...${NC}"
    sudo $PKG_UPDATE
    
    # Base dependencies
    BASE_PACKAGES="python3 python3-pip python3-venv git build-essential"
    
    # ARM64/RPi specific packages
    if [ "$IS_ARM64" = true ] || [ "$IS_RPI" = true ]; then
        ARM_PACKAGES="gcc g++ make libffi-dev libssl-dev pkg-config"
        if [ "$PACKAGE_MANAGER" = "apt" ]; then
            ARM_PACKAGES="$ARM_PACKAGES libjpeg-dev libpng-dev zlib1g-dev"
        fi
        BASE_PACKAGES="$BASE_PACKAGES $ARM_PACKAGES"
    fi
    
    # RPi specific packages
    if [ "$IS_RPI" = true ]; then
        if [ "$PACKAGE_MANAGER" = "apt" ]; then
            BASE_PACKAGES="$BASE_PACKAGES libraspberrypi-dev"
        fi
    fi
    
    echo -e "${YELLOW}Installing packages: $BASE_PACKAGES${NC}"
    sudo $PKG_INSTALL $BASE_PACKAGES
    
    echo -e "${GREEN}✓ System dependencies installed${NC}"
}

# Install Python dependencies
install_python_dependencies() {
    echo ""
    echo -e "${BLUE}Setting up Python environment...${NC}"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv .venv
    fi
    
    # Activate virtual environment
    source .venv/bin/activate
    
    # Upgrade pip
    echo -e "${YELLOW}Upgrading pip...${NC}"
    pip install --upgrade pip wheel setuptools
    
    # Determine requirements file and additional packages
    REQUIREMENTS_FILE="requirements.txt"
    ADDITIONAL_PACKAGES=""
    
    if [ "$IS_RPI" = true ]; then
        echo -e "${GREEN}🥧 Installing Raspberry Pi optimized packages${NC}"
        if [ -f "requirements-rpi.txt" ]; then
            REQUIREMENTS_FILE="requirements-rpi.txt"
            echo -e "  • Using: ${CYAN}requirements-rpi.txt${NC}"
        else
            ADDITIONAL_PACKAGES="psutil==5.9.8"
            echo -e "  • Using: ${CYAN}requirements.txt + psutil${NC}"
        fi
        echo -e "  • Features: ${GREEN}Thermal monitoring, GPIO support, ARM64 optimizations${NC}"
        
    elif [ "$IS_ARM64" = true ]; then
        echo -e "${GREEN}🏗️  Installing ARM64 optimized packages${NC}"
        ADDITIONAL_PACKAGES="psutil==5.9.8"
        echo -e "  • Using: ${CYAN}requirements.txt + psutil${NC}"
        echo -e "  • Features: ${GREEN}ARM64 optimizations, Enhanced monitoring${NC}"
        
    else
        echo -e "${BLUE}💻 Installing base packages${NC}"
        echo -e "  • Using: ${CYAN}requirements.txt${NC}"
        echo -e "  • Features: ${GREEN}Cross-platform compatibility, Fallback monitoring${NC}"
        
        # Ask if user wants enhanced features on x86_64
        echo ""
        read -p "Install psutil for enhanced system monitoring? [y/N]: " install_psutil
        if [[ "$install_psutil" =~ ^[Yy] ]]; then
            ADDITIONAL_PACKAGES="psutil==5.9.8"
            echo -e "  • Enhanced monitoring: ${GREEN}Enabled${NC}"
        else
            echo -e "  • Enhanced monitoring: ${YELLOW}Disabled (fallbacks available)${NC}"
        fi
    fi
    
    # Install requirements
    echo -e "${YELLOW}Installing Python packages...${NC}"
    pip install -r "$REQUIREMENTS_FILE"
    
    # Install additional packages
    if [ -n "$ADDITIONAL_PACKAGES" ]; then
        echo -e "${YELLOW}Installing additional packages: $ADDITIONAL_PACKAGES${NC}"
        pip install $ADDITIONAL_PACKAGES
    fi
    
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
}

# Configure environment
configure_environment() {
    echo ""
    echo -e "${BLUE}Configuring environment...${NC}"
    
    # Copy .env if it doesn't exist
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            echo -e "${YELLOW}Creating .env from template...${NC}"
            cp .env.example .env
        else
            echo -e "${YELLOW}Creating basic .env file...${NC}"
            cat > .env << EOF
# ArmGuard Environment Configuration
SECRET_KEY=your-secret-key-change-this
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Cross-compatibility settings
ENABLE_SECURITY_MIDDLEWARE=True
ENABLE_DEVICE_AUTHORIZATION=True
EOF
        fi
    fi
    
    # Add platform-specific settings
    if [ "$IS_RPI" = true ]; then
        echo "" >> .env
        echo "# Raspberry Pi optimizations" >> .env
        echo "RPI_THERMAL_MONITORING=True" >> .env
        echo "ARM64_OPTIMIZATIONS=True" >> .env
    elif [ "$IS_ARM64" = true ]; then
        echo "" >> .env
        echo "# ARM64 optimizations" >> .env
        echo "ARM64_OPTIMIZATIONS=True" >> .env
    fi
    
    echo -e "${GREEN}✓ Environment configured${NC}"
}

# Run Django setup
run_django_setup() {
    echo ""
    echo -e "${BLUE}Setting up Django application...${NC}"
    
    source .venv/bin/activate
    
    echo -e "${YELLOW}Running database migrations...${NC}"
    python manage.py migrate
    
    echo -e "${YELLOW}Collecting static files...${NC}"
    python manage.py collectstatic --noinput
    
    echo -e "${GREEN}✓ Django application ready${NC}"
}

# Main installation flow
main() {
    print_banner
    detect_environment
    
    # Check if we're in the right directory
    if [ ! -f "manage.py" ]; then
        echo -e "${RED}❌ manage.py not found. Please run from ArmGuard root directory.${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${YELLOW}This will install ArmGuard with optimizations for: ${CYAN}$PLATFORM_NAME${NC}"
    read -p "Continue? [Y/n]: " continue_install
    if [[ "$continue_install" =~ ^[Nn] ]]; then
        echo -e "${YELLOW}Installation cancelled${NC}"
        exit 0
    fi
    
    install_system_dependencies
    install_python_dependencies
    configure_environment
    run_django_setup
    
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Installation Complete!                       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}Platform:${NC} $PLATFORM_NAME"
    echo -e "${CYAN}Next Steps:${NC}"
    echo -e "  1. Activate virtual environment: ${YELLOW}source .venv/bin/activate${NC}"
    echo -e "  2. Create superuser: ${YELLOW}python manage.py createsuperuser${NC}"
    echo -e "  3. Start development server: ${YELLOW}python manage.py runserver 0.0.0.0:8000${NC}"
    echo ""
    if [ "$IS_RPI" = true ]; then
        echo -e "${GREEN}🥧 Raspberry Pi features enabled:${NC}"
        echo -e "  • Thermal monitoring and protection"
        echo -e "  • Memory-aware performance scaling"
        echo -e "  • ARM64 optimizations"
    elif [ "$IS_ARM64" = true ]; then
        echo -e "${GREEN}🏗️  ARM64 features enabled:${NC}"
        echo -e "  • ARM64 architecture optimizations"
        echo -e "  • Enhanced system monitoring"
    fi
    echo ""
    echo -e "${YELLOW}For production deployment, see: deployment/COMPLETE_DEPLOYMENT_GUIDE.md${NC}"
}

# Run main function
main "$@"