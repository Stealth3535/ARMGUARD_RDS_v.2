#!/bin/bash

################################################################################
# ArmGuard Safe Update Script
# 
# This script safely updates the application while preserving all data
# Usage: sudo bash deployment/update-armguard.sh
#
# What it does:
# - Backs up database automatically
# - Pulls latest code from GitHub
# - Installs/updates dependencies
# - Runs migrations (preserves data)
# - Collects static files
# - Restarts services
# - Verifies deployment
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="/var/www/armguard"
BACKUP_DIR="/var/www/armguard/backups"
SERVICE_NAME="gunicorn-armguard"
RUN_USER="www-data"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Print banner
clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║         ${GREEN}ArmGuard Safe Update Script${CYAN}                      ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║  This script will:                                        ║${NC}"
echo -e "${CYAN}║  ${YELLOW}✓${CYAN} Backup your database automatically                   ║${NC}"
echo -e "${CYAN}║  ${YELLOW}✓${CYAN} Update code from GitHub                              ║${NC}"
echo -e "${CYAN}║  ${YELLOW}✓${CYAN} Install new dependencies                             ║${NC}"
echo -e "${CYAN}║  ${YELLOW}✓${CYAN} Run migrations (preserves all data)                  ║${NC}"
echo -e "${CYAN}║  ${YELLOW}✓${CYAN} Restart services                                     ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}║  ${GREEN}✓ Your data is SAFE - automatic backup included${CYAN}      ║${NC}"
echo -e "${CYAN}║                                                            ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    echo ""
    echo -e "${YELLOW}Usage: sudo bash deployment/update-armguard.sh${NC}"
    exit 1
fi

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}ERROR: Project directory not found: $PROJECT_DIR${NC}"
    echo -e "${YELLOW}Run the initial deployment first: sudo bash deployment/deploy-armguard.sh${NC}"
    exit 1
fi

# Function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to check command success
check_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1 failed${NC}"
        exit 1
    fi
}

# Step 1: Pre-update checks
print_section "Step 1: Pre-Update Checks"

echo -e "${YELLOW}Checking service status...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service is running${NC}"
    SERVICE_WAS_RUNNING=true
else
    echo -e "${YELLOW}⚠ Service is not running${NC}"
    SERVICE_WAS_RUNNING=false
fi

echo -e "${YELLOW}Checking database...${NC}"
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    DB_SIZE=$(du -h "$PROJECT_DIR/db.sqlite3" | cut -f1)
    echo -e "${GREEN}✓ Database found (Size: $DB_SIZE)${NC}"
    HAS_DATABASE=true
else
    echo -e "${YELLOW}⚠ No database found (first run?)${NC}"
    HAS_DATABASE=false
fi

echo -e "${YELLOW}Checking virtual environment...${NC}"
if [ -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${GREEN}✓ Virtual environment found${NC}"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    exit 1
fi

# Step 2: Backup database
print_section "Step 2: Backing Up Database"

if [ "$HAS_DATABASE" = true ]; then
    echo -e "${YELLOW}Creating backup directory...${NC}"
    mkdir -p "$BACKUP_DIR"
    chown $RUN_USER:$RUN_USER "$BACKUP_DIR"
    check_success "Backup directory created"
    
    BACKUP_FILE="$BACKUP_DIR/db.sqlite3.backup_${TIMESTAMP}"
    echo -e "${YELLOW}Backing up database to: $(basename $BACKUP_FILE)${NC}"
    cp "$PROJECT_DIR/db.sqlite3" "$BACKUP_FILE"
    check_success "Database backed up"
    
    echo -e "${GREEN}✓ Backup location: $BACKUP_FILE${NC}"
    
    # Keep only last 5 backups
    echo -e "${YELLOW}Cleaning old backups (keeping last 5)...${NC}"
    cd "$BACKUP_DIR"
    ls -t db.sqlite3.backup_* 2>/dev/null | tail -n +6 | xargs -r rm
    BACKUP_COUNT=$(ls -1 db.sqlite3.backup_* 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ Backups retained: $BACKUP_COUNT${NC}"
else
    echo -e "${YELLOW}⚠ No database to backup${NC}"
fi

# Step 3: Stop service
print_section "Step 3: Stopping Service"

if [ "$SERVICE_WAS_RUNNING" = true ]; then
    echo -e "${YELLOW}Stopping $SERVICE_NAME...${NC}"
    systemctl stop $SERVICE_NAME
    check_success "Service stopped"
else
    echo -e "${YELLOW}⚠ Service was not running, skipping stop${NC}"
fi

# Step 4: Update code
print_section "Step 4: Updating Code from GitHub"

cd "$PROJECT_DIR"

echo -e "${YELLOW}Fetching latest changes...${NC}"
sudo -u $RUN_USER git fetch origin
check_success "Fetched from GitHub"

echo -e "${YELLOW}Checking for updates...${NC}"
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    echo -e "${GREEN}✓ Already up to date (no changes)${NC}"
    NO_UPDATES=true
else
    echo -e "${YELLOW}Updates found, pulling changes...${NC}"
    sudo -u $RUN_USER git pull origin main
    check_success "Code updated"
    NO_UPDATES=false
    
    # Show what changed
    echo -e "${CYAN}Recent changes:${NC}"
    git log --oneline -5 --decorate
fi

# Step 5: Update dependencies
print_section "Step 5: Updating Dependencies"

echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate
check_success "Virtual environment activated"

echo -e "${YELLOW}Upgrading pip...${NC}"
.venv/bin/pip install --upgrade pip -q
check_success "Pip upgraded"

echo -e "${YELLOW}Installing/updating dependencies...${NC}"
.venv/bin/pip install -r requirements.txt -q
check_success "Dependencies updated"

# Step 6: Run migrations
print_section "Step 6: Running Database Migrations"

echo -e "${YELLOW}Checking for pending migrations...${NC}"
PENDING_MIGRATIONS=$(.venv/bin/python manage.py showmigrations --settings=core.settings_production | grep '\[ \]' | wc -l)

if [ "$PENDING_MIGRATIONS" -gt 0 ]; then
    echo -e "${YELLOW}Found $PENDING_MIGRATIONS pending migration(s)${NC}"
    echo -e "${YELLOW}Running migrations (this preserves your data)...${NC}"
    .venv/bin/python manage.py migrate --settings=core.settings_production
    check_success "Migrations completed"
else
    echo -e "${GREEN}✓ No pending migrations${NC}"
fi

# Step 7: Collect static files
print_section "Step 7: Collecting Static Files"

echo -e "${YELLOW}Collecting static files...${NC}"
.venv/bin/python manage.py collectstatic --noinput --settings=core.settings_production > /dev/null 2>&1
check_success "Static files collected"

# Step 8: Fix permissions
print_section "Step 8: Fixing Permissions"

echo -e "${YELLOW}Setting file permissions...${NC}"
chown -R $RUN_USER:$RUN_USER "$PROJECT_DIR"
check_success "Permissions set"

# Step 9: Restart service
print_section "Step 9: Restarting Service"

echo -e "${YELLOW}Starting $SERVICE_NAME...${NC}"
systemctl start $SERVICE_NAME
sleep 2
check_success "Service started"

echo -e "${YELLOW}Checking service status...${NC}"
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo -e "${YELLOW}Checking logs...${NC}"
    journalctl -u $SERVICE_NAME -n 20 --no-pager
    
    # Offer to restore backup
    if [ "$HAS_DATABASE" = true ] && [ -f "$BACKUP_FILE" ]; then
        echo ""
        echo -e "${YELLOW}Would you like to restore the backup? (y/n)${NC}"
        read -p "> " RESTORE
        if [[ "$RESTORE" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Restoring backup...${NC}"
            cp "$BACKUP_FILE" "$PROJECT_DIR/db.sqlite3"
            echo -e "${GREEN}✓ Backup restored${NC}"
            echo -e "${YELLOW}Restarting service...${NC}"
            systemctl restart $SERVICE_NAME
        fi
    fi
    exit 1
fi

# Step 10: Verify deployment
print_section "Step 10: Verifying Deployment"

echo -e "${YELLOW}Checking service health...${NC}"
sleep 2

# Check if service is still running
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${RED}✗ Service is not running${NC}"
    exit 1
fi

# Get server details
SERVER_IP=$(hostname -I | awk '{print $1}')
DOMAIN=$(grep "armguard" /etc/hosts 2>/dev/null | grep -v "^#" | awk '{print $2}' | head -1)

# Step 11: Summary
print_section "Update Summary"

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}║              ✓ Update Completed Successfully!              ║${NC}"
echo -e "${GREEN}║                                                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$NO_UPDATES" = true ]; then
    echo -e "${CYAN}Status: ${GREEN}Already up to date (no changes applied)${NC}"
else
    echo -e "${CYAN}Status: ${GREEN}Successfully updated to latest version${NC}"
fi

echo ""
echo -e "${CYAN}Application URLs:${NC}"
echo -e "  • Local:          ${YELLOW}http://localhost:8000${NC}"
echo -e "  • Network:        ${YELLOW}http://${SERVER_IP}:8000${NC}"
if [ ! -z "$DOMAIN" ]; then
    echo -e "  • Custom Domain:  ${YELLOW}http://${DOMAIN}:8000${NC}"
fi

echo ""
echo -e "${CYAN}Service Status:${NC}"
systemctl status $SERVICE_NAME --no-pager -l | grep -E "Active:|Main PID:|Memory:|CPU:" || true

echo ""
echo -e "${CYAN}Database:${NC}"
if [ "$HAS_DATABASE" = true ]; then
    NEW_SIZE=$(du -h "$PROJECT_DIR/db.sqlite3" | cut -f1)
    echo -e "  • Status:         ${GREEN}✓ Preserved${NC}"
    echo -e "  • Size:           ${YELLOW}${NEW_SIZE}${NC}"
    echo -e "  • Backup:         ${YELLOW}$(basename $BACKUP_FILE)${NC}"
    echo -e "  • Backup Location: ${YELLOW}${BACKUP_DIR}${NC}"
fi

echo ""
echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  • View logs:      ${YELLOW}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo -e "  • Restart:        ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
echo -e "  • Status:         ${YELLOW}sudo systemctl status $SERVICE_NAME${NC}"
echo -e "  • List backups:   ${YELLOW}ls -lh $BACKUP_DIR${NC}"

if [ "$HAS_DATABASE" = true ] && [ -f "$BACKUP_FILE" ]; then
    echo ""
    echo -e "${CYAN}Restore Backup (if needed):${NC}"
    echo -e "  ${YELLOW}sudo cp $BACKUP_FILE $PROJECT_DIR/db.sqlite3${NC}"
    echo -e "  ${YELLOW}sudo systemctl restart $SERVICE_NAME${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Update completed at: $(date)${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""

exit 0
