import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from qr_manager.models import QRCodeImage

# Check for personnel with serial 999999
p = Personnel.all_objects.filter(serial='999999').first()
print(f'Personnel with serial 999999: {p}')
if p:
    print(f'  ID: {p.id}')
    print(f'  deleted_at: {p.deleted_at}')
    print(f'  created_at: {p.created_at}')
    
    # Check QR codes
    qrs = QRCodeImage.all_objects.filter(reference_id=p.id)
    print(f'\n  Associated QR codes: {qrs.count()}')
    for qr in qrs:
        print(f'    - ID:{qr.id} active:{qr.is_active} ref:{qr.reference_id}')
else:
    print('  None found')

# Check orphaned QR codes
orphaned = QRCodeImage.all_objects.filter(reference_id__startswith='PE-999999')
print(f'\nOrphaned QR codes for PE-999999*: {orphaned.count()}')
for qr in orphaned:
    print(f'  - ID:{qr.id} ref:{qr.reference_id} active:{qr.is_active}')
    # Try to find personnel
    try:
        pers = Personnel.all_objects.get(id=qr.reference_id)
        print(f'    Personnel exists: {pers.serial}')
    except Personnel.DoesNotExist:
        print(f'    Personnel DOES NOT EXIST')
