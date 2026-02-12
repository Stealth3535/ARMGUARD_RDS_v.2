#!/usr/bin/env python
"""
Comprehensive Personnel Audit and Fix Script
============================================
Audits and fixes:
1. Rank vs Classification mismatches
2. Serial number format issues
3. ID construction problems
4. Personnel with specific IDs (PO-154068110226)
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from django.db.models import Q

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def print_section(title):
    """Print formatted section"""
    print(f"\n{title}")
    print("-" * 70)

def audit_specific_personnel(personnel_id):
    """Audit a specific personnel record"""
    try:
        person = Personnel.objects.get(Q(id=personnel_id) | Q(qr_code=personnel_id))
        print(f"\n📋 PERSONNEL DETAILS:")
        print(f"  ID: {person.id}")
        print(f"  Name: {person.get_full_name()}")
        print(f"  Rank: {person.rank}")
        print(f"  Serial: {person.serial}")
        print(f"  Classification: {person.classification}")
        print(f"  Group: {person.group}")
        print(f"  Is Officer: {person.is_officer()}")
        print(f"  Expected Classification: {person.get_classification_from_rank()}")
        
        # Check for issues
        issues = []
        if person.rank and person.classification != person.get_classification_from_rank():
            issues.append(f"❌ MISMATCH: Classification is '{person.classification}' but rank '{person.rank}' should be '{person.get_classification_from_rank()}'")
        
        if person.is_officer() and not person.id.startswith('PO-'):
            issues.append(f"❌ ID FORMAT: Officer should have 'PO-' prefix, got '{person.id}'")
        
        if not person.is_officer() and not person.id.startswith('PE-'):
            issues.append(f"❌ ID FORMAT: Enlisted should have 'PE-' prefix, got '{person.id}'")
        
        # Check serial format (should be numeric only)
        if person.serial and not person.serial.replace('-', '').replace('O', '').isdigit():
            issues.append(f"⚠️ SERIAL FORMAT: Serial '{person.serial}' contains non-numeric characters")
        
        if issues:
            print_section("🚨 ISSUES FOUND")
            for issue in issues:
                print(f"  {issue}")
            return person, issues
        else:
            print_section("✅ NO ISSUES")
            return person, []
            
    except Personnel.DoesNotExist:
        print(f"\n❌ Personnel '{personnel_id}' not found")
        return None, []

def audit_all_classification_mismatches():
    """Find all personnel with rank/classification mismatches"""
    print_section("🔍 AUDITING CLASSIFICATION MISMATCHES")
    
    officer_ranks = [rank_code for rank_code, _ in Personnel.RANKS_OFFICER]
    enlisted_ranks = [rank_code for rank_code, _ in Personnel.RANKS_ENLISTED]
    
    # Officers with wrong classification
    misclassified_officers = Personnel.objects.filter(
        rank__in=officer_ranks
    ).exclude(classification='OFFICER').exclude(classification='SUPERUSER')
    
    # Enlisted with wrong classification
    misclassified_enlisted = Personnel.objects.filter(
        rank__in=enlisted_ranks
    ).exclude(classification='ENLISTED PERSONNEL').exclude(classification='SUPERUSER')
    
    issues = []
    
    if misclassified_officers.exists():
        print(f"\n❌ Found {misclassified_officers.count()} OFFICERS with wrong classification:")
        for person in misclassified_officers:
            issue = {
                'person': person,
                'type': 'officer_classification',
                'old': person.classification,
                'new': 'OFFICER'
            }
            issues.append(issue)
            print(f"  • {person.get_full_name()} ({person.rank}) - ID: {person.id}")
            print(f"    Current: '{person.classification}' → Should be: 'OFFICER'")
    
    if misclassified_enlisted.exists():
        print(f"\n❌ Found {misclassified_enlisted.count()} ENLISTED with wrong classification:")
        for person in misclassified_enlisted:
            issue = {
                'person': person,
                'type': 'enlisted_classification',
                'old': person.classification,
                'new': 'ENLISTED PERSONNEL'
            }
            issues.append(issue)
            print(f"  • {person.get_full_name()} ({person.rank}) - ID: {person.id}")
            print(f"    Current: '{person.classification}' → Should be: 'ENLISTED PERSONNEL'")
    
    if not issues:
        print("✅ No classification mismatches found!")
    
    return issues

def audit_serial_format():
    """Check all serial numbers for format issues"""
    print_section("🔍 AUDITING SERIAL NUMBER FORMAT")
    
    issues = []
    all_personnel = Personnel.objects.all()
    
    for person in all_personnel:
        # Serial should be numeric only (6 digits typically)
        serial = person.serial
        
        # Check for O- prefix (old format for officers)
        if serial.startswith('O-'):
            issue = {
                'person': person,
                'type': 'serial_prefix',
                'old': serial,
                'new': serial.replace('O-', '')
            }
            issues.append(issue)
            print(f"  ⚠️ {person.get_full_name()} - Serial has 'O-' prefix: {serial}")
        
        # Check for non-numeric characters (except hyphen)
        clean_serial = serial.replace('-', '').replace('O', '')
        if not clean_serial.isdigit():
            issue = {
                'person': person,
                'type': 'serial_format',
                'old': serial,
                'new': None  # Manual review needed
            }
            issues.append(issue)
            print(f"  ⚠️ {person.get_full_name()} - Serial contains non-numeric: {serial}")
    
    if not issues:
        print("✅ All serial numbers are properly formatted!")
    
    return issues

def audit_id_construction():
    """Check ID construction (PO-/PE- prefix matching classification)"""
    print_section("🔍 AUDITING ID CONSTRUCTION")
    
    issues = []
    
    # Officers should have PO- prefix
    officers = Personnel.objects.filter(classification='OFFICER')
    for person in officers:
        if not person.id.startswith('PO-'):
            issue = {
                'person': person,
                'type': 'id_prefix',
                'old': person.id,
                'new': f"PO-{person.serial}{person.id.split('-', 1)[-1].split('PO')[0].split('PE')[0]}" if '-' in person.id else None
            }
            issues.append(issue)
            print(f"  ❌ Officer {person.get_full_name()} has wrong ID prefix: {person.id}")
    
    # Enlisted should have PE- prefix
    enlisted = Personnel.objects.filter(classification='ENLISTED PERSONNEL')
    for person in enlisted:
        if not person.id.startswith('PE-'):
            issue = {
                'person': person,
                'type': 'id_prefix',
                'old': person.id,
                'new': None
            }
            issues.append(issue)
            print(f"  ❌ Enlisted {person.get_full_name()} has wrong ID prefix: {person.id}")
    
    if not issues:
        print("✅ All IDs have correct prefixes!")
    
    return issues

def fix_issues(issues, dry_run=True):
    """Fix identified issues"""
    if not issues:
        print("\n✅ No issues to fix!")
        return 0
    
    print_section(f"{'🔧 DRY RUN - PROPOSED FIXES' if dry_run else '🔧 FIXING ISSUES'}")
    
    fixed_count = 0
    
    for issue in issues:
        person = issue['person']
        issue_type = issue['type']
        
        try:
            if issue_type in ['officer_classification', 'enlisted_classification']:
                old_class = issue['old']
                new_class = issue['new']
                print(f"\n  {'[DRY RUN]' if dry_run else '✓'} {person.get_full_name()} ({person.rank})")
                print(f"    Classification: '{old_class}' → '{new_class}'")
                
                if not dry_run:
                    person.classification = new_class
                    person.save()
                    fixed_count += 1
            
            elif issue_type == 'serial_prefix':
                old_serial = issue['old']
                new_serial = issue['new']
                print(f"\n  {'[DRY RUN]' if dry_run else '✓'} {person.get_full_name()}")
                print(f"    Serial: '{old_serial}' → '{new_serial}'")
                
                if not dry_run:
                    person.serial = new_serial
                    person.save()
                    fixed_count += 1
            
            elif issue_type == 'serial_format':
                print(f"\n  ⚠️ {person.get_full_name()} - Serial '{issue['old']}' needs manual review")
            
            elif issue_type == 'id_prefix':
                print(f"\n  ⚠️ {person.get_full_name()} - ID '{issue['old']}' - Manual review recommended")
                print(f"    (ID changes can break references - proceed with caution)")
        
        except Exception as e:
            print(f"\n  ❌ ERROR fixing {person.get_full_name()}: {e}")
    
    return fixed_count

def main():
    """Main audit function"""
    print_header("🔍 PERSONNEL AUDIT & FIX TOOL")
    
    # Check for specific personnel ID
    print_section("📍 SEARCHING FOR SPECIFIC RECORD")
    specific_id = "PO-154068110226"
    print(f"Looking for: {specific_id}")
    
    person, specific_issues = audit_specific_personnel(specific_id)
    
    # Run comprehensive audit
    print_header("📊 COMPREHENSIVE AUDIT")
    
    classification_issues = audit_all_classification_mismatches()
    serial_issues = audit_serial_format()
    id_issues = audit_id_construction()
    
    all_issues = classification_issues + serial_issues + id_issues
    
    # Summary
    print_header("📈 AUDIT SUMMARY")
    print(f"  Total personnel: {Personnel.objects.count()}")
    print(f"  Officers: {Personnel.objects.filter(classification='OFFICER').count()}")
    print(f"  Enlisted: {Personnel.objects.filter(classification='ENLISTED PERSONNEL').count()}")
    print(f"  Superusers: {Personnel.objects.filter(classification='SUPERUSER').count()}")
    print()
    print(f"  Issues found: {len(all_issues)}")
    print(f"    - Classification mismatches: {len(classification_issues)}")
    print(f"    - Serial format issues: {len(serial_issues)}")
    print(f"    - ID construction issues: {len(id_issues)}")
    
    if all_issues:
        print_header("🔧 FIX OPTIONS")
        print("\nThis was a DRY RUN. No changes were made.")
        print("\nTo apply fixes, uncomment the following line in the script:")
        print("  # fixed_count = fix_issues(all_issues, dry_run=False)")
        print("\nOr run with --fix flag:")
        print("  python audit_fix_personnel.py --fix")
        
        # Dry run - show what would be fixed
        fix_issues(all_issues, dry_run=True)
    else:
        print_header("✅ ALL CLEAR")
        print("No issues found! All personnel records are properly configured.")

if __name__ == "__main__":
    import sys
    
    # Check for --fix flag
    if len(sys.argv) > 1 and sys.argv[1] == '--fix':
        print_header("⚠️  FIX MODE ENABLED")
        print("This will apply changes to the database!")
        response = input("\nAre you sure you want to proceed? (yes/no): ")
        
        if response.lower() == 'yes':
            main()
            # Apply fixes
            all_issues = []
            all_issues += audit_all_classification_mismatches()
            all_issues += audit_serial_format()
            all_issues += audit_id_construction()
            
            if all_issues:
                fixed_count = fix_issues(all_issues, dry_run=False)
                print_header("✅ FIX COMPLETE")
                print(f"Fixed {fixed_count} issues successfully!")
        else:
            print("\n❌ Cancelled by user")
    else:
        main()
