#!/usr/bin/env python
"""Quick script to check and optionally clean test users"""
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.db.models import Q

print("="*60)
print("CURRENT USER DATABASE STATUS")
print("="*60)

# Get all users
all_users = User.objects.all()
print(f"\nTotal users in database: {all_users.count()}")

print("\n" + "-"*60)
print("DETAILED USER LIST:")
print("-"*60)
for user in all_users.order_by('id'):
    groups = ', '.join([g.name for g in user.groups.all()])
    role = 'Superuser' if user.is_superuser else f'Groups: {groups}' if groups else 'Regular User'
    status = '✓ Active' if user.is_active else '✗ Inactive'
    print(f"ID: {user.id:3d} | {user.username:20s} | {role:30s} | {status}")

# Calculate statistics matching dashboard query
print("\n" + "-"*60)
print("DASHBOARD STATISTICS:")
print("-"*60)
superusers_count = User.objects.filter(is_superuser=True).count()
admins_count = User.objects.filter(groups__name='Admin').count()
administrators_count = User.objects.filter(
    Q(groups__name='Admin') | Q(is_superuser=True)
).distinct().count()
armorers_count = User.objects.filter(groups__name='Armorer').count()
active_users = User.objects.filter(is_active=True).count()

print(f"Total Users: {all_users.count()}")
print(f"Active Users: {active_users}")
print(f"Superusers: {superusers_count}")
print(f"Admin Group Members: {admins_count}")
print(f"Administrators (Superusers + Admins): {administrators_count}")
print(f"Armorers: {armorers_count}")

# Identify test users
print("\n" + "-"*60)
print("TEST USERS (can be safely deleted):")
print("-"*60)
test_users = User.objects.filter(username__startswith='test_')
if test_users.exists():
    for user in test_users:
        groups = ', '.join([g.name for g in user.groups.all()])
        print(f"  • {user.username} (ID: {user.id}) - {groups if groups else 'No groups'}")
    
    print(f"\nFound {test_users.count()} test user(s)")
    print("\nTo delete these test users, run:")
    print("  python delete_test_users.py")
else:
    print("  No test users found ✓")

print("\n" + "="*60)
print("After deleting test users and hard refreshing browser (Ctrl+F5),")
print("your dashboard should show the correct administrator count.")
print("="*60)
