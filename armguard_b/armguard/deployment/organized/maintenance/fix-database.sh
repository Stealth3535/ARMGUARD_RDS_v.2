#!/bin/bash

################################################################################
# ArmGuard Database Configuration Fix
# Switches to SQLite and fixes database setup
################################################################################

set -e

echo "🔧 Fixing database configuration..."

PROJECT_DIR="/opt/armguard"
ENV_FILE="$PROJECT_DIR/.env"

# Option 1: Fix PostgreSQL database setup
echo "Choose database option:"
echo "1) Use SQLite (recommended for development)"
echo "2) Set up PostgreSQL properly"
read -p "Enter choice (1 or 2): " choice

case $choice in
    1)
        echo "🗄️  Configuring SQLite database..."
        
        # Update .env to force SQLite usage
        if [ -f "$ENV_FILE" ]; then
            # Remove any PostgreSQL DATABASE_URL and add SQLite
            sudo sed -i '/^DATABASE_URL=/d' "$ENV_FILE"
            echo "DATABASE_URL=sqlite:///$PROJECT_DIR/db.sqlite3" | sudo tee -a "$ENV_FILE" > /dev/null
            
            # Ensure USE_SQLITE is set to True
            sudo sed -i '/^USE_SQLITE=/d' "$ENV_FILE"
            echo "USE_SQLITE=True" | sudo tee -a "$ENV_FILE" > /dev/null
            
            echo "✅ Updated .env for SQLite"
        fi
        
        # Create empty SQLite database file with proper permissions
        touch "$PROJECT_DIR/db.sqlite3"
        chown ubuntu:www-data "$PROJECT_DIR/db.sqlite3"
        chmod 664 "$PROJECT_DIR/db.sqlite3"
        
        echo "✅ SQLite database configured"
        ;;
        
    2)
        echo "🐘 Setting up PostgreSQL database..."
        
        # Create PostgreSQL database and user
        sudo -u postgres psql << EOF
CREATE USER armguard WITH PASSWORD 'armguard_secure_password';
CREATE DATABASE armguard OWNER armguard;
GRANT ALL PRIVILEGES ON DATABASE armguard TO armguard;
ALTER USER armguard CREATEDB;
\q
EOF
        
        echo "✅ PostgreSQL database and user created"
        ;;
        
    *)
        echo "Invalid choice. Using SQLite by default..."
        choice=1
        ;;
esac

# Test database connection
echo "🧪 Testing database connection..."
cd "$PROJECT_DIR"
source venv/bin/activate

if [ "$choice" = "1" ]; then
    echo "Testing SQLite connection..."
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
print('✅ SQLite connection successful')
"
else
    echo "Testing PostgreSQL connection..."
    python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
print('✅ PostgreSQL connection successful')
"
fi

echo ""
echo "✅ Database configuration fixed!"
echo ""
echo "Now run the migrations:"
echo "cd /opt/armguard"
echo "source venv/bin/activate"
echo "python manage.py migrate"
echo "python manage.py createsuperuser"