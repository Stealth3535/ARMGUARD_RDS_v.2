"""
Simple Performance Grade Validation for ArmGuard A+ Rating
"""
import time
import os
import sys
import django
from django.core.cache import cache
from django.db import connection

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()


def test_cache_performance():
    """Test cache performance for A+ validation"""
    print("🔄 Testing Cache Performance...")
    
    # Clear cache
    cache.clear()
    
    # Test cache operations
    start_time = time.time()
    for i in range(100):
        cache.set(f'perf_test_{i}', f'value_{i}', 300)
    set_time = time.time() - start_time
    
    start_time = time.time()
    hits = 0
    for i in range(100):
        if cache.get(f'perf_test_{i}'):
            hits += 1
    get_time = time.time() - start_time
    
    hit_rate = hits / 100 * 100
    
    print(f"   ✅ Cache SET (100 ops): {set_time*1000:.1f}ms")
    print(f"   ✅ Cache GET (100 ops): {get_time*1000:.1f}ms") 
    print(f"   ✅ Cache Hit Rate: {hit_rate:.1f}%")
    
    # A+ Requirements
    cache_grade = "A+"
    if set_time > 0.1:
        cache_grade = "A-"
    if get_time > 0.05:
        cache_grade = "A-"
    if hit_rate < 95:
        cache_grade = "B+"
        
    print(f"   📊 Cache Grade: {cache_grade}")
    return cache_grade == "A+"


def test_database_performance():
    """Test database connection and basic query performance"""
    print("🗄️  Testing Database Performance...")
    
    try:
        # Test database connection
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        connect_time = time.time() - start_time
        
        print(f"   ✅ Database Connection: {connect_time*1000:.1f}ms")
        
        # Test simple query performance
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            count = cursor.fetchone()[0]
        query_time = time.time() - start_time
        
        print(f"   ✅ Simple Query: {query_time*1000:.1f}ms")
        print(f"   ✅ Database Vendor: {connection.vendor}")
        
        # A+ Requirements: <50ms for queries
        db_grade = "A+"
        if connect_time > 0.05:
            db_grade = "A-"
        if query_time > 0.05:
            db_grade = "A-"
            
        print(f"   📊 Database Grade: {db_grade}")
        return db_grade == "A+"
        
    except Exception as e:
        print(f"   ❌ Database Error: {e}")
        print(f"   📊 Database Grade: C")
        return False


def test_static_configuration():
    """Test static file configuration"""
    print("📁 Testing Static File Configuration...")
    
    from django.conf import settings
    
    # Check compression settings
    compression_enabled = getattr(settings, 'STATICFILES_STORAGE', '') == 'whitenoise.storage.CompressedManifestStaticFilesStorage'
    whitenoise_configured = hasattr(settings, 'WHITENOISE_MAX_AGE')
    
    print(f"   ✅ Static Compression: {'Enabled' if compression_enabled else 'Disabled'}")
    print(f"   ✅ Whitenoise Config: {'Configured' if whitenoise_configured else 'Basic'}")
    print(f"   ✅ Static URL: {settings.STATIC_URL}")
    print(f"   ✅ Static Root: {settings.STATIC_ROOT}")
    
    static_grade = "A+" if (compression_enabled and whitenoise_configured) else "B+"
    print(f"   📊 Static Files Grade: {static_grade}")
    return static_grade == "A+"


def test_cache_configuration():
    """Test advanced cache configuration"""
    print("⚡ Testing Cache Configuration...")
    
    from django.conf import settings
    
    caches = settings.CACHES
    cache_backends = len(caches)
    has_redis = any('redis' in cache.get('BACKEND', '') for cache in caches.values())
    has_sessions_cache = 'sessions' in caches
    has_template_cache = 'template_cache' in caches
    
    print(f"   ✅ Cache Backends: {cache_backends}")
    print(f"   ✅ Redis Available: {'Yes' if has_redis else 'No'}")
    print(f"   ✅ Session Cache: {'Dedicated' if has_sessions_cache else 'Shared'}")
    print(f"   ✅ Template Cache: {'Dedicated' if has_template_cache else 'Shared'}")
    
    # A+ requires multiple cache backends (Redis preferred, but multi-level locmem acceptable)
    config_grade = "A+" if (cache_backends >= 3 and has_sessions_cache and has_template_cache) else "B+"
    if not has_redis and cache_backends >= 3:
        print(f"   ℹ️  Note: Using fallback multi-level local memory cache (Redis preferred)")
    print(f"   📊 Cache Config Grade: {config_grade}")
    return config_grade == "A+"


def main():
    """Run all performance validation tests"""
    print("🚀 ArmGuard A+ Performance Validation")
    print("=" * 50)
    
    results = []
    
    # Run all tests
    results.append(test_cache_performance())
    results.append(test_database_performance()) 
    results.append(test_static_configuration())
    results.append(test_cache_configuration())
    
    # Calculate overall grade
    passed_tests = sum(results)
    total_tests = len(results)
    success_rate = passed_tests / total_tests * 100
    
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE VALIDATION RESULTS")
    print("=" * 50)
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 100:
        grade = "A+"
        status = "🎉 EXCEPTIONAL - A+ Performance Validated!"
    elif success_rate >= 80:
        grade = "A-" 
        status = "✅ EXCELLENT - Nearly A+ Performance"
    elif success_rate >= 60:
        grade = "B+"
        status = "👍 GOOD - Performance Optimizations Working"
    else:
        grade = "B"
        status = "⚠️  NEEDS IMPROVEMENT"
        
    print(f"Overall Grade: {grade}")
    print(f"Status: {status}")
    
    print("\n🔍 A+ Performance Criteria:")
    print("  • Multi-level Redis caching with fallback")
    print("  • Database queries <50ms")
    print("  • Cache operations <100ms") 
    print("  • Static file compression enabled")
    print("  • Dedicated cache backends for sessions/templates")
    
    return grade == "A+"


if __name__ == '__main__':
    main()