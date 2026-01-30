#!/bin/bash

################################################################################
# ArmGuard - LAN Network Setup (mkcert SSL)
# Configure secure internal network for Armory PC communication
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOYMENT_DIR="$(dirname "$SCRIPT_DIR")"

# Source configuration
if [ -f "$DEPLOYMENT_DIR/config.sh" ]; then
    source "$DEPLOYMENT_DIR/config.sh"
    echo -e "${GREEN}✓ Configuration loaded from config.sh${NC}"
else
    echo -e "${YELLOW}⚠ config.sh not found, using defaults${NC}"
    # Default configuration
    export LAN_INTERFACE="${LAN_INTERFACE:-eth1}"
    export SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.10.1}"
    export ARMORY_PC_IP="${ARMORY_PC_IP:-192.168.10.2}"
    export LAN_SUBNET="${LAN_SUBNET:-192.168.10.0/24}"
    export PROJECT_DIR="${PROJECT_DIR:-/var/www/armguard}"
fi

LAN_CERT_DIR="/etc/ssl/armguard/lan"
NGINX_CONF="/etc/nginx/sites-available/armguard-lan"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         ArmGuard LAN Network Setup (mkcert)                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Verify Network Interface${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check if LAN interface exists
if ! ip link show $LAN_INTERFACE &> /dev/null; then
    echo -e "${RED}ERROR: LAN interface $LAN_INTERFACE not found${NC}"
    echo -e "${YELLOW}Available interfaces:${NC}"
    ip link show | grep -E '^[0-9]+:' | cut -d: -f2
    exit 1
fi

echo -e "${GREEN}✓ LAN interface $LAN_INTERFACE found${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Configure Static IP${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Configuring static IP: $SERVER_LAN_IP${NC}"

# Create netplan configuration
NETPLAN_FILE="/etc/netplan/02-lan-armguard.yaml"

cat > "$NETPLAN_FILE" << EOF
network:
  version: 2
  ethernets:
    $LAN_INTERFACE:
      dhcp4: no
      addresses:
        - ${SERVER_LAN_IP}/24
      # No gateway (isolated network)
EOF

echo -e "${YELLOW}Applying network configuration...${NC}"
netplan apply

# Verify IP
if ip addr show $LAN_INTERFACE | grep -q "$SERVER_LAN_IP"; then
    echo -e "${GREEN}✓ Static IP $SERVER_LAN_IP configured${NC}"
else
    echo -e "${RED}✗ Failed to configure static IP${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Install mkcert${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if ! command -v mkcert &> /dev/null; then
    echo -e "${YELLOW}Installing mkcert...${NC}"
    
    # Detect architecture
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)
            MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-amd64"
            ;;
        aarch64|arm64)
            MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-arm64"
            ;;
        armv7l)
            MKCERT_URL="https://github.com/FiloSottile/mkcert/releases/latest/download/mkcert-v1.4.4-linux-arm"
            ;;
        *)
            echo -e "${RED}Unsupported architecture: $ARCH${NC}"
            exit 1
            ;;
    esac
    
    wget -q "$MKCERT_URL" -O /usr/local/bin/mkcert
    chmod +x /usr/local/bin/mkcert
    
    # Install CA
    apt-get install -y libnss3-tools
    mkcert -install
    
    echo -e "${GREEN}✓ mkcert installed and CA created${NC}"
else
    echo -e "${GREEN}✓ mkcert already installed${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Generate LAN SSL Certificates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Creating certificate directory...${NC}"
mkdir -p "$LAN_CERT_DIR"

echo -e "${YELLOW}Generating certificates for LAN...${NC}"
cd "$LAN_CERT_DIR"

mkcert -key-file armguard-lan-key.pem \
       -cert-file armguard-lan-cert.pem \
       "$SERVER_LAN_IP" \
       "192.168.10.1" \
       "armguard.local" \
       "localhost"

# Set proper permissions
chmod 644 armguard-lan-cert.pem
chmod 600 armguard-lan-key.pem

echo -e "${GREEN}✓ LAN SSL certificates generated${NC}"

# Display CA location for Armory PC installation
echo ""
echo -e "${CYAN}mkcert Root CA Location:${NC}"
CAROOT=$(mkcert -CAROOT)
echo -e "${YELLOW}$CAROOT${NC}"
echo ""
echo -e "${YELLOW}⚠ IMPORTANT: Copy rootCA.pem to Armory PC and install it!${NC}"
echo -e "${CYAN}Copy command for Armory PC:${NC}"
echo -e "${YELLOW}scp $CAROOT/rootCA.pem user@$ARMORY_PC_IP:~/armguard-ca.pem${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5: Install Nginx (if needed)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if ! command -v nginx &> /dev/null; then
    echo -e "${YELLOW}Installing Nginx...${NC}"
    apt-get update -qq
    apt-get install -y nginx
    echo -e "${GREEN}✓ Nginx installed${NC}"
else
    echo -e "${GREEN}✓ Nginx already installed${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6: Configure Nginx for LAN${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Copying LAN Nginx configuration...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/nginx-lan.conf" ]; then
    cp "$SCRIPT_DIR/nginx-lan.conf" "$NGINX_CONF"
    
    # Update IPs in config
    sed -i "s/192\.168\.10\.1/$SERVER_LAN_IP/g" "$NGINX_CONF"
    sed -i "s/192\.168\.10\.2/$ARMORY_PC_IP/g" "$NGINX_CONF"
    
    # Enable site
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/armguard-lan
    
    echo -e "${GREEN}✓ Nginx LAN configuration installed${NC}"
else
    echo -e "${RED}ERROR: nginx-lan.conf not found${NC}"
    exit 1
fi

# Test Nginx configuration
echo -e "${YELLOW}Testing Nginx configuration...${NC}"
if nginx -t; then
    echo -e "${GREEN}✓ Nginx configuration valid${NC}"
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi

# Reload Nginx
echo -e "${YELLOW}Reloading Nginx...${NC}"
systemctl reload nginx

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║            LAN Network Setup Complete!                    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}LAN Network Configuration:${NC}"
echo ""
echo -e "${GREEN}✓ Server Configuration:${NC}"
echo "  Interface:      $LAN_INTERFACE"
echo "  IP Address:     $SERVER_LAN_IP"
echo "  Subnet:         $LAN_SUBNET"
echo "  HTTPS Port:     8443"
echo "  Certificate:    $LAN_CERT_DIR/armguard-lan-cert.pem"
echo ""
echo -e "${GREEN}✓ Armory PC Configuration Needed:${NC}"
echo "  IP Address:     $ARMORY_PC_IP (static)"
echo "  Subnet Mask:    255.255.255.0"
echo "  Gateway:        (none - isolated network)"
echo "  DNS:            (none needed for direct IP access)"
echo ""
echo -e "${YELLOW}⚠ Next Steps:${NC}"
echo ""
echo -e "${CYAN}1. Configure Armory PC:${NC}"
echo "   • Set static IP: $ARMORY_PC_IP"
echo "   • Copy and install mkcert root CA:"
echo -e "     ${YELLOW}scp $CAROOT/rootCA.pem user@$ARMORY_PC_IP:~/armguard-ca.pem${NC}"
echo "   • On Armory PC (Windows): Double-click armguard-ca.pem → Install to Trusted Root"
echo "   • On Armory PC (Linux): sudo cp armguard-ca.pem /usr/local/share/ca-certificates/ && sudo update-ca-certificates"
echo ""
echo -e "${CYAN}2. Test Connection:${NC}"
echo "   • From Armory PC: https://$SERVER_LAN_IP:8443"
echo "   • Should show valid SSL certificate"
echo ""
echo -e "${CYAN}3. Configure Firewall:${NC}"
echo "   • Run: sudo bash network_setup/configure-firewall.sh"
echo ""
