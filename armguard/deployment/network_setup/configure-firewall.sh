#!/bin/bash

################################################################################
# ArmGuard - Comprehensive Firewall Configuration
# Hybrid Network Setup (LAN + WAN)
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
fi

# Configuration (can be overridden by config.sh or environment)
LAN_INTERFACE="${LAN_INTERFACE:-eth1}"      # LAN network interface
WAN_INTERFACE="${WAN_INTERFACE:-eth0}"      # WAN network interface
LAN_SUBNET="${LAN_SUBNET:-192.168.10.0/24}"
SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.10.1}"
ARMORY_PC_IP="${ARMORY_PC_IP:-192.168.10.2}"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       ArmGuard Hybrid Network Firewall Setup              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Backup Existing Firewall Rules${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Backup existing rules
if command -v ufw &> /dev/null; then
    echo -e "${YELLOW}Backing up UFW rules...${NC}"
    ufw status verbose > /root/ufw-backup-$(date +%Y%m%d_%H%M%S).txt 2>/dev/null || true
fi

if command -v iptables &> /dev/null; then
    echo -e "${YELLOW}Backing up iptables rules...${NC}"
    iptables-save > /root/iptables-backup-$(date +%Y%m%d_%H%M%S).rules 2>/dev/null || true
fi

echo -e "${GREEN}✓ Backup complete${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Install Firewall Tools${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Install UFW if not present
if ! command -v ufw &> /dev/null; then
    echo -e "${YELLOW}Installing UFW...${NC}"
    apt-get update -qq
    apt-get install -y ufw
    echo -e "${GREEN}✓ UFW installed${NC}"
else
    echo -e "${GREEN}✓ UFW already installed${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Reset and Configure UFW${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Resetting UFW to defaults...${NC}"
ufw --force reset

# Set default policies
echo -e "${YELLOW}Setting default policies...${NC}"
ufw default deny incoming
ufw default allow outgoing
echo -e "${GREEN}✓ Default policies set${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Configure LAN Network Rules${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}LAN Network Configuration:${NC}"
echo "  Subnet:     $LAN_SUBNET"
echo "  Interface:  $LAN_INTERFACE"
echo "  Server IP:  $SERVER_LAN_IP"
echo "  Armory PC:  $ARMORY_PC_IP"
echo ""

# Allow LAN traffic from Armory PC only
echo -e "${YELLOW}Allowing HTTPS from Armory PC (port 8443)...${NC}"
ufw allow in on $LAN_INTERFACE from $ARMORY_PC_IP to $SERVER_LAN_IP port 8443 proto tcp comment 'ArmGuard LAN HTTPS'

# Allow HTTP redirect from Armory PC
echo -e "${YELLOW}Allowing HTTP from Armory PC (port 80)...${NC}"
ufw allow in on $LAN_INTERFACE from $ARMORY_PC_IP to $SERVER_LAN_IP port 80 proto tcp comment 'ArmGuard LAN HTTP redirect'

# Deny all other traffic on LAN interface
echo -e "${YELLOW}Denying all other traffic on LAN interface...${NC}"
ufw deny in on $LAN_INTERFACE comment 'Block all other LAN traffic'

echo -e "${GREEN}✓ LAN rules configured${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5: Block LAN from Internet Access${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Blocking LAN subnet from accessing internet...${NC}"

# Use iptables for advanced routing control
# Block forwarding from LAN to WAN
iptables -I FORWARD -s $LAN_SUBNET -o $WAN_INTERFACE -j DROP
iptables -I FORWARD -s $LAN_SUBNET -o $WAN_INTERFACE -m comment --comment "Block LAN internet access" -j LOG --log-prefix "LAN-INTERNET-BLOCKED: "

# Save iptables rules
iptables-save > /etc/iptables/rules.v4 2>/dev/null || mkdir -p /etc/iptables && iptables-save > /etc/iptables/rules.v4

echo -e "${GREEN}✓ LAN internet access blocked${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6: Configure WAN Network Rules${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}WAN Network Configuration:${NC}"
echo "  Interface:  $WAN_INTERFACE"
echo "  Public:     Internet-facing"
echo ""

# Allow HTTPS for personnel portal (port 443)
echo -e "${YELLOW}Allowing HTTPS on WAN (port 443)...${NC}"
ufw allow in on $WAN_INTERFACE to any port 443 proto tcp comment 'ArmGuard WAN Personnel HTTPS'

# Allow HTTP for ACME challenges and redirects (port 80)
echo -e "${YELLOW}Allowing HTTP on WAN (port 80)...${NC}"
ufw allow in on $WAN_INTERFACE to any port 80 proto tcp comment 'ArmGuard WAN HTTP redirect/ACME'

echo -e "${GREEN}✓ WAN rules configured${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 7: Configure SSH Access${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Configuring SSH access...${NC}"

# Ask user preference
echo -e "${CYAN}How should SSH be accessible?${NC}"
echo "  1) Both LAN and WAN (default)"
echo "  2) LAN only (more secure)"
echo "  3) WAN only"
read -p "Choose option [1-3] (default: 1): " SSH_CHOICE
SSH_CHOICE=${SSH_CHOICE:-1}

case $SSH_CHOICE in
    1)
        ufw allow ssh comment 'SSH access (both networks)'
        echo -e "${GREEN}✓ SSH allowed on both LAN and WAN${NC}"
        ;;
    2)
        ufw allow in on $LAN_INTERFACE to any port 22 proto tcp comment 'SSH LAN only'
        echo -e "${GREEN}✓ SSH allowed on LAN only${NC}"
        ;;
    3)
        ufw allow in on $WAN_INTERFACE to any port 22 proto tcp comment 'SSH WAN only'
        echo -e "${YELLOW}⚠ SSH allowed on WAN (consider using VPN or key-only auth)${NC}"
        ;;
esac

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 8: Enable Connection Tracking${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Configuring connection tracking...${NC}"

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Drop invalid packets
iptables -A INPUT -m conntrack --ctstate INVALID -j DROP

echo -e "${GREEN}✓ Connection tracking enabled${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 9: Configure Rate Limiting (DDoS Protection)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Setting up rate limiting...${NC}"

# Limit NEW connections to 10 per minute per IP (WAN)
ufw limit in on $WAN_INTERFACE to any port 443 proto tcp comment 'Rate limit HTTPS'

echo -e "${GREEN}✓ Rate limiting configured${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 10: Enable Logging${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Enabling firewall logging...${NC}"
ufw logging medium

echo -e "${GREEN}✓ Logging enabled (medium level)${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 11: Enable Firewall${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Enabling UFW firewall...${NC}"
ufw --force enable

echo -e "${GREEN}✓ Firewall enabled${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 12: Configure Persistence${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Making rules persistent across reboots...${NC}"

# Install iptables-persistent
if ! dpkg -l | grep -q iptables-persistent; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y iptables-persistent
fi

# Save current rules
iptables-save > /etc/iptables/rules.v4
ip6tables-save > /etc/iptables/rules.v6

# Enable UFW at boot
systemctl enable ufw

echo -e "${GREEN}✓ Firewall rules will persist across reboots${NC}"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         Firewall Configuration Complete!                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Current Firewall Status:${NC}"
echo ""
ufw status verbose

echo ""
echo -e "${CYAN}Summary of Rules:${NC}"
echo ""
echo -e "${GREEN}✓ LAN Network:${NC}"
echo "  • Armory PC ($ARMORY_PC_IP) can access server on ports 80, 8443"
echo "  • All other LAN traffic blocked"
echo "  • LAN subnet CANNOT access internet"
echo ""
echo -e "${GREEN}✓ WAN Network:${NC}"
echo "  • Public access on port 443 (HTTPS)"
echo "  • Public access on port 80 (HTTP redirect/ACME)"
echo "  • Rate limiting enabled"
echo ""
echo -e "${GREEN}✓ Security:${NC}"
echo "  • Connection tracking enabled"
echo "  • Invalid packets dropped"
echo "  • Logging enabled (medium)"
echo "  • Rules persist across reboots"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Test LAN access from Armory PC"
echo "  2. Verify WAN access from internet"
echo "  3. Check logs: sudo tail -f /var/log/ufw.log"
echo "  4. Monitor: sudo ufw status verbose"
echo ""

echo -e "${CYAN}To view detailed rules:${NC}"
echo "  sudo iptables -L -v -n"
echo "  sudo ufw status numbered"
echo ""
