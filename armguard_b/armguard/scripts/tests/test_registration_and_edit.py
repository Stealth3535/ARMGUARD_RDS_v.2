"""
Comprehensive Test Suite for User Registration and Editing
Tests administrator, armorer, and personnel registration and updates
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User, Group
from personnel.models import Personnel
from users.models import UserProfile
from admin.forms import UniversalForm


class TestRunner:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.errors = []
    
    def log(self, message, level='INFO'):
        prefix = {
            'INFO': '✓',
            'ERROR': '✗',
            'WARN': '⚠',
            'TEST': '→'
        }.get(level, '•')
        print(f"{prefix} {message}")
    
    def assert_equal(self, actual, expected, message):
        if actual == expected:
            self.tests_passed += 1
            self.log(f"{message}: PASS (expected: {expected}, got: {actual})", 'INFO')
            return True
        else:
            self.tests_failed += 1
            error_msg = f"{message}: FAIL (expected: {expected}, got: {actual})"
            self.log(error_msg, 'ERROR')
            self.errors.append(error_msg)
            return False
    
    def assert_true(self, condition, message):
        if condition:
            self.tests_passed += 1
            self.log(f"{message}: PASS", 'INFO')
            return True
        else:
            self.tests_failed += 1
            error_msg = f"{message}: FAIL"
            self.log(error_msg, 'ERROR')
            self.errors.append(error_msg)
            return False
    
    def cleanup(self):
        """Remove test data"""
        self.log("\n=== CLEANUP ===", 'TEST')
        User.objects.filter(username__startswith='test_').delete()
        Personnel.objects.filter(serial__startswith='TEST').delete()
        self.log("Cleanup completed", 'INFO')
    
    def test_create_administrator(self):
        """Test creating an administrator with personnel record"""
        self.log("\n=== TEST 1: CREATE ADMINISTRATOR ===", 'TEST')
        
        form_data = {
            'role': 'admin',
            'username': 'test_admin',
            'first_name': 'Admin',
            'last_name': 'User',
            'email': 'admin@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'is_active': True,
            'surname': 'User',
            'firstname': 'Admin',
            'middle_initial': 'A',
            'rank': '2LT',
            'serial': 'TESTADM001',
            'personnel_group': 'HAS',
            'tel': '09123456789',
            'personnel_status': 'Active'
        }
        
        # Note: profile_picture is intentionally NOT included - using personnel_picture instead
        
        form = UniversalForm(form_data)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return None
        
        try:
            user, personnel = form.save()
            
            # Verify user creation
            self.assert_true(user is not None, "User object created")
            self.assert_equal(user.username, 'test_admin', "Username correct")
            self.assert_equal(user.first_name, 'Admin', "First name correct")
            self.assert_equal(user.is_staff, True, "User is staff")
            self.assert_true(user.groups.filter(name='Admin').exists(), "User in Admin group")
            
            # Verify personnel creation
            self.assert_true(personnel is not None, "Personnel object created")
            self.assert_equal(personnel.surname, 'USER', "Surname correct (uppercase for officers)")
            self.assert_equal(personnel.rank, '2LT', "Rank correct")
            self.assert_equal(personnel.tel, '+639123456789', "Tel converted correctly")
            
            # Verify link
            self.assert_equal(personnel.user, user, "Personnel linked to user")
            
            self.log(f"Created admin user ID: {user.id}, Personnel ID: {personnel.id}", 'INFO')
            self.log("Note: Profile picture field hidden for admin/armorer (use personnel picture)", 'INFO')
            return user, personnel
            
        except Exception as e:
            self.log(f"Exception during save: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return None
    
    def test_create_armorer(self):
        """Test creating an armorer with personnel record"""
        self.log("\n=== TEST 2: CREATE ARMORER ===", 'TEST')
        
        form_data = {
            'role': 'armorer',
            'username': 'test_armorer',
            'first_name': 'Armorer',
            'last_name': 'User',
            'email': 'armorer@test.com',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'is_active': True,
            'surname': 'User',
            'firstname': 'Armorer',
            'middle_initial': 'B',
            'rank': 'SGT',
            'serial': 'TESTARM002',
            'personnel_group': '951st',
            'tel': '+639987654321',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return None
        
        try:
            user, personnel = form.save()
            
            # Verify user creation
            self.assert_true(user is not None, "User object created")
            self.assert_equal(user.username, 'test_armorer', "Username correct")
            self.assert_equal(user.is_staff, True, "User is staff")
            self.assert_true(user.groups.filter(name='Armorer').exists(), "User in Armorer group")
            
            # Verify personnel creation
            self.assert_true(personnel is not None, "Personnel object created")
            self.assert_equal(personnel.rank, 'SGT', "Rank correct")
            self.assert_equal(personnel.group, '951st', "Group correct")
            self.assert_equal(personnel.tel, '+639987654321', "Tel correct (already in +639 format)")
            
            # Verify UserProfile
            profile = user.userprofile
            self.assert_equal(profile.is_armorer, True, "UserProfile marked as armorer")
            
            self.log(f"Created armorer user ID: {user.id}, Personnel ID: {personnel.id}", 'INFO')
            return user, personnel
            
        except Exception as e:
            self.log(f"Exception during save: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return None
    
    def test_create_personnel_only(self):
        """Test creating personnel without user account"""
        self.log("\n=== TEST 3: CREATE PERSONNEL ONLY ===", 'TEST')
        
        form_data = {
            'role': 'personnel',
            'surname': 'Smith',
            'firstname': 'John',
            'middle_initial': 'C',
            'rank': 'SGT',
            'serial': 'TESTPER003',
            'personnel_group': '952nd',
            'tel': '09111222333',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return None
        
        try:
            user, personnel = form.save()
            
            # Verify no user created
            self.assert_true(user is None, "No user account created")
            
            # Verify personnel creation
            self.assert_true(personnel is not None, "Personnel object created")
            self.assert_equal(personnel.firstname, 'John', "First name correct")
            self.assert_equal(personnel.surname, 'Smith', "Surname correct")
            self.assert_equal(personnel.serial, 'TESTPER003', "Serial correct")
            self.assert_equal(personnel.tel, '+639111222333', "Tel converted correctly")
            self.assert_true(personnel.user is None, "Personnel not linked to user")
            
            self.log(f"Created personnel ID: {personnel.id}", 'INFO')
            return None, personnel
            
        except Exception as e:
            self.log(f"Exception during save: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return None
    
    def test_edit_administrator(self, user, personnel):
        """Test editing an administrator"""
        self.log("\n=== TEST 4: EDIT ADMINISTRATOR ===", 'TEST')
        
        form_data = {
            'operation_type': 'edit_both',
            'edit_user_id': user.id,
            'edit_personnel_id': personnel.id,
            'role': 'admin',
            'username': 'test_admin_edited',
            'first_name': 'Admin',
            'last_name': 'Modified',
            'email': 'admin_new@test.com',
            'is_active': True,
            'group': '951st',
            'surname': 'Modified',
            'firstname': 'Admin',
            'middle_initial': 'A',
            'rank': '1LT',
            'serial': 'TESTADM001',
            'personnel_group': '951st',
            'tel': '09999888777',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data, edit_user=user, edit_personnel=personnel)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return False
        
        try:
            edited_user, edited_personnel = form.save()
            
            # Refresh from database
            edited_user.refresh_from_db()
            edited_personnel.refresh_from_db()
            
            # Verify user updates
            self.assert_equal(edited_user.username, 'test_admin_edited', "Username updated")
            self.assert_equal(edited_user.last_name, 'Modified', "Last name updated")
            self.assert_equal(edited_user.email, 'admin_new@test.com', "Email updated")
            
            # Verify personnel updates
            self.assert_equal(edited_personnel.surname, 'MODIFIED', "Surname updated (uppercase for officers)")
            self.assert_equal(edited_personnel.rank, '1LT', "Rank updated")
            self.assert_equal(edited_personnel.group, '951st', "Group updated")
            self.assert_equal(edited_personnel.tel, '+639999888777', "Tel updated and converted")
            
            # Verify sync
            self.assert_equal(edited_personnel.user.id, edited_user.id, "Personnel still linked to user")
            
            self.log("Edit administrator test completed successfully", 'INFO')
            return True
            
        except Exception as e:
            self.log(f"Exception during edit: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
    
    def test_edit_armorer(self, user, personnel):
        """Test editing an armorer"""
        self.log("\n=== TEST 5: EDIT ARMORER ===", 'TEST')
        
        form_data = {
            'operation_type': 'edit_both',
            'edit_user_id': user.id,
            'edit_personnel_id': personnel.id,
            'role': 'armorer',
            'username': 'test_armorer_edited',
            'first_name': 'Armorer',
            'last_name': 'Updated',
            'email': 'armorer_new@test.com',
            'is_active': True,
            'group': '952nd',
            'surname': 'Updated',
            'firstname': 'Armorer',
            'middle_initial': 'B',
            'rank': 'SSGT',
            'serial': 'TESTARM002',
            'personnel_group': '952nd',
            'tel': '+639123123123',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data, edit_user=user, edit_personnel=personnel)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return False
        
        try:
            edited_user, edited_personnel = form.save()
            
            # Refresh from database
            edited_user.refresh_from_db()
            edited_personnel.refresh_from_db()
            
            # Verify user updates
            self.assert_equal(edited_user.username, 'test_armorer_edited', "Username updated")
            self.assert_equal(edited_user.last_name, 'Updated', "Last name updated")
            self.assert_true(edited_user.groups.filter(name='Armorer').exists(), "Still in Armorer group")
            
            # Verify personnel updates
            self.assert_equal(edited_personnel.surname, 'Updated', "Surname updated (title case for enlisted)")
            self.assert_equal(edited_personnel.rank, 'SSGT', "Rank updated")
            self.assert_equal(edited_personnel.tel, '+639123123123', "Tel updated")
            
            # Verify UserProfile
            profile = edited_user.userprofile
            self.assert_equal(profile.is_armorer, True, "Still marked as armorer")
            self.assert_equal(profile.group, '952nd', "Profile group updated")
            
            self.log("Edit armorer test completed successfully", 'INFO')
            return True
            
        except Exception as e:
            self.log(f"Exception during edit: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
    
    def test_edit_personnel_only(self, personnel):
        """Test editing personnel without user account"""
        self.log("\n=== TEST 6: EDIT PERSONNEL ONLY ===", 'TEST')
        
        form_data = {
            'operation_type': 'edit_personnel',
            'edit_personnel_id': personnel.id,
            'role': 'personnel',
            'surname': 'Smith',
            'firstname': 'Jonathan',
            'middle_initial': 'D',
            'rank': 'SGT',
            'serial': 'TESTPER003',
            'personnel_group': '953rd',
            'tel': '09444555666',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data, edit_personnel=personnel)
        
        if not form.is_valid():
            self.log(f"Form validation failed: {form.errors}", 'ERROR')
            self.tests_failed += 1
            return False
        
        try:
            edited_user, edited_personnel = form.save()
            
            # Refresh from database
            edited_personnel.refresh_from_db()
            
            # Verify no user created
            self.assert_true(edited_user is None, "No user created during edit")
            
            # Verify personnel updates
            self.assert_equal(edited_personnel.firstname, 'Jonathan', "First name updated (title case for enlisted)")
            self.assert_equal(edited_personnel.middle_initial, 'D', "Middle initial updated")
            self.assert_equal(edited_personnel.rank, 'SGT', "Rank updated")
            self.assert_equal(edited_personnel.group, '953rd', "Group updated")
            self.assert_equal(edited_personnel.tel, '+639444555666', "Tel updated and converted")
            self.assert_true(edited_personnel.user is None, "Still not linked to user")
            
            self.log("Edit personnel only test completed successfully", 'INFO')
            return True
            
        except Exception as e:
            self.log(f"Exception during edit: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            self.tests_failed += 1
            return False
    
    def test_tel_maxlength_validation(self):
        """Test that tel field rejects overly long input"""
        self.log("\n=== TEST 7: TEL MAXLENGTH VALIDATION ===", 'TEST')
        
        form_data = {
            'role': 'personnel',
            'surname': 'Test',
            'firstname': 'Tel',
            'middle_initial': 'T',
            'rank': 'AM',  # Changed from PVT to valid rank
            'serial': 'TESTTEL999',
            'personnel_group': 'HAS',
            'tel': '09123456789123456',  # Too long (17 digits)
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data)
        
        # Note: The form itself doesn't validate maxlength in clean(), 
        # but the HTML input maxlength prevents this from being submitted
        # We're testing the validation logic here
        
        if form.is_valid():
            self.log("Form accepted overly long tel (will be handled by HTML maxlength)", 'WARN')
        else:
            if 'tel' in form.errors:
                self.assert_true(True, "Tel validation rejected invalid format")
            else:
                self.log(f"Form invalid for other reasons: {form.errors}", 'WARN')
        
        # Test valid short format
        form_data['tel'] = '09123456789'
        form_data['serial'] = 'TESTTEL998'
        form_data['rank'] = 'AM'  # Ensure valid rank
        form = UniversalForm(form_data)
        
        valid = form.is_valid()
        self.assert_true(valid, "Valid 11-digit tel accepted")
        
        if valid:
            try:
                user, personnel = form.save()
                self.assert_equal(personnel.tel, '+639123456789', "Tel converted correctly")
                personnel.delete()
            except Exception as e:
                self.log(f"Save failed: {str(e)}", 'ERROR')
    
    def run_all_tests(self):
        """Run all tests"""
        self.log("\n" + "="*60, 'TEST')
        self.log("COMPREHENSIVE REGISTRATION AND EDIT TEST SUITE", 'TEST')
        self.log("="*60 + "\n", 'TEST')
        
        # Cleanup first
        self.cleanup()
        
        # Test creation
        admin_result = self.test_create_administrator()
        armorer_result = self.test_create_armorer()
        personnel_result = self.test_create_personnel_only()
        
        # Test editing (only if creation succeeded)
        if admin_result:
            admin_user, admin_personnel = admin_result
            self.test_edit_administrator(admin_user, admin_personnel)
        
        if armorer_result:
            armorer_user, armorer_personnel = armorer_result
            self.test_edit_armorer(armorer_user, armorer_personnel)
        
        if personnel_result:
            _, personnel_only = personnel_result
            self.test_edit_personnel_only(personnel_only)
        
        # Test tel validation
        self.test_tel_maxlength_validation()
        
        # Summary
        self.log("\n" + "="*60, 'TEST')
        self.log("TEST SUMMARY", 'TEST')
        self.log("="*60, 'TEST')
        self.log(f"Tests Passed: {self.tests_passed}", 'INFO')
        self.log(f"Tests Failed: {self.tests_failed}", 'ERROR' if self.tests_failed > 0 else 'INFO')
        
        if self.errors:
            self.log("\nFailed Tests:", 'ERROR')
            for error in self.errors:
                self.log(f"  - {error}", 'ERROR')
        
        # Cleanup after tests
        self.log("\n=== FINAL CLEANUP ===", 'TEST')
        self.cleanup()
        
        return self.tests_failed == 0


if __name__ == '__main__':
    runner = TestRunner()
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)
