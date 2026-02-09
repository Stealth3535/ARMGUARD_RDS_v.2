# 🔐 ArmGuard Unified VPN Integration Guide

## Overview

This guide unifies the VPN access solutions for ArmGuard, combining the comprehensive WireGuard integration with quick-setup options. The system provides secure remote access while maintaining strict military-grade security compliance.

**✅ Status**: **UNIFIED AND PRODUCTION READY**

## 🔐 **SECURITY COMPLIANCE MAINTAINED**

### **✅ Core Security Requirements:**
1. **Transactions LAN-Only**: ✅ **STRICTLY ENFORCED** - All armory transactions require physical LAN presence
2. **Network Isolation**: ✅ **IMPLEMENTED** - VPN provides read-only remote monitoring only
3. **Internet Safety**: ✅ **SECURED** - No direct internet exposure of sensitive operations
4. **Remote Monitoring**: ✅ **ENHANCED** - Secure inventory viewing and status monitoring from any location

### **Access Control Matrix:**
| Connection Type | Location | Transactions | Inventory | Status | Reports |
|----------------|----------|--------------|-----------|---------|---------|
| **Physical LAN** | On-Site | ✅ Full Access | ✅ Full Access | ✅ Full Access | ✅ All Reports |
| **VPN Remote** | Off-Site | ❌ **BLOCKED** | ✅ Read-Only | ✅ Read-Only | ✅ Basic Reports |
| **Direct WAN** | Internet | ❌ **BLOCKED** | ❌ **BLOCKED** | ❌ **BLOCKED** | ❌ **BLOCKED** |

## 🚀 **Unified VPN Architecture**

### **Two-Tier VPN System**

#### **Tier 1: Comprehensive VPN Integration**
- **Location**: `armguard/vpn_integration/`
- **Purpose**: Full-featured WireGuard implementation with Django integration
- **Features**: Role-based access, audit logging, session management, monitoring
- **Best For**: Production deployments requiring full compliance and monitoring

#### **Tier 2: Quick Setup VPN**
- **Location**: `armguard/vpn_integration/tools/quick-vpn-setup.sh`
- **Purpose**: Rapid deployment for testing and simple setups
- **Features**: Basic WireGuard server setup, client generation
- **Best For**: Development, testing, and simple deployments

## 📋 **Installation Options**

### **Option A: Full Production VPN (Recommended)**

For military-grade deployment with comprehensive monitoring and compliance:

```bash
# Navigate to VPN integration directory
cd armguard/vpn_integration

# Follow the comprehensive implementation guide
cat IMPLEMENTATION_GUIDE.md

# Run the comprehensive setup
sudo bash wireguard/scripts/setup-wireguard-server.sh
```

**Features Included:**
- Military-grade encryption (ChaCha20Poly1305)
- Role-based access control (4 levels)
- Real-time session monitoring
- Comprehensive audit logging
- Django middleware integration
- Automatic security enforcement

### **Option B: Quick Setup VPN**

For rapid deployment and testing:

```bash
# Navigate to tools directory  
cd armguard/vpn_integration/tools

# Run quick setup
sudo bash quick-vpn-setup.sh

# Follow prompts for basic configuration
```

**Features Included:**
- Basic WireGuard server setup
- Simple client configuration generation
- Standard encryption
- Basic firewall rules

### **Option C: Hybrid Approach**

Start with quick setup for immediate access, then upgrade to comprehensive:

```bash
# 1. Initial quick setup
cd armguard/vpn_integration/tools
sudo bash quick-vpn-setup.sh

# 2. Later upgrade to comprehensive
cd ../
sudo bash wireguard/scripts/setup-wireguard-server.sh --upgrade-from-quick
```

## 🔧 **Configuration Integration**

### **Django Settings Integration**

The unified system automatically integrates with Django settings through VPN-aware middleware:

```python
# Automatically included in unified deployment
MIDDLEWARE = [
    'vpn_integration.core_integration.vpn_middleware.VPNSecurityMiddleware',
    # ... other middleware
]

# VPN-specific settings
VPN_SETTINGS = {
    'enabled': True,
    'enforce_lan_only_transactions': True,
    'allow_vpn_monitoring': True,
    'vpn_network_range': '10.0.0.0/16',
    'session_timeout': 3600,  # 1 hour
}
```

### **Network Access Control**

```python
# Automatic enforcement through decorators
@vpn_aware_view
@require_lan_for_transactions
def transaction_create(request):
    # Only accessible from LAN
    pass

@allow_vpn_access  
def inventory_status(request):
    # Read-only access via VPN allowed
    pass
```

## 🔐 **Security Features**

### **Unified Security Enforcement**

1. **Network Layer Security**
   ```bash
   # Automatic firewall configuration
   ufw allow 51820/udp  # WireGuard port
   ufw allow 8443/tcp   # LAN HTTPS (restricted to VPN/LAN)
   ufw deny 443/tcp     # Block direct WAN access
   ```

2. **Application Layer Security**
   - VPN-aware middleware automatically detects connection source
   - Transaction endpoints blocked for VPN connections
   - Read-only inventory access via VPN
   - Session management with automatic timeouts

3. **Audit and Monitoring**
   ```bash
   # Real-time monitoring
   tail -f /var/log/armguard/vpn-access.log
   tail -f /var/log/armguard/security-audit.log
   ```

## 📊 **Monitoring and Management**

### **VPN Status Dashboard**

Access the VPN management interface:
```
https://your-server:8443/admin/vpn/status/
```

**Available Information:**
- Active VPN connections
- User session details
- Connection history
- Security events
- Performance metrics

### **Command Line Management**

```bash
# View active connections
sudo wg show

# Check VPN logs
sudo journalctl -u wg-quick@wg0 -f

# Monitor ArmGuard VPN access
tail -f /var/log/armguard/vpn-access.log

# Security audit
bash armguard/vpn_integration/monitoring/security-audit.sh
```

## 🔄 **Migration and Upgrade Paths**

### **From Previous VPN Implementations**

If you have existing VPN setups, migrate to the unified system:

```bash
# Backup existing configuration
sudo cp /etc/wireguard/wg0.conf /etc/wireguard/wg0.conf.backup

# Run migration script
cd armguard/vpn_integration/tools
sudo bash migrate-existing-vpn.sh

# Test new configuration
sudo systemctl restart wg-quick@wg0
```

### **From Internet Access Solutions**

If you were using the root-level internet access solutions:

```bash
# The unified deployment system automatically handles this
cd deployment
sudo bash unified-deployment.sh

# Select VPN remote access mode when prompted
```

## 📱 **Client Configuration**

### **Client Files Location**

After VPN server setup, client configurations are available:

```
armguard/vpn_integration/clients/
├── commander-client.conf      # Full access (LAN equivalent)
├── officer-client.conf        # Management access
├── technician-client.conf     # Technical monitoring
├── observer-client.conf       # Read-only access
└── mobile/                    # Mobile-specific configs
    ├── ios/
    └── android/
```

### **Client Setup Instructions**

**Desktop Clients (Windows/Mac/Linux):**
```bash
# Install WireGuard client
# Import .conf file
# Connect using WireGuard application
```

**Mobile Clients:**
```bash
# Install WireGuard app from app store
# Scan QR code generated during setup
# Or import configuration file
```

## 🚨 **Security Guidelines**

### **Best Practices**

1. **Regular Security Audits**
   ```bash
   # Run weekly security checks
   cd armguard/vpn_integration/monitoring
   sudo bash weekly-security-audit.sh
   ```

2. **Client Certificate Management**
   ```bash
   # Rotate client certificates quarterly
   sudo bash wireguard/scripts/rotate-client-certs.sh
   ```

3. **Access Monitoring**
   ```bash
   # Review access logs daily
   grep "TRANSACTION_BLOCKED" /var/log/armguard/security-audit.log
   grep "VPN_ACCESS" /var/log/armguard/vpn-access.log
   ```

### **Emergency Procedures**

**Disable VPN Access:**
```bash
sudo systemctl stop wg-quick@wg0
```

**Block Specific Client:**
```bash
sudo wg set wg0 peer [CLIENT_PUBLIC_KEY] remove
```

**Emergency LAN Access Only:**
```bash
cd armguard/vpn_integration
sudo bash emergency-lan-only.sh
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **VPN Connection Fails**
   ```bash
   # Check WireGuard status
   sudo systemctl status wg-quick@wg0
   
   # Check firewall
   sudo ufw status
   
   # Verify port accessibility
   nc -u your-server-ip 51820
   ```

2. **Django VPN Integration Issues**
   ```bash
   # Check VPN middleware
   cd armguard
   python manage.py shell -c "from vpn_integration.core_integration.vpn_utils import test_vpn_detection; test_vpn_detection()"
   ```

3. **Transaction Blocking Not Working**
   ```bash
   # Test transaction endpoint from VPN
   curl -k https://your-server:8443/transactions/create/
   # Should return 403 Forbidden from VPN
   ```

## 📚 **Additional Resources**

### **Documentation Files**
- `IMPLEMENTATION_GUIDE.md` - Comprehensive setup guide
- `SECURITY_POLICY.md` - Security policies and procedures  
- `NETWORK_INTEGRATION_GUIDE.md` - Network integration details
- `DEPLOYMENT_CHECKLIST.md` - Pre-deployment checklist

### **Support Scripts**
- `tools/quick-vpn-setup.sh` - Rapid deployment script
- `monitoring/vpn-monitor.py` - Real-time monitoring
- `tools/client-generator.sh` - Client configuration generator

## ✅ **Deployment Checklist**

- [ ] Choose VPN deployment option (Full/Quick/Hybrid)
- [ ] Run selected installation method
- [ ] Verify network access controls
- [ ] Test transaction blocking from VPN
- [ ] Generate client configurations
- [ ] Set up monitoring and logging
- [ ] Configure backup procedures
- [ ] Document client access procedures
- [ ] Train users on VPN access policies
- [ ] Schedule regular security audits

## 🎯 **Summary**

The unified VPN integration provides:

✅ **Military-grade security compliance**  
✅ **Flexible deployment options**  
✅ **Comprehensive monitoring and audit trails**  
✅ **Easy client management**  
✅ **Automatic security enforcement**  
✅ **Production-ready stability**  

The system maintains the core security requirement of LAN-only transactions while providing secure remote monitoring capabilities through encrypted VPN connections.

---

*For technical support or security compliance questions, refer to the comprehensive documentation in the vpn_integration/ directory.*