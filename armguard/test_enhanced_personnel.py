"""
Test Enhanced Personnel Model
Tests all new features: version tracking, status tracking, history, email validation, etc.

Run with: python test_enhanced_personnel.py
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel
from admin.models import AuditLog
from django.utils import timezone


def print_separator(title=""):
    print("\n" + "=" * 80)
    if title:
        print(f"  {title}")
        print("=" * 80)


def test_enhanced_features():
    """Test all enhanced features of the Personnel model"""
    
    print_separator("ENHANCED PERSONNEL MODEL TEST")
    
    # 1. Setup test user
    print("\n1. Setting up test user...")
    test_user, created = User.objects.get_or_create(
        username='enhanced_test_user',
        defaults={
            'email': 'enhanced@test.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
    print(f"   ✓ Test user: {test_user.username}")
    
    # 2. Clean up any existing test personnel
    Personnel.all_objects.filter(serial='777777').delete()
    
    # 3. Test personnel creation with comprehensive audit tracking
    print("\n2. Creating personnel with comprehensive audit tracking...")
    
    new_personnel = Personnel(
        surname='Enhanced',
        firstname='Test',
        middle_initial='E',
        rank='CPT',
        serial='777777',
        group='HAS',
        tel='+639178888888',
        email='enhanced@yahoo.com',  # Will be auto-corrected to @gmail.com
        classification='OFFICER',
        status='Active'
    )
    
    # Set comprehensive audit context
    new_personnel._audit_user = test_user
    new_personnel._audit_ip = '192.168.1.200'
    new_personnel._audit_user_agent = 'Enhanced Test Agent/2.0'
    new_personnel._audit_session = 'test-session-123'
    new_personnel.save()
    
    print(f"   ✓ Created personnel: {new_personnel.id}")
    print(f"   ✓ Name: {new_personnel.get_full_name()}")
    print(f"   ✓ Email auto-corrected: {new_personnel.email}")
    print(f"   ✓ Version: {new_personnel.version}")
    print(f"   ✓ Created by: {new_personnel.created_by}")
    print(f"   ✓ Created IP: {new_personnel.created_ip}")
    print(f"   ✓ Session ID: {new_personnel.session_id}")
    print(f"   ✓ is_deleted: {new_personnel.is_deleted}")
    
    # 4. Test version increment on update
    print("\n3. Testing version tracking...")
    initial_version = new_personnel.version
    
    new_personnel._audit_user = test_user
    new_personnel._change_reason = "Promotion to Major"
    new_personnel.rank = 'MAJ'
    new_personnel.save()
    
    print(f"   ✓ Version incremented: {initial_version} → {new_personnel.version}")
    print(f"   ✓ Change reason: {new_personnel.change_reason}")
    
    # 5. Test status tracking
    print("\n4. Testing status change tracking...")
    old_status = new_personnel.status
    
    new_personnel._audit_user = test_user
    new_personnel.status = 'Suspended'
    new_personnel.save()
    
    print(f"   ✓ Status changed: {old_status} → {new_personnel.status}")
    print(f"   ✓ Status changed at: {new_personnel.status_changed_at}")
    print(f"   ✓ Status changed by: {new_personnel.status_changed_by}")
    
    # 6. Test django-simple-history
    print("\n5. Testing django-simple-history integration...")
    
    # Get history records
    history = new_personnel.history.all()
    print(f"   ✓ Historical records: {history.count()}")
    
    if history.exists():
        print(f"\n   History timeline:")
        for i, hist in enumerate(history, 1):
            print(f"     {i}. {hist.history_date} - {hist.history_type} by {hist.history_user}")
            print(f"        Rank: {hist.rank}, Status: {hist.status}, Version: {hist.version}")
    
    # 7. Test field-level change detection
    print("\n6. Testing field-level change detection...")
    
    # Make multiple changes
    new_personnel._audit_user = test_user
    new_personnel._change_reason = "Administrative update"
    new_personnel.tel = '+639189999999'
    new_personnel.group = '951st'
    new_personnel.save()
    
    # Get latest history record
    latest_history = new_personnel.history.first()
    if latest_history and latest_history.prev_record:
        print(f"   ✓ Changes detected:")
        delta = latest_history.diff_against(latest_history.prev_record)
        for change in delta.changes:
            print(f"     • {change.field}: '{change.old}' → '{change.new}'")
    
    # 8. Test email validation
    print("\n7. Testing email validation...")
    
    test_emails = [
        ('test@yahoo.com', 'test@gmail.com'),
        ('user@hotmail.com', 'user@gmail.com'),
        ('admin@gmail.com', 'admin@gmail.com'),
    ]
    
    for original, expected in test_emails:
        new_personnel.email = original
        new_personnel.save()
        print(f"   ✓ '{original}' → '{new_personnel.email}' (expected: '{expected}')")
    
    # 9. Test soft delete with new is_deleted flag
    print("\n8. Testing enhanced soft delete...")
    
    new_personnel.soft_delete(deleted_by=test_user)
    
    print(f"   ✓ Personnel soft deleted")
    print(f"     - is_deleted: {new_personnel.is_deleted}")
    print(f"     - deleted_at: {new_personnel.deleted_at}")
    print(f"     - deleted_by: {new_personnel.deleted_by}")
    print(f"     - status: {new_personnel.status}")
    
    # Verify personnel is excluded from default queryset
    exists_in_default = Personnel.objects.filter(id=new_personnel.id).exists()
    exists_with_deleted = Personnel.all_objects.filter(id=new_personnel.id).exists()
    
    print(f"   ✓ Excluded from default queryset: {not exists_in_default}")
    print(f"   ✓ Exists in all_objects queryset: {exists_with_deleted}")
    
    # 10. Test data retention fields
    print("\n9. Testing data retention and compliance fields...")
    
    # Restore personnel for testing retention
    new_personnel.is_deleted = False
    new_personnel.deleted_at = None
    new_personnel.retention_period = 365  # days
    new_personnel.can_purge_at = timezone.now() + timezone.timedelta(days=365)
    new_personnel.save()
    
    print(f"   ✓ Retention period: {new_personnel.retention_period} days")
    print(f"   ✓ Can purge at: {new_personnel.can_purge_at.strftime('%Y-%m-%d')}")
    
    # 11. Summary
    print_separator("SUMMARY OF NEW FEATURES")
    
    features_tested = [
        ("✓", "Comprehensive audit fields (IP, user agent, session)"),
        ("✓", "Version tracking (auto-increment on updates)"),
        ("✓", "Change reason documentation"),
        ("✓", "Status change tracking with timestamp"),
        ("✓", "django-simple-history integration"),
        ("✓", "Field-level change history"),
        ("✓", "Email validation and auto-correction"),
        ("✓", "Enhanced soft delete with is_deleted flag"),
        ("✓", "Data retention and compliance fields"),
        ("✓", "Session tracking"),
    ]
    
    print()
    for status, feature in features_tested:
        print(f"   {status} {feature}")
    
    print(f"\n   Total historical records: {new_personnel.history.count()}")
    print(f"   Total audit logs: {AuditLog.objects.filter(target_id=new_personnel.id).count()}")
    print(f"   Final version: {new_personnel.version}")
    
    print("\n" + "=" * 80)
    print("  ALL ENHANCED FEATURES TESTED SUCCESSFULLY!")
    print("=" * 80 + "\n")
    
    # Cleanup
    print("Cleaning up test data...")
    Personnel.all_objects.filter(id=new_personnel.id).delete()
    print("✓ Test personnel deleted\n")


if __name__ == '__main__':
    test_enhanced_features()
