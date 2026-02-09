import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

# Get user rds
user = User.objects.get(username='rds')

# Check all personnel records (including ones without user links)
all_personnel = Personnel.objects.all()
print(f'=== ALL PERSONNEL RECORDS ===')
for p in all_personnel:
    linked_user = f" (User: {p.user.username})" if p.user else " (No user link)"
    print(f'ID: {p.id} | {p.rank} {p.get_full_name()} | Serial: {p.serial}{linked_user}')

print(f'\n=== UNLINKED PERSONNEL ===')
unlinked = Personnel.objects.filter(user__isnull=True)
print(f'Count: {unlinked.count()}')
for p in unlinked:
    print(f'ID: {p.id} | {p.rank} {p.get_full_name()} | Serial: {p.serial}')
