# 📋 ARMGUARD Deployment Organization & Process Guide

**Version:** 4.0.0  
**Last Updated:** February 10, 2026  
**Status:** ✅ Production Ready

---

## 📁 Folder Structure Overview

```
deployment_A/
│
├── 🎯 ENTRY POINTS (Start Here)
│   ├── deployment-helper.sh/.ps1    → Interactive guide (RECOMMENDED FOR NEW USERS)
│   ├── ubuntu-deploy.sh             → Ubuntu auto-optimized deployment
│   ├── 01_setup.sh/.ps1             → Modular: Step 1 - Prerequisites
│   ├── 02_config.sh/.ps1            → Modular: Step 2 - Configuration
│   ├── 03_services.sh               → Modular: Step 3 - Services
│   └── 04_monitoring.sh             → Modular: Step 4 - Monitoring
│
├── 🔧 CONFIGURATION & HELPERS
│   ├── master-config.sh             → Shared configuration variables
│   ├── unified-env-generator.ps1    → Generates .env files
│   └── sync-validator.ps1/.sh       → Validates deployment integrity
│
├── 📂 methods/
│   ├── production/                  → Production-specific scripts
│   │   ├── deploy-armguard.sh       → Complete production deployment
│   │   ├── master-deploy.sh         → Orchestrated production deployment
│   │   ├── detect-environment.sh    → Auto-detect system capabilities
│   │   ├── health-check.sh          → Verify deployment health
│   │   ├── install-gunicorn-service.sh
│   │   ├── install-daphne-service.sh
│   │   └── ...                      → Other production utilities
│   │
│   ├── basic-setup/                 → Quick setup scripts
│   │   ├── serversetup.sh           → Basic server installation
│   │   └── vmsetup.sh               → VMware-specific setup
│   │
│   ├── docker-testing/              → Comprehensive testing environment
│   │   ├── docker-compose.yml       → Full testing stack
│   │   ├── Dockerfile               → Container definition
│   │   └── ...                      → Test suites
│   │
│   └── vmware-setup/                → VMware VM specific scripts
│
├── 📚 DOCUMENTATION
│   ├── README.md                    → Main deployment documentation
│   ├── QUICK_DEPLOY_GUIDE.md        → Quick start guide (NEW!)
│   ├── UBUNTU_DEPLOYMENT_GUIDE.md   → Ubuntu-specific guide
│   ├── DEVICE_AUTHORIZATION_GUIDE.md → Security setup
│   └── docs_archive/                → Additional documentation
│
├── 🔧 DEVICE AUTHORIZATION
│   ├── device_auth_setup.sh
│   └── device_auth_config.sh
│
└── 🗄️ legacy_archive/              → Old scripts (for reference only)
    └── ...                          → Deprecated files

```

---

## 🎯 Deployment Decision Tree

### **START HERE: Which deployment should I use?**

```
❓ What do you want to do?
│
├─ 🆕 "I'M NEW - Just show me what to run!"
│   ├─ Ubuntu Server:
│   │   └─ cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
│   │      sudo bash ubuntu-deploy.sh --production
│   │
│   └─ Any Linux System:
│       └─ cd deployment_A
│          bash deployment-helper.sh  (Interactive guide)
│
├─ 🚀 "I want QUICK deployment for dev/testing"
│   └─ cd deployment_A
│      bash 01_setup.sh
│      bash 02_config.sh
│      bash 03_services.sh
│      (Skip 04_monitoring.sh if you don't need monitoring)
│
├─ 🏭 "I need PRODUCTION deployment with full features"
│   ├─ Option A - Auto-optimized (RECOMMENDED):
│   │   └─ bash ubuntu-deploy.sh --production
│   │
│   ├─ Option B - Full control:
│   │   └─ bash methods/production/deploy-armguard.sh
│   │
│   └─ Option C - Step-by-step with monitoring:
│       └─ bash 01_setup.sh
│          bash 02_config.sh
│          bash 03_services.sh
│          bash 04_monitoring.sh
│
├─ 🌐 "I need network separation (LAN/WAN isolation)"
│   └─ bash 02_config.sh  (Choose hybrid/LAN/WAN during setup)
│      OR
│      bash methods/production/master-deploy.sh --network-type hybrid
│
├─ 🧪 "I need comprehensive TESTING environment"
│   └─ cd methods/docker-testing
│      docker-compose up
│
└─ 💻 "I'm deploying on VMware VM"
    └─ bash methods/vmware-setup/vm-deploy.sh
       Then: bash 01_setup.sh && bash 02_config.sh ...
```

---

## 📊 Deployment Methods Comparison

| Method | Use Case | Difficulty | Auto-Detection | Time | Recommended For |
|--------|----------|------------|----------------|------|-----------------|
| **ubuntu-deploy.sh** | Ubuntu servers | ⚡ Easy | ✅ Yes | ~10 min | ⭐ Most users |
| **deployment-helper.sh** | Any Linux | ⚡ Easy | ✅ Yes | ~15 min | New users |
| **Modular (01-04)** | Any deployment | ⚡⚡ Medium | ❌ No | ~20 min | Customization needed |
| **deploy-armguard.sh** | Production | ⚡⚡ Medium | ⚙️ Partial | ~15 min | Full control |
| **master-deploy.sh** | Enterprise | ⚡⚡⚡ Hard | ✅ Yes | ~25 min | Network isolation |
| **Docker testing** | Testing/CI | ⚡⚡ Medium | ✅ Yes | ~5 min | Automated testing |

---

## 🔄 Step-by-Step Process Breakdown

### **Method 1: Ubuntu Auto-Deploy (RECOMMENDED)**

```bash
# Location: deployment_A/ubuntu-deploy.sh
```

**Process:**
1. **Auto-Detection Phase**
   - Detects Ubuntu version, architecture
   - Identifies hardware (HP ProDesk, Raspberry Pi, standard server)
   - Calculates optimal workers based on CPU/RAM
   - Auto-detects project location (git repo)

2. **Configuration Phase**
   - Shows detected configuration
   - Prompts for network type (LAN/WAN)
   - Auto-selects database (PostgreSQL vs SQLite)
   - Configures SSL (mkcert for LAN, Let's Encrypt for production)

3. **Execution Phase**
   - Calls appropriate deployment script:
     * Quick mode → `methods/basic-setup/serversetup.sh`
     * Production → `methods/production/deploy-armguard.sh`
     * Standard → `methods/production/master-deploy.sh`

4. **Result**
   - Services running
   - Auto-configured for your hardware
   - Ready to use

**Commands:**
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A

# For production with Let's Encrypt SSL
sudo bash ubuntu-deploy.sh --production

# For LAN-only with mkcert
sudo bash ubuntu-deploy.sh --quick

# For standard with prompts
sudo bash ubuntu-deploy.sh
```

---

### **Method 2: Modular Deployment (01-04 Scripts)**

```bash
# Location: deployment_A/01_setup.sh through 04_monitoring.sh
```

**Process:**

#### **Phase 1: 01_setup.sh - Prerequisites**
- System package installation
- Environment detection
- Python environment setup
- Database installation (PostgreSQL/SQLite)
- Redis configuration
- Service user creation

**What it does:**
```bash
✅ System updates
✅ Install: python3, nginx, redis, postgresql, fail2ban
✅ Create virtual environment
✅ Install Python packages
✅ Configure Redis for WebSockets
✅ Setup database
```

**Outputs:**
- `/var/log/armguard-deploy/01-setup-*.log`
- Virtual environment at `armguard/venv/`
- Database created

---

#### **Phase 2: 02_config.sh - Configuration**
- .env file generation
- Django configuration
- SSL certificate setup
- Network configuration
- Static files setup

**What it does:**
```bash
✅ Generate Django SECRET_KEY
✅ Create .env file
✅ Configure allowed hosts
✅ Setup SSL (mkcert, Let's Encrypt, or self-signed)
✅ Network type selection (LAN/WAN/Hybrid)
✅ Database connection configuration
✅ Static file collection
```

**Outputs:**
- `armguard/.env` file
- `/etc/nginx/sites-available/armguard`
- SSL certificates
- `/var/log/armguard-deploy/02-config-*.log`

---

#### **Phase 3: 03_services.sh - Services**
- Gunicorn service configuration
- Daphne service (WebSockets)
- Nginx configuration
- Service startup

**What it does:**
```bash
✅ Create systemd service units
✅ Configure Gunicorn workers
✅ Setup Daphne for WebSockets
✅ Configure Nginx reverse proxy
✅ Enable and start services
✅ Run migrations
```

**Outputs:**
- `/etc/systemd/system/gunicorn-armguard.service`
- `/etc/systemd/system/daphne-armguard.service`
- Nginx site enabled
- Services running
- `/var/log/armguard-deploy/03-services-*.log`

---

#### **Phase 4: 04_monitoring.sh - Monitoring**
- Health checks
- Log rotation
- Monitoring setup
- Performance validation

**What it does:**
```bash
✅ Setup health check scripts
✅ Configure log rotation
✅ Install monitoring (Prometheus/Grafana optional)
✅ Performance validation
✅ Create monitoring dashboards
```

**Options:**
1. **Minimal**: Basic health checks only
2. **Operational**: System metrics + alerts
3. **Full**: Prometheus + Grafana dashboards

**Outputs:**
- Health check scripts
- Log rotation configs
- Monitoring services (if full selected)
- `/var/log/armguard-deploy/04-monitoring-*.log`

---

**Usage:**
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A

# Run all phases
sudo bash 01_setup.sh
sudo bash 02_config.sh
sudo bash 03_config.sh
sudo bash 04_monitoring.sh

# OR run in one command
sudo bash 01_setup.sh && sudo bash 02_config.sh && sudo bash 03_services.sh && sudo bash 04_monitoring.sh
```

---

### **Method 3: Production Deploy (deploy-armguard.sh)**

```bash
# Location: deployment_A/methods/production/deploy-armguard.sh
```

**Process:**
1. **Interactive Configuration**
   - Project directory (auto-detects git repo!)
   - Domain name
   - SSL type selection
   - Database choice
   - Firewall setup

2. **Installation Steps** (Sequential)
   - System packages
   - Python environment
   - Database setup
   - Service configuration
   - Nginx + SSL
   - Firewall rules

3. **Auto-Detection Features** (NEW!)
   - Detects if running from git repository
   - Offers to use existing location vs copy
   - Benefits shown: Easy updates with git pull

**What makes it different:**
- More detailed prompts
- PostgreSQL optimization
- Production-grade SSL
- Complete audit logging
- Security hardening

**Usage:**
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production

sudo bash deploy-armguard.sh
```

**Special Features:**
- ✅ Admin URL randomization
- ✅ Fail2ban integration
- ✅ Rate limiting
- ✅ Enhanced security headers

---

### **Method 4: Master Deploy (master-deploy.sh)**

```bash
# Location: deployment_A/methods/production/master-deploy.sh
```

**Process - Orchestrated 10-Phase Deployment:**

1. **Phase 1**: Environment Detection
2. **Phase 2**: System Dependencies
3. **Phase 3**: Python Environment
4. **Phase 4**: Database Setup & Migrations
5. **Phase 5**: Gunicorn Service
6. **Phase 6**: Nginx Configuration
7. **Phase 7**: SSL Certificates
8. **Phase 8**: Firewall Configuration
9. **Phase 9**: Log Rotation
10. **Phase 10**: Health Check

**What makes it different:**
- Phase-by-phase execution
- Result tracking for each phase
- Network type support (LAN/WAN/Hybrid)
- Integration with 02_config.sh for network setup
- Comprehensive error handling

**Usage:**
```bash
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production

# Standard LAN deployment
sudo bash master-deploy.sh --network-type lan

# Production WAN deployment
sudo bash master-deploy.sh --network-type wan

# Hybrid LAN+WAN
sudo bash master-deploy.sh --network-type hybrid

# Skip all prompts
sudo bash master-deploy.sh --skip-prompts
```

---

## 🔍 Configuration Files Explained

### **master-config.sh**
Central configuration file used by all scripts.

**Key Variables:**
```bash
PROJECT_NAME="armguard"
PROJECT_DIR="/home/rds/ARMGUARD_RDS_v.2/armguard"  # Auto-detected
SERVICE_NAME="gunicorn-armguard"
RUN_USER="www-data"
RUN_GROUP="www-data"
DEFAULT_DOMAIN="armguard.local"

# Network settings
LAN_INTERFACE="eth1"
SERVER_LAN_IP="192.168.10.1"
WAN_INTERFACE="eth0"

# Service settings
GUNICORN_WORKERS="auto"  # Calculated from CPU cores
DAPHNE_PORT="8001"
```

### **.env File (Generated)**
Django-specific environment configuration.

**Auto-Generated by 02_config.sh:**
```bash
DJANGO_SECRET_KEY=<auto-generated>
DJANGO_DEBUG=False
ALLOWED_HOSTS=armguard.local,192.168.0.10

DATABASE_ENGINE=django.db.backends.postgresql
DATABASE_NAME=armguard_db
DATABASE_USER=armguard_user
DATABASE_PASSWORD=<auto-generated>

REDIS_PASSWORD=<auto-generated>
REDIS_HOST=127.0.0.1

NETWORK_TYPE=lan
LAN_INTERFACE=eth1
LAN_SUBNET=192.168.10.0/24
```

---

## 🛠️ Post-Deployment Tasks

### **Verify Deployment**
```bash
# Check all services
sudo systemctl status gunicorn-armguard
sudo systemctl status daphne-armguard
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis-server

# Run health check
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A/methods/production
sudo bash health-check.sh
```

### **Access Application**
```bash
# Get server IP
hostname -I

# Access via browser
https://192.168.0.10
https://armguard.local
```

### **View Logs**
```bash
# Application logs
sudo journalctl -u gunicorn-armguard -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Deployment logs
ls -la /var/log/armguard-deploy/
```

---

## 🔄 Update Workflow

### **After Git Pull**
```bash
# 1. Pull latest code
cd ~/ARMGUARD_RDS_v.2
git pull origin main

# 2. Update dependencies
cd armguard
source venv/bin/activate  # or .venv/bin/activate
pip install -r requirements.txt --upgrade

# 3. Run migrations
python manage.py migrate

# 4. Collect static files
python manage.py collectstatic --noinput

# 5. Restart services
sudo systemctl restart gunicorn-armguard
sudo systemctl restart daphne-armguard
sudo systemctl restart nginx
```

---

## 📌 Quick Reference

### **Most Common Scenario**
```bash
# First time deployment on Ubuntu server
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

### **Development Setup**
```bash
# Quick dev setup
cd deployment_A
sudo bash 01_setup.sh
sudo bash 02_config.sh
sudo bash 03_services.sh
# Skip monitoring for dev
```

### **Production with Custom Network**
```bash
# Production with network isolation
cd deployment_A/methods/production
sudo bash master-deploy.sh --network-type hybrid
cd ../../
sudo bash 04_monitoring.sh  # Add monitoring
```

### **Testing Environment**
```bash
# Docker-based testing
cd deployment_A/methods/docker-testing
docker-compose up -d
```

---

## 🚫 What NOT to Use

### **legacy_archive/**
- ❌ Old deprecated scripts
- ❌ Kept for reference only
- ❌ May have bugs or outdated approaches
- ✅ Use new modular system instead

### **systematized-deploy.sh**
- ❌ Deprecated wrapper
- ✅ Use 01-04 scripts instead

---

## 💡 Best Practices

1. **Always use ubuntu-deploy.sh first** if you're on Ubuntu
2. **Let scripts auto-detect your project** - don't copy files manually
3. **Run health-check.sh after deployment** to verify
4. **Use git repo directly** for easy updates
5. **Read logs in /var/log/armguard-deploy/** if issues occur
6. **Run sync-validator.ps1** before major deployments

---

## 📞 Troubleshooting

### **Script Won't Execute**
```bash
chmod +x deployment_A/*.sh
chmod +x deployment_A/methods/production/*.sh
```

### **Can't Find Project**
```bash
# Verify path
ls -la ~/ARMGUARD_RDS_v.2/armguard/manage.py

# Run from correct directory
cd ~/ARMGUARD_RDS_v.2/armguard/deployment_A
pwd  # Should show deployment_A folder
```

### **Service Won't Start**
```bash
# Check logs
sudo journalctl -u gunicorn-armguard -n 50
sudo systemctl status gunicorn-armguard
```

### **Need to Change Configuration**
```bash
# Re-run config phase
cd deployment_A
sudo bash 02_config.sh
```

---

## ✅ Summary

**For 90% of users:**
```bash
sudo bash ubuntu-deploy.sh --production
```

**For custom deployments:**
```bash
sudo bash 01_setup.sh && sudo bash 02_config.sh && sudo bash 03_services.sh && sudo bash 04_monitoring.sh
```

**For network isolation:**
```bash
sudo bash methods/production/master-deploy.sh --network-type hybrid
```

That's it! Choose your path and deploy with confidence. 🚀
