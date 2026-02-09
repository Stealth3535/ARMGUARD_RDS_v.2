import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

# Check the rds user
u = User.objects.get(username='rds')
print(f'User: {u.username} (ID: {u.id})')
print(f'Staff: {u.is_staff}')
print(f'Superuser: {u.is_superuser}')
print(f'Active: {u.is_active}')
print(f'Groups: {[g.name for g in u.groups.all()]}')

# Check personnel
try:
    p = u.personnel
    print(f'\nPersonnel Linked: YES')
    print(f'Personnel ID: {p.id}')
    print(f'Personnel Name: {p.get_full_name()}')
    print(f'Personnel Serial: {p.serial}')
except Personnel.DoesNotExist:
    print(f'\nPersonnel Linked: NO')
    p_query = Personnel.objects.filter(user=u)
    print(f'Personnel query count: {p_query.count()}')
