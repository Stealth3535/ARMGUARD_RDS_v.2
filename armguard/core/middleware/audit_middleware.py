"""
Audit Context Middleware for ArmGuard
Automatically sets audit context for all model operations to ensure comprehensive audit logging
"""
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger('audit')

class AuditContextMiddleware(MiddlewareMixin):
    """
    Middleware to automatically set audit context for model operations.
    This ensures all model saves have proper audit information without manual intervention.
    """
    
    def process_request(self, request):
        """Set audit context for the entire request lifecycle"""
        try:
            # Set audit context that models can access
            if hasattr(request, 'user') and request.user.is_authenticated:
                request._audit_context = {
                    'user': request.user,
                    'ip': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'session': getattr(request.session, 'session_key', ''),
                    'path': request.path,
                    'method': request.method
                }
            else:
                # Anonymous user context
                request._audit_context = {
                    'user': None,
                    'ip': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'session': '',
                    'path': request.path,
                    'method': request.method
                }
                
            # Log audit context creation
            logger.debug(f"Audit context set for {request.path} from {request._audit_context['ip']}")
            
        except Exception as e:
            logger.error(f"Failed to set audit context: {e}")
            # Don't break the request if audit context fails
            request._audit_context = None
    
    def get_client_ip(self, request):
        """Extract client IP address from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
    
    def process_response(self, request, response):
        """Clean up audit context after request processing"""
        if hasattr(request, '_audit_context'):
            # Log completion of audited request
            if request._audit_context and request._audit_context.get('user'):
                logger.debug(
                    f"Request completed: {request.method} {request.path} "
                    f"by {request._audit_context['user']} - Status: {response.status_code}"
                )
        return response

class ModelAuditMixin:
    """
    Mixin to automatically apply audit context from middleware to model instances.
    Add this to models that need automatic audit context.
    """
    
    def set_audit_context_from_request(self):
        """
        Set audit context from current request middleware.
        Call this in model save methods to enable automatic audit logging.
        """
        from django.middleware import get_current_request
        
        try:
            # Try to get current request from middleware
            request = get_current_request()
            if request and hasattr(request, '_audit_context') and request._audit_context:
                context = request._audit_context
                
                # Set audit attributes that models can use
                self._audit_user = context.get('user')
                self._audit_ip = context.get('ip')
                self._audit_user_agent = context.get('user_agent', '')
                self._audit_session = context.get('session', '')
                self._audit_path = context.get('path', '')
                self._audit_method = context.get('method', '')
                
                return True
        except Exception as e:
            logger.warning(f"Failed to set audit context from request: {e}")
        
        return False

# Utility function to get current request (needs to be implemented)
_current_request = None

class CurrentRequestMiddleware(MiddlewareMixin):
    """
    Simple middleware to store current request in thread-local storage
    so models can access it for audit context
    """
    
    def process_request(self, request):
        global _current_request
        _current_request = request
    
    def process_response(self, request, response):
        global _current_request
        _current_request = None
        return response

def get_current_request():
    """Get current request from thread-local storage"""
    global _current_request
    return _current_request

# Enhanced audit context for transaction API
class TransactionAuditContext:
    """
    Context manager for transaction-specific audit logging.
    Ensures all operations within a business transaction are properly audited.
    """
    
    def __init__(self, request, operation_type, target_info=None):
        self.request = request
        self.operation_type = operation_type
        self.target_info = target_info or {}
        self.start_time = None
        self.context_dict = {}
    
    def __enter__(self):
        from datetime import datetime
        self.start_time = datetime.now()
        
        # Build comprehensive audit context
        if hasattr(self.request, '_audit_context') and self.request._audit_context:
            base_context = self.request._audit_context.copy()
        else:
            base_context = {
                'user': getattr(self.request, 'user', None),
                'ip': self.get_client_ip(self.request),
                'user_agent': self.request.META.get('HTTP_USER_AGENT', ''),
                'session': getattr(self.request.session, 'session_key', ''),
                'path': self.request.path,
                'method': self.request.method
            }
        
        # Add operation-specific context
        self.context_dict = {
            **base_context,
            'operation_type': self.operation_type,
            'start_time': self.start_time,
            'target_info': self.target_info
        }
        
        # Log operation start
        logger.info(
            f"Starting {self.operation_type} operation "
            f"by {base_context.get('user', 'Anonymous')} "
            f"from {base_context.get('ip')}"
        )
        
        return self.context_dict
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from datetime import datetime
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        if exc_type is None:
            # Successful operation
            logger.info(
                f"Completed {self.operation_type} operation "
                f"in {duration:.2f}s - SUCCESS"
            )
        else:
            # Failed operation
            logger.error(
                f"Failed {self.operation_type} operation "
                f"after {duration:.2f}s - ERROR: {exc_val}"
            )
        
        return False  # Don't suppress exceptions
    
    def get_client_ip(self, request):
        """Extract client IP address from request headers"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip

# Decorator for automatic audit context in views
def audit_operation(operation_type):
    """
    Decorator to automatically set audit context for view functions.
    
    Usage:
        @audit_operation('CREATE_TRANSACTION')
        def create_transaction_view(request):
            # Audit context automatically available
            pass
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            with TransactionAuditContext(request, operation_type):
                return view_func(request, *args, **kwargs)
        return wrapper
    return decorator