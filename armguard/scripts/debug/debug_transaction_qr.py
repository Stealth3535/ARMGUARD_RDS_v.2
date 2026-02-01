import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from qr_manager.models import QRCodeImage
from personnel.models import Personnel

print("=" * 80)
print("DEBUGGING QR CODE TRANSACTION ISSUE")
print("=" * 80)

# Check the QR code that's failing
qr_id = 'PE-987703210126'
print(f"\nLooking up QR code: {qr_id}")

try:
    qr = QRCodeImage.objects.get(reference_id=qr_id)
    print(f"\n✅ QR Code found:")
    print(f"  reference_id: {qr.reference_id}")
    print(f"  qr_data: {qr.qr_data}")
    print(f"  qr_type: {qr.qr_type}")
    print(f"  is_active: {qr.is_active}")
    
    print(f"\n--- Transaction View Logic Simulation ---")
    print(f"Step 1: Get QR code by reference_id='{qr_id}' ✅")
    print(f"Step 2: Validate QR code...")
    is_valid, msg = qr.is_valid_for_transaction()
    print(f"  Result: {is_valid}, Message: {msg}")
    
    if qr.qr_type == 'personnel':
        print(f"\nStep 3: Get personnel by id='{qr.qr_data}'")
        try:
            personnel = Personnel.objects.get(id=qr.qr_data)
            print(f"  ✅ Personnel found: {personnel.get_full_name()}")
        except Personnel.DoesNotExist:
            print(f"  ❌ ERROR: Personnel.DoesNotExist")
            print(f"\n  Trying with reference_id instead...")
            try:
                personnel = Personnel.objects.get(id=qr.reference_id)
                print(f"  ✅ Personnel found using reference_id: {personnel.get_full_name()}")
            except Personnel.DoesNotExist:
                print(f"  ❌ Still not found with reference_id")
                
    # Check all personnel
    print(f"\n--- All Active Personnel ---")
    all_personnel = Personnel.objects.all()
    print(f"Total active: {all_personnel.count()}")
    for p in all_personnel:
        print(f"  {p.id}: {p.get_full_name()}")
        
except QRCodeImage.DoesNotExist:
    print(f"\n❌ QR Code not found: {qr_id}")
    print("\nAll personnel QR codes:")
    all_qrs = QRCodeImage.objects.filter(qr_type='personnel')
    for qr in all_qrs:
        print(f"  {qr.reference_id}: qr_data={qr.qr_data}")
