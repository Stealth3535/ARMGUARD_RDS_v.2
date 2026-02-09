import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

print('=== CHECKING ALL USERS ===')
users = User.objects.all().prefetch_related('groups')
for u in users:
    print(f'\nUser: {u.username} (ID: {u.id})')
    print(f'  Staff: {u.is_staff}')
    print(f'  Superuser: {u.is_superuser}')
    print(f'  Groups: {[g.name for g in u.groups.all()]}')
    try:
        p = u.personnel
        print(f'  Personnel: {p.get_full_name()}')
        print(f'  Personnel ID: {p.id}')
    except Personnel.DoesNotExist:
        print(f'  Personnel: None')

print('\n=== CHECKING ALL PERSONNEL ===')
personnel = Personnel.objects.all()
for p in personnel:
    print(f'\nPersonnel: {p.get_full_name()} (ID: {p.id})')
    print(f'  Rank: {p.rank}')
    print(f'  Serial: {p.serial}')
    print(f'  Classification: {p.classification}')
    print(f'  User: {p.user.username if p.user else "None"}')
    print(f'  Surname: "{p.surname}"')
    print(f'  Firstname: "{p.firstname}"')
