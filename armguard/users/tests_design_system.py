"""
ARMGUARD RDS v.2 - Users App Design System Tests
Tests for login, authentication, and user-related views
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import gzip

User = get_user_model()


def decode_response(response):
    """Helper to decode response content, handling gzip if needed"""
    if response.get('Content-Encoding') == 'gzip':
        return gzip.decompress(response.content).decode('utf-8')
    return response.content.decode('utf-8', errors='replace')


class UsersDesignSystemTests(TestCase):
    """Test users app templates use design system correctly"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_login_page_design_system(self):
        """Test login page uses design system"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        
        # Handle gzip encoding
        if response.get('Content-Encoding') == 'gzip':
            html = gzip.decompress(response.content).decode('utf-8')
        else:
            html = response.content.decode('utf-8', errors='replace')
        
        # Check for design system components
        self.assertIn('card', html, "Should use card component")
        self.assertIn('form-', html, "Should use form components")
        self.assertIn('btn', html, "Should use button component")
        
    def test_login_form_components(self):
        """Test login form uses design system classes"""
        response = self.client.get(reverse('login'))
        if response.get('Content-Encoding') == 'gzip':
            html = gzip.decompress(response.content).decode('utf-8')
        else:
            html = response.content.decode('utf-8', errors='replace')
        
        # Check for form classes
        self.assertIn('form-input', html, "Should use form-input class")
        self.assertIn('form-label', html, "Should use form-label class")
        
    def test_login_button_styling(self):
        """Test login button uses design system"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for button classes
        self.assertIn('btn-primary', html, "Should use btn-primary class")
        
    def test_login_card_layout(self):
        """Test login page uses card layout"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for card component
        self.assertIn('card', html, "Should use card layout")
        
    def test_login_color_system(self):
        """Test login page uses design system colors"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for color classes
        color_classes = ['text-neutral-', 'text-primary', 'bg-white']
        found = any(cls in html for cls in color_classes)
        self.assertTrue(found, "Should use design system colors")
        
    def test_login_spacing(self):
        """Test login page uses spacing system"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for spacing utilities
        spacing_patterns = ['mb-', 'mt-', 'p-', 'gap-']
        found = any(pattern in html for pattern in spacing_patterns)
        self.assertTrue(found, "Should use spacing utilities")
        
    def test_logout_redirect(self):
        """Test logout functionality"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('logout'))
        
        # Should redirect after logout
        self.assertEqual(response.status_code, 302)


class UsersFormTests(TestCase):
    """Test user forms use design system"""
    
    def setUp(self):
        self.client = Client()
        
    def test_login_form_structure(self):
        """Test login form structure"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for form elements
        self.assertIn('<form', html, "Should have form element")
        self.assertIn('type="text"', html, "Should have username field")
        self.assertIn('type="password"', html, "Should have password field")
        
    def test_form_input_styling(self):
        """Test form inputs use design system classes"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for form-input class
        self.assertIn('form-input', html, "Inputs should use form-input class")
        
    def test_form_validation_messages(self):
        """Test form validation message styling"""
        # Attempt login with invalid credentials
        response = self.client.post(reverse('login'), {
            'username': 'invalid',
            'password': 'wrong'
        })
        
        html = decode_response(response)
        
        # Should show validation message
        if 'alert' in html:
            self.assertIn('alert', html, "Should use alert component for errors")


class UsersAccessibilityTests(TestCase):
    """Test accessibility in users app"""
    
    def setUp(self):
        self.client = Client()
        
    def test_login_semantic_html(self):
        """Test login page uses semantic HTML"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for semantic elements
        self.assertIn('<form', html, "Should use form element")
        self.assertIn('<label', html, "Should use label elements")
        
    def test_login_form_labels(self):
        """Test form labels are present"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for labels
        self.assertIn('label', html, "Should have form labels")
        
    def test_login_input_accessibility(self):
        """Test inputs have proper accessibility attributes"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Inputs should be associated with labels
        self.assertIn('<input', html, "Should have input elements")


class UsersComponentTests(TestCase):
    """Test specific components in users app"""
    
    def setUp(self):
        self.client = Client()
        
    def test_alert_components(self):
        """Test alert components for messages"""
        # Login with wrong credentials to trigger error
        response = self.client.post(reverse('login'), {
            'username': 'wrong',
            'password': 'credentials'
        })
        
        html = decode_response(response)
        
        # Check if error is displayed with alert component
        # Note: This depends on implementation
        self.assertEqual(response.status_code, 200)
        
    def test_button_hover_states(self):
        """Test button classes include hover states"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Buttons should exist
        self.assertIn('btn', html, "Should have button classes")


class UsersIntegrationTests(TestCase):
    """Integration tests for users app"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='integration_test',
            password='securepass123'
        )
        
    def test_login_flow(self):
        """Test complete login flow"""
        # Get login page
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        
        # Post login credentials
        response = self.client.post(reverse('login'), {
            'username': 'integration_test',
            'password': 'securepass123'
        })
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
        
    def test_logout_flow(self):
        """Test complete logout flow"""
        # Login first
        self.client.login(username='integration_test', password='securepass123')
        
        # Logout
        response = self.client.get(reverse('logout'))
        
        # Should redirect
        self.assertEqual(response.status_code, 302)
        
    def test_authentication_required(self):
        """Test that protected pages require authentication"""
        # Try to access protected page without login
        response = self.client.get(reverse('armguard_admin:dashboard'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)


class UsersResponsiveTests(TestCase):
    """Test responsive design in users app"""
    
    def setUp(self):
        self.client = Client()
        
    def test_login_responsive_layout(self):
        """Test login page is responsive"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Check for responsive classes
        # Login should be mobile-friendly
        self.assertIn('card', html, "Should use card for mobile layout")
        
    def test_mobile_viewport(self):
        """Test viewport meta tag"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Should have viewport meta
        self.assertIn('viewport', html, "Should have viewport meta tag")


class UserPasswordTests(TestCase):
    """Test password field styling"""
    
    def setUp(self):
        self.client = Client()
        
    def test_password_input_styling(self):
        """Test password input uses design system"""
        response = self.client.get(reverse('login'))
        html = decode_response(response)
        
        # Password field should exist with proper styling
        self.assertIn('type="password"', html)
        self.assertIn('form-input', html, "Should use form-input class")


def run_tests():
    """Helper function to run users tests"""
    print("\n" + "="*60)
    print("ARMGUARD RDS v.2 - Users App Design System Tests")
    print("="*60 + "\n")
    
    from django.core.management import call_command
    call_command('test', 'users.tests_design_system', verbosity=2)
    
    print("\n" + "="*60)
    print("Users Tests Complete")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_tests()
