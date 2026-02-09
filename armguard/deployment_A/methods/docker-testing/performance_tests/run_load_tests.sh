#!/bin/bash
# ArmGuard Performance Test Runner
# Executes load tests and generates reports

set -e

# Configuration
TARGET_URL="${TARGET_URL:-https://nginx}"
REPORT_DIR="${REPORT_DIR:-/results/performance}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Test configurations
USERS_LIGHT=10
USERS_MEDIUM=50
USERS_HEAVY=100
USERS_STRESS=200
SPAWN_RATE=5
RUN_TIME="5m"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ArmGuard Performance Testing Suite                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create report directory
mkdir -p "$REPORT_DIR"

# =============================================================================
# Light Load Test (10 users)
# =============================================================================

echo -e "${YELLOW}[1/4] Running Light Load Test ($USERS_LIGHT users)...${NC}"

locust -f /locust/locustfile.py \
    --headless \
    --host="$TARGET_URL" \
    --users=$USERS_LIGHT \
    --spawn-rate=$SPAWN_RATE \
    --run-time=2m \
    --csv="$REPORT_DIR/light_load_$TIMESTAMP" \
    --html="$REPORT_DIR/light_load_$TIMESTAMP.html" \
    --only-summary

echo -e "${GREEN}✓ Light load test complete${NC}"

# =============================================================================
# Medium Load Test (50 users)
# =============================================================================

echo ""
echo -e "${YELLOW}[2/4] Running Medium Load Test ($USERS_MEDIUM users)...${NC}"

locust -f /locust/locustfile.py \
    --headless \
    --host="$TARGET_URL" \
    --users=$USERS_MEDIUM \
    --spawn-rate=$SPAWN_RATE \
    --run-time=$RUN_TIME \
    --csv="$REPORT_DIR/medium_load_$TIMESTAMP" \
    --html="$REPORT_DIR/medium_load_$TIMESTAMP.html" \
    --only-summary

echo -e "${GREEN}✓ Medium load test complete${NC}"

# =============================================================================
# Heavy Load Test (100 users)
# =============================================================================

echo ""
echo -e "${YELLOW}[3/4] Running Heavy Load Test ($USERS_HEAVY users)...${NC}"

locust -f /locust/locustfile.py \
    --headless \
    --host="$TARGET_URL" \
    --users=$USERS_HEAVY \
    --spawn-rate=$SPAWN_RATE \
    --run-time=$RUN_TIME \
    --csv="$REPORT_DIR/heavy_load_$TIMESTAMP" \
    --html="$REPORT_DIR/heavy_load_$TIMESTAMP.html" \
    --only-summary

echo -e "${GREEN}✓ Heavy load test complete${NC}"

# =============================================================================
# Stress Test (200 users)
# =============================================================================

echo ""
echo -e "${YELLOW}[4/4] Running Stress Test ($USERS_STRESS users)...${NC}"

locust -f /locust/locustfile.py \
    --headless \
    --host="$TARGET_URL" \
    --users=$USERS_STRESS \
    --spawn-rate=10 \
    --run-time=$RUN_TIME \
    --csv="$REPORT_DIR/stress_test_$TIMESTAMP" \
    --html="$REPORT_DIR/stress_test_$TIMESTAMP.html" \
    --only-summary

echo -e "${GREEN}✓ Stress test complete${NC}"

# =============================================================================
# Generate Summary Report
# =============================================================================

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Generating Performance Summary...${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# Parse CSV files and generate summary
cat > "$REPORT_DIR/performance_summary_$TIMESTAMP.md" << EOF
# ArmGuard Performance Test Report

**Date:** $(date)
**Target:** $TARGET_URL

## Test Configurations

| Test Type | Users | Spawn Rate | Duration |
|-----------|-------|------------|----------|
| Light Load | $USERS_LIGHT | $SPAWN_RATE/s | 2m |
| Medium Load | $USERS_MEDIUM | $SPAWN_RATE/s | $RUN_TIME |
| Heavy Load | $USERS_HEAVY | $SPAWN_RATE/s | $RUN_TIME |
| Stress Test | $USERS_STRESS | 10/s | $RUN_TIME |

## Results Summary

### Light Load ($USERS_LIGHT users)
$(cat "$REPORT_DIR/light_load_${TIMESTAMP}_stats.csv" 2>/dev/null | head -20 || echo "Results pending")

### Medium Load ($USERS_MEDIUM users)
$(cat "$REPORT_DIR/medium_load_${TIMESTAMP}_stats.csv" 2>/dev/null | head -20 || echo "Results pending")

### Heavy Load ($USERS_HEAVY users)
$(cat "$REPORT_DIR/heavy_load_${TIMESTAMP}_stats.csv" 2>/dev/null | head -20 || echo "Results pending")

### Stress Test ($USERS_STRESS users)
$(cat "$REPORT_DIR/stress_test_${TIMESTAMP}_stats.csv" 2>/dev/null | head -20 || echo "Results pending")

## Performance Metrics

### Response Time Thresholds
- Excellent: < 200ms
- Good: 200ms - 500ms
- Acceptable: 500ms - 1000ms
- Poor: 1000ms - 2000ms
- Critical: > 2000ms

### Failure Rate Thresholds
- Excellent: < 0.1%
- Good: 0.1% - 0.5%
- Acceptable: 0.5% - 1%
- Poor: 1% - 5%
- Critical: > 5%

## Detailed Reports

- Light Load: light_load_$TIMESTAMP.html
- Medium Load: medium_load_$TIMESTAMP.html
- Heavy Load: heavy_load_$TIMESTAMP.html
- Stress Test: stress_test_$TIMESTAMP.html

## Recommendations

1. Review any endpoints with response times > 1000ms
2. Investigate failure rates above 1%
3. Consider caching for frequently accessed resources
4. Optimize database queries for high-load scenarios
5. Scale infrastructure if stress test shows degradation

---
*Generated by ArmGuard Performance Test Suite*
EOF

echo ""
echo -e "${GREEN}Performance testing complete!${NC}"
echo "Reports saved to: $REPORT_DIR"
