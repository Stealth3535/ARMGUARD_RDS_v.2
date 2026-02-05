#!/bin/bash

################################################################################
# ArmGuard Log Rotation Setup Script
# 
# Installs and configures log rotation for ArmGuard
# Usage: sudo bash deployment/setup-logrotate.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          ArmGuard Log Rotation Setup                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Check if logrotate is installed
if ! command -v logrotate &> /dev/null; then
    echo -e "${YELLOW}Installing logrotate...${NC}"
    apt-get update -qq
    apt-get install -y logrotate
    echo -e "${GREEN}✓ Logrotate installed${NC}"
else
    echo -e "${GREEN}✓ Logrotate already installed${NC}"
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copy logrotate configuration
echo -e "${YELLOW}Installing logrotate configuration...${NC}"
cp "$SCRIPT_DIR/logrotate-armguard.conf" /etc/logrotate.d/armguard
chmod 644 /etc/logrotate.d/armguard

echo -e "${GREEN}✓ Configuration installed: /etc/logrotate.d/armguard${NC}"

# Test configuration
echo -e "${YELLOW}Testing logrotate configuration...${NC}"
if logrotate -d /etc/logrotate.d/armguard 2>&1 | grep -q "error"; then
    echo -e "${RED}✗ Configuration test failed${NC}"
    logrotate -d /etc/logrotate.d/armguard
    exit 1
else
    echo -e "${GREEN}✓ Configuration test passed${NC}"
fi

# Display current status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Log Rotation Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""
echo "  Frequency:       Daily"
echo "  Retention:       14 days"
echo "  Compression:     Enabled"
echo "  Logs managed:"
echo "    - /var/log/armguard/*.log"
echo "    - /var/log/nginx/armguard_*.log"
echo ""

# Force a test rotation (optional)
echo -e "${YELLOW}Would you like to test log rotation now? (y/n)${NC}"
read -p "> " test_now

if [ "$test_now" = "y" ] || [ "$test_now" = "Y" ]; then
    echo -e "${YELLOW}Running test rotation...${NC}"
    logrotate -f /etc/logrotate.d/armguard
    echo -e "${GREEN}✓ Test rotation complete${NC}"
    echo ""
    echo -e "${CYAN}Check rotated logs in:${NC}"
    echo "  /var/log/armguard/"
    echo "  /var/log/nginx/"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           Log Rotation Setup Complete                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Logs will be automatically rotated daily at 06:25 AM${NC}"
