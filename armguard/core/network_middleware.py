# Network-Based Access Control Middleware for LAN/WAN Architecture

from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import ipaddress
import logging

logger = logging.getLogger(__name__)

class NetworkBasedAccessMiddleware(MiddlewareMixin):
    """
    Enforce LAN/WAN access control for ArmGuard military operations
    
    LAN (8443): Full access - registration, transactions, inventory management
    WAN (443): Read-only access - status checking and reports only
    """
    
    # Define operations that require LAN access (write operations)
    LAN_ONLY_PATHS = [
        '/admin/register/',              # User registration
        '/admin/users/create/',          # User creation
        '/api/transactions/',            # Transaction creation
        '/inventory/update/',            # Inventory updates
        '/personnel/add/',               # Personnel registration
        '/personnel/edit/',              # Personnel editing
        '/admin/items/',                 # Item management
        '/print_handler/',               # Print operations
        '/qr_manager/generate/',         # QR generation
    ]
    
    # Define operations that are allowed on WAN (read-only)
    WAN_ALLOWED_PATHS = [
        '/admin/dashboard/',             # Dashboard viewing
        '/admin/reports/',               # Reports viewing
        '/api/personnel/',               # Personnel lookup (GET only)
        '/api/items/',                   # Item lookup (GET only)
        '/transactions/status/',         # Transaction status
        '/personnel/search/',            # Personnel search
        '/inventory/view/',              # Inventory viewing
        '/static/',                      # Static files
        '/media/',                       # Media files
        '/users/login/',                 # Login
        '/users/logout/',                # Logout
    ]
    
    def process_request(self, request):
        """Process each request based on network origin"""
        
        # Skip middleware if not enabled
        if not getattr(settings, 'ENABLE_NETWORK_ACCESS_CONTROL', False):
            # Still set default attributes for compatibility
            request.is_lan_access = True
            request.is_wan_access = False
            request.network_type = 'lan'
            return None
            
        # Get client information
        client_ip = self.get_client_ip(request)
        server_port = request.META.get('SERVER_PORT', '80')
        current_path = request.path
        http_method = request.method
        
        # Determine network type based on port and IP
        network_type = self.determine_network_type(client_ip, server_port)
        
        # Set request attributes for use in views and templates
        request.network_type = network_type
        request.is_lan_access = (network_type == 'lan')
        request.is_wan_access = (network_type == 'wan')
        
        # Log access attempt for security monitoring
        logger.info(f"Access attempt: {client_ip}:{server_port} -> {current_path} ({http_method}) via {network_type}")
        
        # Apply network-based restrictions
        if network_type == 'lan':
            # LAN: Allow all operations
            return None
            
        elif network_type == 'wan':
            # WAN: Restrict to read-only operations
            return self.enforce_wan_restrictions(request, current_path, http_method)
            
        else:
            # Unknown network: Treat as WAN for security (default to most restrictive)
            logger.warning(f"Unknown network type, defaulting to WAN restrictions: {client_ip}:{server_port}")
            return self.enforce_wan_restrictions(request, current_path, http_method)
    
    def determine_network_type(self, client_ip, server_port):
        """Determine if request is from LAN or WAN based on IP and port"""
        
        # Port-based detection (primary method)
        if server_port == '8443':
            return 'lan'  # LAN access port
        elif server_port == '443':
            return 'wan'  # WAN access port
        
        # IP-based detection (fallback method)
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            
            # Define LAN networks
            lan_networks = [
                ipaddress.ip_network('192.168.0.0/16'),    # Private Class C
                ipaddress.ip_network('172.16.0.0/12'),     # Private Class B  
                ipaddress.ip_network('10.0.0.0/8'),        # Private Class A
                ipaddress.ip_network('127.0.0.0/8'),       # Loopback
            ]
            
            # Check if IP is in LAN range
            for network in lan_networks:
                if ip_obj in network:
                    return 'lan'
            
            # If not in LAN range, consider it WAN
            return 'wan'
            
        except ValueError:
            # Invalid IP address - default to WAN for security
            return 'wan'
    
    def enforce_wan_restrictions(self, request, current_path, http_method):
        """Enforce WAN read-only restrictions"""
        
        # Block write operations (POST, PUT, DELETE, PATCH)
        if http_method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Allow only specific read-only POST operations (like login)
            allowed_post_paths = ['/users/login/', '/users/logout/']
            if not any(current_path.startswith(path) for path in allowed_post_paths):
                logger.warning(f"WAN write operation blocked: {http_method} {current_path}")
                return self.access_denied_response(
                    "Write operations not allowed via WAN. Use LAN connection for transactions and modifications."
                )
        
        # Block LAN-only paths entirely
        for lan_path in self.LAN_ONLY_PATHS:
            if current_path.startswith(lan_path):
                logger.warning(f"WAN access to LAN-only path blocked: {current_path}")
                return self.access_denied_response(
                    "This operation requires LAN access for security. Please use the local network connection."
                )
        
        # Allow WAN-allowed paths
        for wan_path in self.WAN_ALLOWED_PATHS:
            if current_path.startswith(wan_path):
                return None  # Allow access
        
        # For API endpoints, ensure GET-only access
        if current_path.startswith('/api/'):
            if http_method != 'GET':
                logger.warning(f"WAN API write operation blocked: {http_method} {current_path}")
                return JsonResponse(
                    {'error': 'API write operations not allowed via WAN'},
                    status=403
                )
        
        # Default: Allow GET requests, block others
        if http_method != 'GET':
            return self.access_denied_response(
                "Only read operations allowed via WAN"
            )
        
        return None  # Allow GET requests
    
    def access_denied_response(self, message):
        """Return access denied response"""
        return HttpResponseForbidden(f'''
        <html>
        <head><title>Access Denied - Network Security</title></head>
        <body>
            <h1>🔒 Network Access Restricted</h1>
            <p><strong>ArmGuard Security Policy:</strong></p>
            <p>{message}</p>
            <hr>
            <p><strong>Network Access Guidelines:</strong></p>
            <ul>
                <li><strong>LAN (port 8443):</strong> Full access for armory operations</li>
                <li><strong>WAN (port 443):</strong> Read-only access for status checking</li>
            </ul>
            <p>Contact your system administrator if you need assistance.</p>
        </body>
        </html>
        ''')
    
    def get_client_ip(self, request):
        """Get real client IP (handle proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserRoleNetworkMiddleware(MiddlewareMixin):
    """
    Additional role-based restrictions based on network access
    Enhances user permissions based on network location
    """
    
    def process_request(self, request):
        """Add network-based context to user permissions"""
        
        if not request.user.is_authenticated:
            return None
            
        # Add network context to request for templates and views
        client_ip = self.get_client_ip(request)
        server_port = request.META.get('SERVER_PORT', '80')
        
        # Determine network type
        if server_port == '8443' or self.is_lan_ip(client_ip):
            request.network_type = 'LAN'
            request.allow_write_operations = True
        else:
            request.network_type = 'WAN'
            request.allow_write_operations = False
            
        return None
    
    def is_lan_ip(self, client_ip):
        """Check if IP is from LAN"""
        try:
            ip_obj = ipaddress.ip_address(client_ip)
            lan_networks = [
                ipaddress.ip_network('192.168.0.0/16'),
                ipaddress.ip_network('172.16.0.0/12'),
                ipaddress.ip_network('10.0.0.0/8'),
                ipaddress.ip_network('127.0.0.0/8'),
            ]
            return any(ip_obj in network for network in lan_networks)
        except ValueError:
            return False
    
    def get_client_ip(self, request):
        """Get real client IP (handle proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip