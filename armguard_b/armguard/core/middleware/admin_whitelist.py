"""
IP whitelist middleware for admin interface
"""
from django.http import HttpResponseForbidden
from django.conf import settings
import ipaddress

class AdminIPWhitelistMiddleware:
    """Restrict admin interface to whitelisted IP addresses"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        # TODO: Configure allowed IPs in settings
        self.allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', ['127.0.0.1'])
    
    def __call__(self, request):
        if request.path.startswith('/admin/'):
            client_ip = self.get_client_ip(request)
            if not self.is_ip_allowed(client_ip):
                return HttpResponseForbidden("Access denied")
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        """Get the client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def is_ip_allowed(self, ip):
        """Check if IP is in allowed list"""
        try:
            client_ip = ipaddress.ip_address(ip)
            for allowed_ip in self.allowed_ips:
                if ipaddress.ip_address(allowed_ip) == client_ip:
                    return True
            return False
        except ValueError:
            return False
