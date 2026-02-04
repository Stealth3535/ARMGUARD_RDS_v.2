#!/bin/bash
# Pre-deployment validation script for ArmGuard A+ RPi deployment
# This script validates the deployment environment and fixes common issues

echo "🔍 ArmGuard A+ Pre-Deployment Validation"
echo "========================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VALIDATION_FAILED=false

log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
    VALIDATION_FAILED=true
}

# Check system requirements
check_system_requirements() {
    log "🖥️ Checking system requirements..."
    
    # Check Ubuntu version
    if ! lsb_release -a 2>/dev/null | grep -q "Ubuntu"; then
        warn "Non-Ubuntu system detected - deployment may have issues"
    fi
    
    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>/dev/null | cut -d' ' -f2)
    if [[ ! "$PYTHON_VERSION" =~ ^3\.(12|13) ]]; then
        error "Python 3.12+ required, found: $PYTHON_VERSION"
    else
        log "✅ Python $PYTHON_VERSION detected"
    fi
    
    # Check available memory
    MEMORY_MB=$(free -m | awk 'NR==2{printf "%.0f", $2}')
    if [ $MEMORY_MB -lt 2000 ]; then
        warn "Low memory: ${MEMORY_MB}MB - consider adding swap"
    else
        log "✅ Memory: ${MEMORY_MB}MB available"
    fi
}

# Check required system packages
check_system_packages() {
    log "📦 Checking system packages..."
    
    REQUIRED_PACKAGES=("python3-pip" "python3-venv" "python3-dev" "postgresql" "nginx" "redis-server" "git" "curl" "build-essential" "libpq-dev")
    
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$package "; then
            error "Missing package: $package"
        fi
    done
    
    log "✅ System packages check completed"
}

# Check network connectivity  
check_network() {
    log "🌐 Checking network connectivity..."
    
    if ! ping -c 1 github.com >/dev/null 2>&1; then
        error "Cannot reach GitHub - check internet connection"
    fi
    
    if ! ping -c 1 pypi.org >/dev/null 2>&1; then
        error "Cannot reach PyPI - package installation may fail"
    fi
    
    log "✅ Network connectivity OK"
}

# Check disk space
check_disk_space() {
    log "💾 Checking disk space..."
    
    AVAILABLE_GB=$(df / | awk 'NR==2 {printf "%.1f", $4/1024/1024}')
    if (( $(echo "$AVAILABLE_GB < 2.0" | bc -l) )); then
        error "Insufficient disk space: ${AVAILABLE_GB}GB available (2GB+ recommended)"
    else
        log "✅ Disk space: ${AVAILABLE_GB}GB available"
    fi
}

# Check for conflicting services
check_conflicting_services() {
    log "⚡ Checking for service conflicts..."
    
    # Check if ports are already in use
    if netstat -tuln 2>/dev/null | grep -q ":80 "; then
        warn "Port 80 already in use - may conflict with Nginx"
    fi
    
    if netstat -tuln 2>/dev/null | grep -q ":5432 "; then
        log "✅ PostgreSQL detected on port 5432"
    fi
    
    if netstat -tuln 2>/dev/null | grep -q ":6379 "; then
        log "✅ Redis detected on port 6379"
    fi
}

# Check ARM64 specific requirements
check_arm64_requirements() {
    log "🍓 Checking ARM64/RPi requirements..."
    
    ARCH=$(uname -m)
    if [[ "$ARCH" != "aarch64" ]]; then
        warn "Non-ARM64 architecture: $ARCH - deployment optimized for ARM64"
    else
        log "✅ ARM64 architecture detected"
    fi
    
    # Check for Raspberry Pi
    if [ -f /proc/device-tree/model ]; then
        RPI_MODEL=$(cat /proc/device-tree/model 2>/dev/null)
        log "✅ Raspberry Pi detected: $RPI_MODEL"
    fi
    
    # Check thermal monitoring
    if command -v vcgencmd >/dev/null 2>&1; then
        TEMP=$(vcgencmd measure_temp 2>/dev/null | sed 's/temp=//; s/°C//')
        if (( $(echo "$TEMP > 70" | bc -l) )); then
            warn "High temperature: ${TEMP}°C - ensure adequate cooling"
        else
            log "✅ Temperature: ${TEMP}°C"
        fi
    fi
}

# Run all checks
main() {
    echo ""
    check_system_requirements
    echo ""
    check_system_packages  
    echo ""
    check_network
    echo ""
    check_disk_space
    echo ""
    check_conflicting_services
    echo ""
    check_arm64_requirements
    echo ""
    
    # Final report
    echo "========================================"
    if [ "$VALIDATION_FAILED" = true ]; then
        echo -e "${RED}❌ Pre-deployment validation FAILED${NC}"
        echo "Please resolve the errors above before deployment"
        exit 1
    else
        echo -e "${GREEN}✅ Pre-deployment validation PASSED${NC}"
        echo "System ready for ArmGuard A+ deployment!"
        echo ""
        echo "To start deployment, run:"
        echo 'curl -sSL "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/quick-rpi-setup.sh?$(date +%s)" | bash'
    fi
}

main "$@"