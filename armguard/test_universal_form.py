#!/usr/bin/env python
"""
Test script for UniversalForm
"""
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from admin.forms import UniversalForm
from django.contrib.auth.models import User
from personnel.models import Personnel
from users.models import UserProfile

def test_universal_form():
    print("=== Testing UniversalForm ===")
    
    # Clean up any existing test data
    User.objects.filter(username='test_universal').delete()
    Personnel.objects.filter(serial='TEST001').delete()
    
    # Test data for creating user + personnel
    test_data = {
        'operation_type': 'create_user_with_personnel',
        'username': 'test_universal',
        'first_name': 'Test',
        'last_name': 'User',
        'email': 'test@example.com',
        'password': 'TestPass123!',
        'confirm_password': 'TestPass123!',
        'role': 'regular',
        'group': 'HAS',
        'phone_number': '09123456789',
        'surname': 'User',
        'firstname': 'Test',
        'middle_initial': 'T',
        'rank': 'AM',
        'serial': 'TEST001',
        'personnel_group': 'HAS',
        'tel': '09123456789',
        'personnel_status': 'Active'
    }
    
    print("1. Testing form validation...")
    form = UniversalForm(test_data)
    
    if form.is_valid():
        print("✅ Form validation PASSED")
        print(f"   - Tel converted: {test_data['tel']} → {form.cleaned_data['tel']}")
        
        print("2. Testing form save...")
        try:
            user, personnel = form.save()
            print("✅ Form save PASSED")
            print(f"   - User created: {user.username} ({user.first_name} {user.last_name})")
            print(f"   - Personnel created: {personnel.firstname} {personnel.surname}")
            print(f"   - Personnel rank: {personnel.rank}, group: {personnel.group}")
            print(f"   - Personnel tel: {personnel.tel}")
            print(f"   - Personnel classification: {personnel.classification}")
            
            # Check UserProfile
            profile = user.userprofile
            print(f"   - UserProfile group: {profile.group}")
            print(f"   - UserProfile phone: {profile.phone_number}")
            
        except Exception as e:
            print(f"❌ Form save FAILED: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("❌ Form validation FAILED")
        print(f"   - Errors: {form.errors}")
    
    print("\n=== Test Complete ===")

if __name__ == '__main__':
    test_universal_form()