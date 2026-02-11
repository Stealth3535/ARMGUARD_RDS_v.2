#!/bin/bash

################################################################################
# Quick Fix: Use Cloned Repository Instead of /var/www/armguard
# 
# This script reconfigures the Gunicorn service to use the cloned repository
# directly without copying to /var/www/armguard
#
# Usage: sudo bash quick-fix-use-cloned-repo.sh
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
echo -e "${CYAN}║   ${GREEN}Quick Fix: Using Cloned Repository for Deployment${CYAN}        ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: Run as root (use sudo)${NC}"
    exit 1
fi

# Configuration
PROJECT_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard"
RUN_USER="rds"
RUN_GROUP="rds"
SERVICE_NAME="gunicorn-armguard"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${BLUE}Step 1: Verifying Project Directory${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}✗ Project directory not found: $PROJECT_DIR${NC}"
    exit 1
fi

if [ ! -f "$PROJECT_DIR/manage.py" ]; then
    echo -e "${RED}✗ manage.py not found in $PROJECT_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Project directory verified${NC}"

echo ""
echo -e "${BLUE}Step 2: Checking Virtual Environment${NC}"
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo -e "${YELLOW}⚠ Virtual environment not found, creating...${NC}"
    cd "$PROJECT_DIR"
    sudo -u $RUN_USER python3 -m venv .venv
    sudo -u $RUN_USER .venv/bin/pip install --upgrade pip -q
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

if [ ! -f "$PROJECT_DIR/.venv/bin/gunicorn" ]; then
    echo -e "${YELLOW}Installing gunicorn...${NC}"
    cd "$PROJECT_DIR"
    sudo -u $RUN_USER .venv/bin/pip install gunicorn -q
    echo -e "${GREEN}✓ Gunicorn installed${NC}"
fi

echo -e "${GREEN}✓ Virtual environment ready${NC}"

echo ""
echo -e "${BLUE}Step 3: Updating Systemd Service File${NC}"

# Stop service if running
systemctl stop $SERVICE_NAME 2>/dev/null || true

# Backup existing service file
if [ -f "$SERVICE_FILE" ]; then
    cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}  Backed up existing service file${NC}"
fi

# Calculate optimal workers
CPU_CORES=$(nproc)
WORKERS=$((2 * CPU_CORES + 1))

# Create new service file
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Gunicorn daemon for ArmGuard
Documentation=https://github.com/Stealth3535/armguard
After=network.target

[Service]
Type=exec
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${PROJECT_DIR}/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=-${PROJECT_DIR}/.env

ExecStart=${PROJECT_DIR}/.venv/bin/gunicorn \\
          --workers ${WORKERS} \\
          --bind unix:/run/gunicorn-armguard.sock \\
          --timeout 60 \\
          --max-requests 1000 \\
          --max-requests-jitter 50 \\
          --access-logfile /var/log/armguard/access.log \\
          --error-logfile /var/log/armguard/error.log \\
          --log-level info \\
          core.wsgi:application

ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=3

# Security settings (relaxed for home directory)
PrivateTmp=true
NoNewPrivileges=true

# Process management
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file updated${NC}"

echo ""
echo -e "${BLUE}Step 4: Setting Up Directories${NC}"

# Create log directory
mkdir -p /var/log/armguard
chown ${RUN_USER}:${RUN_GROUP} /var/log/armguard
chmod 755 /var/log/armguard
echo -e "${GREEN}✓ Log directory configured${NC}"

# Set project directory permissions
cd "$PROJECT_DIR"
chown -R ${RUN_USER}:${RUN_GROUP} "$PROJECT_DIR"

# Secure .env
if [ -f ".env" ]; then
    chmod 600 .env
    chown ${RUN_USER}:${RUN_GROUP} .env
    echo -e "${GREEN}✓ .env file secured${NC}"
fi

# Database permissions
if [ -f "db.sqlite3" ]; then
    chmod 664 db.sqlite3
    chown ${RUN_USER}:${RUN_GROUP} db.sqlite3
    echo -e "${GREEN}✓ Database permissions set${NC}"
fi

echo ""
echo -e "${BLUE}Step 5: Testing Configuration${NC}"

# Test directory access
echo -e "${YELLOW}Testing directory access as ${RUN_USER}...${NC}"
if sudo -u $RUN_USER test -x "$PROJECT_DIR" && \
   sudo -u $RUN_USER test -r "$PROJECT_DIR/manage.py"; then
    echo -e "${GREEN}✓ Directory access OK${NC}"
else
    echo -e "${RED}✗ Access test failed${NC}"
    exit 1
fi

# Test gunicorn access
if sudo -u $RUN_USER test -x "$PROJECT_DIR/.venv/bin/gunicorn"; then
    echo -e "${GREEN}✓ Gunicorn executable OK${NC}"
else
    echo -e "${RED}✗ Gunicorn not accessible${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Step 6: Starting Service${NC}"

# Reload systemd
systemctl daemon-reload

# Start service
systemctl start $SERVICE_NAME

# Wait and check
sleep 3

if systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✓ Service started successfully!${NC}"
    
    # Enable on boot
    systemctl enable $SERVICE_NAME
    echo -e "${GREEN}✓ Service enabled for boot${NC}"
    
    # Check socket
    if [ -S "/run/gunicorn-armguard.sock" ]; then
        echo -e "${GREEN}✓ Socket file created${NC}"
    fi
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo ""
    echo -e "${YELLOW}Journal output:${NC}"
    journalctl -u $SERVICE_NAME -n 50 --no-pager
    exit 1
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Configuration Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Service Information:${NC}"
echo "  Project Directory:  $PROJECT_DIR"
echo "  Run User:           $RUN_USER:$RUN_GROUP"
echo "  Virtual Environment: $PROJECT_DIR/.venv"
echo "  Socket:             /run/gunicorn-armguard.sock"
echo ""
systemctl status $SERVICE_NAME --no-pager -l | head -20
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Status:   sudo systemctl status $SERVICE_NAME"
echo "  Logs:     sudo journalctl -u $SERVICE_NAME -f"
echo "  Restart:  sudo systemctl restart $SERVICE_NAME"
echo "  Stop:     sudo systemctl stop $SERVICE_NAME"
echo ""
echo -e "${GREEN}✓ You can now update code with 'git pull' and restart the service!${NC}"
echo ""
