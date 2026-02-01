#!/bin/bash
# ArmGuard Complete Test Suite Runner
# Executes all tests and generates consolidated report

set -e

# Configuration
REPORT_DIR="./test-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Banner
echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║            █████╗ ██████╗ ███╗   ███╗ ██████╗ ██╗   ██╗ █████╗   ║"
echo "║           ██╔══██╗██╔══██╗████╗ ████║██╔════╝ ██║   ██║██╔══██╗  ║"
echo "║           ███████║██████╔╝██╔████╔██║██║  ███╗██║   ██║███████║  ║"
echo "║           ██╔══██║██╔══██╗██║╚██╔╝██║██║   ██║██║   ██║██╔══██║  ║"
echo "║           ██║  ██║██║  ██║██║ ╚═╝ ██║╚██████╔╝╚██████╔╝██║  ██║  ║"
echo "║           ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝  ║"
echo "║                                                                   ║"
echo "║                    Complete Test Suite Runner                     ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Create report directory
mkdir -p "$REPORT_DIR"

# Track test results
FUNCTIONAL_RESULT="NOT_RUN"
SECURITY_RESULT="NOT_RUN"
PERFORMANCE_RESULT="NOT_RUN"

# =============================================================================
# Helper Functions
# =============================================================================

wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=${3:-30}
    
    echo -e "${YELLOW}Waiting for $name to be ready...${NC}"
    
    for i in $(seq 1 $max_attempts); do
        if curl -ks "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ $name is ready${NC}"
            return 0
        fi
        echo "  Attempt $i/$max_attempts..."
        sleep 5
    done
    
    echo -e "${RED}✗ $name failed to start${NC}"
    return 1
}

# =============================================================================
# Step 1: Start Infrastructure
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 1: Starting Infrastructure${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Check if SSL certs exist
if [ ! -f "nginx/ssl/server.crt" ]; then
    echo "Generating SSL certificates..."
    cd nginx/ssl
    chmod +x generate-certs.sh
    ./generate-certs.sh
    cd ../..
fi

# Start core services
echo "Starting core services..."
docker compose up -d armguard-db armguard-redis

# Wait for database
echo "Waiting for database..."
sleep 10

# Start application
docker compose up -d armguard-app nginx

# Wait for application
wait_for_service "https://localhost/health/" "ArmGuard Application" 30

# =============================================================================
# Step 2: Run Functional Tests
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 2: Running Functional Tests${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Start Selenium Grid
docker compose --profile testing up -d selenium-hub selenium-chrome selenium-firefox

# Wait for Selenium
wait_for_service "http://localhost:4444/wd/hub/status" "Selenium Grid" 20

# Run functional tests
echo "Running functional tests..."
if docker compose run --rm test-runner pytest /tests/functional_tests/ \
    -v --tb=short \
    --junitxml=/results/functional/functional_results_$TIMESTAMP.xml \
    --html=/results/functional/functional_report_$TIMESTAMP.html; then
    FUNCTIONAL_RESULT="PASSED"
    echo -e "${GREEN}✓ Functional tests passed${NC}"
else
    FUNCTIONAL_RESULT="FAILED"
    echo -e "${RED}✗ Functional tests failed${NC}"
fi

# =============================================================================
# Step 3: Run Security Tests
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 3: Running Security Tests${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Start ZAP
docker compose --profile testing up -d zap

# Wait for ZAP
sleep 20

# Run security tests
echo "Running OWASP ZAP baseline scan..."
if docker compose run --rm zap zap-baseline.py \
    -t https://nginx \
    -r zap_baseline_$TIMESTAMP.html \
    -w zap_baseline_$TIMESTAMP.md \
    -c /zap/wrk/zap-rules.tsv; then
    echo "Baseline scan completed"
fi

# Copy ZAP reports
docker cp $(docker compose ps -q zap):/zap/wrk/zap_baseline_$TIMESTAMP.html \
    "$REPORT_DIR/security/" 2>/dev/null || true

# Run custom security checks
echo "Running custom security checks..."
if docker compose run --rm test-runner bash /security_tests/run_security_scan.sh; then
    SECURITY_RESULT="PASSED"
    echo -e "${GREEN}✓ Security tests passed${NC}"
else
    SECURITY_RESULT="FAILED"
    echo -e "${YELLOW}⚠ Security tests completed with findings${NC}"
fi

# =============================================================================
# Step 4: Run Performance Tests
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 4: Running Performance Tests${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Run performance tests
echo "Running load tests..."
if docker compose run --rm locust-master locust \
    -f /locust/locustfile.py \
    --headless \
    --host=https://nginx \
    --users=50 \
    --spawn-rate=5 \
    --run-time=5m \
    --csv=/results/performance/perf_$TIMESTAMP \
    --html=/results/performance/perf_report_$TIMESTAMP.html \
    --only-summary; then
    PERFORMANCE_RESULT="PASSED"
    echo -e "${GREEN}✓ Performance tests passed${NC}"
else
    PERFORMANCE_RESULT="FAILED"
    echo -e "${RED}✗ Performance tests failed${NC}"
fi

# =============================================================================
# Step 5: Start Monitoring (Optional)
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 5: Monitoring Stack${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

read -p "Start monitoring stack (Prometheus, Grafana)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker compose --profile monitoring up -d
    wait_for_service "http://localhost:3000" "Grafana" 20
    echo -e "${GREEN}Monitoring available at:${NC}"
    echo "  - Grafana:     http://localhost:3000 (admin/admin)"
    echo "  - Prometheus:  http://localhost:9090"
    echo "  - Alertmanager: http://localhost:9093"
fi

# =============================================================================
# Step 6: Generate Report
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Step 6: Generating Test Report${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Determine overall status
if [ "$FUNCTIONAL_RESULT" == "PASSED" ] && [ "$PERFORMANCE_RESULT" == "PASSED" ]; then
    OVERALL_RESULT="PASSED"
    OVERALL_COLOR="${GREEN}"
else
    OVERALL_RESULT="FAILED"
    OVERALL_COLOR="${RED}"
fi

# Generate summary report
cat > "$REPORT_DIR/summary_$TIMESTAMP.md" << EOF
# ArmGuard Test Summary Report

**Date:** $(date)
**Timestamp:** $TIMESTAMP

## Results Overview

| Test Suite | Result |
|------------|--------|
| Functional Tests | $FUNCTIONAL_RESULT |
| Security Tests | $SECURITY_RESULT |
| Performance Tests | $PERFORMANCE_RESULT |
| **Overall** | **$OVERALL_RESULT** |

## Report Locations

- Functional: \`$REPORT_DIR/functional/\`
- Security: \`$REPORT_DIR/security/\`
- Performance: \`$REPORT_DIR/performance/\`

## Services Status

\`\`\`
$(docker compose ps)
\`\`\`

## Next Steps

1. Review detailed reports in respective directories
2. Address any failed tests
3. Review security findings
4. Optimize slow endpoints

---
*Generated by ArmGuard Test Suite Runner*
EOF

echo -e "${GREEN}Report generated: $REPORT_DIR/summary_$TIMESTAMP.md${NC}"

# =============================================================================
# Summary
# =============================================================================

echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}                    TEST SUMMARY                            ${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Functional Tests:  $([ "$FUNCTIONAL_RESULT" == "PASSED" ] && echo -e "${GREEN}$FUNCTIONAL_RESULT${NC}" || echo -e "${RED}$FUNCTIONAL_RESULT${NC}")"
echo -e "  Security Tests:    $([ "$SECURITY_RESULT" == "PASSED" ] && echo -e "${GREEN}$SECURITY_RESULT${NC}" || echo -e "${YELLOW}$SECURITY_RESULT${NC}")"
echo -e "  Performance Tests: $([ "$PERFORMANCE_RESULT" == "PASSED" ] && echo -e "${GREEN}$PERFORMANCE_RESULT${NC}" || echo -e "${RED}$PERFORMANCE_RESULT${NC}")"
echo ""
echo -e "  ${OVERALL_COLOR}Overall: $OVERALL_RESULT${NC}"
echo ""
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo "Reports saved to: $REPORT_DIR"
echo ""

# Cleanup prompt
read -p "Stop test environment? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Stopping all services..."
    docker compose --profile monitoring --profile testing down
    echo -e "${GREEN}✓ Environment stopped${NC}"
else
    echo ""
    echo "Services still running. Stop with: docker compose down"
    echo ""
    echo "Access points:"
    echo "  - Application:   https://localhost"
    echo "  - Grafana:       http://localhost:3000"
    echo "  - Prometheus:    http://localhost:9090"
    echo "  - Selenium Grid: http://localhost:4444"
    echo "  - Locust:        http://localhost:8089"
fi
