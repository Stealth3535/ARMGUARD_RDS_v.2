#!/bin/bash

################################################################################
# ArmGuard Environment Fix Script
# Fixes missing database configuration in .env file
################################################################################

set -e

echo "🔧 Fixing environment configuration..."

PROJECT_DIR="/opt/armguard"
ENV_FILE="$PROJECT_DIR/.env"

# Check if .env file exists
if [ -f "$ENV_FILE" ]; then
    echo "Found existing .env file, adding missing database variables..."
    
    # Add missing database variables if they don't exist
    if ! grep -q "DB_PASSWORD" "$ENV_FILE"; then
        echo "" >> "$ENV_FILE"
        echo "# Database Configuration" >> "$ENV_FILE"
        echo "DB_NAME=armguard" >> "$ENV_FILE"
        echo "DB_USER=armguard" >> "$ENV_FILE"
        echo "DB_PASSWORD=armguard_secure_password" >> "$ENV_FILE"
        echo "DB_HOST=localhost" >> "$ENV_FILE"
        echo "DB_PORT=5432" >> "$ENV_FILE"
        echo "USE_SQLITE=True" >> "$ENV_FILE"
        echo "✅ Added missing database configuration"
    else
        echo "✅ Database configuration already exists"
    fi
else
    echo "❌ .env file not found at $ENV_FILE"
    echo "Creating new .env file..."
    
    SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    LAN_IP=$(hostname -I | cut -d' ' -f1)
    
    cat > "$ENV_FILE" << EOF
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
    
    echo "✅ Created complete .env file"
fi

# Fix file permissions
chown www-data:www-data "$ENV_FILE"
chmod 600 "$ENV_FILE"

echo "✅ Environment configuration fixed!"
echo ""
echo "Now retry the database migration:"
echo "cd $PROJECT_DIR"
echo "source venv/bin/activate"
echo "python manage.py migrate"