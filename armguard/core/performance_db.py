"""
Performance-optimized database utilities for ArmGuard
Implements query optimization, prefetching, and caching strategies
"""
from django.db import models
from django.core.cache import cache
from django.db.models import Prefetch
from django.utils import timezone
from datetime import timedelta
import hashlib


class OptimizedQuerySetMixin:
    """
    Mixin for QuerySet optimization with caching and prefetching
    """
    
    def with_cache(self, timeout=300):
        """Cache queryset results"""
        query_key = self._get_cache_key()
        cached_result = cache.get(query_key)
        
        if cached_result is not None:
            return cached_result
        
        result = list(self)
        cache.set(query_key, result, timeout)
        return result
    
    def _get_cache_key(self):
        """Generate unique cache key for queryset"""
        query_str = str(self.query)
        return f"armguard_qs:{hashlib.md5(query_str.encode()).hexdigest()}"


class OptimizedPersonnelQuerySet(models.QuerySet, OptimizedQuerySetMixin):
    """Optimized queries for Personnel model"""
    
    def active(self):
        """Get active personnel with optimizations"""
        return self.filter(status='Active', deleted_at__isnull=True)
    
    def with_transactions(self):
        """Prefetch transactions to avoid N+1 queries"""
        return self.prefetch_related(
            Prefetch('transactions', 
                    queryset=models.Q(action='Take') | models.Q(action='Return'))
        )
    
    def search_optimized(self, query):
        """Optimized search with database indexes"""
        return self.filter(
            models.Q(firstname__icontains=query) |
            models.Q(surname__icontains=query) |
            models.Q(serial__icontains=query)
        ).select_related('user')


class OptimizedItemQuerySet(models.QuerySet, OptimizedQuerySetMixin):
    """Optimized queries for Item model"""
    
    def available(self):
        """Get available items with caching"""
        return self.filter(status='Available')
    
    def by_type(self, item_type):
        """Get items by type with prefetching"""
        return self.filter(item_type=item_type).select_related()
    
    def with_current_holder(self):
        """Get items with current holder information"""
        from transactions.models import Transaction
        
        return self.prefetch_related(
            Prefetch('transactions',
                    queryset=Transaction.objects.filter(
                        action='Take'
                    ).select_related('personnel').order_by('-timestamp'),
                    to_attr='current_transactions')
        )


class OptimizedTransactionQuerySet(models.QuerySet, OptimizedQuerySetMixin):
    """Optimized queries for Transaction model"""
    
    def recent(self, days=30):
        """Get recent transactions with optimizations"""
        cutoff_date = timezone.now() - timedelta(days=days)
        return self.filter(timestamp__gte=cutoff_date).select_related('personnel', 'item', 'issued_by')
    
    def by_personnel(self, personnel):
        """Get transactions by personnel with prefetching"""
        return self.filter(personnel=personnel).select_related('item').order_by('-timestamp')
    
    def by_item(self, item):
        """Get transactions by item with prefetching"""
        return self.filter(item=item).select_related('personnel').order_by('-timestamp')
    
    def active_takes(self):
        """Get active take transactions (not returned)"""
        return self.filter(action='Take').exclude(
            item__transactions__action='Return',
            item__transactions__timestamp__gt=models.F('timestamp')
        )


class PerformanceManager(models.Manager):
    """
    Base manager with performance optimizations
    """
    
    def get_cached(self, **kwargs):
        """Get single object with caching"""
        cache_key = f"armguard_obj:{self.model._meta.label}:{hash(frozenset(kwargs.items()))}"
        cached_obj = cache.get(cache_key)
        
        if cached_obj is not None:
            return cached_obj
        
        obj = self.get(**kwargs)
        cache.set(cache_key, obj, timeout=300)  # 5 minutes
        return obj
    
    def bulk_create_optimized(self, objs, batch_size=100):
        """Optimized bulk create with batching"""
        return self.bulk_create(objs, batch_size=batch_size, ignore_conflicts=False)
    
    def bulk_update_optimized(self, objs, fields, batch_size=100):
        """Optimized bulk update with batching"""
        return self.bulk_update(objs, fields, batch_size=batch_size)


def clear_model_cache(model_class):
    """Clear all cached data for a model"""
    cache_pattern = f"armguard_*{model_class._meta.label}*"
    # Note: This would require cache backend that supports pattern deletion
    # For now, we'll use cache versioning
    cache.clear()


def get_dashboard_stats_cached():
    """Get dashboard statistics with caching"""
    cache_key = "armguard_dashboard_stats"
    stats = cache.get(cache_key)
    
    if stats is not None:
        return stats
    
    from personnel.models import Personnel
    from inventory.models import Item
    from transactions.models import Transaction
    
    stats = {
        'total_personnel': Personnel.objects.filter(deleted_at__isnull=True).count(),
        'active_personnel': Personnel.objects.filter(status='Active', deleted_at__isnull=True).count(),
        'total_items': Item.objects.count(),
        'available_items': Item.objects.filter(status='Available').count(),
        'recent_transactions': Transaction.objects.filter(
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count(),
        'items_on_loan': Transaction.objects.filter(action='Take').exclude(
            item__transactions__action='Return',
            item__transactions__timestamp__gt=models.F('timestamp')
        ).count(),
    }
    
    cache.set(cache_key, stats, timeout=300)  # Cache for 5 minutes
    return stats


def invalidate_dashboard_cache():
    """Invalidate dashboard cache when data changes"""
    cache.delete("armguard_dashboard_stats")


# Database connection optimization utilities
def optimize_database_settings():
    """Apply database optimizations based on environment"""
    from django.db import connection
    
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            # PostgreSQL specific optimizations
            cursor.execute("SET work_mem = '256MB';")
            cursor.execute("SET maintenance_work_mem = '512MB';")
            cursor.execute("SET effective_cache_size = '2GB';")
            cursor.execute("SET random_page_cost = 1.1;")
    
    elif connection.vendor == 'sqlite':
        with connection.cursor() as cursor:
            # SQLite specific optimizations
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA cache_size = -64000;")  # 64MB cache
            cursor.execute("PRAGMA temp_store = MEMORY;")
            cursor.execute("PRAGMA synchronous = NORMAL;")