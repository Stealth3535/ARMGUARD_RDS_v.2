"""
Test QR Code Display in GUI
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from qr_manager.models import QRCodeImage

print('=== QR CODE GUI DISPLAY TEST ===\n')

# Test 1: Check what QR codes appear in default query (used by GUI)
print('1. DEFAULT QUERY (what GUI sees)')
default_qr = QRCodeImage.objects.all()
print(f'   QR codes shown in GUI: {default_qr.count()}')
for qr in default_qr:
    try:
        personnel = Personnel.objects.get(id=qr.reference_id)
        print(f'   ✓ {qr.reference_id}: {personnel.get_full_name()} (active)')
    except Personnel.DoesNotExist:
        print(f'   ⚠ {qr.reference_id}: Personnel not found (should not appear!)')

# Test 2: Check Rodil's QR specifically
print('\n2. RODIL QR CODE CHECK')
try:
    rodil_qr = QRCodeImage.objects.get(reference_id='PE-986887270126')
    print(f'   ERROR: Rodil QR appears in active list! is_active={rodil_qr.is_active}')
except QRCodeImage.DoesNotExist:
    print('   ✓ Rodil QR correctly hidden from active list')

# Check with all_objects
rodil_qr_all = QRCodeImage.all_objects.filter(reference_id='PE-986887270126')
if rodil_qr_all.exists():
    qr = rodil_qr_all.first()
    print(f'   Database record exists: is_active={qr.is_active}, deleted_at={qr.deleted_at}')

# Test 3: Check Rodil's personnel record
print('\n3. RODIL PERSONNEL CHECK')
try:
    rodil_personnel = Personnel.objects.get(id='PE-986887270126')
    print(f'   ERROR: Rodil personnel appears in active list!')
except Personnel.DoesNotExist:
    print('   ✓ Rodil personnel correctly hidden from active list')

# Check with all_objects
rodil_all = Personnel.all_objects.filter(id='PE-986887270126')
if rodil_all.exists():
    p = rodil_all.first()
    print(f'   Database record exists: deleted_at={p.deleted_at}, status={p.status}')

# Test 4: Simulate print view query
print('\n4. PRINT VIEW SIMULATION')
from print_handler.views import QRCodeImage as QRModel
personnel_qrcodes_raw = QRCodeImage.objects.filter(qr_type='personnel')
personnel_qrcodes = []
for qr in personnel_qrcodes_raw:
    try:
        person = Personnel.objects.get(id=qr.reference_id)
        if qr.qr_image and qr.is_active:
            personnel_qrcodes.append({
                'id': qr.reference_id,
                'name': person.get_full_name(),
                'is_active': qr.is_active
            })
    except Personnel.DoesNotExist:
        pass

print(f'   Personnel QR codes in print view: {len(personnel_qrcodes)}')
for qr in personnel_qrcodes:
    print(f'   - {qr["id"]}: {qr["name"]}')

# Check if Rodil appears
rodil_in_list = any(qr['id'] == 'PE-986887270126' for qr in personnel_qrcodes)
if rodil_in_list:
    print('   ERROR: Rodil QR appears in print view!')
else:
    print('   ✓ Rodil QR correctly excluded from print view')

print('\n=== TEST COMPLETE ===')
