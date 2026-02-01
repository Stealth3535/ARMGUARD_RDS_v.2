#!/usr/bin/env python
"""Delete test users from the database"""
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

print("="*60)
print("DELETING TEST USERS")
print("="*60)

# Find test users
test_users = User.objects.filter(username__startswith='test_')

if not test_users.exists():
    print("\n✓ No test users found. Database is clean!")
else:
    print(f"\nFound {test_users.count()} test user(s) to delete:\n")
    for user in test_users:
        groups = ', '.join([g.name for g in user.groups.all()])
        print(f"  • {user.username} (ID: {user.id}) - {groups if groups else 'No groups'}")
    
    confirm = input("\nAre you sure you want to delete these users? (yes/no): ")
    if confirm.lower() == 'yes':
        count = test_users.count()
        test_users.delete()
        print(f"\n✓ Successfully deleted {count} test user(s)!")
        print("\nRemaining users:")
        for user in User.objects.all():
            groups = ', '.join([g.name for g in user.groups.all()])
            role = 'Superuser' if user.is_superuser else f'{groups}' if groups else 'Regular'
            print(f"  • {user.username} - {role}")
    else:
        print("\n✗ Deletion cancelled.")

print("\n" + "="*60)
