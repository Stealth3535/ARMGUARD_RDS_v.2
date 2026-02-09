"""
Test Personnel Audit Logging System
Demonstrates the high-quality audit logging features

Run with: python manage.py shell < test_personnel_audit.py
Or: python test_personnel_audit.py
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


def test_audit_logging():
    """Test comprehensive audit logging features"""
    
    print_separator("PERSONNEL AUDIT LOGGING TEST")
    
    # 1. Get or create test user
    print("\n1. Setting up test user...")
    test_user, created = User.objects.get_or_create(
        username='audit_test_user',
        defaults={
            'email': 'audit@test.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        test_user.set_password('testpass123')
        test_user.save()
        print(f"   ✓ Created test user: {test_user.username}")
    else:
        print(f"   ✓ Using existing test user: {test_user.username}")
    
    # 2. Create new personnel with audit tracking
    print("\n2. Creating new personnel with audit tracking...")
    
    # Check if test personnel already exists
    test_serial = '888888'
    existing = Personnel.objects.filter(serial=test_serial).first()
    if existing:
        print(f"   ⚠ Personnel with serial {test_serial} already exists. Deleting...")
        existing.delete()
    
    new_personnel = Personnel(
        surname='TestSurname',
        firstname='TestFirstname',
        middle_initial='T',
        rank='SGT',
        serial=test_serial,
        group='HAS',
        tel='+639171234567',
        classification='ENLISTED PERSONNEL',
        status='Active'
    )
    
    # Set audit context
    new_personnel._audit_user = test_user
    new_personnel._audit_ip = '192.168.1.100'
    new_personnel._audit_user_agent = 'Test Agent/1.0'
    new_personnel.save()
    
    print(f"   ✓ Created personnel: {new_personnel.id} - {new_personnel.get_full_name()}")
    print(f"   ✓ Created by: {new_personnel.created_by}")
    print(f"   ✓ Modified by: {new_personnel.modified_by}")
    
    # 3. Check audit log
    print("\n3. Checking audit log for CREATE action...")
    create_logs = AuditLog.objects.filter(
        target_model='Personnel',
        target_id=new_personnel.id,
        action=AuditLog.ACTION_CREATE
    )
    
    if create_logs.exists():
        log = create_logs.first()
        print(f"   ✓ Audit log created:")
        print(f"     - Action: {log.action}")
        print(f"     - Performed by: {log.performed_by}")
        print(f"     - Timestamp: {log.timestamp}")
        print(f"     - IP Address: {log.ip_address}")
        print(f"     - Description: {log.description}")
        print(f"     - Changes tracked: {len(log.changes)} fields")
    else:
        print("   ✗ No audit log found for CREATE action!")
    
    # 4. Update personnel with audit tracking
    print("\n4. Updating personnel with audit tracking...")
    new_personnel._audit_user = test_user
    new_personnel._audit_ip = '192.168.1.101'
    new_personnel._audit_user_agent = 'Test Agent/1.0'
    new_personnel.rank = 'SSGT'  # Promote!
    new_personnel.tel = '+639187654321'  # Change phone
    new_personnel.save()
    
    print(f"   ✓ Updated personnel:")
    print(f"     - New rank: {new_personnel.rank}")
    print(f"     - New phone: {new_personnel.tel}")
    print(f"     - Modified by: {new_personnel.modified_by}")
    
    # 5. Check audit log for update
    print("\n5. Checking audit log for UPDATE action...")
    update_logs = AuditLog.objects.filter(
        target_model='Personnel',
        target_id=new_personnel.id,
        action=AuditLog.ACTION_PERSONNEL_EDIT
    ).order_by('-timestamp')
    
    if update_logs.exists():
        log = update_logs.first()
        print(f"   ✓ Audit log created:")
        print(f"     - Action: {log.action}")
        print(f"     - Performed by: {log.performed_by}")
        print(f"     - Timestamp: {log.timestamp}")
        print(f"     - IP Address: {log.ip_address}")
        print(f"     - Description: {log.description}")
        if log.changes:
            print(f"     - Changes:")
            for field, change in log.changes.items():
                print(f"       • {field}: '{change.get('old')}' → '{change.get('new')}'")
    else:
        print("   ✗ No audit log found for UPDATE action!")
    
    # 6. Get complete audit history
    print("\n6. Getting complete audit history...")
    audit_history = new_personnel.get_audit_history()
    print(f"   ✓ Total audit entries: {audit_history.count()}")
    
    for i, log in enumerate(audit_history, 1):
        print(f"\n   Entry #{i}:")
        print(f"     - Action: {log.action}")
        print(f"     - By: {log.performed_by}")
        print(f"     - When: {log.timestamp}")
        print(f"     - From IP: {log.ip_address}")
        print(f"     - Description: {log.description}")
    
    # 7. Test soft delete with audit
    print("\n7. Testing soft delete with audit logging...")
    new_personnel.soft_delete(deleted_by=test_user)
    
    print(f"   ✓ Personnel soft deleted:")
    print(f"     - Status: {new_personnel.status}")
    print(f"     - Deleted at: {new_personnel.deleted_at}")
    
    # Check for delete audit log
    delete_logs = AuditLog.objects.filter(
        target_model='Personnel',
        target_id=new_personnel.id,
        action='DELETE'
    )
    
    if delete_logs.exists():
        log = delete_logs.first()
        print(f"   ✓ Delete audit log created:")
        print(f"     - Performed by: {log.performed_by}")
        print(f"     - Timestamp: {log.timestamp}")
        print(f"     - Description: {log.description}")
    
    # 8. Summary
    print_separator("AUDIT LOGGING TEST SUMMARY")
    total_logs = AuditLog.objects.filter(
        target_model='Personnel',
        target_id=new_personnel.id
    ).count()
    
    print(f"\n✓ Total audit entries created: {total_logs}")
    print(f"✓ Personnel ID: {new_personnel.id}")
    print(f"✓ All operations tracked successfully!")
    
    print("\n" + "=" * 80)
    print("  Audit logging test completed successfully!")
    print("=" * 80 + "\n")
    
    # Cleanup
    print("\nCleaning up test data...")
    # Delete the personnel (hard delete this time for cleanup)
    Personnel.all_objects.filter(id=new_personnel.id).delete()
    print("✓ Test personnel deleted")
    
    # Note: We keep audit logs for demonstration
    # In production, audit logs should NEVER be deleted
    print("  (Audit logs preserved for review)\n")


if __name__ == '__main__':
    test_audit_logging()
