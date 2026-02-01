#!/bin/bash

# Gunicorn Service Deployment Script for ArmGuard
# This script automates the installation and configuration of Gunicorn systemd service

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration variables
PROJECT_NAME="armguard"
PROJECT_DIR="/var/www/armguard"
SERVICE_NAME="gunicorn-armguard"
SERVICE_FILE="${SERVICE_NAME}.service"
VENV_DIR="${PROJECT_DIR}/.venv"
LOG_DIR="/var/log/armguard"
RUN_USER="www-data"
RUN_GROUP="www-data"

# Calculate optimal worker count (2 × CPU + 1)
CPU_CORES=$(nproc)
WORKERS=$((2 * CPU_CORES + 1))

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}ArmGuard Gunicorn Service Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: Please run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project: ${PROJECT_NAME}"
echo "  Directory: ${PROJECT_DIR}"
echo "  Service: ${SERVICE_NAME}"
echo "  User: ${RUN_USER}"
echo "  Group: ${RUN_GROUP}"
echo "  Workers: ${WORKERS}"
echo ""

# Check if project directory exists
if [ ! -d "${PROJECT_DIR}" ]; then
    echo -e "${RED}ERROR: Project directory ${PROJECT_DIR} not found!${NC}"
    echo "Please deploy your Django app first."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "${VENV_DIR}" ]; then
    echo -e "${RED}ERROR: Virtual environment ${VENV_DIR} not found!${NC}"
    echo "Please create virtual environment first: python3 -m venv .venv"
    exit 1
fi

# Check if gunicorn is installed in venv
if [ ! -f "${VENV_DIR}/bin/gunicorn" ]; then
    echo -e "${YELLOW}Installing Gunicorn...${NC}"
    ${VENV_DIR}/bin/pip install gunicorn
fi

# Create log directory
echo -e "${YELLOW}Creating log directory...${NC}"
mkdir -p ${LOG_DIR}
chown ${RUN_USER}:${RUN_GROUP} ${LOG_DIR}
chmod 755 ${LOG_DIR}

# Create systemd service file
echo -e "${YELLOW}Creating systemd service file...${NC}"

cat > /etc/systemd/system/${SERVICE_FILE} <<EOF
[Unit]
Description=Gunicorn daemon for ArmGuard
Documentation=https://github.com/Stealth3535/armguard
After=network.target

[Service]
Type=exec
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${PROJECT_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=-${PROJECT_DIR}/.env

ExecStart=${VENV_DIR}/bin/gunicorn \\
          --workers ${WORKERS} \\
          --bind unix:/run/${SERVICE_NAME}.sock \\
          --timeout 60 \\
          --access-logfile ${LOG_DIR}/access.log \\
          --error-logfile ${LOG_DIR}/error.log \\
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

echo -e "${GREEN}✓ Service file created: /etc/systemd/system/${SERVICE_FILE}${NC}"

# Set proper permissions
echo -e "${YELLOW}Setting permissions...${NC}"
chown -R ${RUN_USER}:${RUN_GROUP} ${PROJECT_DIR}
chmod 600 ${PROJECT_DIR}/.env 2>/dev/null || echo -e "${YELLOW}  Warning: .env file not found${NC}"

if [ -f "${PROJECT_DIR}/db.sqlite3" ]; then
    chmod 664 ${PROJECT_DIR}/db.sqlite3
    chown ${RUN_USER}:${RUN_GROUP} ${PROJECT_DIR}/db.sqlite3
    echo -e "${GREEN}✓ SQLite database permissions set${NC}"
fi

# Reload systemd
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

# Start service
echo -e "${YELLOW}Starting Gunicorn service...${NC}"
systemctl start ${SERVICE_NAME}

# Check if service started successfully
sleep 2
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo -e "${GREEN}✓ Service started successfully${NC}"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs: sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi

# Enable service to start on boot
echo -e "${YELLOW}Enabling service to start on boot...${NC}"
systemctl enable ${SERVICE_NAME}
echo -e "${GREEN}✓ Service enabled${NC}"

# Check socket file
sleep 1
if [ -S "/run/${SERVICE_NAME}.sock" ]; then
    echo -e "${GREEN}✓ Socket file created: /run/${SERVICE_NAME}.sock${NC}"
else
    echo -e "${YELLOW}  Warning: Socket file not found (may be normal)${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Service Status:"
systemctl status ${SERVICE_NAME} --no-pager -l
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  View status:  sudo systemctl status ${SERVICE_NAME}"
echo "  Restart:      sudo systemctl restart ${SERVICE_NAME}"
echo "  Stop:         sudo systemctl stop ${SERVICE_NAME}"
echo "  View logs:    sudo journalctl -u ${SERVICE_NAME} -f"
echo "  Access logs:  sudo tail -f ${LOG_DIR}/access.log"
echo "  Error logs:   sudo tail -f ${LOG_DIR}/error.log"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Configure Nginx to proxy to /run/${SERVICE_NAME}.sock"
echo "  2. Set up SSL/HTTPS certificates"
echo "  3. Configure firewall (UFW)"
echo "  4. See: UBUNTU_MKCERT_SSL_SETUP.md"
echo ""
