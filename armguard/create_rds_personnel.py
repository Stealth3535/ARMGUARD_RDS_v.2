import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel

# Get user rds
user = User.objects.get(username='rds')

# Create a new personnel record for rds
personnel = Personnel.objects.create(
    surname='Surname',
    firstname='RDS',
    middle_initial='',
    rank='AM',  # Airman - you can change this
    serial='999999',  # Temporary serial - you can change this
    group='HAS',  # Change if needed
    tel='+639000000000',  # Temporary phone
    status='Active',
    classification='SUPERUSER',
    user=user
)

print(f'✓ Created personnel record:')
print(f'  ID: {personnel.id}')
print(f'  Name: {personnel.get_full_name()}')
print(f'  Serial: {personnel.serial}')
print(f'  Linked to user: {user.username}')
print(f'\nYou can now edit this personnel record to update the details.')
