# 🔧 VPN Integration Completion Guide
**Complete the VPN integration with the main ArmGuard application**

## 🚀 **Quick Integration (10 minutes)**

### **Step 1: Update Core Settings (5 minutes)**

Add the following to `core/settings.py`:

```python
# Add vpn_integration to INSTALLED_APPS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Security Apps
    'axes',
    # ArmGuard Apps
    'core',
    'admin.apps.AdminConfig',
    'users',
    'personnel',
    'inventory',
    'transactions',
    'qr_manager',
    'print_handler',
    # VPN Integration - ADD THIS
    'vpn_integration',  # ✅ NEW
]

# Update MIDDLEWARE - add VPN integration
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Security Middleware
    'axes.middleware.AxesMiddleware',
    'core.middleware.RateLimitMiddleware',
    'core.middleware.SecurityHeadersMiddleware',
    'core.middleware.StripSensitiveHeadersMiddleware',
    # Network-based Access Control
    'core.network_middleware.NetworkBasedAccessMiddleware',
    'vpn_integration.core_integration.vpn_middleware.VPNAwareNetworkMiddleware',  # ✅ NEW
    'core.network_middleware.UserRoleNetworkMiddleware',
]

# Add VPN configuration settings - ADD THESE
WIREGUARD_ENABLED = config('WIREGUARD_ENABLED', default=False, cast=bool)
WIREGUARD_INTERFACE = config('WIREGUARD_INTERFACE', default='wg0')
WIREGUARD_NETWORK = config('WIREGUARD_NETWORK', default='10.0.0.0/24')
WIREGUARD_PORT = config('WIREGUARD_PORT', default=51820, cast=int)

# VPN Role-based access configuration - ADD THIS
VPN_ROLE_RANGES = {
    'commander': {
        'ip_range': ('10.0.0.10', '10.0.0.19'),
        'access_level': 'VPN_INVENTORY_VIEW',
        'session_timeout': 7200,
        'description': 'Commander remote inventory access'
    },
    'armorer': {
        'ip_range': ('10.0.0.20', '10.0.0.39'),
        'access_level': 'VPN_INVENTORY_VIEW',
        'session_timeout': 3600,
        'description': 'Armorer remote inventory access'
    },
    'emergency': {
        'ip_range': ('10.0.0.40', '10.0.0.49'),
        'access_level': 'VPN_INVENTORY_LIMITED',
        'session_timeout': 1800,
        'description': 'Emergency limited inventory access'
    },
    'personnel': {
        'ip_range': ('10.0.0.50', '10.0.0.199'),
        'access_level': 'VPN_STATUS_ONLY',
        'session_timeout': 900,
        'description': 'Personnel status checking only'
    }
}

# VPN rate limiting - ADD THIS
VPN_RATE_LIMITS = {
    'commander': 100,
    'armorer': 50,
    'emergency': 200,
    'personnel': 30
}

# Update TEMPLATES context processors - ADD VPN CONTEXT
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.network_context.network_context',
                'vpn_integration.core_integration.vpn_context.vpn_context',  # ✅ NEW
            ],
        },
    },
]
```

### **Step 2: Update Environment Variables (2 minutes)**

Add to `.env` file:
```bash
# VPN Integration Settings
WIREGUARD_ENABLED=False
WIREGUARD_INTERFACE=wg0
WIREGUARD_NETWORK=10.0.0.0/24
WIREGUARD_PORT=51820

# VPN Email Alerts (optional)
VPN_EMAIL_ALERTS_ENABLED=False
VPN_ALERT_EMAILS=admin@armguard.local
```

### **Step 3: Create VPN Context Processor (2 minutes)**

Create `vpn_integration/core_integration/vpn_context.py`:
```python
def vpn_context(request):
    """Add VPN context to templates"""
    context = {
        'is_vpn_access': False,
        'vpn_role': None,
        'vpn_client_info': None,
    }
    
    if hasattr(request, 'vpn_client') and request.vpn_client:
        context.update({
            'is_vpn_access': True,
            'vpn_role': request.vpn_client.get('vpn_role'),
            'vpn_client_info': request.vpn_client,
        })
    
    return context
```

### **Step 4: Test Integration (3 minutes)**

```bash
# Check Django configuration
python manage.py check

# Test VPN integration (should work even with VPN disabled)
python manage.py vpn_command --action status

# Run existing tests to ensure compatibility
python manage.py test core.tests
python manage.py test transactions.tests

# Test VPN-specific functionality
python manage.py test vpn_integration.tests
```

## ✅ **Verification Checklist**

After integration, verify these work correctly:

### **LAN Access (Physical Network)**
- [ ] Can access `https://192.168.x.x:8443/transactions/create/`
- [ ] Can scan QR codes for transactions
- [ ] Can add/edit inventory items
- [ ] All admin functions work

### **WAN Access (Read-Only)**
- [ ] Can view `https://192.168.x.x:443/inventory/view/`
- [ ] Can check transaction history
- [ ] Cannot access transaction creation (blocked)
- [ ] Cannot modify inventory (blocked)

### **VPN Integration (When Enabled)**
- [ ] VPN middleware loads without errors
- [ ] Settings and environment variables recognized
- [ ] Django check passes with VPN integration
- [ ] Existing functionality unchanged

## 🔧 **Troubleshooting**

### **Import Errors**
```python
# If you get import errors, ensure the path is correct
# In manage.py or any Django management command:
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'vpn_integration'))
```

### **Middleware Order Issues**
```python
# Ensure network middleware order is correct:
# 1. NetworkBasedAccessMiddleware (base LAN/WAN)
# 2. VPNAwareNetworkMiddleware (VPN extension)  
# 3. UserRoleNetworkMiddleware (user restrictions)
```

### **Template Context Issues**
```python
# If VPN context doesn't work in templates, verify:
# 1. Context processor is in settings TEMPLATES
# 2. VPN context processor file exists
# 3. No circular import issues
```

## 🎯 **Production Deployment**

Once integration testing is complete:

1. **Enable VPN**: Set `WIREGUARD_ENABLED=True` in `.env`
2. **Deploy VPN Server**: Run `setup-wireguard-server.sh` on Raspberry Pi
3. **Create VPN Clients**: Generate client configurations
4. **Test Full Stack**: Verify LAN, WAN, and VPN access patterns
5. **Monitor**: Use VPN monitoring and audit logging

## 📝 **Integration Summary**

**What This Integration Provides:**
- ✅ **Seamless VPN Extension**: Enhances existing security without disruption
- ✅ **Maintained Security**: All current LAN/WAN restrictions preserved
- ✅ **Enhanced Remote Access**: Secure inventory viewing from any location
- ✅ **Zero Downtime**: Integration doesn't affect existing operations
- ✅ **Comprehensive Monitoring**: Full audit trail and security logging

**Result**: ArmGuard gains secure remote capabilities while maintaining all existing security measures and operational procedures.