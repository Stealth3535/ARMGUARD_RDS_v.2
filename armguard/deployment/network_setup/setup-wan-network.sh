#!/bin/bash

################################################################################
# ArmGuard - WAN Network Setup (ZeroSSL via ACME)
# Configure public personnel login portal with automatic SSL
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
WAN_INTERFACE="${WAN_INTERFACE:-eth0}"
DOMAIN="${DOMAIN:-login.yourdomain.com}"
EMAIL="${ACME_EMAIL:-admin@yourdomain.com}"
NGINX_CONF="/etc/nginx/sites-available/armguard-wan"
ACME_CLIENT="${ACME_CLIENT:-acme.sh}"  # or "certbot"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     ArmGuard WAN Network Setup (ZeroSSL/Let's Encrypt)    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Prompt for domain
echo -e "${YELLOW}Enter your public domain name:${NC}"
read -p "Domain [login.yourdomain.com]: " INPUT_DOMAIN
DOMAIN=${INPUT_DOMAIN:-$DOMAIN}

echo -e "${YELLOW}Enter your email for certificate notifications:${NC}"
read -p "Email [$EMAIL]: " INPUT_EMAIL
EMAIL=${INPUT_EMAIL:-$EMAIL}

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Verify Network Interface${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check if WAN interface exists
if ! ip link show $WAN_INTERFACE &> /dev/null; then
    echo -e "${RED}ERROR: WAN interface $WAN_INTERFACE not found${NC}"
    echo -e "${YELLOW}Available interfaces:${NC}"
    ip link show | grep -E '^[0-9]+:' | cut -d: -f2
    exit 1
fi

echo -e "${GREEN}✓ WAN interface $WAN_INTERFACE found${NC}"

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me)
echo -e "${CYAN}Public IP: ${YELLOW}$PUBLIC_IP${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Verify DNS Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Checking DNS resolution for $DOMAIN...${NC}"

# Check if domain resolves
if RESOLVED_IP=$(dig +short $DOMAIN | tail -n1); then
    if [ -n "$RESOLVED_IP" ]; then
        echo -e "${CYAN}Domain resolves to: ${YELLOW}$RESOLVED_IP${NC}"
        
        if [ "$RESOLVED_IP" = "$PUBLIC_IP" ]; then
            echo -e "${GREEN}✓ DNS correctly points to this server${NC}"
        else
            echo -e "${RED}✗ DNS points to $RESOLVED_IP but server is $PUBLIC_IP${NC}"
            echo -e "${YELLOW}Update your DNS records before continuing${NC}"
            read -p "Continue anyway? (yes/no): " CONTINUE
            if [ "$CONTINUE" != "yes" ]; then
                exit 1
            fi
        fi
    else
        echo -e "${RED}✗ Domain does not resolve${NC}"
        echo -e "${YELLOW}Configure DNS before continuing${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Could not verify DNS (dig not installed)${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Choose ACME Client${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${CYAN}Choose ACME client:${NC}"
echo "  1) acme.sh (recommended - supports ZeroSSL and Let's Encrypt)"
echo "  2) certbot (official Let's Encrypt client)"
read -p "Choose [1-2] (default: 1): " CLIENT_CHOICE
CLIENT_CHOICE=${CLIENT_CHOICE:-1}

if [ "$CLIENT_CHOICE" = "2" ]; then
    ACME_CLIENT="certbot"
else
    ACME_CLIENT="acme.sh"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Install ACME Client${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$ACME_CLIENT" = "acme.sh" ]; then
    # Install acme.sh
    if [ ! -d "/root/.acme.sh" ]; then
        echo -e "${YELLOW}Installing acme.sh...${NC}"
        curl https://get.acme.sh | sh -s email=$EMAIL
        
        # Source acme.sh
        . /root/.acme.sh/acme.sh.env
        
        echo -e "${GREEN}✓ acme.sh installed${NC}"
    else
        echo -e "${GREEN}✓ acme.sh already installed${NC}"
        . /root/.acme.sh/acme.sh.env
    fi
    
    # Set default CA to ZeroSSL
    echo -e "${YELLOW}Setting default CA to ZeroSSL...${NC}"
    /root/.acme.sh/acme.sh --set-default-ca --server zerossl
    
else
    # Install certbot
    if ! command -v certbot &> /dev/null; then
        echo -e "${YELLOW}Installing certbot...${NC}"
        apt-get update -qq
        apt-get install -y certbot python3-certbot-nginx
        echo -e "${GREEN}✓ certbot installed${NC}"
    else
        echo -e "${GREEN}✓ certbot already installed${NC}"
    fi
fi

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
echo -e "${BLUE}Step 6: Configure Temporary Nginx (for ACME challenge)${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Creating temporary Nginx configuration...${NC}"

# Create ACME challenge directory
mkdir -p /var/www/acme-challenge

# Create temporary config for ACME challenge
cat > /etc/nginx/sites-available/armguard-wan-temp << EOF
server {
    listen 80;
    listen [::]:80;
    
    server_name $DOMAIN www.$DOMAIN;
    
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/acme-challenge;
        default_type "text/plain";
        allow all;
    }
    
    location / {
        return 200 "ArmGuard WAN Setup in Progress";
        add_header Content-Type text/plain;
    }
}
EOF

ln -sf /etc/nginx/sites-available/armguard-wan-temp /etc/nginx/sites-enabled/armguard-wan-temp

# Test and reload
nginx -t && systemctl reload nginx

echo -e "${GREEN}✓ Temporary Nginx configuration active${NC}"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 7: Obtain SSL Certificate${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$ACME_CLIENT" = "acme.sh" ]; then
    echo -e "${YELLOW}Requesting ZeroSSL certificate via acme.sh...${NC}"
    
    # Issue certificate
    /root/.acme.sh/acme.sh --issue \
        -d $DOMAIN \
        -d www.$DOMAIN \
        -w /var/www/acme-challenge \
        --server zerossl \
        --force
    
    # Install certificate to Let's Encrypt compatible location
    mkdir -p /etc/letsencrypt/live/$DOMAIN
    
    /root/.acme.sh/acme.sh --install-cert \
        -d $DOMAIN \
        --cert-file /etc/letsencrypt/live/$DOMAIN/cert.pem \
        --key-file /etc/letsencrypt/live/$DOMAIN/privkey.pem \
        --fullchain-file /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
        --ca-file /etc/letsencrypt/live/$DOMAIN/chain.pem \
        --reloadcmd "systemctl reload nginx"
    
else
    echo -e "${YELLOW}Requesting Let's Encrypt certificate via certbot...${NC}"
    
    certbot certonly \
        --webroot \
        -w /var/www/acme-challenge \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        --force-renewal
fi

# Verify certificate exists
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${GREEN}✓ SSL certificate obtained successfully${NC}"
else
    echo -e "${RED}✗ Failed to obtain SSL certificate${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 8: Configure Production Nginx${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

echo -e "${YELLOW}Installing WAN Nginx configuration...${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$SCRIPT_DIR/nginx-wan.conf" ]; then
    cp "$SCRIPT_DIR/nginx-wan.conf" "$NGINX_CONF"
    
    # Update domain in config
    sed -i "s/login\.yourdomain\.com/$DOMAIN/g" "$NGINX_CONF"
    
    # Remove temporary config
    rm -f /etc/nginx/sites-enabled/armguard-wan-temp
    
    # Enable production site
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/armguard-wan
    
    echo -e "${GREEN}✓ Nginx WAN configuration installed${NC}"
else
    echo -e "${RED}ERROR: nginx-wan.conf not found${NC}"
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
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 9: Configure Auto-Renewal${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ "$ACME_CLIENT" = "acme.sh" ]; then
    echo -e "${YELLOW}Configuring acme.sh auto-renewal...${NC}"
    
    # acme.sh automatically installs a cron job
    if crontab -l | grep -q "acme.sh"; then
        echo -e "${GREEN}✓ Auto-renewal cron job already configured${NC}"
    else
        echo -e "${YELLOW}⚠ Cron job not found, should have been installed automatically${NC}"
    fi
    
else
    echo -e "${YELLOW}Configuring certbot auto-renewal...${NC}"
    
    # Test renewal
    certbot renew --dry-run
    
    # Certbot automatically installs systemd timer
    systemctl enable certbot.timer
    systemctl start certbot.timer
    
    echo -e "${GREEN}✓ Auto-renewal configured (systemd timer)${NC}"
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           WAN Network Setup Complete!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}WAN Network Configuration:${NC}"
echo ""
echo -e "${GREEN}✓ Server Configuration:${NC}"
echo "  Interface:      $WAN_INTERFACE"
echo "  Public IP:      $PUBLIC_IP"
echo "  Domain:         $DOMAIN"
echo "  HTTPS Port:     443"
echo "  HTTP Port:      80 (redirects to 443)"
echo "  Certificate:    /etc/letsencrypt/live/$DOMAIN/"
echo "  ACME Client:    $ACME_CLIENT"
echo ""
echo -e "${GREEN}✓ SSL Certificate:${NC}"
if [ "$ACME_CLIENT" = "acme.sh" ]; then
    echo "  Provider:       ZeroSSL"
    echo "  Auto-renewal:   Via acme.sh cron (daily check)"
    echo "  Manual renewal: /root/.acme.sh/acme.sh --renew -d $DOMAIN"
else
    echo "  Provider:       Let's Encrypt"
    echo "  Auto-renewal:   Via certbot.timer (twice daily)"
    echo "  Manual renewal: certbot renew"
fi
echo ""
echo -e "${YELLOW}⚠ Next Steps:${NC}"
echo ""
echo -e "${CYAN}1. Test HTTPS Access:${NC}"
echo "   • From internet: https://$DOMAIN"
echo "   • Should show valid SSL certificate"
echo "   • Check certificate: https://www.ssllabs.com/ssltest/"
echo ""
echo -e "${CYAN}2. Configure Firewall:${NC}"
echo "   • Run: sudo bash network_setup/configure-firewall.sh"
echo ""
echo -e "${CYAN}3. Monitor Certificate Renewal:${NC}"
if [ "$ACME_CLIENT" = "acme.sh" ]; then
    echo "   • Check logs: cat /root/.acme.sh/$DOMAIN/*.log"
    echo "   • List certs: /root/.acme.sh/acme.sh --list"
else
    echo "   • Check status: systemctl status certbot.timer"
    echo "   • View logs: journalctl -u certbot"
fi
echo ""
echo -e "${CYAN}4. Verify Auto-Renewal:${NC}"
if [ "$ACME_CLIENT" = "acme.sh" ]; then
    echo "   • Test renewal: /root/.acme.sh/acme.sh --renew -d $DOMAIN --force"
else
    echo "   • Test renewal: certbot renew --dry-run"
fi
echo ""
