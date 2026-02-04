#!/bin/bash
# ArmGuard One-Time Server Setup Script
# Usage: sudo bash serversetup.sh

set -e

# 1. Update and upgrade system
sudo apt update && sudo apt upgrade -y

# 2. Install required system packages
echo "[*] Installing system packages..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib libjpeg-dev zlib1g-dev

# Detect architecture for specific optimizations
ARCH=$(uname -m)
if [[ "$ARCH" =~ ^(aarch64|arm64)$ ]]; then
    echo "[*] ARM64 architecture detected - installing ARM64 build tools..."
    sudo apt install -y build-essential gcc g++ make libffi-dev libssl-dev
    if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
        echo "[*] 🥧 Raspberry Pi detected - installing RPi-specific tools..."
        sudo apt install -y libraspberrypi-dev
    fi
fi

# 3. Create project directory and clone repo (edit URL as needed)
PROJECT_DIR="/var/www/armguard"
if [ ! -d "$PROJECT_DIR" ]; then
    sudo git clone https://github.com/Stealth3535/armguard.git "$PROJECT_DIR"
    sudo chown -R $USER:$USER "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# 4. Set up Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 5. Install Python dependencies
echo "[*] Installing Python dependencies..."
pip install --upgrade pip

# Detect environment and install appropriate requirements
if grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "[*] 🥧 Raspberry Pi detected - installing RPi optimized requirements..."
    if [ -f "requirements-rpi.txt" ]; then
        pip install -r requirements-rpi.txt
        echo "[+] RPi enhanced features enabled (psutil monitoring, thermal protection)"
    else
        pip install -r requirements.txt
        pip install psutil==5.9.8
        echo "[+] RPi optimizations applied with enhanced monitoring"
    fi
elif [[ $(uname -m) =~ ^(aarch64|arm64)$ ]]; then
    echo "[*] ARM64 architecture detected - installing ARM64 optimized requirements..."
    pip install -r requirements.txt
    pip install psutil==5.9.8
    echo "[+] ARM64 optimizations applied"
else
    echo "[*] Installing base requirements..."
    pip install -r requirements.txt
    echo "[*] Note: Some monitoring features will use fallbacks (psutil not required)"
fi

# 6. Set up environment variables
if [ ! -f .env ]; then
    cp .env.example .env
    echo "[!] Please edit .env with your production secrets before running the app!"
fi

# 7. Database setup
python manage.py migrate
python manage.py collectstatic --noinput

# 8. Create superuser (manual step)
echo "[!] Run 'python manage.py createsuperuser' to create an admin account."

# 9. Create required groups
python assign_user_groups.py

# 10. (Optional) Set up Gunicorn and Nginx (see deployment/README.md)
echo "[!] For production, configure Gunicorn and Nginx as per deployment/README.md."

echo "[+] ArmGuard server setup complete!"
