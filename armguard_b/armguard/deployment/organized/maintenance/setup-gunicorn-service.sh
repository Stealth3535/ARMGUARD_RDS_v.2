#!/bin/bash

################################################################################
# ArmGuard Gunicorn Service Setup
# Creates and configures the systemd service for ArmGuard Django application
################################################################################

set -e

echo "🔧 Setting up ArmGuard Gunicorn service..."

PROJECT_DIR="/opt/armguard"
SERVICE_FILE="/etc/systemd/system/armguard.service"

# Create systemd service file
echo "📝 Creating systemd service file..."

sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=ArmGuard Django Application
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=armguard
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind unix:/run/armguard/armguard.sock core.wsgi:application --access-logfile /var/log/armguard/access.log --error-logfile /var/log/armguard/error.log
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStopSec=5
KillMode=mixed
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Service file created"

# Create log directory
echo "📁 Creating log directories..."
sudo mkdir -p /var/log/armguard
sudo chown www-data:www-data /var/log/armguard

# Create runtime directory for socket
echo "📁 Creating runtime directory..."
sudo mkdir -p /run/armguard
sudo chown www-data:www-data /run/armguard

# Reload systemd and enable service
echo "🔄 Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable armguard.service

# Test the service configuration
echo "🧪 Testing service configuration..."
sudo systemctl start armguard.service

# Wait a moment for the service to start
sleep 3

# Check service status
echo "📊 Checking service status..."
if sudo systemctl is-active --quiet armguard.service; then
    echo "✅ ArmGuard service is running successfully"
    sudo systemctl status armguard.service --no-pager -l
else
    echo "❌ Service failed to start. Checking logs..."
    sudo journalctl -u armguard.service --no-pager -l
    echo ""
    echo "🔧 Troubleshooting steps:"
    echo "1. Check if virtual environment exists: ls -la $PROJECT_DIR/venv"
    echo "2. Check if Django project is in place: ls -la $PROJECT_DIR/core"
    echo "3. Test Gunicorn manually:"
    echo "   cd $PROJECT_DIR"
    echo "   source venv/bin/activate"
    echo "   gunicorn --bind 127.0.0.1:8000 core.wsgi:application"
fi

echo ""
echo "🌐 Next steps:"
echo "1. Check service status: sudo systemctl status armguard"
echo "2. View logs: sudo journalctl -u armguard -f"
echo "3. Test web access: curl http://localhost"
echo "4. Check Nginx configuration: sudo nginx -t"