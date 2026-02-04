#!/bin/bash

################################################################################
# Raspberry Pi Test Deployment Script for ArmGuard A+ Performance Edition
# 
# This script deploys ArmGuard v2.1.0-aplus to Raspberry Pi for testing
# Includes all A+ performance optimizations and comprehensive testing
################################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# RPi Configuration Detection
detect_rpi_config() {
    log "🔍 Detecting Raspberry Pi Configuration..."
    
    # Check if running on RPi
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        export IS_RASPBERRY_PI=true
        RPi_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown RPi")
        log "✅ Detected: $RPi_MODEL"
    else
        export IS_RASPBERRY_PI=false
        warn "Not running on Raspberry Pi - using RPi-compatible settings anyway"
    fi
    
    # Memory detection
    TOTAL_MEMORY_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_MEMORY_MB=$((TOTAL_MEMORY_KB / 1024))
    TOTAL_MEMORY_GB=$((TOTAL_MEMORY_MB / 1024))
    
    log "💾 System Memory: ${TOTAL_MEMORY_MB}MB (${TOTAL_MEMORY_GB}GB)"
    
    # Set RPi-optimized configurations based on memory
    if [ $TOTAL_MEMORY_MB -lt 2048 ]; then
        export MEMORY_PROFILE="low"
        export GUNICORN_WORKERS=2
        export DB_POOL_SIZE=5
        warn "Low memory configuration applied"
    elif [ $TOTAL_MEMORY_MB -lt 4096 ]; then
        export MEMORY_PROFILE="medium"
        export GUNICORN_WORKERS=3
        export DB_POOL_SIZE=10
        log "Medium memory configuration applied"
    else
        export MEMORY_PROFILE="high"
        export GUNICORN_WORKERS=4
        export DB_POOL_SIZE=20
        log "High memory configuration applied"
    fi
}

# Update system packages
update_system() {
    log "📦 Updating Raspberry Pi system packages..."
    
    sudo apt update
    sudo apt upgrade -y
    
    # Install essential packages for RPi
    sudo apt install -y \
        python3 python3-pip python3-venv python3-dev \
        nginx postgresql postgresql-contrib \
        git curl wget htop tree \
        build-essential libpq-dev \
        redis-server \
        supervisor \
        ufw fail2ban \
        mkcert
        
    log "✅ System packages updated"
}

# Configure RPi-specific optimizations
configure_rpi_optimizations() {
    log "⚡ Configuring Raspberry Pi optimizations..."
    
    # GPU memory split (more RAM for applications)
    if [ "$IS_RASPBERRY_PI" = true ]; then
        sudo sh -c 'echo "gpu_mem=16" >> /boot/config.txt'
        log "✅ GPU memory reduced to 16MB (more RAM for ArmGuard)"
    fi
    
    # Swap file optimization
    if [ $TOTAL_MEMORY_MB -lt 4096 ]; then
        sudo dphys-swapfile swapoff
        sudo sh -c 'echo "CONF_SWAPSIZE=1024" > /etc/dphys-swapfile'
        sudo dphys-swapfile setup
        sudo dphys-swapfile swapon
        log "✅ Swap file optimized for ArmGuard"
    fi
    
    # I/O scheduler optimization for SD card
    echo mq-deadline | sudo tee /sys/block/mmcblk0/queue/scheduler > /dev/null 2>&1 || true
    log "✅ I/O scheduler optimized"
}

# Clone ArmGuard repository with A+ performance optimizations
clone_armguard() {
    log "📥 Cloning ArmGuard v2.1.0-aplus from GitHub..."
    
    # Set deployment directory
    export DEPLOY_DIR="/opt/armguard"
    
    # Remove existing directory if it exists
    if [ -d "$DEPLOY_DIR" ]; then
        warn "Removing existing ArmGuard installation..."
        sudo rm -rf "$DEPLOY_DIR"
    fi
    
    # Clone the repository
    sudo git clone https://github.com/Stealth3535/ARMGUARD_RDS.git "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
    
    # Use main branch (contains latest A+ performance optimizations)
    sudo git checkout main
    
    # Set proper permissions
    sudo chown -R $(whoami):$(whoami) "$DEPLOY_DIR"
    
    log "✅ ArmGuard v2.1.0-aplus cloned successfully"
}

# Setup Python virtual environment with A+ performance packages
setup_python_environment() {
    log "🐍 Setting up Python environment with A+ performance packages..."
    
    cd "$DEPLOY_DIR/armguard"
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install A+ performance optimized requirements
    pip install -r requirements.txt
    
    # Additional performance packages for RPi
    pip install \
        psutil \
        redis \
        django-redis \
        whitenoise \
        gunicorn \
        supervisor
    
    log "✅ Python environment with A+ performance packages ready"
}

# Configure database with A+ performance optimizations
setup_database() {
    log "🗄️ Setting up database with A+ performance optimizations..."
    
    cd "$DEPLOY_DIR/armguard"
    source venv/bin/activate
    
    # Run database migrations
    python manage.py makemigrations
    python manage.py migrate
    
    # Create superuser for testing
    echo "Creating admin user for testing..."
    python manage.py shell << 'EOF'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@armguard.test', 'ArmGuard2024!')
    print("✅ Admin user created: admin / ArmGuard2024!")
else:
    print("✅ Admin user already exists")
EOF

    # Collect static files with compression
    python manage.py collectstatic --noinput --clear
    
    log "✅ Database configured with A+ optimizations"
}

# Configure Redis for A+ performance caching
setup_redis_cache() {
    log "🔄 Configuring Redis for A+ performance caching..."
    
    # Configure Redis for RPi
    sudo sh -c 'cat > /etc/redis/redis.conf << EOF
# Redis configuration optimized for Raspberry Pi + ArmGuard A+
port 6379
bind 127.0.0.1
protected-mode yes
tcp-keepalive 300
timeout 0

# Memory optimizations for RPi
maxmemory 128mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000

# Persistence optimizations
dir /var/lib/redis
dbfilename armguard-dump.rdb
EOF'

    # Start and enable Redis
    sudo systemctl enable redis-server
    sudo systemctl restart redis-server
    
    log "✅ Redis configured for A+ performance caching"
}

# Configure Nginx with A+ performance settings
setup_nginx() {
    log "🌐 Configuring Nginx with A+ performance settings..."
    
    # Create ArmGuard Nginx configuration
    sudo sh -c "cat > /etc/nginx/sites-available/armguard << 'EOF'
# ArmGuard A+ Performance Nginx Configuration for Raspberry Pi
upstream armguard {
    server unix:/opt/armguard/armguard.sock;
}

server {
    listen 80;
    listen 443 ssl http2;
    server_name armguard.test localhost $(hostname -I | awk '{print $1}');
    
    # SSL Configuration (self-signed for testing)
    ssl_certificate /etc/ssl/certs/armguard-test.crt;
    ssl_certificate_key /etc/ssl/private/armguard-test.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # A+ Performance headers
    add_header X-Frame-Options \"DENY\" always;
    add_header X-Content-Type-Options \"nosniff\" always;
    add_header X-XSS-Protection \"1; mode=block\" always;
    add_header Referrer-Policy \"strict-origin-when-cross-origin\" always;
    add_header Cache-Control \"public, max-age=31536000\" always;
    
    # Gzip compression (A+ performance)
    gzip on;
    gzip_comp_level 6;
    gzip_min_length 1000;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    
    # Static files with long-term caching
    location /static/ {
        alias /opt/armguard/armguard/staticfiles/;
        expires 1y;
        add_header Cache-Control \"public, immutable\";
    }
    
    location /media/ {
        alias /opt/armguard/armguard/core/media/;
        expires 1y;
        add_header Cache-Control \"public, immutable\";
    }
    
    # Main application
    location / {
        include proxy_params;
        proxy_pass http://armguard;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # Health check endpoint
    location /health/ {
        access_log off;
        return 200 \"healthy\";
        add_header Content-Type text/plain;
    }
}
EOF"

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Generate self-signed SSL certificate for testing
    sudo mkdir -p /etc/ssl/private
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/ssl/private/armguard-test.key \
        -out /etc/ssl/certs/armguard-test.crt \
        -subj "/C=US/ST=Test/L=Test/O=ArmGuard/OU=Testing/CN=armguard.test"
    
    # Test and reload Nginx
    sudo nginx -t && sudo systemctl reload nginx
    
    log "✅ Nginx configured with A+ performance settings"
}

# Configure Gunicorn with RPi optimizations
setup_gunicorn() {
    log "🔧 Configuring Gunicorn with RPi A+ optimizations..."
    
    # Create Gunicorn configuration
    cat > "$DEPLOY_DIR/armguard/gunicorn.conf.py" << EOF
# Gunicorn configuration optimized for Raspberry Pi A+ performance
import multiprocessing

# Server socket
bind = "unix:/opt/armguard/armguard.sock"
backlog = 2048

# Worker processes
workers = $GUNICORN_WORKERS
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 30
keepalive = 2

# Restart workers after serving this many requests (memory optimization)
max_requests = 1000

# Logging
accesslog = "/var/log/armguard/gunicorn-access.log"
errorlog = "/var/log/armguard/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'armguard-aplus'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Performance tuning for RPi
worker_tmp_dir = '/dev/shm'
EOF

    # Create systemd service
    sudo sh -c "cat > /etc/systemd/system/armguard.service << 'EOF'
[Unit]
Description=ArmGuard A+ Performance Edition
Requires=armguard.socket
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=armguard
WorkingDirectory=/opt/armguard/armguard
Environment=DJANGO_SETTINGS_MODULE=core.settings
ExecStart=/opt/armguard/armguard/venv/bin/gunicorn \
    --pid /run/armguard/armguard.pid \
    --config /opt/armguard/armguard/gunicorn.conf.py \
    core.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF"

    # Create socket file
    sudo sh -c "cat > /etc/systemd/system/armguard.socket << 'EOF'
[Unit]
Description=ArmGuard A+ Performance Edition Socket

[Socket]
ListenStream=/opt/armguard/armguard.sock
SocketUser=www-data

[Install]
WantedBy=sockets.target
EOF"

    # Set permissions and enable service
    sudo mkdir -p /var/log/armguard
    sudo chown www-data:www-data /var/log/armguard
    sudo chown -R www-data:www-data "$DEPLOY_DIR"
    
    sudo systemctl daemon-reload
    sudo systemctl enable armguard.socket
    sudo systemctl enable armguard.service
    
    log "✅ Gunicorn configured with RPi A+ optimizations"
}

# Run comprehensive tests
run_comprehensive_tests() {
    log "🧪 Running comprehensive A+ performance tests..."
    
    cd "$DEPLOY_DIR/armguard"
    source venv/bin/activate
    
    # Run the comprehensive test suite
    python comprehensive_test_suite.py
    
    # Run A+ performance validation
    python performance_grade_test.py
    
    log "✅ Comprehensive tests completed"
}

# Start all services
start_services() {
    log "🚀 Starting all ArmGuard A+ services..."
    
    sudo systemctl start redis-server
    sudo systemctl start postgresql
    sudo systemctl start armguard.socket
    sudo systemctl start armguard.service
    sudo systemctl start nginx
    
    # Wait a moment for services to start
    sleep 5
    
    # Check service status
    log "📊 Service Status:"
    sudo systemctl is-active redis-server && echo "✅ Redis: Running" || echo "❌ Redis: Failed"
    sudo systemctl is-active postgresql && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Failed"
    sudo systemctl is-active armguard.service && echo "✅ ArmGuard: Running" || echo "❌ ArmGuard: Failed"
    sudo systemctl is-active nginx && echo "✅ Nginx: Running" || echo "❌ Nginx: Failed"
    
    log "✅ All services started"
}

# Display deployment summary
show_deployment_summary() {
    log "🎉 ArmGuard A+ Performance Deployment Complete!"
    
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}          ArmGuard v2.1.0-aplus Deployment Summary${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}🌐 Access URLs:${NC}"
    echo -e "   • Local:     http://${LOCAL_IP}"
    echo -e "   • HTTPS:     https://${LOCAL_IP} (self-signed)"
    echo -e "   • Admin:     https://${LOCAL_IP}/admin"
    echo -e "   • Hostname:  http://$(hostname).local"
    echo ""
    echo -e "${GREEN}🔑 Admin Credentials:${NC}"
    echo -e "   • Username: admin"
    echo -e "   • Password: ArmGuard2024!"
    echo ""
    echo -e "${GREEN}⚡ A+ Performance Features:${NC}"
    echo -e "   • Multi-level caching (4 backends)"
    echo -e "   • Database connection pooling"
    echo -e "   • Redis caching with fallback"
    echo -e "   • Static file compression"
    echo -e "   • Performance monitoring"
    echo -e "   • Query optimization"
    echo ""
    echo -e "${GREEN}🛡️ Security Features:${NC}"
    echo -e "   • SSL/TLS encryption"
    echo -e "   • Security headers"
    echo -e "   • Rate limiting"
    echo -e "   • SQL injection protection"
    echo ""
    echo -e "${GREEN}📊 System Specs:${NC}"
    echo -e "   • Model: $RPi_MODEL"
    echo -e "   • Memory: ${TOTAL_MEMORY_MB}MB (${MEMORY_PROFILE} profile)"
    echo -e "   • Workers: $GUNICORN_WORKERS"
    echo -e "   • DB Pool: $DB_POOL_SIZE"
    echo ""
    echo -e "${YELLOW}🧪 Test Commands:${NC}"
    echo -e "   • Performance: cd $DEPLOY_DIR/armguard && python performance_grade_test.py"
    echo -e "   • Full tests:  cd $DEPLOY_DIR/armguard && python comprehensive_test_suite.py"
    echo -e "   • Health:      curl http://${LOCAL_IP}/health/"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
}

# Main deployment function
main() {
    log "🚀 Starting ArmGuard A+ Performance Deployment on Raspberry Pi"
    
    detect_rpi_config
    update_system
    configure_rpi_optimizations
    clone_armguard
    setup_python_environment
    setup_database
    setup_redis_cache
    setup_nginx
    setup_gunicorn
    start_services
    run_comprehensive_tests
    show_deployment_summary
    
    log "🎉 Deployment completed successfully!"
}

# Run main function
main "$@"