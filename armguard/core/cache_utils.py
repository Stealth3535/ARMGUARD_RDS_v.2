"""
Caching utilities for ARMGUARD application
Provides query result caching and cache invalidation helpers
"""
from django.core.cache import cache
from django.db.models import Count, Q
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CacheKeys:
    """Centralized cache key definitions"""
    DASHBOARD_STATS = 'dashboard_stats'
    PERSONNEL_COUNT = 'personnel_count'
    ACTIVE_PERSONNEL_COUNT = 'active_personnel_count'
    OFFICERS_COUNT = 'officers_count'
    ENLISTED_COUNT = 'enlisted_count'
    ITEMS_COUNT = 'items_count'
    TRANSACTIONS_COUNT = 'transactions_count'
    USERS_COUNT = 'users_count'
    ITEMS_BY_TYPE = 'items_by_type'
    
    @staticmethod
    def personnel_detail(personnel_id):
        return f'personnel_detail_{personnel_id}'
    
    @staticmethod
    def user_detail(user_id):
        return f'user_detail_{user_id}'


class DashboardCache:
    """
    Cache manager for dashboard statistics.
    Provides methods to get, set, and invalidate dashboard data.
    """
    
    CACHE_TIMEOUT = 300  # 5 minutes
    
    @classmethod
    def get_stats(cls):
        """
        Get cached dashboard statistics or compute if not cached.
        Returns dictionary with all dashboard stats.
        """
        stats = cache.get(CacheKeys.DASHBOARD_STATS)
        
        if stats is None:
            stats = cls._compute_stats()
            cache.set(CacheKeys.DASHBOARD_STATS, stats, cls.CACHE_TIMEOUT)
            logger.info("Dashboard stats computed and cached")
        else:
            logger.debug("Dashboard stats retrieved from cache")
        
        return stats
    
    @classmethod
    def _compute_stats(cls):
        """Compute all dashboard statistics (expensive operation)"""
        from personnel.models import Personnel
        from inventory.models import Item
        from transactions.models import Transaction
        from django.contrib.auth.models import User
        
        stats = {
            # Personnel statistics
            'total_personnel': Personnel.objects.count(),
            'active_personnel': Personnel.objects.filter(status='Active').count(),
            'officers_count': Personnel.objects.filter(classification='OFFICER').count(),
            'enlisted_count': Personnel.objects.filter(classification='ENLISTED PERSONNEL').count(),
            'unlinked_personnel': Personnel.objects.filter(user__isnull=True).count(),
            
            # Item statistics
            'total_items': Item.objects.count(),
            'available_items': Item.objects.filter(status='Available').count(),
            'issued_items': Item.objects.filter(status='Issued').count(),
            'maintenance_items': Item.objects.filter(status='Maintenance').count(),
            
            # Items by type
            'items_by_type': list(Item.objects.values('item_type').annotate(count=Count('id'))),
            
            # Transaction statistics
            'total_transactions': Transaction.objects.count(),
            'recent_transactions_count': Transaction.objects.filter(
                date_time__gte=timezone.now() - timedelta(days=7)
            ).count() if 'timezone' in dir() else 0,
            
            # User statistics
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'administrators_count': User.objects.filter(
                Q(groups__name='Admin') | Q(is_superuser=True)
            ).distinct().count(),
            'armorers_count': User.objects.filter(groups__name='Armorer').count(),
        }
        
        return stats
    
    @classmethod
    def invalidate(cls):
        """Invalidate (clear) cached dashboard statistics"""
        cache.delete(CacheKeys.DASHBOARD_STATS)
        logger.info("Dashboard stats cache invalidated")
    
    @classmethod
    def refresh(cls):
        """Force refresh of cached dashboard statistics"""
        cls.invalidate()
        return cls.get_stats()


class QueryCache:
    """
    General-purpose query result caching.
    Use for frequently accessed, slowly changing data.
    """
    
    DEFAULT_TIMEOUT = 300  # 5 minutes
    
    @staticmethod
    def cached_query(cache_key, timeout=DEFAULT_TIMEOUT):
        """
        Decorator to cache query results.
        
        Usage:
            @QueryCache.cached_query('my_cache_key', timeout=600)
            def get_expensive_query():
                return Model.objects.filter(...).annotate(...)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Try to get from cache
                result = cache.get(cache_key)
                
                if result is None:
                    # Cache miss - compute result
                    result = func(*args, **kwargs)
                    cache.set(cache_key, result, timeout)
                    logger.debug(f"Cache miss for {cache_key}, computed and cached")
                else:
                    logger.debug(f"Cache hit for {cache_key}")
                
                return result
            return wrapper
        return decorator
    
    @staticmethod
    def invalidate(cache_key):
        """Invalidate a specific cache key"""
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated: {cache_key}")
    
    @staticmethod
    def invalidate_pattern(pattern):
        """Invalidate all cache keys matching pattern (Redis only)"""
        try:
            from django.conf import settings
            if 'redis' in settings.CACHES['default']['BACKEND'].lower():
                cache_obj = cache._cache
                keys = cache_obj.keys(f"*{pattern}*")
                if keys:
                    cache_obj.delete_many(keys)
                    logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
        except Exception as e:
            logger.warning(f"Pattern invalidation failed (may not be using Redis): {e}")


def invalidate_on_save(cache_keys):
    """
    Decorator to invalidate cache when model is saved.
    
    Usage in models:
        @invalidate_on_save([CacheKeys.DASHBOARD_STATS, CacheKeys.PERSONNEL_COUNT])
        def save(self, *args, **kwargs):
            super().save(*args, **kwargs)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            
            # Invalidate specified cache keys
            for key in cache_keys:
                if callable(key):
                    # Dynamic key (e.g., CacheKeys.personnel_detail(self.id))
                    cache.delete(key(self.id))
                else:
                    # Static key
                    cache.delete(key)
            
            return result
        return wrapper
    return decorator


# Convenience functions
def invalidate_dashboard_cache():
    """Invalidate dashboard statistics cache"""
    DashboardCache.invalidate()


def invalidate_personnel_caches():
    """Invalidate all personnel-related caches"""
    QueryCache.invalidate_pattern('personnel')
    DashboardCache.invalidate()


def invalidate_item_caches():
    """Invalidate all item-related caches"""
    QueryCache.invalidate_pattern('item')
    QueryCache.invalidate_pattern('inventory')
    DashboardCache.invalidate()


def invalidate_transaction_caches():
    """Invalidate all transaction-related caches"""
    QueryCache.invalidate_pattern('transaction')
    DashboardCache.invalidate()


# Import timezone here to avoid circular import
from django.utils import timezone
from datetime import timedelta
