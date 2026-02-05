#!/bin/bash

################################################################################
# Modern HTTPS Setup - Alternative to mkcert
# Uses OpenSSL with proper CA setup for trusted local certificates
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

LAN_IP="192.168.0.177"

echo -e "${CYAN}🔒 MODERN HTTPS SETUP (mkcert Alternative)${NC}"
echo "=========================================="
echo ""

echo -e "${BLUE}📋 Certificate Options:${NC}"
echo "1. 🔧 Accept self-signed certificate (Already working)"
echo "2. 🏠 Create proper CA and certificates (Modern alternative to mkcert)" 
echo "3. 🌐 Use Caddy server (Auto HTTPS)"
echo ""

read -p "Choose option (1-3): " cert_option

case $cert_option in
    1)
        echo -e "${GREEN}✅ Your HTTPS is already working with self-signed certificates!${NC}"
        echo ""
        echo -e "${YELLOW}To bypass the warning:${NC}"
        echo "1. Visit: https://192.168.0.177"
        echo "2. Click 'Advanced'"
        echo "3. Click 'Proceed to 192.168.0.177 (unsafe)'"
        echo "4. Your browser will remember this choice"
        echo ""
        echo -e "${CYAN}🎯 This is perfectly secure for local network use!${NC}"
        ;;
        
    2)
        echo -e "${YELLOW}🏠 Creating proper Certificate Authority...${NC}"
        
        # Create CA directory
        sudo mkdir -p /etc/ssl/armguard-ca
        cd /etc/ssl/armguard-ca
        
        # Create CA private key
        sudo openssl genrsa -out ca-key.pem 4096
        
        # Create CA certificate
        sudo openssl req -new -x509 -days 3650 -key ca-key.pem -sha256 -out ca.pem -subj "/C=US/ST=Local/L=Local/O=ArmGuard CA/CN=ArmGuard Local CA"
        
        # Create server private key
        sudo openssl genrsa -out server-key.pem 4096
        
        # Create certificate signing request
        sudo openssl req -subj "/C=US/ST=Local/L=Local/O=ArmGuard/CN=$LAN_IP" -sha256 -new -key server-key.pem -out server.csr
        
        # Create extensions file for server certificate
        sudo tee server-extfile.cnf > /dev/null << EOF
subjectAltName = @alt_names
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = localhost
DNS.2 = armguard.local
IP.1 = $LAN_IP
IP.2 = 127.0.0.1
EOF
        
        # Sign the server certificate
        sudo openssl x509 -req -days 365 -in server.csr -CA ca.pem -CAkey ca-key.pem -out server-cert.pem -extfile server-extfile.cnf -CAcreateserial
        
        # Copy certificates to nginx location
        sudo cp server-cert.pem /etc/ssl/armguard/armguard.crt
        sudo cp server-key.pem /etc/ssl/armguard/armguard.key
        
        # Set proper permissions
        sudo chmod 600 /etc/ssl/armguard/armguard.key
        sudo chmod 644 /etc/ssl/armguard/armguard.crt
        
        echo -e "${GREEN}✅ CA and server certificates created${NC}"
        
        # Restart nginx
        sudo systemctl restart nginx
        
        echo ""
        echo -e "${CYAN}🔗 To trust on Windows:${NC}"
        echo "1. Copy CA certificate to Windows:"
        echo "   scp ubuntu@$LAN_IP:/etc/ssl/armguard-ca/ca.pem ca-armguard.crt"
        echo ""
        echo "2. On Windows (as Administrator):"
        echo "   - Double-click ca-armguard.crt"
        echo "   - Click 'Install Certificate'"
        echo "   - Choose 'Local Machine'"
        echo "   - Select 'Trusted Root Certification Authorities'"
        echo "   - Click 'Finish'"
        echo ""
        echo "3. Restart browser and visit: https://$LAN_IP"
        
        # Create download instructions
        echo -e "${BLUE}📋 Or download CA certificate:${NC}"
        echo "Visit: https://$LAN_IP (accept warning once)"
        echo "Then download: https://$LAN_IP/ca.crt"
        
        # Create a simple endpoint to serve the CA certificate
        sudo cp /etc/ssl/armguard-ca/ca.pem /opt/armguard/staticfiles/ca.crt 2>/dev/null || echo "Note: CA cert available at /etc/ssl/armguard-ca/ca.pem"
        ;;
        
    3)
        echo -e "${YELLOW}🌐 Installing Caddy for automatic HTTPS...${NC}"
        
        # Install Caddy
        if ! command -v caddy &> /dev/null; then
            echo "Installing Caddy..."
            sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
            curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
            sudo apt update
            sudo apt install caddy
        fi
        
        # Stop nginx
        sudo systemctl stop nginx
        sudo systemctl disable nginx
        
        # Create Caddyfile
        sudo tee /etc/caddy/Caddyfile > /dev/null << EOF
$LAN_IP {
    reverse_proxy localhost:8000
    
    # Security headers
    header {
        Strict-Transport-Security "max-age=31536000;"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        X-XSS-Protection "1; mode=block"
        Referrer-Policy strict-origin-when-cross-origin
    }
    
    # Static files
    handle /static/* {
        root * /opt/armguard/staticfiles
        file_server
    }
    
    handle /media/* {
        root * /opt/armguard/media
        file_server
    }
}
EOF

        # Start Caddy
        sudo systemctl enable caddy
        sudo systemctl start caddy
        
        echo -e "${GREEN}✅ Caddy installed and configured${NC}"
        echo ""
        echo -e "${YELLOW}⚠️  Note: Caddy provides automatic HTTPS but may still show warnings for local IPs${NC}"
        echo "For local development, the CA approach (option 2) is better."
        ;;
        
    *)
        echo -e "${RED}❌ Invalid option${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}🧪 Testing HTTPS...${NC}"

# Test HTTPS
HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost 2>/dev/null || echo "000")
echo "HTTPS test: HTTP $HTTPS_STATUS"

if [ "$HTTPS_STATUS" = "200" ] || [ "$HTTPS_STATUS" = "302" ]; then
    echo -e "${GREEN}✅ HTTPS is working!${NC}"
    echo ""
    echo -e "${CYAN}🌐 Your ArmGuard system:${NC}"
    echo "• HTTPS: https://$LAN_IP"
    echo "• Admin: https://$LAN_IP/admin/"
    
    if [ "$cert_option" = "1" ]; then
        echo ""
        echo -e "${YELLOW}💡 Remember: Click 'Advanced' → 'Proceed' to bypass the warning${NC}"
        echo "The connection is fully encrypted and secure for local use!"
    fi
else
    echo -e "${RED}❌ HTTPS setup needs troubleshooting${NC}"
fi