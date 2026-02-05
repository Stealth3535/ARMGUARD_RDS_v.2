# Basic Server Setup

Simple deployment method for basic Linux servers with minimal configuration.

## Overview

- **Target**: Basic Linux server (Ubuntu/Debian)
- **Purpose**: Simple production deployment
- **Features**: Essential services only
- **Database**: SQLite (default) or PostgreSQL
- **Path**: `/var/www/armguard`

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04+, Debian 11+, or Raspberry Pi OS
- **RAM**: 1GB minimum (2GB recommended)
- **Storage**: 5GB free space
- **Network**: Internet connection for packages

### User Requirements
- Root access or sudo privileges
- Basic Linux command line knowledge

## Quick Start

### Option 1: Via Master Deployment
```bash
cd armguard/deployment
./deploy-master.sh basic-setup
```

### Option 2: Direct Execution
```bash
cd armguard/deployment/methods/basic-setup
chmod +x serversetup.sh
./serversetup.sh
```

## What Gets Installed

### System Packages
- Python 3.11+ with pip and virtual environment
- SQLite3 (default database)
- Nginx web server (optional)
- Git for version control
- Essential development tools

### Application Setup
- **Project directory**: `/var/www/armguard`
- **Virtual environment**: `/var/www/armguard/venv`
- **Database**: SQLite by default
- **Static files**: Collected and served
- **Basic superuser**: Created with prompts

### Services
- **Django application** running on port 8000
- **Nginx** (if selected) as reverse proxy
- **Systemd service** for application management

## Configuration

### Database Options
1. **SQLite** (default): No additional setup required
2. **PostgreSQL**: Prompts for database configuration

### Network Configuration
- **Development server**: Runs on `0.0.0.0:8000`
- **Nginx option**: Reverse proxy on port 80
- **Domain**: Can be configured during setup

### Security Settings
- Basic Django security enabled
- Debug mode disabled for production
- Secret key auto-generated
- Basic firewall rules (optional)

## Usage

### Starting the Application
```bash
cd /var/www/armguard
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Managing Services
```bash
# If systemd service was installed
sudo systemctl start armguard
sudo systemctl status armguard
sudo systemctl enable armguard  # Auto-start on boot
```

### Database Management
```bash
cd /var/www/armguard
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

## Files Included

### Scripts
- **serversetup.sh**: Main deployment script for servers
- **vmsetup.sh**: Variant for VMware environments (legacy)

### Configuration
- Uses system-wide configuration
- Environment variables in `.env` file
- Basic Django settings

## Limitations

### Basic Setup Limitations
- ❌ **No SSL/TLS** (HTTP only by default)
- ❌ **No monitoring** (basic logging only)
- ❌ **No automated backups**
- ❌ **No load balancing**
- ❌ **No container support**
- ❌ **Limited security hardening**

### Recommended For
- ✅ **Development servers**
- ✅ **Small internal deployments**
- ✅ **Proof of concept installations**
- ✅ **Learning and testing**

### Not Recommended For
- ❌ **High-traffic production sites**
- ❌ **Security-critical applications**
- ❌ **Multi-server deployments**
- ❌ **Enterprise environments**

## Upgrading

### To Production Deployment
```bash
# Backup current installation
sudo cp -r /var/www/armguard /var/backups/armguard-basic-backup

# Run production deployment
cd armguard/deployment
./deploy-master.sh production

# The production deployment will detect and migrate existing data
```

## Troubleshooting

### Common Issues

**1. Permission Errors**
```bash
# Fix ownership
sudo chown -R www-data:www-data /var/www/armguard
sudo chmod -R 755 /var/www/armguard
```

**2. Python Virtual Environment**
```bash
# Recreate virtual environment
cd /var/www/armguard
sudo rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Database Issues**
```bash
# Reset SQLite database
cd /var/www/armguard
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

**4. Static Files Not Loading**
```bash
cd /var/www/armguard
source venv/bin/activate
python manage.py collectstatic --clear
```

### Getting Support
- Check the main deployment documentation
- Review Django error logs in the application directory
- Use `./deploy-master.sh status` to check system status

## Migration Path

For users needing more features, consider upgrading to:
- **Production deployment**: Full enterprise features
- **Docker testing**: Containerized development environment
- **VM test environment**: Development with shared folders

The unified deployment system makes migration between methods straightforward.