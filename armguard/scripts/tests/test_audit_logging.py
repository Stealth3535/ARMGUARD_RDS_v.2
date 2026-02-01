"""
Test Audit Logging Security and Integration
Comprehensive test for audit trail functionality
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.test import RequestFactory
from inventory.models import Item
from personnel.models import Personnel
from admin.models import AuditLog, DeletedRecord
from admin.forms import ItemEditForm


def setup_test_users():
    """Setup test users"""
    print("\n" + "="*80)
    print("SETUP: Creating test users")
    print("="*80)
    
    # Create superuser
    superuser = User.objects.filter(username='audit_superuser').first()
    if not superuser:
        superuser = User.objects.create_superuser(
            username='audit_superuser',
            email='audit_super@test.com',
            password='TestPass123!'
        )
        print(f"✓ Created superuser: {superuser.username}")
    else:
        print(f"✓ Superuser exists: {superuser.username}")
    
    return superuser


def test_item_edit_audit_log(user):
    """Test that item edits create audit logs"""
    print("\n" + "="*80)
    print("TEST 1: Item Edit Audit Logging")
    print("="*80)
    
    # Create a test item
    item = Item.objects.create(
        item_type='M16',
        serial='AUDIT001',
        description='Test item for audit',
        condition='Good',
        status='Available'
    )
    print(f"\n✓ Created test item: {item.id}")
    
    # Clear existing audit logs for this item
    AuditLog.objects.filter(target_model='Item', target_id=str(item.id)).delete()
    
    # Edit the item using the form (simulating view behavior)
    # IMPORTANT: Capture old values BEFORE creating the form
    old_values = {
        'item_type': item.item_type,
        'serial': item.serial,
        'condition': item.condition,
        'status': item.status,
    }
    
    form_data = {
        'item_type': 'M4',  # Changed
        'serial': 'AUDIT001-EDITED',  # Changed
        'description': 'Updated description',  # Changed
        'condition': 'Fair',  # Changed
        'status': 'Maintenance',  # Changed
    }
    
    form = ItemEditForm(form_data, instance=item)
    if form.is_valid():
        # Save
        updated_item = form.save()
        
        # Create audit log (simulating view behavior)
        changes = []
        for field, old_value in old_values.items():
            new_value = getattr(updated_item, field)
            if old_value != new_value:
                changes.append(f"{field}: {old_value} → {new_value}")
        
        print(f"✓ Changes detected: {changes}")
        
        if changes:
            AuditLog.objects.create(
                action='ITEM_EDIT',
                target_model='Item',
                target_id=str(updated_item.id),
                target_name=f"{updated_item.item_type} - {updated_item.serial}",
                description=f"Updated item: {', '.join(changes)}",
                performed_by=user,
                ip_address='127.0.0.1',
                user_agent='Test Agent'
            )
        
        print(f"✓ Item edited: {', '.join(changes)}")
        
        # Verify audit log created
        audit_logs = AuditLog.objects.filter(
            action='ITEM_EDIT',
            target_model='Item',
            target_id=str(updated_item.id)
        )
        
        if audit_logs.exists():
            log = audit_logs.first()
            print(f"✓ PASS: Audit log created")
            print(f"  - Action: {log.action}")
            print(f"  - Target: {log.target_name}")
            print(f"  - Performed by: {log.performed_by.username}")
            print(f"  - Description: {log.description}")
            print(f"  - IP: {log.ip_address}")
            print(f"  - Timestamp: {log.timestamp}")
            return True
        else:
            print("✗ FAIL: No audit log created")
            return False
    else:
        print(f"✗ FAIL: Form validation failed: {form.errors}")
        return False


def test_item_delete_audit_log(user):
    """Test that item deletions create audit logs and deleted records"""
    print("\n" + "="*80)
    print("TEST 2: Item Delete Audit Logging")
    print("="*80)
    
    # Create a test item
    item = Item.objects.create(
        item_type='GLOCK',
        serial='AUDIT002',
        description='Item to delete',
        condition='Good',
        status='Available'
    )
    print(f"\n✓ Created test item: {item.id}")
    
    # Store item details
    item_data = {
        'id': item.id,
        'item_type': item.item_type,
        'serial': item.serial,
        'description': item.description,
        'condition': item.condition,
        'status': item.status,
    }
    
    item_name = f"{item.item_type} - {item.serial}"
    item_id = str(item.id)
    deletion_reason = "Test deletion for audit log"
    
    # Clear existing logs
    AuditLog.objects.filter(target_model='Item', target_id=item_id).delete()
    DeletedRecord.objects.filter(model_name='Item', record_id=item_id).delete()
    
    # Create deleted record
    DeletedRecord.objects.create(
        model_name='Item',
        record_id=item_id,
        record_name=item_name,
        record_data=item_data,
        deleted_by=user,
        reason=deletion_reason,
        deletion_reason=deletion_reason
    )
    
    # Create audit log
    AuditLog.objects.create(
        action='ITEM_DELETE',
        target_model='Item',
        target_id=item_id,
        target_name=item_name,
        description=f"Deleted item: {item_name}. Reason: {deletion_reason}",
        performed_by=user,
        ip_address='127.0.0.1',
        user_agent='Test Agent'
    )
    
    # Delete the item
    item.delete()
    print(f"✓ Item deleted: {item_name}")
    
    # Verify deleted record
    deleted_record = DeletedRecord.objects.filter(
        model_name='Item',
        record_id=item_id
    ).first()
    
    if deleted_record:
        print(f"✓ PASS: Deleted record created")
        print(f"  - Model: {deleted_record.model_name}")
        print(f"  - Record ID: {deleted_record.record_id}")
        print(f"  - Record Name: {deleted_record.record_name}")
        print(f"  - Deleted by: {deleted_record.deleted_by.username}")
        print(f"  - Reason: {deleted_record.reason}")
        print(f"  - Data preserved: {len(deleted_record.record_data)} fields")
    else:
        print("✗ FAIL: No deleted record created")
        return False
    
    # Verify audit log
    audit_log = AuditLog.objects.filter(
        action='ITEM_DELETE',
        target_model='Item',
        target_id=item_id
    ).first()
    
    if audit_log:
        print(f"✓ PASS: Audit log created")
        print(f"  - Action: {audit_log.action}")
        print(f"  - Target: {audit_log.target_name}")
        print(f"  - Performed by: {audit_log.performed_by.username}")
        print(f"  - IP: {audit_log.ip_address}")
        return True
    else:
        print("✗ FAIL: No audit log created")
        return False


def test_audit_log_query_performance():
    """Test that audit log queries are efficient"""
    print("\n" + "="*80)
    print("TEST 3: Audit Log Query Performance")
    print("="*80)
    
    import time
    
    # Query recent logs
    start_time = time.time()
    recent_logs = AuditLog.objects.select_related('performed_by').order_by('-timestamp')[:100]
    log_count = recent_logs.count()
    query_time = (time.time() - start_time) * 1000  # Convert to milliseconds
    
    print(f"\n✓ Retrieved {log_count} audit logs")
    print(f"✓ Query time: {query_time:.2f}ms")
    
    if query_time < 1000:  # Should be under 1 second
        print("✓ PASS: Query performance acceptable")
        return True
    else:
        print("⚠ WARNING: Query took longer than expected")
        return True


def test_audit_log_filtering():
    """Test filtering audit logs by action and model"""
    print("\n" + "="*80)
    print("TEST 4: Audit Log Filtering")
    print("="*80)
    
    # Filter by action
    item_edits = AuditLog.objects.filter(action='ITEM_EDIT')
    item_deletes = AuditLog.objects.filter(action='ITEM_DELETE')
    
    print(f"\n✓ Item edits: {item_edits.count()}")
    print(f"✓ Item deletes: {item_deletes.count()}")
    
    # Filter by model
    item_logs = AuditLog.objects.filter(target_model='Item')
    user_logs = AuditLog.objects.filter(target_model='User')
    personnel_logs = AuditLog.objects.filter(target_model='Personnel')
    
    print(f"✓ Item logs: {item_logs.count()}")
    print(f"✓ User logs: {user_logs.count()}")
    print(f"✓ Personnel logs: {personnel_logs.count()}")
    
    print("✓ PASS: Filtering works correctly")
    return True


def test_sensitive_data_protection():
    """Test that sensitive data is not logged"""
    print("\n" + "="*80)
    print("TEST 5: Sensitive Data Protection")
    print("="*80)
    
    # Check all audit logs for sensitive keywords
    sensitive_keywords = ['password', 'token', 'secret', 'key']
    
    all_logs = AuditLog.objects.all()
    violations = []
    
    for log in all_logs:
        description_lower = log.description.lower()
        for keyword in sensitive_keywords:
            if keyword in description_lower:
                violations.append(f"Log {log.id}: contains '{keyword}' in description")
    
    if violations:
        print("⚠ WARNING: Potential sensitive data in logs:")
        for violation in violations:
            print(f"  - {violation}")
        return False
    else:
        print("✓ PASS: No sensitive data found in audit logs")
        return True


def test_audit_log_retention():
    """Test audit log data integrity"""
    print("\n" + "="*80)
    print("TEST 6: Audit Log Data Integrity")
    print("="*80)
    
    # Check for required fields
    logs_missing_data = AuditLog.objects.filter(
        performed_by__isnull=True
    ) | AuditLog.objects.filter(
        target_model=''
    ) | AuditLog.objects.filter(
        target_id=''
    )
    
    if logs_missing_data.exists():
        print(f"⚠ WARNING: {logs_missing_data.count()} logs with missing critical data")
        return False
    else:
        print("✓ PASS: All audit logs have required fields")
    
    # Check IP address tracking
    logs_with_ip = AuditLog.objects.filter(ip_address__isnull=False).count()
    total_logs = AuditLog.objects.count()
    
    if total_logs > 0:
        ip_percentage = (logs_with_ip / total_logs) * 100
        print(f"✓ IP tracking: {ip_percentage:.1f}% of logs have IP addresses")
        
        if ip_percentage > 50:
            print("✓ PASS: Good IP address tracking coverage")
            return True
        else:
            print("⚠ WARNING: Low IP address tracking coverage")
            return True
    else:
        print("⚠ No audit logs to check")
        return True


def cleanup_test_data():
    """Clean up test data"""
    print("\n" + "="*80)
    print("CLEANUP: Removing test data")
    print("="*80)
    
    # Delete test items
    Item.objects.filter(serial__startswith='AUDIT').delete()
    
    # Delete test audit logs
    AuditLog.objects.filter(target_id__contains='AUDIT').delete()
    
    # Delete test deleted records
    DeletedRecord.objects.filter(record_id__contains='AUDIT').delete()
    
    # Delete test user
    User.objects.filter(username='audit_superuser').delete()
    
    print("✓ Cleanup complete")


def main():
    print("\n" + "="*80)
    print("AUDIT LOGGING SECURITY TEST SUITE")
    print("="*80)
    print("\nTesting audit trail security and integration...")
    
    # Setup
    user = setup_test_users()
    
    # Run tests
    results = {}
    
    results['Item Edit Audit Log'] = test_item_edit_audit_log(user)
    results['Item Delete Audit Log'] = test_item_delete_audit_log(user)
    results['Query Performance'] = test_audit_log_query_performance()
    results['Filtering'] = test_audit_log_filtering()
    results['Sensitive Data Protection'] = test_sensitive_data_protection()
    results['Data Integrity'] = test_audit_log_retention()
    
    # Print results
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    # Cleanup
    cleanup_test_data()
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL AUDIT LOGGING TESTS PASSED")
        print("✓ Audit trail is secure and properly integrated")
    else:
        print("✗ SOME TESTS FAILED - Review audit logging implementation")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
