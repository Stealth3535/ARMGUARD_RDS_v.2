import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

users = User.objects.all()
print(f"\nTotal users: {users.count()}\n")

for user in users:
    print(f"User: {user.username}")
    print(f"  - Is staff: {user.is_staff}")
    print(f"  - Is superuser: {user.is_superuser}")
    if hasattr(user, 'userprofile'):
        print(f"  - Has UserProfile: Yes")
        print(f"  - Role: {user.userprofile.role}")
    else:
        print(f"  - Has UserProfile: NO")
    print()
