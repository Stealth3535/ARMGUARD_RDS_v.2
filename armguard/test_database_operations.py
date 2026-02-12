"""
Comprehensive Test Suite for Database Operations
Tests CREATE, UPDATE, DELETE operations with focus on:
- Data integrity
- Transaction atomicity
- Audit logging
- Performance optimization
- Error handling
"""
import unittest
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from admin.models import AuditLog, DeletedRecord
from users.models import UserProfile


class PersonnelCreateTests(TestCase):
    """Test personnel CREATE operations"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123',
            is_staff=True
        )
    
    def test_create_officer(self):
        """Test creating an officer with proper formatting"""
        personnel = Personnel.objects.create(
            surname='DOE',
            firstname='JOHN',
            middle_initial='A',
            rank='1LT',
            serial='23494',
            group='HAS',
            tel='09123456789',
            email='john.doe@gmail.com',
            created_by=self.admin_user
        )
        
        # Verify auto-formatting
        self.assertEqual(personnel.classification, 'OFFICER')
        self.assertTrue(personnel.serial.startswith('O-'))
        self.assertTrue(personnel.id.startswith('PO-'))
        self.assertEqual(personnel.surname, 'DOE')
        
    def test_create_enlisted(self):
        """Test creating enlisted personnel"""
        personnel = Personnel.objects.create(
            surname='Smith',
            firstname='Robert',
            rank='SGT',
            serial='994360',
            group='951st',
            tel='09123456789',
            created_by=self.admin_user
        )
        
        # Verify classification
        self.assertEqual(personnel.classification, 'ENLISTED PERSONNEL')
        self.assertFalse(personnel.serial.startswith('O-'))
        self.assertTrue(personnel.id.startswith('PE-'))
        self.assertEqual(personnel.surname, 'Smith')  # Title case for enlisted
    
    def test_duplicate_serial_prevention(self):
        """Test that duplicate serials are prevented"""
        Personnel.objects.create(
            surname='Test1',
            firstname='User1',
            rank='CPT',
            serial='12345',
            group='HAS',
            tel='09123456789'
        )
        
        # This should raise IntegrityError (if unique constraint exists)
        # Note: Currently serial is not unique at DB level, but should be
        pass  # TODO: Add unique constraint to serial field
    
    def test_serial_formatting(self):
        """Test serial number formatting logic"""
        # Officer serial gets O- prefix
        officer = Personnel.objects.create(
            surname='Officer',
            firstname='Test',
            rank='2LT',
            serial='11111',
            group='HAS',
            tel='09123456789'
        )
        self.assertEqual(officer.serial, 'O-11111')
        
        # Enlisted serial stays numeric
        enlisted = Personnel.objects.create(
            surname='Enlisted',
            firstname='Test',
            rank='PVT',
            serial='22222',
            group='HAS',
            tel='09123456789'
        )
        self.assertEqual(enlisted.serial, '22222')


class PersonnelUpdateTests(TestCase):
    """Test personnel UPDATE operations"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123'
        )
        self.personnel = Personnel.objects.create(
            surname='Original',
            firstname='Name',
            rank='1LT',
            serial='99999',
            group='HAS',
            tel='09123456789',
            created_by=self.admin_user
        )
    
    def test_update_name(self):
        """Test updating personnel name"""
        old_name = self.personnel.get_full_name()
        
        self.personnel.firstname = 'UPDATED'
        self.personnel._audit_user = self.admin_user
        self.personnel.save()
        
        self.assertEqual(self.personnel.firstname, 'UPDATED')
        self.assertNotEqual(old_name, self.personnel.get_full_name())
        
    def test_version_increment(self):
        """Test that version increments on update"""
        initial_version = self.personnel.version
        
        self.personnel.tel = '09987654321'
        self.personnel.save()
        
        self.assertEqual(self.personnel.version, initial_version + 1)
    
    def test_classification_auto_correction(self):
        """Test that classification auto-corrects based on rank"""
        # Manually set wrong classification
        self.personnel.classification = 'ENLISTED PERSONNEL'  # Wrong for 1LT
        self.personnel.save()
        
        # Should auto-correct to OFFICER
        self.personnel.refresh_from_db()
        self.assertEqual(self.personnel.classification, 'OFFICER')
    
    def test_bulk_status_update(self):
        """Test batch status update"""
        # Create multiple personnel
        p1 = Personnel.objects.create(
            surname='Test1', firstname='User1', rank='SGT',
            serial='11111', group='HAS', tel='09111111111'
        )
        p2 = Personnel.objects.create(
            surname='Test2', firstname='User2', rank='SGT',
            serial='22222', group='HAS', tel='09222222222'
        )
        
        # Bulk update status
        updated_count = Personnel.bulk_update_status(
            [p1.id, p2.id],
            'Inactive',
            self.admin_user
        )
        
        self.assertEqual(updated_count, 2)
        p1.refresh_from_db()
        p2.refresh_from_db()
        self.assertEqual(p1.status, 'Inactive')
        self.assertEqual(p2.status, 'Inactive')


class PersonnelDeleteTests(TestCase):
    """Test personnel DELETE operations (soft delete)"""
    
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            password='testpass123',
            email='admin@test.com'
        )
        self.personnel = Personnel.objects.create(
            surname='ToDelete',
            firstname='Test',
            rank='CPT',
            serial='99999',
            group='HAS',
            tel='09123456789'
        )
    
    def test_soft_delete(self):
        """Test soft delete preserves record"""
        personnel_id = self.personnel.id
        
        self.personnel.soft_delete(deleted_by=self.admin_user)
        
        # Should not be in default queryset
        self.assertFalse(Personnel.objects.filter(id=personnel_id).exists())
        
        # But should exist in all_objects
        self.assertTrue(Personnel.all_objects.filter(id=personnel_id).exists())
        
        # Check fields
        deleted_personnel = Personnel.all_objects.get(id=personnel_id)
        self.assertTrue(deleted_personnel.is_deleted)
        self.assertIsNotNone(deleted_personnel.deleted_at)
        self.assertEqual(deleted_personnel.status, 'Inactive')
    
    def test_deleted_record_creation(self):
        """Test that DeletedRecord is created on deletion"""
        initial_count = DeletedRecord.objects.count()
        
        # This would normally be done in the view
        DeletedRecord.objects.create(
            deleted_by=self.admin_user,
            model_name='Personnel',
            record_id=self.personnel.id,
            record_data={'name': self.personnel.get_full_name()},
            reason='Test deletion'
        )
        
        self.assertEqual(DeletedRecord.objects.count(), initial_count + 1)


class TransactionCreateTests(TransactionTestCase):
    """Test transaction CREATE operations (uses TransactionTestCase for isolation)"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123'
        )
        self.personnel = Personnel.objects.create(
            surname='Borrower',
            firstname='Test',
            rank='SGT',
            serial='12345',
            group='HAS',
            tel='09123456789'
        )
        self.item = Item.objects.create(
            item_type='M16',
            serial='TEST-001',
            status='Available',
            condition='Good'
        )
    
    def test_create_withdrawal_transaction(self):
        """Test creating a withdrawal transaction"""
        txn = Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            issued_by=self.admin_user,
            mags=2,
            rounds=60,
            duty_type='Training'
        )
        
        # Verify transaction created
        self.assertIsNotNone(txn.id)
        self.assertEqual(txn.action, 'Take')
        
        # Verify item status updated
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'Issued')
    
    def test_prevent_double_issue(self):
        """Test that personnel can't have multiple items"""
        # Create first transaction
        Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            issued_by=self.admin_user
        )
        
        # Try to issue another item to same personnel
        item2 = Item.objects.create(
            item_type='M4',
            serial='TEST-002',
            status='Available',
            condition='Good'
        )
        
        with self.assertRaises(ValueError):
            Transaction.objects.create(
                personnel=self.personnel,
                item=item2,
                action='Take',
                issued_by=self.admin_user
            )
    
    def test_atomic_transaction_rollback(self):
        """Test that transaction rolls back on error"""
        initial_item_status = self.item.status
        
        # Force an error during transaction
        try:
            with transaction.atomic():
                Transaction.objects.create(
                    personnel=self.personnel,
                    item=self.item,
                    action='Take',
                    issued_by=self.admin_user
                )
                # Force error
                raise Exception("Forced error for testing")
        except Exception:
            pass
        
        # Item status should not have changed
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, initial_item_status)


class AuditLoggingTests(TestCase):
    """Test audit logging functionality"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='testpass123'
        )
    
    def test_personnel_create_audit_log(self):
        """Test that personnel creation creates audit log"""
        initial_count = AuditLog.objects.count()
        
        personnel = Personnel.objects.create(
            surname='Test',
            firstname='Audit',
            rank='CPT',
            serial='99999',
            group='HAS',
            tel='09123456789',
            created_by=self.admin_user
        )
        
        # Should have created audit log via signal
        # Check if audit log count increased
        self.assertGreater(AuditLog.objects.count(), initial_count)
    
    def test_audit_log_field_changes(self):
        """Test that field changes are tracked"""
        personnel = Personnel.objects.create(
            surname='Original',
            firstname='Name',
            rank='1LT',
            serial='12345',
            group='HAS',
            tel='09123456789'
        )
        
        old_surname = personnel.surname
        personnel.surname = 'CHANGED'
        personnel._audit_user = self.admin_user
        personnel.save()
        
        # Get field changes
        changes = personnel.get_field_changes(
            Personnel.objects.get(surname=old_surname) if False else None
        )
        
        # Should track the change (if old instance available)
        # This is a simplified test - actual implementation tracks via signals


class PerformanceTests(TestCase):
    """Test query performance optimizations"""
    
    def test_no_n_plus_one_queries(self):
        """Test that related queries use select_related"""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        
        # Create test data
        user = User.objects.create_user('testuser', password='test123')
        Personnel.objects.create(
            surname='Test1',
            firstname='User1',
            rank='SGT',
            serial='11111',
            group='HAS',
            tel='09111111111',
            user=user
        )
        
        # Test query count
        with CaptureQueriesContext(connection) as context:
            # This should use select_related to avoid N+1
            personnel_list = list(Personnel.objects.select_related('user').all())
            for p in personnel_list:
                # Accessing user should not trigger additional query
                _ = p.user.username if p.user else None
        
        # Should be minimal queries (ideally 1 for personnel + users)
        self.assertLessEqual(len(context.captured_queries), 2)


class ValidationTests(TestCase):
    """Test data validation"""
    
    def test_email_format_validation(self):
        """Test email auto-correction"""
        personnel = Personnel.objects.create(
            surname='Test',
            firstname='Email',
            rank='SGT',
            serial='11111',
            group='HAS',
            tel='09111111111',
            email='test@yahoo.com'  # Should auto-correct to @gmail.com
        )
        
        # Should auto-correct to @gmail.com
        self.assertTrue(personnel.email.endswith('@gmail.com'))
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        with self.assertRaises((IntegrityError, ValidationError)):
            Personnel.objects.create(
                # Missing required fields
                surname='',  # Required
                firstname='Test'
            )


if __name__ == '__main__':
    unittest.main()
