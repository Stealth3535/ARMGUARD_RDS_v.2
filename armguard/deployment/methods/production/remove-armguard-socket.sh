#!/bin/bash
# ArmGuard Deployment: Remove systemd socket unit and ensure clean Gunicorn service deployment
# Usage: sudo bash remove-armguard-socket.sh

set -e

SERVICE_NAME="armguard"
SOCKET_UNIT="/etc/systemd/system/${SERVICE_NAME}.socket"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking for old/conflicting systemd socket unit...${NC}"
if [ -f "$SOCKET_UNIT" ]; then
    echo -e "${YELLOW}Stopping and disabling ${SERVICE_NAME}.socket...${NC}"
    systemctl stop ${SERVICE_NAME}.socket || true
    systemctl disable ${SERVICE_NAME}.socket || true
    rm -f "$SOCKET_UNIT"
    echo -e "${GREEN}✓ Removed ${SERVICE_NAME}.socket unit${NC}"
else
    echo -e "${GREEN}No ${SERVICE_NAME}.socket unit found. Proceeding...${NC}"
fi

# Remove any stale socket file
SOCKET_FILE="/run/${SERVICE_NAME}.sock"
echo -e "${YELLOW}Removing stale socket file if present...${NC}"
rm -f "$SOCKET_FILE"

# Reload systemd to apply changes
echo -e "${YELLOW}Reloading systemd daemon...${NC}"
systemctl daemon-reload

echo -e "${GREEN}Systemd socket cleanup complete. You can now run the Gunicorn install script safely.${NC}"
