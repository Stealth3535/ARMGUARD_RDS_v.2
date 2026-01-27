import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

print("\n" + "="*80)
print("FIXING PERSONNEL CLASSIFICATION")
print("="*80)

officer_ranks = [rank_code for rank_code, _ in Personnel.RANKS_OFFICER]
print(f"\nOfficer ranks: {', '.join(officer_ranks)}")

# Find personnel with officer ranks but wrong classification
misclassified = Personnel.objects.filter(
    rank__in=officer_ranks
).exclude(classification='OFFICER')

print(f"\nFound {misclassified.count()} personnel with officer ranks but wrong classification:")

fixed_count = 0
for person in misclassified:
    old_classification = person.classification
    person.classification = 'OFFICER'
    person.save()
    fixed_count += 1
    print(f"  ✓ Fixed: {person.get_full_name()} ({person.rank})")
    print(f"    Changed from '{old_classification}' to 'OFFICER'")

# Find enlisted personnel with wrong classification
enlisted_ranks = [rank_code for rank_code, _ in Personnel.RANKS_ENLISTED]
misclassified_enlisted = Personnel.objects.filter(
    rank__in=enlisted_ranks
).exclude(classification='ENLISTED PERSONNEL')

if misclassified_enlisted.exists():
    print(f"\nFound {misclassified_enlisted.count()} enlisted with wrong classification:")
    for person in misclassified_enlisted:
        if person.classification != 'SUPERUSER':  # Don't change superusers
            old_classification = person.classification
            person.classification = 'ENLISTED PERSONNEL'
            person.save()
            fixed_count += 1
            print(f"  ✓ Fixed: {person.get_full_name()} ({person.rank})")
            print(f"    Changed from '{old_classification}' to 'ENLISTED PERSONNEL'")

print("\n" + "="*80)
print(f"SUMMARY: Fixed {fixed_count} personnel records")
print("="*80 + "\n")

# Show current counts
officers = Personnel.objects.filter(classification='OFFICER').count()
enlisted = Personnel.objects.filter(classification='ENLISTED PERSONNEL').count()
superusers = Personnel.objects.filter(classification='SUPERUSER').count()

print(f"Current classification counts:")
print(f"  Officers: {officers}")
print(f"  Enlisted Personnel: {enlisted}")
print(f"  Superusers: {superusers}")
print()
