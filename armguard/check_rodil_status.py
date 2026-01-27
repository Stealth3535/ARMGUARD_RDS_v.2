import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from personnel.models import Personnel
from qr_manager.models import QRCodeImage

print("=" * 80)
print("CHECKING RODIL'S STATUS")
print("=" * 80)

rodil = Personnel.objects.get(serial='986887')
print(f'\nRodil: {rodil.get_full_name()}')
print(f'  ID: {rodil.id}')
print(f'  Status: {rodil.status}')
print(f'  deleted_at: {rodil.deleted_at}')
print(f'  Active in GUI: {Personnel.objects.filter(serial="986887").exists()}')

qr = QRCodeImage.all_objects.filter(reference_id=rodil.id).first()
if qr:
    print(f'\n  QR Code:')
    print(f'    is_active: {qr.is_active}')
    print(f'    deleted_at: {qr.deleted_at}')
    print(f'    Visible in GUI: {QRCodeImage.objects.filter(reference_id=rodil.id).exists()}')
    is_valid, msg = qr.is_valid_for_transaction()
    print(f'    Transaction valid: {is_valid}')
    print(f'    Message: {msg}')
else:
    print('\n  No QR code found!')

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f'Personnel reactivated: {"✅ YES" if not rodil.deleted_at else "❌ NO"}')
print(f'QR code reactivated: {"✅ YES" if qr and qr.is_active else "❌ NO"}')
print(f'Visible in GUI: {"✅ YES" if Personnel.objects.filter(serial="986887").exists() else "❌ NO"}')
print(f'QR usable for transactions: {"✅ YES" if qr and qr.is_valid_for_transaction()[0] else "❌ NO"}')
