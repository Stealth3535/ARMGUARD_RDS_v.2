"""
Device Authorization Middleware for Enhanced Transaction Security
Provides device-based authorization for sensitive operations
"""
import json
import os
from datetime import datetime
from django.http import JsonResponse, HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.core.exceptions import PermissionDenied
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Middleware to restrict certain operations to authorized devices only
    Useful for armory PCs that handle sensitive transactions
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.authorized_devices_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
        self.load_authorized_devices()
    
    def load_authorized_devices(self):
        """Load authorized devices from JSON file"""
        try:
            if self.authorized_devices_file.exists():
                with open(self.authorized_devices_file, 'r') as f:
                    self.authorized_devices = json.load(f)
            else:
                # Create default authorized devices file
                self.authorized_devices = {
                    "devices": [],
                    "allow_all": True,  # Default: allow all devices (disable in production)
                    "restricted_paths": [
                        "/transactions/create/",
                        "/transactions/api/",
                        "/inventory/api/",
                        "/admin/transactions/",
                        "/admin/inventory/"
                    ]
                }
                self.save_authorized_devices()
        except Exception as e:
            logger.error(f"Error loading authorized devices: {e}")
            # Fallback: allow all devices
            self.authorized_devices = {
                "devices": [],
                "allow_all": True,
                "restricted_paths": []
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
        
        import hashlib
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
        for restricted_path in self.authorized_devices.get('restricted_paths', []):
            if path.startswith(restricted_path):
                return True
        return False
    
    def is_device_authorized(self, device_fingerprint, ip_address):
        """Check if device is authorized"""
        # If allow_all is True, skip device checks (development mode)
        if self.authorized_devices.get('allow_all', False):
            return True
        
        # Check device fingerprint
        for device in self.authorized_devices.get('devices', []):
            if device.get('fingerprint') == device_fingerprint:
                # Check if device is active
                if device.get('active', True):
                    # Optional: Check IP address if specified
                    device_ip = device.get('ip_address')
                    if device_ip and device_ip != ip_address:
                        logger.warning(f"Device fingerprint matches but IP differs: {device_ip} vs {ip_address}")
                        return False
                    return True
        
        return False
    
    def process_request(self, request):
        """Process request for device authorization"""
        
        # Skip device checks for superusers and staff in development
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.is_superuser and settings.DEBUG:
                return None
        
        # Check if path requires authorization
        if not self.is_restricted_path(request.path):
            return None
        
        # Get device information
        device_fingerprint = self.get_device_fingerprint(request)
        ip_address = self.get_client_ip(request)
        
        # Check authorization
        if not self.is_device_authorized(device_fingerprint, ip_address):
            logger.warning(f"Unauthorized device access attempt: {device_fingerprint} from {ip_address} to {request.path}")
            
            # Return JSON response for API calls
            if request.path.startswith('/api/') or 'api' in request.path:
                return JsonResponse({
                    'error': 'Device not authorized for this operation',
                    'code': 'DEVICE_NOT_AUTHORIZED',
                    'message': 'This device is not authorized to perform sensitive operations. Please contact an administrator.'
                }, status=403)
            
            # Return HTML response for web interface
            return HttpResponseForbidden(
                '<h1>Device Not Authorized</h1>'
                '<p>This device is not authorized to perform sensitive operations.</p>'
                '<p>Please contact an administrator to authorize this device.</p>'
                f'<p>Device ID: {device_fingerprint[:8]}...</p>'
            )
        
        # Log successful authorization
        logger.info(f"Device authorized: {device_fingerprint[:8]}... from {ip_address} accessing {request.path}")
        
        return None
    
    def authorize_device(self, device_fingerprint, device_name, ip_address=None, description=None):
        """
        Add a device to authorized list
        Called by admin interface or management command
        """
        new_device = {
            'fingerprint': device_fingerprint,
            'name': device_name,
            'ip_address': ip_address,
            'description': description or '',
            'active': True,
            'created_at': str(datetime.now()),
            'authorized_by': 'system'
        }
        
        # Check if device already exists
        for device in self.authorized_devices.get('devices', []):
            if device.get('fingerprint') == device_fingerprint:
                # Update existing device
                device.update(new_device)
                self.save_authorized_devices()
                return True
        
        # Add new device
        if 'devices' not in self.authorized_devices:
            self.authorized_devices['devices'] = []
        
        self.authorized_devices['devices'].append(new_device)
        self.save_authorized_devices()
        
        logger.info(f"Device authorized: {device_name} ({device_fingerprint[:8]}...)")
        return True
    
    def revoke_device(self, device_fingerprint):
        """Revoke device authorization"""
        for device in self.authorized_devices.get('devices', []):
            if device.get('fingerprint') == device_fingerprint:
                device['active'] = False
                self.save_authorized_devices()
                logger.info(f"Device revoked: {device_fingerprint[:8]}...")
                return True
        return False


# Utility functions for device management
def get_current_device_fingerprint(request):
    """Get current request's device fingerprint"""
    middleware = DeviceAuthorizationMiddleware(None)
    return middleware.get_device_fingerprint(request)

def is_device_authorized_for_path(request, path=None):
    """Check if current device is authorized for specific path"""
    middleware = DeviceAuthorizationMiddleware(None)
    middleware.load_authorized_devices()
    
    check_path = path or request.path
    if not middleware.is_restricted_path(check_path):
        return True
    
    device_fingerprint = middleware.get_device_fingerprint(request)
    ip_address = middleware.get_client_ip(request)
    
    return middleware.is_device_authorized(device_fingerprint, ip_address)