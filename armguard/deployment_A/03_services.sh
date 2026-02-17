#!/bin/bash

# =============================================================================
# 03_SERVICES.SH - SERVICE DEPLOYMENT AND APPLICATION STARTUP
# =============================================================================
# PURPOSE: Service deployment, systemd units, application startup
# INTEGRATED: Service management from deployment_A + deployment best practices
# VERSION: 4.0.0 - Modular Deployment System
# =============================================================================

set -e  # Exit on any error
set -u  # Exit on undefined variables

# =============================================================================
# CONFIGURATION AND CONSTANTS
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_DIR="/var/log/armguard-deploy"
readonly LOG_FILE="$LOG_DIR/03-services-$(date +%Y%m%d-%H%M%S).log"
readonly ARMGUARD_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -f "$SCRIPT_DIR/.db_config" ]; then
    source "$SCRIPT_DIR/.db_config"
fi

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Service configuration
PROJECT_NAME="${PROJECT_NAME:-armguard}"
GUNICORN_WORKERS="${GUNICORN_WORKERS:-3}"
DAPHNE_PORT="${DAPHNE_PORT:-8001}"

# =============================================================================
# LOGGING SYSTEM
# =============================================================================

log_info() {
    echo -e "${GREEN}[SERVICES-INFO]${NC} $*" | tee -a "$LOG_FILE"
}

log_warn() {
    echo -e "${YELLOW}[SERVICES-WARN]${NC} $*" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[SERVICES-ERROR]${NC} $*" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${CYAN}[SERVICES-SUCCESS]${NC} $*" | tee -a "$LOG_FILE"
}

# =============================================================================
# PYTHON VIRTUAL ENVIRONMENT SETUP
# =============================================================================

setup_python_environment() {
    log_info "Setting up Python virtual environment..."
    
    local venv_path="$ARMGUARD_ROOT/.venv"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_path" ]; then
        python3 -m venv "$venv_path"
        log_success "Virtual environment created"
    fi
    
    # Activate virtual environment
    source "$venv_path/bin/activate"
    log_info "Virtual environment activated"
    
    # Upgrade pip and install requirements
    python -m pip install --upgrade pip
    
    if [ -f "$ARMGUARD_ROOT/requirements.txt" ]; then
        python -m pip install -r "$ARMGUARD_ROOT/requirements.txt"
        log_success "Python requirements installed"
    else
        # Install essential packages for ArmGuard
        log_info "Installing essential Python packages..."
        python -m pip install \
            django \
            djangorestframework \
            django-cors-headers \
            channels \
            channels-redis \
            daphne \
            gunicorn \
            psycopg2-binary \
            redis \
            celery \
            whitenoise \
            django-environ
        log_success "Essential Python packages installed"
    fi
}

# =============================================================================
# DJANGO APPLICATION SETUP (FROM deployment_A/methods/production)
# =============================================================================

setup_django_application() {
    log_info "Setting up Django application..."
    
    cd "$ARMGUARD_ROOT"
    
    # Activate virtual environment
    source ".venv/bin/activate"
    
    # Set Django settings
    export DJANGO_SETTINGS_MODULE=core.settings_production
    
    # Create necessary directories
    sudo mkdir -p ${ARMGUARD_ROOT}/staticfiles
    sudo mkdir -p ${ARMGUARD_ROOT}/media
    sudo mkdir -p /var/log/armguard
    sudo chown -R rds:rds ${ARMGUARD_ROOT}
    sudo chown -R rds:rds /var/log/armguard
    
    # Database migrations
    log_info "Running database migrations..."
    python manage.py migrate --settings=core.settings_production
    if [ $? -eq 0 ]; then
        log_success "Database migrations completed"
    else
        log_error "Database migrations failed"
        return 1
    fi
    
    # Collect static files
    log_info "Collecting static files..."
    python manage.py collectstatic --noinput --settings=core.settings_production
    if [ $? -eq 0 ]; then
        log_success "Static files collected"
    else
        log_error "Static files collection failed"
        return 1
    fi
    
    # Create superuser (interactive)
    echo ""
    echo -e "${WHITE}🔐 Create Django administrator account:${NC}"
    python manage.py createsuperuser --settings=core.settings_production || log_warn "Superuser creation skipped"
    echo ""
    
    log_success "Django application setup completed"
}

# =============================================================================
# GUNICORN SERVICE SETUP (FROM deployment_A/methods/production/install-gunicorn-service.sh)
# =============================================================================

create_gunicorn_service() {
    log_info "Creating Gunicorn systemd service..."
    
    local service_file="/etc/systemd/system/gunicorn-armguard.service"
    local venv_path="$ARMGUARD_ROOT/.venv"
    
    # Create Gunicorn service file
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=ArmGuard Gunicorn Application Server
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=notify
User=rds
Group=rds
RuntimeDirectory=armguard
WorkingDirectory=${ARMGUARD_ROOT}
Environment=DJANGO_SETTINGS_MODULE=core.settings_production
Environment=PATH=${venv_path}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${venv_path}/bin/gunicorn \\
    --user rds \\
    --group rds \\
    --bind 127.0.0.1:8000 \\
    --workers ${GUNICORN_WORKERS} \\
    --worker-class sync \\
    --worker-connections 1000 \\
    --max-requests 1000 \\
    --max-requests-jitter 100 \\
    --timeout 30 \\
    --keep-alive 5 \\
    --log-level info \\
    --log-file /var/log/armguard/gunicorn.log \\
    --access-logfile /var/log/armguard/gunicorn-access.log \\
    --capture-output \\
    --pid /run/armguard/gunicorn.pid \\
    core.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Set proper permissions
    sudo systemctl daemon-reload
    sudo systemctl enable gunicorn-armguard.service
    
    log_success "Gunicorn service created and enabled"
}

# =============================================================================
# DAPHNE SERVICE SETUP (FOR WEBSOCKET SUPPORT)
# =============================================================================

create_daphne_service() {
    log_info "Creating Daphne WebSocket service..."
    
    local service_file="/etc/systemd/system/armguard-daphne.service"
    local venv_path="$ARMGUARD_ROOT/.venv"
    
    # Create Daphne service file (resolves WebSocket blocking issues)
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=ArmGuard Daphne WebSocket Server
After=network.target redis.service
Requires=redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=${ARMGUARD_ROOT}
Environment=DJANGO_SETTINGS_MODULE=core.settings_production
Environment=PATH=${venv_path}/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${venv_path}/bin/daphne \\
    --bind 127.0.0.1 \\
    --port ${DAPHNE_PORT} \\
    --access-log /var/log/armguard/daphne-access.log \\
    --verbosity 1 \\
    core.asgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    # Set proper permissions and enable
    sudo systemctl daemon-reload
    sudo systemctl enable armguard-daphne.service
    
    log_success "Daphne WebSocket service created and enabled"
}

# =============================================================================
# LOG ROTATION SETUP (FROM deployment_A/methods/production/setup-logrotate.sh)
# =============================================================================

setup_log_rotation() {
    log_info "Setting up log rotation..."
    
    local logrotate_config="/etc/logrotate.d/armguard"
    
    sudo tee "$logrotate_config" > /dev/null << EOF
/var/log/armguard/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        /bin/systemctl reload gunicorn-armguard armguard-daphne || true
    endscript
}

/var/log/armguard-deploy/*.log {
    weekly
    missingok
    rotate 12
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOF
    
    # Test logrotate configuration
    if sudo logrotate -t "$logrotate_config"; then
        log_success "Log rotation configured successfully"
    else
        log_error "Log rotation configuration failed"
        return 1
    fi
}

# =============================================================================
# SERVICE HEALTH CHECKS (FROM deployment_A/methods/production/health-check.sh)
# =============================================================================

check_service_health() {
    log_info "Performing service health checks..."
    
    local health_passed=true
    
    # Check PostgreSQL
    if sudo -u postgres pg_isready >/dev/null 2>&1; then
        log_success "PostgreSQL is healthy"
    else
        log_error "PostgreSQL health check failed"
        health_passed=false
    fi
    
    # Check Redis
    if redis-cli ping >/dev/null 2>&1; then
        log_success "Redis is healthy"
    else
        log_error "Redis health check failed"
        health_passed=false
    fi
    
    # Check Nginx
    if nginx -t >/dev/null 2>&1; then
        log_success "Nginx configuration is valid"
    else
        log_error "Nginx configuration check failed"
        health_passed=false
    fi
    
    # Check if services are running
    local services=("postgresql" "redis-server" "nginx")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null || 
           systemctl is-active --quiet "${service%%-server}" 2>/dev/null; then
            log_success "$service is running"
        else
            log_error "$service is not running"
            health_passed=false
        fi
    done
    
    if [ "$health_passed" = true ]; then
        log_success "All service health checks passed"
        return 0
    else
        log_error "Some service health checks failed"
        return 1
    fi
}

# =============================================================================
# SERVICE STARTUP
# =============================================================================

start_services() {
    log_info "Starting ArmGuard services..."
    
    # Start Gunicorn service
    sudo systemctl start gunicorn-armguard.service
    if systemctl is-active --quiet gunicorn-armguard.service; then
        log_success "Gunicorn service started"
    else
        log_error "Failed to start Gunicorn service"
        sudo journalctl -u gunicorn-armguard.service --no-pager -l
        return 1
    fi
    
    # Start Daphne service
    sudo systemctl start armguard-daphne.service
    if systemctl is-active --quiet armguard-daphne.service; then
        log_success "Daphne WebSocket service started"
    else
        log_error "Failed to start Daphne service"
        sudo journalctl -u armguard-daphne.service --no-pager -l
        return 1
    fi
    
    # Reload Nginx to apply new configuration
    sudo systemctl reload nginx
    log_success "Nginx configuration reloaded"
    
    log_success "All ArmGuard services started successfully"
}

# =============================================================================
# SERVICE VALIDATION (INTEGRATED FROM BOTH SYSTEMS)
# =============================================================================

validate_deployment() {
    log_info "Validating deployment..."
    
    local validation_passed=true
    
    # Test HTTP redirect (should redirect to HTTPS)
    log_info "Testing HTTP redirect..."
    local http_response
    http_response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ || echo "000")
    if [ "$http_response" = "301" ] || [ "$http_response" = "302" ]; then
        log_success "HTTP redirect working (status: $http_response)"
    else  
        log_warn "HTTP redirect not working (status: $http_response)"
    fi
    
    # Test HTTPS response
    log_info "Testing HTTPS response..."
    local https_response
    if [ -f "/etc/ssl/armguard/cert.pem" ]; then
        https_response=$(curl -s -k -o /dev/null -w "%{http_code}" https://localhost:8443/ || echo "000")
        if [ "$https_response" = "200" ]; then
            log_success "HTTPS response working (status: $https_response)"
        else
            log_warn "HTTPS response issue (status: $https_response)"
        fi
    else
        log_warn "SSL certificate not found - skipping HTTPS test"
    fi
    
    # Test WebSocket connection
    log_info "Testing WebSocket endpoint..."
    local ws_port_open
    ws_port_open=$(nc -z localhost "$DAPHNE_PORT" && echo "open" || echo "closed")
    if [ "$ws_port_open" = "open" ]; then
        log_success "WebSocket port $DAPHNE_PORT is open"
    else
        log_warn "WebSocket port $DAPHNE_PORT is not accessible"
    fi
    
    # Test database connection
    log_info "Testing database connection..."
    cd "$ARMGUARD_ROOT"
    source ".venv/bin/activate"
    if python manage.py check --database default --settings=core.settings_production >/dev/null 2>&1; then
        log_success "Database connection working"
    else
        log_error "Database connection failed"
        validation_passed=false
    fi
    
    # Service status summary
    echo ""
    log_info "Service status summary:"
    local services=("gunicorn-armguard" "armguard-daphne" "nginx" "postgresql" "redis-server")
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null || 
           systemctl is-active --quiet "${service%%-server}" 2>/dev/null; then
            echo -e "  ${GREEN}✅ $service${NC}: Running"
        else
            echo -e "  ${RED}❌ $service${NC}: Not running"
            validation_passed=false
        fi
    done
    
    if [ "$validation_passed" = true ]; then
        return 0
    else
        return 1
    fi
}

# =============================================================================
# MAIN SERVICES EXECUTION
# =============================================================================

print_services_header() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}║               ${WHITE}🚀 ARMGUARD SERVICE DEPLOYMENT${BLUE}                            ║${NC}"
    echo -e "${BLUE}║                     ${CYAN}Phase 3: Application Services${BLUE}                        ║${NC}"
    echo -e "${BLUE}║                                                                               ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

main() {
    print_services_header
    
    log_info "Starting ArmGuard service deployment..."
    log_info "Logging to: $LOG_FILE"
    
    # Pre-deployment health checks
    if ! check_service_health; then
        log_error "Pre-deployment health checks failed - attempting to fix..."
        
        # Try to start prerequisite services
        sudo systemctl start postgresql redis-server nginx
        sleep 5
        
        if ! check_service_health; then
            log_error "Could not resolve service health issues"
            exit 1
        fi
    fi
    
    echo -e "${YELLOW}🔧 Setting up application environment...${NC}"
    setup_python_environment
    setup_django_application
    
    echo -e "${YELLOW}🛠️  Creating system services...${NC}"
    create_gunicorn_service
    create_daphne_service
    setup_log_rotation
    
    echo -e "${YELLOW}🚀 Starting services...${NC}"
    start_services
    
    # Give services time to start
    sleep 10
    
    echo -e "${YELLOW}✅ Validating deployment...${NC}"
    if validate_deployment; then
        echo ""
        log_success "✅ Service deployment completed successfully!"
        echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║                      ${WHITE}SERVICE DEPLOYMENT COMPLETED${GREEN}                        ║${NC}"
        echo -e "${GREEN}║                                                                               ║${NC}"
        echo -e "${GREEN}║  Services Running:                                                            ║${NC}"
        echo -e "${GREEN}║  • ${WHITE}Gunicorn${GREEN}: Django application server (port 8000)                   ║${NC}"
        echo -e "${GREEN}║  • ${WHITE}Daphne${GREEN}: WebSocket server (port $DAPHNE_PORT)                                ║${NC}"
        echo -e "${GREEN}║  • ${WHITE}Nginx${GREEN}: Reverse proxy and SSL termination                           ║${NC}"
        echo -e "${GREEN}║  • ${WHITE}PostgreSQL${GREEN}: Database server                                          ║${NC}"
        echo -e "${GREEN}║  • ${WHITE}Redis${GREEN}: Cache and WebSocket backend                                   ║${NC}"
        echo -e "${GREEN}║                                                                               ║${NC}"
        echo -e "${GREEN}║  Next: Run 04_monitoring.sh to enable monitoring and health checks           ║${NC}"
        echo -e "${GREEN}║                                                                               ║${NC}"
        echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    else
        echo ""
        log_warn "⚠️  Service deployment completed with warnings!"
        echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${YELLOW}║                   ${WHITE}SERVICE DEPLOYMENT - WARNINGS DETECTED${YELLOW}                   ║${NC}"
        echo -e "${YELLOW}║                                                                               ║${NC}"
        echo -e "${YELLOW}║  Some validation checks failed. Please review the logs:                      ║${NC}"
        echo -e "${YELLOW}║  • Service logs: sudo journalctl -u gunicorn-armguard                        ║${NC}"
        echo -e "${YELLOW}║  • WebSocket logs: sudo journalctl -u armguard-daphne                        ║${NC}"
        echo -e "${YELLOW}║  • Deployment logs: $LOG_FILE    ║${NC}"
        echo -e "${YELLOW}║                                                                               ║${NC}"
        echo -e "${YELLOW}║  You can proceed to monitoring or troubleshoot first.                        ║${NC}"
        echo -e "${YELLOW}║                                                                               ║${NC}"
        echo -e "${YELLOW}╚═══════════════════════════════════════════════════════════════════════════════╝${NC}"
    fi
    
    echo ""
    log_info "Service deployment log saved to: $LOG_FILE"
}

# Execute main function
main "$@"