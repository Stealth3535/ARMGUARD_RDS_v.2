# ArmGuard Network Security Implementation

## LAN/WAN Hybrid Military Security Architecture

### Overview

ArmGuard has been designed with a military-grade hybrid network security architecture where sensitive operations are restricted to LAN access while status checking operations are available via WAN. This ensures maximum security for critical armory management while providing necessary external access for personnel status verification.

## Security Model

### Core Principles

1. **LAN-Only Operations**: All transaction creation, registration, and administrative functions require direct LAN access
2. **WAN Status Checking**: Personnel can check their transaction status and view reports via WAN connection
3. **Network-Based Access Control**: Security is enforced at the network layer, not just user permissions
4. **Dual-Port Architecture**: Different ports for different network access types

### Network Architecture

```
    ┌─────────────────┐    LAN Port 8443     ┌──────────────────┐
    │   LAN Network   │ ◄──────────────────► │                  │
    │  (192.168.x.x)  │                      │   Raspberry Pi   │
    └─────────────────┘                      │  ArmGuard Server │
                                             │                  │
    ┌─────────────────┐    WAN Port 443      │                  │
    │   WAN Network   │ ◄──────────────────► │                  │
    │   (Internet)    │                      └──────────────────┘
    └─────────────────┘
```

## Implementation Components

### 1. Network Middleware (`core/network_middleware.py`)

#### NetworkBasedAccessMiddleware
- Detects network type based on server port (8443=LAN, 443=WAN)
- Enforces path-based restrictions
- Provides comprehensive security logging

#### UserRoleNetworkMiddleware
- Applies role-based network restrictions
- Enforces session timeouts by network type
- Manages user permissions based on access method

### 2. Network Decorators (`core/network_decorators.py`)

#### @lan_required
- Forces view to require LAN access
- Redirects WAN users with security message
- Applied to sensitive operations

#### @read_only_on_wan
- Allows view access from both networks
- Restricts POST/PUT/DELETE operations on WAN
- Perfect for status checking functions

#### @network_aware_permission_required
- Combines network restrictions with Django permissions
- Provides flexible access control

### 3. Network Context (`core/network_context.py`)

Template context processor that provides:
- `is_lan_access`: Boolean indicating LAN access
- `is_wan_access`: Boolean indicating WAN access
- `network_type`: String ('lan' or 'wan')

### 4. Network Settings (`core/network_settings.py`)

Configuration for:
- Port mappings
- Path restrictions
- Role-based access rules
- Session timeout settings

## Security Implementation by App

### Transactions App
- ✅ **LAN-Only**: QR transaction scanner, transaction creation
- ✅ **WAN Read-Only**: Transaction history, status checking

### Users App
- ✅ **LAN-Only**: User registration (admin only)
- ✅ **WAN Access**: Login, profile viewing

### Personnel App
- ✅ **LAN-Only**: Personnel registration (via admin)
- ✅ **WAN Read-Only**: Personnel profile viewing, search

### Inventory App
- ✅ **LAN-Only**: Item creation, editing, deletion
- ✅ **WAN Read-Only**: Item viewing, inventory reports

### Admin App
- ✅ **LAN-Only**: All administrative functions
- ❌ **WAN Access**: Completely blocked

## Configuration

### Settings.py Network Configuration

```python
# Network-based Security Settings
NETWORK_PORTS = {
    'lan': 8443,  # Secure LAN operations
    'wan': 443,   # WAN status checking
}

LAN_ONLY_PATHS = [
    '/admin/',
    '/transactions/qr-scanner/',
    '/transactions/create/',
    '/inventory/add/',
    '/users/register/',
]

WAN_READ_ONLY_PATHS = [
    '/personnel/',
    '/inventory/',
    '/transactions/history/',
    '/status/',
]

ROLE_NETWORK_RESTRICTIONS = {
    'admin': {'lan': True, 'wan': False},
    'staff': {'lan': True, 'wan': True},
    'user': {'lan': False, 'wan': True},
}

SESSION_TIMEOUT = {
    'lan': 120,  # 2 hours for LAN
    'wan': 30,   # 30 minutes for WAN
}
```

### Middleware Configuration

```python
MIDDLEWARE = [
    # ... standard Django middleware ...
    'core.network_middleware.NetworkBasedAccessMiddleware',
    'core.network_middleware.UserRoleNetworkMiddleware',
]
```

### Template Context Configuration

```python
TEMPLATES = [
    {
        'OPTIONS': {
            'context_processors': [
                # ... standard processors ...
                'core.network_context.network_context',
            ],
        },
    },
]
```

## Deployment Configuration

### Apache/Nginx Configuration

The server must be configured to serve the application on two different ports:

#### Port 8443 (LAN Access)
```apache
<VirtualHost *:8443>
    ServerName armguard.local
    DocumentRoot /var/www/armguard
    
    # LAN-only access
    <RequireAll>
        Require ip 192.168.0.0/16
        Require ip 10.0.0.0/8
        Require ip 172.16.0.0/12
    </RequireAll>
    
    # SSL configuration for secure LAN access
    SSLEngine on
    SSLCertificateFile /path/to/lan-cert.pem
    SSLCertificateKeyFile /path/to/lan-key.pem
</VirtualHost>
```

#### Port 443 (WAN Access)
```apache
<VirtualHost *:443>
    ServerName armguard.example.com
    DocumentRoot /var/www/armguard
    
    # Public SSL certificate
    SSLEngine on
    SSLCertificateFile /path/to/public-cert.pem
    SSLCertificateKeyFile /path/to/public-key.pem
</VirtualHost>
```

### Firewall Rules

```bash
# Allow LAN access on port 8443
ufw allow from 192.168.0.0/16 to any port 8443

# Allow WAN access on port 443
ufw allow 443/tcp

# Block all other access to 8443
ufw deny 8443/tcp
```

## Security Features

### 1. Network Detection
- Automatic detection of access method based on server port
- No reliance on IP addresses which can be spoofed
- Tamper-resistant network type identification

### 2. Path-Based Restrictions
- Sensitive paths completely blocked on WAN
- Read-only enforcement for status checking paths
- Comprehensive path pattern matching

### 3. Role-Based Network Access
- Different network privileges by user role
- Admin users must use LAN for security
- Regular users restricted to WAN access only

### 4. Session Management
- Shorter session timeouts on WAN
- Different security levels by network type
- Automatic session invalidation on network change

### 5. Security Logging
- Comprehensive audit trail of network access attempts
- Security violation logging
- Access pattern monitoring

## Usage Examples

### View Implementation

```python
from core.network_decorators import lan_required, read_only_on_wan

@login_required
@lan_required
def create_transaction(request):
    """Transaction creation - LAN only"""
    # Sensitive operation
    pass

@login_required
@read_only_on_wan
def transaction_history(request):
    """Transaction history - WAN read-only"""
    # Status checking operation
    pass
```

### Template Usage

```html
{% if is_lan_access %}
    <a href="{% url 'transactions:create' %}" class="btn btn-primary">
        Create New Transaction
    </a>
{% else %}
    <div class="alert alert-info">
        Transaction creation requires LAN access
    </div>
{% endif %}

{% if is_wan_access %}
    <small class="text-muted">Read-only access via WAN</small>
{% endif %}
```

## Testing

### Network Security Tests

1. **LAN Access Tests**
   - Verify sensitive operations work on port 8443
   - Confirm admin functions require LAN access
   - Test transaction creation via LAN

2. **WAN Access Tests**
   - Verify status checking works on port 443
   - Confirm sensitive operations are blocked
   - Test read-only functionality

3. **Security Violation Tests**
   - Attempt to access admin functions via WAN
   - Try to create transactions via WAN
   - Verify proper error messages and logging

### Test Commands

```bash
# Test LAN access (should work)
curl -k https://armguard.local:8443/admin/

# Test WAN access to admin (should be blocked)
curl -k https://armguard.example.com:443/admin/

# Test WAN access to status (should work read-only)
curl -k https://armguard.example.com:443/transactions/history/
```

## Monitoring and Logs

### Security Event Monitoring

The system logs all network-based security events:

- LAN/WAN access attempts
- Security violations
- Network type detection
- Access pattern anomalies

### Log Locations

```bash
# Security audit logs
/var/log/armguard/security.log

# Network access logs
/var/log/armguard/network.log

# Django application logs
/var/log/armguard/django.log
```

## Troubleshooting

### Common Issues

1. **Network Type Not Detected**
   - Check server port configuration
   - Verify middleware installation
   - Review network settings in Django

2. **LAN Operations Blocked**
   - Confirm access via port 8443
   - Check LAN IP address ranges
   - Verify SSL certificate configuration

3. **WAN Users Can't Access Status**
   - Verify port 443 accessibility
   - Check firewall rules
   - Confirm read-only paths configuration

### Debugging Commands

```python
# Check network type detection
python manage.py shell
>>> from core.network_middleware import NetworkBasedAccessMiddleware
>>> # Test network detection logic

# Verify middleware configuration
python manage.py check

# Test network decorators
python manage.py test core.tests.test_network_security
```

## Security Compliance

This implementation meets military security requirements by:

✅ **Network Segregation**: Physical separation of sensitive operations  
✅ **Access Control**: Role-based network restrictions  
✅ **Audit Trail**: Comprehensive security logging  
✅ **Defense in Depth**: Multiple layers of security  
✅ **Least Privilege**: Minimum necessary access by network type  
✅ **Fail Secure**: Default deny for sensitive operations  

## Maintenance

### Regular Security Reviews

1. **Monthly**: Review security logs for anomalies
2. **Quarterly**: Update network access patterns
3. **Annually**: Comprehensive security audit
4. **As Needed**: Update restrictions based on threats

### Updates and Patches

- Network security middleware updates
- Certificate renewal procedures
- Firewall rule maintenance
- Security configuration reviews

---

**Classification**: Internal Use  
**Last Updated**: $(date)  
**Version**: 1.0  
**Reviewed By**: System Administrator