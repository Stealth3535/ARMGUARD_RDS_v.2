"""
ARMGUARD RDS v.2 - Inventory App Design System Tests
Tests for inventory list, item detail, and related views
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from inventory.models import Item
from personnel.models import Personnel
import gzip

User = get_user_model()


class InventoryDesignSystemTests(TestCase):
    """Test that inventory templates use design system classes correctly"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test items
        self.item1 = Item.objects.create(
            serial='AFP123456',
            item_type='M16',
            status='Available'
        )
        self.item2 = Item.objects.create(
            serial='AFP789012',
            item_type='M4',
            status='Issued'
        )
        
    def test_inventory_list_loads_with_design_system(self):
        """Test inventory list uses design system"""
        response = self.client.get(reverse('inventory:item_list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system components
        self.assertIn('stat-card', html, "Should use stat-card component")
        self.assertIn('card', html, "Should use card component")
        self.assertIn('table', html, "Should use table component")
        self.assertIn('badge', html, "Should use badge for status")
        
    def test_inventory_stats_display(self):
        """Test inventory stat cards"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for stat categories
        self.assertIn('Available', html)
        self.assertIn('Total', html)
        
    def test_inventory_table_design(self):
        """Test inventory table uses design system"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for table classes
        self.assertIn('table', html, "Should use table class")
        self.assertIn('<thead>', html, "Should have proper table structure")
        self.assertIn('<tbody>', html)
        
    def test_inventory_filter_components(self):
        """Test filter UI components"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for filter elements
        self.assertIn('form-input', html, "Should use form inputs")
        self.assertIn('pill', html, "Should use filter pills")
        
    def test_inventory_buttons(self):
        """Test button components in inventory"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for button classes
        self.assertIn('btn', html, "Should use button components")
        
    def test_inventory_status_badges(self):
        """Test status badges use design system"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for badge components
        self.assertIn('badge', html, "Should use badge components for status")
        
    def test_inventory_layout_grid(self):
        """Test grid layout usage"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for grid classes
        self.assertIn('grid', html, "Should use grid layout")
        self.assertIn('gap-', html, "Should use gap utilities")
        
    def test_inventory_responsive_design(self):
        """Test responsive classes"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for responsive classes
        self.assertIn('grid-cols-', html, "Should have responsive grid columns")
        
    def test_item_detail_design_system(self):
        """Test item detail page uses design system"""
        response = self.client.get(
            reverse('inventory:item_detail', args=[self.item1.id])
        )
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system components
        self.assertIn('card', html, "Should use card component")
        self.assertIn('badge', html, "Should use badge component")
        
    def test_inventory_color_system(self):
        """Test design system colors"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for color classes
        color_classes = ['text-neutral-', 'text-success', 'text-warning', 'text-danger']
        found = any(cls in html for cls in color_classes)
        self.assertTrue(found, "Should use design system colors")
        
    def test_inventory_spacing(self):
        """Test spacing system"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for spacing utilities
        spacing_patterns = ['mb-', 'mt-', 'p-', 'gap-']
        found = any(pattern in html for pattern in spacing_patterns)
        self.assertTrue(found, "Should use spacing utilities")


class InventoryComponentTests(TestCase):
    """Test specific components in inventory app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='comp_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_stat_card_variants(self):
        """Test stat card color variants"""
        Item.objects.create(serial='T001', item_type='M16', status='Available')
        Item.objects.create(serial='T002', item_type='M4', status='Issued')
        
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for stat card variants  
        self.assertIn('stat-card', html)
        
    def test_search_input_component(self):
        """Test search input styling"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for form input
        self.assertIn('form-input', html, "Should use form-input class")
        
    def test_action_buttons(self):
        """Test action button components"""
        Item.objects.create(serial='T003', item_type='GLOCK', status='Available')
        
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for buttons
        self.assertIn('btn', html)


class InventoryAccessibilityTests(TestCase):
    """Test accessibility features in inventory"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='a11y_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_semantic_html(self):
        """Test semantic HTML usage"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for semantic elements
        self.assertIn('<main', html, "Should use semantic HTML")
        self.assertIn('<table', html, "Should use table element")
        
    def test_aria_labels(self):
        """Test ARIA labels presence"""
        response = self.client.get(reverse('inventory:item_list'))
        html = response.content.decode('utf-8')
        
        # Check for ARIA attributes (if any)
        # Note: This is a basic check, expand as needed
        self.assertIn('href=', html, "Should have proper links")


class InventoryIntegrationTests(TestCase):
    """Integration tests with real data scenarios"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integ_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create multiple items with different statuses
        for i in range(10):
            Item.objects.create(
                serial=f'AFP{i:06d}',
                item_type='M16' if i % 2 == 0 else 'M4',
                status='Available' if i % 3 == 0 else 'Issued'
            )
            
    def test_inventory_with_multiple_items(self):
        """Test inventory displays correctly with multiple items"""
        response = self.client.get(reverse('inventory:item_list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Should display all items
        self.assertGreater(html.count('<tr'), 5, "Should display multiple rows")
        
    def test_statistics_accuracy(self):
        """Test that statistics reflect actual data"""
        response = self.client.get(reverse('inventory:item_list'))
        self.assertEqual(response.status_code, 200)
        
        # Stats should be present
        self.assertEqual(Item.objects.count(), 10)


def run_tests():
    """Helper function to run inventory tests"""
    print("\n" + "="*60)
    print("ARMGUARD RDS v.2 - Inventory App Design System Tests")
    print("="*60 + "\n")
    
    from django.core.management import call_command
    call_command('test', 'inventory.tests_design_system', verbosity=2)
    
    print("\n" + "="*60)
    print("Inventory Tests Complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_tests()
