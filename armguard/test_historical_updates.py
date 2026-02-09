#!/usr/bin/env python3
"""
Test script to verify that Personnel historical updates are working correctly
after the django-simple-history integration fix.
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel
from admin.forms import UniversalForm
from django.test.client import RequestFactory
import json
from datetime import datetime

def test_personnel_historical_updates():
    """Test that personnel updates create proper historical records"""
    
    print("=== Testing Personnel Historical Updates ===\n")
    
    # Get the test personnel (Hermosa)
    try:
        personnel = Personnel.objects.get(id='PE-994360070226')
        print(f"Found test personnel: {personnel.get_full_name()}")
    except Personnel.DoesNotExist:
        print("Test personnel not found. Creating test data...")
        # Create test data if needed
        return False
    
    # Get or create test user for audit context
    test_user, created = User.objects.get_or_create(
        username='test_admin',
        defaults={
            'first_name': 'Test',
            'last_name': 'Admin',
            'email': 'test@admin.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    if created:
        test_user.set_password('test123')
        test_user.save()
        print(f"Created test user: {test_user.username}")
    
    # Record current historical count
    initial_history_count = personnel.history.count()
    print(f"Initial historical record count: {initial_history_count}")
    
    # Show current personnel data
    print(f"Current personnel data:")
    print(f"  Name: {personnel.surname}, {personnel.firstname} {personnel.middle_initial or ''}")
    print(f"  Rank: {personnel.rank}")
    print(f"  Tel: {personnel.tel}")
    print(f"  Email: {personnel.email}")
    print(f"  Status: {personnel.status}")
    
    # Create mock request for the form
    factory = RequestFactory()
    request = factory.post('/test/')
    request.user = test_user
    request.META = {
        'REMOTE_ADDR': '127.0.0.1',
        'HTTP_USER_AGENT': 'Test Browser'
    }
    request.session = {'session_key': 'test_session'}
    
    # Make test changes using the UniversalForm
    print(f"\nMaking test updates...")
    test_data = {
        'operation_type': 'edit_personnel',
        'edit_personnel_id': personnel.id,
        'surname': personnel.surname,
        'firstname': personnel.firstname,  
        'middle_initial': personnel.middle_initial or '',
        'rank': personnel.rank,
        'serial': personnel.serial,
        'personnel_group': personnel.group,
        'tel': '+639555555555',  # Change telephone
        'personnel_email': 'updated@email.com',  # Change email
        'personnel_status': personnel.status,
        'change_reason': 'Test historical update'
    }
    
    # Submit form with changes
    form = UniversalForm(
        data=test_data,
        edit_personnel=personnel,
        request_user=test_user,
        request=request
    )
    
    if form.is_valid():
        try:
            user, updated_personnel = form.save()
            print("✓ Form saved successfully")
            
            # Check if historical record was created
            new_history_count = updated_personnel.history.count()
            print(f"New historical record count: {new_history_count}")
            
            if new_history_count > initial_history_count:
                print("✓ New historical record created successfully")
                
                # Show the latest historical record
                latest_history = updated_personnel.history.first()
                print(f"\nLatest historical record:")
                print(f"  History ID: {latest_history.history_id}")
                print(f"  History Date: {latest_history.history_date}")
                print(f"  History Type: {latest_history.history_type}")
                print(f"  History User: {latest_history.history_user}")
                print(f"  Change Reason: {latest_history.history_change_reason}")
                print(f"  Name: {latest_history.surname}, {latest_history.firstname}")
                print(f"  Tel: {latest_history.tel}")
                print(f"  Email: {latest_history.email}")
                
                # Compare with previous record if exists
                if new_history_count > 1:
                    previous_history = updated_personnel.history.all()[1]
                    print(f"\nField changes detected:")
                    
                    if latest_history.tel != previous_history.tel:
                        print(f"  Tel: {previous_history.tel} → {latest_history.tel}")
                    
                    if latest_history.email != previous_history.email:
                        print(f"  Email: {previous_history.email} → {latest_history.email}")
                
                return True
            else:
                print("✗ No new historical record was created")
                return False
                
        except Exception as e:
            print(f"✗ Error saving form: {e}")
            return False
    else:
        print(f"✗ Form validation failed: {form.errors}")
        return False

def show_all_historical_records():
    """Show all historical records in the system"""
    print("\n=== All Historical Records ===")
    
    try:
        personnel = Personnel.objects.get(id='PE-994360070226')
        history_records = personnel.history.all().order_by('-history_date')
        
        print(f"Found {len(history_records)} historical records for {personnel.get_full_name()}:")
        
        for i, record in enumerate(history_records):
            print(f"\n{i+1}. Record ID: {record.history_id}")
            print(f"   Date: {record.history_date}")
            print(f"   Type: {record.history_type} ({'Created' if record.history_type == '+' else 'Updated' if record.history_type == '~' else 'Deleted'})")
            print(f"   User: {record.history_user or 'Unknown'}")
            print(f"   Name: {record.surname}, {record.firstname} {record.middle_initial or ''}")
            print(f"   Tel: {record.tel}")
            print(f"   Email: {record.email}")
            print(f"   Reason: {record.history_change_reason or 'Not specified'}")
            
    except Personnel.DoesNotExist:
        print("No personnel found for testing")

if __name__ == '__main__':
    print("Django Simple History Integration Test")
    print("=====================================\n")
    
    # Show initial state
    show_all_historical_records()
    
    # Run the test
    success = test_personnel_historical_updates()
    
    if success:
        print("\n✓ Historical updates are working correctly!")
        print("\nShowing updated historical records:")
        show_all_historical_records()
    else:
        print("\n✗ Historical updates are not working properly")
        print("Please check the django-simple-history configuration")
    
    print("\n" + "="*50)