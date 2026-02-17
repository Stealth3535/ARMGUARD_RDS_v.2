# 🛡️ ArmGuard Synchronized Deployment System
**Version 4.0.0 - Complete App-Deployment Synchronization**  
**Status:** ✅ All Critical Issues Resolved - Cross-Platform Compatible

---

## 🚨 **NEW: SYNCHRONIZED DEPLOYMENT SYSTEM**

**All app-deployment synchronization issues have been resolved!** This system now provides:

- ✅ **Cross-Platform Support**: Native Windows PowerShell + Linux Bash scripts
- ✅ **Unified Configuration**: Single `.env` file approach (no more hardcoded settings)  
- ✅ **Advanced Database Optimization**: Complete PostgreSQL performance features
- ✅ **Secured Redis**: Password authentication and encryption
- ✅ **Aligned Requirements**: Consistent package versions across all files
- ✅ **Production-Ready Paths**: Proper static/media file handling

### 🚀 Quick Start (Windows Users)
```powershell
# Navigate to deployment directory
cd armguard\deployment_A

# Run interactive deployment helper
.\deployment-helper.ps1

# OR choose specific deployment type
.\deployment-helper.ps1 -DeploymentType main
```

### 🚀 Quick Start (Linux Users)  
```bash
# Navigate to deployment directory
cd armguard/deployment_A

# Run the authoritative production deployment path
sudo bash ubuntu-deploy.sh --production
```

### 🔍 Validate Your System
```powershell
# Windows: Comprehensive validation
.\sync-validator.ps1 -Detailed

# Linux: Basic validation  
./deployment-helper.sh --validate
```

---

## 🎯 **AUTHORITATIVE DEPLOYMENT PATH** 

**✅ Use a single production entrypoint:**

```bash
cd armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

This path handles:
- Development deployments ✅
- Small-scale production ✅  
- Standard enterprise deployments ✅
- SSL certificates (3 types) ✅
- Monitoring (3 levels) ✅
- Cross-platform compatibility ✅

### 🔁 CI/CD Automation Package

![Deployment A CI/CD](https://github.com/Stealth3535/ARMGUARD_RDS_v.2/actions/workflows/deployment-a-cicd.yml/badge.svg)

[View workflow runs](https://github.com/Stealth3535/ARMGUARD_RDS_v.2/actions/workflows/deployment-a-cicd.yml)

Production/staging pipeline assets are now available at:

- `deployment_A/methods/production/ci/`
- `.github/workflows/deployment-a-cicd.yml`

Use this package for automated build/validate/deploy with rollback support over SSH.

#### ⚡ CI/CD Quick Start

1. Configure GitHub Environments: `staging` and `production`.
2. Enable required reviewers for `production` in Environment protection rules.
3. Add required repository/environment secrets listed in `deployment_A/methods/production/ci/README.md`.
4. On target server, copy env templates, set real values, and run: `chmod +x deployment_A/methods/production/ci/*.sh`.
5. Trigger workflow dispatch with `target=staging`; after success and approval gate, run `target=production`.

### 🔧 **New Unified Configuration System**
Instead of hardcoded settings files, the system now uses environment variables:

```bash
# Automatically generated .env file
DJANGO_SECRET_KEY=auto-generated-secure-key
DJANGO_DEBUG=False  
DB_ENGINE=django.db.backends.postgresql
REDIS_PASSWORD=auto-generated-secure-password
NETWORK_TYPE=lan  # or wan, hybrid
# ... 50+ configuration options automatically generated
```

---

## 🔐 **NEW: DEVICE AUTHORIZATION SYSTEM v2.0**

**✅ Military-Grade Device Authorization now integrated!**

### 🛡️ **Enhanced Security Features**
- **Production Security Mode**: Only authorized devices can access sensitive operations
- **Device Fingerprinting**: SHA-256 hashing with MAC address validation
- **Transaction-Level Authorization**: Granular control over who can perform transactions
- **Compliance Ready**: NIST 800-53, FISMA Moderate, OWASP 2021, DoD 8500.01
- **Real-time Monitoring**: All unauthorized attempts logged and monitored

### 🔧 **Device Authorization Integration**
The deployment system automatically configures device authorization:

```bash
# Automatically created during deployment:
authorized_devices.json      → Production device configuration
device_authorization_deployment_summary.txt → Deployment summary

# Key Features:
✅ Production Security Mode (allow_all = false)
✅ 15+ Protected Endpoints (transactions, admin, inventory)
✅ 7+ High-Security Paths (/admin/, /delete/ operations)
✅ Lockout Protection (3 attempts, 30-minute lockout)
✅ Comprehensive Audit Logging
```

### 🎯 **Device Authorization in Deployment**
```
01_setup.sh       → System prerequisites + Redis (required for device auth)
02_config.sh      → Network configuration + SSL setup
03_services.sh    → Django deployment + Device Authorization System ←NEW
04_monitoring.sh  → Health checks + Device Authorization validation
```

### 📋 **Production Device Management**
```bash
# Device management commands (available after deployment):
python manage.py device_auth --list                    # List authorized devices
python manage.py device_auth --add --name "PC-1" --ip "192.168.0.50"  # Add device
python manage.py device_auth --revoke "192.168.0.50"   # Revoke device access
python manage.py device_auth --status                   # System status
python manage.py device_auth --production              # Enable production mode
```

### 🔐 **Security Architecture**
```
Layer 1: Network Segregation (LAN-only transactions)
Layer 2: User Authentication + RBAC
Layer 3: Single Session Enforcement  
Layer 4: Device Authorization (NEW) ← THIS SYSTEM
Layer 5: Rate Limiting + Attack Prevention
Layer 6: Comprehensive Audit Logging
```

### ⚠️ **Important Security Notes**
- **Default Configuration**: 2 devices pre-configured (Server + Armory PC)
- **MAC Address Updates**: Update MAC addresses in `authorized_devices.json` with actual hardware
- **Network Configuration**: Device IPs must match your network configuration
- **Production Mode**: Never set `allow_all = true` in production environments

---

## ⚠️ **DEPRECATED SCRIPT MIGRATION GUIDE**

**If you're upgrading from older ArmGuard deployments:**

### 🔄 **Legacy Script Migration**
| **Old Script (DEPRECATED)** | **Canonical Replacement** | **Status** |
|------------------------------|---------------------------|------------|
| `deploy-master.sh` | `ubuntu-deploy.sh --production` | ❌ **DEPRECATED** - Use canonical path |
| `master-config.sh` | `ubuntu-deploy.sh --production` | ❌ **DEPRECATED** - Use canonical path |
| `systematized-deploy.sh` | `ubuntu-deploy.sh --production` | ❌ **DEPRECATED** - Use canonical path |
| `quick-rpi-setup.sh` | `ubuntu-deploy.sh --production` | ❌ **DEPRECATED** - Auto-detected |
| `fix-all-production-issues.sh` | `ubuntu-deploy.sh --production` | ❌ **DEPRECATED** - Integrated |

### 📁 **Legacy Archive Location**
- **Deprecated scripts moved to**: `./legacy_archive/`
- **Status**: For reference only - do not use for new deployments
- **Migration**: Run any deprecated script to get automatic migration guidance

### 🚨 **Important Notes**
- ⚠️ **Legacy scripts will show deprecation warnings if executed**
- ✅ **All functionality preserved in modular system with improvements**
- 🔄 **Automatic migration prompts provided when running deprecated scripts**

---

## 🚀 Quick Start Guide

### Prerequisites
- **Operating System**: Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, Fedora 34+
- **User Access**: sudo/root privileges required
- **Network**: Internet connectivity for package installation
- **Resources**: Minimum 2GB RAM, 10GB disk space

### 🎬 One-Line Deployment
```bash
cd /path/to/armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

### 📋 Canonical Deployment Flow

```bash
cd /path/to/armguard/deployment_A
sudo bash ubuntu-deploy.sh --production
```

**What it does**: Detects platform/hardware, configures SSL/database/network, deploys services, and validates health.

---

## 🌟 Features

### 🔒 Security Features
- **SSL/TLS Encryption**: Multiple certificate options (self-signed, mkcert, Let's Encrypt)
- **Firewall Configuration**: Automatic port management and security rules
- **Security Middleware**: CSRF, XSS protection, secure headers
- **Database Security**: Connection encryption, user isolation

### 📊 Monitoring & Health
- **Health Checks**: Automated service monitoring every 5 minutes  
- **Log Management**: Centralized logging with automatic rotation
- **Performance Metrics**: System resource monitoring (operational mode)
- **Enterprise Monitoring**: Prometheus + Grafana stack (full mode)

### 🎮 User Experience  
- **Interactive Setup**: Guided configuration with intelligent defaults
- **Progress Indicators**: Clear status updates throughout deployment
- **Error Recovery**: Rollback capabilities and detailed error reporting
- **Validation**: Comprehensive deployment verification

### 🏗️ Enterprise Production
- **Cross-Platform**: Support for major Linux distributions
- **Modular Design**: Independently executable components
- **Production Ready**: Optimized for enterprise deployment scenarios
- **WebSocket Support**: Real-time features with Daphne integration

---

## 📋 Detailed Script Documentation

### 🔧 01_setup.sh - Environment Setup
**Purpose**: Prepares the system foundation for ArmGuard deployment

**Key Functions**:
- System detection and package management
- PostgreSQL installation and configuration
- Redis installation and optimization  
- Nginx installation and basic setup
- Log directory creation
- Security baseline configuration

**Outputs**:
- Environment variables for subsequent scripts
- Configured database server
- Running Redis cache
- Basic Nginx installation

**Configuration Options**:
- Package manager detection (apt/dnf/yum)
- Service management (systemd)
- Log structure setup

### ⚙️ 02_config.sh - Configuration Management
**Purpose**: Configures SSL certificates, Django settings, and application-specific setup

**Key Functions**:
- **SSL Certificate Management**:
  - Self-signed certificates (development)
  - mkcert certificates (development with CA)
  - Let's Encrypt certificates (production)
- **Django Configuration**:
  - Settings.py generation
  - Database connection configuration
  - Security middleware setup
- **Network Configuration**:
  - Firewall rules management
  - Port configuration and validation

**Interactive Prompts**:
- Domain name configuration
- SSL certificate type selection
- Database credentials setup
- Port selection (with conflict detection)

### 🚀 03_services.sh - Service Deployment
**Purpose**: Creates and starts all ArmGuard application services

**Key Functions**:
- **Systemd Service Creation**:
  - armguard-gunicorn.service (HTTP)
  - armguard-daphne.service (WebSocket)
- **Service Configuration**:
  - Process management
  - Log rotation setup
  - Environment variable management
- **Health Validation**:
  - Service status verification
  - Network connectivity testing
  - Application responsiveness checks

**Service Architecture**:
```
Nginx (Port 80/443) → Load Balancer
    ├── Gunicorn (Port 8000) → HTTP Requests
    └── Daphne (Port 8001)   → WebSocket Connections
```

### 📊 04_monitoring.sh - Monitoring & Health Checks
**Purpose**: Implements comprehensive monitoring and health validation

**Monitoring Levels**:

#### 🔹 Minimal Monitoring
- Health checks every 5 minutes
- Basic log error detection
- Service status monitoring

#### 🔹 Operational Monitoring  
- System metrics collection (CPU, memory, disk)
- Advanced log analysis  
- Performance trending
- Automated alerting

#### 🔹 Full Monitoring Stack
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visual dashboards and analytics
- **Node Exporter**: System metrics
- **Redis Exporter**: Cache performance metrics
- **PostgreSQL Exporter**: Database metrics

**Health Check Components**:
```bash
# Manual health check
/usr/local/bin/armguard-health-check

# Log monitoring
/usr/local/bin/armguard-log-monitor

# System metrics (operational/full mode)
/usr/local/bin/armguard-metrics
```

---

## 🔧 Configuration Reference

### 🌐 Network Configuration
| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Nginx | 80 | HTTP | Web server (redirects to HTTPS) |
| Nginx | 443/8443 | HTTPS | Secure web traffic |
| Gunicorn | 8000 | HTTP | Django application |
| Daphne | 8001 | WebSocket | Real-time features |
| PostgreSQL | 5432 | TCP | Database |
| Redis | 6379 | TCP | Cache |

### 🗂️ File Structure
```
/opt/armguard/                    # Application root
├── django_project/               # Django application
├── logs/                         # Application logs  
├── media/                        # User uploads
└── static/                       # Static files

/etc/nginx/                       # Nginx configuration
├── sites-available/armguard      # Site configuration
└── ssl/                          # SSL certificates

/etc/systemd/system/              # Service definitions
├── armguard-gunicorn.service
└── armguard-daphne.service

/var/log/armguard/               # Centralized logging
├── django.log                   # Application logs
├── gunicorn.log                 # HTTP server logs  
├── daphne-access.log           # WebSocket logs
└── deployment/                  # Deploy logs
```

### 🔑 Environment Variables
```bash
# Core Configuration
PROJECT_NAME=armguard
DEFAULT_DOMAIN=your-domain.com
PORT_HTTP=80
PORT_HTTPS=443  
PORT_GUNICORN=8000
PORT_DAPHNE=8001

# Database Configuration  
DB_NAME=armguard_db
DB_USER=armguard_user
DB_PASSWORD=auto_generated

# SSL Configuration
SSL_TYPE=letsencrypt|mkcert|selfsigned
CERT_PATH=/etc/nginx/ssl/
```

---

## 🩺 Troubleshooting Guide

### 🔍 Common Issues & Solutions

#### ❌ Issue: Services Not Starting
**Symptoms**: 
- `systemctl status armguard-*` shows failed
- 502 Bad Gateway errors

**Solution**:
```bash
# Check service logs
journalctl -u gunicorn-armguard -f
journalctl -u armguard-daphne -f

# Restart services
sudo systemctl restart gunicorn-armguard armguard-daphne
sudo systemctl reload nginx

# Validate configuration
/usr/local/bin/armguard-health-check
```

#### ❌ Issue: SSL Certificate Problems
**Symptoms**:
- Browser security warnings
- Certificate expired errors

**Solution**:
```bash
# Regenerate certificates
cd /path/to/deployment_A
sudo bash ubuntu-deploy.sh --production

# Choose appropriate SSL option:
# - letsencrypt (production)
# - mkcert (development)  
# - selfsigned (testing)
```

#### ❌ Issue: Database Connection Errors  
**Symptoms**:
- Django connection errors
- PostgreSQL authentication failures

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -c "SELECT 1;"

# Restart database
sudo systemctl restart postgresql

# Rerun database setup
cd /path/to/deployment_A
sudo bash ubuntu-deploy.sh --production
```

#### ❌ Issue: Port Conflicts
**Symptoms**:
- "Address already in use" errors
- Services fail to bind to ports

**Solution**:
```bash
# Check port usage
sudo netstat -tulpn | grep -E "(80|443|8000|8001)"
sudo ss -tulpn | grep -E "(80|443|8000|8001)"

# Kill conflicting processes
sudo fuser -k 80/tcp
sudo fuser -k 443/tcp

# Reconfigure with different ports
sudo bash ubuntu-deploy.sh --production  # choose different ports when prompted
```

#### ❌ Issue: WebSocket Connection Failures
**Symptoms**:
- Real-time features not working
- WebSocket handshake errors

**Solution**:
```bash
# Check Daphne service
sudo systemctl status armguard-daphne
journalctl -u armguard-daphne --since "1 hour ago"

# Verify Redis connection
redis-cli ping

# Check Nginx WebSocket configuration  
sudo nginx -t
sudo systemctl reload nginx

# Test WebSocket endpoint
curl -H "Connection: Upgrade" -H "Upgrade: websocket" \
     http://localhost:8001/ws/
```

### 🛠️ Diagnostic Commands

```bash
# Comprehensive system check
/usr/local/bin/armguard-health-check

# Service status overview
systemctl status armguard-gunicorn armguard-daphne nginx postgresql redis

# Log monitoring
/usr/local/bin/armguard-log-monitor

# Network connectivity test
curl -I http://localhost/
curl -I https://localhost/

# Database connectivity
sudo -u postgres pg_isready

# Redis connectivity  
redis-cli ping

# Application test
curl http://localhost:8000/admin/
```

### 📞 Getting Help

1. **Check Deployment Logs**: All deployment activities are logged in `/var/log/armguard-deploy/`
2. **Run Health Checks**: Use `/usr/local/bin/armguard-health-check` for quick diagnosis  
3. **View Service Logs**: Use `journalctl -u service-name -f` for real-time logs
4. **Validate Configuration**: Each script can be run multiple times safely for reconfiguration

---

## 🔄 Maintenance & Updates

### 📅 Regular Maintenance Tasks

#### Daily
- Monitor service health via automated checks
- Review error logs for issues
- Check disk space and resource usage

#### Weekly  
- Review security logs
- Update system packages
- Verify backup integrity

#### Monthly
- Rotate and archive old logs
- Update SSL certificates if needed
- Performance optimization review

### 🔄 Update Procedures

#### Application Updates
```bash
# Stop services
sudo systemctl stop armguard-gunicorn armguard-daphne

# Update application code
cd /opt/armguard
git pull origin main

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl start armguard-gunicorn armguard-daphne
```

#### System Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade  # Ubuntu/Debian
sudo dnf update                        # Fedora
sudo yum update                        # CentOS/RHEL

# Reboot if kernel updated
sudo systemctl reboot
```

### 📊 Monitoring Dashboard Access

#### Full Monitoring Stack URLs:
- **Grafana Dashboard**: http://your-domain:3000
  - Username: `admin`  
  - Password: `armguard2024`
- **Prometheus Metrics**: http://your-domain:9090
- **Node Exporter**: http://your-domain:9100/metrics

---

## 🏗️ Advanced Configuration

### 🌐 Production Deployment Checklist

#### Before Production:
- [ ] Configure Let's Encrypt SSL certificates  
- [ ] Set up proper DNS records
- [ ] Configure firewall rules
- [ ] Set up backup procedures
- [ ] Configure monitoring alerts
- [ ] Test disaster recovery procedures

#### Security Hardening:
- [ ] Change default passwords
- [ ] Configure fail2ban
- [ ] Set up log monitoring
- [ ] Enable security updates
- [ ] Configure network security groups
- [ ] Set up intrusion detection

### 🔧 Customization Options

#### Environment-Specific Configuration:
```bash
# Development
export DJANGO_DEBUG=True
export SSL_TYPE=selfsigned

# Staging  
export DJANGO_DEBUG=False
export SSL_TYPE=mkcert

# Production
export DJANGO_DEBUG=False
export SSL_TYPE=letsencrypt
export MONITORING_TYPE=full
```

#### Load Balancing Configuration:
- Modify Nginx upstream configuration
- Add additional Gunicorn workers
- Configure Redis clustering
- Set up database read replicas

---

## 📚 Additional Resources

### 🔗 Links & References
- [ArmGuard Project Documentation](../md/)
- [Django Deployment Best Practices](https://docs.djangoproject.com/en/stable/howto/deployment/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Configuration](https://redis.io/docs/management/config/)

### 📋 Related Files
- [Comprehensive Analysis Report](COMPREHENSIVE_ANALYSIS_REPORT.md) - Detailed comparison of deployment methods
- [Phase 5 Validation Report](PHASE_5_VALIDATION_REPORT.md) - Complete testing and validation results  
- [Security Audit Report](../SECURITY_AUDIT_REPORT.md) - Security assessment
- [Technical Audit Report](../TECHNICAL_AUDIT_REPORT.md) - Technical analysis

---

## ✅ Validation Checklist

After deployment, verify all components:

### 🎯 Core Services
- [ ] Django application accessible via HTTP/HTTPS
- [ ] Admin interface available at `/admin/`
- [ ] WebSocket connections working for real-time features
- [ ] Database operations functioning correctly
- [ ] Redis cache operational

### 🔒 Security  
- [ ] SSL certificates installed and valid
- [ ] HTTPS redirects working
- [ ] Firewall rules applied correctly
- [ ] Security headers present
- [ ] Admin panel secured

### 📊 Monitoring
- [ ] Health checks running automatically  
- [ ] Log rotation configured
- [ ] Monitoring dashboards accessible (if full mode)
- [ ] Alerting configured
- [ ] Error tracking functional

### 🚀 Performance
- [ ] Page load times acceptable
- [ ] WebSocket latency reasonable
- [ ] Database query performance optimized
- [ ] Static file serving efficient
- [ ] Cache hit rates healthy

---

## 🎉 Conclusion

This modular deployment system provides a **production-ready, systematic approach** to deploying ArmGuard with enterprise-grade features, comprehensive monitoring, and excellent user experience. The four-script sequence ensures reliable, repeatable deployments while maintaining flexibility for different deployment scenarios.

**🏆 Achievement Unlocked**: Single systematized deployment solution combining the best of both deployment approaches! 

---

*Documentation Version: 4.0.0*  
*Last Updated: December 19, 2024*  
*Deployment System Status: Production Ready ✅*