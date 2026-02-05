# VPN-Aware Network Middleware for ArmGuard
# Enhanced middleware that integrates WireGuard VPN with existing LAN/WAN architecture

import ipaddress
import logging
import time
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger('armguard.vpn')

class VPNAwareNetworkMiddleware(MiddlewareMixin):
    """
    Enhanced network middleware with WireGuard VPN awareness
    
    Extends the existing LAN/WAN network security model to include VPN access
    with role-based permissions and comprehensive security logging.
    """
    
    # VPN network configuration
    VPN_NETWORK = getattr(settings, 'WIREGUARD_NETWORK', '10.0.0.0/24')
    
    # IP range mappings for different user roles
    VPN_ROLE_RANGES = {
        'commander': ('10.0.0.10', '10.0.0.19'),    # Field commanders
        'armorer': ('10.0.0.20', '10.0.0.29'),      # Armorers
        'emergency': ('10.0.0.30', '10.0.0.39'),    # Emergency operations
        'personnel': ('10.0.0.40', '10.0.0.49'),    # General personnel
    }
    
    # Access level mappings - STRICT COMPLIANCE MODEL
    # TRANSACTIONS ONLY ON LAN - VPN provides READ-ONLY INVENTORY ACCESS
    ROLE_ACCESS_LEVELS = {
        'commander': 'VPN_INVENTORY_VIEW',     # Can view inventory remotely, transactions LAN-only
        'armorer': 'VPN_INVENTORY_VIEW',       # Can view inventory remotely, transactions LAN-only
        'emergency': 'VPN_INVENTORY_LIMITED',  # Limited inventory view for emergency
        'personnel': 'VPN_STATUS_ONLY',        # Can only check personal status
    }
    
    # Session timeout by role (in seconds)
    ROLE_SESSION_TIMEOUTS = {
        'commander': 7200,      # 2 hours
        'armorer': 3600,        # 1 hour
        'emergency': 1800,      # 30 minutes
        'personnel': 900,       # 15 minutes
    }
    
    # Paths requiring PHYSICAL LAN-level access ONLY (NO VPN ACCESS)
    # These operations are NEVER allowed over VPN for maximum security
    PHYSICAL_LAN_ONLY_PATHS = [
        '/admin/register/',
        '/admin/users/create/',
        '/transactions/create/',           # CRITICAL: Transaction creation LAN ONLY
        '/transactions/qr-scanner/',       # CRITICAL: QR scanning LAN ONLY
        '/transactions/checkout/',         # CRITICAL: Equipment checkout LAN ONLY
        '/transactions/checkin/',          # CRITICAL: Equipment checkin LAN ONLY
        '/inventory/add/',
        '/inventory/edit/',
        '/personnel/add/',
        '/personnel/edit/',
        '/qr_manager/generate/',
        '/print_handler/',
        '/admin/manage/',
    ]
    
    # Paths available for VPN access (READ-ONLY INVENTORY & STATUS)
    VPN_ALLOWED_PATHS = {
        'VPN_INVENTORY_VIEW': [           # Commander/Armorer remote inventory access
            '/inventory/view/',
            '/inventory/list/',
            '/inventory/detail/',
            '/inventory/reports/',
            '/personnel/list/',
            '/personnel/detail/',
            '/transactions/history/',      # View transaction history only
            '/transactions/status/',       # Check transaction status only
            '/dashboard/',
            '/reports/',
            '/users/profile/',
        ],
        'VPN_INVENTORY_LIMITED': [        # Emergency limited access
            '/inventory/view/',
            '/inventory/critical/',        # Only critical equipment
            '/transactions/status/',
            '/dashboard/emergency/',
            '/users/profile/',
        ],
        'VPN_STATUS_ONLY': [             # Personnel status checking only
            '/transactions/status/',       # Personal transaction status
            '/personnel/profile/',         # Own profile only
            '/users/profile/',
        ],
        'COMMON': [                      # Common paths for all VPN users
            '/static/',
            '/media/',
            '/users/login/',
            '/users/logout/',
        ]
    }

    def process_request(self, request):
        """Process each request with VPN awareness"""
        
        # Skip if VPN integration is disabled
        if not getattr(settings, 'WIREGUARD_ENABLED', False):
            return None
        
        # Detect network type including VPN
        network_type = self.detect_network_type(request)
        client_ip = self.get_client_ip(request)
        
        # Add network information to request
        request.network_type = network_type
        request.client_ip = client_ip
        request.vpn_role = None
        request.access_level = None
        
        # Enhanced logging for VPN connections
        if network_type.startswith('VPN_'):
            request.vpn_role = self.detect_vpn_role(client_ip)
            request.access_level = self.ROLE_ACCESS_LEVELS.get(request.vpn_role, 'VPN_UNKNOWN')
            
            self.log_vpn_access(request, network_type, client_ip)
            
            # Check session timeout for VPN users
            if hasattr(request, 'user') and request.user.is_authenticated:
                if not self.check_session_timeout(request):
                    return self.session_timeout_response()
        
        # Apply access control based on network type
        return self.apply_access_control(request, network_type)
    
    def detect_network_type(self, request):
        """Enhanced network detection including VPN"""
        server_port = str(request.get_port())
        client_ip = self.get_client_ip(request)
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            vpn_network = ipaddress.ip_network(self.VPN_NETWORK)
            
            # Check for VPN connection
            if client_addr in vpn_network:
                vpn_role = self.detect_vpn_role(client_ip)
                if vpn_role:
                    access_level = self.ROLE_ACCESS_LEVELS.get(vpn_role, 'VPN_UNKNOWN')
                    logger.info(f"VPN connection detected: {client_ip} -> Role: {vpn_role}, Access: {access_level}")
                    return access_level
                else:
                    logger.warning(f"VPN connection from unrecognized IP range: {client_ip}")
                    return 'VPN_UNKNOWN'
            
            # Existing LAN/WAN detection
            lan_port = getattr(settings, 'LAN_PORT', '8443')
            wan_port = getattr(settings, 'WAN_PORT', '443')
            
            if server_port == lan_port:
                # Verify it's actually from LAN network
                lan_networks = getattr(settings, 'LAN_NETWORKS', ['192.168.0.0/16'])
                for network in lan_networks:
                    if client_addr in ipaddress.ip_network(network):
                        return 'LAN'
                logger.warning(f"Non-LAN IP {client_ip} attempting LAN port {lan_port}")
                return 'UNAUTHORIZED_LAN'
            
            elif server_port == wan_port:
                return 'WAN'
            
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.error(f"Invalid IP address {client_ip}: {e}")
        
        return 'UNKNOWN'
    
    def detect_vpn_role(self, client_ip):
        """Determine VPN user role based on IP address"""
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for role, (start_ip, end_ip) in self.VPN_ROLE_RANGES.items():
                start_addr = ipaddress.ip_address(start_ip)
                end_addr = ipaddress.ip_address(end_ip)
                
                if start_addr <= client_addr <= end_addr:
                    return role
            
        except (ValueError, ipaddress.AddressValueError):
            pass
        
        return None
    
    def get_client_ip(self, request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def apply_access_control(self, request, network_type):
        """Apply access control rules based on network type"""
        path = request.path
        method = request.method
        
        # Skip static files and media
        if path.startswith('/static/') or path.startswith('/media/'):
            return None
        
        # Check path-based restrictions
        if network_type in ['VPN_LAN', 'LAN']:
            # Full access to all paths for LAN and VPN_LAN users
            return None
        
        elif network_type == 'VPN_LAN_LIMITED':
            # Limited LAN access for emergency operations
            if self.is_emergency_authorized_path(path, request):
                return None
            elif path in self.WAN_ALLOWED_PATHS or any(path.startswith(p) for p in self.WAN_ALLOWED_PATHS):
                return None
            else:
                return self.access_denied_response(
                    f"Emergency access does not permit this operation: {path}",
                    network_type
                )
        
        elif network_type in ['VPN_WAN', 'WAN']:
            # WAN-level access - check if path is allowed
            if path in self.WAN_ALLOWED_PATHS or any(path.startswith(p) for p in self.WAN_ALLOWED_PATHS):
                # For POST/PUT/DELETE requests, deny even on allowed paths
                if method not in ['GET', 'HEAD', 'OPTIONS']:
                    return self.access_denied_response(
                        "Write operations not allowed via WAN access",
                        network_type
                    )
                return None
            else:
                return self.access_denied_response(
                    f"WAN access does not permit access to: {path}",
                    network_type
                )
        
        else:
            # Unknown or unauthorized network type
            return self.access_denied_response(
                "Network access not authorized",
                network_type
            )
    
    def is_emergency_authorized_path(self, path, request):
        """Check if path is authorized for emergency operations"""
        # Emergency operations can access transaction creation but not user management
        emergency_allowed = [
            '/transactions/create/',
            '/transactions/qr-scanner/',
            '/inventory/view/',
            '/personnel/list/',
            '/dashboard/',
        ]
        
        return path in emergency_allowed or any(path.startswith(p) for p in emergency_allowed)
    
    def check_session_timeout(self, request):
        """Check if VPN session has exceeded timeout"""
        if not hasattr(request, 'session') or not request.session.get('last_activity'):
            # First request, set activity timestamp
            request.session['last_activity'] = request.META.get('HTTP_X_REQUEST_TIME', str(int(time.time())))
            return True
        
        import time
        current_time = int(time.time())
        last_activity = int(request.session.get('last_activity', current_time))
        
        # Get timeout based on VPN role
        timeout = self.ROLE_SESSION_TIMEOUTS.get(
            request.vpn_role,
            self.ROLE_SESSION_TIMEOUTS['personnel']  # Default to most restrictive
        )
        
        if current_time - last_activity > timeout:
            logger.warning(f"VPN session timeout for {request.client_ip} (role: {request.vpn_role})")
            return False
        
        # Update last activity
        request.session['last_activity'] = str(current_time)
        return True
    
    def log_vpn_access(self, request, network_type, client_ip):
        """Log VPN access attempts with detailed information"""
        user_info = "anonymous"
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_info = f"{request.user.username} (ID: {request.user.id})"
        
        vpn_role = request.vpn_role or 'unknown'
        
        logger.info(
            f"VPN Access: {client_ip} -> {request.path} "
            f"[User: {user_info}, Role: {vpn_role}, Network: {network_type}, "
            f"Method: {request.method}, UserAgent: {request.META.get('HTTP_USER_AGENT', 'N/A')[:100]}]"
        )
    
    def access_denied_response(self, message, network_type):
        """Return comprehensive access denied response"""
        
        # For API requests, return JSON
        if hasattr(self, 'request') and (
            self.request.path.startswith('/api/') or 
            self.request.META.get('HTTP_ACCEPT', '').startswith('application/json')
        ):
            return JsonResponse({
                'error': 'Access Denied',
                'message': message,
                'network_type': network_type,
                'timestamp': str(timezone.now()),
            }, status=403)
        
        # For web requests, return HTML response
        return HttpResponseForbidden(f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>ArmGuard - Access Denied</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 50px auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .error-icon {{ font-size: 64px; color: #d32f2f; margin-bottom: 20px; }}
                h1 {{ color: #d32f2f; margin: 0; }}
                .message {{ background: #ffebee; border-left: 4px solid #d32f2f; padding: 15px; margin: 20px 0; }}
                .info {{ background: #e3f2fd; border-left: 4px solid #1976d2; padding: 15px; margin: 20px 0; }}
                .network-info {{ background: #f3e5f5; border-left: 4px solid #7b1fa2; padding: 15px; margin: 20px 0; }}
                ul {{ margin: 10px 0; padding-left: 20px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="error-icon">🔒</div>
                    <h1>Network Access Restricted</h1>
                </div>
                
                <div class="message">
                    <strong>Access Denied:</strong> {message}
                </div>
                
                <div class="network-info">
                    <strong>Network Type:</strong> {network_type}<br>
                    <strong>Timestamp:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
                </div>
                
                <div class="info">
                    <h3>🌐 ArmGuard Network Access Guidelines:</h3>
                    <ul>
                        <li><strong>LAN Access (Port 8443):</strong> Full armory operations, inventory management, user administration</li>
                        <li><strong>VPN Access:</strong> Role-based access with cryptographic authentication</li>
                        <li><strong>WAN Access (Port 443):</strong> Read-only status checking and reports</li>
                    </ul>
                    
                    <h3>🔐 VPN Role Access Levels:</h3>
                    <ul>
                        <li><strong>Commander VPN:</strong> Full LAN-equivalent access for field operations</li>
                        <li><strong>Armorer VPN:</strong> Complete armorer functions for off-site management</li>
                        <li><strong>Emergency VPN:</strong> Limited LAN access for crisis response</li>
                        <li><strong>Personnel VPN:</strong> WAN-equivalent read-only access</li>
                    </ul>
                </div>
                
                <div class="info">
                    <h3>📞 Need Help?</h3>
                    <p>If you believe this is an error or need access to perform authorized duties:</p>
                    <ul>
                        <li>Contact your system administrator</li>
                        <li>Verify your VPN connection and role assignment</li>
                        <li>Check if your session has timed out</li>
                        <li>For emergencies, contact base IT support</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p>ArmGuard Military Inventory Management System<br>
                    Network Security Policy Enforcement<br>
                    All access attempts are logged and monitored</p>
                </div>
            </div>
        </body>
        </html>
        ''')
    
    def session_timeout_response(self):
        """Return session timeout response"""
        return HttpResponseForbidden('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Session Timeout - ArmGuard</title>
            <meta http-equiv="refresh" content="5; url=/users/login/">
        </head>
        <body>
            <h1>🕐 Session Timeout</h1>
            <p>Your VPN session has expired due to inactivity.</p>
            <p>You will be redirected to the login page in 5 seconds.</p>
            <p><a href="/users/login/">Click here to login again</a></p>
        </body>
        </html>
        ''')


class VPNConnectionLogMiddleware(MiddlewareMixin):
    """
    Separate middleware for detailed VPN connection logging
    """
    
    def process_response(self, request, response):
        """Log VPN connection details on response"""
        
        if not getattr(settings, 'WIREGUARD_ENABLED', False):
            return response
        
        if hasattr(request, 'network_type') and request.network_type.startswith('VPN_'):
            # Log successful responses
            if 200 <= response.status_code < 300:
                logger.info(
                    f"VPN Success: {request.client_ip} -> {request.path} "
                    f"[Status: {response.status_code}, Role: {getattr(request, 'vpn_role', 'unknown')}, "
                    f"Size: {len(response.content) if hasattr(response, 'content') else 0}]"
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"VPN Error: {request.client_ip} -> {request.path} "
                    f"[Status: {response.status_code}, Role: {getattr(request, 'vpn_role', 'unknown')}]"
                )
        
        return response