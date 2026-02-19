import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

# Get personnel ID from command line or use default
personnel_id = sys.argv[1] if len(sys.argv) > 1 else 'PE-994857110226'

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
    print(f'Usage: python check_personnel_user.py [PERSONNEL_ID]')
    sys.exit(1)
