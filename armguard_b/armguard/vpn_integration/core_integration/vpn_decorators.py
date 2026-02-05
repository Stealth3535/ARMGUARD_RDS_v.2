# VPN-Aware Decorators for ArmGuard Views
# Enhanced decorators that work with VPN network types and roles

from functools import wraps
import logging
from django.http import HttpResponseForbidden, JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.utils import timezone

logger = logging.getLogger('armguard.vpn')

def vpn_role_required(allowed_roles):
    """
    Decorator to require specific VPN roles for view access
    
    Usage:
        @vpn_role_required(['commander', 'armorer'])
        def sensitive_view(request):
            ...
    
    Args:
        allowed_roles (list): List of VPN roles that can access this view
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Check if this is a VPN connection
            network_type = getattr(request, 'network_type', 'UNKNOWN')
            vpn_role = getattr(request, 'vpn_role', None)
            
            if not network_type.startswith('VPN_'):
                # Not a VPN connection - apply standard rules
                return view_func(request, *args, **kwargs)
            
            if vpn_role not in allowed_roles:
                logger.warning(
                    f"VPN role access denied: {request.client_ip} "
                    f"(role: {vpn_role}) attempted to access {request.path} "
                    f"(requires: {allowed_roles})"
                )
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'error': 'Insufficient VPN role permissions',
                        'required_roles': allowed_roles,
                        'your_role': vpn_role,
                        'network_type': network_type
                    }, status=403)
                else:
                    raise PermissionDenied(f"This operation requires VPN role: {', '.join(allowed_roles)}")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def vpn_lan_required(view_func):
    """
    Decorator to require VPN LAN-level access
    Allows: LAN, VPN_LAN connections
    Denies: WAN, VPN_WAN, VPN_LIMITED connections
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        network_type = getattr(request, 'network_type', 'UNKNOWN')
        
        if network_type not in ['LAN', 'VPN_LAN']:
            vpn_role = getattr(request, 'vpn_role', 'unknown')
            
            logger.warning(
                f"VPN LAN access denied: {request.client_ip} "
                f"(network: {network_type}, role: {vpn_role}) "
                f"attempted to access {request.path}"
            )
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'error': 'VPN LAN access required',
                    'network_type': network_type,
                    'required': 'LAN or VPN_LAN',
                    'vpn_role': vpn_role
                }, status=403)
            else:
                raise PermissionDenied("This operation requires VPN LAN-level access")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def vpn_wan_allowed(view_func):
    """
    Decorator for views that allow WAN/VPN_WAN access but restrict write operations
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        network_type = getattr(request, 'network_type', 'UNKNOWN')
        
        # Block write operations for WAN/VPN_WAN users
        if network_type in ['WAN', 'VPN_WAN'] and request.method not in ['GET', 'HEAD', 'OPTIONS']:
            vpn_role = getattr(request, 'vpn_role', 'unknown')
            
            logger.warning(
                f"VPN WAN write operation blocked: {request.client_ip} "
                f"(network: {network_type}, role: {vpn_role}) "
                f"attempted {request.method} {request.path}"
            )
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'error': 'Write operations not allowed via WAN/VPN_WAN',
                    'network_type': network_type,
                    'method': request.method,
                    'vpn_role': vpn_role
                }, status=403)
            else:
                raise PermissionDenied("Write operations not allowed via WAN access")
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def emergency_access_only(max_duration_hours=4):
    """
    Decorator for emergency-only operations with time limits
    
    Args:
        max_duration_hours (int): Maximum duration for emergency access
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            network_type = getattr(request, 'network_type', 'UNKNOWN')
            vpn_role = getattr(request, 'vpn_role', None)
            
            # Allow LAN access without restrictions
            if network_type == 'LAN':
                return view_func(request, *args, **kwargs)
            
            # For VPN connections, check if it's emergency role
            if network_type == 'VPN_LAN_LIMITED' and vpn_role == 'emergency':
                # Check if emergency access is still valid (time-based)
                if hasattr(request, 'session'):
                    import time
                    emergency_start = request.session.get('emergency_access_start')
                    if not emergency_start:
                        request.session['emergency_access_start'] = str(int(time.time()))
                        emergency_start = request.session['emergency_access_start']
                    
                    current_time = int(time.time())
                    start_time = int(emergency_start)
                    duration_hours = (current_time - start_time) / 3600
                    
                    if duration_hours > max_duration_hours:
                        logger.warning(
                            f"Emergency access expired: {request.client_ip} "
                            f"(duration: {duration_hours:.1f}h, limit: {max_duration_hours}h)"
                        )
                        return JsonResponse({
                            'error': 'Emergency access time limit exceeded',
                            'duration_hours': round(duration_hours, 1),
                            'limit_hours': max_duration_hours
                        }, status=403)
                
                return view_func(request, *args, **kwargs)
            
            # Deny all other access types
            logger.warning(
                f"Emergency-only access denied: {request.client_ip} "
                f"(network: {network_type}, role: {vpn_role}) "
                f"attempted to access {request.path}"
            )
            
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'error': 'Emergency access required',
                    'network_type': network_type,
                    'required': 'LAN or Emergency VPN',
                    'vpn_role': vpn_role
                }, status=403)
            else:
                raise PermissionDenied("This operation requires emergency access authorization")
        
        return wrapper
    return decorator

def log_vpn_access(action_description):
    """
    Decorator to log specific VPN actions for audit purposes
    
    Args:
        action_description (str): Description of the action being performed
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            network_type = getattr(request, 'network_type', 'UNKNOWN')
            
            if network_type.startswith('VPN_'):
                vpn_role = getattr(request, 'vpn_role', 'unknown')
                client_ip = getattr(request, 'client_ip', 'unknown')
                user = request.user.username if request.user.is_authenticated else 'anonymous'
                
                # Log the action
                logger.info(
                    f"VPN Action: {action_description} "
                    f"[User: {user}, IP: {client_ip}, Role: {vpn_role}, "
                    f"Network: {network_type}, Path: {request.path}, "
                    f"Method: {request.method}, Time: {timezone.now()}]"
                )
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def rate_limit_vpn(requests_per_minute=30):
    """
    Rate limiting decorator specifically for VPN connections
    
    Args:
        requests_per_minute (int): Maximum requests per minute for VPN users
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            network_type = getattr(request, 'network_type', 'UNKNOWN')
            
            if not network_type.startswith('VPN_'):
                # Not a VPN connection, skip rate limiting
                return view_func(request, *args, **kwargs)
            
            client_ip = getattr(request, 'client_ip', 'unknown')
            
            # Simple in-memory rate limiting (consider Redis for production)
            import time
            from collections import defaultdict
            
            # Store request times per IP
            if not hasattr(wrapper, 'request_times'):
                wrapper.request_times = defaultdict(list)
            
            current_time = time.time()
            minute_ago = current_time - 60
            
            # Clean old requests
            wrapper.request_times[client_ip] = [
                t for t in wrapper.request_times[client_ip] if t > minute_ago
            ]
            
            # Check rate limit
            if len(wrapper.request_times[client_ip]) >= requests_per_minute:
                logger.warning(
                    f"VPN rate limit exceeded: {client_ip} "
                    f"({len(wrapper.request_times[client_ip])} requests/minute, "
                    f"limit: {requests_per_minute})"
                )
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'error': 'Rate limit exceeded',
                        'limit': f"{requests_per_minute} requests per minute",
                        'network_type': network_type
                    }, status=429)
                else:
                    return HttpResponseForbidden("Rate limit exceeded. Please slow down your requests.")
            
            # Record this request
            wrapper.request_times[client_ip].append(current_time)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def vpn_session_active(view_func):
    """
    Decorator to ensure VPN session is active and not expired
    """
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        network_type = getattr(request, 'network_type', 'UNKNOWN')
        
        if not network_type.startswith('VPN_'):
            return view_func(request, *args, **kwargs)
        
        # Check session activity
        if hasattr(request, 'session'):
            import time
            current_time = int(time.time())
            last_activity = int(request.session.get('last_activity', current_time))
            
            # Get timeout based on role
            from .vpn_middleware import VPNAwareNetworkMiddleware
            vpn_role = getattr(request, 'vpn_role', 'personnel')
            timeout = VPNAwareNetworkMiddleware.ROLE_SESSION_TIMEOUTS.get(vpn_role, 900)
            
            if current_time - last_activity > timeout:
                logger.warning(
                    f"VPN session expired: {request.client_ip} "
                    f"(role: {vpn_role}, inactive: {current_time - last_activity}s)"
                )
                
                # Clear session
                request.session.flush()
                
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({
                        'error': 'VPN session expired',
                        'timeout_seconds': timeout,
                        'vpn_role': vpn_role
                    }, status=401)
                else:
                    from django.shortcuts import redirect
                    return redirect('/users/login/?reason=session_expired')
            
            # Update last activity
            request.session['last_activity'] = str(current_time)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def commander_or_armorer_only(view_func):
    """
    Convenience decorator for operations requiring commander or armorer access
    """
    return vpn_role_required(['commander', 'armorer'])(view_func)

def emergency_or_higher(view_func):
    """
    Convenience decorator for operations allowing emergency level access or higher
    """
    return vpn_role_required(['commander', 'armorer', 'emergency'])(view_func)

# Backward compatibility aliases
vpn_admin_required = commander_or_armorer_only
vpn_full_access_required = vpn_lan_required