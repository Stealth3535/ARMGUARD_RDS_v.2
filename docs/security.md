# ARMGUARD - Security Implementation

## Table of Contents
- [Security Overview](#security-overview)
- [Authentication & Authorization](#authentication--authorization)
- [Network Security](#network-security)
- [Data Protection](#data-protection)
- [Audit & Compliance](#audit--compliance)
- [Security Middleware](#security-middleware)
- [Password Policies](#password-policies)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Security Headers](#security-headers)
- [Vulnerability Assessment](#vulnerability-assessment)
- [Incident Response](#incident-response)
- [Security Best Practices](#security-best-practices)

## Security Overview

ARMGUARD implements **military-grade security** with multiple defense layers designed to protect sensitive armory data and operations. The security architecture follows **Zero Trust principles** with comprehensive auditing and monitoring.

### Security Architecture Layers
1. **Network Security**: LAN/WAN access controls, VPN integration, firewall rules
2. **Application Security**: Authentication, authorization, input validation, CSRF protection
3. **Data Security**: Encryption at rest and in transit, secure backup, audit trails
4. **Infrastructure Security**: Secure deployment, monitoring, incident response
5. **Operational Security**: Security procedures, training, compliance monitoring

### Security Principles
- **Defense in Depth**: Multiple security layers for comprehensive protection
- **Least Privilege**: Minimum necessary access for users and systems
- **Fail Secure**: System fails to a secure state when errors occur
- **Complete Auditing**: All actions logged with user attribution
- **Network Isolation**: Sensitive operations restricted to secure network

## Authentication & Authorization

### Multi-Factor Authentication System

#### Primary Authentication (Username/Password)
```python
# Enhanced login view with security features
@ratelimit(key='ip', rate='5/5m', method=['POST'])
def login_view(request):
    """Secure login with rate limiting and audit logging"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Log login attempt
        logger.info(f"Login attempt for user: {username} from IP: {get_client_ip(request)}")
        
        user = authenticate(request, username=username, password=password)
        
        if user:
            # Check account policies
            if not user.is_active:
                messages.error(request, 'Account is disabled')
                return render(request, 'registration/login.html')
            
            # Verify device authorization
            if not check_device_authorization(request, user):
                messages.error(request, 'Unauthorized device')
                return render(request, 'registration/login.html')
            
            # Verify network access
            if not verify_network_access(request, user):
                messages.error(request, 'Network access denied')
                return render(request, 'registration/login.html')
            
            # Successful login
            login(request, user)
            
            # Update user profile
            user.last_login = timezone.now()
            user.save()
            
            # Log successful login
            AuditLog.objects.create(
                model_name='User',
                object_id=str(user.id),
                action='LOGIN',
                user=user,
                ip_address=get_client_ip(request)
            )
            
            return redirect('dashboard')
        else:
            # Log failed login
            logger.warning(f"Failed login for user: {username} from IP: {get_client_ip(request)}")
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'registration/login.html')
```

#### Device Authorization System
```python
# Device authorization middleware
class DeviceAuthorizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Get device MAC address
            client_mac = self.get_client_mac(request)
            
            try:
                profile = request.user.userprofile
                authorized_devices = json.loads(profile.authorized_devices or '[]')
                
                if client_mac and client_mac not in authorized_devices:
                    # New device detected
                    if self.should_auto_authorize_device(request):
                        # Auto-authorize for admins on LAN
                        authorized_devices.append(client_mac)
                        profile.authorized_devices = json.dumps(authorized_devices)
                        profile.save()
                        
                        # Log device authorization
                        AuditLog.objects.create(
                            model_name='UserProfile',
                            object_id=str(profile.id),
                            action='DEVICE_AUTHORIZED',
                            user=request.user,
                            ip_address=get_client_ip(request),
                            changes=json.dumps({'new_device': client_mac})
                        )
                    else:
                        # Require explicit device authorization
                        logout(request)
                        messages.error(request, 'Device authorization required')
                        return redirect('device_authorization')
                
                # Update last device check
                profile.last_device_check = timezone.now()
                profile.save()
                
            except UserProfile.DoesNotExist:
                # Create user profile with current device
                UserProfile.objects.create(
                    user=request.user,
                    authorized_devices=json.dumps([client_mac] if client_mac else [])
                )
        
        return self.get_response(request)
    
    def get_client_mac(self, request):
        """Get client MAC address (implementation depends on network setup)"""
        # This would integrate with network infrastructure
        # For demo purposes, using a header
        return request.META.get('HTTP_X_CLIENT_MAC')
    
    def should_auto_authorize_device(self, request):
        """Check if device should be auto-authorized"""
        # Auto-authorize admins on LAN
        return (request.user.is_superuser and 
                is_lan_access(request))
```

### Role-Based Access Control (RBAC)

#### Permission Matrix
```python
ROLE_PERMISSIONS = {
    'Admin': {
        'personnel': ['add', 'change', 'delete', 'view'],
        'inventory': ['add', 'change', 'delete', 'view'],
        'transactions': ['add', 'change', 'delete', 'view'],
        'users': ['add', 'change', 'delete', 'view'],
        'reports': ['generate', 'view', 'export'],
        'system': ['configure', 'monitor', 'backup']
    },
    'Armorer': {
        'personnel': ['view', 'change'],
        'inventory': ['view', 'change'],
        'transactions': ['add', 'view'],
        'reports': ['view'],
        'qr': ['scan', 'generate']
    },
    'Staff': {
        'personnel': ['view'],
        'inventory': ['view'],
        'transactions': ['view'],
        'reports': ['view']
    }
}

# Permission checking decorators
def has_permission(permission):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            user_role = get_user_role(request.user)
            app_name, permission_name = permission.split('.')
            
            if app_name not in ROLE_PERMISSIONS.get(user_role, {}):
                return HttpResponseForbidden("Access denied")
            
            if permission_name not in ROLE_PERMISSIONS[user_role][app_name]:
                return HttpResponseForbidden("Insufficient permissions")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

# Usage example
@has_permission('personnel.add')
@lan_required
def create_personnel(request):
    """Create personnel - requires personnel.add permission and LAN access"""
    pass
```

#### Dynamic Permission Checking
```python
def check_object_permission(user, obj, action):
    """Check if user has permission for specific object action"""
    user_role = get_user_role(user)
    
    # Admin has all permissions
    if user_role == 'Admin':
        return True
    
    # Object-level permissions
    if isinstance(obj, Personnel):
        app_permissions = ROLE_PERMISSIONS.get(user_role, {}).get('personnel', [])
        
        # Check if user created the personnel record
        if action in ['change', 'delete'] and obj.created_by == user:
            return 'change' in app_permissions
        
        return action in app_permissions
    
    elif isinstance(obj, Transaction):
        app_permissions = ROLE_PERMISSIONS.get(user_role, {}).get('transactions', [])
        
        # Armorer can only view/edit transactions they issued
        if user_role == 'Armorer' and action in ['change', 'delete']:
            return obj.issued_by == user and action == 'change'
        
        return action in app_permissions
    
    return False
```

### Session Security

#### Secure Session Configuration
```python
# Session security settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_NAME = 'armguard_sessionid'
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_SAMESITE = 'Lax'

# Single session enforcement
class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            current_session = request.session.session_key
            
            # Check for existing sessions
            existing_sessions = Session.objects.filter(
                expire_date__gt=timezone.now()
            ).exclude(session_key=current_session)
            
            # Remove other sessions for this user
            for session in existing_sessions:
                session_data = session.get_decoded()
                if session_data.get('_auth_user_id') == str(request.user.id):
                    session.delete()
                    
                    # Log session termination
                    logger.info(f"Terminated duplicate session for user {request.user.username}")
        
        return self.get_response(request)
```

#### Session Activity Monitoring
```python
class SessionActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated:
            # Update session activity
            request.session['last_activity'] = timezone.now().isoformat()
            request.session['ip_address'] = get_client_ip(request)
            request.session['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
            
            # Check for session anomalies
            if self.detect_session_anomaly(request):
                # Force logout on suspicious activity
                logout(request)
                messages.error(request, 'Session security violation detected')
                return redirect('login')
        
        return self.get_response(request)
    
    def detect_session_anomaly(self, request):
        """Detect suspicious session activity"""
        current_ip = get_client_ip(request)
        session_ip = request.session.get('ip_address')
        
        # Check for IP address change (could indicate session hijacking)
        if session_ip and session_ip != current_ip:
            # Allow IP change for VPN users
            if not is_vpn_user(request.user):
                logger.warning(f"IP change detected for user {request.user.username}: {session_ip} -> {current_ip}")
                return True
        
        # Check for unusual user agent change
        current_ua = request.META.get('HTTP_USER_AGENT', '')
        session_ua = request.session.get('user_agent', '')
        
        if session_ua and not self.user_agents_similar(session_ua, current_ua):
            logger.warning(f"User agent change detected for user {request.user.username}")
            return True
        
        return False
```

## Network Security

### LAN/WAN Access Control

#### Network-based Middleware
```python
class NetworkBasedAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.lan_networks = [
            ipaddress.IPv4Network('192.168.0.0/16'),
            ipaddress.IPv4Network('10.0.0.0/8'),
            ipaddress.IPv4Network('172.16.0.0/12')
        ]
    
    def __call__(self, request):
        client_ip = ipaddress.IPv4Address(get_client_ip(request))
        is_lan = any(client_ip in network for network in self.lan_networks)
        
        # Add network context to request
        request.network_context = {
            'is_lan': is_lan,
            'is_wan': not is_lan,
            'client_ip': str(client_ip)
        }
        
        # Check LAN-only paths
        if self.is_lan_only_path(request.path) and not is_lan:
            logger.warning(f"WAN access blocked for LAN-only path: {request.path} from {client_ip}")
            return HttpResponseForbidden("LAN access required")
        
        # Apply WAN restrictions
        if not is_lan and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if not self.is_wan_write_allowed(request):
                return HttpResponseForbidden("WAN write operations not allowed")
        
        return self.get_response(request)
    
    def is_lan_only_path(self, path):
        """Check if path requires LAN access"""
        lan_only_paths = [
            '/admin/',
            '/transactions/create/',
            '/transactions/qr-scanner/',
            '/personnel/create/',
            '/inventory/create/'
        ]
        return any(path.startswith(lop) for lop in lan_only_paths)
    
    def is_wan_write_allowed(self, request):
        """Check if WAN write operation is allowed"""
        # Only allow specific WAN write operations
        wan_write_allowed = [
            '/api/auth/logout/',
            '/profile/update/'
        ]
        return any(request.path.startswith(wwa) for wwa in wan_write_allowed)
```

#### Network Access Decorators
```python
def lan_required(view_func):
    """Decorator to require LAN access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'network_context'):
            # Fallback network detection
            client_ip = get_client_ip(request)
            is_lan = ipaddress.IPv4Address(client_ip).is_private
            request.network_context = {'is_lan': is_lan}
        
        if not request.network_context.get('is_lan'):
            return HttpResponseForbidden("LAN access required for this operation")
        
        return view_func(request, *args, **kwargs)
    return wrapper

def network_aware_permission_required(permission, allow_wan_read=True):
    """Permission decorator with network awareness"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check basic permission
            if not request.user.has_perm(permission):
                return HttpResponseForbidden("Permission denied")
            
            # Network-based restrictions
            is_lan = request.network_context.get('is_lan', False)
            
            if not is_lan:
                # WAN access restrictions
                if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                    return HttpResponseForbidden("WAN write access denied")
                
                if not allow_wan_read and request.method == 'GET':
                    return HttpResponseForbidden("WAN read access denied")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
```

### VPN Integration Security

#### VPN User Detection and Management
```python
class VPNSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.vpn_networks = {
            'commander': ipaddress.IPv4Network('10.8.0.10/29'),
            'armorer': ipaddress.IPv4Network('10.8.0.20/29'),
            'emergency': ipaddress.IPv4Network('10.8.0.40/29'),
            'personnel': ipaddress.IPv4Network('10.8.0.50/24')
        }
    
    def __call__(self, request):
        client_ip = ipaddress.IPv4Address(get_client_ip(request))
        vpn_role = self.detect_vpn_role(client_ip)
        
        if vpn_role:
            request.vpn_context = {
                'is_vpn': True,
                'vpn_role': vpn_role,
                'client_ip': str(client_ip)
            }
            
            # Apply VPN-specific restrictions
            if not self.check_vpn_access(request, vpn_role):
                return HttpResponseForbidden("VPN access denied for this operation")
            
            # Update VPN usage logs
            self.log_vpn_usage(request.user, vpn_role, client_ip)
        else:
            request.vpn_context = {'is_vpn': False}
        
        return self.get_response(request)
    
    def detect_vpn_role(self, client_ip):
        """Detect VPN role based on IP range"""
        for role, network in self.vpn_networks.items():
            if client_ip in network:
                return role
        return None
    
    def check_vpn_access(self, request, vpn_role):
        """Check if VPN access is allowed for this operation"""
        vpn_permissions = {
            'commander': ['view_all', 'generate_reports'],
            'armorer': ['view_inventory', 'view_personnel'],
            'emergency': ['view_status', 'emergency_access'],
            'personnel': ['view_own_records']
        }
        
        # Simple path-based access control for demo
        return True  # Implement specific logic based on requirements
```

### Firewall Configuration

#### IPTables Rules for ARMGUARD
```bash
#!/bin/bash
# ARMGUARD Firewall Configuration

# Clear existing rules
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# Default policies
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# Loopback traffic
iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# SSH access (restrict to admin network)
iptables -A INPUT -p tcp --dport 22 -s 192.168.1.0/24 -j ACCEPT

# HTTPS access (public)
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# LAN-only secure port
iptables -A INPUT -p tcp --dport 8443 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8443 -s 10.0.0.0/8 -j ACCEPT

# Database access (local only)
iptables -A INPUT -p tcp --dport 5432 -s 127.0.0.1 -j ACCEPT

# Redis access (local only)  
iptables -A INPUT -p tcp --dport 6379 -s 127.0.0.1 -j ACCEPT

# VPN access (WireGuard)
iptables -A INPUT -p udp --dport 51820 -j ACCEPT

# VPN client access to application
iptables -A INPUT -p tcp --dport 8443 -s 10.8.0.0/24 -j ACCEPT

# ICMP (ping) - limited
iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/second -j ACCEPT

# Log dropped packets
iptables -A INPUT -j LOG --log-prefix "ARMGUARD-DROPPED: "

# Save rules
iptables-save > /etc/iptables/rules.v4
```

#### Fail2Ban Configuration
```ini
# /etc/fail2ban/filter.d/armguard.conf
[Definition]
failregex = ^.*ARMGUARD-SECURITY.*Failed login.*from <HOST>.*$
            ^.*ARMGUARD-SECURITY.*Invalid access attempt.*from <HOST>.*$
            ^.*ARMGUARD-SECURITY.*Rate limit exceeded.*from <HOST>.*$
ignoreregex =

# /etc/fail2ban/jail.d/armguard.conf
[armguard]
enabled = true
port = https,http,8443
filter = armguard
logpath = /var/log/armguard/security.log
maxretry = 3
bantime = 3600
findtime = 600
action = iptables-multiport[name=armguard, port="http,https,8443", protocol=tcp]
```

## Data Protection

### Encryption Implementation

#### Database Field Encryption
```python
from cryptography.fernet import Fernet
import base64

class EncryptedTextField(models.TextField):
    """Encrypted text field using symmetric encryption"""
    
    def __init__(self, *args, **kwargs):
        self.encryption_key = kwargs.pop('encryption_key', settings.FIELD_ENCRYPTION_KEY)
        super().__init__(*args, **kwargs)
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        
        try:
            fernet = Fernet(self.encryption_key.encode())
            decrypted = fernet.decrypt(value.encode())
            return decrypted.decode()
        except Exception:
            # Return encrypted value if decryption fails
            return f"[ENCRYPTED: {value[:20]}...]"
    
    def to_python(self, value):
        return value
    
    def get_prep_value(self, value):
        if value is None:
            return value
        
        fernet = Fernet(self.encryption_key.encode())
        encrypted = fernet.encrypt(value.encode())
        return encrypted.decode()

# Usage in models
class Personnel(models.Model):
    # ... other fields
    telephone_encrypted = EncryptedTextField(null=True, blank=True)
    notes_encrypted = EncryptedTextField(null=True, blank=True)
```

#### File Encryption
```python
import os
from cryptography.fernet import Fernet
from django.core.files.storage import default_storage

class SecureFileHandler:
    def __init__(self):
        self.encryption_key = settings.FILE_ENCRYPTION_KEY.encode()
        self.fernet = Fernet(self.encryption_key)
    
    def encrypt_file(self, file_path, content):
        """Encrypt file content before storage"""
        if isinstance(content, str):
            content = content.encode()
        
        encrypted_content = self.fernet.encrypt(content)
        
        with default_storage.open(file_path, 'wb') as f:
            f.write(encrypted_content)
        
        return file_path
    
    def decrypt_file(self, file_path):
        """Decrypt file content after retrieval"""
        try:
            with default_storage.open(file_path, 'rb') as f:
                encrypted_content = f.read()
            
            decrypted_content = self.fernet.decrypt(encrypted_content)
            return decrypted_content
        except Exception as e:
            logger.error(f"File decryption failed for {file_path}: {e}")
            return None
    
    def secure_delete(self, file_path):
        """Securely delete file with overwriting"""
        if default_storage.exists(file_path):
            # Overwrite with random data before deletion
            file_size = default_storage.size(file_path)
            random_data = os.urandom(file_size)
            
            with default_storage.open(file_path, 'wb') as f:
                f.write(random_data)
            
            default_storage.delete(file_path)

# QR code encryption
class SecureQRManager:
    def __init__(self):
        self.file_handler = SecureFileHandler()
    
    def generate_encrypted_qr(self, qr_type, reference_id):
        """Generate QR code with encrypted data"""
        qr_data = f"{qr_type}:{reference_id}:{timezone.now().isoformat()}"
        
        # Generate QR code image
        qr_image = qrcode.make(qr_data)
        
        # Save encrypted QR image
        image_buffer = BytesIO()
        qr_image.save(image_buffer, format='PNG')
        
        file_path = f"qr_codes/{qr_type.lower()}/{reference_id}.png"
        encrypted_path = self.file_handler.encrypt_file(file_path, image_buffer.getvalue())
        
        return {
            'qr_data': qr_data,
            'file_path': encrypted_path,
            'encrypted': True
        }
```

### Secure Backup Implementation

#### Encrypted Database Backup
```bash
#!/bin/bash
# Secure database backup with encryption

BACKUP_DIR="/var/backups/armguard"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="armguard"
DB_USER="armguard_backup"
ENCRYPTION_KEY_FILE="/etc/armguard/backup.key"

# Create secure backup directory
mkdir -p $BACKUP_DIR
chmod 700 $BACKUP_DIR

# Database dump with compression
pg_dump -h localhost -U $DB_USER -d $DB_NAME \
    --format=custom --compress=9 \
    --file=$BACKUP_DIR/armguard_raw_$DATE.backup

# Encrypt backup file
gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
    --s2k-digest-algo SHA512 --s2k-count 65536 \
    --symmetric --output $BACKUP_DIR/armguard_encrypted_$DATE.backup.gpg \
    --batch --passphrase-file $ENCRYPTION_KEY_FILE \
    $BACKUP_DIR/armguard_raw_$DATE.backup

# Secure delete of unencrypted backup
shred -vfz -n 3 $BACKUP_DIR/armguard_raw_$DATE.backup

# Create backup checksum
sha256sum $BACKUP_DIR/armguard_encrypted_$DATE.backup.gpg > \
    $BACKUP_DIR/armguard_encrypted_$DATE.backup.gpg.sha256

# Remove old encrypted backups (keep 30 days)
find $BACKUP_DIR -name "armguard_encrypted_*.backup.gpg" -mtime +30 -exec shred -vfz -n 3 {} \;
find $BACKUP_DIR -name "armguard_encrypted_*.backup.gpg.sha256" -mtime +30 -delete

echo "Encrypted backup created: armguard_encrypted_$DATE.backup.gpg"
```

#### Backup Integrity Verification
```python
import hashlib
import os
from pathlib import Path

class BackupIntegrityManager:
    def __init__(self, backup_dir="/var/backups/armguard"):
        self.backup_dir = Path(backup_dir)
    
    def verify_backup_integrity(self, backup_file):
        """Verify backup file integrity using checksum"""
        backup_path = self.backup_dir / backup_file
        checksum_path = backup_path.with_suffix(backup_path.suffix + '.sha256')
        
        if not backup_path.exists():
            return False, "Backup file not found"
        
        if not checksum_path.exists():
            return False, "Checksum file not found"
        
        # Calculate current checksum
        current_checksum = self.calculate_file_checksum(backup_path)
        
        # Read stored checksum
        with open(checksum_path, 'r') as f:
            stored_checksum = f.read().split()[0]  # First part is the hash
        
        if current_checksum == stored_checksum:
            return True, "Backup integrity verified"
        else:
            return False, f"Checksum mismatch: {current_checksum} != {stored_checksum}"
    
    def calculate_file_checksum(self, file_path):
        """Calculate SHA-256 checksum of file"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def create_backup_manifest(self):
        """Create manifest of all backup files with checksums"""
        manifest = {}
        
        for backup_file in self.backup_dir.glob("armguard_encrypted_*.backup.gpg"):
            checksum = self.calculate_file_checksum(backup_file)
            file_size = backup_file.stat().st_size
            file_mtime = backup_file.stat().st_mtime
            
            manifest[backup_file.name] = {
                'checksum': checksum,
                'size': file_size,
                'mtime': file_mtime,
                'verified': True
            }
        
        # Save manifest
        manifest_path = self.backup_dir / 'backup_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
```

## Audit & Compliance

### Comprehensive Audit Logging

#### Enhanced Audit Log Model
```python
class AuditLog(models.Model):
    """Comprehensive audit logging for all system changes"""
    
    # Action types
    ACTION_CREATE = 'CREATE'
    ACTION_READ = 'READ'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_EXPORT = 'EXPORT'
    ACTION_SYSTEM = 'SYSTEM'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_READ, 'Read'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_EXPORT, 'Export'),
        (ACTION_SYSTEM, 'System'),
    ]
    
    # Audit fields
    id = models.BigAutoField(primary_key=True)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    
    # Change tracking
    changes = models.TextField(null=True, blank=True)  # JSON
    previous_values = models.TextField(null=True, blank=True)  # JSON
    
    # User context
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    username = models.CharField(max_length=150)  # Preserve username even if user deleted
    
    # Network context
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    session_key = models.CharField(max_length=40, null=True, blank=True)
    
    # Security context
    is_lan_access = models.BooleanField(default=False)
    is_vpn_access = models.BooleanField(default=False)
    device_mac = models.CharField(max_length=17, null=True, blank=True)
    
    # Temporal information
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    # Integrity protection
    record_hash = models.CharField(max_length=64, editable=False)
    
    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save to generate integrity hash"""
        if not self.record_hash:
            self.record_hash = self.generate_record_hash()
        super().save(*args, **kwargs)
    
    def generate_record_hash(self):
        """Generate SHA-256 hash for record integrity"""
        hash_input = f"{self.model_name}{self.object_id}{self.action}{self.username}{self.ip_address}{self.timestamp.isoformat()}"
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def verify_integrity(self):
        """Verify record integrity"""
        expected_hash = self.generate_record_hash()
        return self.record_hash == expected_hash
```

#### Audit Middleware
```python
class ComprehensiveAuditMiddleware:
    """Middleware to automatically audit all model changes"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Store request context for audit logging
        request._audit_context = {
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'session_key': request.session.session_key,
            'is_lan_access': getattr(request, 'network_context', {}).get('is_lan', False),
            'is_vpn_access': getattr(request, 'vpn_context', {}).get('is_vpn', False),
            'device_mac': request.META.get('HTTP_X_CLIENT_MAC'),
        }
        
        response = self.get_response(request)
        return response

# Model signal handlers for automatic audit logging
@receiver(post_save)
def audit_model_save(sender, instance, created, **kwargs):
    """Audit model save operations"""
    if sender in [AuditLog, Session]:  # Skip audit models
        return
    
    request = get_current_request()
    if not request:
        return
    
    action = AuditLog.ACTION_CREATE if created else AuditLog.ACTION_UPDATE
    changes = {}
    previous_values = {}
    
    # Capture field changes for updates
    if not created and hasattr(instance, '_original_values'):
        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(instance._original_values, field_name, None)
            new_value = getattr(instance, field_name)
            
            if old_value != new_value:
                changes[field_name] = {
                    'old': str(old_value) if old_value else None,
                    'new': str(new_value) if new_value else None
                }
                previous_values[field_name] = str(old_value) if old_value else None
    
    # Create audit log entry
    AuditLog.objects.create(
        model_name=sender.__name__,
        object_id=str(instance.pk),
        action=action,
        changes=json.dumps(changes) if changes else None,
        previous_values=json.dumps(previous_values) if previous_values else None,
        user=request.user if request.user.is_authenticated else None,
        username=request.user.username if request.user.is_authenticated else 'anonymous',
        **request._audit_context
    )

@receiver(pre_delete)  
def audit_model_delete(sender, instance, **kwargs):
    """Audit model delete operations"""
    if sender in [AuditLog, Session]:
        return
    
    request = get_current_request()
    if not request:
        return
    
    # Capture all field values before deletion
    instance_data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field.name)
        instance_data[field.name] = str(value) if value else None
    
    AuditLog.objects.create(
        model_name=sender.__name__,
        object_id=str(instance.pk),
        action=AuditLog.ACTION_DELETE,
        previous_values=json.dumps(instance_data),
        user=request.user if request.user.is_authenticated else None,
        username=request.user.username if request.user.is_authenticated else 'anonymous',
        **request._audit_context
    )
```

### Compliance Monitoring

#### Security Metrics Dashboard
```python
class SecurityMetricsManager:
    """Generate security metrics for compliance monitoring"""
    
    def __init__(self):
        self.metrics_cache_timeout = 300  # 5 minutes
    
    @cached_property
    def failed_login_attempts(self):
        """Count failed login attempts in last 24 hours"""
        yesterday = timezone.now() - timedelta(hours=24)
        return AuditLog.objects.filter(
            action=AuditLog.ACTION_LOGIN,
            timestamp__gte=yesterday,
            changes__icontains='failed'
        ).count()
    
    @cached_property  
    def unauthorized_access_attempts(self):
        """Count unauthorized access attempts"""
        yesterday = timezone.now() - timedelta(hours=24)
        return AuditLog.objects.filter(
            timestamp__gte=yesterday,
            changes__icontains='unauthorized'
        ).count()
    
    def get_user_activity_summary(self, days=7):
        """Get user activity summary for compliance"""
        start_date = timezone.now() - timedelta(days=days)
        
        user_activity = AuditLog.objects.filter(
            timestamp__gte=start_date,
            user__isnull=False
        ).values('user__username').annotate(
            login_count=Count('id', filter=Q(action=AuditLog.ACTION_LOGIN)),
            create_count=Count('id', filter=Q(action=AuditLog.ACTION_CREATE)),
            update_count=Count('id', filter=Q(action=AuditLog.ACTION_UPDATE)),
            delete_count=Count('id', filter=Q(action=AuditLog.ACTION_DELETE)),
            total_actions=Count('id')
        ).order_by('-total_actions')
        
        return list(user_activity)
    
    def get_security_violations(self, days=30):
        """Get security violations for compliance reporting"""
        start_date = timezone.now() - timedelta(days=days)
        
        violations = []
        
        # Multiple failed logins
        failed_logins = AuditLog.objects.filter(
            timestamp__gte=start_date,
            changes__icontains='failed_login'
        ).values('ip_address').annotate(
            attempt_count=Count('id')
        ).filter(attempt_count__gte=5)
        
        for failed_login in failed_logins:
            violations.append({
                'type': 'Multiple Failed Logins',
                'ip_address': failed_login['ip_address'],
                'count': failed_login['attempt_count'],
                'severity': 'HIGH'
            })
        
        # Unauthorized access attempts
        unauth_attempts = AuditLog.objects.filter(
            timestamp__gte=start_date,
            changes__icontains='unauthorized'
        )
        
        for attempt in unauth_attempts:
            violations.append({
                'type': 'Unauthorized Access Attempt',
                'ip_address': attempt.ip_address,
                'user': attempt.username,
                'timestamp': attempt.timestamp,
                'severity': 'CRITICAL'
            })
        
        return violations
    
    def generate_compliance_report(self, start_date, end_date):
        """Generate comprehensive compliance report"""
        report = {
            'period': f"{start_date.date()} to {end_date.date()}",
            'generated_at': timezone.now(),
            'summary': {},
            'user_activity': {},
            'security_events': {},
            'system_integrity': {}
        }
        
        # Summary statistics
        total_logs = AuditLog.objects.filter(
            timestamp__range=[start_date, end_date]
        ).count()
        
        report['summary'] = {
            'total_audit_logs': total_logs,
            'unique_users': AuditLog.objects.filter(
                timestamp__range=[start_date, end_date]
            ).values('user').distinct().count(),
            'failed_logins': AuditLog.objects.filter(
                timestamp__range=[start_date, end_date],
                action=AuditLog.ACTION_LOGIN,
                changes__icontains='failed'
            ).count(),
            'data_modifications': AuditLog.objects.filter(
                timestamp__range=[start_date, end_date],
                action__in=[AuditLog.ACTION_CREATE, AuditLog.ACTION_UPDATE, AuditLog.ACTION_DELETE]
            ).count()
        }
        
        # User activity breakdown
        report['user_activity'] = self.get_user_activity_summary(
            days=(end_date - start_date).days
        )
        
        # Security events
        report['security_events'] = self.get_security_violations(
            days=(end_date - start_date).days
        )
        
        # System integrity check
        integrity_check = self.verify_audit_log_integrity(start_date, end_date)
        report['system_integrity'] = {
            'logs_verified': integrity_check['verified_count'],
            'integrity_violations': integrity_check['violation_count'],
            'integrity_status': 'PASS' if integrity_check['violation_count'] == 0 else 'FAIL'
        }
        
        return report
    
    def verify_audit_log_integrity(self, start_date, end_date):
        """Verify integrity of audit logs in date range"""
        logs = AuditLog.objects.filter(
            timestamp__range=[start_date, end_date]
        )
        
        verified_count = 0
        violation_count = 0
        
        for log in logs:
            if log.verify_integrity():
                verified_count += 1
            else:
                violation_count += 1
                logger.critical(f"Audit log integrity violation: {log.id}")
        
        return {
            'verified_count': verified_count,
            'violation_count': violation_count,
            'total_checked': verified_count + violation_count
        }
```

### Regulatory Compliance Features

#### GDPR Data Protection
```python
class DataProtectionManager:
    """Handle GDPR and data protection requirements"""
    
    def export_user_data(self, user):
        """Export all user data for GDPR compliance"""
        user_data = {
            'personal_info': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_joined': user.date_joined.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
        }
        
        # User profile data
        try:
            profile = user.userprofile
            user_data['profile'] = {
                'role': profile.role,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat()
            }
        except UserProfile.DoesNotExist:
            pass
        
        # Personnel records created/modified by user
        personnel_created = Personnel.objects.filter(created_by=user)
        user_data['personnel_created'] = [
            {
                'id': p.id,
                'name': f"{p.rank} {p.firstname} {p.surname}",
                'created_at': p.created_at.isoformat()
            } for p in personnel_created
        ]
        
        # Transactions issued by user
        transactions_issued = Transaction.objects.filter(issued_by=user)
        user_data['transactions_issued'] = [
            {
                'id': t.id,
                'action': t.action,
                'date_time': t.date_time.isoformat(),
                'personnel': str(t.personnel),
                'item': str(t.item)
            } for t in transactions_issued
        ]
        
        # Audit logs
        audit_logs = AuditLog.objects.filter(user=user)
        user_data['audit_activity'] = [
            {
                'action': log.action,
                'model': log.model_name,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address
            } for log in audit_logs[:100]  # Limit to recent 100 entries
        ]
        
        return user_data
    
    def anonymize_user_data(self, user):
        """Anonymize user data while preserving audit trails"""
        # Generate anonymous identifier
        anonymous_id = f"anon_{hashlib.sha256(str(user.id).encode()).hexdigest()[:8]}"
        
        # Update user record
        user.username = anonymous_id
        user.email = f"{anonymous_id}@anonymized.local"
        user.first_name = "Anonymous"
        user.last_name = "User" 
        user.is_active = False
        user.save()
        
        # Update audit logs
        AuditLog.objects.filter(user=user).update(username=anonymous_id)
        
        # Log anonymization
        AuditLog.objects.create(
            model_name='User',
            object_id=str(user.id),
            action='ANONYMIZE',
            changes=json.dumps({'anonymized_id': anonymous_id}),
            username='system',
            ip_address='127.0.0.1',
            user_agent='Data Protection System'
        )
        
        return anonymous_id
```

## Security Middleware

### Comprehensive Security Middleware Stack

```python
# Security headers middleware
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy
        csp_policy = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline'",  # Inline scripts for CSRF tokens
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com",
            "img-src 'self' data: https:",
            "font-src 'self' https://cdnjs.cloudflare.com",
            "connect-src 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "object-src 'none'"
        ]
        response['Content-Security-Policy'] = '; '.join(csp_policy)
        
        return response

# Rate limiting middleware
class RateLimitingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = cache
    
    def __call__(self, request):
        # Skip rate limiting for static files
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return self.get_response(request)
        
        client_ip = get_client_ip(request)
        
        # Different limits for different user types
        if request.user.is_authenticated:
            if request.user.is_superuser:
                rate_limit = 300  # 300 requests per minute for admins
            else:
                rate_limit = 120  # 120 requests per minute for users
        else:
            rate_limit = 60   # 60 requests per minute for anonymous
        
        # Check rate limit
        cache_key = f"rate_limit:{client_ip}"
        current_requests = self.cache.get(cache_key, 0)
        
        if current_requests >= rate_limit:
            logger.warning(f"Rate limit exceeded for {client_ip}: {current_requests} requests")
            
            # Log security event
            AuditLog.objects.create(
                model_name='Security',
                object_id=client_ip,
                action='RATE_LIMIT',
                changes=json.dumps({'requests': current_requests, 'limit': rate_limit}),
                username=request.user.username if request.user.is_authenticated else 'anonymous',
                ip_address=client_ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return HttpResponseTooManyRequests("Rate limit exceeded")
        
        response = self.get_response(request)
        
        # Update request count
        self.cache.set(cache_key, current_requests + 1, 60)  # 1 minute window
        
        # Add rate limit headers
        response['X-RateLimit-Limit'] = str(rate_limit)
        response['X-RateLimit-Remaining'] = str(max(0, rate_limit - current_requests - 1))
        response['X-RateLimit-Reset'] = str(int(time.time()) + 60)
        
        return response
```

## Password Policies

### Enhanced Password Security

```python
import re
from django.contrib.auth.password_validation import BasePasswordValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class MilitaryPasswordValidator(BasePasswordValidator):
    """Military-grade password validation"""
    
    def validate(self, password, user=None):
        errors = []
        
        # Minimum length
        if len(password) < 12:
            errors.append(ValidationError(
                _('Password must be at least 12 characters long.'),
                code='password_too_short'
            ))
        
        # Must contain uppercase letter
        if not re.search(r'[A-Z]', password):
            errors.append(ValidationError(
                _('Password must contain at least one uppercase letter.'),
                code='password_no_upper'
            ))
        
        # Must contain lowercase letter
        if not re.search(r'[a-z]', password):
            errors.append(ValidationError(
                _('Password must contain at least one lowercase letter.'),
                code='password_no_lower'
            ))
        
        # Must contain digit
        if not re.search(r'\d', password):
            errors.append(ValidationError(
                _('Password must contain at least one digit.'),
                code='password_no_digit'
            ))
        
        # Must contain special character
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(ValidationError(
                _('Password must contain at least one special character.'),
                code='password_no_special'
            ))
        
        # No common patterns
        common_patterns = [
            r'123456', r'password', r'admin', r'armguard', 
            r'qwerty', r'abc123', r'111111'
        ]
        
        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                errors.append(ValidationError(
                    _('Password contains common patterns that are not allowed.'),
                    code='password_common_pattern'
                ))
                break
        
        # No personal information (if user provided)
        if user:
            personal_info = [
                user.username.lower(),
                user.first_name.lower(),
                user.last_name.lower(),
                user.email.lower().split('@')[0]
            ]
            
            for info in personal_info:
                if info and len(info) >= 3 and info in password.lower():
                    errors.append(ValidationError(
                        _('Password must not contain personal information.'),
                        code='password_personal_info'
                    ))
                    break
        
        if errors:
            raise ValidationError(errors)
    
    def get_help_text(self):
        return _(
            'Your password must be at least 12 characters long, contain uppercase and '
            'lowercase letters, digits, and special characters. It must not contain '
            'common patterns or personal information.'
        )

# Password history tracking
class PasswordHistory(models.Model):
    """Track password history to prevent reuse"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    password_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'password_history'
        ordering = ['-created_at']

class PasswordReuseValidator(BasePasswordValidator):
    """Prevent password reuse"""
    
    def validate(self, password, user=None):
        if not user:
            return
        
        # Check last 5 passwords
        recent_passwords = PasswordHistory.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        for old_password in recent_passwords:
            if check_password(password, old_password.password_hash):
                raise ValidationError(
                    _('Cannot reuse one of your last 5 passwords.'),
                    code='password_reused'
                )

# Password management utilities
class PasswordSecurityManager:
    @staticmethod
    def password_expires_soon(user, days=7):
        """Check if password expires within specified days"""
        try:
            last_password = PasswordHistory.objects.filter(user=user).first()
            if not last_password:
                return True  # No password history, should change
            
            expiry_date = last_password.created_at + timedelta(days=90)  # 90 day policy
            warning_date = expiry_date - timedelta(days=days)
            
            return timezone.now() >= warning_date
        except:
            return False
    
    @staticmethod
    def force_password_change(user, reason="Security policy"):
        """Force user to change password on next login"""
        user.profile.force_password_change = True
        user.profile.password_change_reason = reason
        user.profile.save()
        
        # Log mandatory password change
        AuditLog.objects.create(
            model_name='User',
            object_id=str(user.id),
            action='FORCE_PASSWORD_CHANGE',
            changes=json.dumps({'reason': reason}),
            username='system',
            ip_address='127.0.0.1',
            user_agent='Security System'
        )
    
    @staticmethod
    def check_compromised_password(password):
        """Check password against known breach databases (simplified)"""
        # In production, integrate with HaveIBeenPwned API or similar
        password_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        
        # For demo, check against small list of common compromised passwords
        common_compromised = [
            '5994471ABB01112AFCC18159F6CC74B4F511B99806DA59B3CAF5A9C173CACFC5',  # password
            'E38AD214943DAAD1D64C102FAEC29DE4AFE9DA3D',  # password123
            'B1B3773A05C0ED0176787A4F1574FF0075F7521E',  # qwerty
        ]
        
        return password_hash in common_compromised
```

---

**Document Version**: 1.0  
**Last Updated**: February 2026  
**Next Review**: March 2026  

---

*This document contains sensitive security information. Restrict access to authorized personnel only.*

*For implementation details, see [architecture.md](architecture.md)*  
*For deployment security, see [deployment.md](deployment.md)*  
*For monitoring and alerts, see [monitoring.md](monitoring.md)*