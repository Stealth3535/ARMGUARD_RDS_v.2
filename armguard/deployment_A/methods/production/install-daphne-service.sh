#!/bin/bash

# Daphne ASGI Service Deployment Script for ArmGuard
# This script automates the installation and configuration of Daphne systemd service
# Replaces Gunicorn for WebSocket support

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

############################################################
# ArmGuard Deployment Location Detection & Configuration
############################################################
PROJECT_NAME="armguard"
DEFAULT_PROJECT_DIR="/var/www/armguard"
ALT_PROJECT_DIR="/home/ubuntu/ARMGUARD_RDS/armguard"
DEFAULT_VENV_DIR="${DEFAULT_PROJECT_DIR}/.venv"
ALT_VENV_DIR="/home/ubuntu/ARMGUARD_RDS/venv"
DEFAULT_LOG_DIR="/var/log/armguard"
ALT_LOG_DIR="/home/ubuntu/ARMGUARD_RDS/logs"

# Detect deployment location
if [ -d "$ALT_PROJECT_DIR" ]; then
    PROJECT_DIR="$ALT_PROJECT_DIR"
    VENV_DIR="$ALT_VENV_DIR"
    LOG_DIR="$ALT_LOG_DIR"
    RUN_USER="ubuntu"
    RUN_GROUP="ubuntu"
    SERVICE_NAME="armguard-daphne"
    SERVICE_FILE="${SERVICE_NAME}.service"
    echo -e "${YELLOW}Detected RPi/ARMGUARD_RDS deployment at $ALT_PROJECT_DIR${NC}"
else
    PROJECT_DIR="$DEFAULT_PROJECT_DIR"
    VENV_DIR="$DEFAULT_VENV_DIR"
    LOG_DIR="$DEFAULT_LOG_DIR"
    RUN_USER="www-data"
    RUN_GROUP="www-data"
    SERVICE_NAME="daphne-armguard"
    SERVICE_FILE="${SERVICE_NAME}.service"
    echo -e "${YELLOW}Using default deployment at $DEFAULT_PROJECT_DIR${NC}"
fi

PYTHON_EXEC="${VENV_DIR}/bin/python"
DAPHNE_EXEC="${VENV_DIR}/bin/daphne"
MANAGE_PY="${PROJECT_DIR}/armguard/manage.py"
ASGI_MODULE="core.asgi:application"
BIND_ADDRESS="127.0.0.1"
BIND_PORT="8000"
WORKERS="4"

############################################################
# Helper Functions
############################################################

print_header() {
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

############################################################
# Validation Checks
############################################################

validate_environment() {
    print_header "Validating Environment"
    
    # Check if project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        print_error "Project directory not found: $PROJECT_DIR"
        exit 1
    fi
    print_success "Project directory found"
    
    # Check if virtual environment exists
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found: $VENV_DIR"
        exit 1
    fi
    print_success "Virtual environment found"
    
    # Check if manage.py exists
    if [ ! -f "$MANAGE_PY" ]; then
        print_error "manage.py not found: $MANAGE_PY"
        exit 1
    fi
    print_success "manage.py found"
    
    # Check if daphne is installed
    if [ ! -f "$DAPHNE_EXEC" ]; then
        print_error "Daphne not found in virtual environment"
        print_info "Install with: $VENV_DIR/bin/pip install daphne channels channels-redis"
        exit 1
    fi
    print_success "Daphne found"
    
    # Check if Redis is installed and running
    if ! command -v redis-cli &> /dev/null; then
        print_warning "Redis not installed (required for production)"
        print_info "Install with: sudo apt-get install redis-server"
        print_info "For development, InMemoryChannelLayer can be used"
    else
        if systemctl is-active --quiet redis; then
            print_success "Redis is installed and running"
        else
            print_warning "Redis is installed but not running"
            print_info "Start with: sudo systemctl start redis"
        fi
    fi
    
    # Check if user exists
    if ! id "$RUN_USER" &>/dev/null; then
        print_error "User $RUN_USER does not exist"
        exit 1
    fi
    print_success "Run user ($RUN_USER) exists"
}

############################################################
# Service Installation
############################################################

create_log_directory() {
    print_header "Creating Log Directory"
    
    mkdir -p "$LOG_DIR"
    chown -R "$RUN_USER:$RUN_GROUP" "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    
    print_success "Log directory created: $LOG_DIR"
}

stop_existing_service() {
    print_header "Stopping Existing Services"
    
    # Stop old Gunicorn service if it exists
    if systemctl is-active --quiet gunicorn-armguard 2>/dev/null; then
        print_info "Stopping old Gunicorn service..."
        systemctl stop gunicorn-armguard
        systemctl disable gunicorn-armguard
        print_success "Gunicorn service stopped and disabled"
    fi
    
    if systemctl is-active --quiet armguard 2>/dev/null; then
        print_info "Stopping old armguard service..."
        systemctl stop armguard
        systemctl disable armguard
        print_success "Old armguard service stopped and disabled"
    fi
    
    # Stop Daphne service if already exists
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        print_info "Stopping existing Daphne service..."
        systemctl stop "$SERVICE_NAME"
        print_success "Existing Daphne service stopped"
    fi
}

create_systemd_service() {
    print_header "Creating Systemd Service"
    
    cat > "/etc/systemd/system/$SERVICE_FILE" << EOF
[Unit]
Description=Daphne ASGI Server for ArmGuard (WebSocket Support)
After=network.target redis.service
Wants=redis.service

[Service]
Type=notify
User=$RUN_USER
Group=$RUN_GROUP
WorkingDirectory=$PROJECT_DIR/armguard
Environment="PATH=$VENV_DIR/bin"
ExecStart=$DAPHNE_EXEC \\
    --bind $BIND_ADDRESS \\
    --port $BIND_PORT \\
    --workers $WORKERS \\
    --proxy-headers \\
    --verbosity 2 \\
    --access-log $LOG_DIR/daphne-access.log \\
    $ASGI_MODULE

# Logging
StandardOutput=append:$LOG_DIR/daphne.log
StandardError=append:$LOG_DIR/daphne-error.log

# Security
PrivateTmp=true
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$LOG_DIR
ReadWritePaths=$PROJECT_DIR/armguard/core/media

# Restart policy
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    print_success "Systemd service file created: /etc/systemd/system/$SERVICE_FILE"
}

enable_and_start_service() {
    print_header "Enabling and Starting Service"
    
    # Reload systemd daemon
    systemctl daemon-reload
    print_success "Systemd daemon reloaded"
    
    # Enable service to start on boot
    systemctl enable "$SERVICE_NAME"
    print_success "Service enabled for auto-start on boot"
    
    # Start the service
    systemctl start "$SERVICE_NAME"
    sleep 3
    
    # Check if service started successfully
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        print_success "Service started successfully"
    else
        print_error "Service failed to start"
        print_info "Check logs: journalctl -u $SERVICE_NAME -n 50"
        exit 1
    fi
}

show_status() {
    print_header "Service Status"
    
    systemctl status "$SERVICE_NAME" --no-pager || true
    
    print_header "Useful Commands"
    echo -e "${YELLOW}Service Management:${NC}"
    echo "  sudo systemctl status $SERVICE_NAME      # Check status"
    echo "  sudo systemctl stop $SERVICE_NAME        # Stop service"
    echo "  sudo systemctl start $SERVICE_NAME       # Start service"
    echo "  sudo systemctl restart $SERVICE_NAME     # Restart service"
    echo "  sudo systemctl reload $SERVICE_NAME      # Reload (if supported)"
    echo ""
    echo -e "${YELLOW}Logs:${NC}"
    echo "  sudo journalctl -u $SERVICE_NAME -f      # Follow live logs"
    echo "  sudo journalctl -u $SERVICE_NAME -n 100  # Last 100 lines"
    echo "  tail -f $LOG_DIR/daphne.log              # Application logs"
    echo "  tail -f $LOG_DIR/daphne-error.log        # Error logs"
    echo ""
    echo -e "${YELLOW}Redis:${NC}"
    echo "  sudo systemctl status redis              # Check Redis status"
    echo "  redis-cli ping                           # Test Redis connection"
    echo "  redis-cli MONITOR                        # Monitor Redis commands"
    echo ""
    echo -e "${YELLOW}Testing:${NC}"
    echo "  curl http://localhost:8000/              # Test HTTP"
    echo "  Navigate to: http://your-server/test-realtime/  # Test WebSocket"
}

############################################################
# Main Installation Flow
############################################################

main() {
    print_header "ArmGuard Daphne ASGI Service Installer"
    print_info "This will install Daphne for WebSocket support"
    print_warning "This will replace any existing Gunicorn service"
    
    check_root
    validate_environment
    create_log_directory
    stop_existing_service
    create_systemd_service
    enable_and_start_service
    show_status
    
    print_header "Installation Complete!"
    print_success "Daphne ASGI server is now running"
    print_info "WebSocket endpoints are now available"
    print_warning "Make sure to update Nginx configuration for WebSocket support"
    print_info "See: deployment/nginx-websocket.conf"
}

# Run main installation
main
