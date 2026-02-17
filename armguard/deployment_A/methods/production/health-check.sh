#!/bin/bash

################################################################################
# ArmGuard Health Check Script
# 
# Comprehensive health check for deployed application
# Usage: sudo bash deployment/health-check.sh
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and source config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
fi

# Configuration (can be overridden by config.sh)
PROJECT_DIR="${PROJECT_DIR:-/var/www/armguard}"
SERVICE_NAME="${SERVICE_NAME:-gunicorn-armguard}"
NGINX_SERVICE="nginx"
GUNICORN_BIND_HOST="${GUNICORN_BIND_HOST:-127.0.0.1}"
GUNICORN_BIND_PORT="${GUNICORN_BIND_PORT:-18000}"
DOMAIN="${1:-${DEFAULT_DOMAIN:-localhost}}"
SERVER_IP="$(hostname -I | awk '{print $1}')"
CONNECTIVITY_HOST="${DOMAIN}"
if [ "$#" -eq 0 ] && [[ "$DOMAIN" =~ \.local$ ]]; then
    CONNECTIVITY_HOST="${SERVER_IP:-127.0.0.1}"
fi
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNED=0

# Print banner
echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              ArmGuard Health Check Report                 ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Timestamp: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
echo ""

# Helper functions
check_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((CHECKS_FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((CHECKS_WARNED++))
}

# 1. System Health
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}System Health${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "Disk space: ${DISK_USAGE}% used"
elif [ "$DISK_USAGE" -lt 90 ]; then
    check_warn "Disk space: ${DISK_USAGE}% used (getting high)"
else
    check_fail "Disk space: ${DISK_USAGE}% used (critically high)"
fi

# Memory
MEMORY_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3*100/$2}')
if [ "$MEMORY_USAGE" -lt 80 ]; then
    check_pass "Memory usage: ${MEMORY_USAGE}%"
elif [ "$MEMORY_USAGE" -lt 90 ]; then
    check_warn "Memory usage: ${MEMORY_USAGE}% (getting high)"
else
    check_fail "Memory usage: ${MEMORY_USAGE}% (critically high)"
fi

# CPU Load
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
CPU_CORES=$(nproc)
CPU_THRESHOLD=$(echo "$CPU_CORES * 2" | bc)
if (( $(echo "$CPU_LOAD < $CPU_THRESHOLD" | bc -l) )); then
    check_pass "CPU load: ${CPU_LOAD} (${CPU_CORES} cores)"
else
    check_warn "CPU load: ${CPU_LOAD} (high for ${CPU_CORES} cores)"
fi

# 2. Service Status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Service Status${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Gunicorn service
if systemctl is-active --quiet $SERVICE_NAME; then
    check_pass "Gunicorn service is running"
    
    # Check if service is enabled
    if systemctl is-enabled --quiet $SERVICE_NAME; then
        check_pass "Gunicorn service is enabled (auto-start)"
    else
        check_warn "Gunicorn service not enabled for auto-start"
    fi
    
    # Check service uptime
    UPTIME=$(systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp --value)
    if [ -n "$UPTIME" ]; then
        echo -e "  ${CYAN}Started: $UPTIME${NC}"
    fi
else
    check_fail "Gunicorn service is NOT running"
fi

# Nginx service
if systemctl is-active --quiet $NGINX_SERVICE; then
    check_pass "Nginx service is running"
    
    if systemctl is-enabled --quiet $NGINX_SERVICE; then
        check_pass "Nginx service is enabled (auto-start)"
    else
        check_warn "Nginx service not enabled for auto-start"
    fi
else
    check_fail "Nginx service is NOT running"
fi

# 3. Network & Connectivity
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Network & Connectivity${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check ports
if netstat -tuln | grep -q ":80 "; then
    check_pass "Port 80 (HTTP) is listening"
else
    check_fail "Port 80 (HTTP) is NOT listening"
fi

if netstat -tuln | grep -q ":443 "; then
    check_pass "Port 443 (HTTPS) is listening"
else
    check_warn "Port 443 (HTTPS) is NOT listening (SSL may not be configured)"
fi

# Check Gunicorn backend (socket or localhost TCP)
if [ -S "/run/gunicorn-armguard/gunicorn.sock" ] || [ -S "/run/gunicorn-armguard.sock" ] || netstat -tuln | grep -q "${GUNICORN_BIND_HOST}:${GUNICORN_BIND_PORT}" || netstat -tuln | grep -q "127.0.0.1:8000"; then
    check_pass "Gunicorn backend is available"
else
    check_fail "Gunicorn backend NOT found"
fi

# HTTP connectivity test
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${CONNECTIVITY_HOST}" 2>/dev/null || true)
HTTP_STATUS=${HTTP_STATUS:-000}
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
    check_pass "HTTP endpoint responding via ${CONNECTIVITY_HOST} (status: $HTTP_STATUS)"
elif [ "$HTTP_STATUS" = "000" ]; then
    check_fail "HTTP endpoint not reachable via ${CONNECTIVITY_HOST}"
else
    check_warn "HTTP endpoint via ${CONNECTIVITY_HOST} responding with status: $HTTP_STATUS"
fi

# HTTPS connectivity test (if configured)
if netstat -tuln | grep -q ":443 "; then
    HTTPS_STATUS=$(curl -k -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "https://${CONNECTIVITY_HOST}" 2>/dev/null || true)
    HTTPS_STATUS=${HTTPS_STATUS:-000}
    if [ "$HTTPS_STATUS" = "200" ] || [ "$HTTPS_STATUS" = "302" ]; then
        check_pass "HTTPS endpoint responding via ${CONNECTIVITY_HOST} (status: $HTTPS_STATUS)"
    elif [ "$HTTPS_STATUS" = "000" ]; then
        check_fail "HTTPS endpoint not reachable via ${CONNECTIVITY_HOST}"
    else
        check_warn "HTTPS endpoint via ${CONNECTIVITY_HOST} responding with status: $HTTPS_STATUS"
    fi
fi

# 4. Application Files
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Application Files & Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Project directory
if [ -d "$PROJECT_DIR" ]; then
    check_pass "Project directory exists"
else
    check_fail "Project directory NOT found"
fi

# manage.py
if [ -f "$PROJECT_DIR/manage.py" ]; then
    check_pass "Django manage.py found"
else
    check_fail "Django manage.py NOT found"
fi

# Virtual environment
if [ -d "$PROJECT_DIR/.venv" ]; then
    check_pass "Virtual environment exists"
else
    check_fail "Virtual environment NOT found"
fi

# Database
if [ -f "$PROJECT_DIR/db.sqlite3" ]; then
    DB_SIZE=$(du -h "$PROJECT_DIR/db.sqlite3" | cut -f1)
    check_pass "Database file exists (Size: $DB_SIZE)"
else
    check_warn "Database file NOT found (may use PostgreSQL)"
fi

# Static files
if [ -d "$PROJECT_DIR/staticfiles" ]; then
    STATIC_COUNT=$(find "$PROJECT_DIR/staticfiles" -type f 2>/dev/null | wc -l)
    if [ "$STATIC_COUNT" -gt 0 ]; then
        check_pass "Static files collected ($STATIC_COUNT files)"
    else
        check_warn "Static files directory empty"
    fi
else
    check_fail "Static files directory NOT found"
fi

# Environment file
if [ -f "$PROJECT_DIR/.env" ]; then
    check_pass "Environment file (.env) exists"
else
    check_warn "Environment file (.env) NOT found"
fi

# 5. Logs & Errors
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Logs & Recent Errors${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Check for recent errors in Gunicorn logs
if [ -f "/var/log/armguard/error.log" ]; then
    ERROR_COUNT=$(grep -i "error" /var/log/armguard/error.log | tail -100 | wc -l)
    if [ "$ERROR_COUNT" -eq 0 ]; then
        check_pass "No recent errors in Gunicorn logs"
    elif [ "$ERROR_COUNT" -lt 10 ]; then
        check_warn "Found $ERROR_COUNT recent errors in Gunicorn logs"
    else
        check_fail "Found $ERROR_COUNT recent errors in Gunicorn logs"
    fi
else
    check_warn "Gunicorn error log not found"
fi

# Check systemd journal for service errors
if command -v journalctl &> /dev/null; then
    JOURNAL_ERRORS=$(journalctl -u $SERVICE_NAME --since "1 hour ago" -p err --no-pager -q | wc -l)
    if [ "$JOURNAL_ERRORS" -eq 0 ]; then
        check_pass "No service errors in last hour"
    else
        check_warn "Found $JOURNAL_ERRORS service errors in last hour"
    fi
fi

# 6. Security
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Security Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Firewall status
if command -v ufw &> /dev/null; then
    if ufw status | grep -q "Status: active"; then
        check_pass "Firewall (UFW) is active"
    else
        check_warn "Firewall (UFW) is inactive"
    fi
else
    check_warn "UFW not installed"
fi

# File permissions
if [ -f "$PROJECT_DIR/.env" ]; then
    ENV_PERMS=$(stat -c "%a" "$PROJECT_DIR/.env" 2>/dev/null)
    if [ "$ENV_PERMS" = "600" ] || [ "$ENV_PERMS" = "640" ]; then
        check_pass "Environment file has secure permissions ($ENV_PERMS)"
    else
        check_warn "Environment file permissions may be too open ($ENV_PERMS)"
    fi
fi

# 7. Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Health Check Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

TOTAL_CHECKS=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNED))
echo -e "${GREEN}✓ Passed:  $CHECKS_PASSED${NC}"
echo -e "${YELLOW}⚠ Warnings: $CHECKS_WARNED${NC}"
echo -e "${RED}✗ Failed:   $CHECKS_FAILED${NC}"
echo -e "${CYAN}  Total:    $TOTAL_CHECKS${NC}"
echo ""

# Overall health status
if [ "$CHECKS_FAILED" -eq 0 ] && [ "$CHECKS_WARNED" -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              ✓ SYSTEM HEALTHY - ALL CHECKS PASSED         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
elif [ "$CHECKS_FAILED" -eq 0 ]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║        ⚠ SYSTEM OPERATIONAL - MINOR WARNINGS FOUND        ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║           ✗ SYSTEM ISSUES DETECTED - ACTION NEEDED        ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    exit 1
fi
