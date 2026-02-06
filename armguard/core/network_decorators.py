# Network-Aware Decorators for Views

from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def lan_required(view_func):
    """
    Decorator to require LAN access for sensitive operations
    Use on views that handle registration, transactions, or modifications
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        network_type = getattr(request, 'network_type', 'wan')  # Default to WAN for security
        
        if network_type != 'lan':
            logger.warning(f"LAN-only operation attempted via {network_type}: {request.path}")
            
            if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'This operation requires LAN access',
                    'network_type': network_type,
                    'required': 'lan'
                }, status=403)
            else:
                raise PermissionDenied("This operation requires LAN access for security")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def read_only_on_wan(view_func):
    """
    Decorator to allow GET requests from WAN but restrict write operations
    Use on views that should be readable from WAN but not modifiable
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        network_type = getattr(request, 'network_type', 'UNKNOWN')
        
        if network_type == 'WAN' and request.method not in ['GET', 'HEAD', 'OPTIONS']:
            logger.warning(f"WAN write operation blocked: {request.method} {request.path}")
            
            if request.headers.get('Content-Type') == 'application/json' or request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Write operations not allowed via WAN',
                    'network_type': network_type,
                    'allowed_methods': ['GET', 'HEAD', 'OPTIONS']
                }, status=403)
            else:
                raise PermissionDenied("Write operations not allowed via WAN")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def network_aware_permission_required(permission, lan_only=False):
    """
    Enhanced permission decorator that considers network location
    
    Args:
        permission: Django permission string
        lan_only: If True, require LAN access regardless of permission
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check basic authentication
            if not request.user.is_authenticated:
                raise PermissionDenied("Authentication required")
            
            # Check network restrictions
            network_type = getattr(request, 'network_type', 'UNKNOWN')
            
            if lan_only and network_type != 'LAN':
                logger.warning(f"LAN-only permission check failed: {permission} via {network_type}")
                raise PermissionDenied("This operation requires LAN access")
            
            # Check user permission
            if not request.user.has_perm(permission):
                logger.warning(f"Permission denied: {request.user.username} lacks {permission}")
                raise PermissionDenied(f"Permission {permission} required")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator