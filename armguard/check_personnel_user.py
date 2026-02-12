import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel

p = Personnel.objects.get(id='PE-994857110226')
print(f'Personnel: {p.get_full_name()}')
print(f'Has User: {"Yes" if p.user else "No"}')
if p.user:
    print(f'Username: {p.user.username}')
else:
    print('User: None')
