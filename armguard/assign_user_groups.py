"""
Assign groups to existing users based on their permissions
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User, Group


def assign_groups_to_existing_users():
    """Assign groups to users who don't have them"""
    
    # Create groups if they don't exist
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    armorer_group, _ = Group.objects.get_or_create(name='Armorer')
    
    print("Assigning groups to existing users...\n")
    
    for user in User.objects.all():
        print(f"User: {user.username}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - Current groups: {list(user.groups.values_list('name', flat=True))}")
        
        if user.is_superuser:
            print(f"  → Superuser (no group assignment needed)")
        elif user.is_staff:
            # Check if already has a group
            if not user.groups.exists():
                # For now, let's assign based on username pattern or ask
                # Default staff users to Admin group
                user.groups.add(admin_group)
                print(f"  → Added to 'Admin' group")
            else:
                print(f"  → Already has group assignment")
        else:
            print(f"  → Personnel (no group assignment needed)")
        
        print()
    
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    for user in User.objects.all():
        if user.is_superuser:
            role = "Superuser"
        elif user.groups.filter(name='Admin').exists():
            role = "Admin"
        elif user.groups.filter(name='Armorer').exists():
            role = "Armorer"
        else:
            role = "Personnel"
        
        print(f"{user.username:15} → {role}")
    
    print("\n✅ Group assignment complete!")


if __name__ == '__main__':
    assign_groups_to_existing_users()
