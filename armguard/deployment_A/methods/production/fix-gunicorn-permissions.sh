#!/bin/bash

################################################################################
# Gunicorn Permission Fix Script for ArmGuard
# 
# This script fixes the "Permission denied" error when changing to working directory
# Root cause: www-data user cannot access /var/www/armguard
# 
# Usage: sudo bash fix-gunicorn-permissions.sh
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="armguard"
DEFAULT_PROJECT_DIR="/var/www/armguard"
SOURCE_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard"
SERVICE_NAME="gunicorn-armguard"
RUN_USER="www-data"
RUN_GROUP="www-data"

# Print banner
clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║       ${GREEN}Gunicorn Permission Fix for ArmGuard${CYAN}                    ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Step 1: Analyze the current situation
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Analyzing Current Setup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Checking directories...${NC}"

# Check if /var/www exists
if [ ! -d "/var/www" ]; then
    echo -e "${RED}✗ /var/www does not exist${NC}"
    mkdir -p /var/www
    echo -e "${GREEN}✓ Created /var/www${NC}"
else
    echo -e "${GREEN}✓ /var/www exists${NC}"
fi

# Check permissions of /var/www
VAR_WWW_PERMS=$(stat -c "%a" /var/www)
VAR_WWW_OWNER=$(stat -c "%U:%G" /var/www)
echo "  Permissions: ${VAR_WWW_PERMS}"
echo "  Owner: ${VAR_WWW_OWNER}"

# Check if project directory exists
if [ ! -d "$DEFAULT_PROJECT_DIR" ]; then
    echo -e "${RED}✗ ${DEFAULT_PROJECT_DIR} does not exist${NC}"
    PROJECT_EXISTS=false
else
    echo -e "${GREEN}✓ ${DEFAULT_PROJECT_DIR} exists${NC}"
    PROJECT_PERMS=$(stat -c "%a" $DEFAULT_PROJECT_DIR)
    PROJECT_OWNER=$(stat -c "%U:%G" $DEFAULT_PROJECT_DIR)
    echo "  Permissions: ${PROJECT_PERMS}"
    echo "  Owner: ${PROJECT_OWNER}"
    PROJECT_EXISTS=true
fi

# Check www-data user
if id "$RUN_USER" >/dev/null 2>&1; then
    echo -e "${GREEN}✓ User ${RUN_USER} exists${NC}"
else
    echo -e "${RED}✗ User ${RUN_USER} does not exist${NC}"
    exit 1
fi

# Check service status
if systemctl list-unit-files | grep -q "$SERVICE_NAME.service"; then
    echo -e "${GREEN}✓ Service ${SERVICE_NAME} is installed${NC}"
    SERVICE_STATUS=$(systemctl is-active $SERVICE_NAME || echo "inactive")
    echo "  Status: ${SERVICE_STATUS}"
else
    echo -e "${RED}✗ Service ${SERVICE_NAME} not found${NC}"
    exit 1
fi

echo ""

# Step 2: Determine action needed
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Determining Required Action${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ "$PROJECT_EXISTS" = false ]; then
    echo -e "${YELLOW}Project directory does not exist at ${DEFAULT_PROJECT_DIR}${NC}"
    echo ""
    echo "Options:"
    echo "  1) Copy from ${SOURCE_DIR} (if it exists)"
    echo "  2) Specify another source directory"
    echo "  3) Exit and manually set up the directory"
    echo ""
    read -p "Select option [1-3]: " OPTION
    
    case $OPTION in
        1)
            if [ ! -d "$SOURCE_DIR" ]; then
                echo -e "${RED}ERROR: Source directory ${SOURCE_DIR} not found${NC}"
                exit 1
            fi
            
            echo -e "${YELLOW}Copying project from ${SOURCE_DIR} to ${DEFAULT_PROJECT_DIR}...${NC}"
            mkdir -p $DEFAULT_PROJECT_DIR
            
            # Copy all files except certain directories
            rsync -av --exclude='.git' \
                      --exclude='*.pyc' \
                      --exclude='__pycache__' \
                      --exclude='*.sqlite3' \
                      --exclude='.venv' \
                      --exclude='venv' \
                      --exclude='node_modules' \
                      --exclude='staticfiles' \
                      --exclude='media' \
                      "$SOURCE_DIR/" "$DEFAULT_PROJECT_DIR/"
            
            echo -e "${GREEN}✓ Project copied${NC}"
            PROJECT_EXISTS=true
            ;;
        2)
            read -p "Enter source directory path: " CUSTOM_SOURCE
            if [ ! -d "$CUSTOM_SOURCE" ]; then
                echo -e "${RED}ERROR: Directory ${CUSTOM_SOURCE} not found${NC}"
                exit 1
            fi
            
            echo -e "${YELLOW}Copying project from ${CUSTOM_SOURCE} to ${DEFAULT_PROJECT_DIR}...${NC}"
            mkdir -p $DEFAULT_PROJECT_DIR
            
            rsync -av --exclude='.git' \
                      --exclude='*.pyc' \
                      --exclude='__pycache__' \
                      --exclude='*.sqlite3' \
                      --exclude='.venv' \
                      --exclude='venv' \
                      --exclude='node_modules' \
                      --exclude='staticfiles' \
                      --exclude='media' \
                      "$CUSTOM_SOURCE/" "$DEFAULT_PROJECT_DIR/"
            
            echo -e "${GREEN}✓ Project copied${NC}"
            PROJECT_EXISTS=true
            ;;
        3)
            echo -e "${YELLOW}Please manually set up ${DEFAULT_PROJECT_DIR} and run this script again${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            exit 1
            ;;
    esac
fi

# Step 3: Fix permissions
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Fixing Permissions${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Stop service first
echo -e "${YELLOW}Stopping ${SERVICE_NAME} service...${NC}"
systemctl stop $SERVICE_NAME 2>/dev/null || true

# Fix /var/www permissions (parent directory must be accessible)
echo -e "${YELLOW}Setting permissions on /var/www...${NC}"
chmod 755 /var/www
chown root:root /var/www
echo -e "${GREEN}✓ /var/www permissions set (755, root:root)${NC}"

# Fix project directory ownership and permissions
echo -e "${YELLOW}Setting ownership on ${DEFAULT_PROJECT_DIR}...${NC}"
chown -R ${RUN_USER}:${RUN_GROUP} "$DEFAULT_PROJECT_DIR"
echo -e "${GREEN}✓ Ownership set to ${RUN_USER}:${RUN_GROUP}${NC}"

# Set proper directory permissions (755 = rwxr-xr-x)
echo -e "${YELLOW}Setting directory permissions...${NC}"
find "$DEFAULT_PROJECT_DIR" -type d -exec chmod 755 {} \;
echo -e "${GREEN}✓ Directory permissions set to 755${NC}"

# Set proper file permissions (644 = rw-r--r--)
echo -e "${YELLOW}Setting file permissions...${NC}"
find "$DEFAULT_PROJECT_DIR" -type f -exec chmod 644 {} \;
echo -e "${GREEN}✓ File permissions set to 644${NC}"

# Make scripts executable
echo -e "${YELLOW}Making scripts executable...${NC}"
if [ -d "$DEFAULT_PROJECT_DIR/.venv/bin" ]; then
    chmod +x "$DEFAULT_PROJECT_DIR/.venv/bin/"* 2>/dev/null || true
    echo -e "${GREEN}✓ Virtual environment scripts are executable${NC}"
fi

# Secure sensitive files
echo -e "${YELLOW}Securing sensitive files...${NC}"
if [ -f "$DEFAULT_PROJECT_DIR/.env" ]; then
    chmod 600 "$DEFAULT_PROJECT_DIR/.env"
    chown ${RUN_USER}:${RUN_GROUP} "$DEFAULT_PROJECT_DIR/.env"
    echo -e "${GREEN}✓ .env secured (600)${NC}"
fi

if [ -f "$DEFAULT_PROJECT_DIR/db.sqlite3" ]; then
    chmod 664 "$DEFAULT_PROJECT_DIR/db.sqlite3"
    chown ${RUN_USER}:${RUN_GROUP} "$DEFAULT_PROJECT_DIR/db.sqlite3"
    echo -e "${GREEN}✓ SQLite database permissions set (664)${NC}"
fi

# Create and fix log directories
echo -e "${YELLOW}Setting up log directories...${NC}"
mkdir -p /var/log/armguard
mkdir -p "$DEFAULT_PROJECT_DIR/logs"
chown -R ${RUN_USER}:${RUN_GROUP} /var/log/armguard
chown -R ${RUN_USER}:${RUN_GROUP} "$DEFAULT_PROJECT_DIR/logs"
chmod 755 /var/log/armguard
chmod 755 "$DEFAULT_PROJECT_DIR/logs"
echo -e "${GREEN}✓ Log directories configured${NC}"

# Ensure socket directory is accessible
echo -e "${YELLOW}Configuring socket directory...${NC}"
mkdir -p /run
chmod 755 /run
echo -e "${GREEN}✓ Socket directory accessible${NC}"

# Step 4: Verify systemd service configuration
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Verifying Service Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
if [ -f "$SERVICE_FILE" ]; then
    echo -e "${YELLOW}Checking ${SERVICE_FILE}...${NC}"
    
    # Check for ProtectSystem=strict which can cause issues
    if grep -q "ProtectSystem=strict" "$SERVICE_FILE"; then
        echo -e "${YELLOW}⚠ Found ProtectSystem=strict - this may cause issues${NC}"
        echo -e "${YELLOW}  Updating to ProtectSystem=full...${NC}"
        
        # Backup service file
        cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        
        # Update ProtectSystem
        sed -i 's/ProtectSystem=strict/ProtectSystem=full/' "$SERVICE_FILE"
        
        # Remove or update ReadWritePaths if it exists
        if grep -q "ReadWritePaths=" "$SERVICE_FILE"; then
            sed -i '/^ReadWritePaths=/d' "$SERVICE_FILE"
        fi
        
        echo -e "${GREEN}✓ Service file updated${NC}"
        systemctl daemon-reload
    else
        echo -e "${GREEN}✓ Service configuration looks good${NC}"
    fi
    
    # Display relevant parts of service file
    echo ""
    echo -e "${CYAN}Service Configuration:${NC}"
    grep -E "^(User|Group|WorkingDirectory|Environment=)" "$SERVICE_FILE" | sed 's/^/  /'
    echo ""
else
    echo -e "${RED}ERROR: Service file not found: ${SERVICE_FILE}${NC}"
    exit 1
fi

# Step 5: Test permissions
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5: Testing Permissions${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Testing directory access as ${RUN_USER}...${NC}"
if sudo -u $RUN_USER test -r "$DEFAULT_PROJECT_DIR" && \
   sudo -u $RUN_USER test -x "$DEFAULT_PROJECT_DIR"; then
    echo -e "${GREEN}✓ ${RUN_USER} can access ${DEFAULT_PROJECT_DIR}${NC}"
else
    echo -e "${RED}✗ ${RUN_USER} cannot access ${DEFAULT_PROJECT_DIR}${NC}"
    echo -e "${RED}  This will cause the service to fail${NC}"
    exit 1
fi

echo -e "${YELLOW}Testing manage.py access...${NC}"
if sudo -u $RUN_USER test -r "$DEFAULT_PROJECT_DIR/manage.py"; then
    echo -e "${GREEN}✓ ${RUN_USER} can read manage.py${NC}"
else
    echo -e "${RED}✗ ${RUN_USER} cannot read manage.py${NC}"
    exit 1
fi

if [ -f "$DEFAULT_PROJECT_DIR/.venv/bin/gunicorn" ]; then
    echo -e "${YELLOW}Testing gunicorn executable access...${NC}"
    if sudo -u $RUN_USER test -x "$DEFAULT_PROJECT_DIR/.venv/bin/gunicorn"; then
        echo -e "${GREEN}✓ ${RUN_USER} can execute gunicorn${NC}"
    else
        echo -e "${RED}✗ ${RUN_USER} cannot execute gunicorn${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Gunicorn not found in virtual environment${NC}"
    echo -e "${YELLOW}  Installing gunicorn...${NC}"
    cd "$DEFAULT_PROJECT_DIR"
    sudo -u $RUN_USER .venv/bin/pip install gunicorn
    echo -e "${GREEN}✓ Gunicorn installed${NC}"
fi

# Step 6: Restart service
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6: Starting Service${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

echo -e "${YELLOW}Starting ${SERVICE_NAME}...${NC}"
systemctl start $SERVICE_NAME

# Wait for service to start
sleep 3

# Check service status
if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service started successfully!${NC}"
    
    # Enable on boot
    systemctl enable $SERVICE_NAME 2>/dev/null || true
    echo -e "${GREEN}✓ Service enabled for automatic start${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo ""
    echo -e "${YELLOW}Recent journal entries:${NC}"
    journalctl -u $SERVICE_NAME -n 30 --no-pager
    exit 1
fi

# Check socket file
SOCKET_FILE="/run/${SERVICE_NAME}.sock"
sleep 1
if [ -S "$SOCKET_FILE" ]; then
    echo -e "${GREEN}✓ Socket file created: ${SOCKET_FILE}${NC}"
    SOCKET_OWNER=$(stat -c "%U:%G" "$SOCKET_FILE")
    echo "  Owner: ${SOCKET_OWNER}"
else
    echo -e "${YELLOW}⚠ Socket file not found (this may be normal if using systemd socket activation)${NC}"
fi

# Final summary
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Permission Fix Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Service Status:${NC}"
systemctl status $SERVICE_NAME --no-pager -l | head -n 20
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Check status:   sudo systemctl status ${SERVICE_NAME}"
echo "  View logs:      sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Restart:        sudo systemctl restart ${SERVICE_NAME}"
echo "  Stop:           sudo systemctl stop ${SERVICE_NAME}"
echo "  Access log:     sudo tail -f /var/log/armguard/access.log"
echo "  Error log:      sudo tail -f /var/log/armguard/error.log"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "  1. Configure Nginx to proxy to ${SOCKET_FILE}"
echo "  2. Set up SSL certificates"
echo "  3. Test the application access"
echo ""
