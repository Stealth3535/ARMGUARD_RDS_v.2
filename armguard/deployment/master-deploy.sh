#!/bin/bash

################################################################################
# ArmGuard Master Deployment Script
# 
# Orchestrates complete deployment with proper ordering and verification
# Usage: sudo bash deployment/master-deploy.sh [--network-type <lan|wan|hybrid>]
################################################################################

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source configuration
if [ -f "$SCRIPT_DIR/config.sh" ]; then
    source "$SCRIPT_DIR/config.sh"
else
    echo "ERROR: config.sh not found"
    exit 1
fi

# Deployment options
NETWORK_TYPE="${NETWORK_TYPE:-lan}"  # lan, wan, or hybrid
SKIP_PROMPTS="${SKIP_PROMPTS:-no}"
RUN_HEALTH_CHECK="${RUN_HEALTH_CHECK:-yes}"

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --network-type) NETWORK_TYPE="$2"; shift ;;
        --skip-prompts) SKIP_PROMPTS="yes" ;;
        --no-health-check) RUN_HEALTH_CHECK="no" ;;
        -h|--help)
            echo "Usage: sudo bash master-deploy.sh [options]"
            echo ""
            echo "Options:"
            echo "  --network-type <type>  Network setup type: lan, wan, or hybrid (default: lan)"
            echo "  --skip-prompts         Skip all confirmation prompts"
            echo "  --no-health-check      Skip health check after deployment"
            echo "  -h, --help             Show this help message"
            exit 0
            ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# Print banner
clear
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║           ${GREEN}ArmGuard Master Deployment Script${CYAN}                  ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║  This script orchestrates the complete deployment process:    ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 1:${CYAN} Environment Detection & Pre-checks                ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 2:${CYAN} System Dependencies Installation                  ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 3:${CYAN} Python Environment Setup                          ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 4:${CYAN} Database Setup & Migrations                       ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 5:${CYAN} Gunicorn Service Installation                     ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 6:${CYAN} Nginx Configuration                               ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 7:${CYAN} SSL Certificate Setup                             ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 8:${CYAN} Firewall Configuration                            ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 9:${CYAN} Log Rotation Setup                                ║${NC}"
echo -e "${CYAN}║  ${YELLOW}Phase 10:${CYAN} Health Check & Verification                      ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root (use sudo)${NC}"
    exit 1
fi

# Display configuration
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Deployment Configuration${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${CYAN}Project Settings:${NC}"
echo "  Name:             $PROJECT_NAME"
echo "  Directory:        $PROJECT_DIR"
echo "  Domain:           $DEFAULT_DOMAIN"
echo ""
echo -e "${CYAN}Network Settings:${NC}"
echo "  Network Type:     $NETWORK_TYPE"
if [ "$NETWORK_TYPE" = "lan" ] || [ "$NETWORK_TYPE" = "hybrid" ]; then
    echo "  LAN Interface:    $LAN_INTERFACE"
    echo "  LAN IP:           $SERVER_LAN_IP"
    echo "  Armory PC IP:     $ARMORY_PC_IP"
fi
if [ "$NETWORK_TYPE" = "wan" ] || [ "$NETWORK_TYPE" = "hybrid" ]; then
    echo "  WAN Interface:    $WAN_INTERFACE"
fi
echo ""
echo -e "${CYAN}Service Settings:${NC}"
echo "  Service Name:     $SERVICE_NAME"
echo "  Run User:         $RUN_USER:$RUN_GROUP"
echo "  Workers:          $(calculate_workers)"
echo ""

if [ "$SKIP_PROMPTS" != "yes" ]; then
    read -p "Continue with this configuration? (yes/no): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy] ]]; then
        echo -e "${YELLOW}Deployment cancelled.${NC}"
        exit 0
    fi
fi

DEPLOY_START=$(date +%s)
PHASE_RESULTS=()

# Function to record phase result
record_phase() {
    local phase_name="$1"
    local result="$2"
    PHASE_RESULTS+=("$phase_name:$result")
}

# Function to print phase header
print_phase() {
    local phase_num="$1"
    local phase_name="$2"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Phase $phase_num: $phase_name${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# ============================================================================
# PHASE 1: Environment Detection
# ============================================================================
print_phase "1" "Environment Detection & Pre-checks"

echo -e "${YELLOW}Running environment detection...${NC}"
if [ -f "$SCRIPT_DIR/detect-environment.sh" ]; then
    bash "$SCRIPT_DIR/detect-environment.sh" --quiet || true
    echo -e "${GREEN}✓ Environment detected${NC}"
else
    echo -e "${YELLOW}⚠ detect-environment.sh not found, using defaults${NC}"
fi

echo -e "${YELLOW}Running pre-checks...${NC}"
if [ -f "$SCRIPT_DIR/pre-check.sh" ]; then
    if bash "$SCRIPT_DIR/pre-check.sh"; then
        echo -e "${GREEN}✓ Pre-checks passed${NC}"
        record_phase "Pre-checks" "PASS"
    else
        echo -e "${RED}✗ Pre-checks failed${NC}"
        record_phase "Pre-checks" "FAIL"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ pre-check.sh not found, skipping${NC}"
    record_phase "Pre-checks" "SKIP"
fi

# ============================================================================
# PHASE 2: System Dependencies
# ============================================================================
print_phase "2" "System Dependencies Installation"

echo -e "${YELLOW}Updating package lists...${NC}"
apt-get update -qq

echo -e "${YELLOW}Installing system packages...${NC}"
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    nginx \
    wget \
    curl \
    libjpeg-dev \
    zlib1g-dev \
    libnss3-tools \
    openssl \
    ufw \
    fail2ban \
    net-tools \
    bc

echo -e "${GREEN}✓ System packages installed${NC}"
record_phase "System Dependencies" "PASS"

# ============================================================================
# PHASE 3: Python Environment
# ============================================================================
print_phase "3" "Python Environment Setup"

cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

echo -e "${YELLOW}Upgrading pip...${NC}"
.venv/bin/pip install --upgrade pip -q

echo -e "${YELLOW}Installing Python packages...${NC}"
.venv/bin/pip install -r requirements.txt -q

# Ensure gunicorn is installed
if [ ! -f ".venv/bin/gunicorn" ]; then
    .venv/bin/pip install gunicorn -q
fi

echo -e "${GREEN}✓ Python environment ready${NC}"
record_phase "Python Environment" "PASS"

# ============================================================================
# PHASE 4: Database Setup
# ============================================================================
print_phase "4" "Database Setup & Migrations"

# Create log directories first
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"
mkdir -p "logs"

# Set directory permissions
chown -R $RUN_USER:$RUN_GROUP "$LOG_DIR"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Creating .env from template...${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        # Generate new secret key
        SECRET_KEY=$(openssl rand -base64 50)
        sed -i "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" .env
    fi
fi

echo -e "${YELLOW}Running migrations...${NC}"
.venv/bin/python manage.py migrate --settings=core.settings_production --noinput

echo -e "${YELLOW}Collecting static files...${NC}"
.venv/bin/python manage.py collectstatic --settings=core.settings_production --noinput > /dev/null 2>&1

# Set permissions
chown -R $RUN_USER:$RUN_GROUP "$PROJECT_DIR"
chmod 600 .env 2>/dev/null || true
chmod 664 db.sqlite3 2>/dev/null || true

echo -e "${GREEN}✓ Database ready${NC}"
record_phase "Database Setup" "PASS"

# ============================================================================
# PHASE 5: Gunicorn Service
# ============================================================================
print_phase "5" "Gunicorn Service Installation"

echo -e "${YELLOW}Installing Gunicorn systemd service...${NC}"

# Calculate workers
WORKERS=$(calculate_workers)

# Create service file
cat > /etc/systemd/system/gunicorn-armguard.service << EOF
[Unit]
Description=Gunicorn daemon for ArmGuard
Documentation=https://github.com/Stealth3535/armguard
After=network.target

[Service]
Type=exec
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="DJANGO_SETTINGS_MODULE=core.settings_production"
EnvironmentFile=-$PROJECT_DIR/.env

ExecStart=$VENV_DIR/bin/gunicorn \\
          --workers $WORKERS \\
          --bind unix:$SOCKET_PATH \\
          --timeout $GUNICORN_TIMEOUT \\
          --max-requests $GUNICORN_MAX_REQUESTS \\
          --max-requests-jitter $GUNICORN_MAX_REQUESTS_JITTER \\
          --access-logfile $LOG_DIR/access.log \\
          --error-logfile $LOG_DIR/error.log \\
          --log-level info \\
          core.wsgi:application

ExecReload=/bin/kill -s HUP \$MAINPID

Restart=always
RestartSec=3

PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$PROJECT_DIR $LOG_DIR /run

KillMode=mixed
KillSignal=SIGQUIT
TimeoutStopSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and start service
systemctl daemon-reload
systemctl enable gunicorn-armguard
systemctl restart gunicorn-armguard

# Verify service started
sleep 2
if systemctl is-active --quiet gunicorn-armguard; then
    echo -e "${GREEN}✓ Gunicorn service running${NC}"
    record_phase "Gunicorn Service" "PASS"
else
    echo -e "${RED}✗ Gunicorn service failed to start${NC}"
    journalctl -u gunicorn-armguard -n 20 --no-pager
    record_phase "Gunicorn Service" "FAIL"
fi

# ============================================================================
# PHASE 6: Nginx Configuration
# ============================================================================
print_phase "6" "Nginx Configuration"

echo -e "${YELLOW}Configuring Nginx...${NC}"

# Use enhanced nginx script if available
if [ -f "$SCRIPT_DIR/install-nginx-enhanced.sh" ]; then
    bash "$SCRIPT_DIR/install-nginx-enhanced.sh" "$DEFAULT_DOMAIN"
    echo -e "${GREEN}✓ Nginx configured (enhanced security)${NC}"
else
    bash "$SCRIPT_DIR/install-nginx.sh" "$DEFAULT_DOMAIN"
    echo -e "${GREEN}✓ Nginx configured${NC}"
fi

record_phase "Nginx Configuration" "PASS"

# ============================================================================
# PHASE 7: SSL Certificate Setup
# ============================================================================
print_phase "7" "SSL Certificate Setup"

case $NETWORK_TYPE in
    lan)
        echo -e "${YELLOW}Setting up LAN SSL (mkcert)...${NC}"
        if [ -f "$SCRIPT_DIR/network_setup/setup-lan-network.sh" ]; then
            bash "$SCRIPT_DIR/network_setup/setup-lan-network.sh"
        elif [ -f "$SCRIPT_DIR/install-mkcert-ssl.sh" ]; then
            bash "$SCRIPT_DIR/install-mkcert-ssl.sh" "$DEFAULT_DOMAIN"
        fi
        echo -e "${GREEN}✓ LAN SSL configured${NC}"
        record_phase "SSL Setup" "PASS (LAN/mkcert)"
        ;;
    wan)
        echo -e "${YELLOW}Setting up WAN SSL (ACME)...${NC}"
        if [ -f "$SCRIPT_DIR/network_setup/setup-wan-network.sh" ]; then
            bash "$SCRIPT_DIR/network_setup/setup-wan-network.sh"
        else
            echo -e "${YELLOW}⚠ WAN setup script not found, manual SSL required${NC}"
        fi
        echo -e "${GREEN}✓ WAN SSL configured${NC}"
        record_phase "SSL Setup" "PASS (WAN/ACME)"
        ;;
    hybrid)
        echo -e "${YELLOW}Setting up Hybrid SSL (LAN + WAN)...${NC}"
        if [ -f "$SCRIPT_DIR/network_setup/setup-lan-network.sh" ]; then
            bash "$SCRIPT_DIR/network_setup/setup-lan-network.sh"
        fi
        if [ -f "$SCRIPT_DIR/network_setup/setup-wan-network.sh" ]; then
            bash "$SCRIPT_DIR/network_setup/setup-wan-network.sh"
        fi
        echo -e "${GREEN}✓ Hybrid SSL configured${NC}"
        record_phase "SSL Setup" "PASS (Hybrid)"
        ;;
esac

# ============================================================================
# PHASE 8: Firewall Configuration
# ============================================================================
print_phase "8" "Firewall Configuration"

if [ "$ENABLE_FIREWALL" = "yes" ]; then
    echo -e "${YELLOW}Configuring firewall...${NC}"
    
    if [ "$NETWORK_TYPE" = "hybrid" ] && [ -f "$SCRIPT_DIR/network_setup/configure-firewall.sh" ]; then
        bash "$SCRIPT_DIR/network_setup/configure-firewall.sh"
    else
        # Basic firewall setup
        ufw --force reset > /dev/null 2>&1
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow ssh
        ufw allow 'Nginx Full'
        ufw --force enable
    fi
    
    echo -e "${GREEN}✓ Firewall configured${NC}"
    record_phase "Firewall" "PASS"
else
    echo -e "${YELLOW}⚠ Firewall configuration skipped${NC}"
    record_phase "Firewall" "SKIP"
fi

# ============================================================================
# PHASE 9: Log Rotation
# ============================================================================
print_phase "9" "Log Rotation Setup"

if [ -f "$SCRIPT_DIR/setup-logrotate.sh" ]; then
    bash "$SCRIPT_DIR/setup-logrotate.sh"
    echo -e "${GREEN}✓ Log rotation configured${NC}"
    record_phase "Log Rotation" "PASS"
else
    echo -e "${YELLOW}⚠ setup-logrotate.sh not found, skipping${NC}"
    record_phase "Log Rotation" "SKIP"
fi

# ============================================================================
# PHASE 10: Health Check
# ============================================================================
print_phase "10" "Health Check & Verification"

if [ "$RUN_HEALTH_CHECK" = "yes" ] && [ -f "$SCRIPT_DIR/health-check.sh" ]; then
    echo -e "${YELLOW}Running health check...${NC}"
    if bash "$SCRIPT_DIR/health-check.sh" "$DEFAULT_DOMAIN"; then
        echo -e "${GREEN}✓ All health checks passed${NC}"
        record_phase "Health Check" "PASS"
    else
        echo -e "${YELLOW}⚠ Some health checks failed${NC}"
        record_phase "Health Check" "WARN"
    fi
else
    echo -e "${YELLOW}⚠ Health check skipped${NC}"
    record_phase "Health Check" "SKIP"
fi

# ============================================================================
# DEPLOYMENT SUMMARY
# ============================================================================
DEPLOY_END=$(date +%s)
DEPLOY_TIME=$((DEPLOY_END - DEPLOY_START))

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}║            ✓ Deployment Completed Successfully!               ║${NC}"
echo -e "${GREEN}║                                                                ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Deployment Summary:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
for result in "${PHASE_RESULTS[@]}"; do
    phase_name="${result%:*}"
    status="${result#*:}"
    if [[ "$status" == *"PASS"* ]]; then
        echo -e "  ${GREEN}✓${NC} $phase_name: ${GREEN}$status${NC}"
    elif [[ "$status" == "FAIL" ]]; then
        echo -e "  ${RED}✗${NC} $phase_name: ${RED}$status${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} $phase_name: ${YELLOW}$status${NC}"
    fi
done
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${CYAN}Time Elapsed:${NC} ${DEPLOY_TIME} seconds"
echo ""

# Display access URLs
SERVER_IP=$(get_server_ip)

echo -e "${CYAN}Access URLs:${NC}"
case $NETWORK_TYPE in
    lan)
        echo "  • LAN (HTTPS):  https://$SERVER_LAN_IP:8443"
        echo "  • LAN (HTTP):   http://$SERVER_IP (redirect to HTTPS)"
        ;;
    wan)
        echo "  • WAN (HTTPS):  https://$DEFAULT_DOMAIN"
        echo "  • WAN (HTTP):   http://$DEFAULT_DOMAIN (redirect to HTTPS)"
        ;;
    hybrid)
        echo "  • LAN (HTTPS):  https://$SERVER_LAN_IP:8443"
        echo "  • WAN (HTTPS):  https://$DEFAULT_DOMAIN"
        ;;
esac
echo ""

echo -e "${CYAN}Management Commands:${NC}"
echo "  • Status:       sudo systemctl status gunicorn-armguard"
echo "  • Restart:      sudo systemctl restart gunicorn-armguard"
echo "  • Logs:         sudo journalctl -u gunicorn-armguard -f"
echo "  • Health:       sudo bash $SCRIPT_DIR/health-check.sh"
echo "  • Update:       sudo bash $SCRIPT_DIR/update-armguard.sh"
echo "  • Rollback:     sudo bash $SCRIPT_DIR/rollback.sh"
echo ""

echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Deployment completed at: $(date)${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"

exit 0
