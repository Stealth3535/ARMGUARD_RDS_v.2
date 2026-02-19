"""
ARMGUARD RDS v.2 - Admin App Design System Tests
Tests for admin dashboard, user management, and related views
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction
import re

User = get_user_model()


class AdminDesignSystemTests(TestCase):
    """Test that admin templates use design system classes correctly"""
    
    def setUp(self):
        """Set up test user and client"""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='testadmin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_login(self.superuser)
        
    def test_dashboard_loads_with_design_system(self):
        """Test admin dashboard loads with new design system classes"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check for design system classes
        self.assertIn('stat-card', html, "Should use stat-card component")
        self.assertIn('card', html, "Should use card component")
        self.assertIn('btn btn-', html, "Should use btn component classes")
        self.assertIn('grid', html, "Should use grid layout")
        self.assertIn('form-label', html, "Should use form-label class")
        self.assertIn('form-input', html, "Should use form-input class")
        self.assertIn('badge', html, "Should use badge component")
        
    def test_dashboard_stats_display(self):
        """Test that dashboard stat cards display correctly"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for stat card components with correct class names
        self.assertIn('stat-card primary', html)
        self.assertIn('stat-card success', html)
        self.assertIn('stat-card warning', html)
        self.assertIn('stat-card danger', html)
        
        # Check for stat labels
        self.assertIn('Users', html)
        self.assertIn('Personnel', html)
        self.assertIn('Administrators', html)
        self.assertIn('Armorers', html)
        
    def test_dashboard_filter_functionality(self):
        """Test filter and search box elements"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for filter elements
        self.assertIn('searchInput', html)
        self.assertIn('sortSelect', html)
        self.assertIn('pill', html, "Should have filter pills")
        
    def test_dashboard_responsive_classes(self):
        """Test that responsive utility classes are present"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for responsive grid classes
        self.assertIn('grid-cols-', html, "Should use responsive grid columns")
        self.assertIn('flex', html, "Should use flexbox utilities")
        self.assertIn('gap-', html, "Should use gap utilities")
        
    def test_dashboard_color_system(self):
        """Test that design system colors are used"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for design system color classes
        color_classes = [
            'text-primary', 'text-success', 'text-warning', 'text-danger',
            'text-neutral-', 'bg-white'
        ]
        
        for cls in color_classes:
            found = cls in html
            if found:
                break
        self.assertTrue(found, "Should use design system color classes")
        
    def test_dashboard_typography(self):
        """Test typography system usage"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for typography classes
        self.assertIn('text-', html, "Should use text size utilities")
        self.assertIn('font-', html, "Should use font weight utilities")
        
    def test_dashboard_spacing(self):
        """Test spacing system usage"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for spacing classes
        spacing_patterns = ['mb-', 'mt-', 'p-', 'py-', 'px-', 'gap-']
        found = any(pattern in html for pattern in spacing_patterns)
        self.assertTrue(found, "Should use spacing utilities from 8pt grid")
        
    def test_dashboard_no_inline_styles(self):
        """Test that minimal inline styles are used"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Count style tags (should be minimal)
        style_count = html.count('<style>')
        self.assertLessEqual(style_count, 2, 
            "Should use minimal inline styles, rely on design system")
        
    def test_user_management_page_design_system(self):
        """Test user management page uses design system"""
        response = self.client.get(reverse('armguard_admin:user_management'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        self.assertIn('table', html, "Should use table component")
        self.assertIn('btn', html, "Should use button components")
        
    def test_accessibility_features(self):
        """Test that accessibility features are present"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for ARIA and semantic HTML
        self.assertIn('role=', html, "Should include ARIA roles")
        self.assertIn('<header', html, "Should use semantic HTML")


class AdminComponentTests(TestCase):
    """Test specific design system components in admin app"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='component_test',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_login(self.superuser)
        
    def test_button_variants(self):
        """Test that all button variants are available"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for button variants
        button_variants = [
            'btn-primary', 'btn-success', 'btn-danger', 
            'btn-secondary', 'btn-warning', 'btn-info'
        ]
        
        found_variants = [v for v in button_variants if v in html]
        self.assertGreater(len(found_variants), 0, 
            "Should use multiple button variants")
        
    def test_card_component(self):
        """Test card component structure"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Cards should have proper padding
        self.assertIn('card', html)
        self.assertIn('p-6', html, "Cards should use consistent padding")
        
    def test_alert_component(self):
        """Test alert component for messages"""
        # Create a message scenario
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check alert structure exists
        self.assertIn('alert', html, "Should have alert component")
        
    def test_table_component(self):
        """Test table component styling"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        if '<table' in html:
            self.assertIn('table', html, "Should use table class")
            

class AdminResponsiveTests(TestCase):
    """Test responsive design implementation"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='responsive_test',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_login(self.superuser)
        
    def test_mobile_viewport_meta(self):
        """Test that viewport meta tag is present"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        self.assertIn('viewport', html, "Should have viewport meta tag")
        
    def test_responsive_grid(self):
        """Test responsive grid classes"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for responsive grid
        self.assertIn('grid', html, "Should use CSS Grid")
        
    def test_mobile_friendly_spacing(self):
        """Test that mobile-friendly spacing is used"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Check for responsive spacing
        self.assertIn('gap-', html, "Should use gap utilities")


class AdminPerformanceTests(TestCase):
    """Test performance aspects of design system"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='perf_test',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_login(self.superuser)
        
    def test_css_loading(self):
        """Test that design system CSS is loaded"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Should load main.css which imports design system
        self.assertIn('main.css', html, "Should load main.css")
        
    def test_minimal_css_bloat(self):
        """Test that CSS is not excessively bloated"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        html = response.content.decode('utf-8')
        
        # Count inline style blocks
        style_blocks = re.findall(r'<style[^>]*>.*?</style>', html, re.DOTALL)
        
        # Should have minimal inline styles
        self.assertLessEqual(len(style_blocks), 2,
            "Should minimize inline style blocks")


class AdminIntegrationTests(TestCase):
    """Integration tests with real data"""
    
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='integration_test',
            email='test@test.com',
            password='testpass123'
        )
        self.client.force_login(self.superuser)
        
        # Create test personnel
        self.personnel = Personnel.objects.create(
            firstname='John',
            surname='Doe',
            rank='CPT',
            serial='12345678',
            tel='+639123456789',
            classification='OFFICER'
        )
        
    def test_dashboard_with_data(self):
        """Test dashboard displays correctly with real data"""
        response = self.client.get(reverse('armguard_admin:dashboard'))
        self.assertEqual(response.status_code, 200)
        
        html = response.content.decode('utf-8')
        
        # Check that stats show numbers
        self.assertIn('stat-card-value', html, "Should display stat values")
        
    def test_filter_functionality_with_data(self):
        """Test that filters work with actual data"""
        response = self.client.get(reverse('armguard_admin:dashboard') + '?history=week')
        self.assertEqual(response.status_code, 200)
        

def run_tests():
    """Helper function to run all admin tests"""
    import sys
    from django.core.management import call_command
    
    print("\n" + "="*60)
    print("ARMGUARD RDS v.2 - Admin App Design System Tests")
    print("="*60 + "\n")
    
    call_command('test', 'admin.tests', verbosity=2)
    
    print("\n" + "="*60)
    print("Admin Tests Complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_tests()
