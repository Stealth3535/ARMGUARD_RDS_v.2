#!/bin/bash

################################################################################
# ArmGuard Permission Fix Script
# Fixes file permissions for .env and project files
################################################################################

set -e

echo "🔧 Fixing file permissions..."

PROJECT_DIR="/opt/armguard"

# Check if .env file exists
if [ -f "$PROJECT_DIR/.env" ]; then
    echo "Fixing .env file permissions..."
    
    # Make .env readable by the current user but still secure
    sudo chown ubuntu:www-data "$PROJECT_DIR/.env"
    sudo chmod 640 "$PROJECT_DIR/.env"
    
    echo "✅ Fixed .env file permissions"
else
    echo "❌ .env file not found at $PROJECT_DIR/.env"
    echo "Creating .env file with proper permissions..."
    
    SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    LAN_IP=$(hostname -I | cut -d' ' -f1)
    
    sudo tee "$PROJECT_DIR/.env" > /dev/null << EOF
# Django Configuration
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$LAN_IP,*.local,10.0.0.*

# Database Configuration (SQLite for development)
DATABASE_URL=sqlite://$PROJECT_DIR/db.sqlite3
DB_NAME=armguard
DB_USER=armguard
DB_PASSWORD=armguard_secure_password
DB_HOST=localhost
DB_PORT=5432

# VPN Integration
WIREGUARD_ENABLED=True
VPN_NETWORK=10.0.0.0/24
VPN_SERVER_IP=10.0.0.1

# Network Security
ENFORCE_LAN_TRANSACTIONS=True
LAN_SUBNET=192.168.0.0/16

# Additional Django settings
USE_SQLITE=True
DEBUG_TOOLBAR=False
EOF
    
    # Set proper permissions
    sudo chown ubuntu:www-data "$PROJECT_DIR/.env"
    sudo chmod 640 "$PROJECT_DIR/.env"
    
    echo "✅ Created .env file with proper permissions"
fi

# Fix other project file permissions
echo "Fixing project directory permissions..."
sudo chown -R ubuntu:www-data "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"

# Make sure database directory is writable
sudo mkdir -p "$PROJECT_DIR"
sudo chown ubuntu:www-data "$PROJECT_DIR"

# Make sure log directory exists and is writable
sudo mkdir -p "$PROJECT_DIR/logs"
sudo chown ubuntu:www-data "$PROJECT_DIR/logs"

# Make sure static/media directories exist
sudo mkdir -p /var/www/armguard/{static,media}
sudo chown -R www-data:www-data /var/www/armguard

echo "✅ All permissions fixed!"
echo ""
echo "Now you can run Django commands:"
echo "cd /opt/armguard"
echo "source venv/bin/activate"
echo "python manage.py migrate"