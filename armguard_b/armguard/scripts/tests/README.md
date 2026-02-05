# ArmGuard Test Suite

This directory contains all test files and system verification scripts for the ArmGuard Military Armory Management System.

**Location:** `scripts/tests/` - Organized within the scripts directory structure

## Test Structure

### Test Categories:
- **Network Security Tests** - **NEW: LAN/WAN hybrid architecture validation**
- **System Integration Tests** - End-to-end workflow testing
- **API Security Tests** - Authentication and authorization validation  
- **Database Tests** - Data integrity and relationship testing
- **Print Handler Tests** - PDF generation and form filling
- **QR Code Tests** - QR code generation and scanning
- **Transaction Flow Tests** - Issue/return workflow validation
- **User Interface Tests** - Form validation and GUI functionality

### Key Test Files:
- `test_network_security.py` - **NEW: Comprehensive network security testing**
- `test_comprehensive.py` - Main comprehensive test suite (48 tests)
- `test_final_verification.py` - Soft delete system verification
- `test_registration_and_edit.py` - User and personnel management tests
- `test_qr_transaction_flow.py` - QR code workflow tests
- `test_auto_print_comprehensive.py` - Automated printing tests
- `test_security_*` - Security-focused test files

### Network Security Validation:
- **LAN/WAN Detection** - Port-based network type identification
- **Access Control** - Path-based restrictions enforcement
- **Role-Based Security** - User role network access validation
- **Middleware Testing** - Security middleware functionality
- **Decorator Testing** - @lan_required and @read_only_on_wan validation

### System Verification Scripts:
- `check_qr_status.py` - Comprehensive QR code status audit
- `check_test_personnel.py` - Test personnel verification
- `verify_pdf.py` - Transaction PDF output verification

## Running Tests

### Run All Tests:
```bash
python manage.py test scripts/tests/
```

### Run Network Security Tests (PRIORITY):
```bash
python scripts/tests/test_network_security.py
python manage.py test scripts.tests.test_network_security
```

### Run Specific Test File:
```bash
python manage.py test scripts.tests.test_comprehensive
```

### Run Individual Test Methods:
```bash
python manage.py test scripts.tests.test_comprehensive.TestClass.test_method
```

### Run System Verification Scripts:
```bash
python scripts/tests/check_qr_status.py
python scripts/tests/check_test_personnel.py
python scripts/tests/verify_pdf.py
```

### Run Tests with Coverage:
```bash
python manage.py test tests/ --verbosity=2 --keepdb
```

## Test Results Summary

- **Total Tests:** 48
- **Success Rate:** 100%
- **Security Grade:** A+
- **OWASP Compliance:** ✅ Verified

## Development Notes

All tests are designed to:
- Run independently without dependencies on external services
- Use Django's built-in test framework
- Create and clean up their own test data
- Test both positive and negative scenarios
- Validate security measures and access controls

For detailed test results and security audit information, see:
- `../FINAL_TEST_REPORT.md`
- `../COMPREHENSIVE_SECURITY_AUDIT.md`
- `../DEPLOYMENT_READY.md`