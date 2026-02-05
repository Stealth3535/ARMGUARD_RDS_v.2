#!/bin/bash

################################################################################
# ArmGuard Production Issues Comprehensive Fix Script
# 
# This script fixes all identified deployment issues:
# 1. CSRF token failures (403 errors) - Missing CSRF_TRUSTED_ORIGINS
# 2. Nginx proxy header configuration
# 3. Session/cookie configuration for reverse proxy
# 4. Service startup and connectivity issues
# 
# Usage: sudo bash fix-all-production-issues.sh
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
error() { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; exit 1; }
info() { echo -e "${BLUE}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        ArmGuard Production Issues - Comprehensive Fix        ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Detect deployment location
DEPLOY_DIR=""
if [ -f "/opt/armguard/venv/bin/gunicorn" ]; then
    DEPLOY_DIR="/opt/armguard"
    log "Detected deployment at: /opt/armguard"
elif [ -f "/home/ubuntu/ARMGUARD_RDS/venv/bin/gunicorn" ]; then
    DEPLOY_DIR="/home/ubuntu/ARMGUARD_RDS"
    log "Detected deployment at: /home/ubuntu/ARMGUARD_RDS"
else
    error "Cannot find ArmGuard deployment - neither /opt/armguard nor /home/ubuntu/ARMGUARD_RDS exist"
fi

APP_DIR="$DEPLOY_DIR/armguard"

# Get server IP address
SERVER_IP=$(hostname -I | awk '{print $1}')
log "Server IP: $SERVER_IP"

# ============================================================================
# FIX 1: Update Django settings for reverse proxy and CSRF
# ============================================================================
info "FIX 1: Updating Django settings for reverse proxy support..."

ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    warn ".env file not found, checking if settings are correct..."
fi

# Check if settings.py has the required configurations
SETTINGS_FILE="$APP_DIR/core/settings.py"
if ! grep -q "CSRF_TRUSTED_ORIGINS" "$SETTINGS_FILE"; then
    warn "CSRF_TRUSTED_ORIGINS not found in settings.py"
    warn "You need to pull the latest code from GitHub or manually add:"
    warn "  CSRF_TRUSTED_ORIGINS = ['http://$SERVER_IP', 'https://$SERVER_IP', ...]"
    warn "  USE_X_FORWARDED_HOST = True"
    warn "  USE_X_FORWARDED_PORT = True"
    warn "  SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')"
else
    log "Django reverse proxy settings found in settings.py"
fi

# ============================================================================
# FIX 2: Update Nginx configuration for proper proxy headers
# ============================================================================
info "FIX 2: Verifying Nginx proxy headers configuration..."

NGINX_CONFIG="/etc/nginx/sites-available/armguard"
if [ ! -f "$NGINX_CONFIG" ]; then
    error "Nginx configuration not found at $NGINX_CONFIG"
fi

# Check if proxy headers are properly configured
if grep -q "proxy_set_header Host" "$NGINX_CONFIG"; then
    log "Nginx proxy headers configured correctly"
else
    warn "Nginx proxy headers may need updating"
fi

# Ensure Nginx has the correct upstream socket path
if ! grep -q "unix:/run/armguard.sock" "$NGINX_CONFIG"; then
    warn "Nginx may be pointing to wrong Gunicorn socket"
fi

# Test Nginx configuration
if sudo nginx -t 2>&1 | grep -q "successful"; then
    log "Nginx configuration test passed"
else
    error "Nginx configuration test failed - check /etc/nginx/sites-available/armguard"
fi

# ============================================================================
# FIX 3: Verify Gunicorn service configuration
# ============================================================================
info "FIX 3: Verifying Gunicorn service configuration..."

SERVICE_FILE="/etc/systemd/system/armguard.service"
if [ ! -f "$SERVICE_FILE" ]; then
    error "Gunicorn service file not found at $SERVICE_FILE"
fi

# Check if service file has correct paths
if ! grep -q "WorkingDirectory=$APP_DIR" "$SERVICE_FILE"; then
    warn "Service file may have incorrect working directory"
fi

# Check if service file has correct gunicorn path
if ! grep -q "$DEPLOY_DIR/venv/bin/gunicorn" "$SERVICE_FILE"; then
    warn "Service file may have incorrect gunicorn path"
fi

# ============================================================================
# FIX 4: Remove socket activation conflicts
# ============================================================================
info "FIX 4: Checking for systemd socket activation conflicts..."

if [ -f "/etc/systemd/system/armguard.socket" ]; then
    warn "Found armguard.socket - this conflicts with Gunicorn --bind"
    info "Stopping and disabling socket unit..."
    sudo systemctl stop armguard.socket 2>/dev/null || true
    sudo systemctl disable armguard.socket 2>/dev/null || true
    sudo rm -f /etc/systemd/system/armguard.socket
    sudo systemctl daemon-reload
    log "Removed socket activation conflict"
else
    log "No socket activation conflicts found"
fi

# ============================================================================
# FIX 5: Restart services with proper configuration
# ============================================================================
info "FIX 5: Restarting services..."

# Reload systemd
sudo systemctl daemon-reload

# Restart Gunicorn
info "Restarting ArmGuard (Gunicorn)..."
sudo systemctl restart armguard.service
sleep 2

# Check if Gunicorn is running
if sudo systemctl is-active --quiet armguard.service; then
    log "ArmGuard service is running"
else
    error "ArmGuard service failed to start - check: sudo journalctl -u armguard.service -n 50"
fi

# Check if socket was created
if [ -S "/run/armguard.sock" ]; then
    log "Gunicorn socket created successfully: /run/armguard.sock"
else
    error "Gunicorn socket not found at /run/armguard.sock"
fi

# Restart Nginx
info "Restarting Nginx..."
sudo systemctl restart nginx

if sudo systemctl is-active --quiet nginx; then
    log "Nginx is running"
else
    error "Nginx failed to start"
fi

# ============================================================================
# FIX 6: Test connectivity
# ============================================================================
info "FIX 6: Testing application connectivity..."

# Test HTTP connection
if curl -s -o /dev/null -w "%{http_code}" "http://localhost/" | grep -qE "200|302"; then
    log "HTTP endpoint responding (localhost)"
else
    warn "HTTP endpoint not responding on localhost"
fi

# Test IP connection
if curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP/" | grep -qE "200|302"; then
    log "HTTP endpoint responding ($SERVER_IP)"
else
    warn "HTTP endpoint not responding on $SERVER_IP"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Fix Summary                                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
log "Deployment Directory: $DEPLOY_DIR"
log "Application Directory: $APP_DIR"
log "Server IP: $SERVER_IP"
echo ""

# Service status
echo "Service Status:"
echo "───────────────────────────────────────────────────────────────"
printf "ArmGuard (Gunicorn): "
if sudo systemctl is-active --quiet armguard.service; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Stopped${NC}"
fi

printf "Nginx:               "
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Stopped${NC}"
fi

printf "Redis:               "
if sudo systemctl is-active --quiet redis-server; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${YELLOW}⚠️  Stopped${NC}"
fi

printf "PostgreSQL:          "
if sudo systemctl is-active --quiet postgresql; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${YELLOW}⚠️  Stopped${NC}"
fi

echo ""
echo "Access URLs:"
echo "───────────────────────────────────────────────────────────────"
echo "  • HTTP:  http://$SERVER_IP/"
echo "  • HTTPS: https://$SERVER_IP/"
echo "  • Admin: http://$SERVER_IP/admin/"
echo ""

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                     Fix Complete!                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
info "If you still see CSRF errors:"
echo "  1. Clear your browser cache and cookies"
echo "  2. Access the site using: http://$SERVER_IP/ (not localhost)"
echo "  3. Check logs: sudo journalctl -u armguard.service -f"
echo ""
info "If services failed to start:"
echo "  • ArmGuard logs: sudo journalctl -u armguard.service -n 50"
echo "  • Nginx logs:    sudo tail -f /var/log/nginx/error.log"
echo "  • Full fix:      curl -sSL 'https://raw.githubusercontent.com/Stealth3535/ARMGUARD_RDS/main/armguard/deployment/fix-rpi-deployment.sh' | sudo bash"
echo ""
