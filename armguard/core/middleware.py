"""
Custom security middleware for ArmGuard
"""
from django.core.cache import cache
from django.http import HttpResponseForbidden, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import time


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware
    Limits requests per IP address to prevent abuse
    """
    
    def process_request(self, request):
        # Skip rate limiting for authenticated admin users
        if request.user.is_authenticated and request.user.is_staff:
            return None
        
        # Skip if rate limiting is disabled
        if not getattr(settings, 'RATELIMIT_ENABLE', False):
            return None
            
        ip = self.get_client_ip(request)
        cache_key = f'ratelimit_{ip}'
        
        requests = cache.get(cache_key, [])
        now = time.time()
        
        # Remove requests older than 1 minute
        requests = [req_time for req_time in requests if now - req_time < 60]
        
        # Allow 60 requests per minute per IP (configurable)
        rate_limit = getattr(settings, 'RATELIMIT_REQUESTS_PER_MINUTE', 60)
        
        if len(requests) >= rate_limit:
            return HttpResponseForbidden(
                '<h1>429 Too Many Requests</h1>'
                '<p>Rate limit exceeded. Please try again later.</p>',
                content_type='text/html'
            )
        
        requests.append(now)
        cache.set(cache_key, requests, 60)
        
        return None
    
    def get_client_ip(self, request):
        """Get real client IP (handle proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Additional security headers middleware
    Adds custom security headers to all responses
    """
    
    def process_response(self, request, response):
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'accelerometer=()'
        )
        
        # Expect-CT (Certificate Transparency)
        if not settings.DEBUG:
            response['Expect-CT'] = 'max-age=86400, enforce'
        
        # Remove server header (reduce fingerprinting)
        if 'Server' in response:
            del response['Server']
        
        # Add custom security headers
        response['X-Permitted-Cross-Domain-Policies'] = 'none'
        
        return response


class AdminIPWhitelistMiddleware(MiddlewareMixin):
    """
    Optional: Restrict admin access to specific IPs
    Enable by adding ADMIN_ALLOWED_IPS to settings
    """
    
    def process_request(self, request):
        # Only check admin paths
        admin_url = getattr(settings, 'ADMIN_URL_PREFIX', 'admin')
        if not request.path.startswith(f'/{admin_url}/'):
            return None
        
        # Get allowed IPs from settings
        allowed_ips = getattr(settings, 'ADMIN_ALLOWED_IPS', [])
        if not allowed_ips:
            return None  # Skip if not configured
        
        ip = self.get_client_ip(request)
        
        if ip not in allowed_ips:
            return HttpResponseForbidden(
                '<h1>403 Forbidden</h1>'
                '<p>Access denied from your IP address.</p>',
                content_type='text/html'
            )
        
        return None
    
    def get_client_ip(self, request):
        """Get real client IP (handle proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class StripSensitiveHeadersMiddleware(MiddlewareMixin):
    """
    Remove potentially sensitive headers from responses
    """
    
    def process_response(self, request, response):
        # Headers to remove (information disclosure)
        sensitive_headers = [
            'X-Powered-By',
            'X-AspNet-Version',
            'X-AspNetMvc-Version',
        ]
        
        for header in sensitive_headers:
            if header in response:
                del response[header]
        
        return response
