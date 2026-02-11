#!/bin/bash

################################################################################
# Complete Cleanup and Re-deployment Script
# 
# This script will:
# 1. Clean up any failed deployment remnants
# 2. Ensure you have the latest code from Git
# 3. Run the quick fix to get everything working
#
# Usage: sudo bash cleanup-and-redeploy.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║          ${GREEN}ArmGuard Cleanup and Re-deployment${CYAN}                    ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: Run as root (use sudo)${NC}"
    exit 1
fi

# Detect project directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

echo -e "${BLUE}Step 1: Cleaning Up Failed Deployment${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Stop and disable service
if systemctl list-unit-files | grep -q gunicorn-armguard.service; then
    echo -e "${YELLOW}Stopping gunicorn-armguard service...${NC}"
    systemctl stop gunicorn-armguard 2>/dev/null || true
    systemctl disable gunicorn-armguard 2>/dev/null || true
    echo -e "${GREEN}✓ Service stopped${NC}"
fi

# Remove service file
if [ -f /etc/systemd/system/gunicorn-armguard.service ]; then
    echo -e "${YELLOW}Removing service file...${NC}"
    rm -f /etc/systemd/system/gunicorn-armguard.service
    echo -e "${GREEN}✓ Service file removed${NC}"
fi

# Reload systemd
echo -e "${YELLOW}Reloading systemd...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

# Remove wrong static location if it exists
if [ -d "/var/www/armguard" ]; then
    echo -e "  ${YELLOW}⚠ Found files at /var/www/armguard (incorrect location)${NC}"
    read -p "  Remove /var/www/armguard? (yes/no) [yes]: " REMOVE_VAR_WWW
    REMOVE_VAR_WWW=${REMOVE_VAR_WWW:-yes}
    if [[ "$REMOVE_VAR_WWW" =~ ^[Yy] ]]; then
        rm -rf /var/www/armguard
        echo -e "${GREEN}✓ Removed /var/www/armguard${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Step 2: Verifying Project Directory${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}✗ Project directory not found: $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${RED}✗ manage.py not found in $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Project directory verified: $PROJECT_DIR${NC}"

echo ""
echo -e "${BLUE}Step 3: Checking for Git Updates${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

cd "$PROJECT_DIR"

if git rev-parse --git-dir > /dev/null 2>&1; then
    # Get current user (not root)
    ORIGINAL_USER=$(who am i | awk '{print $1}')
    if [ -z "$ORIGINAL_USER" ]; then
        ORIGINAL_USER="rds"  # fallback
    fi
    
    echo -e "${YELLOW}Fetching latest changes from Git...${NC}"
    sudo -u $ORIGINAL_USER git fetch origin main 2>/dev/null || true
    
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u} 2>/dev/null || echo $LOCAL)
    
    if [ "$LOCAL" != "$REMOTE" ]; then
        echo -e "${YELLOW}⚠ Updates available from Git${NC}"
        read -p "Pull latest changes? (yes/no) [yes]: " PULL_GIT
        PULL_GIT=${PULL_GIT:-yes}
        if [[ "$PULL_GIT" =~ ^[Yy] ]]; then
            echo -e "${YELLOW}Pulling latest changes...${NC}"
            sudo -u $ORIGINAL_USER git pull origin main
            echo -e "${GREEN}✓ Code updated${NC}"
        fi
    else
        echo -e "${GREEN}✓ Code is up to date${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Not a Git repository${NC}"
fi

echo ""
echo -e "${BLUE}Step 4: Running Quick Fix Script${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

QUICK_FIX_SCRIPT="$PROJECT_DIR/deployment_A/methods/production/quick-fix-use-cloned-repo.sh"

if [ ! -f "$QUICK_FIX_SCRIPT" ]; then
    echo -e "${RED}✗ Quick fix script not found: $QUICK_FIX_SCRIPT${NC}"
    echo -e "${YELLOW}Please pull the latest changes from Git${NC}"
    exit 1
fi

chmod +x "$QUICK_FIX_SCRIPT"

echo -e "${CYAN}Running quick fix script...${NC}"
echo ""

bash "$QUICK_FIX_SCRIPT"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Cleanup and Re-deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
