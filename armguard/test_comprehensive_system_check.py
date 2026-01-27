"""
Comprehensive System Test - Find all issues
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from qr_manager.models import QRCodeImage
from django.contrib.auth.models import User
from inventory.models import Item
from transactions.models import Transaction

print('=== COMPREHENSIVE SYSTEM TEST ===\n')

# Test 1: Check all personnel records
print('1. PERSONNEL RECORDS')
print(f'   Active personnel: {Personnel.objects.count()}')
print(f'   Deleted personnel: {Personnel.all_objects.filter(deleted_at__isnull=False).count()}')
print(f'   Total personnel: {Personnel.all_objects.count()}')

deleted_list = Personnel.all_objects.filter(deleted_at__isnull=False)
if deleted_list:
    print('   Deleted records:')
    for p in deleted_list:
        print(f'     - {p.id}: {p.get_full_name()}, deleted_at={p.deleted_at}')

# Test 2: Check all QR codes
print('\n2. QR CODE RECORDS')
print(f'   Active QR codes: {QRCodeImage.objects.count()}')
print(f'   Inactive QR codes: {QRCodeImage.all_objects.filter(is_active=False).count()}')
print(f'   Total QR codes: {QRCodeImage.all_objects.count()}')

inactive_qr = QRCodeImage.all_objects.filter(is_active=False)
if inactive_qr:
    print('   Inactive QR codes:')
    for qr in inactive_qr:
        print(f'     - {qr.reference_id}: deleted_at={qr.deleted_at}')

# Test 3: Check orphaned QR codes (QR without personnel)
print('\n3. ORPHANED QR CODES CHECK')
all_qr = QRCodeImage.all_objects.filter(qr_type='personnel')
orphaned = []
for qr in all_qr:
    try:
        Personnel.all_objects.get(id=qr.reference_id)
    except Personnel.DoesNotExist:
        orphaned.append(qr.reference_id)
        print(f'   WARNING: Orphaned QR {qr.reference_id}')

if not orphaned:
    print('   ✓ No orphaned QR codes found')
else:
    print(f'   Total orphaned: {len(orphaned)}')

# Test 4: Check personnel without user accounts
print('\n4. PERSONNEL WITHOUT USER ACCOUNTS')
no_user = Personnel.objects.filter(user__isnull=True)
print(f'   Personnel without users: {no_user.count()}')
if no_user.count() > 0:
    for p in no_user[:5]:  # Show first 5
        print(f'     - {p.id}: {p.get_full_name()}')

# Test 5: Check users
print('\n5. USER ACCOUNTS')
print(f'   Total users: {User.objects.count()}')
print(f'   Superusers: {User.objects.filter(is_superuser=True).count()}')
print(f'   Admin group: {User.objects.filter(groups__name="Admin").count()}')
print(f'   Armorer group: {User.objects.filter(groups__name="Armorer").count()}')

# Test 6: Check deleted personnel still linked to active users
print('\n6. INTEGRITY CHECK: Deleted personnel with active users')
deleted_personnel = Personnel.all_objects.filter(deleted_at__isnull=False)
integrity_issues = []
for p in deleted_personnel:
    if p.user and p.user.is_active:
        integrity_issues.append(f'{p.id} linked to active user {p.user.username}')
        print(f'   ERROR: {p.id} is deleted but linked to active user {p.user.username}')

if not integrity_issues:
    print('   ✓ No integrity issues found')

# Test 7: Check QR code validation
print('\n7. QR CODE VALIDATION TEST')
test_qr = QRCodeImage.all_objects.filter(is_active=False).first()
if test_qr:
    is_valid, message = test_qr.is_valid_for_transaction()
    print(f'   Testing inactive QR {test_qr.reference_id}:')
    print(f'     Valid for transaction: {is_valid}')
    print(f'     Message: {message}')
else:
    print('   No inactive QR codes to test')

# Test 8: Check for missing QR codes
print('\n8. MISSING QR CODES CHECK')
missing_qr = []
for p in Personnel.objects.all()[:10]:  # Check first 10 active
    qr_exists = QRCodeImage.objects.filter(qr_type='personnel', reference_id=p.id).exists()
    if not qr_exists:
        missing_qr.append(p.id)
        print(f'   WARNING: Personnel {p.id} ({p.get_full_name()}) has no QR code')

if not missing_qr:
    print('   ✓ All active personnel have QR codes')

# Test 9: Check transaction integrity
print('\n9. TRANSACTION INTEGRITY CHECK')
total_transactions = Transaction.objects.count()
print(f'   Total transactions: {total_transactions}')

if total_transactions > 0:
    # Check for transactions with deleted personnel
    transactions_with_deleted = 0
    for txn in Transaction.objects.all()[:20]:  # Check first 20
        if txn.personnel and txn.personnel.deleted_at:
            transactions_with_deleted += 1
    
    if transactions_with_deleted > 0:
        print(f'   WARNING: {transactions_with_deleted} transactions reference deleted personnel')
    else:
        print('   ✓ No transactions reference deleted personnel')

print('\n=== SUMMARY ===')
issues_found = len(orphaned) + len(integrity_issues) + len(missing_qr)
if issues_found == 0:
    print('✓ No critical issues found!')
else:
    print(f'⚠ Found {issues_found} issue(s) that need attention')

print('\n=== TEST COMPLETE ===')
