#!/bin/bash

################################################################################
# Quick RPi Setup Script - Run this on your Raspberry Pi
# Downloads and executes the full ArmGuard A+ Performance deployment
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

# Check if running on Raspberry Pi
check_system() {
    log "🔍 Checking system compatibility..."
    
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        warn "Not detected as Raspberry Pi, but continuing anyway..."
    fi
    
    # Check internet connection
    if ! ping -c 1 github.com &> /dev/null; then
        error "No internet connection. Please check your network."
        exit 1
    fi
    
    log "✅ System check passed"
}

# Download and run deployment script
deploy_armguard() {
    log "🚀 Starting ArmGuard A+ Performance deployment..."
    
    # Create temporary directory
    TEMP_DIR=$(mktemp -d)
    cd "$TEMP_DIR"
    
    # Download the deployment script
    log "📥 Downloading deployment script from GitHub..."
    wget -O deploy-rpi-test.sh \
        "https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/v2.1.0-aplus/armguard/deployment/deploy-rpi-test.sh"
    
    # Make executable and run
    chmod +x deploy-rpi-test.sh
    
    log "🎯 Running ArmGuard A+ deployment..."
    sudo ./deploy-rpi-test.sh
    
    # Cleanup
    cd /
    rm -rf "$TEMP_DIR"
    
    log "✅ Deployment completed!"
}

# Main function
main() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║           ArmGuard A+ Performance Edition                    ║${NC}"
    echo -e "${BLUE}║           Raspberry Pi Quick Deployment                     ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    check_system
    deploy_armguard
    
    echo ""
    echo -e "${GREEN}🎉 ArmGuard A+ deployment completed successfully!${NC}"
    echo -e "${BLUE}   Access your application at: http://$(hostname -I | awk '{print $1}')${NC}"
    echo -e "${BLUE}   Admin login: admin / ArmGuard2024!${NC}"
}

main "$@"