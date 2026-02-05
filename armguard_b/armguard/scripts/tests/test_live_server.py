"""
Live Server Test - Test Registration and Editing Directly
Tests the form functionality and database operations
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel
from users.models import UserProfile
from admin.forms import UniversalForm


class LiveServerTester:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
        self.created_users = []
        self.created_personnel = []
    
    def log(self, message, level='INFO'):
        prefix = {
            'INFO': '✓',
            'ERROR': '✗',
            'WARN': '⚠',
            'TEST': '→'
        }.get(level, '•')
        print(f"{prefix} {message}")
    
    def cleanup(self):
        """Remove test data created during tests"""
        self.log("\n=== CLEANUP ===", 'TEST')
        for username in self.created_users:
            try:
                User.objects.filter(username=username).delete()
                self.log(f"Deleted user: {username}", 'INFO')
            except:
                pass
        
        for serial in self.created_personnel:
            try:
                Personnel.objects.filter(serial=serial).delete()
                self.log(f"Deleted personnel: {serial}", 'INFO')
            except:
                pass
        
        self.log("Cleanup completed", 'INFO')
    
    def test_administrator_registration(self):
        """Test creating an administrator via UniversalForm"""
        self.log("\n=== TEST 1: ADMINISTRATOR REGISTRATION ===", 'TEST')
        
        form_data = {
            'role': 'admin',
            'username': 'live_admin_test',
            'first_name': 'Admin',
            'last_name': 'Live',
            'email': 'adminlive@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'is_active': True,
            'surname': 'Live',
            'firstname': 'Admin',
            'middle_initial': 'L',
            'rank': '2LT',
            'serial': 'LIVEADM001',
            'personnel_group': 'HAS',
            'tel': '09123456789',
            'personnel_status': 'Active'
        }
        
        try:
            form = UniversalForm(form_data)
            
            if not form.is_valid():
                self.tests_failed += 1
                self.log(f"Form validation failed: {form.errors}", 'ERROR')
                return
            
            user, personnel = form.save()
            
            self.tests_passed += 1
            self.log("✓ Admin user created successfully", 'INFO')
            self.created_users.append('live_admin_test')
            
            # Verify user properties
            if user.is_staff:
                self.tests_passed += 1
                self.log("✓ User is staff", 'INFO')
            else:
                self.tests_failed += 1
                self.log("✗ User is not staff", 'ERROR')
            
            if user.groups.filter(name='Admin').exists():
                self.tests_passed += 1
                self.log("✓ User in Admin group", 'INFO')
            else:
                self.tests_failed += 1
                self.log("✗ User not in Admin group", 'ERROR')
            
            # Check personnel
            if personnel:
                self.tests_passed += 1
                self.log(f"✓ Personnel created: {personnel.id}", 'INFO')
                self.created_personnel.append('LIVEADM001')
                
                # Check tel conversion
                if personnel.tel == '+639123456789':
                    self.tests_passed += 1
                    self.log("✓ Tel converted correctly: +639123456789", 'INFO')
                else:
                    self.tests_failed += 1
                    self.log(f"✗ Tel incorrect: {personnel.tel}", 'ERROR')
                
                # Check officer name uppercase
                if personnel.surname == 'LIVE':
                    self.tests_passed += 1
                    self.log("✓ Officer surname uppercase: LIVE", 'INFO')
                else:
                    self.tests_failed += 1
                    self.log(f"✗ Surname not uppercase: {personnel.surname}", 'ERROR')
            else:
                self.tests_failed += 1
                self.log("✗ Personnel not created", 'ERROR')
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"Exception: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
    
    def test_armorer_registration(self):
        """Test creating an armorer via the registration form"""
        self.log("\n=== TEST 2: ARMORER REGISTRATION (LIVE) ===", 'TEST')
        
        form_data = {
            'role': 'armorer',
            'username': 'live_armorer_test',
            'first_name': 'Armorer',
            'last_name': 'Live',
            'email': 'armorerlive@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'is_active': True,
            'surname': 'Live',
            'firstname': 'Armorer',
            'middle_initial': 'A',
            'rank': 'SGT',
            'serial': 'LIVEARM002',
            'personnel_group': '951st',
            'tel': '+639987654321',
            'personnel_status': 'Active'
        }
        
        try:
            response = self.client.post('/admin/register/', form_data, follow=True)
            
            self.log(f"Response status: {response.status_code}", 'INFO')
            
            user = User.objects.filter(username='live_armorer_test').first()
            if user:
                self.tests_passed += 1
                self.log("✓ Armorer user created", 'INFO')
                self.created_users.append('live_armorer_test')
                
                if user.groups.filter(name='Armorer').exists():
                    self.tests_passed += 1
                    self.log("✓ User in Armorer group", 'INFO')
                
                personnel = Personnel.objects.filter(serial='LIVEARM002').first()
                if personnel:
                    self.tests_passed += 1
                    self.log(f"✓ Personnel created: {personnel.id}", 'INFO')
                    self.created_personnel.append('LIVEARM002')
                    
                    # Check enlisted name title case
                    if personnel.surname == 'Live':
                        self.tests_passed += 1
                        self.log("✓ Enlisted surname title case: Live", 'INFO')
                    else:
                        self.tests_failed += 1
                        self.log(f"✗ Surname not title case: {personnel.surname}", 'ERROR')
            else:
                self.tests_failed += 1
                self.log("✗ Armorer user not created", 'ERROR')
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"Exception: {str(e)}", 'ERROR')
    
    def test_personnel_only_registration(self):
        """Test creating personnel without user account"""
        self.log("\n=== TEST 3: PERSONNEL ONLY REGISTRATION (LIVE) ===", 'TEST')
        
        form_data = {
            'role': 'personnel',
            'surname': 'LiveTest',
            'firstname': 'Personnel',
            'middle_initial': 'P',
            'rank': 'AM',
            'serial': 'LIVEPER003',
            'personnel_group': '952nd',
            'tel': '09111222333',
            'personnel_status': 'Active'
        }
        
        try:
            response = self.client.post('/admin/register/', form_data, follow=True)
            
            self.log(f"Response status: {response.status_code}", 'INFO')
            
            personnel = Personnel.objects.filter(serial='LIVEPER003').first()
            if personnel:
                self.tests_passed += 1
                self.log(f"✓ Personnel created: {personnel.id}", 'INFO')
                self.created_personnel.append('LIVEPER003')
                
                # Check no user linked
                if personnel.user is None:
                    self.tests_passed += 1
                    self.log("✓ No user account linked", 'INFO')
                else:
                    self.tests_failed += 1
                    self.log("✗ User account incorrectly linked", 'ERROR')
                
                # Check tel conversion
                if personnel.tel == '+639111222333':
                    self.tests_passed += 1
                    self.log("✓ Tel converted correctly", 'INFO')
                else:
                    self.tests_failed += 1
                    self.log(f"✗ Tel incorrect: {personnel.tel}", 'ERROR')
            else:
                self.tests_failed += 1
                self.log("✗ Personnel not created", 'ERROR')
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"Exception: {str(e)}", 'ERROR')
    
    def test_edit_functionality(self):
        """Test editing a user/personnel"""
        self.log("\n=== TEST 4: EDIT FUNCTIONALITY (LIVE) ===", 'TEST')
        
        # First create a user to edit
        user = User.objects.filter(username='live_admin_test').first()
        if not user:
            self.log("No test user found to edit, skipping", 'WARN')
            return
        
        personnel = Personnel.objects.filter(user=user).first()
        if not personnel:
            self.log("No test personnel found to edit, skipping", 'WARN')
            return
        
        self.log(f"Editing user: {user.username}, personnel: {personnel.id}", 'INFO')
        
        # Try to edit
        form_data = {
            'operation_type': 'edit_both',
            'edit_user_id': user.id,
            'edit_personnel_id': personnel.id,
            'role': 'admin',
            'username': 'live_admin_test',
            'first_name': 'Admin',
            'last_name': 'Edited',
            'email': 'edited@test.com',
            'is_active': True,
            'group': '951st',
            'surname': 'Edited',
            'firstname': 'Admin',
            'middle_initial': 'E',
            'rank': '1LT',
            'serial': 'LIVEADM001',
            'personnel_group': '951st',
            'tel': '09999888777',
            'personnel_status': 'Active'
        }
        
        try:
            # Try editing via the user edit endpoint
            url = f'/admin/users/{user.id}/edit/'
            response = self.client.post(url, form_data, follow=True)
            
            self.log(f"Response status: {response.status_code}", 'INFO')
            
            # Refresh from database
            user.refresh_from_db()
            personnel.refresh_from_db()
            
            # Check updates
            if user.last_name == 'Edited':
                self.tests_passed += 1
                self.log("✓ User last name updated", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ User last name not updated: {user.last_name}", 'ERROR')
            
            if personnel.tel == '+639999888777':
                self.tests_passed += 1
                self.log("✓ Personnel tel updated and converted", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ Personnel tel not updated: {personnel.tel}", 'ERROR')
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"Exception: {str(e)}", 'ERROR')
    
    def test_tel_maxlength_html(self):
        """Test that HTML form has maxlength attribute on tel field"""
        self.log("\n=== TEST 5: TEL FIELD MAXLENGTH ATTRIBUTE ===", 'TEST')
        
        try:
            response = self.client.get('/admin/register/')
            content = response.content.decode('utf-8')
            
            # Check for tel field with maxlength
            if 'name="tel"' in content:
                self.tests_passed += 1
                self.log("✓ Tel field found in HTML", 'INFO')
                
                # Check for maxlength attribute
                if 'maxlength="13"' in content or "maxlength='13'" in content:
                    self.tests_passed += 1
                    self.log("✓ Tel field has maxlength='13' attribute", 'INFO')
                else:
                    self.tests_failed += 1
                    self.log("✗ Tel field missing maxlength='13' attribute", 'ERROR')
                    # Show snippet around tel field
                    import re
                    tel_match = re.search(r'.{0,200}name="tel".{0,200}', content, re.DOTALL)
                    if tel_match:
                        self.log(f"Tel field HTML: {tel_match.group(0)[:200]}", 'WARN')
            else:
                self.tests_failed += 1
                self.log("✗ Tel field not found in HTML", 'ERROR')
        
        except Exception as e:
            self.tests_failed += 1
            self.log(f"Exception: {str(e)}", 'ERROR')
    
    def run_all_tests(self):
        """Run all live server tests"""
        self.log("\n" + "="*60, 'TEST')
        self.log("LIVE SERVER TEST SUITE", 'TEST')
        self.log("Testing: http://192.168.59.138:8000", 'TEST')
        self.log("="*60 + "\n", 'TEST')
        
        # Login first
        self.login_as_superuser()
        
        # Run tests
        self.test_tel_maxlength_html()
        self.test_administrator_registration()
        self.test_armorer_registration()
        self.test_personnel_only_registration()
        self.test_edit_functionality()
        
        # Summary
        self.log("\n" + "="*60, 'TEST')
        self.log("TEST SUMMARY", 'TEST')
        self.log("="*60, 'TEST')
        self.log(f"Tests Passed: {self.tests_passed}", 'INFO')
        self.log(f"Tests Failed: {self.tests_failed}", 'ERROR' if self.tests_failed > 0 else 'INFO')
        
        if self.errors:
            self.log("\nErrors:", 'ERROR')
            for error in self.errors:
                self.log(f"  - {error}", 'ERROR')
        
        # Cleanup
        self.cleanup()
        
        return self.tests_failed == 0


if __name__ == '__main__':
    tester = LiveServerTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
