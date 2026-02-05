# 🚀 ArmGuard Deployment v2.0 - Upgrade Guide

## What's New in v2.0

The deployment folder has been significantly enhanced with production-grade features:

### 🆕 New Features

#### 1. **Health Check System** (`health-check.sh`)
Comprehensive deployment verification that checks:
- System resources (CPU, memory, disk space)
- Service status (Gunicorn, Nginx)
- Network connectivity and port availability
- Application files and configuration
- Recent errors in logs
- Security configuration

**Usage:**
```bash
sudo bash deployment/health-check.sh
```

**Exit codes:**
- `0` - All checks passed (healthy)
- `0` - Warnings only (operational)
- `1` - Critical failures detected

---

#### 2. **Rollback Capability** (`rollback.sh`)
Safely restore from backup with:
- Interactive backup selection
- Automatic safety backup before rollback
- Database restoration
- Service restart
- Integrated health check

**Usage:**
```bash
# Interactive mode - choose from available backups
sudo bash deployment/rollback.sh

# Direct mode - specify backup file
sudo bash deployment/rollback.sh /var/www/armguard/backups/db.sqlite3.backup_20260128_120000
```

---

#### 3. **Centralized Configuration** (`config.sh`)
All deployment scripts now support a centralized configuration:

**Environment Variables:**
```bash
# Customize paths
export ARMGUARD_PROJECT_DIR="/custom/path"
export ARMGUARD_SOCKET_PATH="/custom/socket"

# Customize performance
export ARMGUARD_WORKERS=5
export ARMGUARD_TIMEOUT=120

# Customize security
export ARMGUARD_RATE_LIMIT="20r/s"
export ARMGUARD_CLIENT_MAX_BODY_SIZE="20M"
```

**Helper Functions:**
```bash
source deployment/config.sh

# Use helper functions
WORKERS=$(calculate_workers)
PLATFORM=$(detect_platform)
ARCH=$(detect_architecture)
```

---

#### 4. **Environment Detection** (`detect-environment.sh`)
Automatically detects and optimizes for your platform:
- Hardware architecture (x86, ARM64, ARMv7)
- Platform type (Raspberry Pi, VM, Docker, WSL)
- CPU cores and memory
- Optimization recommendations
- Configuration suggestions

**Usage:**
```bash
bash deployment/detect-environment.sh
```

**Detected Platforms:**
- Raspberry Pi (models 3, 4, 5)
- Virtual Machines (VMware, VirtualBox, KVM)
- Docker Containers
- WSL/WSL2
- Physical Servers

---

#### 5. **Log Rotation** (`setup-logrotate.sh`)
Automated log management:
- Daily rotation
- 14-day retention
- Automatic compression
- Graceful service reload

**Usage:**
```bash
sudo bash deployment/setup-logrotate.sh
```

**Managed Logs:**
- `/var/log/armguard/*.log`
- `/var/log/nginx/armguard_*.log`

---

#### 6. **Enhanced Nginx Security** (`install-nginx-enhanced.sh`)
Advanced security features:
- **Rate Limiting:**
  - General pages: 10 req/s (burst: 20)
  - Login/Auth: 5 req/min (burst: 3)
  - API: 20 req/s (burst: 10)
  - Admin: 5 req/min (burst: 5)
- **Connection Limiting:** 10 connections per IP
- **Security Headers:** XSS, CSRF, frame protection
- **Exploit Blocking:** PHP, ASP, hidden files
- **Strict Admin Protection**

**Usage:**
```bash
sudo bash deployment/install-nginx-enhanced.sh [domain]
```

---

## 🔄 Upgrading from v1.0

### Option 1: Quick Upgrade (Existing Deployment)

Simply pull the latest deployment scripts:

```bash
cd /var/www/armguard
sudo git pull origin main
```

The new scripts are fully backward compatible!

### Option 2: Enable New Features

1. **Set up log rotation:**
```bash
sudo bash deployment/setup-logrotate.sh
```

2. **Run initial health check:**
```bash
sudo bash deployment/health-check.sh
```

3. **Detect your environment:**
```bash
bash deployment/detect-environment.sh
```

4. **Upgrade to enhanced Nginx (optional):**
```bash
sudo bash deployment/install-nginx-enhanced.sh
```

### Option 3: Fresh Installation

For new deployments, use the main deployment script which now includes all new features:

```bash
sudo bash deployment/deploy-armguard.sh
```

---

## 📊 New Workflow

### Before v2.0:
```bash
1. Deploy
2. Hope everything works
3. Manual troubleshooting
```

### With v2.0:
```bash
1. Pre-check environment: bash deployment/pre-check.sh
2. Detect platform: bash deployment/detect-environment.sh
3. Deploy: sudo bash deployment/deploy-armguard.sh
4. Verify: sudo bash deployment/health-check.sh
5. Update safely: sudo bash deployment/update-armguard.sh
   → Auto-backup → Update → Health check → Rollback if failed
```

---

## 🛡️ Enhanced Update Process

The update script now includes automatic health checks:

```bash
sudo bash deployment/update-armguard.sh
```

**What happens:**
1. ✅ Pre-update checks
2. ✅ Automatic database backup
3. ✅ Code update from GitHub
4. ✅ Dependencies installation
5. ✅ Database migrations
6. ✅ Static files collection
7. ✅ Service restart
8. ✅ **🆕 Health check**
9. ✅ **🆕 Automatic rollback on failure**

If health check fails, you'll be prompted to rollback automatically!

---

## 🔧 Configuration Examples

### High-Traffic Setup
```bash
export ARMGUARD_WORKERS=9  # 2 * 4 cores + 1
export ARMGUARD_RATE_LIMIT="30r/s"
export ARMGUARD_TIMEOUT=120
```

### Low-Memory Setup (Raspberry Pi 3)
```bash
export ARMGUARD_WORKERS=3
export ARMGUARD_TIMEOUT=90
export ARMGUARD_MAX_REQUESTS=500
```

### Development Setup
```bash
export ARMGUARD_WORKERS=2
export ARMGUARD_RATE_LIMIT="100r/s"  # Relaxed
```

---

## 📈 Monitoring & Maintenance

### Daily Health Check
```bash
# Add to crontab
0 6 * * * /var/www/armguard/deployment/health-check.sh
```

### Weekly Backup Check
```bash
# List backups
ls -lh /var/www/armguard/backups/

# Test restore (to temporary location)
sudo bash deployment/rollback.sh
```

### Log Monitoring
```bash
# Real-time logs
sudo tail -f /var/log/armguard/error.log

# Check for errors
sudo grep -i error /var/log/armguard/error.log | tail -20
```

---

## 🆘 Troubleshooting

### Health Check Failed

1. **Check detailed output:**
```bash
sudo bash deployment/health-check.sh
```

2. **Review specific failures and follow recommendations**

3. **Check service logs:**
```bash
sudo journalctl -u gunicorn-armguard -n 50
```

### Need to Rollback

```bash
# Interactive selection
sudo bash deployment/rollback.sh

# Or specify backup
sudo bash deployment/rollback.sh /var/www/armguard/backups/db.sqlite3.backup_YYYYMMDD_HHMMSS
```

### Rate Limiting Too Strict

Edit `/etc/nginx/sites-available/armguard` and adjust:
```nginx
limit_req_zone $binary_remote_addr zone=armguard_general:10m rate=20r/s;
```

Then reload:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📚 Additional Resources

- **Full Documentation:** [README.md](README.md)
- **Quick Deploy:** [QUICK_DEPLOY.md](QUICK_DEPLOY.md)
- **Security Guide:** [NGINX_SSL_GUIDE.md](NGINX_SSL_GUIDE.md)
- **LAN Deployment:** [SECURE_LAN_DEPLOYMENT.md](SECURE_LAN_DEPLOYMENT.md)

---

## 🎉 Summary

**v2.0 brings enterprise-grade reliability to ArmGuard deployments:**

✅ Automated health checks
✅ One-click rollback
✅ Platform optimization
✅ Log management
✅ Enhanced security
✅ Backward compatible

**Upgrade today for a more robust and maintainable deployment!**
