#!/usr/bin/env python
"""
Direct fix for personnel classification mismatches
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

print("\n" + "="*80)
print(" FIXING RANK/CLASSIFICATION MISMATCHES")
print("="*80)

# Get all personnel with officer ranks
officer_ranks = [rank_code for rank_code, _ in Personnel.RANKS_OFFICER]
misclassified = Personnel.objects.filter(
    rank__in=officer_ranks
).exclude(classification='OFFICER').exclude(classification='SUPERUSER')

enlisted_ranks = [rank_code for rank_code, _ in Personnel.RANKS_ENLISTED]
misclassified_enlisted = Personnel.objects.filter(
    rank__in=enlisted_ranks
).exclude(classification='ENLISTED PERSONNEL').exclude(classification='SUPERUSER')

fixed_count = 0

if misclassified.exists():
    print(f"\nFixing {misclassified.count()} officers with wrong classification:")
    for person in misclassified:
        old = person.classification
        person.classification = 'OFFICER'
        person.save()
        fixed_count += 1
        print(f"  ✓ {person.get_full_name()} ({person.rank}) - ID: {person.id}")
        print(f"    '{old}' → 'OFFICER'")

if misclassified_enlisted.exists():
    print(f"\nFixing {misclassified_enlisted.count()} enlisted with wrong classification:")
    for person in misclassified_enlisted:
        old = person.classification
        person.classification = 'ENLISTED PERSONNEL'
        person.save()
        fixed_count += 1
        print(f"  ✓ {person.get_full_name()} ({person.rank}) - ID: {person.id}")
        print(f"    '{old}' → 'ENLISTED PERSONNEL'")

print("\n" + "="*80)
print(f" COMPLETE: Fixed {fixed_count} personnel records")
print("="*80)

# Show final counts
print(f"\nFinal classification counts:")
print(f"  Officers: {Personnel.objects.filter(classification='OFFICER').count()}")
print(f"  Enlisted: {Personnel.objects.filter(classification='ENLISTED PERSONNEL').count()}")
print(f"  Superusers: {Personnel.objects.filter(classification='SUPERUSER').count()}")
print()
