#!/bin/bash

################################################################################
# ArmGuard Pre-Deployment Validation Script
# 
# This script checks all requirements BEFORE deployment to catch issues early
# Usage: sudo bash deployment/pre-check.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     ArmGuard Pre-Deployment Validation                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}✗ ERROR: Must run as root (use sudo)${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✓ Running as root${NC}"
fi

# Check internet connectivity
echo ""
echo -e "${YELLOW}Checking network connectivity...${NC}"
if ping -c 1 -W 2 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Internet connectivity OK${NC}"
else
    echo -e "${RED}✗ ERROR: No internet connection${NC}"
    echo -e "${YELLOW}  Fix: Check network cable/WiFi and run: sudo systemctl restart NetworkManager${NC}"
    ((ERRORS++))
fi

# Check DNS resolution
if ping -c 1 -W 2 google.com > /dev/null 2>&1; then
    echo -e "${GREEN}✓ DNS resolution OK${NC}"
else
    echo -e "${RED}✗ ERROR: DNS not working${NC}"
    echo -e "${YELLOW}  Fix: Check /etc/resolv.conf or run: sudo systemctl restart systemd-resolved${NC}"
    ((ERRORS++))
fi

# Check Python 3
echo ""
echo -e "${YELLOW}Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}✓ Python 3 installed: ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}✗ ERROR: Python 3 not found${NC}"
    echo -e "${YELLOW}  Fix: sudo apt install python3${NC}"
    ((ERRORS++))
fi

# Check python3-venv
if dpkg -l | grep -q python3-venv; then
    echo -e "${GREEN}✓ python3-venv installed${NC}"
else
    echo -e "${RED}✗ ERROR: python3-venv not installed${NC}"
    echo -e "${YELLOW}  Fix: sudo apt install python3-venv${NC}"
    ((ERRORS++))
fi

# Check pip
if command -v pip3 &> /dev/null; then
    echo -e "${GREEN}✓ pip3 installed${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: pip3 not found (will be installed)${NC}"
    ((WARNINGS++))
fi

# Check Git
echo ""
echo -e "${YELLOW}Checking Git...${NC}"
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    echo -e "${GREEN}✓ Git installed: ${GIT_VERSION}${NC}"
else
    echo -e "${RED}✗ ERROR: Git not installed${NC}"
    echo -e "${YELLOW}  Fix: sudo apt install git${NC}"
    ((ERRORS++))
fi

# Check project directory
echo ""
echo -e "${YELLOW}Checking project files...${NC}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${GREEN}✓ manage.py found${NC}"
else
    echo -e "${RED}✗ ERROR: manage.py not found in ${PROJECT_DIR}${NC}"
    ((ERRORS++))
fi

if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    echo -e "${GREEN}✓ requirements.txt found${NC}"
else
    echo -e "${RED}✗ ERROR: requirements.txt not found${NC}"
    ((ERRORS++))
fi

if [ -f "$PROJECT_DIR/core/wsgi.py" ]; then
    echo -e "${GREEN}✓ wsgi.py found${NC}"
else
    echo -e "${RED}✗ ERROR: core/wsgi.py not found${NC}"
    ((ERRORS++))
fi

# Check disk space
echo ""
echo -e "${YELLOW}Checking disk space...${NC}"
AVAILABLE_SPACE=$(df / | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -gt 1048576 ]; then  # 1GB in KB
    AVAILABLE_GB=$((AVAILABLE_SPACE / 1048576))
    echo -e "${GREEN}✓ Disk space OK: ${AVAILABLE_GB}GB available${NC}"
else
    echo -e "${RED}✗ ERROR: Low disk space (need at least 1GB)${NC}"
    ((ERRORS++))
fi

# Check memory
echo ""
echo -e "${YELLOW}Checking memory...${NC}"
TOTAL_MEM=$(free -m | awk 'NR==2 {print $2}')
if [ "$TOTAL_MEM" -gt 512 ]; then
    echo -e "${GREEN}✓ Memory OK: ${TOTAL_MEM}MB${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Low memory (${TOTAL_MEM}MB). Consider adding swap.${NC}"
    ((WARNINGS++))
fi

# Check if ports are available
echo ""
echo -e "${YELLOW}Checking ports...${NC}"
if ! lsof -i :80 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Port 80 available${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Port 80 already in use${NC}"
    lsof -i :80 | head -2
    ((WARNINGS++))
fi

if ! lsof -i :443 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Port 443 available${NC}"
else
    echo -e "${YELLOW}⚠ WARNING: Port 443 already in use${NC}"
    lsof -i :443 | head -2
    ((WARNINGS++))
fi

# Check if previous installation exists
echo ""
echo -e "${YELLOW}Checking for previous installation...${NC}"
if [ -d "/var/www/armguard" ]; then
    echo -e "${YELLOW}⚠ WARNING: /var/www/armguard already exists${NC}"
    echo -e "${YELLOW}  Will be cleaned up during deployment${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓ No previous installation${NC}"
fi

if systemctl list-units --full -all | grep -q gunicorn-armguard; then
    echo -e "${YELLOW}⚠ WARNING: gunicorn-armguard service exists${NC}"
    echo -e "${YELLOW}  Will be cleaned up during deployment${NC}"
    ((WARNINGS++))
else
    echo -e "${GREEN}✓ No previous service${NC}"
fi

# Test PyPI connectivity
echo ""
echo -e "${YELLOW}Testing PyPI connectivity...${NC}"
if curl -s --head --max-time 5 https://pypi.org | head -n 1 | grep "HTTP/[12].[01] [23].." > /dev/null; then
    echo -e "${GREEN}✓ Can reach PyPI${NC}"
else
    echo -e "${RED}✗ ERROR: Cannot reach PyPI (Python package repository)${NC}"
    echo -e "${YELLOW}  This will cause pip install to fail${NC}"
    echo -e "${YELLOW}  Fix: Check internet/firewall settings${NC}"
    ((ERRORS++))
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to deploy.${NC}"
    echo ""
    echo -e "${GREEN}Run deployment with:${NC}"
    echo -e "${BLUE}  sudo bash deployment/deploy-armguard.sh${NC}"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found, but can proceed${NC}"
    echo ""
    echo -e "${YELLOW}Run deployment with:${NC}"
    echo -e "${BLUE}  sudo bash deployment/deploy-armguard.sh${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ ${ERRORS} error(s) found!${NC}"
    echo -e "${YELLOW}⚠ ${WARNINGS} warning(s) found${NC}"
    echo ""
    echo -e "${RED}Fix the errors above before deploying.${NC}"
    echo ""
    exit 1
fi
