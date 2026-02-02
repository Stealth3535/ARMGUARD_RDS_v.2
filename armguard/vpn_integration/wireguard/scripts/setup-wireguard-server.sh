#!/bin/bash

################################################################################
# ArmGuard WireGuard Server Setup Script
# 
# This script installs and configures WireGuard VPN server for secure remote
# access to ArmGuard Military Inventory Management System
#
# Usage: sudo ./setup-wireguard-server.sh
# Requirements: Ubuntu 20.04+, root privileges, dual network interfaces
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
WG_INTERFACE="wg0"
WG_PORT="51820"
WG_NET="10.0.0.0/24"
WG_SERVER_IP="10.0.0.1"
LAN_INTERFACE="eth1"
WAN_INTERFACE="eth0"
LAN_SUBNET="192.168.10.0/24"

# Logging
LOG_FILE="/var/log/armguard/wireguard-setup.log"
mkdir -p /var/log/armguard
exec > >(tee -a "$LOG_FILE")
exec 2>&1

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  ArmGuard WireGuard VPN Server Setup${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Started: $(date)"
echo "Log file: $LOG_FILE"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Check system compatibility
echo -e "${CYAN}🔍 Checking system compatibility...${NC}"

# Check OS version
if ! grep -q "Ubuntu 20\|Ubuntu 22\|Debian 11\|Debian 12" /etc/os-release; then
    echo -e "${YELLOW}⚠️  Warning: This script is tested on Ubuntu 20.04+/Debian 11+${NC}"
    echo "Current OS: $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check network interfaces
echo "Checking network interfaces..."
if ! ip link show "$LAN_INTERFACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: LAN interface $LAN_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep "^[0-9]" | cut -d: -f2 | tr -d ' '
    read -p "Enter correct LAN interface name: " LAN_INTERFACE
fi

if ! ip link show "$WAN_INTERFACE" &>/dev/null; then
    echo -e "${YELLOW}⚠️  Warning: WAN interface $WAN_INTERFACE not found${NC}"
    echo "Available interfaces:"
    ip link show | grep "^[0-9]" | cut -d: -f2 | tr -d ' '
    read -p "Enter correct WAN interface name: " WAN_INTERFACE
fi

echo -e "${GREEN}✓ System compatibility check passed${NC}"
echo ""

# Update system packages
echo -e "${CYAN}📦 Updating system packages...${NC}"
apt update
apt upgrade -y
echo -e "${GREEN}✓ System packages updated${NC}"
echo ""

# Install WireGuard and dependencies
echo -e "${CYAN}🔧 Installing WireGuard and dependencies...${NC}"
apt install -y wireguard wireguard-tools qrencode iptables-persistent ufw fail2ban
echo -e "${GREEN}✓ WireGuard and dependencies installed${NC}"
echo ""

# Enable IP forwarding
echo -e "${CYAN}🌐 Configuring IP forwarding...${NC}"
cat >> /etc/sysctl.conf << EOF
# WireGuard VPN - IP forwarding
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# Enhanced network security
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
EOF

sysctl -p
echo -e "${GREEN}✓ IP forwarding configured${NC}"
echo ""

# Create WireGuard directory structure
echo -e "${CYAN}📂 Creating WireGuard directory structure...${NC}"
mkdir -p /etc/wireguard/{keys,clients,backups}
chmod 700 /etc/wireguard
chmod 700 /etc/wireguard/keys
echo -e "${GREEN}✓ Directory structure created${NC}"
echo ""

# Generate server keys
echo -e "${CYAN}🔐 Generating server cryptographic keys...${NC}"
cd /etc/wireguard/keys
if [[ ! -f server_private.key ]]; then
    wg genkey | tee server_private.key | wg pubkey > server_public.key
    chmod 600 server_private.key
    chmod 644 server_public.key
    echo -e "${GREEN}✓ Server keys generated${NC}"
else
    echo -e "${YELLOW}⚠️  Server keys already exist, skipping generation${NC}"
fi

SERVER_PRIVATE_KEY=$(cat server_private.key)
SERVER_PUBLIC_KEY=$(cat server_public.key)
echo "Server public key: $SERVER_PUBLIC_KEY"
echo ""

# Create server configuration
echo -e "${CYAN}⚙️  Creating WireGuard server configuration...${NC}"
cat > /etc/wireguard/wg0.conf << EOF
# ArmGuard WireGuard Server Configuration
# Generated: $(date)
# Interface: $WG_INTERFACE
# Network: $WG_NET

[Interface]
# Server private key
PrivateKey = $SERVER_PRIVATE_KEY

# Server IP address and network
Address = $WG_SERVER_IP/24

# Listen port
ListenPort = $WG_PORT

# DNS servers for VPN clients
DNS = $WG_SERVER_IP, 8.8.8.8, 8.8.4.4

# Firewall rules for routing
PostUp = iptables -A FORWARD -i $WG_INTERFACE -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -s $WG_NET -o $WAN_INTERFACE -j MASQUERADE
PostUp = iptables -A FORWARD -i $WAN_INTERFACE -o $WG_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
PostUp = iptables -A FORWARD -i $WG_INTERFACE -o $LAN_INTERFACE -j ACCEPT
PostUp = iptables -A FORWARD -i $LAN_INTERFACE -o $WG_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT

PostDown = iptables -D FORWARD -i $WG_INTERFACE -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s $WG_NET -o $WAN_INTERFACE -j MASQUERADE
PostDown = iptables -D FORWARD -i $WAN_INTERFACE -o $WG_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -D FORWARD -i $WG_INTERFACE -o $LAN_INTERFACE -j ACCEPT
PostDown = iptables -D FORWARD -i $LAN_INTERFACE -o $WG_INTERFACE -m state --state RELATED,ESTABLISHED -j ACCEPT

# Clients will be added below this line
# Format: [Peer] sections with PublicKey and AllowedIPs
EOF

chmod 600 /etc/wireguard/wg0.conf
echo -e "${GREEN}✓ Server configuration created${NC}"
echo ""

# Configure firewall
echo -e "${CYAN}🛡️  Configuring firewall rules...${NC}"

# Reset UFW to defaults
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (be careful not to lock yourself out!)
ufw allow ssh

# Allow WireGuard port
ufw allow $WG_PORT/udp comment "WireGuard VPN"

# Allow ArmGuard ports
ufw allow 8443/tcp comment "ArmGuard LAN"
ufw allow 443/tcp comment "ArmGuard WAN"
ufw allow 80/tcp comment "HTTP redirect"

# Allow VPN clients to access LAN
ufw route allow in on $WG_INTERFACE out on $LAN_INTERFACE to $LAN_SUBNET
ufw route allow in on $LAN_INTERFACE out on $WG_INTERFACE from $LAN_SUBNET

# Enable logging
ufw logging on

# Enable firewall
echo "y" | ufw enable

echo -e "${GREEN}✓ Firewall configured${NC}"
echo ""

# Configure Fail2Ban for additional security
echo -e "${CYAN}🔒 Configuring Fail2Ban for VPN security...${NC}"

# Create WireGuard filter
cat > /etc/fail2ban/filter.d/wireguard.conf << 'EOF'
# Fail2Ban filter for WireGuard
# Monitors for potential brute force attacks on VPN

[Definition]
failregex = ^.*Invalid handshake initiation from <HOST>.*$
            ^.*Bad packet received from <HOST>.*$
            ^.*Handshake did not complete after 5 seconds, retrying from <HOST>.*$
ignoreregex =
EOF

# Create WireGuard jail
cat > /etc/fail2ban/jail.d/wireguard.local << EOF
[wireguard]
enabled = true
port = $WG_PORT
protocol = udp
filter = wireguard
logpath = /var/log/syslog
maxretry = 5
bantime = 3600
findtime = 600
EOF

# Restart Fail2Ban
systemctl restart fail2ban
systemctl enable fail2ban

echo -e "${GREEN}✓ Fail2Ban configured${NC}"
echo ""

# Create management scripts
echo -e "${CYAN}📜 Creating management scripts...${NC}"

# Client addition script
cat > /usr/local/bin/add-vpn-client << 'EOFSCRIPT'
#!/bin/bash

# ArmGuard WireGuard Client Addition Script
# Usage: add-vpn-client <client_name> <description> <role>

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <client_name> <description> <role>"
    echo "Roles: commander, armorer, emergency, personnel"
    exit 1
fi

CLIENT_NAME="$1"
CLIENT_DESC="$2"
CLIENT_ROLE="$3"

# Validate role and assign IP
case $CLIENT_ROLE in
    "commander")
        if [[ -f "/etc/wireguard/clients/${CLIENT_NAME}.conf" ]]; then
            echo "Client $CLIENT_NAME already exists"
            exit 1
        fi
        # Find next available IP in commander range (10.0.0.10-19)
        for i in {10..19}; do
            if ! grep -q "AllowedIPs = 10.0.0.$i/32" /etc/wireguard/wg0.conf; then
                CLIENT_IP="10.0.0.$i"
                break
            fi
        done
        ;;
    "armorer")
        # Find next available IP in armorer range (10.0.0.20-29)
        for i in {20..29}; do
            if ! grep -q "AllowedIPs = 10.0.0.$i/32" /etc/wireguard/wg0.conf; then
                CLIENT_IP="10.0.0.$i"
                break
            fi
        done
        ;;
    "emergency")
        # Find next available IP in emergency range (10.0.0.30-39)
        for i in {30..39}; do
            if ! grep -q "AllowedIPs = 10.0.0.$i/32" /etc/wireguard/wg0.conf; then
                CLIENT_IP="10.0.0.$i"
                break
            fi
        done
        ;;
    "personnel")
        # Find next available IP in personnel range (10.0.0.40-49)
        for i in {40..49}; do
            if ! grep -q "AllowedIPs = 10.0.0.$i/32" /etc/wireguard/wg0.conf; then
                CLIENT_IP="10.0.0.$i"
                break
            fi
        done
        ;;
    *)
        echo "Invalid role: $CLIENT_ROLE"
        echo "Valid roles: commander, armorer, emergency, personnel"
        exit 1
        ;;
esac

if [[ -z "${CLIENT_IP:-}" ]]; then
    echo "No available IP addresses in range for role: $CLIENT_ROLE"
    exit 1
fi

echo "Adding VPN client: $CLIENT_NAME ($CLIENT_DESC)"
echo "Role: $CLIENT_ROLE"
echo "Assigned IP: $CLIENT_IP"

# Generate client keys
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)

# Add peer to server configuration
cat >> /etc/wireguard/wg0.conf << EOFPEER

# Client: $CLIENT_DESC
# Role: $CLIENT_ROLE
# Added: $(date)
[Peer]
PublicKey = $CLIENT_PUBLIC_KEY
AllowedIPs = $CLIENT_IP/32
EOFPEER

# Create client configuration
mkdir -p /etc/wireguard/clients

# Get server public key
SERVER_PUBLIC_KEY=$(cat /etc/wireguard/keys/server_public.key)

# Determine allowed IPs based on role
case $CLIENT_ROLE in
    "commander"|"armorer"|"emergency")
        ALLOWED_IPS="192.168.10.0/24"  # Full LAN access
        ;;
    "personnel")
        ALLOWED_IPS="192.168.10.1/32"  # Server only (WAN-level access)
        ;;
esac

cat > /etc/wireguard/clients/${CLIENT_NAME}.conf << EOFCLIENT
# ArmGuard VPN Client Configuration
# Client: $CLIENT_DESC
# Role: $CLIENT_ROLE
# Generated: $(date)

[Interface]
# Client private key
PrivateKey = $CLIENT_PRIVATE_KEY

# Client VPN IP address
Address = $CLIENT_IP/24

# DNS servers
DNS = 10.0.0.1

[Peer]
# ArmGuard VPN Server
PublicKey = $SERVER_PUBLIC_KEY

# Server endpoint (replace YOUR_SERVER_PUBLIC_IP with actual IP or domain)
Endpoint = YOUR_SERVER_PUBLIC_IP:51820

# Networks accessible through VPN
AllowedIPs = $ALLOWED_IPS

# Keep connection alive (for mobile devices behind NAT)
PersistentKeepalive = 25
EOFCLIENT

echo ""
echo "✓ Client configuration created: /etc/wireguard/clients/${CLIENT_NAME}.conf"
echo "✓ Client public key: $CLIENT_PUBLIC_KEY"
echo ""
echo "Next steps:"
echo "1. Replace YOUR_SERVER_PUBLIC_IP in client config with your actual server IP"
echo "2. Restart WireGuard: systemctl restart wg-quick@wg0"
echo "3. Send client configuration to user securely"
echo ""
echo "QR Code for mobile devices:"
qrencode -t ansiutf8 < /etc/wireguard/clients/${CLIENT_NAME}.conf

EOFSCRIPT

chmod +x /usr/local/bin/add-vpn-client

# Client removal script
cat > /usr/local/bin/remove-vpn-client << 'EOFSCRIPT'
#!/bin/bash

# ArmGuard WireGuard Client Removal Script
# Usage: remove-vpn-client <client_name>

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <client_name>"
    exit 1
fi

CLIENT_NAME="$1"
CLIENT_CONFIG="/etc/wireguard/clients/${CLIENT_NAME}.conf"

if [[ ! -f "$CLIENT_CONFIG" ]]; then
    echo "Client $CLIENT_NAME not found"
    exit 1
fi

echo "Removing VPN client: $CLIENT_NAME"

# Get client public key
CLIENT_PUBLIC_KEY=$(grep "PublicKey" "$CLIENT_CONFIG" | head -1 | cut -d'=' -f2 | tr -d ' ')

if [[ -n "$CLIENT_PUBLIC_KEY" ]]; then
    # Remove peer from server configuration
    # This is a complex sed command to remove the entire [Peer] block
    sed -i "/# Client: .*${CLIENT_NAME}/,/^\[Peer\]/d" /etc/wireguard/wg0.conf
    sed -i "/PublicKey = ${CLIENT_PUBLIC_KEY}/,/^$/d" /etc/wireguard/wg0.conf
fi

# Backup and remove client configuration
mkdir -p /etc/wireguard/backups
cp "$CLIENT_CONFIG" "/etc/wireguard/backups/${CLIENT_NAME}.conf.$(date +%Y%m%d-%H%M%S)"
rm "$CLIENT_CONFIG"

echo "✓ Client $CLIENT_NAME removed"
echo "✓ Configuration backed up to /etc/wireguard/backups/"
echo ""
echo "Restart WireGuard to apply changes: systemctl restart wg-quick@wg0"

EOFSCRIPT

chmod +x /usr/local/bin/remove-vpn-client

# Connection monitoring script
cat > /usr/local/bin/monitor-vpn << 'EOFSCRIPT'
#!/bin/bash

# ArmGuard WireGuard Connection Monitor
# Usage: monitor-vpn

echo "=== ArmGuard VPN Connection Monitor ==="
echo "Generated: $(date)"
echo ""

echo "WireGuard Interface Status:"
wg show

echo ""
echo "Active Connections:"
wg show wg0 peers

echo ""
echo "Network Interface Statistics:"
cat /proc/net/dev | grep wg0 || echo "No statistics available"

echo ""
echo "Recent VPN Log Entries (last 10):"
journalctl -u wg-quick@wg0 -n 10 --no-pager

echo ""
echo "Firewall Status:"
ufw status | grep -E "51820|WireGuard"

echo ""
echo "Fail2Ban Status:"
fail2ban-client status wireguard 2>/dev/null || echo "Fail2Ban wireguard jail not active"

EOFSCRIPT

chmod +x /usr/local/bin/monitor-vpn

echo -e "${GREEN}✓ Management scripts created${NC}"
echo ""

# Enable and start WireGuard
echo -e "${CYAN}🚀 Starting WireGuard service...${NC}"
systemctl enable wg-quick@wg0
systemctl start wg-quick@wg0

# Verify service is running
if systemctl is-active --quiet wg-quick@wg0; then
    echo -e "${GREEN}✓ WireGuard service started successfully${NC}"
else
    echo -e "${RED}❌ Failed to start WireGuard service${NC}"
    echo "Check logs: journalctl -u wg-quick@wg0"
    exit 1
fi
echo ""

# Display status
echo -e "${CYAN}📊 WireGuard Status:${NC}"
wg show
echo ""

# Final configuration summary
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  WireGuard VPN Server Setup Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}✅ Installation Summary:${NC}"
echo "• WireGuard server installed and configured"
echo "• VPN network: $WG_NET"
echo "• Server IP: $WG_SERVER_IP"
echo "• Listen port: $WG_PORT (UDP)"
echo "• Firewall configured with UFW"
echo "• Fail2Ban protection enabled"
echo "• Management scripts created"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Update YOUR_SERVER_PUBLIC_IP in client configs"
echo "2. Add VPN clients using: add-vpn-client <name> <desc> <role>"
echo "3. Monitor connections: monitor-vpn"
echo "4. Integrate with ArmGuard (see IMPLEMENTATION_GUIDE.md)"
echo ""
echo -e "${CYAN}🛠️  Management Commands:${NC}"
echo "• Add client: add-vpn-client <name> <description> <role>"
echo "• Remove client: remove-vpn-client <name>"
echo "• Monitor: monitor-vpn"
echo "• Status: systemctl status wg-quick@wg0"
echo "• Logs: journalctl -u wg-quick@wg0 -f"
echo ""
echo -e "${CYAN}📁 Important Files:${NC}"
echo "• Server config: /etc/wireguard/wg0.conf"
echo "• Client configs: /etc/wireguard/clients/"
echo "• Server keys: /etc/wireguard/keys/"
echo "• Backups: /etc/wireguard/backups/"
echo ""
echo -e "${GREEN}Setup completed successfully at $(date)${NC}"
echo "Log file: $LOG_FILE"