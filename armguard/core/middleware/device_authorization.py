"""
Device Authorization Middleware for Enhanced Transaction Security
Provides device-based authorization for sensitive operations with production features
"""
import json
import os
from datetime import datetime, time, timedelta
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from pathlib import Path
from django.core.cache import cache
from django.utils import timezone
import logging
import hashlib

logger = logging.getLogger(__name__)

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Middleware to restrict certain operations to authorized devices only
    Useful for armory PCs that handle sensitive transactions
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.authorized_devices_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
        self._last_auth_reason = 'not_evaluated'
        self.load_authorized_devices()

    def _persist_access_log(self, request, user, device_fingerprint, ip_address, security_level, is_authorized, reason, response_status):
        """Persist device access decisions for forensic analysis."""
        try:
            from admin.models import DeviceAccessLog

            db_user = None
            if user is not None and getattr(user, 'is_authenticated', False):
                db_user = user

            DeviceAccessLog.objects.create(
                user=db_user,
                path=request.path,
                method=request.method,
                ip_address=ip_address or None,
                device_fingerprint=device_fingerprint,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:2000],
                security_level=security_level if security_level in {'STANDARD', 'RESTRICTED', 'HIGH_SECURITY'} else 'RESTRICTED',
                is_authorized=is_authorized,
                reason=(reason or '')[:255],
                response_status=response_status,
            )
        except Exception as log_error:
            logger.error(f"Failed to persist device access log: {log_error}")
    
    def load_authorized_devices(self):
        """Load authorized devices from JSON file with production defaults"""
        try:
            if self.authorized_devices_file.exists():
                with open(self.authorized_devices_file, 'r') as f:
                    self.authorized_devices = json.load(f)
                    
                # Validate production configuration
                if not self.authorized_devices.get('security_mode'):
                    self.authorized_devices['security_mode'] = 'DEVELOPMENT' if settings.DEBUG else 'PRODUCTION'

                if 'protect_root_path' not in self.authorized_devices:
                    self.authorized_devices['protect_root_path'] = not settings.DEBUG

                default_exempt_paths = [
                    '/static/',
                    '/media/',
                    '/favicon.ico',
                    '/robots.txt',
                    '/login/',
                    '/accounts/login/',
                    '/logout/',
                    '/admin/device/request-authorization/',
                ]
                configured_exempt_paths = self.authorized_devices.get('exempt_paths', [])
                normalized_exempt_paths = [
                    path for path in configured_exempt_paths
                    if path != '/admin/device/authorize/'
                ]
                for required_path in default_exempt_paths:
                    if required_path not in normalized_exempt_paths:
                        normalized_exempt_paths.append(required_path)
                self.authorized_devices['exempt_paths'] = normalized_exempt_paths
                    
            else:
                # Create production-ready default configuration
                self.authorized_devices = {
                    "devices": [],
                    "allow_all": settings.DEBUG,  # False in production
                    "security_mode": "DEVELOPMENT" if settings.DEBUG else "PRODUCTION",
                    "require_device_registration": not settings.DEBUG,
                    "max_failed_attempts": 3,
                    "lockout_duration_minutes": 30,
                    "protect_root_path": not settings.DEBUG,
                    "exempt_paths": [
                        "/static/",
                        "/media/",
                        "/favicon.ico",
                        "/robots.txt",
                        "/login/",
                        "/accounts/login/",
                        "/logout/",
                        "/admin/device/request-authorization/"
                    ],
                    "restricted_paths": [
                        "/transactions/create/",
                        "/transactions/api/",
                        "/inventory/api/",
                        "/admin/transactions/",
                        "/admin/inventory/",
                        "/qr_manager/generate/",
                        "/personnel/api/create/"
                    ],
                    "high_security_paths": [
                        "/admin/",
                        "/transactions/delete/",
                        "/users/delete/",
                        "/inventory/delete/"
                    ],
                    "audit_settings": {
                        "log_all_attempts": True,
                        "alert_on_unauthorized": True,
                        "retention_days": 90
                    }
                }
                self.save_authorized_devices()
        except Exception as e:
            logger.error(f"Error loading authorized devices: {e}")
            # Production fallback: strict security
            self.authorized_devices = {
                "devices": [],
                "allow_all": settings.DEBUG,
                "security_mode": "PRODUCTION",
                "protect_root_path": not settings.DEBUG,
                "exempt_paths": ["/static/", "/media/", "/favicon.ico", "/robots.txt", "/login/", "/accounts/login/", "/logout/", "/admin/device/request-authorization/"],
                "restricted_paths": ["/transactions/", "/admin/", "/api/"]
            }
    
    def save_authorized_devices(self):
        """Save authorized devices to JSON file"""
        try:
            with open(self.authorized_devices_file, 'w') as f:
                json.dump(self.authorized_devices, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving authorized devices: {e}")
    
    def get_device_fingerprint(self, request):
        """
        Generate device fingerprint from request headers
        Combines multiple headers for unique identification
        """
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        remote_addr = self.get_client_ip(request)
        
        # Create fingerprint from combined headers
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}|{remote_addr}"
        
        fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()[:32]
        
        return fingerprint
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def is_restricted_path(self, path):
        """Check if path requires device authorization"""
        exempt_paths = self.authorized_devices.get('exempt_paths', [])
        for exempt_path in exempt_paths:
            if path.startswith(exempt_path):
                return False

        if self.authorized_devices.get('protect_root_path', not settings.DEBUG):
            return 'HIGH_SECURITY'

        # Check high security paths first (stricter requirements)
        high_security_paths = self.authorized_devices.get('high_security_paths', [])
        for restricted_path in high_security_paths:
            if path.startswith(restricted_path):
                return 'HIGH_SECURITY'
                
        # Check regular restricted paths
        restricted_paths = self.authorized_devices.get('restricted_paths', [])
        for restricted_path in restricted_paths:
            if path.startswith(restricted_path):
                return 'RESTRICTED'
                
        return False

    def _security_rank(self, level):
        normalized_level = (level or 'STANDARD').upper()
        aliases = {
            'HIGH': 'HIGH_SECURITY',
            'MILITARY': 'HIGH_SECURITY',
            'DEVELOPMENT': 'STANDARD',
        }
        normalized_level = aliases.get(normalized_level, normalized_level)

        rank_map = {
            'STANDARD': 1,
            'RESTRICTED': 2,
            'HIGH_SECURITY': 3,
        }
        return rank_map.get(normalized_level, 1)

    def _mtls_required_for_security(self, required_security):
        if not getattr(settings, 'MTLS_ENABLED', False):
            return False

        min_level = getattr(settings, 'MTLS_REQUIRED_SECURITY_LEVEL', 'HIGH_SECURITY')
        return self._security_rank(required_security) >= self._security_rank(min_level)

    def _get_mtls_context(self, request):
        """Read mTLS verification context from trusted reverse-proxy headers."""
        verify_header = getattr(settings, 'MTLS_HEADER_VERIFY', 'HTTP_X_SSL_CLIENT_VERIFY')
        dn_header = getattr(settings, 'MTLS_HEADER_DN', 'HTTP_X_SSL_CLIENT_DN')
        serial_header = getattr(settings, 'MTLS_HEADER_SERIAL', 'HTTP_X_SSL_CLIENT_SERIAL')
        fingerprint_header = getattr(settings, 'MTLS_HEADER_FINGERPRINT', 'HTTP_X_SSL_CLIENT_FINGERPRINT')

        if not getattr(settings, 'MTLS_TRUST_PROXY_HEADERS', True):
            return {
                'verified': False,
                'verify_status': 'UNTRUSTED_PROXY_HEADERS',
                'subject_dn': '',
                'serial': '',
                'fingerprint': '',
            }

        verify_status = (request.META.get(verify_header, '') or '').strip().upper()
        subject_dn = (request.META.get(dn_header, '') or '').strip()
        serial = (request.META.get(serial_header, '') or '').strip()
        fingerprint = (request.META.get(fingerprint_header, '') or '').strip()
        verified = verify_status == 'SUCCESS'

        return {
            'verified': verified,
            'verify_status': verify_status or 'NONE',
            'subject_dn': subject_dn,
            'serial': serial,
            'fingerprint': fingerprint,
        }
    
    def is_device_authorized(self, device_fingerprint, ip_address, path=None, user=None, required_security=None):
        """Check if device is authorized with enhanced security checks"""
        self._last_auth_reason = 'authorized'

        # Check if device is locked out
        if self._is_device_locked_out(device_fingerprint):
            logger.warning(f"Device {device_fingerprint[:8]}... is locked out due to failed attempts")
            self._last_auth_reason = 'locked_out'
            return False
            
        # Development mode bypass
        if self.authorized_devices.get('allow_all', False) and settings.DEBUG:
            self._last_auth_reason = 'allow_all_debug'
            return True
        
        device_config = None
        # Find device configuration
        for device in self.authorized_devices.get('devices', []):
            if (device.get('fingerprint') == device_fingerprint or 
                device.get('ip') == ip_address):
                device_config = device
                break
        
        if not device_config:
            self._record_failed_attempt(device_fingerprint, ip_address)
            self._last_auth_reason = 'device_not_registered'
            return False

        # Enforce required security tier for the requested path
        if required_security is None and path:
            required_security = self.is_restricted_path(path)

        if required_security:
            device_security_level = device_config.get('security_level', 'STANDARD')
            required_rank = self._security_rank(required_security)
            device_rank = self._security_rank(device_security_level)

            if device_rank < required_rank:
                logger.warning(
                    "Device security level insufficient: device=%s required=%s path=%s",
                    device_security_level,
                    required_security,
                    path,
                )
                self._last_auth_reason = f'insufficient_security_level_{device_security_level.lower()}_for_{required_security.lower()}'
                return False
            
        # Check if device is active
        if not device_config.get('active', True):
            logger.warning(f"Device {device_config.get('name', 'Unknown')} is deactivated")
            self._last_auth_reason = 'device_deactivated'
            return False
            
        # Check IP address match (if specified)
        device_ip = device_config.get('ip')
        if device_ip and device_ip != ip_address:
            logger.warning(f"Device IP mismatch: expected {device_ip}, got {ip_address}")
            self._record_failed_attempt(device_fingerprint, ip_address)
            self._last_auth_reason = 'ip_mismatch'
            return False
            
        # Check active hours (if specified)
        if not self._is_within_active_hours(device_config):
            logger.warning(f"Device {device_config.get('name')} accessed outside active hours")
            self._last_auth_reason = 'outside_active_hours'
            return False
            
        # Check transaction limits
        if path and 'transaction' in path.lower():
            if not self._check_transaction_limits(device_config, device_fingerprint):
                self._last_auth_reason = 'daily_transaction_limit_exceeded'
                return False
                
        # Check user authorization for device (if specified)
        if user and device_config.get('authorized_users'):
            user_groups = [g.name.lower() for g in user.groups.all()]
            authorized_users = [u.lower() for u in device_config.get('authorized_users', [])]
            
            if not any(group in authorized_users for group in user_groups):
                if user.username.lower() not in authorized_users:
                    logger.warning(f"User {user.username} not authorized for device {device_config.get('name')}")
                    self._last_auth_reason = 'user_not_authorized_for_device'
                    return False
        
        return True
    
    def _is_device_locked_out(self, device_fingerprint):
        """Check if device is locked out due to failed attempts"""
        lockout_key = f"device_lockout_{device_fingerprint}"
        lockout_data = cache.get(lockout_key)
        
        if not lockout_data:
            return False
            
        # Check if lockout has expired
        lockout_until = datetime.fromisoformat(lockout_data.get('lockout_until', ''))
        if timezone.now() > lockout_until:
            cache.delete(lockout_key)
            return False
            
        return True
    
    def _record_failed_attempt(self, device_fingerprint, ip_address):
        """Record failed authorization attempt and implement lockout"""
        attempts_key = f"device_attempts_{device_fingerprint}"
        attempts_data = cache.get(attempts_key, {'count': 0, 'first_attempt': timezone.now().isoformat()})
        
        attempts_data['count'] += 1
        attempts_data['last_attempt'] = timezone.now().isoformat()
        attempts_data['last_ip'] = ip_address
        
        # Check if max attempts reached
        max_attempts = self.authorized_devices.get('max_failed_attempts', 5)
        if attempts_data['count'] >= max_attempts:
            # Lock out the device
            lockout_duration = self.authorized_devices.get('lockout_duration_minutes', 30)
            lockout_until = timezone.now() + timedelta(minutes=lockout_duration)
            
            lockout_key = f"device_lockout_{device_fingerprint}"
            cache.set(lockout_key, {
                'lockout_until': lockout_until.isoformat(),
                'reason': 'Too many failed attempts',
                'attempts': attempts_data['count']
            }, timeout=lockout_duration * 60)
            
            logger.warning(
                f"Device locked out: {device_fingerprint[:8]}... "
                f"from IP {ip_address} for {lockout_duration} minutes "
                f"after {attempts_data['count']} failed attempts"
            )
            
            # Clear attempts counter
            cache.delete(attempts_key)
        else:
            # Store updated attempts
            cache.set(attempts_key, attempts_data, timeout=3600)  # 1 hour
    
    def _is_within_active_hours(self, device_config):
        """Check if current time is within device's active hours"""
        active_hours = device_config.get('active_hours')
        if not active_hours:
            return True  # No restrictions
            
        current_time = timezone.now().time()
        start_time = time.fromisoformat(active_hours.get('start', '00:00:00'))
        end_time = time.fromisoformat(active_hours.get('end', '23:59:59'))
        
        if start_time <= end_time:
            return start_time <= current_time <= end_time
        else:
            # Handle overnight range (e.g., 22:00 to 06:00)
            return current_time >= start_time or current_time <= end_time
    
    def _check_transaction_limits(self, device_config, device_fingerprint):
        """Check if device has exceeded daily transaction limits"""
        max_transactions = device_config.get('max_daily_transactions')
        if not max_transactions:
            return True  # No limit
            
        # Get today's transaction count
        today = timezone.now().date().isoformat()
        trans_key = f"device_transactions_{device_fingerprint}_{today}"
        trans_count = cache.get(trans_key, 0)
        
        if trans_count >= max_transactions:
            logger.warning(
                f"Device {device_config.get('name')} exceeded daily transaction limit "
                f"({trans_count}/{max_transactions})"
            )
            return False
            
        # Increment counter
        cache.set(trans_key, trans_count + 1, timeout=86400)  # 24 hours
        return True
    
    def _send_security_alert(self, device_fingerprint, ip_address, path, user):
        """Send security alert for high-security violations"""
        if not self.authorized_devices.get('audit_settings', {}).get('alert_on_unauthorized', True):
            return
            
        alert_data = {
            'timestamp': timezone.now().isoformat(),
            'device_fingerprint': device_fingerprint[:16] + '...',
            'ip_address': ip_address,
            'path': path,
            'user': getattr(user, 'username', 'Anonymous'),
            'severity': 'HIGH'
        }
        
        # Log alert (in production, this could send emails or trigger notifications)
        logger.critical(
            f"SECURITY ALERT: Unauthorized high-security access attempt - "
            f"Device: {alert_data['device_fingerprint']}, "
            f"IP: {ip_address}, "
            f"Path: {path}, "
            f"User: {alert_data['user']}"
        )
        
        # Store alert in cache for dashboard display
        alerts_key = "security_alerts"
        alerts = cache.get(alerts_key, [])
        alerts.insert(0, alert_data)
        cache.set(alerts_key, alerts[:100], timeout=86400)  # Keep last 100 alerts for 24 hours
    
    def process_request(self, request):
        """Process request for device authorization"""
        
        # Skip device checks for superusers and staff in development
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.is_superuser and settings.DEBUG:
                return None
        
        # Check if path requires authorization
        path_security = self.is_restricted_path(request.path)
        if not path_security:
            return None
        
        # Get device information
        device_fingerprint = self.get_device_fingerprint(request)
        ip_address = self.get_client_ip(request)
        mtls_context = self._get_mtls_context(request)
        request.mtls_context = mtls_context

        if self._mtls_required_for_security(path_security) and not mtls_context.get('verified', False):
            self._last_auth_reason = f"mtls_required_but_not_verified_{mtls_context.get('verify_status', 'NONE').lower()}"
            user = getattr(request, 'user', None)

            self._persist_access_log(
                request=request,
                user=user,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                security_level=path_security,
                is_authorized=False,
                reason=self._last_auth_reason,
                response_status=403,
            )

            logger.warning(
                "mTLS verification failed for protected path: status=%s path=%s ip=%s user=%s",
                mtls_context.get('verify_status', 'NONE'),
                request.path,
                ip_address,
                getattr(user, 'username', 'Anonymous')
            )

            if request.path.startswith('/api/') or 'api' in request.path:
                return JsonResponse({
                    'error': 'mTLS verification required',
                    'code': 'MTLS_REQUIRED',
                    'security_level': path_security,
                    'verify_status': mtls_context.get('verify_status', 'NONE'),
                    'message': 'Client certificate verification is required for this operation.'
                }, status=403)

            return HttpResponseRedirect('/admin/device/request-authorization/')
        
        # Check authorization with enhanced security
        user = getattr(request, 'user', None)
        if not self.is_device_authorized(device_fingerprint, ip_address, request.path, user, path_security):
            # Log detailed unauthorized attempt
            logger.warning(
                f"Unauthorized device access attempt: "
                f"Device: {device_fingerprint[:8]}..., "
                f"IP: {ip_address}, "
                f"Path: {request.path}, "
                f"User: {getattr(user, 'username', 'Anonymous')}, "
                f"Security Level: {path_security}"
            )
            
            # Send security alert for high security paths
            if path_security == 'HIGH_SECURITY':
                self._send_security_alert(device_fingerprint, ip_address, request.path, user)
            
            # Return appropriate response
            if request.path.startswith('/api/') or 'api' in request.path:
                self._persist_access_log(
                    request=request,
                    user=user,
                    device_fingerprint=device_fingerprint,
                    ip_address=ip_address,
                    security_level=path_security,
                    is_authorized=False,
                    reason=self._last_auth_reason,
                    response_status=403,
                )
                return JsonResponse({
                    'error': 'Device not authorized for this operation',
                    'code': 'DEVICE_NOT_AUTHORIZED',
                    'security_level': path_security,
                    'message': 'This device is not authorized to perform sensitive operations. Contact administrator.',
                    'device_id': device_fingerprint[:8] + '...',
                    'timestamp': timezone.now().isoformat()
                }, status=403)
            
            self._persist_access_log(
                request=request,
                user=user,
                device_fingerprint=device_fingerprint,
                ip_address=ip_address,
                security_level=path_security,
                is_authorized=False,
                reason=self._last_auth_reason,
                response_status=403,
            )

            return HttpResponseRedirect('/admin/device/request-authorization/')
        
        # Log successful authorization
        logger.info(f"Device authorized: {device_fingerprint[:8]}... from {ip_address} accessing {request.path}")

        self._persist_access_log(
            request=request,
            user=user,
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            security_level=path_security,
            is_authorized=True,
            reason=self._last_auth_reason,
            response_status=200,
        )
        
        return None
    
    def authorize_device(self, device_fingerprint, device_name, ip_address=None, description=None, 
                        can_transact=True, security_level="STANDARD", roles=None, max_daily_transactions=50):
        """
        Add a device to authorized list with enhanced configuration
        Called by admin interface or management command
        """
        new_device = {
            'fingerprint': device_fingerprint,
            'name': device_name,
            'ip': ip_address,  # Updated key name for consistency
            'description': description or '',
            'active': True,
            'can_transact': can_transact,
            'security_level': security_level,
            'roles': roles or [],
            'max_daily_transactions': max_daily_transactions,
            'created_at': timezone.now().isoformat(),
            'authorized_by': 'system',
            'last_accessed': None
        }
        
        # Check if device already exists
        device_updated = False
        for device in self.authorized_devices.get('devices', []):
            if (device.get('fingerprint') == device_fingerprint or 
                (ip_address and device.get('ip') == ip_address)):
                # Update existing device
                device.update(new_device)
                device_updated = True
                break
        
        if not device_updated:
            # Add new device
            if 'devices' not in self.authorized_devices:
                self.authorized_devices['devices'] = []
            
            self.authorized_devices['devices'].append(new_device)
        
        # Update last_updated timestamp
        self.authorized_devices['last_updated'] = timezone.now().isoformat()
        self.save_authorized_devices()
        
        action = "updated" if device_updated else "authorized"
        logger.info(f"Device {action}: {device_name} ({device_fingerprint[:8]}...) - Security: {security_level}")
        return True
    
    def revoke_device(self, device_fingerprint, reason="Manual revocation"):
        """Revoke device authorization with audit trail"""
        for device in self.authorized_devices.get('devices', []):
            if device.get('fingerprint') == device_fingerprint:
                device['active'] = False
                device['revoked_at'] = timezone.now().isoformat()
                device['revocation_reason'] = reason
                
                # Clear any lockouts for this device
                lockout_key = f"device_lockout_{device_fingerprint}"
                cache.delete(lockout_key)
                
                self.save_authorized_devices()
                logger.warning(f"Device revoked: {device.get('name', 'Unknown')} ({device_fingerprint[:8]}...) - Reason: {reason}")
                return True
        return False
    
    def get_device_stats(self):
        """Get device statistics for monitoring"""
        devices = self.authorized_devices.get('devices', [])
        stats = {
            'total_devices': len(devices),
            'active_devices': sum(1 for d in devices if d.get('active', True)),
            'inactive_devices': sum(1 for d in devices if not d.get('active', True)),
            'transaction_enabled': sum(1 for d in devices if d.get('can_transact', False)),
            'security_levels': {},
            'locked_out_devices': 0
        }
        
        # Count security levels
        for device in devices:
            level = device.get('security_level', 'STANDARD')
            stats['security_levels'][level] = stats['security_levels'].get(level, 0) + 1
        
        # Check for locked out devices
        for device in devices:
            fingerprint = device.get('fingerprint')
            if fingerprint and self._is_device_locked_out(fingerprint):
                stats['locked_out_devices'] += 1
        
        return stats


# Utility functions for device management
def get_current_device_fingerprint(request):
    """Get current request's device fingerprint"""
    middleware = DeviceAuthorizationMiddleware(lambda req: None)
    return middleware.get_device_fingerprint(request)

def is_device_authorized_for_path(request, path=None):
    """Check if current device is authorized for specific path"""
    middleware = DeviceAuthorizationMiddleware(lambda req: None)
    middleware.load_authorized_devices()
    
    check_path = path or request.path
    path_security = middleware.is_restricted_path(check_path)
    if not path_security:
        return True
    
    device_fingerprint = middleware.get_device_fingerprint(request)
    ip_address = middleware.get_client_ip(request)
    user = getattr(request, 'user', None)
    
    return middleware.is_device_authorized(device_fingerprint, ip_address, check_path, user, path_security)

def get_device_info(request):
    """Get comprehensive device information for current request"""
    middleware = DeviceAuthorizationMiddleware(lambda req: None)
    middleware.load_authorized_devices()
    
    device_fingerprint = middleware.get_device_fingerprint(request)
    ip_address = middleware.get_client_ip(request)
    
    # Find device config
    device_config = None
    for device in middleware.authorized_devices.get('devices', []):
        if (device.get('fingerprint') == device_fingerprint or 
            device.get('ip') == ip_address):
            device_config = device
            break
    
    return {
        'fingerprint': device_fingerprint,
        'ip_address': ip_address,
        'config': device_config,
        'is_authorized': middleware.is_device_authorized(
            device_fingerprint,
            ip_address,
            request.path,
            getattr(request, 'user', None),
            middleware.is_restricted_path(request.path)
        ),
        'is_locked_out': middleware._is_device_locked_out(device_fingerprint)
    }