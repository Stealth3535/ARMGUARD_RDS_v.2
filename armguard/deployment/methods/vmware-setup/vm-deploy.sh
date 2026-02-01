#!/bin/bash

# =============================================================================
# ArmGuard VM Deployment Script (VMware Environment)
# Designed for test VM with shared folder setup
# =============================================================================

set -e

# Source master configuration
source "../../master-config.sh"

# VM-specific configuration
VM_SHARED_FOLDER="/mnt/hgfs/Armguard"
VM_MOUNT_POINT="/mnt/hgfs"
PROJECT_DIR="$VM_SHARED_FOLDER/armguard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}           ArmGuard VM Deployment (Test Environment)         ${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo

# =============================================================================
# VMware Tools Setup
# =============================================================================

install_vmware_tools() {
    echo -e "${BLUE}Installing VMware Tools...${NC}"
    
    if ! command -v vmhgfs-fuse &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y open-vm-tools open-vm-tools-desktop
        echo -e "${GREEN}✓ VMware Tools installed${NC}"
    else
        echo -e "${GREEN}✓ VMware Tools already installed${NC}"
    fi
}

# =============================================================================
# Shared Folder Setup
# =============================================================================

setup_shared_folder() {
    echo -e "${BLUE}Setting up VMware shared folder...${NC}"
    
    # Create mount point
    sudo mkdir -p $VM_MOUNT_POINT
    
    # Mount shared folder
    if ! mountpoint -q $VM_MOUNT_POINT; then
        sudo vmhgfs-fuse .host:/Armguard $VM_MOUNT_POINT -o allow_other
        echo -e "${GREEN}✓ Shared folder mounted at $VM_MOUNT_POINT${NC}"
    else
        echo -e "${GREEN}✓ Shared folder already mounted${NC}"
    fi
    
    # Verify project directory exists
    if [ ! -d "$PROJECT_DIR" ]; then
        echo -e "${RED}✗ Project directory not found: $PROJECT_DIR${NC}"
        echo "Make sure the host machine has shared the Armguard folder"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Project found at: $PROJECT_DIR${NC}"
}

# =============================================================================
# System Dependencies
# =============================================================================

install_dependencies() {
    echo -e "${BLUE}Installing system dependencies...${NC}"
    
    sudo apt-get update
    sudo apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        postgresql \
        postgresql-contrib \
        redis-server \
        nginx \
        git \
        curl \
        unzip
    
    echo -e "${GREEN}✓ System dependencies installed${NC}"
}

# =============================================================================
# Database Setup (Test Environment)
# =============================================================================

setup_test_database() {
    echo -e "${BLUE}Setting up test database...${NC}"
    
    # Use test database configuration
    DB_NAME="${TEST_DB_NAME:-armguard_test}"
    DB_USER="${TEST_DB_USER:-armguard_test}"
    DB_PASS="${TEST_DB_PASS:-test_password123}"
    
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" || true
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" || true
    sudo -u postgres psql -c "ALTER USER $DB_USER CREATEDB;" || true
    
    echo -e "${GREEN}✓ Test database configured${NC}"
}

# =============================================================================
# Application Setup
# =============================================================================

setup_application() {
    echo -e "${BLUE}Setting up ArmGuard application...${NC}"
    
    cd "$PROJECT_DIR"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install Python dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Setup environment for testing
    cat > .env << EOF
# Test Environment Configuration
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,$(hostname -I | awk '{print $1}')

# Test Database
DATABASE_NAME=$DB_NAME
DATABASE_USER=$DB_USER
DATABASE_PASSWORD=$DB_PASS
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Test Secret Key (not for production!)
SECRET_KEY=test-secret-key-for-vm-development-only

# Test Redis
REDIS_URL=redis://localhost:6379/1

# Testing flags
TESTING=True
VM_ENVIRONMENT=True
EOF
    
    # Run migrations
    python manage.py migrate
    
    # Create test superuser
    python manage.py shell << 'PYTHON_SCRIPT'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@test.local', 'admin123')
    print("Test superuser created: admin/admin123")
PYTHON_SCRIPT
    
    # Collect static files
    python manage.py collectstatic --noinput
    
    echo -e "${GREEN}✓ Application configured for testing${NC}"
}

# =============================================================================
# Test Services Configuration
# =============================================================================

configure_test_services() {
    echo -e "${BLUE}Configuring services for test environment...${NC}"
    
    # Configure nginx for testing
    sudo tee /etc/nginx/sites-available/armguard-test << EOF
server {
    listen 80;
    server_name localhost $(hostname -I | awk '{print $1}');
    
    location /static/ {
        alias $PROJECT_DIR/staticfiles/;
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
    }
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Enable the site
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -sf /etc/nginx/sites-available/armguard-test /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl restart nginx
    
    # Start services
    sudo systemctl enable postgresql redis-server nginx
    sudo systemctl start postgresql redis-server nginx
    
    echo -e "${GREEN}✓ Test services configured${NC}"
}

# =============================================================================
# Main Deployment
# =============================================================================

main() {
    echo -e "${YELLOW}Starting VM deployment for test environment...${NC}"
    echo
    
    install_vmware_tools
    echo
    
    setup_shared_folder
    echo
    
    install_dependencies
    echo
    
    setup_test_database
    echo
    
    setup_application
    echo
    
    configure_test_services
    echo
    
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}           VM Deployment Complete!                           ${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo
    echo -e "${GREEN}Test environment ready:${NC}"
    echo "  • Application: http://$(hostname -I | awk '{print $1}')"
    echo "  • Admin: http://$(hostname -I | awk '{print $1}')/admin"
    echo "  • Credentials: admin/admin123"
    echo "  • Project Path: $PROJECT_DIR"
    echo
    echo -e "${YELLOW}To start development server manually:${NC}"
    echo "  cd $PROJECT_DIR"
    echo "  source venv/bin/activate"
    echo "  python manage.py runserver 0.0.0.0:8000"
    echo
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run this script as root${NC}"
    echo "Run as regular user - sudo will be used when needed"
    exit 1
fi

# Run main function
main "$@"