#!/bin/bash
# ===========================================
# ArmGuard VPN Server Setup Script
# Secure Internet Access via WireGuard VPN
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VPN_SERVER_ADDRESS="10.0.0.1/24"
VPN_PORT="51820"
CLIENT_COUNT=5
SERVER_CONFIG="/etc/wireguard/wg0.conf"
CLIENT_DIR="/etc/wireguard/clients"

echo -e "${BLUE}🔐 ArmGuard VPN Server Setup${NC}"
echo "=================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root${NC}"
    echo "Usage: sudo $0"
    exit 1
fi

# Install WireGuard
echo -e "${YELLOW}📦 Installing WireGuard...${NC}"
apt update
apt install -y wireguard wireguard-tools qrencode

# Create directories
mkdir -p /etc/wireguard/keys
mkdir -p $CLIENT_DIR
chmod 700 /etc/wireguard/keys
chmod 700 $CLIENT_DIR

# Generate server keys
echo -e "${YELLOW}🔑 Generating server keys...${NC}"
cd /etc/wireguard/keys
wg genkey | tee server_private.key | wg pubkey > server_public.key
chmod 600 server_private.key

SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_PUBLIC_KEY=$(cat server_public.key)

echo -e "${GREEN}✅ Server public key: $SERVER_PUBLIC_KEY${NC}"

# Get network interface
INTERFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
echo -e "${YELLOW}🌐 Detected network interface: $INTERFACE${NC}"

# Create server configuration
echo -e "${YELLOW}⚙️ Creating server configuration...${NC}"
cat > $SERVER_CONFIG << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE_KEY
Address = $VPN_SERVER_ADDRESS
ListenPort = $VPN_PORT
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o $INTERFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o $INTERFACE -j MASQUERADE

EOF

# Generate client configurations
echo -e "${YELLOW}👥 Generating client configurations...${NC}"
for i in $(seq 1 $CLIENT_COUNT); do
    CLIENT_NAME="armguard-client-$i"
    CLIENT_IP="10.0.0.$((i+1))/32"
    
    # Generate client keys
    wg genkey | tee $CLIENT_DIR/${CLIENT_NAME}_private.key | wg pubkey > $CLIENT_DIR/${CLIENT_NAME}_public.key
    chmod 600 $CLIENT_DIR/${CLIENT_NAME}_private.key
    
    CLIENT_PRIVATE_KEY=$(cat $CLIENT_DIR/${CLIENT_NAME}_private.key)
    CLIENT_PUBLIC_KEY=$(cat $CLIENT_DIR/${CLIENT_NAME}_public.key)
    
    # Add peer to server config
    cat >> $SERVER_CONFIG << EOF
[Peer]
PublicKey = $CLIENT_PUBLIC_KEY
AllowedIPs = $CLIENT_IP

EOF
    
    # Create client config file
    cat > $CLIENT_DIR/${CLIENT_NAME}.conf << EOF
[Interface]
PrivateKey = $CLIENT_PRIVATE_KEY
Address = $CLIENT_IP
DNS = 8.8.8.8, 8.8.4.4

[Peer]
PublicKey = $SERVER_PUBLIC_KEY
Endpoint = YOUR_PUBLIC_IP:$VPN_PORT
AllowedIPs = 192.168.0.0/24, 10.0.0.0/24
PersistentKeepalive = 25
EOF
    
    # Generate QR code for mobile clients
    qrencode -t ansiutf8 < $CLIENT_DIR/${CLIENT_NAME}.conf > $CLIENT_DIR/${CLIENT_NAME}_qr.txt
    
    echo -e "${GREEN}✅ Generated config for $CLIENT_NAME${NC}"
done

# Enable IP forwarding
echo -e "${YELLOW}🔄 Enabling IP forwarding...${NC}"
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Configure firewall
echo -e "${YELLOW}🛡️ Configuring firewall...${NC}"
ufw allow $VPN_PORT/udp
ufw allow 8000/tcp  # ArmGuard web interface
ufw --force enable

# Start WireGuard service
echo -e "${YELLOW}🚀 Starting WireGuard service...${NC}"
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Display setup completion
echo -e "${GREEN}🎉 VPN Server Setup Complete!${NC}"
echo "=================================="
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Forward port $VPN_PORT (UDP) on your router to 192.168.0.10"
echo "2. Replace 'YOUR_PUBLIC_IP' in client configs with your actual public IP"
echo "3. Distribute client configs from: $CLIENT_DIR"
echo ""
echo -e "${BLUE}🔧 Client Configuration Files:${NC}"
ls -la $CLIENT_DIR/*.conf | while read line; do
    echo "   $line"
done

echo ""
echo -e "${YELLOW}⚠️ Important Security Notes:${NC}"
echo "• Keep client private keys secure"
echo "• Only distribute configs to trusted devices"
echo "• Monitor VPN connections regularly"
echo "• Consider changing default port for security"

echo ""
echo -e "${BLUE}📱 Mobile Setup:${NC}"
echo "Use QR codes in: $CLIENT_DIR/*_qr.txt"

# Show current status
echo ""
echo -e "${BLUE}🔍 Current VPN Status:${NC}"
systemctl status wg-quick@wg0 --no-pager -l