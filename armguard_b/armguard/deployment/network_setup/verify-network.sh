#!/bin/bash

################################################################################
# ArmGuard - Network Verification Script
# Test both LAN and WAN network configurations
################################################################################

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
fi

# Configuration (can be overridden by config.sh or environment)
LAN_INTERFACE="${LAN_INTERFACE:-eth1}"
WAN_INTERFACE="${WAN_INTERFACE:-eth0}"
SERVER_LAN_IP="${SERVER_LAN_IP:-192.168.10.1}"
ARMORY_PC_IP="${ARMORY_PC_IP:-192.168.10.2}"
DOMAIN="${DOMAIN:-login.yourdomain.com}"

TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║         ArmGuard Network Verification                     ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Helper functions
test_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

test_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Test 1: Network Interfaces
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 1: Network Interfaces${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if ip link show $LAN_INTERFACE &> /dev/null; then
    test_pass "LAN interface $LAN_INTERFACE exists"
    
    if ip addr show $LAN_INTERFACE | grep -q "$SERVER_LAN_IP"; then
        test_pass "LAN IP $SERVER_LAN_IP configured"
    else
        test_fail "LAN IP $SERVER_LAN_IP not configured"
    fi
else
    test_fail "LAN interface $LAN_INTERFACE not found"
fi

if ip link show $WAN_INTERFACE &> /dev/null; then
    test_pass "WAN interface $WAN_INTERFACE exists"
else
    test_fail "WAN interface $WAN_INTERFACE not found"
fi

# Test 2: SSL Certificates
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 2: SSL Certificates${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# LAN certificate
if [ -f "/etc/ssl/armguard/lan/armguard-lan-cert.pem" ]; then
    test_pass "LAN SSL certificate exists"
    
    # Check certificate validity
    if openssl x509 -in /etc/ssl/armguard/lan/armguard-lan-cert.pem -noout -checkend 86400 &>/dev/null; then
        test_pass "LAN certificate is valid"
    else
        test_warn "LAN certificate expires soon or is expired"
    fi
else
    test_fail "LAN SSL certificate not found"
fi

# WAN certificate
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    test_pass "WAN SSL certificate exists"
    
    # Check certificate validity
    if openssl x509 -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem -noout -checkend 604800 &>/dev/null; then
        test_pass "WAN certificate valid for at least 7 days"
    else
        test_warn "WAN certificate expires soon or is expired"
    fi
else
    test_fail "WAN SSL certificate not found"
fi

# Test 3: Nginx Configuration
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 3: Nginx Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if nginx -t &>/dev/null; then
    test_pass "Nginx configuration is valid"
else
    test_fail "Nginx configuration has errors"
fi

# Check LAN config
if [ -f "/etc/nginx/sites-enabled/armguard-lan" ]; then
    test_pass "LAN Nginx configuration enabled"
else
    test_fail "LAN Nginx configuration not enabled"
fi

# Check WAN config
if [ -f "/etc/nginx/sites-enabled/armguard-wan" ]; then
    test_pass "WAN Nginx configuration enabled"
else
    test_fail "WAN Nginx configuration not enabled"
fi

# Check if Nginx is running
if systemctl is-active --quiet nginx; then
    test_pass "Nginx service is running"
else
    test_fail "Nginx service is not running"
fi

# Test 4: Firewall Rules
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 4: Firewall Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        test_pass "UFW firewall is active"
        
        # Check WAN rules
        if ufw status | grep -q "443.*ALLOW"; then
            test_pass "WAN HTTPS (443) allowed"
        else
            test_fail "WAN HTTPS (443) not allowed"
        fi
        
        if ufw status | grep -q "80.*ALLOW"; then
            test_pass "WAN HTTP (80) allowed"
        else
            test_fail "WAN HTTP (80) not allowed"
        fi
    else
        test_fail "UFW firewall is not active"
    fi
else
    test_warn "UFW not installed"
fi

# Check iptables for LAN isolation
if iptables -L FORWARD | grep -q "DROP.*192.168.10"; then
    test_pass "LAN internet access blocked"
else
    test_warn "LAN internet isolation not detected"
fi

# Test 5: Port Accessibility
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 5: Port Accessibility${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check LAN port
if netstat -tuln | grep -q ":8443"; then
    test_pass "LAN HTTPS port 8443 is listening"
else
    test_fail "LAN HTTPS port 8443 not listening"
fi

# Check WAN port
if netstat -tuln | grep -q ":443"; then
    test_pass "WAN HTTPS port 443 is listening"
else
    test_fail "WAN HTTPS port 443 not listening"
fi

if netstat -tuln | grep -q ":80"; then
    test_pass "WAN HTTP port 80 is listening"
else
    test_fail "WAN HTTP port 80 not listening"
fi

# Test 6: Connectivity Tests
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 6: Connectivity Tests${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Test LAN HTTPS
echo -e "${YELLOW}Testing LAN HTTPS...${NC}"
LAN_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" https://$SERVER_LAN_IP:8443 2>/dev/null || echo "000")
if [ "$LAN_STATUS" != "000" ]; then
    test_pass "LAN HTTPS responding (status: $LAN_STATUS)"
else
    test_fail "LAN HTTPS not responding"
fi

# Test WAN HTTPS (if domain resolves)
echo -e "${YELLOW}Testing WAN HTTPS...${NC}"
if host $DOMAIN &>/dev/null; then
    WAN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN 2>/dev/null || echo "000")
    if [ "$WAN_STATUS" != "000" ]; then
        test_pass "WAN HTTPS responding (status: $WAN_STATUS)"
    else
        test_fail "WAN HTTPS not responding"
    fi
else
    test_warn "WAN domain $DOMAIN does not resolve (DNS not configured)"
fi

# Test 7: Logging
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 7: Logging Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check LAN logs
if [ -f "/var/log/nginx/armguard_lan_access.log" ]; then
    test_pass "LAN access log configured"
else
    test_fail "LAN access log not found"
fi

if [ -f "/var/log/nginx/armguard_lan_error.log" ]; then
    test_pass "LAN error log configured"
else
    test_fail "LAN error log not found"
fi

# Check WAN logs
if [ -f "/var/log/nginx/armguard_wan_access.log" ]; then
    test_pass "WAN access log configured"
else
    test_fail "WAN access log not found"
fi

if [ -f "/var/log/nginx/armguard_wan_error.log" ]; then
    test_pass "WAN error log configured"
else
    test_fail "WAN error log not found"
fi

# Test 8: Auto-Renewal
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Test 8: Certificate Auto-Renewal${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

if [ -d "/root/.acme.sh" ]; then
    if crontab -l | grep -q "acme.sh"; then
        test_pass "acme.sh auto-renewal configured"
    else
        test_warn "acme.sh installed but cron not found"
    fi
elif command -v certbot &> /dev/null; then
    if systemctl is-enabled certbot.timer &>/dev/null; then
        test_pass "certbot auto-renewal configured"
    else
        test_fail "certbot installed but timer not enabled"
    fi
else
    test_warn "No ACME client found"
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Verification Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
echo -e "${GREEN}✓ Passed:  $TESTS_PASSED${NC}"
echo -e "${RED}✗ Failed:   $TESTS_FAILED${NC}"
echo -e "${CYAN}  Total:    $TOTAL_TESTS${NC}"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║         ✓ ALL TESTS PASSED - Network Ready!               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    
    echo ""
    echo -e "${CYAN}Access Information:${NC}"
    echo ""
    echo -e "${YELLOW}LAN Network (Armory PC):${NC}"
    echo "  URL:      https://$SERVER_LAN_IP:8443"
    echo "  Access:   $ARMORY_PC_IP only"
    echo "  Features: Full inventory, admin, transactions"
    echo ""
    echo -e "${YELLOW}WAN Network (Personnel):${NC}"
    echo "  URL:      https://$DOMAIN"
    echo "  Access:   Public internet"
    echo "  Features: Personnel login, profile, dashboard only"
    echo ""
    
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║         ✗ TESTS FAILED - Review Configuration             ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    
    echo ""
    echo -e "${YELLOW}Troubleshooting Steps:${NC}"
    echo "  1. Review failed tests above"
    echo "  2. Check Nginx: sudo nginx -t"
    echo "  3. Check firewall: sudo ufw status verbose"
    echo "  4. Check services: sudo systemctl status nginx"
    echo "  5. Review logs: sudo tail -f /var/log/nginx/error.log"
    echo ""
    
    exit 1
fi
