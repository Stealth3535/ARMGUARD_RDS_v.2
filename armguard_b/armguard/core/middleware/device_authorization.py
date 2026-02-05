"""
Device Authorization Middleware for ArmGuard
Restricts transaction access to authorized devices only
"""
import json
import logging
import os
from django.http import HttpResponseForbidden
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger(__name__)

class DeviceAuthorizationMiddleware(MiddlewareMixin):
    """
    Middleware to restrict transaction access to authorized devices only
    """
    
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.authorized_devices = self.load_authorized_devices()
        super().__init__(get_response)
    
    def load_authorized_devices(self):
        """Load authorized devices from JSON file"""
        try:
            config_path = os.path.join(settings.BASE_DIR, 'authorized_devices.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    return data.get('devices', [])
            else:
                logger.warning(f"Authorized devices config not found at {config_path}")
                return []
        except Exception as e:
            logger.error(f"Error loading authorized devices: {e}")
            return []
    
    def get_client_ip(self, request):
        """Get client IP with multiple header fallbacks"""
        # Try multiple headers to handle various proxy setups
        headers_to_check = [
            'HTTP_X_FORWARDED_FOR',
            'HTTP_X_REAL_IP',
            'HTTP_X_FORWARDED',
            'HTTP_X_CLUSTER_CLIENT_IP',
            'HTTP_CF_CONNECTING_IP',  # Cloudflare
            'REMOTE_ADDR'
        ]
        
        for header in headers_to_check:
            ip = request.META.get(header)
            if ip:
                # Handle comma-separated IPs (X-Forwarded-For can have multiple IPs)
                if ',' in ip:
                    ip = ip.split(',')[0].strip()
                # Clean up the IP
                ip = ip.strip()
                if ip and ip != 'unknown':
                    logger.debug(f"Found IP {ip} in header {header}")
                    return ip
        
        logger.warning("Could not determine client IP")
        return None
    
    def is_authorized_device(self, client_ip):
        """Check if the client IP is from an authorized device"""
        if not client_ip:
            logger.warning("No client IP provided for authorization check")
            return False
        
        for device in self.authorized_devices:
            device_ip = device.get('ip')
            can_transact = device.get('can_transact', False)
            
            if device_ip == client_ip:
                logger.info(f"Device {client_ip} found in authorized list, can_transact={can_transact}")
                return can_transact
        
        logger.warning(f"Device {client_ip} not found in authorized devices list")
        return False
    
    def requires_authorization(self, path):
        """Determine if a path requires device authorization"""
        # Always allow these paths
        allowed_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/robots.txt',
            '/ping',
            '/health'
        ]
        
        for allowed_path in allowed_paths:
            if path.startswith(allowed_path):
                return False
        
        # Transaction-related paths that require authorization
        restricted_paths = [
            '/transactions/',
            '/inventory/add/',
            '/inventory/edit/',
            '/inventory/delete/',
            '/personnel/add/',
            '/personnel/edit/',
            '/personnel/delete/',
            '/admin/transactions/',
            '/admin/inventory/',
            '/admin/personnel/',
            '/api/transactions/',
            '/api/inventory/',
            '/api/personnel/'
        ]
        
        for restricted_path in restricted_paths:
            if path.startswith(restricted_path):
                return True
        
        # Allow read-only access for viewing pages
        return False
    
    def process_request(self, request):
        """Process incoming request for device authorization"""
        path = request.path
        
        # Skip authorization for paths that don't require it
        if not self.requires_authorization(path):
            return None
        
        # Get client IP
        client_ip = self.get_client_ip(request)
        
        # Log the authorization attempt
        logger.info(f"Authorization check for IP {client_ip} accessing {path}")
        
        # Check if device is authorized
        if not self.is_authorized_device(client_ip):
            logger.warning(f"UNAUTHORIZED ACCESS: {client_ip} tried to access {path}")
            return HttpResponseForbidden(
                f'''
                <html>
                <head>
                    <title>Device Not Authorized</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 50px; }}
                        .error {{ color: #d32f2f; }}
                        .info {{ color: #1976d2; margin-top: 20px; }}
                    </style>
                </head>
                <body>
                    <h1 class="error">🔒 Device Not Authorized</h1>
                    <p>This device is not authorized to perform transactions.</p>
                    <div class="info">
                        <p><strong>Your IP:</strong> {client_ip}</p>
                        <p><strong>Path:</strong> {path}</p>
                        <p>Only authorized devices can access transaction-related functions.</p>
                        <p>You can still view inventory and personnel information.</p>
                    </div>
                </body>
                </html>
                ''',
                content_type='text/html'
            )
        
        logger.info(f"AUTHORIZED ACCESS: {client_ip} granted access to {path}")
        return None