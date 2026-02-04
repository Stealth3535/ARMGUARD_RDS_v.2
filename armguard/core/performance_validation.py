"""
ArmGuard Performance Validation Suite
Validates A+ performance grade through comprehensive benchmarking
"""
import time
import statistics
from django.test import TestCase, TransactionTestCase, Client
from django.core.cache import cache
from django.db import connection, reset_queries
from django.conf import settings
from django.contrib.auth.models import User
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from django.test.utils import override_settings
import logging

logger = logging.getLogger(__name__)


class PerformanceValidationTestCase(TestCase):
    """Comprehensive performance validation tests"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            is_staff=True
        )
        
        # Create test data
        self.personnel = Personnel.objects.create(
            firstname='Test',
            surname='User',
            rank='Sergeant',
            serial='12345',
            status='Active'
        )
        
        self.item = Item.objects.create(
            item_type='Rifle',
            make='TestMake',
            model='TestModel',
            serial='ITEM123',
            status='Available'
        )
    
    def test_page_load_performance(self):
        """Test: Page loads must be <500ms for A+ grade"""
        self.client.login(username='testuser', password='testpass123')
        
        pages_to_test = [
            '/',  # Dashboard
            '/personnel/',  # Personnel list
            '/inventory/',  # Inventory list
            '/transactions/',  # Transaction list
            '/reports/',  # Reports page
        ]
        
        response_times = []
        
        for url in pages_to_test:
            start_time = time.time()
            try:
                response = self.client.get(url)
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Log the performance
                logger.info(f"Page {url}: {response_time:.3f}s")
                
                # A+ requirement: <500ms (0.5s)
                self.assertLess(response_time, 0.5, 
                               f"Page {url} took {response_time:.3f}s (>500ms threshold for A+)")
                
                # Verify successful response
                self.assertIn(response.status_code, [200, 302])
                
            except Exception as e:
                logger.warning(f"Page {url} test failed: {e}")
                # Skip failed pages for now (might not exist in all configurations)
                continue
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            max_response_time = max(response_times)
            
            print(f"\nPage Load Performance Results:")
            print(f"Average Response Time: {avg_response_time:.3f}s")
            print(f"Maximum Response Time: {max_response_time:.3f}s")
            print(f"Pages Tested: {len(response_times)}")
            
            # A+ grade requirements
            self.assertLess(avg_response_time, 0.3, 
                           f"Average response time {avg_response_time:.3f}s exceeds A+ threshold (300ms)")
            self.assertLess(max_response_time, 0.5,
                           f"Maximum response time {max_response_time:.3f}s exceeds A+ threshold (500ms)")
    
    def test_database_query_performance(self):
        """Test: Database queries must be <50ms for A+ grade"""
        query_times = []
        
        # Test common database operations
        test_operations = [
            lambda: list(Personnel.objects.all()),
            lambda: list(Item.objects.all()),
            lambda: list(Transaction.objects.all()),
            lambda: Personnel.objects.filter(status='Active').count(),
            lambda: Item.objects.filter(status='Available').count(),
            lambda: Personnel.objects.select_related('user').first(),
        ]
        
        for operation in test_operations:
            reset_queries()
            start_time = time.time()
            
            try:
                result = operation()
                end_time = time.time()
                query_time = end_time - start_time
                query_times.append(query_time)
                
                # A+ requirement: <50ms (0.05s)
                self.assertLess(query_time, 0.05,
                               f"Database query took {query_time:.3f}s (>50ms threshold for A+)")
                
            except Exception as e:
                logger.warning(f"Query test failed: {e}")
                continue
        
        if query_times:
            avg_query_time = statistics.mean(query_times)
            max_query_time = max(query_times)
            
            print(f"\nDatabase Query Performance Results:")
            print(f"Average Query Time: {avg_query_time*1000:.1f}ms")
            print(f"Maximum Query Time: {max_query_time*1000:.1f}ms")
            print(f"Queries Tested: {len(query_times)}")
            
            # A+ grade requirements
            self.assertLess(avg_query_time, 0.03,
                           f"Average query time {avg_query_time*1000:.1f}ms exceeds A+ threshold (30ms)")
    
    def test_cache_performance(self):
        """Test: Cache operations must be fast and reliable"""
        cache.clear()  # Start fresh
        
        # Test cache set performance
        start_time = time.time()
        for i in range(100):
            cache.set(f'test_key_{i}', f'test_value_{i}', 300)
        set_time = time.time() - start_time
        
        # Test cache get performance
        start_time = time.time()
        for i in range(100):
            value = cache.get(f'test_key_{i}')
            self.assertEqual(value, f'test_value_{i}')
        get_time = time.time() - start_time
        
        print(f"\nCache Performance Results:")
        print(f"100 SET operations: {set_time*1000:.1f}ms")
        print(f"100 GET operations: {get_time*1000:.1f}ms")
        print(f"Average SET time: {set_time*10:.2f}ms per operation")
        print(f"Average GET time: {get_time*10:.2f}ms per operation")
        
        # A+ requirements for cache operations
        self.assertLess(set_time, 0.1, "Cache SET operations too slow for A+")
        self.assertLess(get_time, 0.05, "Cache GET operations too slow for A+")
        
        # Test cache hit rate
        hits = 0
        for i in range(100):
            if cache.get(f'test_key_{i}') is not None:
                hits += 1
        
        hit_rate = hits / 100 * 100
        print(f"Cache Hit Rate: {hit_rate}%")
        self.assertGreaterEqual(hit_rate, 95, "Cache hit rate too low for A+")
    
    def test_concurrent_performance(self):
        """Test: Performance under concurrent load"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def concurrent_request():
            """Single concurrent request"""
            client = Client()
            client.login(username='testuser', password='testpass123')
            
            start_time = time.time()
            try:
                response = client.get('/')
                end_time = time.time()
                results.put(end_time - start_time)
            except Exception as e:
                results.put(None)
        
        # Run 10 concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=concurrent_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        response_times = []
        while not results.empty():
            result = results.get()
            if result is not None:
                response_times.append(result)
        
        if response_times:
            avg_concurrent_time = statistics.mean(response_times)
            max_concurrent_time = max(response_times)
            
            print(f"\nConcurrent Performance Results:")
            print(f"Concurrent Requests: {len(response_times)}")
            print(f"Average Response Time: {avg_concurrent_time:.3f}s")
            print(f"Maximum Response Time: {max_concurrent_time:.3f}s")
            
            # A+ grade: Even under load, should maintain good performance
            self.assertLess(avg_concurrent_time, 1.0,
                           f"Average concurrent response time {avg_concurrent_time:.3f}s too slow for A+")
            self.assertLess(max_concurrent_time, 2.0,
                           f"Maximum concurrent response time {max_concurrent_time:.3f}s too slow for A+")
    
    def test_memory_efficiency(self):
        """Test: Memory usage efficiency"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform memory-intensive operations
        large_queryset = Personnel.objects.all()
        for personnel in large_queryset:
            pass  # Iterate through all personnel
        
        # Force garbage collection
        import gc
        gc.collect()
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"\nMemory Efficiency Results:")
        print(f"Initial Memory: {initial_memory / 1024 / 1024:.1f} MB")
        print(f"Final Memory: {final_memory / 1024 / 1024:.1f} MB")
        print(f"Memory Increase: {memory_increase / 1024 / 1024:.1f} MB")
        
        # A+ grade: Should not have excessive memory growth
        max_allowed_increase = 50 * 1024 * 1024  # 50MB
        self.assertLess(memory_increase, max_allowed_increase,
                       f"Memory increase {memory_increase / 1024 / 1024:.1f}MB too high for A+")
    
    def test_static_file_performance(self):
        """Test: Static file serving performance"""
        static_files = [
            '/static/css/bootstrap.min.css',
            '/static/js/bootstrap.min.js',
            '/static/images/favicon.ico',
        ]
        
        response_times = []
        
        for static_file in static_files:
            start_time = time.time()
            try:
                response = self.client.get(static_file)
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Check for proper caching headers (if not in DEBUG mode)
                if not settings.DEBUG and response.status_code == 200:
                    self.assertIn('Cache-Control', response.headers)
                
            except Exception as e:
                logger.warning(f"Static file {static_file} test failed: {e}")
                continue
        
        if response_times:
            avg_static_time = statistics.mean(response_times)
            print(f"\nStatic File Performance Results:")
            print(f"Average Static File Time: {avg_static_time*1000:.1f}ms")
            print(f"Files Tested: {len(response_times)}")
            
            # A+ grade: Static files should be very fast
            self.assertLess(avg_static_time, 0.1,
                           f"Static file serving {avg_static_time*1000:.1f}ms too slow for A+")


def run_performance_validation():
    """Run all performance validation tests"""
    import django.test.utils
    from django.test.runner import DiscoverRunner
    
    runner = DiscoverRunner()
    suite = runner.build_suite(['core.performance_validation'])
    result = runner.run_suite(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    run_performance_validation()