import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

# Update rds user
user = User.objects.get(username='rds')
personnel = user.personnel

# Fix capitalization
personnel.firstname = 'RDS'
personnel.save()

print(f'✓ Updated personnel firstname: {personnel.firstname}')
print(f'  Full name: {personnel.get_full_name()}')
