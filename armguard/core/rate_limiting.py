"""
Rate limiting decorators for ArmGuard security
Prevents brute force attacks and API abuse
"""
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache
from django.conf import settings
from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

def rate_limit(key_func=None, rate='10/m', methods=['POST'], message='Rate limit exceeded'):
    """
    Rate limiting decorator
    Args:
        key_func: Function to generate cache key (default: uses IP)
        rate: Rate limit in format 'count/period' where period is s/m/h/d
        methods: HTTP methods to rate limit
        message: Error message for rate limited requests
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Only apply rate limiting to specified methods
            if request.method not in methods:
                return view_func(request, *args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(request)
            else:
                # Default: use IP address
                ip = get_client_ip(request)
                cache_key = f"rate_limit:{request.path}:{ip}"
            
            # Parse rate limit
            count, period = rate.split('/')
            count = int(count)
            
            period_seconds = {
                's': 1, 'm': 60, 'h': 3600, 'd': 86400
            }.get(period, 60)
            
            # Check current count
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= count:
                logger.warning(f"Rate limit exceeded for {cache_key}")
                if 'application/json' in request.META.get('HTTP_ACCEPT', ''):
                    return JsonResponse({'error': message}, status=429)
                else:
                    return HttpResponse(f"<h1>429 - {message}</h1>", status=429)
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, period_seconds)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator

def get_client_ip(request):
    """Get client IP address with proxy support"""
    headers_to_check = [
        'HTTP_X_FORWARDED_FOR',
        'HTTP_X_REAL_IP', 
        'HTTP_CF_CONNECTING_IP',
        'REMOTE_ADDR'
    ]
    
    for header in headers_to_check:
        ip = request.META.get(header)
        if ip:
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            if ip and ip != 'unknown':
                return ip
    
    return request.META.get('REMOTE_ADDR', 'unknown')

# Predefined decorators for common use cases
api_rate_limit = rate_limit(rate='30/m', methods=['POST', 'PUT', 'PATCH', 'DELETE'])
login_rate_limit = rate_limit(rate='5/m', methods=['POST'], message='Too many login attempts')
auth_rate_limit = rate_limit(rate='10/m', methods=['POST'])