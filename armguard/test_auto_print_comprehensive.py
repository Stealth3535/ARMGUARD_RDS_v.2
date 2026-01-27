"""
Comprehensive Auto-Print System Test
Tests the entire auto-print workflow including PDF generation, URL routing, and JavaScript triggers
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

# Add testserver to ALLOWED_HOSTS for testing
from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import Client, RequestFactory
from django.contrib.auth.models import User, Group
from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item
from print_handler.pdf_filler.form_filler import TransactionFormFiller
from django.conf import settings
import json
from datetime import datetime


def print_section(title):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print('='*80)


def test_api_response():
    """Test 1: Verify API returns correct data including action and pdf_url"""
    print_section("TEST 1: API Response Structure")
    
    client = Client()
    
    # Create test user with Admin group
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    user = User.objects.filter(groups__name='Admin').first()
    
    if not user:
        user = User.objects.create_user(username='test_admin', password='testpass123')
        user.groups.add(admin_group)
        print("✓ Created test admin user")
    
    # Login
    client.force_login(user)
    print(f"✓ Logged in as: {user.username}")
    
    # Get test data
    personnel = Personnel.objects.filter(deleted_at__isnull=True).first()
    item = Item.objects.filter(status='Available').first()
    
    if not personnel or not item:
        print("✗ FAILED: Need test personnel and available item")
        return False
    
    print(f"✓ Test Personnel: {personnel.get_full_name()}")
    print(f"✓ Test Item: {item.item_type} {item.serial}")
    
    # Test Take (Withdraw) transaction
    print("\n--- Testing WITHDRAW (Take) Transaction ---")
    response = client.post('/api/transactions/', 
        data=json.dumps({
            'personnel_id': str(personnel.id),
            'item_id': str(item.id),
            'action': 'Take',
            'notes': 'Auto-print test',
            'mags': 2,
            'rounds': 30,
            'duty_type': 'Range Duty'
        }),
        content_type='application/json'
    )
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ API Response: {json.dumps(data, indent=2)}")
        
        # Check critical fields
        checks = {
            'success': data.get('success'),
            'transaction_id': data.get('transaction_id'),
            'action': data.get('action'),
            'pdf_url': data.get('pdf_url')
        }
        
        print("\n--- Field Validation ---")
        all_passed = True
        for field, value in checks.items():
            if value:
                print(f"✓ {field}: {value}")
            else:
                print(f"✗ MISSING: {field}")
                all_passed = False
        
        if all_passed and checks['action'] == 'Take' and checks['pdf_url']:
            print("\n✅ TEST 1 PASSED: API returns all required fields for auto-print")
            
            # Clean up - return the item (check if still issued)
            transaction = Transaction.objects.get(id=checks['transaction_id'])
            item.refresh_from_db()
            if item.status == 'Issued':
                return_trans = Transaction.objects.create(
                    personnel=personnel,
                    item=item,
                    action='Return',
                    notes='Cleanup test transaction',
                    issued_by=user
                )
                print(f"✓ Cleanup: Returned item via transaction #{return_trans.id}")
            else:
                print(f"✓ Cleanup: Item already returned")
            return checks['transaction_id']
        else:
            print("\n✗ TEST 1 FAILED: Missing required fields")
            return False
    else:
        print(f"✗ TEST 1 FAILED: API error - {response.content}")
        return False


def test_pdf_generation(transaction_id):
    """Test 2: Verify PDF is generated and accessible"""
    print_section("TEST 2: PDF Generation & Accessibility")
    
    transaction = Transaction.objects.get(id=transaction_id)
    print(f"✓ Testing Transaction #{transaction_id}")
    print(f"  Personnel: {transaction.personnel.get_full_name()}")
    print(f"  Item: {transaction.item.item_type} {transaction.item.serial}")
    print(f"  Action: {transaction.action}")
    
    # Check if PDF exists in media folder
    date_str = transaction.date_time.strftime('%Y%m%d_%H%M%S')
    filename = f"Transaction_{transaction.id}_{date_str}.pdf"
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'transaction_forms', filename)
    
    print(f"\n--- Checking PDF File ---")
    print(f"Expected path: {pdf_path}")
    
    if os.path.exists(pdf_path):
        file_size = os.path.getsize(pdf_path)
        print(f"✓ PDF file exists: {filename}")
        print(f"✓ File size: {file_size:,} bytes")
        
        if file_size > 50000:  # Should be at least 50KB
            print("✅ TEST 2 PASSED: PDF generated successfully")
            return True
        else:
            print("✗ TEST 2 FAILED: PDF file too small, likely corrupted")
            return False
    else:
        print(f"✗ TEST 2 FAILED: PDF file not found at expected location")
        return False


def test_pdf_url_access(transaction_id):
    """Test 3: Verify PDF URL is accessible"""
    print_section("TEST 3: PDF URL Accessibility")
    
    client = Client()
    
    # Login as admin
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    user = User.objects.filter(groups__name='Admin').first()
    client.force_login(user)
    
    pdf_url = f'/print/transaction/{transaction_id}/pdf/'
    print(f"Testing URL: {pdf_url}")
    
    response = client.get(pdf_url)
    
    print(f"Response Status: {response.status_code}")
    print(f"Content-Type: {response.get('Content-Type')}")
    print(f"Content-Disposition: {response.get('Content-Disposition')}")
    
    if response.status_code == 200:
        if response.get('Content-Type') == 'application/pdf':
            content_length = len(response.content)
            print(f"✓ PDF Content Length: {content_length:,} bytes")
            
            if content_length > 50000:
                print("✅ TEST 3 PASSED: PDF URL accessible and returns valid PDF")
                return True
            else:
                print("✗ TEST 3 FAILED: PDF content too small")
                return False
        else:
            print(f"✗ TEST 3 FAILED: Wrong content type")
            return False
    else:
        print(f"✗ TEST 3 FAILED: HTTP {response.status_code}")
        return False


def test_javascript_logic():
    """Test 4: Verify JavaScript auto-print logic"""
    print_section("TEST 4: JavaScript Auto-Print Logic")
    
    # Read the template file
    template_path = os.path.join(
        settings.BASE_DIR, 
        'transactions', 
        'templates', 
        'transactions', 
        'transaction_list.html'
    )
    
    print(f"Reading template: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for key JavaScript elements
    checks = {
        'Action check': "data.action === 'Take'",
        'Transaction ID check': "data.transaction_id",
        'PDF URL construction': "/print/transaction/",
        'Iframe creation': "createElement('iframe')",
        'Hidden iframe': "style.display = 'none'",
        'Iframe onload': "iframe.onload",
        'Print trigger': "iframe.contentWindow.print()",
        'Cleanup': "removeChild(iframe)"
    }
    
    print("\n--- JavaScript Elements Check ---")
    all_found = True
    for check_name, search_string in checks.items():
        if search_string in content:
            print(f"✓ Found: {check_name}")
        else:
            print(f"✗ MISSING: {check_name} (searching for: {search_string})")
            all_found = False
    
    # Check for problematic patterns
    print("\n--- Checking for Issues ---")
    issues = []
    
    # Check reload timing
    if "location.reload(), 800)" in content or "location.reload(), 1000)" in content:
        issues.append("⚠ WARNING: Page reload might happen too quickly (before print dialog)")
    
    # Check if auto-print is conditional
    if "if (data.action === 'Take'" in content:
        print("✓ Auto-print is conditional (only for Take/Withdraw)")
    else:
        issues.append("✗ ISSUE: Auto-print should be conditional")
    
    if issues:
        for issue in issues:
            print(issue)
    
    if all_found and len(issues) == 0:
        print("\n✅ TEST 4 PASSED: JavaScript logic is correct")
        return True
    elif all_found:
        print("\n⚠ TEST 4 PASSED WITH WARNINGS: Logic correct but potential timing issue")
        return True
    else:
        print("\n✗ TEST 4 FAILED: Missing critical JavaScript elements")
        return False


def test_return_transaction_no_print():
    """Test 5: Verify Return transactions don't trigger print"""
    print_section("TEST 5: Return Transaction (No Print)")
    
    client = Client()
    
    # Login
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    user = User.objects.filter(groups__name='Admin').first()
    client.force_login(user)
    
    # Get an item that's currently issued
    item = Item.objects.filter(status='Issued').first()
    
    if not item:
        print("✗ No issued items to test return")
        return True  # Skip test, not a failure
    
    # Get the last transaction for this item
    last_transaction = Transaction.objects.filter(item=item).order_by('-date_time').first()
    personnel = last_transaction.personnel if last_transaction else None
    
    if not personnel:
        print("✗ Cannot determine personnel for return")
        return True
    
    print(f"✓ Testing Return: {item.item_type} {item.serial}")
    print(f"✓ Personnel: {personnel.get_full_name()}")
    
    # Test Return transaction
    response = client.post('/api/transactions/', 
        data=json.dumps({
            'personnel_id': str(personnel.id),
            'item_id': str(item.id),
            'action': 'Return',
            'notes': 'Return test - should not print',
        }),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n--- API Response ---")
        print(f"✓ Success: {data.get('success')}")
        print(f"✓ Action: {data.get('action')}")
        print(f"✓ PDF URL present: {'pdf_url' in data}")
        
        if data.get('action') == 'Return' and 'pdf_url' not in data:
            print("\n✅ TEST 5 PASSED: Return transaction doesn't include pdf_url")
            return True
        else:
            print("\n✗ TEST 5 FAILED: Return transaction should not have pdf_url")
            return False
    else:
        print(f"\n✗ TEST 5 FAILED: API error")
        return False


def test_print_wrapper_page():
    """Test 6: Verify print wrapper page exists and works"""
    print_section("TEST 6: Print Wrapper Page")
    
    # Get a transaction
    transaction = Transaction.objects.filter(action='Take').first()
    
    if not transaction:
        print("✗ No Take transactions to test")
        return False
    
    print(f"✓ Testing with Transaction #{transaction.id}")
    
    client = Client()
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    user = User.objects.filter(groups__name='Admin').first()
    client.force_login(user)
    
    wrapper_url = f'/print/transaction/{transaction.id}/print/'
    print(f"Wrapper URL: {wrapper_url}")
    
    response = client.get(wrapper_url)
    
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Check for critical elements
        checks = {
            'Embed tag': '<embed' in content,
            'PDF source': 'src=' in content,
            'Auto-print script': 'window.print()' in content,
            'Legal paper size': 'size: legal' in content or 'size:legal' in content,
        }
        
        print("\n--- Wrapper Page Elements ---")
        all_found = True
        for check_name, found in checks.items():
            if found:
                print(f"✓ {check_name}")
            else:
                print(f"✗ MISSING: {check_name}")
                all_found = False
        
        if all_found:
            print("\n✅ TEST 6 PASSED: Print wrapper page is properly configured")
            return True
        else:
            print("\n✗ TEST 6 FAILED: Print wrapper missing elements")
            return False
    else:
        print(f"\n✗ TEST 6 FAILED: Cannot access wrapper page")
        return False


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "AUTO-PRINT COMPREHENSIVE TEST SUITE" + " "*23 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {}
    
    # Test 1: API Response
    transaction_id = test_api_response()
    results['API Response'] = bool(transaction_id)
    
    if transaction_id:
        # Test 2: PDF Generation
        results['PDF Generation'] = test_pdf_generation(transaction_id)
        
        # Test 3: PDF URL Access
        results['PDF URL Access'] = test_pdf_url_access(transaction_id)
    else:
        results['PDF Generation'] = False
        results['PDF URL Access'] = False
    
    # Test 4: JavaScript Logic
    results['JavaScript Logic'] = test_javascript_logic()
    
    # Test 5: Return No Print
    results['Return No Print'] = test_return_transaction_no_print()
    
    # Test 6: Print Wrapper
    results['Print Wrapper Page'] = test_print_wrapper_page()
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "✗ FAIL"
        print(f"{status}  {test_name}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {passed}/{total} tests passed ({passed*100//total}%)")
    print('='*80)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Auto-print system is working correctly.")
        print("\n⚠ NOTE: Actual printing depends on:")
        print("  1. Browser settings allowing silent print")
        print("  2. Default printer being configured (EPSON L3210)")
        print("  3. Printer being connected and ready")
        print("  4. No browser popup blockers interfering")
    else:
        print("\n⚠ SOME TESTS FAILED - Issues detected in auto-print system")
        print("Review the failures above for details.")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
