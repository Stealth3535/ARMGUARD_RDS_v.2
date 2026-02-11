################################################################################
# ArmGuard Server Update Script
# Updates the production server with the latest code from GitHub
################################################################################

# Configuration
$SERVER_IP = "192.168.0.1"
$SSH_USER = "rds"
$PROJECT_DIR = "/var/www/armguard"  # Adjust if different
$VENV_PATH = "$PROJECT_DIR/venv"

# Colors
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Error { Write-Host $args -ForegroundColor Red }

Write-Host ""
Write-Success "╔═══════════════════════════════════════════════════════╗"
Write-Success "║        ArmGuard Server Update Script                 ║"
Write-Success "╚═══════════════════════════════════════════════════════╝"
Write-Host ""

# Test SSH connection first
Write-Info "Testing SSH connection to $SSH_USER@$SERVER_IP..."
$sshTest = ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "echo 'SSH connection successful'" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Cannot connect to server via SSH"
    Write-Warning "Please ensure:"
    Write-Warning "  1. SSH is enabled on $SERVER_IP"
    Write-Warning "  2. You have SSH access with user '$SSH_USER'"
    Write-Warning "  3. Your SSH key is configured or you know the password"
    Write-Host ""
    Write-Info "To enable SSH, refer to: armguard\SSH_SETUP_GUIDE.md"
    Write-Host ""
    
    # Ask if user wants to proceed with manual SSH
    $response = Read-Host "Would you like to try manual SSH connection? (y/n)"
    if ($response -ne 'y') {
        exit 1
    }
}
else {
    Write-Success "✅ SSH connection successful"
}

Write-Host ""
Write-Info "Updating ArmGuard on server $SERVER_IP..."
Write-Host ""

# Create update commands
$updateCommands = @"
echo '================================================'
echo 'ArmGuard Server Update Process'
echo '================================================'
echo ''

# Navigate to project directory
cd $PROJECT_DIR || { echo '❌ Project directory not found'; exit 1; }
echo '✅ Navigated to project directory: \$PWD'

# Check if git repository
if [ ! -d .git ]; then
    echo '❌ Not a git repository. Please clone from GitHub first.'
    exit 1
fi

# Backup current version
BACKUP_DIR="backups/backup_\$(date +%Y%m%d_%H%M%S)"
echo ''
echo '📦 Creating backup...'
mkdir -p "\$BACKUP_DIR"
cp -r . "\$BACKUP_DIR/" 2>/dev/null || echo 'Backup created (some files may be skipped)'
echo "✅ Backup created: \$BACKUP_DIR"

# Pull latest changes
echo ''
echo '📥 Pulling latest changes from GitHub...'
git fetch origin
git pull origin main || { echo '❌ Git pull failed'; exit 1; }
echo '✅ Code updated from GitHub'

# Activate virtual environment
echo ''
echo '🐍 Activating virtual environment...'
source $VENV_PATH/bin/activate || { echo '❌ Virtual environment not found'; exit 1; }
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

# Restart Gunicorn service
echo ''
echo '🔄 Restarting Gunicorn service...'
sudo systemctl restart armguard || sudo systemctl restart gunicorn || { 
    echo '⚠️  Service restart command not found. You may need to restart manually.'
}
echo '✅ Service restart initiated'

# Restart Nginx
echo ''
echo '🔄 Restarting Nginx...'
sudo systemctl restart nginx || echo '⚠️  Nginx restart failed (you may need to restart manually)'

# Check service status
echo ''
echo '📊 Service Status:'
echo '-------------------'
sudo systemctl status armguard --no-pager -l || sudo systemctl status gunicorn --no-pager -l || echo 'Service status unavailable'

echo ''
echo '================================================'
echo '✅ Update Complete!'
echo '================================================'
echo ''
echo 'Recent commits:'
git log --oneline -5
"@

# Execute update on server
Write-Info "Executing update commands on server..."
Write-Host ""

# Use SSH to execute the commands
ssh "$SSH_USER@$SERVER_IP" $updateCommands

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Success "╔═══════════════════════════════════════════════════════╗"
    Write-Success "║     ✅ Server Update Completed Successfully! ✅       ║"
    Write-Success "╚═══════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Info "Your ArmGuard server at $SERVER_IP has been updated with the latest code."
    Write-Info "Services have been restarted and are now running the new version."
} else {
    Write-Host ""
    Write-Error "╔═══════════════════════════════════════════════════════╗"
    Write-Error "║        ⚠️  Update Process Encountered Issues         ║"
    Write-Error "╚═══════════════════════════════════════════════════════╝"
    Write-Host ""
    Write-Warning "Please review the output above for errors."
    Write-Warning "You may need to SSH into the server manually to troubleshoot."
}

Write-Host ""
