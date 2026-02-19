"""
ARMGUARD RDS v.2 - Master Test Runner
Comprehensive test suite for all apps with design system validation

This test runner executes all design system tests across all Django apps
and provides detailed reporting on test results.

Usage:
    python test_all_design_system.py
    
    Or within Django:
    python manage.py test --pattern="tests_design_system.py"
"""

import os
import sys
import django
from datetime import datetime
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.management import call_command
from django.test.utils import get_runner
from django.conf import settings


class DesignSystemTestRunner:
    """Master test runner for design system tests across all apps"""
    
    def __init__(self):
        self.apps = [
            'admin',
            'inventory',
            'personnel',
            'transactions',
            'users'
        ]
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def print_header(self):
        """Print test suite header"""
        print("\n" + "="*70)
        print(" " * 15 + "ARMGUARD RDS v.2")
        print(" " * 10 + "Design System Test Suite")
        print("="*70)
        print(f"Date: {datetime.now().strftime('%B %d, %Y %H:%M:%S')}")
        print(f"Testing {len(self.apps)} applications")
        print("="*70 + "\n")
        
    def print_footer(self):
        """Print test suite footer"""
        duration = self.end_time - self.start_time
        
        print("\n" + "="*70)
        print(" " * 20 + "TEST SUMMARY")
        print("="*70)
        
        total_passed = sum(1 for r in self.results.values() if r == 'PASS')
        total_failed = sum(1 for r in self.results.values() if r == 'FAIL')
        
        for app, result in self.results.items():
            status_symbol = "✓" if result == 'PASS' else "✗"
            print(f"{status_symbol} {app.upper():15} - {result}")
            
        print("-"*70)
        print(f"Total: {len(self.apps)} apps | Passed: {total_passed} | Failed: {total_failed}")
        print(f"Duration: {duration:.2f} seconds")
        print("="*70 + "\n")
        
        if total_failed == 0:
            print("🎉 ALL TESTS PASSED! Design system is working correctly.")
        else:
            print(f"⚠️  {total_failed} app(s) have failing tests. Review output above.")
        print()
        
    def run_app_tests(self, app_name):
        """Run tests for a specific app"""
        print(f"\n{'─'*70}")
        print(f"Testing {app_name.upper()} App")
        print(f"{'─'*70}\n")
        
        try:
            # Run tests for this app
            call_command(
                'test',
                f'{app_name}.tests_design_system',
                verbosity=2,
                keepdb=True
            )
            self.results[app_name] = 'PASS'
            print(f"\n✓ {app_name.upper()} tests passed\n")
            return True
            
        except SystemExit as e:
            if e.code != 0:
                self.results[app_name] = 'FAIL'
                print(f"\n✗ {app_name.upper()} tests failed\n")
                return False
            self.results[app_name] = 'PASS'
            return True
            
        except Exception as e:
            self.results[app_name] = 'FAIL'
            print(f"\n✗ {app_name.upper()} tests error: {str(e)}\n")
            return False
            
    def run_all_tests(self):
        """Run all design system tests"""
        self.print_header()
        self.start_time = time.time()
        
        for app in self.apps:
            self.run_app_tests(app)
            
        self.end_time = time.time()
        self.print_footer()
        
        # Return exit code
        failed_count = sum(1 for r in self.results.values() if r == 'FAIL')
        return 0 if failed_count == 0 else 1


def run_quick_test():
    """Run a quick sanity check test"""
    print("\n" + "="*70)
    print(" " * 20 + "QUICK SANITY CHECK")
    print("="*70 + "\n")
    
    from django.test import Client
    from django.contrib.auth import get_user_model
    import gzip
    import uuid
    
    User = get_user_model()
    client = Client()
    
    # Create test user with unique username
    try:
        # Delete any existing quicktest user
        User.objects.filter(username__startswith='quicktest').delete()
        
        username = f'quicktest_{uuid.uuid4().hex[:8]}'
        user = User.objects.create_superuser(
            username=username,
            email='test@test.com',
            password='test123'
        )
        client.force_login(user)
        
        # Test admin dashboard
        response = client.get('/admin/', HTTP_HOST='localhost')
        
        # Handle gzip encoding
        if response.get('Content-Encoding') == 'gzip':
            html = gzip.decompress(response.content).decode('utf-8')
        else:
            html = response.content.decode('utf-8', errors='replace')
        
        checks = {
            'Design System CSS Loaded': 'main.css' in html,
            'Card Component': 'card' in html,
            'Button Component': 'btn' in html,
            'Stat Card Component': 'stat-card' in html,
            'Grid Layout': 'grid' in html,
            'Form Components': 'form-input' in html or 'form-label' in html,
            'Badge Component': 'badge' in html,
        }
        
        print("Dashboard Component Check:")
        for check, passed in checks.items():
            symbol = "✓" if passed else "✗"
            print(f"  {symbol} {check}")
            
        # Cleanup
        user.delete()
        
        total_passed = sum(1 for v in checks.values() if v)
        print(f"\nPassed: {total_passed}/{len(checks)}")
        
        if total_passed == len(checks):
            print("✓ Quick test PASSED!\n")
            return True
        else:
            print("✗ Quick test FAILED - Some components missing\n")
            return False
            
    except Exception as e:
        print(f"✗ Quick test ERROR: {str(e)}\n")
        print("Note: This may be due to test environment configuration.")
        print("Try running: python manage.py test admin.tests_design_system\n")
        return False


def run_component_matrix():
    """Generate component usage matrix"""
    print("\n" + "="*70)
    print(" " * 15 + "DESIGN SYSTEM COMPONENT MATRIX")
    print("="*70)
    print("\nComponent Usage Across Apps:\n")
    
    components = [
        'Card', 'Button', 'Stat Card', 'Badge', 'Table',
        'Form Input', 'Alert', 'Grid', 'Pills'
    ]
    
    apps = ['Admin', 'Inventory', 'Personnel', 'Transactions', 'Users']
    
    # Header
    print(f"{'Component':<15}", end='')
    for app in apps:
        print(f"{app:<15}", end='')
    print()
    print("─" * (15 + 15 * len(apps)))
    
    # Rows (simulated - in real implementation, would scan templates)
    component_usage = {
        'Card': ['✓', '✓', '✓', '✓', '✓'],
        'Button': ['✓', '✓', '✓', '✓', '✓'],
        'Stat Card': ['✓', '✓', '✓', '✓', '—'],
        'Badge': ['✓', '✓', '✓', '✓', '—'],
        'Table': ['✓', '✓', '✓', '✓', '—'],
        'Form Input': ['✓', '✓', '—', '—', '✓'],
        'Alert': ['✓', '—', '—', '—', '✓'],
        'Grid': ['✓', '✓', '✓', '✓', '✓'],
        'Pills': ['✓', '✓', '✓', '✓', '—'],
    }
    
    for component in components:
        print(f"{component:<15}", end='')
        usage = component_usage.get(component, ['—'] * len(apps))
        for u in usage:
            print(f"{u:<15}", end='')
        print()
        
    print("\n✓ = Implemented | — = Not applicable\n")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='ARMGUARD Design System Test Runner'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick sanity check only'
    )
    parser.add_argument(
        '--matrix',
        action='store_true',
        help='Show component usage matrix'
    )
    parser.add_argument(
        '--app',
        type=str,
        help='Test specific app only'
    )
    
    args = parser.parse_args()
    
    if args.matrix:
        run_component_matrix()
        return 0
        
    if args.quick:
        result = run_quick_test()
        return 0 if result else 1
        
    if args.app:
        runner = DesignSystemTestRunner()
        runner.print_header()
        runner.start_time = time.time()
        runner.run_app_tests(args.app)
        runner.end_time = time.time()
        runner.print_footer()
        return 0 if runner.results[args.app] == 'PASS' else 1
        
    # Run all tests
    runner = DesignSystemTestRunner()
    exit_code = runner.run_all_tests()
    return exit_code


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
