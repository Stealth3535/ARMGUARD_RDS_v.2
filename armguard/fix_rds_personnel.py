import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

# Get the rds user's personnel
user = User.objects.get(username='rds')
personnel = user.personnel

print(f'Current Personnel Data:')
print(f'  Name: {personnel.get_full_name()}')
print(f'  Firstname: {personnel.firstname}')
print(f'  Surname: {personnel.surname}')
print(f'  Serial: {personnel.serial}')
print(f'  Phone: {personnel.tel}')
print(f'  Rank: {personnel.rank}')

# Update with proper data
personnel.firstname = 'RDS'
personnel.surname = 'Admin'
personnel.middle_initial = ''
personnel.serial = '000001'  # Admin serial
personnel.tel = '+639171234567'  # Update with proper phone
personnel.rank = None  # Superusers don't need rank
personnel.classification = 'SUPERUSER'
personnel.save()

print(f'\n✓ Updated Personnel Data:')
print(f'  Name: {personnel.get_full_name()}')
print(f'  Firstname: {personnel.firstname}')
print(f'  Surname: {personnel.surname}')
print(f'  Serial: {personnel.serial}')
print(f'  Phone: {personnel.tel}')
print(f'  Rank: {personnel.rank}')
print(f'  Classification: {personnel.classification}')
