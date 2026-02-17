"""
Cleanup script to remove QRCodeImage records for factory QR codes (M4 Carbine)
Factory QR codes don't need digital images since the weapon has the QR engraved
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from qr_manager.models import QRCodeImage
from inventory.models import Item

def cleanup_factory_qr_images():
    """Remove QRCodeImage records for items with factory QR codes"""
    
    print("Searching for QR code images for factory QR codes...")
    
    # Find all items that don't use system-generated IDs (IR-xxx or IP-xxx)
    factory_items = Item.objects.exclude(
        id__startswith='IR-'
    ).exclude(
        id__startswith='IP-'
    )
    
    if not factory_items.exists():
        print("No items with factory QR codes found.")
        return
    
    print(f"\nFound {factory_items.count()} item(s) with factory QR codes:")
    for item in factory_items:
        print(f"  - {item.item_type}: {item.id}")
    
    # Find QRCodeImage records for these items
    factory_qr_images = QRCodeImage.all_objects.filter(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id__in=[item.id for item in factory_items]
    )
    
    if not factory_qr_images.exists():
        print("\nNo QRCodeImage records found for factory QR codes. Already clean!")
        return
    
    print(f"\nFound {factory_qr_images.count()} QRCodeImage record(s) to delete:")
    for qr in factory_qr_images:
        print(f"  - {qr.reference_id} (has image: {bool(qr.qr_image)})")
    
    # Ask for confirmation
    response = input("\nDelete these QRCodeImage records? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Cancelled.")
        return
    
    # Delete the records and their image files
    deleted_count = 0
    for qr in factory_qr_images:
        # Delete image file if exists
        if qr.qr_image:
            try:
                if os.path.isfile(qr.qr_image.path):
                    os.remove(qr.qr_image.path)
                    print(f"  ✓ Deleted image file: {qr.qr_image.path}")
            except Exception as e:
                print(f"  ⚠ Could not delete image file: {e}")
        
        # Delete database record
        qr.delete()
        deleted_count += 1
    
    print(f"\n✓ Deleted {deleted_count} QRCodeImage record(s)")
    print("\nFactory QR codes (like M4 Carbine) will now use the physical QR on the weapon.")
    print("No digital QR images will be generated for these items.")


if __name__ == '__main__':
    cleanup_factory_qr_images()
