#!/bin/bash
# ArmGuard Security Test Suite
# Automated security scanning using OWASP ZAP and custom checks

set -e

# Configuration
TARGET_URL="${TARGET_URL:-https://nginx}"
ZAP_API_URL="${ZAP_API_URL:-http://zap:8080}"
REPORT_DIR="${REPORT_DIR:-/results/security}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ArmGuard Automated Security Testing Suite           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# =============================================================================
# OWASP ZAP Scanning
# =============================================================================

echo -e "${YELLOW}[1/5] Starting OWASP ZAP Security Scan...${NC}"

# Wait for ZAP to be ready
echo "  Waiting for ZAP to start..."
for i in {1..30}; do
    if curl -s "$ZAP_API_URL/JSON/core/view/version/" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ ZAP is ready${NC}"
        break
    fi
    sleep 2
done

# Spider the target
echo "  Spidering target..."
SPIDER_ID=$(curl -s "$ZAP_API_URL/JSON/spider/action/scan/?url=$TARGET_URL" | jq -r '.scan')
while [ "$(curl -s "$ZAP_API_URL/JSON/spider/view/status/?scanId=$SPIDER_ID" | jq -r '.status')" != "100" ]; do
    echo "    Spider progress: $(curl -s "$ZAP_API_URL/JSON/spider/view/status/?scanId=$SPIDER_ID" | jq -r '.status')%"
    sleep 5
done
echo -e "  ${GREEN}✓ Spider complete${NC}"

# Run active scan
echo "  Running active security scan..."
SCAN_ID=$(curl -s "$ZAP_API_URL/JSON/ascan/action/scan/?url=$TARGET_URL" | jq -r '.scan')
while [ "$(curl -s "$ZAP_API_URL/JSON/ascan/view/status/?scanId=$SCAN_ID" | jq -r '.status')" != "100" ]; do
    PROGRESS=$(curl -s "$ZAP_API_URL/JSON/ascan/view/status/?scanId=$SCAN_ID" | jq -r '.status')
    echo "    Scan progress: $PROGRESS%"
    sleep 10
done
echo -e "  ${GREEN}✓ Active scan complete${NC}"

# Generate reports
echo "  Generating ZAP reports..."
curl -s "$ZAP_API_URL/OTHER/core/other/htmlreport/" > "$REPORT_DIR/zap_report_$TIMESTAMP.html"
curl -s "$ZAP_API_URL/JSON/core/view/alerts/" > "$REPORT_DIR/zap_alerts_$TIMESTAMP.json"

# Count vulnerabilities
HIGH_COUNT=$(curl -s "$ZAP_API_URL/JSON/core/view/alerts/" | jq '[.alerts[] | select(.risk == "High")] | length')
MEDIUM_COUNT=$(curl -s "$ZAP_API_URL/JSON/core/view/alerts/" | jq '[.alerts[] | select(.risk == "Medium")] | length')
LOW_COUNT=$(curl -s "$ZAP_API_URL/JSON/core/view/alerts/" | jq '[.alerts[] | select(.risk == "Low")] | length')
INFO_COUNT=$(curl -s "$ZAP_API_URL/JSON/core/view/alerts/" | jq '[.alerts[] | select(.risk == "Informational")] | length')

echo -e "  ${GREEN}✓ ZAP scan complete${NC}"
echo -e "    High: ${RED}$HIGH_COUNT${NC}"
echo -e "    Medium: ${YELLOW}$MEDIUM_COUNT${NC}"
echo -e "    Low: ${GREEN}$LOW_COUNT${NC}"
echo -e "    Info: $INFO_COUNT"

# =============================================================================
# Security Header Check
# =============================================================================

echo ""
echo -e "${YELLOW}[2/5] Checking Security Headers...${NC}"

HEADERS_REPORT="$REPORT_DIR/headers_report_$TIMESTAMP.txt"

check_header() {
    local header=$1
    local value=$(curl -sI -k "$TARGET_URL" | grep -i "^$header:" | cut -d: -f2- | tr -d '\r')
    if [ -n "$value" ]; then
        echo -e "  ${GREEN}✓${NC} $header:$value" | tee -a "$HEADERS_REPORT"
        return 0
    else
        echo -e "  ${RED}✗${NC} $header: MISSING" | tee -a "$HEADERS_REPORT"
        return 1
    fi
}

echo "Security Header Check - $TIMESTAMP" > "$HEADERS_REPORT"
echo "=================================" >> "$HEADERS_REPORT"

HEADERS_PASS=0
HEADERS_FAIL=0

for header in "X-Frame-Options" "X-Content-Type-Options" "X-XSS-Protection" \
              "Strict-Transport-Security" "Content-Security-Policy" \
              "Referrer-Policy" "Permissions-Policy"; do
    if check_header "$header"; then
        ((HEADERS_PASS++))
    else
        ((HEADERS_FAIL++))
    fi
done

echo ""
echo -e "  Headers: ${GREEN}$HEADERS_PASS passed${NC}, ${RED}$HEADERS_FAIL failed${NC}"

# =============================================================================
# SSL/TLS Configuration Check
# =============================================================================

echo ""
echo -e "${YELLOW}[3/5] Checking SSL/TLS Configuration...${NC}"

SSL_REPORT="$REPORT_DIR/ssl_report_$TIMESTAMP.txt"

echo "SSL/TLS Configuration Check - $TIMESTAMP" > "$SSL_REPORT"
echo "=========================================" >> "$SSL_REPORT"

# Check supported protocols
echo "  Checking TLS protocols..."
for proto in "ssl3" "tls1" "tls1_1" "tls1_2" "tls1_3"; do
    if echo | openssl s_client -connect nginx:443 -$proto 2>/dev/null | grep -q "CONNECTED"; then
        if [ "$proto" = "tls1_2" ] || [ "$proto" = "tls1_3" ]; then
            echo -e "  ${GREEN}✓${NC} $proto: Supported" | tee -a "$SSL_REPORT"
        else
            echo -e "  ${RED}✗${NC} $proto: Supported (INSECURE)" | tee -a "$SSL_REPORT"
        fi
    else
        if [ "$proto" = "tls1_2" ] || [ "$proto" = "tls1_3" ]; then
            echo -e "  ${YELLOW}?${NC} $proto: Not supported" | tee -a "$SSL_REPORT"
        else
            echo -e "  ${GREEN}✓${NC} $proto: Not supported (Good)" | tee -a "$SSL_REPORT"
        fi
    fi
done

# Check certificate
echo "  Checking certificate..."
CERT_INFO=$(echo | openssl s_client -connect nginx:443 2>/dev/null | openssl x509 -noout -dates 2>/dev/null)
echo "$CERT_INFO" >> "$SSL_REPORT"

# =============================================================================
# Authentication Security Tests
# =============================================================================

echo ""
echo -e "${YELLOW}[4/5] Testing Authentication Security...${NC}"

AUTH_REPORT="$REPORT_DIR/auth_report_$TIMESTAMP.txt"

echo "Authentication Security Check - $TIMESTAMP" > "$AUTH_REPORT"
echo "===========================================" >> "$AUTH_REPORT"

# Test brute force protection
echo "  Testing brute force protection..."
RATE_LIMITED=false
for i in {1..10}; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -k -X POST "$TARGET_URL/login/" \
        -d "username=test&password=wrong$i" -H "Content-Type: application/x-www-form-urlencoded")
    if [ "$RESPONSE" = "429" ]; then
        echo -e "  ${GREEN}✓${NC} Rate limiting active (triggered at attempt $i)" | tee -a "$AUTH_REPORT"
        RATE_LIMITED=true
        break
    fi
    sleep 0.5
done

if [ "$RATE_LIMITED" = false ]; then
    echo -e "  ${YELLOW}?${NC} Rate limiting may not be active (10 attempts allowed)" | tee -a "$AUTH_REPORT"
fi

# Test session cookie security
echo "  Testing session cookie security..."
COOKIES=$(curl -s -k -c - "$TARGET_URL/login/" 2>/dev/null)
if echo "$COOKIES" | grep -q "HttpOnly"; then
    echo -e "  ${GREEN}✓${NC} HttpOnly flag set" | tee -a "$AUTH_REPORT"
else
    echo -e "  ${RED}✗${NC} HttpOnly flag missing" | tee -a "$AUTH_REPORT"
fi

if echo "$COOKIES" | grep -q "Secure"; then
    echo -e "  ${GREEN}✓${NC} Secure flag set" | tee -a "$AUTH_REPORT"
else
    echo -e "  ${RED}✗${NC} Secure flag missing" | tee -a "$AUTH_REPORT"
fi

# =============================================================================
# Common Vulnerability Checks
# =============================================================================

echo ""
echo -e "${YELLOW}[5/5] Running Common Vulnerability Checks...${NC}"

VULN_REPORT="$REPORT_DIR/vuln_report_$TIMESTAMP.txt"

echo "Common Vulnerability Check - $TIMESTAMP" > "$VULN_REPORT"
echo "========================================" >> "$VULN_REPORT"

# SQL Injection test
echo "  Testing SQL injection..."
SQL_PAYLOADS=("'" "1' OR '1'='1" "1; DROP TABLE users--" "' UNION SELECT * FROM users--")
SQL_VULN=false
for payload in "${SQL_PAYLOADS[@]}"; do
    RESPONSE=$(curl -s -k "$TARGET_URL/personnel/search/?q=$payload" -w "%{http_code}" -o /dev/null)
    if [ "$RESPONSE" = "500" ]; then
        echo -e "  ${RED}✗${NC} Possible SQL injection with: $payload" | tee -a "$VULN_REPORT"
        SQL_VULN=true
    fi
done
if [ "$SQL_VULN" = false ]; then
    echo -e "  ${GREEN}✓${NC} No obvious SQL injection vulnerabilities" | tee -a "$VULN_REPORT"
fi

# XSS test
echo "  Testing XSS..."
XSS_PAYLOAD="<script>alert('xss')</script>"
RESPONSE=$(curl -s -k "$TARGET_URL/personnel/search/?q=$XSS_PAYLOAD")
if echo "$RESPONSE" | grep -q "<script>alert"; then
    echo -e "  ${RED}✗${NC} Possible XSS vulnerability" | tee -a "$VULN_REPORT"
else
    echo -e "  ${GREEN}✓${NC} XSS payload properly escaped" | tee -a "$VULN_REPORT"
fi

# Path traversal test
echo "  Testing path traversal..."
TRAVERSAL_PAYLOAD="../../../etc/passwd"
RESPONSE=$(curl -s -k -o /dev/null -w "%{http_code}" "$TARGET_URL/media/$TRAVERSAL_PAYLOAD")
if [ "$RESPONSE" = "200" ]; then
    echo -e "  ${RED}✗${NC} Possible path traversal vulnerability" | tee -a "$VULN_REPORT"
else
    echo -e "  ${GREEN}✓${NC} Path traversal blocked" | tee -a "$VULN_REPORT"
fi

# Server information disclosure
echo "  Testing information disclosure..."
SERVER_HEADER=$(curl -sI -k "$TARGET_URL" | grep -i "^server:" | cut -d: -f2-)
if echo "$SERVER_HEADER" | grep -qE "[0-9]+\.[0-9]+"; then
    echo -e "  ${YELLOW}!${NC} Server version disclosed: $SERVER_HEADER" | tee -a "$VULN_REPORT"
else
    echo -e "  ${GREEN}✓${NC} Server version not disclosed" | tee -a "$VULN_REPORT"
fi

# =============================================================================
# Generate Summary Report
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Security Test Summary${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

SUMMARY_REPORT="$REPORT_DIR/security_summary_$TIMESTAMP.md"

cat > "$SUMMARY_REPORT" << EOF
# ArmGuard Security Test Report

**Date:** $(date)
**Target:** $TARGET_URL

## Executive Summary

### OWASP ZAP Scan Results
| Severity | Count |
|----------|-------|
| High | $HIGH_COUNT |
| Medium | $MEDIUM_COUNT |
| Low | $LOW_COUNT |
| Informational | $INFO_COUNT |

### Security Headers
- Passed: $HEADERS_PASS
- Failed: $HEADERS_FAIL

### Overall Risk Assessment
$(if [ "$HIGH_COUNT" -gt 0 ]; then echo "⚠️ **HIGH RISK** - Critical vulnerabilities found"; elif [ "$MEDIUM_COUNT" -gt 0 ]; then echo "⚠️ **MEDIUM RISK** - Some vulnerabilities require attention"; else echo "✅ **LOW RISK** - No critical issues found"; fi)

## Detailed Reports
- ZAP HTML Report: zap_report_$TIMESTAMP.html
- ZAP Alerts JSON: zap_alerts_$TIMESTAMP.json
- Headers Report: headers_report_$TIMESTAMP.txt
- SSL Report: ssl_report_$TIMESTAMP.txt
- Auth Report: auth_report_$TIMESTAMP.txt
- Vulnerability Report: vuln_report_$TIMESTAMP.txt

## Recommendations
1. Address all HIGH severity findings immediately
2. Review and fix MEDIUM severity issues within 1 week
3. Consider LOW severity issues for future improvements
4. Ensure all security headers are properly configured
5. Keep all dependencies updated

---
*Generated by ArmGuard Security Test Suite*
EOF

echo ""
echo -e "${GREEN}Security testing complete!${NC}"
echo "Reports saved to: $REPORT_DIR"
echo ""
echo "Summary:"
echo -e "  ZAP High: ${RED}$HIGH_COUNT${NC}"
echo -e "  ZAP Medium: ${YELLOW}$MEDIUM_COUNT${NC}"
echo -e "  Headers: ${GREEN}$HEADERS_PASS passed${NC}, ${RED}$HEADERS_FAIL failed${NC}"
