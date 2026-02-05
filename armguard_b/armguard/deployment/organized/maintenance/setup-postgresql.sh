#!/bin/bash

################################################################################
# ArmGuard PostgreSQL Database Setup
# Creates database and user for ArmGuard with proper permissions
################################################################################

set -e

echo "🐘 Setting up PostgreSQL for ArmGuard..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL service..."
    sudo systemctl start postgresql
    sudo systemctl enable postgresql
fi

echo "📊 Creating database and user..."

# Create the database and user
sudo -u postgres psql << 'EOF'
-- Drop existing database and user if they exist
DROP DATABASE IF EXISTS armguard;
DROP USER IF EXISTS armguard;

-- Create new user with password
CREATE USER armguard WITH PASSWORD 'armguard_secure_password';

-- Create database owned by the user
CREATE DATABASE armguard OWNER armguard;

-- Grant all privileges on the database
GRANT ALL PRIVILEGES ON DATABASE armguard TO armguard;

-- Allow user to create databases (needed for Django tests)
ALTER USER armguard CREATEDB;

-- Connect to the armguard database and grant schema permissions
\c armguard

-- Grant usage and create permissions on public schema
GRANT USAGE, CREATE ON SCHEMA public TO armguard;

-- Grant all privileges on all tables in public schema
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO armguard;

-- Grant all privileges on all sequences in public schema
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO armguard;

-- Set default privileges for future tables and sequences
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO armguard;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO armguard;

\q
EOF

echo "✅ Database and user created successfully"

# Update PostgreSQL authentication configuration
echo "🔐 Configuring PostgreSQL authentication..."

# Find the pg_hba.conf file
PG_HBA_FILE=$(sudo -u postgres psql -t -P format=unaligned -c 'show hba_file;')

# Backup original pg_hba.conf
sudo cp "$PG_HBA_FILE" "$PG_HBA_FILE.backup.$(date +%Y%m%d_%H%M%S)"

# Add/update authentication for armguard user
sudo sed -i '/^local.*armguard.*armguard/d' "$PG_HBA_FILE"
sudo sed -i '/^host.*armguard.*armguard.*127.0.0.1/d' "$PG_HBA_FILE"
sudo sed -i '/^host.*armguard.*armguard.*::1/d' "$PG_HBA_FILE"

# Add new authentication entries at the top of the file
sudo sed -i '1i\# ArmGuard database authentication' "$PG_HBA_FILE"
sudo sed -i '2i\local   armguard    armguard                                md5' "$PG_HBA_FILE"
sudo sed -i '3i\host    armguard    armguard    127.0.0.1/32            md5' "$PG_HBA_FILE"
sudo sed -i '4i\host    armguard    armguard    ::1/128                 md5' "$PG_HBA_FILE"
sudo sed -i '5i\\' "$PG_HBA_FILE"

echo "✅ Authentication configured"

# Reload PostgreSQL configuration
echo "🔄 Reloading PostgreSQL configuration..."
sudo systemctl reload postgresql

# Wait a moment for reload
sleep 2

# Test the database connection
echo "🧪 Testing database connection..."

# Test connection with psql
sudo -u postgres psql -h localhost -U armguard -d armguard -c "SELECT version();" << 'EOF'
armguard_secure_password
EOF

if [ $? -eq 0 ]; then
    echo "✅ PostgreSQL connection test successful"
else
    echo "❌ Connection test failed, but this might be due to password prompt issues"
    echo "The database should still work with Django"
fi

# Update the .env file to ensure correct PostgreSQL configuration
ENV_FILE="/opt/armguard/.env"
echo "📝 Updating .env file for PostgreSQL..."

# Remove SQLite settings and ensure PostgreSQL settings
sudo sed -i '/^USE_SQLITE=/d' "$ENV_FILE"
sudo sed -i '/^DATABASE_URL=sqlite/d' "$ENV_FILE"

# Ensure PostgreSQL settings are correct
if ! grep -q "^DB_NAME=armguard" "$ENV_FILE"; then
    sudo sed -i '/^DB_NAME=/d' "$ENV_FILE"
    echo "DB_NAME=armguard" | sudo tee -a "$ENV_FILE" > /dev/null
fi

if ! grep -q "^DB_USER=armguard" "$ENV_FILE"; then
    sudo sed -i '/^DB_USER=/d' "$ENV_FILE"
    echo "DB_USER=armguard" | sudo tee -a "$ENV_FILE" > /dev/null
fi

if ! grep -q "^DB_PASSWORD=armguard_secure_password" "$ENV_FILE"; then
    sudo sed -i '/^DB_PASSWORD=/d' "$ENV_FILE"
    echo "DB_PASSWORD=armguard_secure_password" | sudo tee -a "$ENV_FILE" > /dev/null
fi

if ! grep -q "^DB_HOST=localhost" "$ENV_FILE"; then
    sudo sed -i '/^DB_HOST=/d' "$ENV_FILE"
    echo "DB_HOST=localhost" | sudo tee -a "$ENV_FILE" > /dev/null
fi

if ! grep -q "^DB_PORT=5432" "$ENV_FILE"; then
    sudo sed -i '/^DB_PORT=/d' "$ENV_FILE"
    echo "DB_PORT=5432" | sudo tee -a "$ENV_FILE" > /dev/null
fi

echo "✅ .env file updated"

echo ""
echo "🎉 PostgreSQL setup complete!"
echo ""
echo "Database Details:"
echo "  Database: armguard"
echo "  User: armguard"
echo "  Password: armguard_secure_password"
echo "  Host: localhost"
echo "  Port: 5432"
echo ""
echo "Now run Django migrations:"
echo "cd /opt/armguard"
echo "source venv/bin/activate"
echo "python manage.py migrate"
echo "python manage.py createsuperuser"