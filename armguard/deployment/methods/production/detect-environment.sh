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

# Check for Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null)
    if [[ "$MODEL" == *"Raspberry Pi"* ]]; then
        PLATFORM="Raspberry Pi"
        PLATFORM_DETAILS="$MODEL"
        
        # Detect specific Pi model
        if [[ "$MODEL" == *"Pi 5"* ]]; then
            PI_MODEL="5"
        elif [[ "$MODEL" == *"Pi 4"* ]]; then
            PI_MODEL="4"
        elif [[ "$MODEL" == *"Pi 3"* ]]; then
            PI_MODEL="3"
        else
            PI_MODEL="Unknown"
        fi
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

# Generate configuration snippet
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
echo -e "${NC}"

# Save to file option
echo ""
echo -e "${YELLOW}Would you like to save this information? (y/n)${NC}"
read -p "> " save_choice

if [ "$save_choice" = "y" ] || [ "$save_choice" = "Y" ]; then
    OUTPUT_FILE="/tmp/armguard-environment-$(date +%Y%m%d_%H%M%S).txt"
    {
        echo "ArmGuard Environment Detection Report"
        echo "Generated: $(date)"
        echo ""
        echo "Architecture: $ARCH_TYPE"
        echo "Platform: $PLATFORM $PLATFORM_DETAILS"
        echo "CPU Cores: $CPU_CORES"
        echo "CPU Model: $CPU_MODEL"
        echo "Total Memory: $TOTAL_MEM"
        echo "Hostname: $HOSTNAME"
        echo "IP Address: $SERVER_IP"
        echo "OS: $NAME $VERSION"
        echo "Kernel: $KERNEL"
        echo ""
        echo "Recommended Workers: $RECOMMENDED_WORKERS"
    } > "$OUTPUT_FILE"
    
    echo -e "${GREEN}✓ Saved to: $OUTPUT_FILE${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Environment Detection Complete                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
