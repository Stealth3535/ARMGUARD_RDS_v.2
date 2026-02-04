"""
Performance Monitoring Dashboard for ArmGuard
Provides real-time performance metrics and optimization insights
"""
import time
import psutil
from django.core.cache import cache
from django.db import connection
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.cache import cache_page
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Performance monitoring utility class"""
    
    @staticmethod
    def get_database_stats():
        """Get database performance statistics"""
        with connection.cursor() as cursor:
            if connection.vendor == 'postgresql':
                cursor.execute("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples
                    FROM pg_stat_user_tables 
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC;
                """)
                tables = cursor.fetchall()
                
                cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
                active_connections = cursor.fetchone()[0]
                
                return {
                    'tables': tables,
                    'active_connections': active_connections,
                    'vendor': 'postgresql'
                }
                
            elif connection.vendor == 'sqlite':
                cursor.execute("PRAGMA database_list;")
                databases = cursor.fetchall()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = cursor.fetchall()
                
                return {
                    'databases': databases,
                    'tables': [{'table': table[0]} for table in tables],
                    'vendor': 'sqlite'
                }
        
        return {'vendor': connection.vendor, 'error': 'Unsupported database'}
    
    @staticmethod
    def get_cache_stats():
        """Get cache performance statistics"""
        stats = {}
        
        try:
            # Test cache connectivity
            cache.set('health_check', 'ok', 60)
            health = cache.get('health_check') == 'ok'
            
            # Get cache info (Redis specific)
            try:
                from django_redis import get_redis_connection
                redis_conn = get_redis_connection("default")
                redis_info = redis_conn.info()
                
                stats.update({
                    'type': 'redis',
                    'healthy': health,
                    'memory_used': redis_info.get('used_memory_human', 'N/A'),
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'total_commands': redis_info.get('total_commands_processed', 0),
                    'keyspace_hits': redis_info.get('keyspace_hits', 0),
                    'keyspace_misses': redis_info.get('keyspace_misses', 0),
                })
                
                # Calculate hit rate
                hits = stats['keyspace_hits']
                misses = stats['keyspace_misses']
                total = hits + misses
                stats['hit_rate'] = (hits / total * 100) if total > 0 else 0
                
            except ImportError:
                stats.update({
                    'type': 'locmem',
                    'healthy': health,
                })
        
        except Exception as e:
            stats = {'type': 'unknown', 'healthy': False, 'error': str(e)}
        
        return stats
    
    @staticmethod
    def get_system_stats():
        """Get system performance statistics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory()._asdict(),
            'disk': psutil.disk_usage('/')._asdict(),
            'load_avg': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0],
            'boot_time': psutil.boot_time(),
            'process_count': len(psutil.pids()),
        }
    
    @staticmethod
    def get_query_stats():
        """Get recent query performance statistics"""
        cache_key = 'performance_query_stats'
        stats = cache.get(cache_key, {
            'slow_queries': 0,
            'total_queries': 0,
            'avg_time': 0,
            'queries_per_minute': 0,
        })
        return stats
    
    @staticmethod
    def log_query_performance(query_time, query):
        """Log query performance for monitoring"""
        cache_key = 'performance_query_stats'
        stats = cache.get(cache_key, {
            'slow_queries': 0,
            'total_queries': 0,
            'total_time': 0,
            'queries_per_minute': 0,
            'last_updated': timezone.now().timestamp()
        })
        
        stats['total_queries'] += 1
        stats['total_time'] += query_time
        
        # Mark as slow if > 50ms
        if query_time > 0.05:
            stats['slow_queries'] += 1
            logger.warning(f"Slow query detected ({query_time:.3f}s): {query[:100]}...")
        
        # Calculate average
        stats['avg_time'] = stats['total_time'] / stats['total_queries']
        
        # Update queries per minute (rolling window)
        now = timezone.now().timestamp()
        time_diff = now - stats.get('last_updated', now - 60)
        if time_diff > 0:
            stats['queries_per_minute'] = stats['total_queries'] / (time_diff / 60)
        
        stats['last_updated'] = now
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes


@staff_member_required
def performance_dashboard(request):
    """Performance monitoring dashboard view"""
    try:
        context = {
            'database_stats': PerformanceMonitor.get_database_stats(),
            'cache_stats': PerformanceMonitor.get_cache_stats(),
            'system_stats': PerformanceMonitor.get_system_stats(),
            'query_stats': PerformanceMonitor.get_query_stats(),
            'timestamp': timezone.now(),
        }
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(context, default=str)
        
        return render(request, 'admin/performance_dashboard.html', context)
    
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse({'error': str(e)}, status=500)
        
        context = {
            'error': f"Performance monitoring error: {e}",
            'timestamp': timezone.now(),
        }
        return render(request, 'admin/performance_dashboard.html', context)


@staff_member_required
@cache_page(60)  # Cache for 1 minute
def performance_api(request):
    """API endpoint for performance metrics"""
    return JsonResponse({
        'cache_stats': PerformanceMonitor.get_cache_stats(),
        'system_stats': PerformanceMonitor.get_system_stats(),
        'query_stats': PerformanceMonitor.get_query_stats(),
        'timestamp': timezone.now().isoformat(),
    }, default=str)


def health_check(request):
    """Simple health check endpoint"""
    try:
        # Test database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True
    except Exception:
        db_ok = False
    
    # Test cache
    try:
        cache.set('health_check', 'ok', 10)
        cache_ok = cache.get('health_check') == 'ok'
    except Exception:
        cache_ok = False
    
    status = 'healthy' if (db_ok and cache_ok) else 'unhealthy'
    status_code = 200 if status == 'healthy' else 503
    
    return JsonResponse({
        'status': status,
        'database': db_ok,
        'cache': cache_ok,
        'timestamp': timezone.now().isoformat(),
    }, status=status_code)