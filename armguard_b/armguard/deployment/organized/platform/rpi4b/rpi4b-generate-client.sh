#!/bin/bash

################################################################################
# ArmGuard VPN Client Configuration Generator for Raspberry Pi 4B
# 
# Generates WireGuard client configurations with role-based access controls
# for secure remote access to ArmGuard military inventory system
#
# Usage: ./rpi4b-generate-client.sh <client-name> <role>
# Roles: commander, armorer, emergency, personnel
################################################################################

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
VPN_NET="10.0.0.0/24"
VPN_SERVER_IP="10.0.0.1"
VPN_PORT="51820"
SERVER_PUBLIC_KEY_FILE="/etc/wireguard/server_public.key"
CLIENT_CONFIG_DIR="/etc/wireguard/clients"
WG_INTERFACE="wg0"

# Get server's public key
if [[ ! -f "$SERVER_PUBLIC_KEY_FILE" ]]; then
    echo -e "${RED}❌ Server public key not found. Run VPN server setup first.${NC}"
    exit 1
fi

SERVER_PUBLIC_KEY=$(cat "$SERVER_PUBLIC_KEY_FILE")

# Create clients directory
mkdir -p "$CLIENT_CONFIG_DIR"

# Function to show usage
show_usage() {
    echo "Usage: $0 <client-name> <role>"
    echo ""
    echo "Roles and permissions:"
    echo "  commander  - Full inventory viewing, reports, user management"
    echo "  armorer    - Equipment inventory viewing, maintenance reports"
    echo "  emergency  - Critical equipment access only"
    echo "  personnel  - Personal transaction history only"
    echo ""
    echo "Example: $0 john-smith commander"
}

# Validate input
if [[ $# -ne 2 ]]; then
    show_usage
    exit 1
fi

CLIENT_NAME="$1"
ROLE="$2"

# Validate role
case "$ROLE" in
    commander|armorer|emergency|personnel)
        ;;
    *)
        echo -e "${RED}❌ Invalid role: $ROLE${NC}"
        show_usage
        exit 1
        ;;
esac

echo -e "${BLUE}🔐 Generating VPN client configuration${NC}"
echo "Client: $CLIENT_NAME"
echo "Role: $ROLE"
echo ""

# Generate client keys
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)

# Assign IP based on role and sequence
# commander: 10.0.0.10-19
# armorer: 10.0.0.20-29  
# emergency: 10.0.0.30-39
# personnel: 10.0.0.40-99

case "$ROLE" in
    commander)
        IP_RANGE="10.0.0.10"
        ;;
    armorer)
        IP_RANGE="10.0.0.20"
        ;;
    emergency)
        IP_RANGE="10.0.0.30"
        ;;
    personnel)
        IP_RANGE="10.0.0.40"
        ;;
esac

# Find next available IP in range
CLIENT_COUNT=$(ls -1 "$CLIENT_CONFIG_DIR"/*-${ROLE}-*.conf 2>/dev/null | wc -l || echo 0)
CLIENT_IP_SUFFIX=$(($(echo "$IP_RANGE" | cut -d. -f4) + CLIENT_COUNT))

if [[ $CLIENT_IP_SUFFIX -gt 254 ]]; then
    echo -e "${RED}❌ No available IPs for role $ROLE${NC}"
    exit 1
fi

CLIENT_IP="10.0.0.$CLIENT_IP_SUFFIX/32"

# Get server's external IP (for your local network)
SERVER_ENDPOINT=$(hostname -I | cut -d' ' -f1)

# Create client configuration file
CLIENT_CONFIG_FILE="$CLIENT_CONFIG_DIR/${CLIENT_NAME}-${ROLE}-$(date +%Y%m%d).conf"

cat > "$CLIENT_CONFIG_FILE" << EOF
# ArmGuard VPN Client Configuration
# Client: $CLIENT_NAME
# Role: $ROLE
# Generated: $(date)
# Server: Raspberry Pi 4B ArmGuard

[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $CLIENT_IP
DNS = 8.8.8.8, 8.8.4.4

# Role-specific routing
EOF

# Add role-specific allowed IPs
case "$ROLE" in
    commander)
        echo "# Commander: Full system access" >> "$CLIENT_CONFIG_FILE"
        echo "AllowedIPs = 10.0.0.0/24, 192.168.0.0/16" >> "$CLIENT_CONFIG_FILE"
        ;;
    armorer)
        echo "# Armorer: Inventory and equipment access" >> "$CLIENT_CONFIG_FILE"
        echo "AllowedIPs = 10.0.0.1/32, 192.168.0.0/16" >> "$CLIENT_CONFIG_FILE"
        ;;
    emergency)
        echo "# Emergency: Critical systems only" >> "$CLIENT_CONFIG_FILE"
        echo "AllowedIPs = 10.0.0.1/32" >> "$CLIENT_CONFIG_FILE"
        ;;
    personnel)
        echo "# Personnel: Status checking only" >> "$CLIENT_CONFIG_FILE"
        echo "AllowedIPs = 10.0.0.1/32" >> "$CLIENT_CONFIG_FILE"
        ;;
esac

cat >> "$CLIENT_CONFIG_FILE" << EOF

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = $SERVER_ENDPOINT:$VPN_PORT
AllowedIPs = 10.0.0.0/24, 192.168.0.0/16
PersistentKeepalive = 25
EOF

# Add client to server configuration
echo "" >> /etc/wireguard/wg0.conf
echo "# Client: $CLIENT_NAME ($ROLE)" >> /etc/wireguard/wg0.conf
echo "[Peer]" >> /etc/wireguard/wg0.conf
echo "PublicKey = $CLIENT_PUBLIC_KEY" >> /etc/wireguard/wg0.conf
echo "AllowedIPs = $CLIENT_IP" >> /etc/wireguard/wg0.conf
echo "" >> /etc/wireguard/wg0.conf

# Generate QR code for mobile devices
QR_CODE_FILE="$CLIENT_CONFIG_DIR/${CLIENT_NAME}-${ROLE}-$(date +%Y%m%d).png"
qrencode -t png -o "$QR_CODE_FILE" < "$CLIENT_CONFIG_FILE"

# Set proper permissions
chmod 600 "$CLIENT_CONFIG_FILE"
chmod 644 "$QR_CODE_FILE"

# Restart WireGuard to apply new peer
systemctl restart wg-quick@wg0

echo -e "${GREEN}✅ Client configuration generated successfully!${NC}"
echo ""
echo "📁 Files created:"
echo "  Config: $CLIENT_CONFIG_FILE"
echo "  QR Code: $QR_CODE_FILE"
echo ""
echo "🔧 Setup instructions:"
echo ""
echo "1. Copy the config file to your device:"
echo "   scp pi@your-rpi-ip:$CLIENT_CONFIG_FILE ."
echo ""
echo "2. Import into WireGuard client:"
echo "   - Desktop: Import the .conf file"
echo "   - Mobile: Scan the QR code"
echo ""
echo "3. Test connection:"
echo "   - Connect to VPN"
echo "   - Visit: http://10.0.0.1 (ArmGuard interface)"
echo ""
echo "🛡️  Security note:"
echo "  Role '$ROLE' has restricted access based on military security policy."
echo ""
echo "📱 Mobile QR Code:"
echo "  Transfer $QR_CODE_FILE to view on your phone"
echo ""

# Show current peers
echo -e "${BLUE}📊 Current VPN Status:${NC}"
wg show