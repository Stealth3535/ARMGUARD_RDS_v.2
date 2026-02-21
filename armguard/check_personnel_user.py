import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

# Require personnel ID from command line
if len(sys.argv) < 2:
    print('Error: Personnel ID is required')
    print('Usage: python check_personnel_user.py <PERSONNEL_ID>')
    print('Example: python check_personnel_user.py PE-994857110226')
    sys.exit(1)

personnel_id = sys.argv[1]

try:
    p = Personnel.objects.get(id=personnel_id)
    print(f'Personnel: {p.get_full_name()}')
    print(f'Has User: {"Yes" if p.user else "No"}')
    if p.user:
        print(f'Username: {p.user.username}')
    else:
        print('User: None')
except Personnel.DoesNotExist:
    print(f'Error: Personnel with ID {personnel_id} does not exist')
    print('Please verify the personnel ID and try again.')
    sys.exit(1)
