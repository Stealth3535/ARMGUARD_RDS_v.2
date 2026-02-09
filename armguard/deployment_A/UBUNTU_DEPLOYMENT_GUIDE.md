# 🐧 ArmGuard Ubuntu Server Deployment Guide

## ✅ **UBUNTU DEPLOYMENT READY!**

Your ArmGuard system is **fully optimized** for Ubuntu server deployment with automatic environment detection and platform-specific optimizations.

## 🚀 **QUICK UBUNTU DEPLOYMENT**

### **Option 1: Automated Ubuntu Deployment**
```bash
# Clone or transfer your ArmGuard project to Ubuntu server
cd /path/to/armguard/deployment_A

# Run comprehensive environment detection
sudo bash methods/production/detect-environment.sh

# Run pre-deployment validation
sudo bash methods/production/pre-check.sh

# Deploy with master script (recommended)
sudo bash methods/production/master-deploy.sh --network-type lan
```

### **Option 2: Complete Production Deployment**
```bash
# For full production deployment with all security features
sudo bash methods/production/deploy-armguard.sh
```

## 🖥️ **UBUNTU-SPECIFIC OPTIMIZATIONS**

### **Automatic Ubuntu Detection**
The deployment scripts automatically detect and optimize for:
- **Ubuntu 18.04+** (all versions supported)
- **Debian-based** systems
- **x86_64 architecture** (standard servers)
- **ARM64 architecture** (ARM-based servers)
- **Virtual machines** (VMware, VirtualBox, KVM)
- **Cloud instances** (AWS, Azure, GCP)

### **Ubuntu Server Optimizations**
```bash
# The system automatically configures:
✅ APT package management with DEBIAN_FRONTEND=noninteractive
✅ Systemd service management (gunicorn, nginx, postgresql, redis)
✅ UFW firewall configuration for Ubuntu
✅ Ubuntu-specific Python virtual environment paths
✅ Standard Ubuntu web server paths (/var/www/)
✅ Ubuntu user permissions (www-data group)
✅ Logrotate integration for Ubuntu log management
✅ Let's Encrypt SSL for Ubuntu servers
```

## 🔧 **UBUNTU DEPLOYMENT PROFILES**

### **Profile 1: Ubuntu LAN Server**
```bash
sudo bash methods/production/master-deploy.sh --network-type lan
```
- **Use Case:** Internal company network, home lab
- **Database:** SQLite (lightweight)
- **SSL:** mkcert (self-signed for LAN)
- **Firewall:** UFW with LAN-only access
- **Performance:** Optimized for local network

### **Profile 2: Ubuntu WAN Server (Internet-Facing)**
```bash
sudo bash methods/production/master-deploy.sh --network-type wan
```
- **Use Case:** Public internet deployment
- **Database:** PostgreSQL (production-ready)
- **SSL:** Let's Encrypt (public valid certificates)
- **Firewall:** UFW with strict internet security
- **Performance:** Optimized for internet traffic

### **Profile 3: Ubuntu Hybrid Server**
```bash
sudo bash methods/production/master-deploy.sh --network-type hybrid
```
- **Use Case:** Mixed internal/external access
- **Database:** PostgreSQL with connection pooling
- **SSL:** Let's Encrypt with LAN fallback
- **Firewall:** UFW with selective access
- **Performance:** Balanced for mixed usage

## 📊 **UBUNTU HARDWARE RECOMMENDATIONS**

### **Minimum Requirements**
- **CPU:** 2 cores (x86_64 or ARM64)
- **RAM:** 2GB minimum, 4GB recommended
- **Storage:** 10GB free space
- **Network:** Stable internet connection

### **Recommended Ubuntu Server Specifications**
- **CPU:** 4+ cores for production workloads
- **RAM:** 8GB+ for optimal performance
- **Storage:** SSD storage for database performance
- **Network:** Gigabit connection for WAN deployment

### **Automatic Resource Optimization**
The deployment system automatically optimizes based on your Ubuntu server:
```bash
# CPU cores detected → Gunicorn workers calculated (2 * cores + 1)
# RAM detected → Database connection limits set appropriately
# Storage detected → Log rotation configured based on available space
# Network detected → Rate limiting configured for connection type
```

## 🔒 **UBUNTU SECURITY FEATURES**

### **Production Security Hardening**
```bash
✅ UFW Firewall: Automatically configured for Ubuntu
✅ Fail2ban: Brute force protection for SSH and web services
✅ SSL/TLS: Let's Encrypt or mkcert certificates
✅ Security Headers: HTTPS enforcement, HSTS, CSP
✅ Rate Limiting: nginx-based request limiting
✅ Log Monitoring: Security event logging and rotation
✅ User Permissions: Proper www-data isolation
✅ Database Security: PostgreSQL with encrypted connections
```

## 🛠️ **UBUNTU SERVICE MANAGEMENT**

### **Service Control Commands**
```bash
# ArmGuard application service
sudo systemctl status gunicorn-armguard
sudo systemctl restart gunicorn-armguard
sudo systemctl enable gunicorn-armguard

# Web server
sudo systemctl status nginx
sudo systemctl restart nginx

# Database (if PostgreSQL)
sudo systemctl status postgresql
sudo systemctl restart postgresql

# Cache server
sudo systemctl status redis-server
sudo systemctl restart redis-server
```

### **Log Monitoring**
```bash
# Application logs
sudo journalctl -u gunicorn-armguard -f

# Nginx access logs
sudo tail -f /var/log/nginx/armguard_access.log

# Security logs
sudo tail -f /var/log/armguard/security.log
```

## 📈 **UBUNTU PERFORMANCE TUNING**

### **Automatic Performance Optimization**
The deployment system automatically configures:

**For Ubuntu Servers (x86_64):**
- **Gunicorn Workers:** Based on CPU cores (optimal for x86_64)
- **Database Connections:** Optimized for available RAM
- **Nginx Configuration:** High-performance settings for Ubuntu
- **Cache Settings:** Redis optimization for Ubuntu

**For Ubuntu ARM64 Servers:**
- **ARM-Optimized Workers:** Adjusted for ARM CPU characteristics
- **Memory Management:** Optimized for ARM memory architecture
- **Storage Optimization:** SSD-aware configuration

## 🌐 **UBUNTU NETWORK INTEGRATION**

### **LAN Deployment (Ubuntu Server)**
```bash
# Perfect for:
✅ Company intranets
✅ Home lab environments
✅ Development/staging servers
✅ Internal tool deployment
```

### **WAN Deployment (Ubuntu Server)**
```bash
# Perfect for:
✅ Production web applications
✅ Client-facing deployments
✅ SaaS applications
✅ Public API servers
```

## 🔄 **UBUNTU UPDATE & MAINTENANCE**

### **Automated Update Script**
```bash
# Update ArmGuard application
sudo bash methods/production/update-armguard.sh

# System maintenance
sudo bash methods/production/health-check.sh
```

### **Ubuntu System Updates**
```bash
# The deployment includes automatic handling of:
✅ Ubuntu package updates (apt update/upgrade)
✅ Python dependency updates
✅ Security patches
✅ Service restarts after updates
```

## 📱 **UBUNTU DEPLOYMENT VERIFICATION**

### **Post-Deployment Health Check**
```bash
sudo bash methods/production/health-check.sh
```

**Verifies:**
- ✅ Ubuntu system resources
- ✅ All services running properly
- ✅ Database connectivity
- ✅ Web server response
- ✅ SSL certificate validity
- ✅ Firewall configuration
- ✅ Log rotation working

## 💡 **UBUNTU DEPLOYMENT TIPS**

### **Best Practices for Ubuntu Servers**
1. **Use Ubuntu LTS versions** (20.04, 22.04, 24.04) for stability
2. **Enable automatic security updates**
3. **Use SSH key authentication** instead of passwords
4. **Configure proper backup strategy** for database and logs
5. **Monitor system resources** with the included health-check script
6. **Use systemd service management** for reliable service control

### **Ubuntu Cloud Deployment**
The scripts work perfectly on:
- **AWS EC2** Ubuntu instances
- **Azure** Ubuntu VMs
- **Google Cloud** Ubuntu instances
- **DigitalOcean** Ubuntu droplets
- **Linode** Ubuntu servers

---

## 🎯 **SUMMARY: UBUNTU DEPLOYMENT READY!**

Your ArmGuard system provides **complete Ubuntu server deployment automation** with:

- ✅ **Automatic Ubuntu detection** and optimization
- ✅ **Production-ready security** hardening
- ✅ **Scalable architecture** for any Ubuntu server size
- ✅ **Comprehensive service management**
- ✅ **Performance optimization** based on hardware
- ✅ **Complete monitoring and logging**

**Deploy on Ubuntu now:** `sudo bash methods/production/master-deploy.sh`