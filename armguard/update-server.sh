#!/bin/bash

################################################################################
# ArmGuard Server Update Script (Linux/WSL/Git Bash)
# Updates the production server with the latest code from GitHub
################################################################################

# Configuration
SERVER_IP="${SERVER_IP:-192.168.0.1}"
SSH_USER="${SSH_USER:-rds}"
PROJECT_DIR="${PROJECT_DIR:-/var/www/armguard}"
VENV_PATH="$PROJECT_DIR/venv"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_success() { echo -e "${GREEN}$1${NC}"; }
log_info() { echo -e "${CYAN}$1${NC}"; }
log_warn() { echo -e "${YELLOW}$1${NC}"; }
log_error() { echo -e "${RED}$1${NC}"; }

echo ""
log_success "╔═══════════════════════════════════════════════════════╗"
log_success "║        ArmGuard Server Update Script                 ║"
log_success "╚═══════════════════════════════════════════════════════╝"
echo ""

# Test SSH connection
log_info "Testing SSH connection to $SSH_USER@$SERVER_IP..."
if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "echo 'SSH connection successful'" >/dev/null 2>&1; then
    log_success "✅ SSH connection successful"
else
    log_error "❌ Cannot connect to server via SSH"
    log_warn "Please ensure:"
    log_warn "  1. SSH is enabled on $SERVER_IP"
    log_warn "  2. You have SSH access with user '$SSH_USER'"
    log_warn "  3. Your SSH key is configured or you know the password"
    echo ""
    log_info "To enable SSH, refer to: armguard/SSH_SETUP_GUIDE.md"
    echo ""
    exit 1
fi

echo ""
log_info "Updating ArmGuard on server $SERVER_IP..."
echo ""

# Update commands to execute on remote server
ssh "$SSH_USER@$SERVER_IP" bash << 'ENDSSH'
set -e

echo '================================================'
echo 'ArmGuard Server Update Process'
echo '================================================'
echo ''

# Navigate to project directory
PROJECT_DIR="${PROJECT_DIR:-/var/www/armguard}"
cd "$PROJECT_DIR" || { echo '❌ Project directory not found'; exit 1; }
echo "✅ Navigated to project directory: $PWD"

# Check if git repository
if [ ! -d .git ]; then
    echo '❌ Not a git repository. Please clone from GitHub first.'
    exit 1
fi

# Backup current version
BACKUP_DIR="backups/backup_$(date +%Y%m%d_%H%M%S)"
echo ''
echo '📦 Creating backup...'
mkdir -p "$BACKUP_DIR"
cp -r . "$BACKUP_DIR/" 2>/dev/null || echo 'Backup created (some files may be skipped)'
echo "✅ Backup created: $BACKUP_DIR"

# Pull latest changes
echo ''
echo '📥 Pulling latest changes from GitHub...'
git fetch origin
git pull origin main || { echo '❌ Git pull failed'; exit 1; }
echo '✅ Code updated from GitHub'

# Activate virtual environment
echo ''
echo '🐍 Activating virtual environment...'
VENV_PATH="${VENV_PATH:-$PROJECT_DIR/venv}"
source "$VENV_PATH/bin/activate" || { echo '❌ Virtual environment not found'; exit 1; }
echo '✅ Virtual environment activated'

# Update Python dependencies
echo ''
echo '📦 Updating Python dependencies...'
pip install -r requirements.txt --upgrade
echo '✅ Dependencies updated'

# Run database migrations
echo ''
echo '🗄️  Running database migrations...'
python manage.py migrate
echo '✅ Migrations complete'

# Collect static files
echo ''
echo '📁 Collecting static files...'
python manage.py collectstatic --noinput
echo '✅ Static files collected'

# Restart services
echo ''
echo '🔄 Restarting services...'

# Try different service names
if sudo systemctl restart armguard 2>/dev/null; then
    echo '✅ ArmGuard service restarted'
elif sudo systemctl restart gunicorn 2>/dev/null; then
    echo '✅ Gunicorn service restarted'
else
    echo '⚠️  Could not find service to restart. You may need to restart manually.'
fi

# Restart Nginx
if sudo systemctl restart nginx 2>/dev/null; then
    echo '✅ Nginx restarted'
else
    echo '⚠️  Nginx restart failed (you may need to restart manually)'
fi

# Check service status
echo ''
echo '📊 Service Status:'
echo '-------------------'
sudo systemctl status armguard --no-pager -l 2>/dev/null || \
sudo systemctl status gunicorn --no-pager -l 2>/dev/null || \
echo 'Service status unavailable'

echo ''
echo '================================================'
echo '✅ Update Complete!'
echo '================================================'
echo ''
echo 'Recent commits:'
git log --oneline -5

ENDSSH

if [ $? -eq 0 ]; then
    echo ""
    log_success "╔═══════════════════════════════════════════════════════╗"
    log_success "║     ✅ Server Update Completed Successfully! ✅       ║"
    log_success "╚═══════════════════════════════════════════════════════╝"
    echo ""
    log_info "Your ArmGuard server at $SERVER_IP has been updated with the latest code."
    log_info "Services have been restarted and are now running the new version."
else
    echo ""
    log_error "╔═══════════════════════════════════════════════════════╗"
    log_error "║        ⚠️  Update Process Encountered Issues         ║"
    log_error "╚═══════════════════════════════════════════════════════╝"
    echo ""
    log_warn "Please review the output above for errors."
    log_warn "You may need to SSH into the server manually to troubleshoot."
fi

echo ""
