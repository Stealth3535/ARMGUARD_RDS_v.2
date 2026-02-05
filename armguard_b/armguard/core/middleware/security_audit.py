"""
Security audit middleware for logging suspicious activity
"""
import logging
from django.utils import timezone

logger = logging.getLogger('security')

class SecurityAuditMiddleware:
    """Log security-relevant events"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Log admin access attempts
        if request.path.startswith('/admin/'):
            logger.info(f"Admin access: {request.user} from {self.get_client_ip(request)}")
        
        # Log authentication events
        if 'login' in request.path:
            logger.info(f"Login attempt: {request.POST.get('username', 'unknown')} from {self.get_client_ip(request)}")
        
        response = self.get_response(request)
        
        # Log failed authentication
        if response.status_code == 401:
            logger.warning(f"Authentication failed from {self.get_client_ip(request)}")
        
        return response
    
    def get_client_ip(self, request):
        """Get the client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
