#!/bin/bash

################################################################################
# ArmGuard Environment Detection Script
# 
# Detects hardware, platform, and optimizes configuration
# Usage: bash deployment/detect-environment.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           ArmGuard Environment Detection                  ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect Architecture
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Hardware Architecture${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

ARCH=$(uname -m)
case "$ARCH" in
    x86_64)
        ARCH_TYPE="x86_64 (64-bit)"
        ARCH_SHORT="amd64"
        ;;
    aarch64|arm64)
        ARCH_TYPE="ARM64 (64-bit)"
        ARCH_SHORT="arm64"
        ;;
    armv7l)
        ARCH_TYPE="ARMv7 (32-bit)"
        ARCH_SHORT="armv7"
        ;;
    *)
        ARCH_TYPE="Unknown ($ARCH)"
        ARCH_SHORT="unknown"
        ;;
esac

echo -e "${CYAN}Architecture:${NC} ${YELLOW}$ARCH_TYPE${NC}"

# Detect Platform
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Platform Detection${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

PLATFORM="Unknown"
PLATFORM_DETAILS=""

# Check for specific hardware types
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Hardware Detection${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

HARDWARE_TYPE="Generic"

# Check for HP ProDesk/EliteDesk mini computers
if command -v dmidecode &>/dev/null && dmidecode -s system-product-name 2>/dev/null | grep -qi "prodesk\|elitedesk\|hp.*mini"; then
    PRODUCT_NAME=$(dmidecode -s system-product-name 2>/dev/null)
    HARDWARE_TYPE="HP Mini Computer"
    PLATFORM_DETAILS="$PRODUCT_NAME"
    echo -e "${GREEN}🖥️ HP Mini Computer detected: $PRODUCT_NAME${NC}"
    
    # Specific HP model detection
    if echo "$PRODUCT_NAME" | grep -qi "prodesk 800"; then
        HP_MODEL="ProDesk 800 Series"
        PERFORMANCE_TIER="high"
    elif echo "$PRODUCT_NAME" | grep -qi "prodesk 600"; then
        HP_MODEL="ProDesk 600 Series"  
        PERFORMANCE_TIER="medium-high"
    elif echo "$PRODUCT_NAME" | grep -qi "prodesk 400"; then
        HP_MODEL="ProDesk 400 Series"
        PERFORMANCE_TIER="medium"
    elif echo "$PRODUCT_NAME" | grep -qi "elitedesk"; then
        HP_MODEL="EliteDesk Series"
        PERFORMANCE_TIER="high"
    else
        HP_MODEL="HP Mini Computer"
        PERFORMANCE_TIER="medium"
    fi
    
    echo -e "${CYAN}Model Series:${NC} ${YELLOW}$HP_MODEL${NC}"
    echo -e "${CYAN}Performance Tier:${NC} ${YELLOW}$PERFORMANCE_TIER${NC}"
fi

# Check for Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
    if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        PLATFORM="Raspberry Pi"
        HARDWARE_TYPE="Raspberry Pi"
        PLATFORM_DETAILS="$MODEL"
        
        # Detect specific Pi model
        if [[ "$MODEL" == *"Pi 5"* ]]; then
            PI_MODEL="5"
            PERFORMANCE_TIER="high"
        elif [[ "$MODEL" == *"Pi 4"* ]]; then
            PI_MODEL="4"
            PERFORMANCE_TIER="medium"
        elif [[ "$MODEL" == *"Pi 3"* ]]; then
            PI_MODEL="3"
            PERFORMANCE_TIER="low-medium"
        else
            PI_MODEL="Unknown"
            PERFORMANCE_TIER="low"
        fi
        
        echo -e "${GREEN}📱 Raspberry Pi Model $PI_MODEL detected${NC}"
        echo -e "${CYAN}Performance Tier:${NC} ${YELLOW}$PERFORMANCE_TIER${NC}"
    fi
fi

# Check for virtual machine
if command -v systemd-detect-virt &>/dev/null; then
    VIRT=$(systemd-detect-virt)
    if [ "$VIRT" != "none" ]; then
        PLATFORM="Virtual Machine"
        PLATFORM_DETAILS="$VIRT"
    fi
fi

# Check for Docker
if [ -f /.dockerenv ] || grep -q docker /proc/1/cgroup 2>/dev/null; then
    PLATFORM="Docker Container"
fi

# Check for WSL
if grep -qi microsoft /proc/version 2>/dev/null; then
    PLATFORM="WSL (Windows Subsystem for Linux)"
    if grep -qi "WSL2" /proc/version 2>/dev/null; then
        PLATFORM_DETAILS="WSL2"
    else
        PLATFORM_DETAILS="WSL1"
    fi
fi

# If still unknown, assume physical
if [ "$PLATFORM" = "Unknown" ]; then
    PLATFORM="Physical Server"
fi

echo -e "${CYAN}Platform:${NC} ${YELLOW}$PLATFORM${NC}"
if [ -n "$PLATFORM_DETAILS" ]; then
    echo -e "${CYAN}Details:${NC} ${YELLOW}$PLATFORM_DETAILS${NC}"
fi

# CPU Information
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}CPU Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

CPU_CORES=$(nproc)
CPU_MODEL=$(lscpu | grep "Model name" | cut -d: -f2 | xargs)
if [ -z "$CPU_MODEL" ]; then
    CPU_MODEL=$(lscpu | grep "Architecture" | cut -d: -f2 | xargs)
fi

echo -e "${CYAN}CPU Cores:${NC} ${YELLOW}$CPU_CORES${NC}"
echo -e "${CYAN}CPU Model:${NC} ${YELLOW}$CPU_MODEL${NC}"

# Calculate recommended workers
RECOMMENDED_WORKERS=$((2 * CPU_CORES + 1))
echo -e "${CYAN}Recommended Gunicorn Workers:${NC} ${GREEN}$RECOMMENDED_WORKERS${NC}"

# Memory Information
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Memory Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_MEM=$(free -h | awk 'NR==2 {print $2}')
AVAILABLE_MEM=$(free -h | awk 'NR==2 {print $7}')
TOTAL_MEM_MB=$(free -m | awk 'NR==2 {print $2}')

echo -e "${CYAN}Total Memory:${NC} ${YELLOW}$TOTAL_MEM${NC}"
echo -e "${CYAN}Available Memory:${NC} ${YELLOW}$AVAILABLE_MEM${NC}"

# Memory recommendations
if [ "$TOTAL_MEM_MB" -lt 1024 ]; then
    echo -e "${RED}⚠ Warning: Low memory (<1GB). Consider reducing worker count.${NC}"
    ADJUSTED_WORKERS=$((CPU_CORES + 1))
    echo -e "${YELLOW}  Suggested workers: $ADJUSTED_WORKERS${NC}"
elif [ "$TOTAL_MEM_MB" -lt 2048 ]; then
    echo -e "${YELLOW}⚠ Moderate memory (<2GB). Standard configuration should work.${NC}"
else
    echo -e "${GREEN}✓ Sufficient memory for standard configuration${NC}"
fi

# Disk Information
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Disk Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

ROOT_TOTAL=$(df -h / | awk 'NR==2 {print $2}')
ROOT_USED=$(df -h / | awk 'NR==2 {print $3}')
ROOT_AVAILABLE=$(df -h / | awk 'NR==2 {print $4}')
ROOT_PERCENT=$(df -h / | awk 'NR==2 {print $5}')

echo -e "${CYAN}Root Partition:${NC}"
echo -e "  Total:     ${YELLOW}$ROOT_TOTAL${NC}"
echo -e "  Used:      ${YELLOW}$ROOT_USED${NC}"
echo -e "  Available: ${YELLOW}$ROOT_AVAILABLE${NC}"
echo -e "  Usage:     ${YELLOW}$ROOT_PERCENT${NC}"

# Network Information
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Network Information${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

SERVER_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

echo -e "${CYAN}Hostname:${NC} ${YELLOW}$HOSTNAME${NC}"
echo -e "${CYAN}IP Address:${NC} ${YELLOW}$SERVER_IP${NC}"

# Operating System
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Operating System${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ -f /etc/os-release ]; then
    . /etc/os-release
    echo -e "${CYAN}Distribution:${NC} ${YELLOW}$NAME${NC}"
    echo -e "${CYAN}Version:${NC} ${YELLOW}$VERSION${NC}"
    echo -e "${CYAN}Codename:${NC} ${YELLOW}$VERSION_CODENAME${NC}"
else
    echo -e "${YELLOW}OS information not available${NC}"
fi

KERNEL=$(uname -r)
echo -e "${CYAN}Kernel:${NC} ${YELLOW}$KERNEL${NC}"

# Optimization Recommendations
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Optimization Recommendations${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Raspberry Pi specific
if [ "$PLATFORM" = "Raspberry Pi" ]; then
    echo -e "${YELLOW}Raspberry Pi Optimizations:${NC}"
    echo "  • Use lightweight workers: $RECOMMENDED_WORKERS"
    echo "  • Enable swap if not present"
    echo "  • Consider using PostgreSQL on external storage"
    echo "  • Monitor temperature: vcgencmd measure_temp"
    
    # Check temperature
    if command -v vcgencmd &>/dev/null; then
        TEMP=$(vcgencmd measure_temp | cut -d= -f2)
        echo -e "${CYAN}Current Temperature:${NC} ${YELLOW}$TEMP${NC}"
    fi
    echo ""
fi

# Low memory specific
if [ "$TOTAL_MEM_MB" -lt 2048 ]; then
    echo -e "${YELLOW}Low Memory Optimizations:${NC}"
    echo "  • Reduce worker count to: $ADJUSTED_WORKERS"
    echo "  • Enable worker timeout: 120 seconds"
    echo "  • Use worker_class: sync (avoid threaded)"
    echo "  • Enable database connection pooling"
    echo ""
fi

# Virtual machine specific
if [ "$PLATFORM" = "Virtual Machine" ]; then
    echo -e "${YELLOW}Virtual Machine Notes:${NC}"
    echo "  • Ensure adequate vCPU allocation"
    echo "  • Enable nested virtualization if needed"
    echo "  • Consider shared folder performance impact"
    echo ""
fi

# Platform-specific deployment recommendations
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Platform-Specific Deployment Recommendations${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

case "$HARDWARE_TYPE" in
    "HP Mini Computer")
        echo -e "${GREEN}🖥️ HP ProDesk/EliteDesk Detected - Business-Grade Optimization:${NC}"
        echo "  • Performance Tier: $PERFORMANCE_TIER"
        echo "  • Recommended workers: $RECOMMENDED_WORKERS (aggressive scaling enabled)"
        echo "  • Database: PostgreSQL strongly recommended"
        echo "  • Caching: Redis with aggressive caching optimal"
        echo "  • SSL: Let's Encrypt recommended for production"
        echo "  • Network: Excellent for WAN/production deployment"
        echo "  • Performance: Optimized for business workloads"
        echo ""
        echo -e "${CYAN}💼 Ideal Business Use Cases:${NC}"
        echo "  • Department-level applications (50-500 users)"
        echo "  • Small-medium business deployment"
        echo "  • Multi-tenant environments"
        echo "  • Customer-facing applications"
        echo "  • Enterprise integration scenarios"
        echo ""
        echo -e "${YELLOW}🚀 Recommended Deployment:${NC}"
        echo -e "  ${GREEN}sudo bash ubuntu-deploy.sh --production${NC}   # Full production setup"
        echo -e "  ${GREEN}sudo bash ubuntu-deploy.sh --wan${NC}          # Internet-facing"
        ;;
    "Raspberry Pi")
        echo -e "${GREEN}📱 Raspberry Pi Model $PI_MODEL Detected - ARM Optimization:${NC}"
        echo "  • Performance Tier: $PERFORMANCE_TIER" 
        echo "  • Recommended workers: $ADJUSTED_WORKERS (conservative for ARM)"
        if [ "$PI_MODEL" = "5" ] || ([ "$PI_MODEL" = "4" ] && [ "$TOTAL_MEM_MB" -gt 4096 ]); then
            echo "  • Database: PostgreSQL suitable for this Pi"
        else
            echo "  • Database: SQLite recommended for this Pi"
        fi
        echo "  • Caching: Redis with power-efficient settings"
        echo "  • SSL: mkcert for LAN, Let's Encrypt available"
        echo "  • Network: Perfect for LAN/edge deployment"
        echo "  • Features: GPIO control, thermal monitoring available"
        echo ""
        echo -e "${CYAN}🏠 Ideal Pi Use Cases:${NC}"
        echo "  • Home lab and personal projects"
        echo "  • IoT edge computing"
        echo "  • Educational environments"
        echo "  • Low-power 24/7 operations"
        echo "  • Development and testing"
        echo ""
        echo -e "${YELLOW}🚀 Recommended Deployment:${NC}"
        echo -e "  ${GREEN}sudo bash ubuntu-deploy.sh --quick${NC}        # Quick Pi setup"
        echo -e "  ${GREEN}sudo bash ubuntu-deploy.sh --lan${NC}          # LAN-only"
        ;;
    *)
        echo -e "${GREEN}🖥️ General Ubuntu Server Detected:${NC}"
        echo "  • Recommended workers: $RECOMMENDED_WORKERS"
        if [ "$TOTAL_MEM_MB" -gt 2048 ]; then
            echo "  • Database: PostgreSQL suitable"
        else
            echo "  • Database: SQLite recommended"
        fi
        echo "  • Standard Ubuntu server optimization applied"
        echo ""
        echo -e "${YELLOW}🚀 Recommended Deployment:${NC}"
        echo -e "  ${GREEN}sudo bash ubuntu-deploy.sh --production${NC}   # Production setup"
        ;;
esac

# Generate configuration snippet
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}ArmGuard Cross-Compatibility Analysis${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Determine optimal requirements file and features
REQUIREMENTS_FILE="requirements.txt"
ENHANCED_FEATURES="false"
PSUTIL_REQUIRED="false"

if [[ "$PLATFORM" == *"Raspberry Pi"* ]]; then
    echo -e "${GREEN}🥧 Raspberry Pi detected - Full RPi optimizations available${NC}"
    REQUIREMENTS_FILE="requirements-rpi.txt"
    ENHANCED_FEATURES="true"
    PSUTIL_REQUIRED="true"
    echo -e "  • Thermal monitoring: ${GREEN}✓ Available${NC}"
    echo -e "  • GPIO control: ${GREEN}✓ Available${NC}"
    echo -e "  • ARM64 optimizations: ${GREEN}✓ Enabled${NC}"
elif [[ "$ARCH_SHORT" == "arm64" ]]; then
    echo -e "${YELLOW}🏗️ ARM64 architecture detected - ARM optimizations available${NC}"
    ENHANCED_FEATURES="true"
    PSUTIL_REQUIRED="true"
    echo -e "  • ARM64 optimizations: ${GREEN}✓ Enabled${NC}"
    echo -e "  • Enhanced monitoring: ${GREEN}✓ Available${NC}"
else
    echo -e "${BLUE}💻 Standard x86_64 environment - Base features available${NC}"
    echo -e "  • Cross-platform compatibility: ${GREEN}✓ Enabled${NC}"
    echo -e "  • Fallback monitoring: ${GREEN}✓ Available${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Deployment Recommendations${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Python Requirements:${NC}"
echo -e "  Primary: ${YELLOW}$REQUIREMENTS_FILE${NC}"
if [ "$PSUTIL_REQUIRED" = "true" ]; then
    echo -e "  Enhanced: ${GREEN}psutil for system monitoring${NC}"
else
    echo -e "  Enhanced: ${YELLOW}psutil optional (fallbacks available)${NC}"
fi

echo ""
echo -e "${CYAN}Installation Commands:${NC}"
if [ "$REQUIREMENTS_FILE" = "requirements-rpi.txt" ]; then
    echo -e "${GREEN}# Raspberry Pi optimized installation${NC}"
    echo -e "pip install -r requirements-rpi.txt"
elif [ "$ARCH_SHORT" = "arm64" ]; then
    echo -e "${GREEN}# ARM64 optimized installation${NC}"
    echo -e "pip install -r requirements.txt"
    echo -e "pip install psutil==5.9.8  # Enhanced monitoring"
else
    echo -e "${GREEN}# Standard installation${NC}"
    echo -e "pip install -r requirements.txt"
    echo -e "pip install psutil==5.9.8  # Optional for enhanced monitoring"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Suggested Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Add to deployment/config.sh or .env:${NC}"
echo ""
echo -e "${GREEN}# Auto-detected configuration"
echo "export ARMGUARD_WORKERS=$RECOMMENDED_WORKERS"
echo "export ARMGUARD_TIMEOUT=60"
echo "export ARMGUARD_PLATFORM=\"$PLATFORM\""
echo "export ARMGUARD_ARCH=\"$ARCH_SHORT\""
echo "export ARMGUARD_REQUIREMENTS=\"$REQUIREMENTS_FILE\""
echo "export ARMGUARD_ENHANCED_FEATURES=\"$ENHANCED_FEATURES\""
echo -e "${NC}"

# Save detection results to file
save_detection_results() {
    OUTPUT_FILE="/tmp/armguard-environment-$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "ArmGuard Environment Detection Report"
        echo "Generated: $(date)"
        echo ""
        echo "Architecture: $ARCH_TYPE"
        echo "Platform: $PLATFORM $PLATFORM_DETAILS"
        echo "Hardware Type: $HARDWARE_TYPE"
        if [ -n "$PI_MODEL" ]; then
            echo "Pi Model: $PI_MODEL"
        fi
        if [ -n "$PERFORMANCE_TIER" ]; then
            echo "Performance Tier: $PERFORMANCE_TIER"
        fi
        echo "CPU Cores: $CPU_CORES"
        echo "CPU Model: $CPU_MODEL"
        echo "Total Memory: $TOTAL_MEM"
        echo "Hostname: $HOSTNAME"
        echo "IP Address: $SERVER_IP"
        echo "OS: $NAME $VERSION"
        echo "Kernel: $KERNEL"
        echo ""
        echo "Recommended Workers: $RECOMMENDED_WORKERS"
        echo "Requirements File: $REQUIREMENTS_FILE"
        echo "Enhanced Features: $ENHANCED_FEATURES"
    } > "$OUTPUT_FILE"
    
    echo -e "${GREEN}✓ Detection report saved to: $OUTPUT_FILE${NC}"
    export DETECTION_REPORT="$OUTPUT_FILE"
}

# Export detected configuration for deployment scripts
export_deployment_config() {
    export ARMGUARD_WORKERS="$RECOMMENDED_WORKERS"
    export ARMGUARD_TIMEOUT="60"
    export ARMGUARD_PLATFORM="$PLATFORM"
    export ARMGUARD_ARCH="$ARCH_SHORT"
    export ARMGUARD_REQUIREMENTS="$REQUIREMENTS_FILE"
    export ARMGUARD_ENHANCED_FEATURES="$ENHANCED_FEATURES"
    export HARDWARE_TYPE
    export PLATFORM_DETAILS
    export CPU_CORES
    export TOTAL_MEM_MB
    export PERFORMANCE_TIER
    if [ -n "$PI_MODEL" ]; then
        export PI_MODEL
    fi
    
    echo -e "${GREEN}✓ Environment variables exported for deployment${NC}"
}

# Auto-deployment option
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Deployment Options${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}🚀 Ready to deploy ArmGuard automatically based on detected environment${NC}"
echo ""

# Determine deployment command based on hardware
case "$HARDWARE_TYPE" in
    "HP Mini Computer")
        DEPLOY_CMD="bash ../../ubuntu-deploy.sh --production"
        DEPLOY_DESC="Production deployment optimized for HP ProDesk/EliteDesk"
        ;;
    "Raspberry Pi")
        if [ "$PI_MODEL" = "5" ] || ([ "$PI_MODEL" = "4" ] && [ "$TOTAL_MEM_MB" -gt 4096 ]); then
            DEPLOY_CMD="bash ../../ubuntu-deploy.sh --production"
            DEPLOY_DESC="Production deployment for high-performance Pi"
        else
            DEPLOY_CMD="bash ../../ubuntu-deploy.sh --lan"
            DEPLOY_DESC="LAN deployment optimized for Raspberry Pi"
        fi
        ;;
    *)
        if [ "$TOTAL_MEM_MB" -gt 4096 ]; then
            DEPLOY_CMD="bash ../../ubuntu-deploy.sh --production"
            DEPLOY_DESC="Production deployment for high-spec server"
        else
            DEPLOY_CMD="bash ../../ubuntu-deploy.sh --lan"
            DEPLOY_DESC="Standard LAN deployment"
        fi
        ;;
esac

echo -e "${YELLOW}Recommended deployment:${NC}"
echo -e "  Command: ${GREEN}$DEPLOY_CMD${NC}"
echo -e "  Description: ${CYAN}$DEPLOY_DESC${NC}"
echo ""

# Deployment mode selection
echo -e "${YELLOW}Select deployment mode:${NC}"
echo "  1) Auto-deploy (recommended based on detection)"
echo "  2) Production deployment (--production)"  
echo "  3) LAN deployment (--lan)"
echo "  4) Quick deployment (--quick)"
echo "  5) Custom deployment options"
echo "  6) Save detection results and exit"
echo "  7) Exit without deploying"
echo ""

read -p "Enter your choice (1-7): " deploy_choice

case "$deploy_choice" in
    "1")
        echo -e "${GREEN}🚀 Starting auto-deployment...${NC}"
        save_detection_results
        export_deployment_config
        
        # Check if running as root
        if [ "$EUID" -ne 0 ]; then 
            echo -e "${RED}❌ Deployment requires root privileges${NC}"
            echo -e "${YELLOW}Re-run with: sudo $0${NC}"
            exit 1
        fi
        
        echo -e "${CYAN}Executing: $DEPLOY_CMD${NC}"
        cd "$(dirname "$0")/../.." && $DEPLOY_CMD
        ;;
    "2")
        echo -e "${GREEN}🏭 Starting production deployment...${NC}"
        save_detection_results
        export_deployment_config
        
        if [ "$EUID" -ne 0 ]; then 
            echo -e "${RED}❌ Deployment requires root privileges${NC}"
            echo -e "${YELLOW}Re-run with: sudo $0${NC}"
            exit 1
        fi
        
        cd "$(dirname "$0")/../.." && bash ubuntu-deploy.sh --production
        ;;
    "3")
        echo -e "${GREEN}🏠 Starting LAN deployment...${NC}"
        save_detection_results
        export_deployment_config
        
        if [ "$EUID" -ne 0 ]; then 
            echo -e "${RED}❌ Deployment requires root privileges${NC}"
            echo -e "${YELLOW}Re-run with: sudo $0${NC}"
            exit 1
        fi
        
        cd "$(dirname "$0")/../.." && bash ubuntu-deploy.sh --lan
        ;;
    "4")
        echo -e "${GREEN}⚡ Starting quick deployment...${NC}"
        save_detection_results
        export_deployment_config
        
        if [ "$EUID" -ne 0 ]; then 
            echo -e "${RED}❌ Deployment requires root privileges${NC}"
            echo -e "${YELLOW}Re-run with: sudo $0${NC}"
            exit 1
        fi
        
        cd "$(dirname "$0")/../.." && bash ubuntu-deploy.sh --quick
        ;;
    "5")
        echo -e "${CYAN}Available deployment options:${NC}"
        echo "  --production  : Full production setup with SSL and security"
        echo "  --lan        : LAN-only deployment"
        echo "  --wan        : Internet-facing deployment"
        echo "  --hybrid     : Mixed LAN/WAN deployment"
        echo "  --quick      : Quick setup with minimal prompts"
        echo ""
        read -p "Enter deployment options: " custom_options
        
        save_detection_results
        export_deployment_config
        
        if [ "$EUID" -ne 0 ]; then 
            echo -e "${RED}❌ Deployment requires root privileges${NC}"
            echo -e "${YELLOW}Re-run with: sudo $0${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}🛠️ Starting custom deployment...${NC}"
        cd "$(dirname "$0")/../.." && bash ubuntu-deploy.sh $custom_options
        ;;
    "6")
        save_detection_results
        echo -e "${GREEN}✓ Detection results saved. You can deploy manually later using:${NC}"
        echo -e "${YELLOW}sudo $DEPLOY_CMD${NC}"
        ;;
    "7"|"")
        echo -e "${YELLOW}⏹️ Exiting without deployment${NC}"
        echo -e "${CYAN}To deploy manually later, run:${NC}"
        echo -e "${YELLOW}sudo $DEPLOY_CMD${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║    Environment Detection and Deployment Complete          ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
