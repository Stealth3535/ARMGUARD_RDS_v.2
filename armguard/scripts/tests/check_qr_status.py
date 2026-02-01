import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from qr_manager.models import QRCodeImage
from personnel.models import Personnel
from inventory.models import Item

print("\n" + "="*80)
print("QR CODE STATUS CHECK")
print("="*80)

# Check Personnel QR Codes
personnel_qrs = QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_PERSONNEL)
print(f"\n📋 Personnel QR Codes: {personnel_qrs.count()} total")

missing_qr_images = []
for qr in personnel_qrs:
    if not qr.qr_image or not os.path.exists(qr.qr_image.path):
        missing_qr_images.append(qr)
        try:
            person = Personnel.objects.get(id=qr.reference_id)
            print(f"  ❌ Missing image: {person.get_full_name()} (ID: {qr.reference_id})")
        except Personnel.DoesNotExist:
            print(f"  ❌ Missing image: Personnel not found (ID: {qr.reference_id})")

if not missing_qr_images:
    print(f"  ✅ All personnel QR images exist")

# Check Item QR Codes
item_qrs = QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_ITEM)
print(f"\n📦 Item QR Codes: {item_qrs.count()} total")

missing_item_qr_images = []
for qr in item_qrs:
    if not qr.qr_image or not os.path.exists(qr.qr_image.path):
        missing_item_qr_images.append(qr)
        try:
            item = Item.objects.get(id=qr.reference_id)
            print(f"  ❌ Missing image: {item.item_type} - {item.serial} (ID: {qr.reference_id})")
        except Item.DoesNotExist:
            print(f"  ❌ Missing image: Item not found (ID: {qr.reference_id})")

if not missing_item_qr_images:
    print(f"  ✅ All item QR images exist")

# Check for orphaned QR records (no corresponding model)
print(f"\n🔍 Checking for orphaned QR records...")
orphaned_personnel_qrs = []
for qr in personnel_qrs:
    if not Personnel.objects.filter(id=qr.reference_id).exists():
        orphaned_personnel_qrs.append(qr)
        print(f"  ⚠️  Orphaned Personnel QR: ID {qr.reference_id} (no Personnel record)")

orphaned_item_qrs = []
for qr in item_qrs:
    if not Item.objects.filter(id=qr.reference_id).exists():
        orphaned_item_qrs.append(qr)
        print(f"  ⚠️  Orphaned Item QR: ID {qr.reference_id} (no Item record)")

if not orphaned_personnel_qrs and not orphaned_item_qrs:
    print(f"  ✅ No orphaned QR records")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Personnel QR codes with missing images: {len(missing_qr_images)}")
print(f"Item QR codes with missing images: {len(missing_item_qr_images)}")
print(f"Orphaned Personnel QR records: {len(orphaned_personnel_qrs)}")
print(f"Orphaned Item QR records: {len(orphaned_item_qrs)}")
print("="*80 + "\n")
