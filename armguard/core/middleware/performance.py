"""
Performance Optimization Middleware for ArmGuard
Implements caching, query optimization, and response compression
"""
import time
import gzip
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django.conf import settings
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class PerformanceOptimizationMiddleware(MiddlewareMixin):
    """
    Advanced performance middleware for:
    - Response caching
    - GZIP compression  
    - Query count monitoring
    - Page load time tracking
    """
    
    def process_request(self, request):
        """Start performance tracking"""
        request._performance_start_time = time.time()
        request._performance_query_count = len(connection.queries)
        
        # Check cache for GET requests (only if user is available and not authenticated)
        if request.method == 'GET' and hasattr(request, 'user') and not request.user.is_authenticated:
            cache_key = self._get_cache_key(request)
            cached_response = cache.get(cache_key)
            if cached_response:
                cached_response['X-Cache-Hit'] = 'True'
                return HttpResponse(
                    cached_response['content'],
                    content_type=cached_response['content_type'],
                    status=cached_response['status'],
                    headers=cached_response.get('headers', {})
                )
    
    def process_response(self, request, response):
        """Process response with performance optimizations"""
        
        # Performance tracking
        if hasattr(request, '_performance_start_time'):
            response_time = time.time() - request._performance_start_time
            query_count = len(connection.queries) - getattr(request, '_performance_query_count', 0)
            
            # Add performance headers
            response['X-Response-Time'] = f"{response_time:.3f}s"
            response['X-Query-Count'] = str(query_count)
            
            # Log slow requests (>500ms)
            if response_time > 0.5:
                logger.warning(f"Slow request: {request.path} took {response_time:.3f}s with {query_count} queries")
        
        # GZIP compression for text responses
        if self._should_compress(request, response):
            response = self._compress_response(response)
        
        # Cache successful GET responses for anonymous users (check if user exists)
        if (request.method == 'GET' and 
            response.status_code == 200 and 
            hasattr(request, 'user') and not request.user.is_authenticated and
            'no-cache' not in response.get('Cache-Control', '')):
            
            self._cache_response(request, response)
        
        # Add cache control headers
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            response['Cache-Control'] = 'public, max-age=31536000'  # 1 year
        elif response.status_code == 200:
            response['Cache-Control'] = 'private, max-age=300'  # 5 minutes
        
        return response
    
    def _get_cache_key(self, request):
        """Generate cache key for request"""
        return f"armguard_page:{request.get_full_path()}"
    
    def _should_compress(self, request, response):
        """Check if response should be compressed"""
        if response.get('Content-Encoding'):
            return False
        
        content_type = response.get('Content-Type', '')
        compressible_types = [
            'text/html',
            'text/css', 
            'application/javascript',
            'application/json',
            'text/plain',
            'application/xml',
        ]
        
        return any(ct in content_type for ct in compressible_types)
    
    def _compress_response(self, response):
        """Compress response content with GZIP"""
        # Don't compress FileResponse (static files handled by whitenoise)
        if hasattr(response, 'streaming_content'):
            return response
            
        # Don't compress if no content attribute (e.g., FileResponse)
        if not hasattr(response, 'content'):
            return response
            
        if len(response.content) < 1024:  # Don't compress small responses
            return response
        
        try:
            compressed_content = gzip.compress(response.content)
            response.content = compressed_content
            response['Content-Encoding'] = 'gzip'
            response['Content-Length'] = str(len(compressed_content))
        except Exception as e:
            logger.error(f"GZIP compression failed: {e}")
        
        return response
    
    def _cache_response(self, request, response):
        """Cache response for anonymous users"""
        try:
            cache_key = self._get_cache_key(request)
            cache_data = {
                'content': response.content,
                'content_type': response.get('Content-Type'),
                'status': response.status_code,
                'headers': dict(response.items())
            }
            cache.set(cache_key, cache_data, timeout=300)  # 5 minutes
        except Exception as e:
            logger.error(f"Response caching failed: {e}")


class DatabaseQueryOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware for database query optimization and monitoring
    """
    
    def process_request(self, request):
        """Start query monitoring"""
        if settings.DEBUG:
            request._db_query_start_count = len(connection.queries)
    
    def process_response(self, request, response):
        """Monitor and optimize database queries"""
        if settings.DEBUG and hasattr(request, '_db_query_start_count'):
            query_count = len(connection.queries) - request._db_query_start_count
            
            # Log excessive query counts (N+1 query detection)
            if query_count > 20:
                logger.warning(f"Potential N+1 query problem: {request.path} executed {query_count} queries")
                
                # Log actual queries for debugging
                for query in connection.queries[request._db_query_start_count:]:
                    if float(query['time']) > 0.01:  # Log slow queries (>10ms)
                        logger.debug(f"Slow query ({query['time']}s): {query['sql'][:200]}...")
        
        return response


class StaticFileOptimizationMiddleware(MiddlewareMixin):
    """
    Optimize static file serving with proper headers
    """
    
    def process_response(self, request, response):
        """Add optimization headers for static files"""
        path = request.path
        
        if path.startswith('/static/') or path.startswith('/media/'):
            # Long-term caching for static assets
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
            response['Expires'] = 'Thu, 31 Dec 2037 23:55:55 GMT'
            
            # Add security headers for media files
            if path.startswith('/media/'):
                response['X-Content-Type-Options'] = 'nosniff'
                if not path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf')):
                    response['Content-Disposition'] = 'attachment'
        
        return response