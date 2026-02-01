# ArmGuard Scripts Directory

This directory contains organized utility scripts for the ArmGuard system.

## 📂 Directory Structure

### `/maintenance/`
System maintenance and cleanup scripts:
- `cleanup_orphaned_files.py` - Remove unused QR codes and pictures
- `cleanup_orphaned_qr.py` - Remove orphaned QR code records
- `cleanup_test_data.py` - Clean up test data
- `delete_test_users.py` - Remove test users

### `/verification/`
System status checking and verification scripts:
- `check_users.py` - User database status verification
- `check_user_role.py` - User role verification
- `check_rodil_status.py` - Specific personnel status check

### `/setup/`
Initial setup and configuration scripts:
- `create_missing_groups.py` - Create required user groups
- `assign_user_groups.py` - Assign groups to existing users
- `fix_classification.py` - Fix personnel rank classifications

### `/debug/`
Debugging and analysis tools:
- `analyze_pdf.py` - PDF template analysis for form filling
- `debug_transaction_qr.py` - QR transaction debugging  
- `regenerate_pdf.py` - PDF regeneration tool
- `check_pdf_data.py` - PDF data verification
- `print_settings_quick_reference.py` - Print configuration reference

### `/tests/`
Test suite and system verification scripts:
- **Test Files:** All `test_*.py` files - Comprehensive application testing
- `check_qr_status.py` - QR code status verification
- `check_test_personnel.py` - Test personnel verification
- `verify_pdf.py` - PDF output verification

## 🚀 Usage

All scripts should be run from the project root directory:

```bash
# Maintenance
python scripts/maintenance/cleanup_orphaned_files.py

# Verification
python scripts/verification/check_users.py

# Setup
python scripts/setup/create_missing_groups.py

# Debug
python scripts/debug/analyze_pdf.py

# Tests and Verification
python manage.py test scripts/tests/
python scripts/tests/check_qr_status.py
python scripts/tests/verify_pdf.py
```

## 🔧 Script Standards

All scripts follow these patterns:
- Standard Django environment setup
- Comprehensive error handling
- Detailed logging and output
- Safety confirmations for destructive operations
- Verification after operations complete

## 📋 Notes

- All scripts require the Django environment to be properly configured
- Run scripts from the project root directory for proper path resolution
- Backup your database before running maintenance scripts
- Test scripts in development environment first