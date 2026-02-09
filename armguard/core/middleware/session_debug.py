"""
Session Debug Middleware - Helps diagnose session issues
Add to MIDDLEWARE in settings.py (after SessionMiddleware) for debugging
"""
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger('core.session_debug')


class SessionDebugMiddleware(MiddlewareMixin):
    """
    Debug middleware to log session information.
    Enable this temporarily when debugging session issues.
    
    Add to settings.py MIDDLEWARE (after SessionMiddleware):
    'core.middleware.session_debug.SessionDebugMiddleware',
    """
    
    def process_request(self, request):
        """Log session information for authenticated users"""
        if request.user.is_authenticated:
            session_key = request.session.session_key
            session_age = request.session.get_expiry_age()
            session_date = request.session.get_expiry_date()
            
            logger.info(
                f"Session Debug - User: {request.user.username}, "
                f"Session Key: {session_key}, "
                f"Expires in: {session_age}s, "
                f"Expire Date: {session_date}, "
                f"Path: {request.path}"
            )
        
        return None
    
    def process_response(self, request, response):
        """Log session cookie in response"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            # Check if session was saved
            if hasattr(request.session, 'modified') and request.session.modified:
                logger.info(f"Session modified for {request.user.username}")
        
        return response
