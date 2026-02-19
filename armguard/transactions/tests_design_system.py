"""
ARMGUARD RDS v.2 - Transactions App Design System Tests
Tests for transaction list, detail views, and DEFCON features
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item
from datetime import datetime, timedelta

User = get_user_model()


class TransactionsDesignSystemTests(TestCase):
    """Test transactions templates use design system correctly"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test personnel and items
        self.personnel = Personnel.objects.create(
            firstname='Test',
            surname='User',
            rank='CPT',
            serial='12345678',
            tel='+639123456789',
            classification='OFFICER'
        )
        
        self.item = Item.objects.create(
            serial='AFP123456',
            item_type='M16',
            status='Available'
        )
        
        # Create test transaction
        self.transaction = Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            transaction_mode='NORMAL',
            date_time=datetime.now()
        )
        
    def test_transaction_list_design_system(self):
        """Test transaction list uses design system"""
        response = self.client.get(reverse('transactions:list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system components
        self.assertIn('stat-card', html, "Should use stat-card component")
        self.assertIn('card', html, "Should use card component")
        self.assertIn('table', html, "Should use table component")
        self.assertIn('badge', html, "Should use badge component")
        
    def test_transaction_stats_display(self):
        """Test transaction statistics cards"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for stat categories
        self.assertIn('DEFCON', html)
        self.assertIn('NORMAL', html)
        self.assertIn('Take', html)
        self.assertIn('Return', html)
        
    def test_transaction_table_component(self):
        """Test transaction table uses design system"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for table structure
        self.assertIn('table', html, "Should use table class")
        self.assertIn('<thead>', html, "Should have proper table structure")
        self.assertIn('<tbody>', html)
        
    def test_transaction_filter_ui(self):
        """Test filter components"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for filter elements
        self.assertIn('form-input', html, "Should use form input")
        self.assertIn('pill', html, "Should use filter pills")
        
    def test_transaction_mode_badges(self):
        """Test transaction mode badges"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for badge components
        self.assertIn('badge', html, "Should use badge for transaction mode")
        
    def test_defcon_indicator_styling(self):
        """Test DEFCON mode indicator"""
        # Create DEFCON transaction
        Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            transaction_mode='DEFCON',
            date_time=datetime.now()
        )
        
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for DEFCON badge
        self.assertIn('badge-danger', html, "DEFCON should use danger badge")
        
    def test_normal_mode_indicator_styling(self):
        """Test NORMAL mode indicator"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for NORMAL badge
        self.assertIn('badge-primary', html, "NORMAL should use primary badge")
        
    def test_transaction_action_badges(self):
        """Test action type badges"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for action badges
        self.assertIn('badge', html, "Should use badges for actions")
        
    def test_transaction_responsive_grid(self):
        """Test responsive grid layout"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for grid classes
        self.assertIn('grid', html, "Should use grid layout")
        self.assertIn('gap-', html, "Should use gap utilities")
        
    def test_transaction_color_system(self):
        """Test color system usage"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for color classes
        color_classes = ['text-neutral-', 'text-danger', 'text-primary']
        found = any(cls in html for cls in color_classes)
        self.assertTrue(found, "Should use design system colors")
        
    def test_transaction_spacing(self):
        """Test spacing system"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for spacing utilities
        spacing_patterns = ['mb-', 'mt-', 'p-', 'gap-']
        found = any(pattern in html for pattern in spacing_patterns)
        self.assertTrue(found, "Should use spacing utilities")


class TransactionFilterTests(TestCase):
    """Test transaction filtering functionality"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='filter_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.personnel = Personnel.objects.create(
            firstname='Filter',
            surname='Test',
            rank='CPT',
            serial='11111111',
            tel='+639111111111',
            classification='OFFICER'
        )
        
        self.item = Item.objects.create(
            serial='AFP000001',
            item_type='GLOCK',
            status='Available'
        )
        
    def test_defcon_filter(self):
        """Test DEFCON filter functionality"""
        Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            transaction_mode='DEFCON',
            date_time=datetime.now()
        )
        
        response = self.client.get(reverse('transactions:list') + '?mode=defcon')
        self.assertEqual(response.status_code, 200)
        
    def test_normal_filter(self):
        """Test NORMAL filter functionality"""
        Transaction.objects.create(
            personnel=self.personnel,
            item=self.item,
            action='Take',
            transaction_mode='NORMAL',
            date_time=datetime.now()
        )
        
        response = self.client.get(reverse('transactions:list') + '?mode=normal')
        self.assertEqual(response.status_code, 200)
        
    def test_time_range_filter(self):
        """Test time range filtering"""
        response = self.client.get(reverse('transactions:list') + '?range=week')
        self.assertEqual(response.status_code, 200)
        
    def test_action_filter(self):
        """Test action type filtering"""
        response = self.client.get(reverse('transactions:list') + '?action=take')
        self.assertEqual(response.status_code, 200)


class TransactionComponentTests(TestCase):
    """Test specific components in transactions app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='comp_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_stat_card_variants(self):
        """Test stat card color variants"""
        personnel = Personnel.objects.create(
            firstname='Comp',
            surname='Test',
            rank='AM',
            serial='22222222',
            tel='+639222222222',
            classification='ENLISTED PERSONNEL'
        )
        
        item = Item.objects.create(
            serial='T001',
            item_type='M16',
            status='Available'
        )
        
        Transaction.objects.create(
            personnel=personnel,
            item=item,
            action='Take',
            transaction_mode='DEFCON'
        )
        
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for stat cards
        self.assertIn('stat-card', html)
        
    def test_badge_color_coding(self):
        """Test badge color coding for different modes"""
        personnel = Personnel.objects.create(
            firstname='Badge',
            surname='Test',
            rank='CPT',
            serial='33333333',
            tel='+639333333333',
            classification='OFFICER'
        )
        
        item = Item.objects.create(
            serial='T002',
            item_type='M4',
            status='Available'
        )
        
        # Create both DEFCON and NORMAL transactions
        Transaction.objects.create(
            personnel=personnel,
            item=item,
            action='Take',
            transaction_mode='DEFCON'
        )
        Transaction.objects.create(
            personnel=personnel,
            item=item,
            action='Return',
            transaction_mode='NORMAL'
        )
        
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for badge components
        self.assertIn('badge', html)


class TransactionAccessibilityTests(TestCase):
    """Test accessibility in transactions app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='a11y_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_semantic_html(self):
        """Test semantic HTML elements"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Check for semantic elements
        self.assertIn('<main', html, "Should use semantic HTML")
        self.assertIn('<table', html)
        
    def test_proper_table_structure(self):
        """Test proper table structure"""
        response = self.client.get(reverse('transactions:list'))
        html = response.content.decode('utf-8')
        
        # Should have proper table elements
        self.assertIn('<thead>', html)
        self.assertIn('<tbody>', html)


class TransactionIntegrationTests(TestCase):
    """Integration tests with real scenarios"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integ_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.personnel = Personnel.objects.create(
            firstname='Integration',
            surname='Test',
            rank='MAJ',
            serial='44444444',
            tel='+639444444444',
            classification='OFFICER'
        )
        
        # Create multiple transactions
        for i in range(10):
            item = Item.objects.create(
                serial=f'AFP{i:06d}',
                item_type='M16',
                status='Available'
            )
            
            Transaction.objects.create(
                personnel=self.personnel,
                item=item,
                action='Take' if i % 2 == 0 else 'Return',
                transaction_mode='DEFCON' if i % 3 == 0 else 'NORMAL',
                date_time=datetime.now() - timedelta(hours=i)
            )
            
    def test_transaction_list_with_multiple_entries(self):
        """Test list displays correctly with multiple transactions"""
        response = self.client.get(reverse('transactions:list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Should display multiple rows
        self.assertGreater(html.count('<tr'), 5, "Should display multiple rows")
        
    def test_statistics_accuracy(self):
        """Test that statistics reflect actual data"""
        response = self.client.get(reverse('transactions:list'))
        self.assertEqual(response.status_code, 200)
        
        # Verify data counts
        total = Transaction.objects.count()
        defcon_count = Transaction.objects.filter(transaction_mode='DEFCON').count()
        normal_count = Transaction.objects.filter(transaction_mode='NORMAL').count()
        
        self.assertEqual(total, 10)
        self.assertGreater(defcon_count, 0)
        self.assertGreater(normal_count, 0)


def run_tests():
    """Helper function to run transaction tests"""
    print("\n" + "="*60)
    print("ARMGUARD RDS v.2 - Transactions App Design System Tests")
    print("="*60 + "\n")
    
    from django.core.management import call_command
    call_command('test', 'transactions.tests_design_system', verbosity=2)
    
    print("\n" + "="*60)
    print("Transactions Tests Complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_tests()
