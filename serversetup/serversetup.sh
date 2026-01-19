#!/bin/bash
# ArmGuard One-Time Server Setup Script
# Usage: sudo bash serversetup.sh

set -e

# 1. Update and upgrade system
sudo apt update && sudo apt upgrade -y

# 2. Install required system packages
sudo apt install -y python3 python3-pip python3-venv git nginx postgresql postgresql-contrib libjpeg-dev zlib1g-dev

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
pip install --upgrade pip
pip install -r requirements.txt

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
