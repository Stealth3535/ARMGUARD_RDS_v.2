# ARMGUARD - Installation Guide

## Table of Contents
- [System Requirements](#system-requirements)
- [Development Environment Setup](#development-environment-setup)
- [Production Environment Setup](#production-environment-setup)
- [Raspberry Pi 4B Deployment](#raspberry-pi-4b-deployment)
- [Database Setup](#database-setup)
- [Environment Configuration](#environment-configuration)
- [First-Time Setup](#first-time-setup)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Hardware Requirements

#### Development Environment
- **CPU**: Dual-core processor (minimum)
- **RAM**: 4GB (minimum), 8GB (recommended)
- **Storage**: 2GB free space (minimum)
- **Network**: Internet connection for package installation

#### Production Environment
- **CPU**: Quad-core processor (recommended)
- **RAM**: 8GB (minimum), 16GB (recommended)
- **Storage**: 20GB free space (minimum)
- **Network**: Secure LAN connection with optional WAN access

#### Raspberry Pi 4B (Optimal Target Platform)
- **Model**: Raspberry Pi 4B (4GB RAM minimum, 8GB recommended)
- **Storage**: 32GB microSD card (Class 10 or better)
- **Network**: Gigabit Ethernet (recommended over WiFi)
- **Power**: Official Raspberry Pi power supply (5V 3A)
- **Cooling**: Heat sinks or active cooling fan

### Software Requirements
- **Operating System**: Ubuntu 20.04+ / Debian 11+ / Raspberry Pi OS
- **Python**: 3.11+ (Python 3.13 recommended)
- **PostgreSQL**: 13+ (production) or SQLite 3.35+ (development)
- **Redis**: 6.0+ (caching and WebSocket support)
- **Nginx**: 1.18+ (production reverse proxy)

## Development Environment Setup

### 1. Install System Dependencies

#### Ubuntu/Debian:
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and development tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install system dependencies for image processing (ARM64 compatible)
sudo apt install -y libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev

# Install PostgreSQL (optional for development)
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Install Redis for caching and WebSocket support
sudo apt install -y redis-server

# Install development tools
sudo apt install -y git curl wget build-essential
```

#### macOS:
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11+
brew install python@3.11

# Install PostgreSQL (optional)
brew install postgresql@15

# Install Redis
brew install redis

# Install image processing libraries
brew install jpeg zlib libtiff freetype lcms2 webp
```

### 2. Clone Repository
```bash
# Clone the ARMGUARD repository
git clone <repository-url> ARMGUARD_RDS_v.2
cd ARMGUARD_RDS_v.2
```

### 3. Create Virtual Environment
```bash
# Create Python virtual environment
python3.11 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate
```

### 4. Install Python Dependencies
```bash
# Navigate to Django project directory
cd armguard

# Install required packages
pip install --upgrade pip
pip install -r requirements.txt

# For development, also install optional monitoring tools
pip install psutil==5.9.8  # System monitoring
```

### 5. Environment Configuration
```bash
# Create environment file
cp .env.example .env

# Edit environment file with your settings
nano .env
```

### 6. Database Setup (Development)
```bash
# Apply database migrations
python manage.py migrate

# Create superuser account
python manage.py createsuperuser

# Load initial data (optional)
python manage.py loaddata fixtures/initial_data.json
```

### 7. Start Development Server
```bash
# Start Redis (if not running as service)
redis-server --daemonize yes

# Start Django development server
python manage.py runserver 127.0.0.1:8000

# Or start with WebSocket support
python -m daphne -b 0.0.0.0 -p 8000 core.asgi:application
```

## Production Environment Setup

### 1. Server Preparation

#### Create Application User
```bash
# Create dedicated application user
sudo adduser armguard
sudo usermod -aG sudo armguard

# Switch to application user
sudo su - armguard
```

#### Install System Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib libpq-dev

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Install system dependencies
sudo apt install -y libjpeg-dev zlib1g-dev libtiff-dev libfreetype6-dev liblcms2-dev libwebp-dev

# Install process management tools
sudo apt install -y supervisor
```

### 2. Database Configuration

#### PostgreSQL Setup
```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE armguard;
CREATE USER armguard_user WITH PASSWORD 'secure_password_here';
ALTER ROLE armguard_user SET client_encoding TO 'utf8';
ALTER ROLE armguard_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE armguard_user SET timezone TO 'Asia/Manila';
GRANT ALL PRIVILEGES ON DATABASE armguard TO armguard_user;
\q

# Configure PostgreSQL for production
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Add to postgresql.conf:
```
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Redis Configuration
```bash
# Configure Redis for production
sudo nano /etc/redis/redis.conf
```

Update Redis configuration:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. Application Deployment
```bash
# Clone repository
git clone <repository-url> /home/armguard/ARMGUARD_RDS_v.2
cd /home/armguard/ARMGUARD_RDS_v.2

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
cd armguard
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psutil

# Set proper permissions
sudo chown -R armguard:armguard /home/armguard/ARMGUARD_RDS_v.2
chmod -R 755 /home/armguard/ARMGUARD_RDS_v.2
```

### 4. Environment Configuration
```bash
# Create production environment file
nano /home/armguard/ARMGUARD_RDS_v.2/armguard/.env
```

Production .env configuration:
```bash
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-server-ip,your-domain.com,localhost

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=armguard
DB_USER=armguard_user
DB_PASSWORD=secure_password_here
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1

# Security Settings
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True

# Network Configuration
ENABLE_NETWORK_ACCESS_CONTROL=True
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-server-ip

# Email Configuration (optional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.your-domain.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password
```

### 5. Database Migration
```bash
# Activate virtual environment
source /home/armguard/ARMGUARD_RDS_v.2/venv/bin/activate
cd /home/armguard/ARMGUARD_RDS_v.2/armguard

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Create superuser
python manage.py createsuperuser
```

### 6. Systemd Service Configuration

#### Create Django application service
```bash
sudo nano /etc/systemd/system/armguard.service
```

Service configuration:
```ini
[Unit]
Description=ARMGUARD Django Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=armguard
Group=armguard
WorkingDirectory=/home/armguard/ARMGUARD_RDS_v.2/armguard
Environment="PATH=/home/armguard/ARMGUARD_RDS_v.2/venv/bin"
ExecStart=/home/armguard/ARMGUARD_RDS_v.2/venv/bin/gunicorn core.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 600
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Create WebSocket service
```bash
sudo nano /etc/systemd/system/armguard-websocket.service
```

WebSocket service configuration:
```ini
[Unit]
Description=ARMGUARD WebSocket Service
After=network.target redis.service

[Service]
Type=simple
User=armguard
Group=armguard
WorkingDirectory=/home/armguard/ARMGUARD_RDS_v.2/armguard
Environment="PATH=/home/armguard/ARMGUARD_RDS_v.2/venv/bin"
ExecStart=/home/armguard/ARMGUARD_RDS_v.2/venv/bin/daphne -b 127.0.0.1 -p 8001 core.asgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7. Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/armguard
```

Nginx configuration:
```nginx
upstream armguard_django {
    server 127.0.0.1:8000;
}

upstream armguard_websocket {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your-domain.com your-server-ip;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com your-server-ip;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";

    # Static files
    location /static/ {
        alias /home/armguard/ARMGUARD_RDS_v.2/armguard/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /home/armguard/ARMGUARD_RDS_v.2/armguard/core/media/;
        expires 30d;
    }

    # WebSocket connections
    location /ws/ {
        proxy_pass http://armguard_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # Django application
    location / {
        proxy_pass http://armguard_django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        client_max_body_size 10M;
    }
}
```

### 8. Service Activation
```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable postgresql redis-server nginx
sudo systemctl enable armguard armguard-websocket

# Start services
sudo systemctl start postgresql redis-server
sudo systemctl start armguard armguard-websocket
sudo systemctl start nginx

# Enable Nginx site
sudo ln -s /etc/nginx/sites-available/armguard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Raspberry Pi 4B Deployment

### 1. Raspberry Pi Preparation
```bash
# Update Raspberry Pi OS
sudo apt update && sudo apt full-upgrade -y

# Install required packages for ARM64
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo apt install -y postgresql-15 postgresql-contrib-15 libpq-dev
sudo apt install -y redis-server nginx supervisor

# Install ARM64-compatible image processing libraries
sudo apt install -y libjpeg62-turbo-dev zlib1g-dev libtiff5-dev libfreetype6-dev liblcms2-dev libwebp-dev libopenjp2-7-dev
```

### 2. Performance Optimization for RPi
```bash
# Configure swap space (recommended for 4GB models)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile
# Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Configure GPU memory split
sudo nano /boot/config.txt
# Add: gpu_mem=64

# Optimize PostgreSQL for RPi
sudo nano /etc/postgresql/15/main/postgresql.conf
```

RPi PostgreSQL optimization:
```
max_connections = 50
shared_buffers = 128MB
effective_cache_size = 512MB
work_mem = 2MB
maintenance_work_mem = 32MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
```

### 3. Thermal Management
```bash
# Install thermal monitoring
sudo apt install -y lm-sensors

# Create thermal monitoring script
sudo nano /usr/local/bin/thermal-monitor.sh
```

Thermal monitoring script:
```bash
#!/bin/bash
TEMP=$(vcgencmd measure_temp | cut -c6-9)
if (( $(echo "$TEMP > 70.0" | bc -l) )); then
    echo "WARNING: RPi temperature is ${TEMP}°C"
    # Optionally, reduce system load
    sudo systemctl restart armguard
fi
```

```bash
# Make script executable and add to cron
sudo chmod +x /usr/local/bin/thermal-monitor.sh
echo "*/5 * * * * /usr/local/bin/thermal-monitor.sh" | sudo crontab -
```

### 4. RPi-Specific Environment Configuration
Create RPi-optimized `.env` file:
```bash
# Python path for ARM64
PYTHONPATH=/home/armguard/ARMGUARD_RDS_v.2/armguard

# Reduced connection limits for RPi
DB_MAX_CONNS=20
REDIS_MAX_CONNECTIONS=25

# Optimized cache settings
CACHE_TIMEOUT=600
SESSION_COOKIE_AGE=1800

# Memory optimization
FILE_UPLOAD_MAX_MEMORY_SIZE=2097152  # 2MB
DATA_UPLOAD_MAX_MEMORY_SIZE=2097152  # 2MB

# RPi monitoring
RPi_THERMAL_WARNING_TEMP=70.0
RPi_THERMAL_CRITICAL_TEMP=80.0
```

## Database Setup

### PostgreSQL Production Setup
```sql
-- Connect to PostgreSQL as superuser
sudo -u postgres psql

-- Create database
CREATE DATABASE armguard
    WITH ENCODING 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TEMPLATE template0;

-- Create application user
CREATE ROLE armguard_user WITH
    LOGIN
    NOSUPERUSER
    CREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    CONNECTION LIMIT -1
    PASSWORD 'secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE armguard TO armguard_user;
ALTER DEFAULT PRIVILEGES FOR ROLE armguard_user IN SCHEMA public GRANT ALL ON TABLES TO armguard_user;
ALTER DEFAULT PRIVILEGES FOR ROLE armguard_user IN SCHEMA public GRANT ALL ON SEQUENCES TO armguard_user;

-- Create backup user (optional)
CREATE ROLE armguard_backup WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    INHERIT
    NOREPLICATION
    PASSWORD 'backup_password_here';

GRANT CONNECT ON DATABASE armguard TO armguard_backup;
GRANT USAGE ON SCHEMA public TO armguard_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO armguard_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE armguard_user IN SCHEMA public GRANT SELECT ON TABLES TO armguard_backup;

\q
```

### Database Optimization
```bash
# Configure PostgreSQL for production
sudo nano /etc/postgresql/15/main/postgresql.conf
```

Production PostgreSQL configuration:
```
# Memory
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Checkpoints
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Connection and authentication
max_connections = 100
listen_addresses = 'localhost'
port = 5432

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 10MB
log_min_duration_statement = 1000
log_line_prefix = '%t [%p-%l] %q%u@%d '
```

### Database Backup Setup
```bash
# Create backup script
sudo nano /usr/local/bin/armguard-backup.sh
```

Backup script:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/armguard"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="armguard"
DB_USER="armguard_backup"

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
export PGPASSWORD="backup_password_here"
pg_dump -h localhost -U $DB_USER -d $DB_NAME -f $BACKUP_DIR/armguard_db_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/armguard_db_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "armguard_db_*.sql.gz" -mtime +30 -delete

echo "Backup completed: armguard_db_$DATE.sql.gz"
```

```bash
# Make script executable and schedule
sudo chmod +x /usr/local/bin/armguard-backup.sh

# Add to cron (daily backup at 2 AM)
echo "0 2 * * * /usr/local/bin/armguard-backup.sh" | sudo crontab -
```

## Environment Configuration

### Development .env File
```bash
# Django Core Settings
DJANGO_SECRET_KEY=your-development-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

# Database (SQLite for development)
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Redis (optional for development)
REDIS_URL=redis://127.0.0.1:6379/1

# Security (relaxed for development)
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
SECURE_SSL_REDIRECT=False

# Network access control (disabled for development)
ENABLE_NETWORK_ACCESS_CONTROL=False

# Rate limiting (relaxed for development)
RATELIMIT_REQUESTS_PER_MINUTE=300

# Email (console backend for development)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Production .env File
```bash
# Django Core Settings - CHANGE THESE
DJANGO_SECRET_KEY=your-production-secret-key-here
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,your-server-ip,192.168.1.100

# Database Configuration
DB_ENGINE=django.db.backends.postgresql
DB_NAME=armguard
DB_USER=armguard_user
DB_PASSWORD=your-secure-database-password
DB_HOST=localhost
DB_PORT=5432
DB_SSL_MODE=prefer

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_MAX_CONNECTIONS=50

# Security Settings
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-server-ip

# Network Security
ENABLE_NETWORK_ACCESS_CONTROL=True

# Rate Limiting
RATELIMIT_ENABLE=True
RATELIMIT_REQUESTS_PER_MINUTE=60

# Django Axes (Failed Login Protection)
AXES_ENABLED=True
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=1

# Session Configuration
SESSION_COOKIE_AGE=3600
SESSION_SAVE_EVERY_REQUEST=True

# File Upload Limits
FILE_UPLOAD_MAX_MEMORY_SIZE=5242880
DATA_UPLOAD_MAX_MEMORY_SIZE=5242880

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=your-smtp-server.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@domain.com
EMAIL_HOST_PASSWORD=your-email-password

# VPN Integration (optional)
WIREGUARD_ENABLED=False
WIREGUARD_INTERFACE=wg0
WIREGUARD_NETWORK=10.0.0.0/24

# Admin URL (change default for security)
DJANGO_ADMIN_URL=your-secret-admin-url

# Cache Configuration
CACHE_TIMEOUT=300

# Performance Settings
DB_CONN_MAX_AGE=600
```

## First-Time Setup

### 1. Initial Data Migration
```bash
# Activate virtual environment
source venv/bin/activate
cd armguard

# Apply all migrations
python manage.py migrate

# Create Django superuser
python manage.py createsuperuser
# Enter: username, email, password

# Collect static files (production only)
python manage.py collectstatic --noinput
```

### 2. Create Initial Groups and Permissions
```bash
# Create Django shell script for initial setup
cat > initial_setup.py << 'EOF'
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

User = get_user_model()

# Create user groups
admin_group, created = Group.objects.get_or_create(name='Admin')
armorer_group, created = Group.objects.get_or_create(name='Armorer')
staff_group, created = Group.objects.get_or_create(name='Staff')

# Get all permissions
all_permissions = Permission.objects.all()

# Admin gets all permissions
admin_group.permissions.set(all_permissions)

# Armorer gets inventory and transaction permissions
armorer_permissions = Permission.objects.filter(
    content_type__app_label__in=['inventory', 'transactions', 'personnel']
)
armorer_group.permissions.set(armorer_permissions)

# Staff gets view permissions
staff_permissions = Permission.objects.filter(
    codename__startswith='view_'
)
staff_group.permissions.set(staff_permissions)

print("User groups created successfully")
print(f"Admin group permissions: {admin_group.permissions.count()}")
print(f"Armorer group permissions: {armorer_group.permissions.count()}")
print(f"Staff group permissions: {staff_group.permissions.count()}")
EOF

# Run initial setup
python manage.py shell < initial_setup.py
```

### 3. Create Test Data (Optional)
```bash
# Create sample data script
cat > sample_data.py << 'EOF'
from personnel.models import Personnel
from inventory.models import Item
from django.contrib.auth.models import User
import datetime

# Create sample personnel
personnel_data = [
    {"surname": "Smith", "firstname": "John", "rank": "SGT", "serial": "12345678"},
    {"surname": "Johnson", "firstname": "Alice", "rank": "CPL", "serial": "87654321"},
    {"surname": "Brown", "firstname": "Michael", "rank": "PVT", "serial": "11223344"},
]

for data in personnel_data:
    Personnel.objects.get_or_create(**data)

# Create sample inventory items
item_data = [
    {"item_type": "M16", "serial": "M16001", "description": "Standard M16 Rifle"},
    {"item_type": "M4", "serial": "M4001", "description": "M4 Carbine"},
    {"item_type": "GLOCK", "serial": "GLK001", "description": "Glock 17 Pistol"},
]

for data in item_data:
    Item.objects.get_or_create(**data)

print(f"Created {Personnel.objects.count()} personnel records")
print(f"Created {Item.objects.count()} inventory items")
EOF

# Run sample data creation
python manage.py shell < sample_data.py
```

## Verification

### 1. System Health Check
```bash
# Check Django configuration
python manage.py check --deploy

# Check database connectivity
python manage.py dbshell
\l  # List databases (PostgreSQL)
\q  # Quit

# Check Redis connectivity
redis-cli ping
# Should return: PONG
```

### 2. Service Status Check
```bash
# Check all services
sudo systemctl status postgresql
sudo systemctl status redis-server
sudo systemctl status nginx
sudo systemctl status armguard
sudo systemctl status armguard-websocket

# Check logs
sudo journalctl -u armguard -n 50
sudo journalctl -u armguard-websocket -n 50
sudo tail -f /var/log/nginx/access.log
```

### 3. Application Access Test
```bash
# Test HTTP(S) access
curl -I http://localhost/
curl -I https://your-domain.com/

# Test WebSocket connection
# Use browser console:
# ws = new WebSocket('wss://your-domain.com/ws/dashboard/');
# ws.onopen = function(e) { console.log('Connected'); };
```

### 4. Security Verification
```bash
# Test SSL configuration
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Test security headers
curl -I https://your-domain.com/ | grep -i "strict\|frame\|content"

# Test rate limiting
# Make multiple rapid requests to trigger rate limiting
for i in {1..10}; do curl -s https://your-domain.com/ >/dev/null; done
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Issues
```bash
# Check PostgreSQL service
sudo systemctl status postgresql

# Check database credentials
sudo -u postgres psql -c "\du"  # List users
sudo -u postgres psql -c "\l"   # List databases

# Test connection with application user
psql -h localhost -d armguard -U armguard_user

# Check pg_hba.conf for authentication
sudo nano /etc/postgresql/15/main/pg_hba.conf
```

#### 2. Redis Connection Problems
```bash
# Check Redis service
sudo systemctl status redis-server

# Test Redis connection
redis-cli ping
redis-cli info

# Check Redis configuration
sudo nano /etc/redis/redis.conf

# Restart Redis
sudo systemctl restart redis-server
```

#### 3. Nginx Configuration Issues
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Reload Nginx configuration
sudo systemctl reload nginx

# Check site configuration
sudo nginx -T | grep -A 20 -B 5 "server_name your-domain"
```

#### 4. Django Application Errors
```bash
# Check application logs
sudo journalctl -u armguard -f

# Check Django settings
cd armguard
python manage.py check --deploy

# Debug mode (temporarily enable for troubleshooting)
export DJANGO_DEBUG=True
python manage.py runserver 127.0.0.1:8000
```

#### 5. WebSocket Connection Issues
```bash
# Check WebSocket service
sudo systemctl status armguard-websocket

# Check WebSocket logs
sudo journalctl -u armguard-websocket -f

# Test WebSocket manually
# Install wscat: npm install -g wscat
# wscat -c ws://localhost:8001/ws/dashboard/
```

#### 6. Permission Issues
```bash
# Check file permissions
ls -la /home/armguard/ARMGUARD_RDS_v.2/

# Fix permissions
sudo chown -R armguard:armguard /home/armguard/ARMGUARD_RDS_v.2/
chmod -R 755 /home/armguard/ARMGUARD_RDS_v.2/

# Check log file permissions
sudo chown -R armguard:armguard /home/armguard/ARMGUARD_RDS_v.2/armguard/logs/
```

#### 7. Memory Issues (Raspberry Pi)
```bash
# Check memory usage
free -h
htop

# Check swap usage
swapon --show

# Monitor temperature
vcgencmd measure_temp

# Reduce memory usage
sudo systemctl restart armguard
sudo systemctl restart armguard-websocket
```

### Environment-Specific Troubleshooting

#### Raspberry Pi Issues
```bash
# Check ARM64 compatibility
uname -a
python3 -c "import platform; print(platform.machine())"

# Check thermal throttling
vcgencmd get_throttled
# 0x0 = OK, other values indicate throttling

# Monitor system performance
iostat -x 1 5
sar -u 1 5
```

#### SSL Certificate Issues
```bash
# Generate self-signed certificate (development)
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/private/armguard.key \
    -out /etc/ssl/certs/armguard.crt

# Check certificate validity
openssl x509 -in /etc/ssl/certs/armguard.crt -text -noout

# Use Let's Encrypt (production)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Emergency Recovery

#### Database Recovery
```bash
# Restore from backup
sudo -u postgres psql -d postgres -c "DROP DATABASE IF EXISTS armguard;"
sudo -u postgres psql -d postgres -c "CREATE DATABASE armguard;"
sudo -u postgres psql -d armguard < /var/backups/armguard/armguard_db_latest.sql
```

#### Service Recovery
```bash
# Reset all services
sudo systemctl restart postgresql redis-server
sudo systemctl restart armguard armguard-websocket
sudo systemctl restart nginx

# Full system recovery (last resort)
sudo reboot
```

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Next Review**: March 2026  

---

*For system architecture details, see [architecture.md](architecture.md)*  
*For database schema information, see [database.md](database.md)*  
*For security configuration, see [security.md](security.md)*