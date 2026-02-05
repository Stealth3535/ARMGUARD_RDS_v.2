#!/bin/bash

################################################################################
# ArmGuard Deployment Dependency Fix Script
# Resolves package conflicts and continues deployment
################################################################################

set -e

echo "🔧 Fixing package dependencies..."

# Update package index
apt update

# Install packages in phases to avoid conflicts
echo "Phase 1: Installing Python and basic tools..."
apt install -y python3 python3-pip git curl htop

echo "Phase 2: Installing development packages..."
apt install -y build-essential
apt install -y python3-dev || echo "Skipping python3-dev (conflict)"
apt install -y python3-venv

echo "Phase 3: Installing web server..."
apt install -y nginx-light || apt install -y nginx-core || apt install -y nginx

echo "Phase 4: Installing database..."
apt install -y postgresql-common postgresql-client-common
apt install -y postgresql postgresql-contrib

echo "Phase 5: Installing Redis..."
apt install -y redis-server

echo "Phase 6: Installing security tools..."
apt install -y fail2ban supervisor

echo "Phase 7: Installing VPN tools..."
apt install -y wireguard wireguard-tools
apt install -y qrencode || echo "QR code generation may not work"

echo "✅ Dependencies resolved! Continuing with deployment..."

# Continue with the rest of the deployment
cd /home/armguard/armguard/deployment
exec ./rpi4b-vpn-deploy.sh