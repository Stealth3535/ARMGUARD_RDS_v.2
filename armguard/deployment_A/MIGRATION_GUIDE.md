# 📋 ARMGUARD DEPLOYMENT MIGRATION GUIDE
**Complete Migration from Legacy Scripts to One Authoritative Deployment Path**

---

## 🎯 **MIGRATION OVERVIEW**

**Migration Date**: February 9, 2026  
**Status**: All legacy scripts deprecated and archived  
**New System**: `ubuntu-deploy.sh --production` canonical production deployment

### ✅ **Why Migrate?**
- **Better reliability**: Enhanced error handling and recovery
- **Improved user experience**: Interactive setup with clear guidance  
- **Enhanced security**: Modern SSL management and security practices
- **Device Authorization**: Military-grade device authorization system v2.0
- **Comprehensive monitoring**: 3-tier monitoring system (minimal/operational/full)
- **Simplified maintenance**: Single systematic approach vs 35+ scattered scripts

---

## 🔄 **LEGACY TO CANONICAL PATH MAPPING**

### 📊 **Direct Replacements**
| **Legacy Script** | **Lines** | **Modular Replacement** | **Improvement** |
|-------------------|-----------|-------------------------|----------------|
| `deploy-master.sh` | 526 | `ubuntu-deploy.sh --production` | Better UX, error handling |
| `master-config.sh` | 778 | `ubuntu-deploy.sh --production` | Unified configuration flow |
| `systematized-deploy.sh` | 470 | `ubuntu-deploy.sh --production` | Enhanced validation |
| `systematized-config.sh` | 283 | `ubuntu-deploy.sh --production` | Unified configuration |
| `fix-all-production-issues.sh` | 333 | Built into all scripts | Proactive fixes |
| `pre-deployment-check.sh` | 157 | `ubuntu-deploy.sh --production` (automatic) | Integrated checks |

### 🏭 **Enterprise Method Equivalents**
| **Legacy Approach** | **New Approach** | **When to Use** |
|-------------------|------------------|----------------|
| `deploy-master.sh production` | `ubuntu-deploy.sh --production` | Standard production |
| `deploy-master.sh vm-test` | `methods/vmware-setup/vm-deploy.sh` | VMware deployments |
| `deploy-master.sh docker-test` | `methods/docker-testing/` | Testing environments |
| `deploy-master.sh basic-setup` | `ubuntu-deploy.sh --production` | Standard deployments |

---

## 🚀 **MIGRATION SCENARIOS**

### 🎯 **Scenario 1: Simple Development Setup**
**Old Way:**
```bash
./deploy-master.sh basic-setup
```

**✅ New Way:**
```bash
./ubuntu-deploy.sh --production
```

**🎉 Benefits:**
- Interactive SSL certificate selection
- Enhanced monitoring options (3 levels)
- Better error messages and recovery
- Automatic platform detection (ARM64, RPi)

### 🏭 **Scenario 2: Production Deployment**
**Old Way:**
```bash  
./deploy-master.sh production
source master-config.sh
./fix-all-production-issues.sh
```

**✅ New Way:**
```bash
./ubuntu-deploy.sh --production
```

**🎉 Benefits:**
- Unified SSL management (Let's Encrypt, mkcert, custom)
- Enhanced security hardening
- Comprehensive health monitoring
- Automatic backup and recovery procedures

### 🧪 **Scenario 3: Testing Environment**
**Old Way:**
```bash
./deploy-master.sh docker-test
# Manual monitoring setup
```

**✅ New Way:**
```bash
cd methods/docker-testing
docker-compose up
```

**🎉 Benefits:**
- Complete testing stack (Prometheus, Grafana, Loki)
- Isolated environment for testing
- Automated testing workflows

### 🔐 **Scenario 4: Device Authorization Migration**
**Old Way (Manual):**
```bash
# No device authorization system - manual security management
./deploy-master.sh production
# Manual whitelist management in code
# No device fingerprinting or lockout protection
```

**✅ New Way (Automated Device Authorization v2.0):**
```bash
./ubuntu-deploy.sh --production
```

**🎉 Benefits:**
- **Military-Grade Security**: NIST 800-53, FISMA, OWASP 2021 compliance
- **Automatic Device Registration**: Production devices pre-configured
- **Runtime Protection**: Real-time device validation and lockout
- **Comprehensive Auditing**: All unauthorized attempts logged
- **Zero Configuration**: Device authorization ready out-of-the-box
- **Production Ready**: Pre-configured for armory deployment

### 📋 **Device Authorization Migration Checklist:**
```bash
✅ Redis Configuration: Automatically configured for device caching
✅ Production Security Mode: allow_all = false (secure by default)  
✅ Device Fingerprinting: SHA-256 hashing with MAC validation
✅ Protected Endpoints: 15+ restricted paths, 7+ high-security paths
✅ Lockout Protection: 3 attempts, 30-minute lockout duration
✅ Audit Integration: Comprehensive logging and monitoring
✅ Network Awareness: LAN/WAN/Hybrid network support
✅ Compliance Ready: Military security standards built-in
```

### 🌐 **Scenario 5: Network Isolation (LAN/WAN)**
**Old Way:**
```bash
# Manual network configuration
./deploy-master.sh production
# Manual SSL per interface
```

**✅ New Way (Integrated):**
```bash
./ubuntu-deploy.sh --production
# Select network type during prompts:
# - LAN-only (192.168.10.x subnet)
# - Hybrid (LAN + WAN isolation)
# - WAN-only (public access)
```

**🎉 Benefits:**
- ✨ **Fully integrated** network isolation configuration
- 🔒 **Advanced security** with interface-specific SSL certificates  
- 🛡️ **Comprehensive firewall** with fail2ban and rate limiting
- ✅ **Automatic verification** of network configuration
- 🎯 **Single deployment path** - no separate network setup required

---

## ⚙️ **CONFIGURATION MIGRATION**

### 🔧 **Old Configuration System**
```bash
# Old scattered approach
source master-config.sh          # 778 lines, complex
./systematized-config.sh          # Additional config
./fix-all-production-issues.sh    # Manual fixes
```

### ✅ **New Unified Configuration**
```bash
# New interactive approach
./ubuntu-deploy.sh --production
```

**🎯 Interactive Configuration Features:**
- **SSL Certificate Management**: Choose from 4 options
  - Self-signed (development)
  - mkcert (local development)
  - Let's Encrypt (production)
  - Custom certificates
- **Database Configuration**: Automated PostgreSQL setup
- **Security Settings**: Firewall, Django security middleware
- **WebSocket Setup**: Optimized Redis and Daphne configuration

---

## 📊 **MONITORING SYSTEM UPGRADE**

### 📈 **Old Monitoring (Limited)**
```bash
# Basic health checks only
./methods/production/health-check.sh
```

### ✅ **New 3-Tier Monitoring System**
```bash
./ubuntu-deploy.sh --production
# Monitoring setup is integrated in the canonical deployment flow.
# For post-deploy checks, run: ./methods/production/health-check.sh
```

**🚀 Enhanced Monitoring Features:**
- **Health Checks**: Every 5 minutes with systemd timer
- **Log Monitoring**: Error detection with pattern matching
- **System Metrics**: CPU, memory, disk, network monitoring
- **Performance Tracking**: Application response time monitoring
- **Full Stack**: Optional Prometheus + Grafana dashboards

---

## 🔐 **SECURITY IMPROVEMENTS**

### 🛡️ **Enhanced Security Features**

| **Security Aspect** | **Legacy System** | **New Canonical Flow** |
|-------------------|------------------|----------------------|
| **SSL Management** | Manual, error-prone | Automated with 4 certificate options |
| **Firewall Config** | Basic rules | Intelligent port management |
| **Input Validation** | Inconsistent | Comprehensive validation |
| **Error Handling** | `set -e` only | `set -e` + `set -u` + comprehensive error trapping |
| **Secrets Management** | Scattered | Centralized with production methods integration |
| **Security Headers** | Manual | Automated Django security middleware |

---

## 🚨 **MIGRATION CHECKLIST**

### ✅ **Pre-Migration**
- [ ] **Backup current deployment** (use `methods/production/secure-backup.sh`)
- [ ] **Document current configuration** (ports, SSL, database settings)
- [ ] **Test new system in staging** (use `methods/docker-testing/`)
- [ ] **Review network requirements** (advanced options available in `02_config.sh`)

### ✅ **During Migration**
- [ ] **Archive old scripts** (automatically moved to `legacy_archive/`)
- [ ] **Run canonical deployment** (`ubuntu-deploy.sh --production`)
- [ ] **Verify SSL certificates** (check certificate renewal)
- [ ] **Test all services** (use health check tools)
- [ ] **Configure monitoring** (select appropriate monitoring level)

### ✅ **Post-Migration** 
- [ ] **Validate deployment** (`/usr/local/bin/armguard-health-check`)
- [ ] **Test application functionality** (login, inventory, transactions)
- [ ] **Verify monitoring** (check logs, metrics, alerts)
- [ ] **Update documentation** (record new procedures)
- [ ] **Train team** (share new deployment commands)

---

## 🔧 **TROUBLESHOOTING MIGRATION ISSUES**

### ❌ **Common Migration Problems**

#### **Problem**: "Legacy script still being used by automation"
**✅ Solution**: Legacy wrapper scripts provide migration prompts
```bash
# Legacy scripts now show deprecation warnings and offer migration
./deploy-master.sh  # Shows migration options automatically
```

#### **Problem**: "Configuration not matching old system"
**✅ Solution**: Use interactive configuration
```bash
./ubuntu-deploy.sh --production  # Guides through all configuration options
```

#### **Problem**: "Monitoring not as comprehensive as expected"
**✅ Solution**: Choose full monitoring stack
```bash
./ubuntu-deploy.sh --production  # Choose full monitoring options during prompts
```

#### **Problem**: "Need enterprise production features"  
**✅ Solution**: Use canonical production deployment
```bash
./ubuntu-deploy.sh --production
```

---

## 🎯 **MIGRATION TIMELINE RECOMMENDATION**

### 📅 **Recommended Migration Schedule**
| **Week** | **Phase** | **Activities** | **Deliverables** |
|----------|-----------|---------------|----------------|
| **Week 1** | **Planning** | Backup, documentation, staging setup | Migration plan |
| **Week 2** | **Staging Test** | Deploy canonical path in test environment | Validated config |
| **Week 3** | **Production Migration** | Execute production migration | Live system |
| **Week 4** | **Validation** | Monitor, optimize, document | Final validation |

---

## 🎉 **POST-MIGRATION BENEFITS SUMMARY**

### 🚀 **Immediate Benefits**
- **Single Command Deployment**: `01-04 script sequence`
- **Interactive Configuration**: No more manual config editing
- **Enhanced Monitoring**: Health checks, metrics, and dashboards
- **Better Error Messages**: Clear guidance when issues occur
- **Automatic Recovery**: Built-in rollback and fix procedures

### 🏆 **Long-term Benefits**
- **Reduced Maintenance**: 50% fewer scripts to maintain
- **Improved Reliability**: Better error handling and validation
- **Enhanced Security**: Modern security practices and SSL management
- **Easier Updates**: Modular system enables easier component updates
- **Better Documentation**: Comprehensive guides and decision trees

---

## 📞 **POST-MIGRATION SUPPORT**

### 🔍 **Resources**
- **Primary Documentation**: `./README.md` (updated with decision tree)
- **Health Checks**: `/usr/local/bin/armguard-health-check`
- **Log Monitoring**: `/usr/local/bin/armguard-log-monitor`
- **Legacy Reference**: `./legacy_archive/` (for reference only)

### 🆘 **If You Need Help**
1. **Check deprecation warnings**: Legacy scripts provide migration guidance
2. **Review README.md**: Updated with clear decision tree
3. **Use health checks**: Validate your deployment status
4. **Check logs**: `/var/log/armguard-deploy/` for deployment logs

---

**🎯 Migration completed successfully! Welcome to the systematized ArmGuard deployment system!** 🚀

*Migration Guide - February 9, 2026*  
*System Status: Legacy deprecated, modular system operational*