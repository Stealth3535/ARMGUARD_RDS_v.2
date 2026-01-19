#!/usr/bin/env python
"""
Create missing user groups for ArmGuard application
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import Group

# Required groups
REQUIRED_GROUPS = ['Superuser', 'Admin', 'Armorer', 'Personnel']

def create_missing_groups():
    """Create any missing groups"""
    created_count = 0
    existing_groups = set(Group.objects.values_list('name', flat=True))
    
    print("Existing groups:", list(existing_groups))
    
    for group_name in REQUIRED_GROUPS:
        if group_name not in existing_groups:
            Group.objects.create(name=group_name)
            print(f"✓ Created group: {group_name}")
            created_count += 1
        else:
            print(f"• Group already exists: {group_name}")
    
    if created_count > 0:
        print(f"\n✓ Successfully created {created_count} group(s)")
    else:
        print("\n✓ All required groups already exist")
    
    # Display final state
    final_groups = list(Group.objects.values_list('name', flat=True))
    print(f"\nFinal groups: {final_groups}")

if __name__ == '__main__':
    create_missing_groups()
