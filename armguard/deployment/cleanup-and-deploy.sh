#!/bin/bash

################################################################################
# ArmGuard Deployment Cleanup and Retry Script
# 
# This script cleans up a failed deployment and retries automatically
# Usage: sudo bash deployment/cleanup-and-deploy.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ArmGuard Cleanup and Deployment Retry Script          ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    echo ""
    echo -e "${YELLOW}Usage: sudo bash deployment/cleanup-and-deploy.sh${NC}"
    exit 1
fi

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${YELLOW}Project source directory: ${PROJECT_SOURCE_DIR}${NC}"
echo ""

# Step 1: Clean up previous installation
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Cleaning Up Previous Installation${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Stopping Gunicorn service...${NC}"
systemctl stop gunicorn-armguard 2>/dev/null && echo -e "${GREEN}✓ Service stopped${NC}" || echo -e "${YELLOW}⚠ Service not running${NC}"

echo -e "${YELLOW}Disabling Gunicorn service...${NC}"
systemctl disable gunicorn-armguard 2>/dev/null && echo -e "${GREEN}✓ Service disabled${NC}" || echo -e "${YELLOW}⚠ Service not enabled${NC}"

echo -e "${YELLOW}Removing systemd service file...${NC}"
if [ -f /etc/systemd/system/gunicorn-armguard.service ]; then
    rm -f /etc/systemd/system/gunicorn-armguard.service
    echo -e "${GREEN}✓ Service file removed${NC}"
else
    echo -e "${YELLOW}⚠ Service file not found${NC}"
fi

echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd reloaded${NC}"

echo -e "${YELLOW}Removing project directory...${NC}"
if [ -d /var/www/armguard ]; then
    rm -rf /var/www/armguard
    echo -e "${GREEN}✓ Directory removed: /var/www/armguard${NC}"
else
    echo -e "${YELLOW}⚠ Directory not found: /var/www/armguard${NC}"
fi

echo -e "${YELLOW}Removing log directory...${NC}"
if [ -d /var/log/armguard ]; then
    rm -rf /var/log/armguard
    echo -e "${GREEN}✓ Log directory removed: /var/log/armguard${NC}"
else
    echo -e "${YELLOW}⚠ Log directory not found${NC}"
fi

echo -e "${YELLOW}Removing Nginx configuration...${NC}"
if [ -f /etc/nginx/sites-enabled/armguard ]; then
    rm -f /etc/nginx/sites-enabled/armguard
    echo -e "${GREEN}✓ Nginx site disabled${NC}"
fi
if [ -f /etc/nginx/sites-available/armguard ]; then
    rm -f /etc/nginx/sites-available/armguard
    echo -e "${GREEN}✓ Nginx config removed${NC}"
fi

echo -e "${YELLOW}Reloading Nginx...${NC}"
systemctl reload nginx 2>/dev/null && echo -e "${GREEN}✓ Nginx reloaded${NC}" || echo -e "${YELLOW}⚠ Nginx not running${NC}"

echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""

# Step 2: Pull latest code
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Updating Code from GitHub${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

cd "$PROJECT_SOURCE_DIR"

# Check if git repository
if [ -d .git ]; then
    echo -e "${YELLOW}Fetching latest changes from GitHub...${NC}"
    git fetch origin
    
    # Check if there are local changes
    if ! git diff-index --quiet HEAD --; then
        echo -e "${YELLOW}Local changes detected. Stashing...${NC}"
        git stash
    fi
    
    echo -e "${YELLOW}Pulling latest code...${NC}"
    git pull origin main
    
    echo -e "${GREEN}✓ Code updated!${NC}"
else
    echo -e "${YELLOW}⚠ Not a git repository. Skipping update.${NC}"
fi

echo ""

# Step 3: Make scripts executable
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Preparing Deployment Scripts${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Making deployment scripts executable...${NC}"
chmod +x "$SCRIPT_DIR/deploy-armguard.sh"
chmod +x "$SCRIPT_DIR/install-gunicorn-service.sh"
chmod +x "$PROJECT_SOURCE_DIR/setup-domain-linux.sh"

echo -e "${GREEN}✓ Scripts ready!${NC}"
echo ""

# Step 4: Run deployment
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Running Automated Deployment${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Starting deployment in 3 seconds...${NC}"
echo -e "${YELLOW}Press Ctrl+C to cancel${NC}"
sleep 3

echo ""
bash "$SCRIPT_DIR/deploy-armguard.sh"

# Check if deployment succeeded
DEPLOY_EXIT_CODE=$?

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
if [ $DEPLOY_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment completed successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Your ArmGuard application should now be running.${NC}"
    echo ""
    echo -e "${CYAN}Check status:${NC}"
    echo -e "  sudo systemctl status gunicorn-armguard"
    echo ""
    echo -e "${CYAN}View logs:${NC}"
    echo -e "  sudo journalctl -u gunicorn-armguard -f"
    echo ""
    echo -e "${CYAN}Access application:${NC}"
    echo -e "  http://armguard.rds:8000"
    echo -e "  http://$(hostname -I | awk '{print $1}'):8000"
else
    echo -e "${RED}✗ Deployment failed with exit code: ${DEPLOY_EXIT_CODE}${NC}"
    echo ""
    echo -e "${YELLOW}Check the error messages above for details.${NC}"
    echo ""
    echo -e "${CYAN}You can try running the deployment manually:${NC}"
    echo -e "  sudo bash deployment/deploy-armguard.sh"
fi
echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
echo ""
