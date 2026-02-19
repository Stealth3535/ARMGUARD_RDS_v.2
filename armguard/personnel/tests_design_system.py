"""
ARMGUARD RDS v.2 - Personnel App Design System Tests
Tests for personnel list, detail views, and profile components
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
from datetime import datetime

User = get_user_model()


class PersonnelDesignSystemTests(TestCase):
    """Test personnel templates use design system correctly"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create test personnel
        self.personnel1 = Personnel.objects.create(
            first_name='John',
            last_name='Doe',
            rank='CPT',
            serial='12345678',
            classification='Officer'
        )
        self.personnel2 = Personnel.objects.create(
            first_name='Jane',
            last_name='Smith',
            rank='AM',
            serial='87654321',
            classification='Enlisted'
        )
        
    def test_personnel_list_design_system(self):
        """Test personnel list uses design system"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system components
        self.assertIn('stat-card', html, "Should use stat-card component")
        self.assertIn('card', html, "Should use card component")
        self.assertIn('table', html, "Should use table component")
        self.assertIn('badge', html, "Should use badge component")
        
    def test_personnel_stats_display(self):
        """Test personnel statistics cards"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for stat categories
        self.assertIn('Officers', html)
        self.assertIn('Enlisted', html)
        self.assertIn('Total', html)
        
    def test_personnel_profile_card(self):
        """Test personnel profile card design"""
        response = self.client.get(
            reverse('personnel:personnel_profile_detail', args=[self.personnel1.id])
        )
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for card components
        self.assertIn('card', html, "Should use card component")
        self.assertIn('badge', html, "Should use badge for status")
        
    def test_personnel_table_component(self):
        """Test personnel table uses design system"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for table structure
        self.assertIn('table', html, "Should use table class")
        self.assertIn('<thead>', html, "Should have proper table structure")
        self.assertIn('<tbody>', html)
        
    def test_personnel_filter_ui(self):
        """Test filter components"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for filter elements
        self.assertIn('form-input', html, "Should use form input")
        self.assertIn('pill', html, "Should use filter pills")
        
    def test_personnel_buttons(self):
        """Test button components"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for buttons
        self.assertIn('btn', html, "Should use button components")
        
    def test_personnel_responsive_grid(self):
        """Test responsive grid layout"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for grid classes
        self.assertIn('grid', html, "Should use grid layout")
        self.assertIn('gap-', html, "Should use gap utilities")
        
    def test_personnel_color_system(self):
        """Test color system usage"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for color classes
        color_classes = ['text-neutral-', 'text-success', 'text-primary']
        found = any(cls in html for cls in color_classes)
        self.assertTrue(found, "Should use design system colors")
        
    def test_personnel_typography(self):
        """Test typography system"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for typography classes
        self.assertIn('text-', html, "Should use text utilities")
        self.assertIn('font-', html, "Should use font weight utilities")
        
    def test_personnel_spacing(self):
        """Test spacing system"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for spacing utilities
        spacing_patterns = ['mb-', 'mt-', 'p-', 'gap-']
        found = any(pattern in html for pattern in spacing_patterns)
        self.assertTrue(found, "Should use spacing utilities")


class PersonnelProfileDetailTests(TestCase):
    """Test personnel profile detail view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='profile_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        self.personnel = Personnel.objects.create(
            first_name='Mike',
            last_name='Johnson',
            rank='1LT',
            serial='11223344',
            classification='Officer'
        )
        
        self.item = Item.objects.create(
            serial='AFP999888',
            item_type='M16',
            status='Issued'
        )
        
    def test_profile_detail_card_layout(self):
        """Test profile detail uses card layout"""
        response = self.client.get(
            reverse('personnel:personnel_profile_detail', args=[self.personnel.id])
        )
        html = response.content.decode('utf-8')
        
        # Check for card components
        self.assertIn('card', html, "Should use card components")
        
    def test_profile_info_display(self):
        """Test profile information display"""
        response = self.client.get(
            reverse('personnel:personnel_profile_detail', args=[self.personnel.id])
        )
        html = response.content.decode('utf-8')
        
        # Check for personnel info
        self.assertIn('Mike', html)
        self.assertIn('Johnson', html)
        self.assertIn('1LT', html)
        self.assertIn('11223344', html)
        
    def test_profile_status_badges(self):
        """Test status badge display"""
        response = self.client.get(
            reverse('personnel:personnel_profile_detail', args=[self.personnel.id])
        )
        html = response.content.decode('utf-8')
        
        # Check for badge
        self.assertIn('badge', html, "Should use badge component")
        
    def test_profile_action_buttons(self):
        """Test action buttons on profile"""
        response = self.client.get(
            reverse('personnel:personnel_profile_detail', args=[self.personnel.id])
        )
        html = response.content.decode('utf-8')
        
        # Check for buttons
        self.assertIn('btn', html, "Should have action buttons")


class PersonnelComponentTests(TestCase):
    """Test specific components in personnel app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='comp_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_stat_card_components(self):
        """Test stat card variants"""
        Personnel.objects.create(
            first_name='Test',
            last_name='Officer',
            rank='MAJ',
            classification='Officer'
        )
        Personnel.objects.create(
            first_name='Test',
            last_name='Enlisted',
            rank='AM',
            classification='Enlisted'
        )
        
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for stat cards
        self.assertIn('stat-card', html)
        
    def test_classification_badges(self):
        """Test classification badge styling"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for badge components
        self.assertIn('badge', html, "Should use badges for classification")


class PersonnelAccessibilityTests(TestCase):
    """Test accessibility in personnel app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='a11y_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
    def test_semantic_html(self):
        """Test semantic HTML elements"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Check for semantic elements
        self.assertIn('<main', html, "Should use semantic HTML")
        self.assertIn('<table', html)
        
    def test_proper_heading_hierarchy(self):
        """Test heading hierarchy"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        html = response.content.decode('utf-8')
        
        # Should have h1
        self.assertIn('<h1', html, "Should have h1 heading")


class PersonnelIntegrationTests(TestCase):
    """Integration tests with real scenarios"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integ_test',
            password='testpass123'
        )
        self.client.force_login(self.user)
        
        # Create multiple personnel
        for i in range(10):
            Personnel.objects.create(
                first_name=f'Person{i}',
                last_name=f'Test{i}',
                rank='CPT' if i % 2 == 0 else 'AM',
                serial=f'{i:08d}',
                classification='Officer' if i % 2 == 0 else 'Enlisted'
            )
            
    def test_personnel_list_with_multiple_entries(self):
        """Test list displays correctly with multiple personnel"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Should display multiple rows
        self.assertGreater(html.count('<tr'), 5, "Should display multiple rows")
        
    def test_statistics_with_mixed_classifications(self):
        """Test stats with officers and enlisted"""
        response = self.client.get(reverse('personnel:personnel_profile_list'))
        self.assertEqual(response.status_code, 200)
        
        # Verify data exists
        self.assertEqual(Personnel.objects.count(), 10)
        officer_count = Personnel.objects.filter(classification='Officer').count()
        enlisted_count = Personnel.objects.filter(classification='Enlisted').count()
        
        self.assertGreater(officer_count, 0)
        self.assertGreater(enlisted_count, 0)


def run_tests():
    """Helper function to run personnel tests"""
    print("\n" + "="*60)
    print("ARMGUARD RDS v.2 - Personnel App Design System Tests")
    print("="*60 + "\n")
    
    from django.core.management import call_command
    call_command('test', 'personnel.tests_design_system', verbosity=2)
    
    print("\n" + "="*60)
    print("Personnel Tests Complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_tests()
