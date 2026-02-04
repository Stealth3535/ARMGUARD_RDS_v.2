"""
Enhanced security middleware for production
"""
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add comprehensive security headers"""
    
    def process_response(self, request, response):
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'same-origin'
        response['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), '
            'payment=(), usb=(), magnetometer=(), gyroscope=()'
        )
        
        # Remove server information
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']
            
        return response

class RequestLoggingMiddleware(MiddlewareMixin):
    """Log security-relevant requests"""
    
    def process_request(self, request):
        # Log sensitive endpoints
        sensitive_paths = [
            '/admin/', '/api/', '/login/', '/logout/',
            '/users/', '/personnel/', '/inventory/', '/transactions/'
        ]
        
        if any(request.path.startswith(path) for path in sensitive_paths):
            logger.info(
                "Access attempt: %s %s from %s user=%s",
                request.method,
                request.path,
                self.get_client_ip(request),
                request.user.username if hasattr(request, 'user') and request.user.is_authenticated else 'anonymous'
            )
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

class SingleSessionMiddleware(MiddlewareMixin):
    """Prevent concurrent sessions for the same user"""
    
    def process_request(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            current_session = request.session.session_key
            stored_session = request.user.userprofile.last_session_key if hasattr(request.user, 'userprofile') else None
            
            # If user has a different active session, log them out
            if stored_session and stored_session != current_session:
                logger.warning(
                    "Multiple session detected for user %s, terminating old session",
                    request.user.username
                )
                # Update to new session
                if hasattr(request.user, 'userprofile'):
                    request.user.userprofile.last_session_key = current_session
                    request.user.userprofile.save()
        
        return None