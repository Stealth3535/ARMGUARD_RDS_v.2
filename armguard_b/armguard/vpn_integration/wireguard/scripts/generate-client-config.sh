#!/bin/bash

################################################################################
# ArmGuard WireGuard Client Configuration Generator
# 
# Generates WireGuard client configurations for different user roles
# with appropriate access levels and security settings
#
# Usage: ./generate-client-config.sh <client_name> <description> [role]
################################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default configuration
DEFAULT_ROLE="personnel"
CONFIG_DIR="/etc/wireguard"
CLIENTS_DIR="$CONFIG_DIR/clients"
KEYS_DIR="$CONFIG_DIR/keys"

# Usage function
usage() {
    echo -e "${BLUE}ArmGuard WireGuard Client Configuration Generator${NC}"
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo "  $0 <client_name> <description> [role]"
    echo ""
    echo -e "${CYAN}Parameters:${NC}"
    echo "  client_name  : Unique identifier for the client (no spaces)"
    echo "  description  : Human-readable description"
    echo "  role         : User role (default: personnel)"
    echo ""
    echo -e "${CYAN}Available Roles:${NC}"
    echo "  commander    : Field Commander (Full LAN access, IP: 10.0.0.10-19)"
    echo "  armorer      : Armorer (Full LAN access, IP: 10.0.0.20-29)"
    echo "  emergency    : Emergency Ops (Full LAN access, IP: 10.0.0.30-39)"
    echo "  personnel    : Personnel (WAN read-only, IP: 10.0.0.40-49)"
    echo ""
    echo -e "${CYAN}Examples:${NC}"
    echo "  $0 field-cmd-01 \"Field Commander Alpha\" commander"
    echo "  $0 armorer-home \"Home Office Armorer\" armorer"
    echo "  $0 emergency-tablet \"Emergency Response Tablet\" emergency"
    echo "  $0 mobile-personnel \"Personnel Mobile Device\" personnel"
    exit 1
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}❌ This script must be run as root${NC}"
   echo "Usage: sudo $0"
   exit 1
fi

# Check parameters
if [[ $# -lt 2 ]] || [[ $# -gt 3 ]]; then
    usage
fi

CLIENT_NAME="$1"
CLIENT_DESC="$2"
CLIENT_ROLE="${3:-$DEFAULT_ROLE}"

# Validate client name (no spaces, special characters)
if [[ ! "$CLIENT_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo -e "${RED}❌ Invalid client name. Use only letters, numbers, hyphens, and underscores.${NC}"
    exit 1
fi

# Check if directories exist
if [[ ! -d "$CONFIG_DIR" ]] || [[ ! -d "$KEYS_DIR" ]]; then
    echo -e "${RED}❌ WireGuard not properly configured. Run setup-wireguard-server.sh first.${NC}"
    exit 1
fi

# Check if server keys exist
if [[ ! -f "$KEYS_DIR/server_public.key" ]]; then
    echo -e "${RED}❌ Server public key not found. Run setup-wireguard-server.sh first.${NC}"
    exit 1
fi

# Create clients directory if it doesn't exist
mkdir -p "$CLIENTS_DIR"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  ArmGuard VPN Client Configuration Generator${NC}"
echo -e "${BLUE}================================================${NC}"
echo "Client Name: $CLIENT_NAME"
echo "Description: $CLIENT_DESC"
echo "Role: $CLIENT_ROLE"
echo "Generated: $(date)"
echo ""

# Validate role and determine IP range and permissions
case "$CLIENT_ROLE" in
    "commander")
        IP_RANGE_START=10
        IP_RANGE_END=19
        ACCESS_LEVEL="full_lan"
        ALLOWED_NETWORKS="192.168.10.0/24"
        SESSION_TIMEOUT="7200"  # 2 hours
        DESCRIPTION_SUFFIX="Field Commander"
        ;;
    "armorer")
        IP_RANGE_START=20
        IP_RANGE_END=29
        ACCESS_LEVEL="full_lan"
        ALLOWED_NETWORKS="192.168.10.0/24"
        SESSION_TIMEOUT="3600"  # 1 hour
        DESCRIPTION_SUFFIX="Armorer"
        ;;
    "emergency")
        IP_RANGE_START=30
        IP_RANGE_END=39
        ACCESS_LEVEL="full_lan_limited"
        ALLOWED_NETWORKS="192.168.10.0/24"
        SESSION_TIMEOUT="1800"  # 30 minutes
        DESCRIPTION_SUFFIX="Emergency Operations"
        ;;
    "personnel")
        IP_RANGE_START=40
        IP_RANGE_END=49
        ACCESS_LEVEL="wan_readonly"
        ALLOWED_NETWORKS="192.168.10.1/32"  # Server only
        SESSION_TIMEOUT="900"   # 15 minutes
        DESCRIPTION_SUFFIX="Personnel"
        ;;
    *)
        echo -e "${RED}❌ Invalid role: $CLIENT_ROLE${NC}"
        echo "Valid roles: commander, armorer, emergency, personnel"
        exit 1
        ;;
esac

echo -e "${CYAN}🔍 Determining available IP address...${NC}"

# Find next available IP in range
CLIENT_IP=""
for i in $(seq $IP_RANGE_START $IP_RANGE_END); do
    POTENTIAL_IP="10.0.0.$i"
    if ! grep -q "AllowedIPs = $POTENTIAL_IP/32" "$CONFIG_DIR/wg0.conf" 2>/dev/null; then
        CLIENT_IP="$POTENTIAL_IP"
        break
    fi
done

if [[ -z "$CLIENT_IP" ]]; then
    echo -e "${RED}❌ No available IP addresses in range for role: $CLIENT_ROLE${NC}"
    echo "Range: 10.0.0.$IP_RANGE_START - 10.0.0.$IP_RANGE_END"
    echo "Check existing configurations or remove unused clients."
    exit 1
fi

echo -e "${GREEN}✓ Assigned IP: $CLIENT_IP${NC}"
echo ""

# Check if client already exists
CLIENT_CONFIG="$CLIENTS_DIR/${CLIENT_NAME}.conf"
if [[ -f "$CLIENT_CONFIG" ]]; then
    echo -e "${YELLOW}⚠️  Client configuration already exists: $CLIENT_CONFIG${NC}"
    read -p "Overwrite existing configuration? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Operation cancelled."
        exit 1
    fi
    
    # Backup existing configuration
    BACKUP_FILE="$CLIENTS_DIR/${CLIENT_NAME}.conf.backup.$(date +%Y%m%d-%H%M%S)"
    cp "$CLIENT_CONFIG" "$BACKUP_FILE"
    echo -e "${YELLOW}Existing configuration backed up to: $BACKUP_FILE${NC}"
fi

echo -e "${CYAN}🔐 Generating client cryptographic keys...${NC}"

# Generate client keys
CLIENT_PRIVATE_KEY=$(wg genkey)
CLIENT_PUBLIC_KEY=$(echo "$CLIENT_PRIVATE_KEY" | wg pubkey)

echo -e "${GREEN}✓ Client keys generated${NC}"
echo "Public key: $CLIENT_PUBLIC_KEY"
echo ""

# Get server public key
SERVER_PUBLIC_KEY=$(cat "$KEYS_DIR/server_public.key")

echo -e "${CYAN}📝 Creating client configuration...${NC}"

# Create comprehensive client configuration
cat > "$CLIENT_CONFIG" << EOF
# =============================================================================
# ArmGuard VPN Client Configuration
# =============================================================================
# Client Name: $CLIENT_NAME
# Description: $CLIENT_DESC ($DESCRIPTION_SUFFIX)
# Role: $CLIENT_ROLE
# Access Level: $ACCESS_LEVEL
# Assigned IP: $CLIENT_IP
# Generated: $(date)
# Session Timeout: ${SESSION_TIMEOUT}s
# =============================================================================

[Interface]
# Client private key (keep this secret!)
PrivateKey = $CLIENT_PRIVATE_KEY

# Client VPN IP address
Address = $CLIENT_IP/24

# DNS servers (VPN server first, then public DNS)
DNS = 10.0.0.1, 8.8.8.8

# Optional: Custom DNS for enhanced security
# DNS = 10.0.0.1

# Optional: Kill switch (uncomment to enable)
# PostUp = iptables -I OUTPUT ! -o %i -m mark ! --mark \$(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT
# PreDown = iptables -D OUTPUT ! -o %i -m mark ! --mark \$(wg show %i fwmark) -m addrtype ! --dst-type LOCAL -j REJECT

[Peer]
# ArmGuard VPN Server
PublicKey = $SERVER_PUBLIC_KEY

# Server endpoint (IMPORTANT: Replace with your actual server IP or domain!)
Endpoint = YOUR_SERVER_PUBLIC_IP:51820

# Networks accessible through VPN
# $CLIENT_ROLE role has access to: $ALLOWED_NETWORKS
AllowedIPs = $ALLOWED_NETWORKS

# Keep connection alive (important for mobile devices behind NAT)
PersistentKeepalive = 25

# =============================================================================
# Usage Instructions:
# =============================================================================
# 1. Replace YOUR_SERVER_PUBLIC_IP with your actual server IP address
# 2. Install WireGuard client on your device
# 3. Import this configuration file
# 4. Connect to establish VPN tunnel
# 
# Access URLs after connection:
# • ArmGuard LAN (full access): https://192.168.10.1:8443
# • ArmGuard WAN (read-only): https://192.168.10.1:443
# 
# Security Notes:
# • Keep this configuration file secure and encrypted
# • Do not share your private key with anyone
# • Report any suspicious activity immediately
# • VPN sessions timeout after ${SESSION_TIMEOUT} seconds of inactivity
# =============================================================================
EOF

chmod 600 "$CLIENT_CONFIG"
echo -e "${GREEN}✓ Client configuration created: $CLIENT_CONFIG${NC}"
echo ""

# Add peer to server configuration
echo -e "${CYAN}🔗 Adding peer to server configuration...${NC}"

# Check if peer already exists in server config
if grep -q "$CLIENT_PUBLIC_KEY" "$CONFIG_DIR/wg0.conf"; then
    echo -e "${YELLOW}⚠️  Peer already exists in server configuration${NC}"
    # Remove existing peer entry
    sed -i "/# Client: .*$CLIENT_NAME/,/^$/d" "$CONFIG_DIR/wg0.conf"
    sed -i "/PublicKey = $CLIENT_PUBLIC_KEY/,/^$/d" "$CONFIG_DIR/wg0.conf"
    echo -e "${YELLOW}Existing peer entry removed${NC}"
fi

# Add new peer entry
cat >> "$CONFIG_DIR/wg0.conf" << EOF

# =============================================================================
# Client: $CLIENT_DESC
# Name: $CLIENT_NAME
# Role: $CLIENT_ROLE ($DESCRIPTION_SUFFIX)
# Access Level: $ACCESS_LEVEL
# Added: $(date)
# =============================================================================
[Peer]
PublicKey = $CLIENT_PUBLIC_KEY
AllowedIPs = $CLIENT_IP/32

EOF

echo -e "${GREEN}✓ Peer added to server configuration${NC}"
echo ""

# Generate QR code for mobile devices
echo -e "${CYAN}📱 Generating QR code for mobile device setup...${NC}"

if command -v qrencode >/dev/null 2>&1; then
    echo "QR Code for mobile device import:"
    echo ""
    
    # Create temporary config with placeholder replaced by actual instruction
    TEMP_CONFIG=$(mktemp)
    sed 's/YOUR_SERVER_PUBLIC_IP/[REPLACE_WITH_SERVER_IP]/g' "$CLIENT_CONFIG" > "$TEMP_CONFIG"
    
    qrencode -t ansiutf8 < "$TEMP_CONFIG"
    rm "$TEMP_CONFIG"
    
    echo ""
    echo -e "${YELLOW}Note: Replace [REPLACE_WITH_SERVER_IP] with your actual server IP before using QR code${NC}"
else
    echo -e "${YELLOW}⚠️  qrencode not installed. Install with: apt install qrencode${NC}"
fi
echo ""

# Create role-specific documentation
DOCS_FILE="$CLIENTS_DIR/${CLIENT_NAME}_instructions.txt"
cat > "$DOCS_FILE" << EOF
ArmGuard VPN Client Setup Instructions
=====================================

Client Information:
------------------
Name: $CLIENT_NAME
Description: $CLIENT_DESC
Role: $CLIENT_ROLE ($DESCRIPTION_SUFFIX)
Assigned IP: $CLIENT_IP
Access Level: $ACCESS_LEVEL
Session Timeout: ${SESSION_TIMEOUT} seconds

Configuration File:
------------------
Location: $CLIENT_CONFIG

Setup Instructions:
------------------
1. SECURITY FIRST:
   - This configuration contains sensitive cryptographic keys
   - Store securely and encrypt if transmitting
   - Never share your private key with anyone

2. REPLACE SERVER IP:
   - Edit the configuration file
   - Replace "YOUR_SERVER_PUBLIC_IP" with the actual server IP address
   - Save the file

3. INSTALL WIREGUARD CLIENT:
   - Windows: Download from wireguard.com
   - macOS: Install from App Store
   - iOS: Install WireGuard app
   - Android: Install WireGuard app
   - Linux: apt install wireguard

4. IMPORT CONFIGURATION:
   - Desktop: Import the .conf file
   - Mobile: Scan QR code or import file

5. CONNECT:
   - Activate the VPN connection
   - Verify connection: ping 10.0.0.1

Access Information:
------------------
Based on your role ($CLIENT_ROLE), you have access to:

EOF

case "$CLIENT_ROLE" in
    "commander"|"armorer"|"emergency")
        cat >> "$DOCS_FILE" << EOF
• Full ArmGuard System Access (LAN-equivalent)
  - URL: https://192.168.10.1:8443
  - Features: Complete inventory management, transactions, administration
  - Permissions: All armory operations authorized for your role

• ArmGuard Status Portal (WAN access)
  - URL: https://192.168.10.1:443
  - Features: Status checking, reports, read-only operations

• VPN Gateway
  - IP: 10.0.0.1
  - Purpose: Network connectivity testing

Security Restrictions:
• Session automatically expires after $((SESSION_TIMEOUT/60)) minutes of inactivity
• All activities are logged and monitored
• Violation of security policies may result in access revocation
EOF
        ;;
    "personnel")
        cat >> "$DOCS_FILE" << EOF
• ArmGuard Status Portal (Read-Only Access)
  - URL: https://192.168.10.1:443
  - Features: Transaction history, status checking, personal records
  - Permissions: Read-only access to your personal information

• Limited Network Access
  - VPN Gateway: 10.0.0.1 (connectivity testing only)
  - ArmGuard Server: 192.168.10.1 (status portal only)

Security Restrictions:
• No access to administrative functions
• No access to full inventory management
• Session automatically expires after $((SESSION_TIMEOUT/60)) minutes of inactivity
• All activities are logged and monitored
EOF
        ;;
esac

cat >> "$DOCS_FILE" << EOF

Troubleshooting:
---------------
• Cannot connect: Check server IP address and firewall settings
• Slow connection: Check network quality and server load
• Access denied: Verify your role permissions and session timeout
• Connection drops: Check PersistentKeepalive setting (25 seconds)

Support Contact:
---------------
IT Support: [Contact information to be filled by administrator]
Emergency: [Emergency contact information]

Generated: $(date)
Configuration: $CLIENT_CONFIG
EOF

chmod 600 "$DOCS_FILE"
echo -e "${GREEN}✓ Setup instructions created: $DOCS_FILE${NC}"
echo ""

# Display summary
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Client Configuration Generation Complete!${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${GREEN}✅ Summary:${NC}"
echo "• Client: $CLIENT_NAME ($CLIENT_DESC)"
echo "• Role: $CLIENT_ROLE ($DESCRIPTION_SUFFIX)"
echo "• VPN IP: $CLIENT_IP"
echo "• Access: $ACCESS_LEVEL"
echo "• Session Timeout: $((SESSION_TIMEOUT/60)) minutes"
echo "• Config File: $CLIENT_CONFIG"
echo "• Instructions: $DOCS_FILE"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Edit client config and replace YOUR_SERVER_PUBLIC_IP with actual IP"
echo "2. Securely transfer configuration to client device"
echo "3. Restart WireGuard server: systemctl restart wg-quick@wg0"
echo "4. Test client connection"
echo "5. Verify access levels work correctly"
echo ""
echo -e "${CYAN}🛠️  Server Management:${NC}"
echo "• Restart WireGuard: systemctl restart wg-quick@wg0"
echo "• Check status: wg show"
echo "• Monitor connections: monitor-vpn"
echo "• View logs: journalctl -u wg-quick@wg0 -f"
echo ""
echo -e "${RED}🔒 Security Reminders:${NC}"
echo "• Configuration contains private keys - handle securely"
echo "• All VPN activity is logged and monitored"
echo "• Report any suspicious activity immediately"
echo "• Review and rotate keys regularly"
echo ""
echo -e "${GREEN}Client configuration generated successfully at $(date)${NC}"