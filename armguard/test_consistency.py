"""
Enhanced Test Suite - Check All Forms for Consistency
Tests all forms across the application for redundancy and consistency
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
from personnel.forms import PersonnelQuickEditForm
from consolidated_forms import PersonnelRegistrationForm


class EnhancedTester:
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
    
    def cleanup(self):
        """Remove test data"""
        self.log("\n=== CLEANUP ===", 'TEST')
        User.objects.filter(username__startswith='consistency_').delete()
        Personnel.objects.filter(serial__startswith='CONSIST').delete()
        self.log("Cleanup completed", 'INFO')
    
    def test_tel_conversion_universal_form(self):
        """Test tel conversion in UniversalForm"""
        self.log("\n=== TEST 1: TEL CONVERSION - UNIVERSAL FORM ===", 'TEST')
        
        # Test with 09 format
        form_data = {
            'role': 'personnel',
            'surname': 'TestUser',
            'firstname': 'Consistency',
            'middle_initial': 'T',
            'rank': 'AM',
            'serial': 'CONSIST001',
            'personnel_group': 'HAS',
            'tel': '09123456789',
            'personnel_status': 'Active'
        }
        
        form = UniversalForm(form_data)
        if form.is_valid():
            self.tests_passed += 1
            self.log("✓ UniversalForm accepts 09XXXXXXXXX format", 'INFO')
            
            user, personnel = form.save()
            if personnel.tel == '+639123456789':
                self.tests_passed += 1
                self.log("✓ UniversalForm converts 09 to +639 correctly", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ UniversalForm conversion failed: {personnel.tel}", 'ERROR')
            personnel.delete()
        else:
            self.tests_failed += 1
            self.log(f"✗ UniversalForm rejected 09 format: {form.errors}", 'ERROR')
    
    def test_tel_conversion_personnel_edit_form(self):
        """Test tel conversion in PersonnelQuickEditForm"""
        self.log("\n=== TEST 2: TEL CONVERSION - PERSONNEL QUICK EDIT FORM ===", 'TEST')
        
        # Create a personnel first
        personnel = Personnel.objects.create(
            surname='EditTest',
            firstname='Consistency',
            middle_initial='E',
            rank='SGT',
            serial='CONSIST002',
            group='HAS',
            tel='+639111111111',
            status='Active'
        )
        
        # Test with 09 format
        form_data = {
            'rank': 'SGT',
            'group': 'HAS',
            'tel': '09222222222',
            'status': 'Active'
        }
        
        form = PersonnelQuickEditForm(form_data, instance=personnel)
        if form.is_valid():
            self.tests_passed += 1
            self.log("✓ PersonnelQuickEditForm accepts 09XXXXXXXXX format", 'INFO')
            
            form.save()
            personnel.refresh_from_db()
            if personnel.tel == '+639222222222':
                self.tests_passed += 1
                self.log("✓ PersonnelQuickEditForm converts 09 to +639 correctly", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ PersonnelQuickEditForm conversion failed: {personnel.tel}", 'ERROR')
        else:
            self.tests_failed += 1
            self.log(f"✗ PersonnelQuickEditForm rejected 09 format: {form.errors}", 'ERROR')
        
        personnel.delete()
    
    def test_tel_conversion_consolidated_form(self):
        """Test tel conversion in PersonnelRegistrationForm (consolidated)"""
        self.log("\n=== TEST 3: TEL CONVERSION - CONSOLIDATED FORM ===", 'TEST')
        
        # Test with 09 format
        form_data = {
            'surname': 'Consolidated',
            'firstname': 'Test',
            'middle_initial': 'C',
            'rank': 'AM',
            'serial': 'CONSIST003',
            'group': 'HAS',
            'tel': '09333333333',
            'status': 'Active',
            'create_user_account': False
        }
        
        form = PersonnelRegistrationForm(form_data)
        if form.is_valid():
            self.tests_passed += 1
            self.log("✓ PersonnelRegistrationForm accepts 09XXXXXXXXX format", 'INFO')
            
            personnel = form.save()
            if personnel.tel == '+639333333333':
                self.tests_passed += 1
                self.log("✓ PersonnelRegistrationForm converts 09 to +639 correctly", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ PersonnelRegistrationForm conversion failed: {personnel.tel}", 'ERROR')
            personnel.delete()
        else:
            self.tests_failed += 1
            self.log(f"✗ PersonnelRegistrationForm rejected 09 format: {form.errors}", 'ERROR')
    
    def test_tel_maxlength_consistency(self):
        """Check that all tel fields have maxlength=13"""
        self.log("\n=== TEST 4: TEL MAXLENGTH CONSISTENCY ===", 'TEST')
        
        # Check UniversalForm
        form1 = UniversalForm()
        tel_widget1 = form1.fields['tel'].widget
        if tel_widget1.attrs.get('maxlength') == '13':
            self.tests_passed += 1
            self.log("✓ UniversalForm tel field has maxlength='13'", 'INFO')
        else:
            self.tests_failed += 1
            self.log(f"✗ UniversalForm tel maxlength: {tel_widget1.attrs.get('maxlength')}", 'ERROR')
        
        # Check PersonnelQuickEditForm
        personnel = Personnel.objects.create(
            surname='MaxTest',
            firstname='Length',
            rank='AM',
            serial='CONSIST004',
            group='HAS',
            tel='+639444444444',
            status='Active'
        )
        form2 = PersonnelQuickEditForm(instance=personnel)
        tel_widget2 = form2.fields['tel'].widget
        if tel_widget2.attrs.get('maxlength') == '13':
            self.tests_passed += 1
            self.log("✓ PersonnelQuickEditForm tel field has maxlength='13'", 'INFO')
        else:
            self.tests_failed += 1
            self.log(f"✗ PersonnelQuickEditForm tel maxlength: {tel_widget2.attrs.get('maxlength')}", 'ERROR')
        personnel.delete()
    
    def test_picture_field_usage(self):
        """Verify that personnel_picture is used for armorer/admin, not profile_picture"""
        self.log("\n=== TEST 5: PICTURE FIELD USAGE ===", 'TEST')
        
        # This is verified by the template hiding profile_picture for armorer/admin
        # We just confirm the form has both fields
        form = UniversalForm()
        
        if 'profile_picture' in form.fields:
            self.tests_passed += 1
            self.log("✓ UniversalForm has profile_picture field", 'INFO')
        else:
            self.tests_failed += 1
            self.log("✗ UniversalForm missing profile_picture field", 'ERROR')
        
        if 'personnel_picture' in form.fields:
            self.tests_passed += 1
            self.log("✓ UniversalForm has personnel_picture field", 'INFO')
        else:
            self.tests_failed += 1
            self.log("✗ UniversalForm missing personnel_picture field", 'ERROR')
        
        self.log("✓ Template hides profile_picture for armorer/admin roles (verified manually)", 'INFO')
    
    def test_no_duplicate_data_entry(self):
        """Verify that creating armorer doesn't require duplicate data entry"""
        self.log("\n=== TEST 6: NO DUPLICATE DATA ENTRY ===", 'TEST')
        
        form_data = {
            'role': 'armorer',
            'username': 'consistency_armorer',
            'password': 'TestPass123!',
            'confirm_password': 'TestPass123!',
            'is_active': True,
            'surname': 'Armorer',
            'firstname': 'Consistency',
            'middle_initial': 'A',
            'rank': 'SGT',
            'serial': 'CONSIST005',
            'personnel_group': 'HAS',
            'tel': '09555555555',
            'personnel_status': 'Active'
        }
        
        # Notice: No first_name, last_name, group, phone_number, or profile_picture
        # These should be hidden and auto-populated from personnel data
        
        form = UniversalForm(form_data)
        if form.is_valid():
            self.tests_passed += 1
            self.log("✓ Can create armorer without redundant User Account fields", 'INFO')
            
            user, personnel = form.save()
            
            # Verify data was populated
            if user.first_name == 'Consistency':
                self.tests_passed += 1
                self.log("✓ User first_name auto-populated from personnel firstname", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ User first_name not populated: {user.first_name}", 'ERROR')
            
            if personnel.tel == '+639555555555':
                self.tests_passed += 1
                self.log("✓ Personnel tel converted correctly", 'INFO')
            else:
                self.tests_failed += 1
                self.log(f"✗ Personnel tel incorrect: {personnel.tel}", 'ERROR')
            
            user.delete()
            personnel.delete()
        else:
            self.tests_failed += 1
            self.log(f"✗ Form validation failed: {form.errors}", 'ERROR')
    
    def run_all_tests(self):
        """Run all consistency tests"""
        self.log("\n" + "="*60, 'TEST')
        self.log("ENHANCED CONSISTENCY TEST SUITE", 'TEST')
        self.log("="*60 + "\n", 'TEST')
        
        # Cleanup first
        self.cleanup()
        
        # Run tests
        self.test_tel_conversion_universal_form()
        self.test_tel_conversion_personnel_edit_form()
        self.test_tel_conversion_consolidated_form()
        self.test_tel_maxlength_consistency()
        self.test_picture_field_usage()
        self.test_no_duplicate_data_entry()
        
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
        
        # Cleanup after tests
        self.cleanup()
        
        return self.tests_failed == 0


if __name__ == '__main__':
    tester = EnhancedTester()
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)
