# VMware Test Environment Setup

This deployment method is specifically designed for **test environments running in VMware VMs** with shared folder access to the host machine.

## Overview

- **Target**: VMware virtual machine
- **Purpose**: Development and testing
- **Features**: Basic setup with test database and development tools
- **Database**: PostgreSQL (test configuration)
- **Path**: Uses VMware shared folder (`/mnt/hgfs/Armguard`)

## Prerequisites

### Host Machine (Windows/Linux)
1. **VMware Workstation/Player** installed and running
2. **Shared folder configured** with name "Armguard" pointing to your project root
3. **Project files** accessible from host

### Virtual Machine (Ubuntu/Debian)
1. **VMware Tools** installed
2. **Shared folder support** enabled
3. **Network connectivity** for package installation

## Quick Start

### 1. Configure VMware Shared Folder

In VMware:
1. VM Settings → Options → Shared Folders
2. Enable shared folders
3. Add folder: Name="Armguard", Host path=your project directory
4. Enable "Always enabled"

### 2. Deploy to VM

From the deployment directory:
```bash
./deploy-master.sh vm-test
```

Or run directly:
```bash
cd methods/vmware-setup
chmod +x vm-deploy.sh
./vm-deploy.sh
```

## What Gets Installed

### System Packages
- Python 3.11+ with pip and venv
- PostgreSQL with contrib packages  
- Redis server
- Nginx web server
- Git and development tools

### Application Setup
- **Virtual environment** created in project directory
- **Python dependencies** installed from requirements.txt
- **Test database** configured (armguard_test/armguard_test)
- **Test superuser** created (admin/admin123)
- **Static files** collected
- **Environment file** configured for testing

### Services Configuration
- **Nginx** configured as reverse proxy
- **PostgreSQL** with test database and user
- **Redis** for caching and sessions
- **All services** enabled and started

## Environment Details

### Paths
- **Project**: `/mnt/hgfs/Armguard/armguard`
- **Shared folder**: `/mnt/hgfs/Armguard` 
- **Virtual env**: `{project}/venv`
- **Static files**: `{project}/staticfiles`
- **Media files**: `{project}/media`

### Test Database
- **Name**: `armguard_test`
- **User**: `armguard_test` 
- **Password**: `test_password123`
- **Host**: `localhost:5432`

### Test Credentials
- **Admin user**: `admin`
- **Admin password**: `admin123`
- **Admin email**: `admin@test.local`

### Network Access
- **HTTP**: `http://{VM_IP}`
- **Admin**: `http://{VM_IP}/admin`
- **Development server**: Port 8000 (manual start)

## Manual Development Server

To run Django development server manually:
```bash
cd /mnt/hgfs/Armguard/armguard
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

## Configuration Files

### Environment (.env)
```env
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,{VM_IP}
DATABASE_NAME=armguard_test
DATABASE_USER=armguard_test
DATABASE_PASSWORD=test_password123
DATABASE_HOST=localhost
DATABASE_PORT=5432
SECRET_KEY=test-secret-key-for-vm-development-only
REDIS_URL=redis://localhost:6379/1
TESTING=True
VM_ENVIRONMENT=True
```

### Nginx Configuration
- **Location**: `/etc/nginx/sites-available/armguard-test`
- **Proxy**: Port 8000 for Django
- **Static**: Served directly from project
- **Enabled**: Replaces default site

## Features

### Enabled in Test Environment
- ✅ **Django Admin** interface
- ✅ **Debug toolbar** for development  
- ✅ **API endpoints** for testing
- ✅ **Static file serving**
- ✅ **Media file uploads**
- ✅ **Database migrations**
- ✅ **Silk profiling** for performance analysis

### Security (Test Mode)
- ❌ **SSL/TLS** (HTTP only)
- ❌ **Firewall restrictions** (open access)
- ❌ **Production security headers**
- ❌ **Rate limiting**
- ✅ **Basic authentication**
- ✅ **Session security**

## Troubleshooting

### Common Issues

**1. Shared folder not accessible**
```bash
# Check if VMware tools are installed
vmware-toolbox-cmd -v

# Manually mount shared folder
sudo mkdir -p /mnt/hgfs
sudo vmhgfs-fuse .host:/Armguard /mnt/hgfs -o allow_other

# Verify mount
ls /mnt/hgfs/Armguard
```

**2. Database connection failed**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "\\l"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

**3. Nginx not serving correctly**
```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx status
sudo systemctl status nginx

# View error logs
sudo tail -f /var/log/nginx/error.log
```

**4. Python dependencies failed**
```bash
# Manually activate environment and install
cd /mnt/hgfs/Armguard/armguard
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Service Management

```bash
# Restart all services
sudo systemctl restart nginx postgresql redis-server

# Check all service status
sudo systemctl status nginx postgresql redis-server

# View application logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Reset Environment

To completely reset the test environment:
```bash
# Stop services
sudo systemctl stop nginx postgresql redis-server

# Remove application data (keeps shared folder)
sudo rm -rf /etc/nginx/sites-enabled/armguard-test
sudo -u postgres dropdb armguard_test || true
sudo -u postgres dropuser armguard_test || true

# Re-run deployment
./deploy-master.sh vm-test --force
```

## Integration with Other Methods

This VM test environment is designed to work alongside:
- **Production deployment**: Same application structure
- **Docker testing**: Shares test data and configuration patterns
- **Basic setup**: Similar system requirements

The master configuration ensures consistency across all deployment methods.

## Development Workflow

1. **Edit code** on host machine using your preferred IDE
2. **Changes reflect immediately** in VM via shared folder
3. **Test changes** using browser to access VM IP
4. **Debug issues** using Django development server
5. **Database changes** persist in VM PostgreSQL
6. **Static files** regenerated with `collectstatic`

Perfect for iterative development and testing!