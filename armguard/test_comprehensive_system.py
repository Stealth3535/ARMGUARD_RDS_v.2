#!/usr/bin/env python
"""
Comprehensive System Test - Verify Registration & Data Persistence
Tests: User creation, Personnel creation, Profile synchronization, Data integrity
"""
import os
import django
import time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin.forms import UniversalForm
from django.contrib.auth.models import User, Group
from personnel.models import Personnel
from users.models import UserProfile

def cleanup():
    """Clean up test data"""
    User.objects.filter(username__startswith='systest_').delete()
    Personnel.objects.filter(serial__in=['SYS001', 'OFF001', 'ARM001']).delete()

def test_create_user_with_personnel():
    """Test 1: Create User + Personnel (Full Registration)"""
    print("\n=== TEST 1: Create User + Personnel ===")
    
    data = {
        'operation_type': 'create_user_with_personnel',
        'username': 'systest_enlisted',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'password': 'Pass123!',
        'confirm_password': 'Pass123!',
        'role': 'regular',
        'group': 'HAS',
        'phone_number': '09171234567',
        'surname': 'Doe',
        'firstname': 'John',
        'middle_initial': 'D',
        'rank': 'AM',  # Airman (enlisted rank)
        'serial': 'SYS001',
        'personnel_group': 'HAS',
        'tel': '09171234567',
        'personnel_status': 'Active'
    }
    
    form = UniversalForm(data)
    if not form.is_valid():
        print(f"❌ FAILED: Form validation errors: {form.errors}")
        return False
    
    user, personnel = form.save()
    
    # Verify User
    user_db = User.objects.filter(username='systest_enlisted').first()
    if not user_db:
        print("❌ FAILED: User not saved to database")
        return False
    
    # Verify Personnel
    personnel_db = Personnel.objects.filter(serial='SYS001').first()
    if not personnel_db:
        print("❌ FAILED: Personnel not saved to database")
        return False
    
    # Verify UserProfile
    profile = UserProfile.objects.filter(user=user_db).first()
    if not profile:
        print("❌ FAILED: UserProfile not created")
        return False
    
    # Verify Links
    if personnel_db.user != user_db:
        print("❌ FAILED: Personnel not linked to User")
        return False
    
    # Verify Phone Conversion
    if personnel_db.tel != '+639171234567':
        print(f"❌ FAILED: Tel conversion failed. Got: {personnel_db.tel}")
        return False
    
    print(f"✅ PASSED: User '{user_db.username}' created")
    print(f"✅ PASSED: Personnel '{personnel_db.firstname} {personnel_db.surname}' (Serial: {personnel_db.serial}) created")
    print(f"✅ PASSED: UserProfile created with group: {profile.group}")
    print(f"✅ PASSED: Tel converted: 09171234567 → {personnel_db.tel}")
    print(f"✅ PASSED: User-Personnel link established")
    print(f"✅ PASSED: Classification: {personnel_db.classification}")
    return True

def test_create_officer():
    """Test 2: Create Officer Personnel"""
    print("\n=== TEST 2: Create Officer ===")
    time.sleep(0.5)  # Small delay to avoid ID collision
    
    data = {
        'operation_type': 'create_user_with_personnel',
        'username': 'systest_officer',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'password': 'Pass123!',
        'confirm_password': 'Pass123!',
        'role': 'admin',
        'group': '951st',
        'surname': 'Smith',
        'firstname': 'Jane',
        'middle_initial': 'S',
        'rank': '2LT',
        'serial': 'OFF001',  # Different serial to avoid ID collision
        'personnel_group': '951st',
        'tel': '09187654321',
        'personnel_status': 'Active'
    }
    
    form = UniversalForm(data)
    if not form.is_valid():
        print(f"❌ FAILED: {form.errors}")
        return False
    
    user, personnel = form.save()
    
    personnel_db = Personnel.objects.get(serial='OFF001')
    
    if personnel_db.classification != 'OFFICER':
        print(f"❌ FAILED: Classification should be OFFICER, got: {personnel_db.classification}")
        return False
    
    if not user.groups.filter(name='Admin').exists():
        print("❌ FAILED: User not added to Admin group")
        return False
    
    print(f"✅ PASSED: Officer created with rank {personnel_db.rank}")
    print(f"✅ PASSED: Classification: {personnel_db.classification}")
    print(f"✅ PASSED: User added to Admin group")
    return True

def test_create_armorer():
    """Test 3: Create Armorer"""
    print("\n=== TEST 3: Create Armorer ===")
    
    data = {
        'operation_type': 'create_user_with_personnel',
        'username': 'systest_armorer',
        'first_name': 'Bob',
        'last_name': 'Johnson',
        'password': 'Pass123!',
        'confirm_password': 'Pass123!',
        'role': 'armorer',
        'group': '952nd',
        'department': 'Armory Section',
        'surname': 'Johnson',
        'firstname': 'Bob',
        'rank': 'SGT',
        'serial': 'ARM001',  # Different serial
        'personnel_group': '952nd',
        'tel': '09199876543',
        'personnel_status': 'Active'
    }
    
    form = UniversalForm(data)
    if not form.is_valid():
        print(f"❌ FAILED: {form.errors}")
        return False
    
    user, personnel = form.save()
    
    print(f"DEBUG: User created: {user.username}")
    print(f"DEBUG: Role from form: {form.cleaned_data.get('role')}")
    print(f"DEBUG: User groups: {[g.name for g in user.groups.all()]}")
    
    if not user.groups.filter(name='Armorer').exists():
        print("❌ FAILED: User not added to Armorer group")
        return False
    
    try:
        profile = user.userprofile
        print(f"DEBUG: Profile.is_armorer = {profile.is_armorer}")
        print(f"DEBUG: Profile.group = {profile.group}")
        if not profile.is_armorer:
            print(f"❌ FAILED: UserProfile is_armorer = {profile.is_armorer}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Error accessing profile: {e}")
        return False
    
    print(f"✅ PASSED: Armorer created")
    print(f"✅ PASSED: User added to Armorer group")
    print(f"✅ PASSED: UserProfile.is_armorer = True")
    return True

def test_edit_user():
    """Test 4: Edit Existing User"""
    print("\n=== TEST 4: Edit User ===")
    
    user = User.objects.get(username='systest_enlisted')
    
    data = {
        'operation_type': 'edit_user',
        'edit_user_id': user.id,
        'username': 'systest_enlisted',
        'first_name': 'John_Updated',
        'last_name': 'Doe',
        'email': 'john.new@example.com',
        'role': 'regular',
        'group': '953rd',
        'phone_number': '+639281234567'
    }
    
    form = UniversalForm(data)
    if not form.is_valid():
        print(f"❌ FAILED: {form.errors}")
        return False
    
    updated_user, _ = form.save()
    user.refresh_from_db()
    
    if user.first_name != 'John_Updated':
        print(f"❌ FAILED: Name not updated. Got: {user.first_name}")
        return False
    
    if user.email != 'john.new@example.com':
        print(f"❌ FAILED: Email not updated")
        return False
    
    profile = user.userprofile
    if profile.group != '953rd':
        print(f"❌ FAILED: Group not updated. Got: {profile.group}")
        return False
    
    print(f"✅ PASSED: User updated successfully")
    print(f"✅ PASSED: Name: John → John_Updated")
    print(f"✅ PASSED: Group: HAS → 953rd")
    return True

def test_edit_personnel():
    """Test 5: Edit Personnel"""
    print("\n=== TEST 5: Edit Personnel ===")
    
    personnel = Personnel.objects.get(serial='SYS001')
    
    data = {
        'operation_type': 'edit_personnel',
        'edit_personnel_id': personnel.id,
        'surname': 'Doe',
        'firstname': 'John',
        'middle_initial': 'D',
        'rank': 'SGT',  # Updated to SGT (Sergeant)
        'serial': 'SYS001',
        'personnel_group': '951st',
        'tel': '+639171234567',
        'personnel_status': 'Active'
    }
    
    form = UniversalForm(data)
    if not form.is_valid():
        print(f"❌ FAILED: {form.errors}")
        return False
    
    _, updated_personnel = form.save()
    personnel.refresh_from_db()
    
    if personnel.rank != 'SGT':
        print(f"❌ FAILED: Rank not updated. Got: {personnel.rank}")
        return False
    
    if personnel.group != '951st':
        print(f"❌ FAILED: Group not updated. Got: {personnel.group}")
        return False
    
    print(f"✅ PASSED: Personnel updated")
    print(f"✅ PASSED: Rank: AM → SGT")
    print(f"✅ PASSED: Group: HAS → 951st")
    return True

def test_serial_uniqueness():
    """Test 6: Serial Number Uniqueness"""
    print("\n=== TEST 6: Serial Uniqueness ===")
    
    data = {
        'operation_type': 'create_personnel_only',
        'surname': 'Test',
        'firstname': 'Duplicate',
        'rank': 'AM',  # Use valid rank
        'serial': 'SYS001',  # Duplicate
        'personnel_group': 'HAS',
        'tel': '+639111111111',
        'personnel_status': 'Active'
    }
    
    form = UniversalForm(data)
    if form.is_valid():
        print("❌ FAILED: Duplicate serial allowed")
        return False
    
    if 'serial' not in form.errors:
        print("❌ FAILED: Serial error not detected")
        return False
    
    print("✅ PASSED: Duplicate serial rejected")
    print(f"✅ PASSED: Error message: {form.errors['serial']}")
    return True

def main():
    print("=" * 60)
    print("COMPREHENSIVE SYSTEM TEST - ARMGUARD REGISTRATION")
    print("=" * 60)
    
    cleanup()
    
    tests = [
        test_create_user_with_personnel,
        test_create_officer,
        test_create_armorer,
        test_edit_user,
        test_edit_personnel,
        test_serial_uniqueness
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - SYSTEM IS WORKING CORRECTLY")
        print("\n✅ DATA PERSISTENCE VERIFIED")
        print("✅ USER-PERSONNEL SYNCHRONIZATION VERIFIED")
        print("✅ VALIDATION WORKING CORRECTLY")
    else:
        print(f"\n⚠️ {failed} TEST(S) FAILED - REVIEW REQUIRED")
    
    cleanup()

if __name__ == '__main__':
    main()
