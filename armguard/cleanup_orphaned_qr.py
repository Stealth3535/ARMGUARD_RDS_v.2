"""
Clean up orphaned QR code records
Run this if you have QR codes in database but no corresponding items
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from qr_manager.models import QRCodeImage
from inventory.models import Item
from personnel.models import Personnel

print("=" * 70)
print("QR CODE CLEANUP UTILITY")
print("=" * 70)

# Find orphaned item QR codes
print("\n🔍 Checking for orphaned ITEM QR codes...")
item_qr_codes = QRCodeImage.all_objects.filter(qr_type='item')
orphaned_item_qr = []

for qr in item_qr_codes:
    try:
        Item.objects.get(id=qr.reference_id)
    except Item.DoesNotExist:
        orphaned_item_qr.append(qr)

print(f"   Found {len(orphaned_item_qr)} orphaned item QR code(s)")

if orphaned_item_qr:
    print("\n   Orphaned Item QR Codes:")
    for qr in orphaned_item_qr:
        print(f"     - ID: {qr.id}, Reference: {qr.reference_id}, Active: {qr.is_active}")

# Find orphaned personnel QR codes
print("\n🔍 Checking for orphaned PERSONNEL QR codes...")
personnel_qr_codes = QRCodeImage.all_objects.filter(qr_type='personnel')
orphaned_personnel_qr = []

for qr in personnel_qr_codes:
    try:
        Personnel.objects.get(id=qr.reference_id)
    except Personnel.DoesNotExist:
        orphaned_personnel_qr.append(qr)

print(f"   Found {len(orphaned_personnel_qr)} orphaned personnel QR code(s)")

if orphaned_personnel_qr:
    print("\n   Orphaned Personnel QR Codes:")
    for qr in orphaned_personnel_qr:
        print(f"     - ID: {qr.id}, Reference: {qr.reference_id}, Active: {qr.is_active}")

# Summary
total_orphaned = len(orphaned_item_qr) + len(orphaned_personnel_qr)
print("\n" + "=" * 70)
print(f"TOTAL ORPHANED QR CODES: {total_orphaned}")
print("=" * 70)

if total_orphaned > 0:
    print("\n⚠️  Found orphaned QR code records!")
    response = input("\nDelete these orphaned QR codes? (yes/no): ")
    
    if response.lower() == 'yes':
        deleted_files = 0
        deleted_records = 0
        
        print("\n🗑️  Deleting orphaned QR codes...")
        
        for qr in orphaned_item_qr + orphaned_personnel_qr:
            # Delete image file if exists
            if qr.qr_image:
                try:
                    if os.path.isfile(qr.qr_image.path):
                        os.remove(qr.qr_image.path)
                        deleted_files += 1
                        print(f"   ✓ Deleted file: {qr.qr_image.name}")
                except Exception as e:
                    print(f"   ✗ Could not delete file: {e}")
            
            # Delete database record
            qr_id = qr.id
            qr.delete()
            deleted_records += 1
            print(f"   ✓ Deleted QR record ID: {qr_id}")
        
        print("\n" + "=" * 70)
        print(f"✅ CLEANUP COMPLETE")
        print(f"   Deleted {deleted_files} file(s)")
        print(f"   Deleted {deleted_records} database record(s)")
        print("=" * 70)
    else:
        print("\n❌ Cleanup cancelled.")
else:
    print("\n✅ No orphaned QR codes found. Database is clean!")

print()
