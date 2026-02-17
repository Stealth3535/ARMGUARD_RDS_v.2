#!/bin/bash

################################################################################
# ArmGuard Ubuntu-Optimized Deployment Script
# 
# Specifically designed for Ubuntu server deployment (x86_64/ARM64)
# Automatically detects and optimizes for Ubuntu vs Raspberry Pi
# Usage: sudo bash ubuntu-deploy.sh [--quick] [--production]
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Better error visibility (prevents silent exits)
on_error() {
    local exit_code=$?
    local line_no=${BASH_LINENO[0]}
    echo -e "${RED}❌ Deployment wrapper failed at line ${line_no} (exit: ${exit_code})${NC}"
    echo -e "${YELLOW}Tip: Re-run with debug: sudo bash -x ubuntu-deploy.sh --production${NC}"
    exit ${exit_code}
}
trap on_error ERR

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try to detect project directory (look for manage.py in parent dirs)
DETECTED_PROJECT_DIR=""
SEARCH_DIR="$SCRIPT_DIR"
for i in {1..5}; do
    if [ -f "$SEARCH_DIR/manage.py" ]; then
        DETECTED_PROJECT_DIR="$SEARCH_DIR"
        break
    fi
    SEARCH_DIR="$(dirname "$SEARCH_DIR")"
done

# Default configuration for Ubuntu
PROJECT_NAME="armguard"
# Use detected project directory if found, otherwise default to /var/www/armguard
PROJECT_DIR="${DETECTED_PROJECT_DIR:-/var/www/armguard}"
DOMAIN="armguard.local"
NETWORK_TYPE="lan"
QUICK_MODE="no"
PRODUCTION_MODE="no"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --quick) QUICK_MODE="yes" ;;
        --production) PRODUCTION_MODE="yes"; NETWORK_TYPE="wan" ;;
        --lan) NETWORK_TYPE="lan" ;;
        --wan) NETWORK_TYPE="wan" ;;
        --hybrid) NETWORK_TYPE="hybrid" ;;
        -h|--help)
            echo "Ubuntu ArmGuard Deployment Script"
            echo ""
            echo "Usage: sudo bash ubuntu-deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --quick       Quick deployment with minimal prompts"
            echo "  --production  Full production deployment (WAN-ready)"
            echo "  --lan         LAN-only deployment (default)"
            echo "  --wan         Internet-facing deployment"
            echo "  --hybrid      Mixed LAN/WAN deployment"
            echo "  -h, --help    Show this help message"
            echo ""
            echo "Examples:"
            echo "  sudo bash ubuntu-deploy.sh --quick"
            echo "  sudo bash ubuntu-deploy.sh --production"
            echo "  sudo bash ubuntu-deploy.sh --lan"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Ubuntu deployment banner
print_ubuntu_banner() {
    clear
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}║   ${GREEN} ArmGuard Ubuntu Server Deployment ${CYAN}           ║${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}║  ${YELLOW}Optimized specifically for Ubuntu servers${CYAN}     ║${NC}"
    echo -e "${CYAN}║  ${YELLOW}Automatic platform detection and optimization${CYAN} ║${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Check if running on Ubuntu
check_ubuntu() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [[ "$NAME" == *"Ubuntu"* ]]; then
            echo -e "${GREEN}✅ Ubuntu detected: $NAME $VERSION${NC}"
            return 0
        elif [[ "$NAME" == *"Debian"* ]]; then
            echo -e "${GREEN}✅ Debian-based system detected: $NAME $VERSION${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️ Non-Ubuntu system detected: $NAME${NC}"
            echo -e "${YELLOW}   This script is optimized for Ubuntu but will attempt deployment${NC}"
        fi
    else
        echo -e "${RED}❌ Cannot determine OS version${NC}"
        exit 1
    fi
}

# Detect platform type
detect_platform() {
    echo -e "${BLUE}🔍 Detecting platform type...${NC}"
    
    # Check architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)
            PLATFORM_TYPE="Ubuntu x86_64 Server"
            ARCH_TYPE="amd64"
            # Check for HP ProDesk mini computers
            if command -v dmidecode >/dev/null 2>&1 && dmidecode -s system-product-name 2>/dev/null | grep -qi "prodesk\|elitedesk\|hp.*mini"; then
                PLATFORM_TYPE="HP ProDesk Mini Computer"
                HARDWARE_TYPE="hp_prodesk"
                echo -e "${CYAN}🖥️ HP ProDesk/EliteDesk mini computer detected${NC}"
            else
                HARDWARE_TYPE="x86_server"
            fi
            ;;
        aarch64|arm64)
            PLATFORM_TYPE="Ubuntu ARM64 Server"
            ARCH_TYPE="arm64"
            HARDWARE_TYPE="arm64_server"
            ;;
        armv7l)
            PLATFORM_TYPE="Ubuntu ARM32"
            ARCH_TYPE="arm32"
            HARDWARE_TYPE="arm32_server"
            ;;
        *)
            PLATFORM_TYPE="Ubuntu Unknown Architecture"
            ARCH_TYPE="unknown"
            HARDWARE_TYPE="unknown"
            ;;
    esac
    
    # Check if it's a Raspberry Pi (even if running Ubuntu)
    if [ -f /proc/device-tree/model ]; then
        MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
        if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
            PLATFORM_TYPE="Ubuntu on Raspberry Pi"
            HARDWARE_TYPE="raspberry_pi"
            # Detect specific Pi model for optimization
            if [[ "$MODEL" == *"Pi 5"* ]]; then
                PI_MODEL="5"
                PI_PERFORMANCE="high"
            elif [[ "$MODEL" == *"Pi 4"* ]]; then
                PI_MODEL="4"
                PI_PERFORMANCE="medium"
            else
                PI_MODEL="3_or_older"
                PI_PERFORMANCE="low"
            fi
            echo -e "${CYAN}📱 Raspberry Pi $PI_MODEL detected running Ubuntu${NC}"
        fi
    fi
    
    # Check if virtual machine
    if command -v systemd-detect-virt &>/dev/null; then
        VIRT=$(systemd-detect-virt)
        if [ "$VIRT" != "none" ]; then
            PLATFORM_TYPE="$PLATFORM_TYPE (Virtual: $VIRT)"
        fi
    fi
    
    echo -e "${GREEN}✅ Platform: $PLATFORM_TYPE${NC}"
    echo -e "${GREEN}✅ Architecture: $ARCH_TYPE${NC}"
}

# Ubuntu-specific optimizations
apply_ubuntu_optimizations() {
    echo -e "${BLUE}⚡ Applying Ubuntu-specific optimizations...${NC}"
    
    # CPU-based worker optimization
    CPU_CORES=$(nproc 2>/dev/null || echo 2)
    
    # Platform-specific optimization
    case "$HARDWARE_TYPE" in
        "hp_prodesk")
            echo -e "${GREEN}🖥️ Optimizing for HP ProDesk mini computer${NC}"
            # HP ProDesk typically has powerful CPUs, optimize accordingly
            GUNICORN_WORKERS=$((CPU_CORES * 3))
            NGINX_WORKER_PROCESSES=$CPU_CORES
            USE_AGGRESSIVE_CACHING="yes"
            ;;
        "raspberry_pi")
            echo -e "${GREEN}📱 Optimizing for Raspberry Pi${NC}"
            if [ "$PI_PERFORMANCE" = "high" ]; then
                # Pi 5 can handle more workers
                GUNICORN_WORKERS=$((CPU_CORES * 2))
            else
                # Pi 4 and older - conservative workers
                GUNICORN_WORKERS=$((CPU_CORES + 1))
            fi
            NGINX_WORKER_PROCESSES=2
            USE_AGGRESSIVE_CACHING="no"
            ;;
        "x86_server")
            echo -e "${GREEN}🖥️ Optimizing for x86_64 server${NC}"
            # Standard x86_64 servers
            GUNICORN_WORKERS=$((CPU_CORES * 2 + 1))
            NGINX_WORKER_PROCESSES=$CPU_CORES
            USE_AGGRESSIVE_CACHING="yes"
            ;;
        *)
            # Default ARM optimization
            GUNICORN_WORKERS=$((CPU_CORES + 1))
            NGINX_WORKER_PROCESSES=2
            USE_AGGRESSIVE_CACHING="no"
            ;;
    esac
    
    # Memory-based database optimization
    TOTAL_MEM_MB=$(free -m 2>/dev/null | awk 'NR==2 {print $2}')
    if [ -z "$TOTAL_MEM_MB" ]; then
        TOTAL_MEM_MB=2048
    fi
    
    # Platform-specific memory optimization
    case "$HARDWARE_TYPE" in
        "hp_prodesk")
            # HP ProDesk usually has 8GB+ RAM, optimize for performance
            if [ "$TOTAL_MEM_MB" -gt 6144 ]; then
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=150
                REDIS_MAXMEMORY="2gb"
            elif [ "$TOTAL_MEM_MB" -gt 4096 ]; then
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=100
                REDIS_MAXMEMORY="1gb"
            else
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=50
                REDIS_MAXMEMORY="512mb"
            fi
            ;;
        "raspberry_pi")
            # Raspberry Pi memory optimization
            if [ "$TOTAL_MEM_MB" -gt 6144 ] && [ "$PI_PERFORMANCE" = "high" ]; then
                # Pi 5 with 8GB RAM
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=50
                REDIS_MAXMEMORY="1gb"
            elif [ "$TOTAL_MEM_MB" -gt 3072 ]; then
                # Pi 4 with 4GB+ RAM
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=25
                REDIS_MAXMEMORY="512mb"
            else
                # Pi with limited RAM - use SQLite
                USE_POSTGRESQL="no"
                REDIS_MAXMEMORY="256mb"
            fi
            ;;
        *)
            # Default memory optimization
            if [ "$TOTAL_MEM_MB" -gt 4096 ]; then
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=100
                REDIS_MAXMEMORY="1gb"
            elif [ "$TOTAL_MEM_MB" -gt 2048 ]; then
                USE_POSTGRESQL="yes"
                DB_MAX_CONNECTIONS=50
                REDIS_MAXMEMORY="512mb"
            else
                USE_POSTGRESQL="no"
                REDIS_MAXMEMORY="256mb"
            fi
            ;;
    esac
    
    # Network type based on deployment mode
    if [ "$PRODUCTION_MODE" = "yes" ]; then
        USE_SSL="yes"
        SSL_TYPE="letsencrypt"
        CONFIGURE_FIREWALL="yes"
    else
        USE_SSL="yes"
        SSL_TYPE="mkcert"
        CONFIGURE_FIREWALL="yes"
    fi
    
    echo -e "${GREEN}✅ Hardware: $PLATFORM_TYPE${NC}"
    echo -e "${GREEN}✅ Optimized for $CPU_CORES cores, ${TOTAL_MEM_MB}MB RAM${NC}"
    echo -e "${GREEN}✅ Gunicorn workers: $GUNICORN_WORKERS${NC}"
    echo -e "${GREEN}✅ Nginx workers: $NGINX_WORKER_PROCESSES${NC}"
    echo -e "${GREEN}✅ Database: $([ "$USE_POSTGRESQL" = "yes" ] && echo "PostgreSQL (${DB_MAX_CONNECTIONS} conn)" || echo "SQLite")${NC}"
    echo -e "${GREEN}✅ Redis memory: $REDIS_MAXMEMORY${NC}"
    echo -e "${GREEN}✅ Aggressive caching: $USE_AGGRESSIVE_CACHING${NC}"
}

# Show Ubuntu deployment summary
show_deployment_summary() {
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                 Ubuntu Deployment Configuration               ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Platform Information:${NC}"
    echo "  Type:             $PLATFORM_TYPE"
    echo "  Hardware:         $HARDWARE_TYPE"
    echo "  Architecture:     $ARCH_TYPE"
    echo "  CPU Cores:        $CPU_CORES"
    echo "  Memory:           ${TOTAL_MEM_MB}MB"
    if [ "$HARDWARE_TYPE" = "raspberry_pi" ]; then
        echo "  Pi Model:         Raspberry Pi $PI_MODEL"
        echo "  Performance:      $PI_PERFORMANCE"
    fi
    echo ""
    echo -e "${YELLOW}Deployment Configuration:${NC}"
    echo "  Project:          $PROJECT_NAME"
    echo "  Directory:        $PROJECT_DIR"
    echo "  Domain:           $DOMAIN"
    echo "  Network Type:     $NETWORK_TYPE"
    echo "  Gunicorn Workers: $GUNICORN_WORKERS"
    echo "  Nginx Workers:    $NGINX_WORKER_PROCESSES"
    echo "  Database:         $([ "$USE_POSTGRESQL" = "yes" ] && echo "PostgreSQL (${DB_MAX_CONNECTIONS} conn)" || echo "SQLite")"
    echo "  Redis Memory:     $REDIS_MAXMEMORY"
    echo "  SSL:              $([ "$USE_SSL" = "yes" ] && echo "$SSL_TYPE" || echo "Disabled")"
    echo "  Firewall:         $([ "$CONFIGURE_FIREWALL" = "yes" ] && echo "UFW Enabled" || echo "Disabled")"
    echo "  Caching:          $USE_AGGRESSIVE_CACHING"
    echo ""
}

# Run Ubuntu-optimized deployment
run_ubuntu_deployment() {
    echo -e "${BLUE}🚀 Starting Ubuntu-optimized deployment...${NC}"
    
    # Set environment variables for the deployment scripts
    export PLATFORM_TYPE
    export HARDWARE_TYPE
    export ARCH_TYPE
    export CPU_CORES
    export TOTAL_MEM_MB
    export GUNICORN_WORKERS
    export NGINX_WORKER_PROCESSES
    export USE_POSTGRESQL
    export DB_MAX_CONNECTIONS
    export REDIS_MAXMEMORY
    export USE_AGGRESSIVE_CACHING
    export USE_SSL
    export SSL_TYPE
    export CONFIGURE_FIREWALL
    export NETWORK_TYPE
    if [ "$HARDWARE_TYPE" = "raspberry_pi" ]; then
        export PI_MODEL
        export PI_PERFORMANCE
    fi
    
    # Choose deployment script based on mode
    if [ "$QUICK_MODE" = "yes" ]; then
        echo -e "${YELLOW}⚡ Quick deployment mode${NC}"
        # Use basic deployment with Ubuntu optimizations
        if [ -f "$SCRIPT_DIR/methods/basic-setup/serversetup.sh" ]; then
            bash "$SCRIPT_DIR/methods/basic-setup/serversetup.sh"
        else
            echo -e "${RED}❌ Basic setup script not found${NC}"
            exit 1
        fi
    elif [ "$PRODUCTION_MODE" = "yes" ]; then
        echo -e "${GREEN}🏭 Production deployment mode${NC}"
        # Use full production deployment
        if [ -f "$SCRIPT_DIR/methods/production/deploy-armguard.sh" ]; then
            bash "$SCRIPT_DIR/methods/production/deploy-armguard.sh"
        else
            echo -e "${RED}❌ Production deployment script not found${NC}"
            exit 1
        fi
    else
        echo -e "${CYAN}🎯 Standard deployment mode${NC}"
        # Use master deployment script
        if [ -f "$SCRIPT_DIR/methods/production/master-deploy.sh" ]; then
            bash "$SCRIPT_DIR/methods/production/master-deploy.sh" --network-type "$NETWORK_TYPE"
        else
            echo -e "${RED}❌ Master deployment script not found${NC}"
            exit 1
        fi
    fi
}

# Main execution
main() {
    print_ubuntu_banner
    
    # Check root privileges
    if [ "$EUID" -ne 0 ]; then 
        echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
        exit 1
    fi
    
    # Ensure script relative paths are stable
    cd "$SCRIPT_DIR"

    # Show detected project location
    if [ -n "$DETECTED_PROJECT_DIR" ]; then
        echo -e "${CYAN}📦 Project auto-detected at: ${GREEN}$DETECTED_PROJECT_DIR${NC}"
        echo -e "${CYAN}   (Will use this location for deployment)${NC}"
        echo ""
    fi
    
    # System checks
    check_ubuntu
    detect_platform
    apply_ubuntu_optimizations
    
    # Show configuration
    show_deployment_summary
    
    # Confirm deployment (unless quick mode or explicit production mode)
    if [ "$QUICK_MODE" != "yes" ] && [ "$PRODUCTION_MODE" != "yes" ]; then
        echo -e "${YELLOW}❓ Proceed with Ubuntu deployment? [y/N]:${NC}"
        read -r CONFIRM
        if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}⏹️ Deployment cancelled${NC}"
            exit 0
        fi
    elif [ "$PRODUCTION_MODE" = "yes" ]; then
        echo -e "${GREEN}✅ Production flag detected, proceeding automatically...${NC}"
    fi
    
    # Run deployment
    run_ubuntu_deployment
    
    # Success message
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}║           🎉 Ubuntu Deployment Completed Successfully! 🎉     ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}║  Your ArmGuard system is now running on Ubuntu!               ║${NC}"
    echo -e "${GREEN}║                                                                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}📱 Access your ArmGuard system at:${NC}"
    echo -e "   ${YELLOW}https://$DOMAIN${NC}"
    echo -e "   ${YELLOW}https://$(hostname -I | awk '{print $1}')${NC}"
    echo ""
    echo -e "${CYAN}🔧 Service management:${NC}"
    echo -e "   ${YELLOW}sudo systemctl status gunicorn-armguard${NC}"
    echo -e "   ${YELLOW}sudo systemctl restart gunicorn-armguard${NC}"
    echo -e "   ${YELLOW}sudo systemctl status nginx${NC}"
    echo ""
    echo -e "${CYAN}📊 Health check:${NC}"
    echo -e "   ${YELLOW}sudo bash methods/production/health-check.sh${NC}"
}

# Execute main function
main "$@"