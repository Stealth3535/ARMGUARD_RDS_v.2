import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from personnel.models import Personnel
from qr_manager.models import QRCodeImage

# Clean up test_delete_user
test_user = User.objects.filter(username='test_delete_user').first()
if test_user:
    print(f'Deleting user: {test_user.username}')
    if hasattr(test_user, 'personnel') and test_user.personnel:
        print(f'  Has personnel: {test_user.personnel.serial}')
    test_user.delete()
    print('User deleted')
else:
    print('No test_delete_user found')

# Clean up any test_user_* users
test_users = User.objects.filter(username__startswith='test_user_')
if test_users.exists():
    print(f'\nDeleting {test_users.count()} test_user_* users')
    test_users.delete()

# Clean up any test personnel (HARD DELETE for test data)
test_pers_1 = Personnel.all_objects.filter(serial='999999')
test_pers_2 = Personnel.all_objects.filter(serial='888888')
test_pers = list(test_pers_1) + list(test_pers_2)

if test_pers:
    print(f'\nDeleting {len(test_pers)} test personnel')
    for p in test_pers:
        print(f'  - {p.serial} (ID: {p.id})')
        # Delete associated QR codes (hard delete)
        qrs = QRCodeImage.all_objects.filter(qr_type='personnel', reference_id=p.id)
        print(f'    Deleting {qrs.count()} QR codes')
        for qr in qrs:
            if qr.qr_image and os.path.isfile(qr.qr_image.path):
                os.remove(qr.qr_image.path)
        qrs.delete()
        
        # Delete personnel picture if exists
        if p.picture and os.path.isfile(p.picture.path):
            os.remove(p.picture.path)
            
        # Hard delete the personnel record
        p.delete()

print('\nCleanup complete')
