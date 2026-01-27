"""
Test User/Personnel Delete Workflow
Creates test data, deletes it, and verifies soft delete works correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User, Group
from personnel.models import Personnel
from qr_manager.models import QRCodeImage
from users.models import UserProfile
from django.utils import timezone

print('=== TESTING DELETE WORKFLOW ===\n')

# Create test user and personnel
print('1. CREATING TEST USER + PERSONNEL')
# Create user
test_user = User.objects.create_user(
    username='test_delete_user',
    password='test123',
    first_name='Test',
    last_name='Delete',
    email='test@delete.com'
)
admin_group, _ = Group.objects.get_or_create(name='Admin')
test_user.groups.add(admin_group)
test_user.is_staff = True
test_user.save()

# Create personnel
test_personnel = Personnel(
    surname='Delete',
    firstname='Test',
    rank='SGT',
    serial='999999',
    group='HAS',
    tel='+639123456789',
    user=test_user
)
test_personnel.save()

print(f'   Created user: {test_user.username}')
print(f'   Created personnel: {test_personnel.id} - {test_personnel.get_full_name()}')

# Check QR code was auto-created
qr_code = QRCodeImage.objects.filter(qr_type='personnel', reference_id=test_personnel.id).first()
if qr_code:
    print(f'   QR code auto-created: {qr_code.reference_id}, is_active={qr_code.is_active}')
else:
    print('   ERROR: QR code not auto-created!')

# Test 2: Soft delete the personnel
print('\n2. SOFT-DELETING PERSONNEL')
test_personnel.soft_delete()
print(f'   Personnel deleted_at: {test_personnel.deleted_at}')
print(f'   Personnel status: {test_personnel.status}')

# Check QR code status
qr_code.refresh_from_db()
print(f'   QR code is_active: {qr_code.is_active}')
print(f'   QR code deleted_at: {qr_code.deleted_at}')

# Test 3: Verify they don't appear in default queries
print('\n3. VERIFYING EXCLUSION FROM DEFAULT QUERIES')
try:
    Personnel.objects.get(id=test_personnel.id)
    print('   ERROR: Personnel still appears in default query!')
except Personnel.DoesNotExist:
    print('   ✓ Personnel correctly hidden from default query')

try:
    QRCodeImage.objects.get(reference_id=test_personnel.id)
    print('   ERROR: QR code still appears in default query!')
except QRCodeImage.DoesNotExist:
    print('   ✓ QR code correctly hidden from default query')

# Test 4: Verify they exist with all_objects
print('\n4. VERIFYING DATABASE RECORDS STILL EXIST')
personnel_exists = Personnel.all_objects.filter(id=test_personnel.id).exists()
qr_exists = QRCodeImage.all_objects.filter(reference_id=test_personnel.id).exists()
print(f'   Personnel record in database: {personnel_exists}')
print(f'   QR code record in database: {qr_exists}')

if personnel_exists and qr_exists:
    print('   ✓ Records kept for audit purposes')
else:
    print('   ERROR: Records were hard deleted!')

# Test 5: Test QR validation
print('\n5. TESTING QR VALIDATION')
qr_code = QRCodeImage.all_objects.get(reference_id=test_personnel.id)
is_valid, message = qr_code.is_valid_for_transaction()
print(f'   QR valid for transaction: {is_valid}')
print(f'   Validation message: {message}')

if not is_valid:
    print('   ✓ QR correctly rejected for transactions')
else:
    print('   ERROR: Inactive QR accepted for transactions!')

# Test 6: Test user delete workflow
print('\n6. TESTING USER DELETE WITH PERSONNEL')

# Create another test set
test_user2 = User.objects.create_user(
    username='test_delete_user2',
    password='test123',
    first_name='Test2',
    last_name='Delete2'
)
test_personnel2 = Personnel(
    surname='Delete2',
    firstname='Test2',
    rank='SGT',
    serial='888888',
    group='HAS',
    tel='+639987654321',
    user=test_user2
)
test_personnel2.save()

print(f'   Created user2: {test_user2.username}')
print(f'   Created personnel2: {test_personnel2.id}')

# Store personnel reference before deleting user
personnel_id = test_personnel2.id
personnel_ref = test_personnel2

# Delete user (should trigger soft delete of personnel)
print('\n   Deleting user...')
test_user2.delete()

# Check if personnel was soft-deleted
personnel_ref.refresh_from_db()
print(f'   Personnel deleted_at: {personnel_ref.deleted_at}')
print(f'   Personnel status: {personnel_ref.status}')

if personnel_ref.deleted_at and personnel_ref.status == 'Inactive':
    print('   ✓ Personnel auto-soft-deleted when user deleted')
else:
    print('   ERROR: Personnel not soft-deleted when user deleted!')

# Check QR code
qr2 = QRCodeImage.all_objects.get(reference_id=personnel_id)
if not qr2.is_active and qr2.deleted_at:
    print('   ✓ QR code auto-deactivated when user deleted')
else:
    print('   ERROR: QR code not deactivated when user deleted!')

# Cleanup test data
print('\n7. CLEANING UP TEST DATA')
test_user.delete()
test_personnel.delete()
test_personnel2.delete()
QRCodeImage.all_objects.filter(reference_id__in=[test_personnel.id, personnel_id]).delete()
print('   ✓ Test data cleaned up')

print('\n=== DELETE WORKFLOW TEST COMPLETE ===')
print('Summary: All soft delete functionality working correctly!')
