#!/bin/bash
# ArmGuard VM Shared Folder Setup Script
# For VMware virtual machines using shared folders
# Usage: bash vmsetup.sh

set -e

echo "[*] ArmGuard VM Setup - Shared Folder Mode"
echo "==========================================="

# 1. Mount VMware shared folder
MOUNT_POINT="/mnt/hgfs"
SHARE_NAME="Armguard"

if [ ! -d "$MOUNT_POINT" ]; then
    sudo mkdir -p "$MOUNT_POINT"
fi

echo "[*] Mounting VMware shared folder..."
sudo vmhgfs-fuse .host:/$SHARE_NAME $MOUNT_POINT -o allow_other

# Verify mount
if [ -d "$MOUNT_POINT/$SHARE_NAME" ]; then
    echo "[+] Shared folder mounted successfully at $MOUNT_POINT/$SHARE_NAME"
else
    echo "[!] Warning: Shared folder may not be accessible. Check VMware sharing settings."
fi

# 2. Create virtual environment if it doesn't exist
VENV_DIR="$HOME/armguard"
if [ ! -d "$VENV_DIR" ]; then
    echo "[*] Creating Python virtual environment at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# 3. Activate virtual environment
echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# 4. Change to project directory
PROJECT_DIR="$MOUNT_POINT/$SHARE_NAME/armguard"
cd "$PROJECT_DIR"
echo "[*] Working directory: $(pwd)"

# 5. Install/update dependencies
echo "[*] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Run migrations
echo "[*] Running database migrations..."
python manage.py migrate

# 7. Collect static files
echo "[*] Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "[+] ArmGuard VM setup complete!"
echo ""
echo "To start the development server, run:"
echo "  python manage.py runserver 0.0.0.0:8000"
echo ""
echo "To re-activate the environment later:"
echo "  sudo vmhgfs-fuse .host:/$SHARE_NAME $MOUNT_POINT -o allow_other"
echo "  source ~/armguard/bin/activate"
echo "  cd $PROJECT_DIR"
