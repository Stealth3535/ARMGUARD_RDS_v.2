#!/bin/bash
# ArmGuard RPi Deployment Path Fix Script
# This script fixes deployment paths and socket issues for RPi deployment

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🔧 Fixing ArmGuard RPi Deployment Paths and Socket Issues...${NC}"

# Step 1: Remove socket activation conflict
echo -e "${YELLOW}Step 1: Removing systemd socket unit conflict...${NC}"
if [ -f "/etc/systemd/system/armguard.socket" ]; then
    sudo systemctl stop armguard.socket || true
    sudo systemctl disable armguard.socket || true
    sudo rm -f /etc/systemd/system/armguard.socket
    echo -e "${GREEN}✓ Removed armguard.socket unit${NC}"
fi

# Step 2: Stop existing services
echo -e "${YELLOW}Step 2: Stopping existing services...${NC}"
sudo systemctl stop armguard.service || true
sudo pkill gunicorn || true
sudo rm -f /run/armguard.sock

# Step 3: Fix systemd service file to use correct paths
echo -e "${YELLOW}Step 3: Updating systemd service file...${NC}"

# Detect actual deployment location by checking for venv with gunicorn
if [ -f "/opt/armguard/venv/bin/gunicorn" ]; then
    PROJECT_DIR="/opt/armguard/armguard"
    VENV_DIR="/opt/armguard/venv"
    LOG_DIR="/var/log/armguard"
    RUN_USER="ubuntu"
    RUN_GROUP="ubuntu"
elif [ -f "/home/ubuntu/ARMGUARD_RDS/venv/bin/gunicorn" ]; then
    PROJECT_DIR="/home/ubuntu/ARMGUARD_RDS/armguard"
    VENV_DIR="/home/ubuntu/ARMGUARD_RDS/venv"
    LOG_DIR="/home/ubuntu/ARMGUARD_RDS/logs"
    RUN_USER="ubuntu"
    RUN_GROUP="ubuntu"
else
    echo -e "${RED}ERROR: Cannot find ArmGuard installation with gunicorn${NC}"
    echo "Checked:"
    echo "  - /opt/armguard/venv/bin/gunicorn"
    echo "  - /home/ubuntu/ARMGUARD_RDS/venv/bin/gunicorn"
    exit 1
fi

echo -e "${GREEN}✓ Detected project at: $PROJECT_DIR${NC}"

# Create log directory
sudo mkdir -p "$LOG_DIR"
sudo chown "$RUN_USER:$RUN_GROUP" "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"

# Create new service file WITHOUT socket activation
sudo tee /etc/systemd/system/armguard.service > /dev/null <<EOF
[Unit]
Description=ArmGuard A+ Performance Edition
After=network.target

[Service]
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings"

ExecStart=$VENV_DIR/bin/gunicorn \\
    --workers 3 \\
    --bind unix:/run/armguard.sock \\
    --timeout 60 \\
    --access-logfile $LOG_DIR/access.log \\
    --error-logfile $LOG_DIR/error.log \\
    --log-level info \\
    core.wsgi:application

Restart=always
RestartSec=3
PrivateTmp=true
NoNewPrivileges=true
KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Service file created${NC}"

# Step 4: Reload systemd
echo -e "${YELLOW}Step 4: Reloading systemd...${NC}"
sudo systemctl daemon-reload

# Step 5: Start service
echo -e "${YELLOW}Step 5: Starting ArmGuard service...${NC}"
sudo systemctl start armguard.service
sudo systemctl enable armguard.service

# Step 6: Check status
sleep 2
if sudo systemctl is-active --quiet armguard.service; then
    echo -e "${GREEN}✅ ArmGuard service started successfully!${NC}"
    echo ""
    sudo systemctl status armguard.service --no-pager
else
    echo -e "${RED}❌ Service failed to start. Check logs:${NC}"
    echo "sudo journalctl -xeu armguard.service -n 50"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Fix Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Status:   sudo systemctl status armguard.service"
echo "  Restart:  sudo systemctl restart armguard.service"
echo "  Logs:     sudo journalctl -u armguard.service -f"
echo "  Socket:   ls -l /run/armguard.sock"
