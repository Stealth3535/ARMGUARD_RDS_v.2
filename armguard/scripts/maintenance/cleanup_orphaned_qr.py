"""
Cleanup Orphaned QR Codes
Removes QR codes that reference non-existent personnel/items
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from qr_manager.models import QRCodeImage
from inventory.models import Item

print('=== ORPHANED QR CODE CLEANUP ===\n')

# Find orphaned personnel QR codes
print('1. Checking personnel QR codes...')
personnel_qr = QRCodeImage.all_objects.filter(qr_type='personnel')
orphaned_personnel = []

for qr in personnel_qr:
    try:
        Personnel.all_objects.get(id=qr.reference_id)
    except Personnel.DoesNotExist:
        orphaned_personnel.append(qr)
        print(f'   Found orphaned: {qr.reference_id}')

print(f'   Total orphaned personnel QR: {len(orphaned_personnel)}')

# Find orphaned item QR codes
print('\n2. Checking item QR codes...')
item_qr = QRCodeImage.all_objects.filter(qr_type='item')
orphaned_items = []

for qr in item_qr:
    try:
        Item.objects.get(id=qr.reference_id)
    except Item.DoesNotExist:
        orphaned_items.append(qr)
        print(f'   Found orphaned: {qr.reference_id}')

print(f'   Total orphaned item QR: {len(orphaned_items)}')

# Delete orphaned QR codes
total_orphaned = len(orphaned_personnel) + len(orphaned_items)
if total_orphaned > 0:
    print(f'\n3. Deleting {total_orphaned} orphaned QR codes...')
    
    for qr in orphaned_personnel + orphaned_items:
        print(f'   Deleting QR: {qr.reference_id}')
        # Delete the image file if it exists
        if qr.qr_image:
            try:
                if os.path.isfile(qr.qr_image.path):
                    os.remove(qr.qr_image.path)
                    print(f'     - Deleted file: {qr.qr_image.path}')
            except Exception as e:
                print(f'     - Error deleting file: {e}')
        
        # Delete the database record
        qr.delete()
    
    print(f'\n✓ Cleanup complete! Deleted {total_orphaned} orphaned QR codes')
else:
    print('\n✓ No orphaned QR codes found')

# Verify cleanup
print('\n4. Verification...')
remaining_orphaned = 0
for qr in QRCodeImage.all_objects.filter(qr_type='personnel'):
    try:
        Personnel.all_objects.get(id=qr.reference_id)
    except Personnel.DoesNotExist:
        remaining_orphaned += 1

for qr in QRCodeImage.all_objects.filter(qr_type='item'):
    try:
        Item.objects.get(id=qr.reference_id)
    except Item.DoesNotExist:
        remaining_orphaned += 1

if remaining_orphaned == 0:
    print('   ✓ All orphaned QR codes successfully removed')
else:
    print(f'   ⚠ Still {remaining_orphaned} orphaned QR codes remaining')

print('\n=== CLEANUP COMPLETE ===')
