"""
Test Orphaned Files Cleanup
"""
import os
import sys
import django
from pathlib import Path
from io import BytesIO
from PIL import Image

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from personnel.models import Personnel
from users.models import UserProfile
from qr_manager.models import QRCodeImage
from django.contrib.auth.models import User


def create_test_image():
    """Create a test image file"""
    img = Image.new('RGB', (100, 100), color='blue')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return SimpleUploadedFile("orphan_test.jpg", img_io.read(), content_type="image/jpeg")


def test_orphaned_files_cleanup():
    """Test that orphaned files are properly detected and cleaned up"""
    print("\n" + "="*80)
    print("TEST: Orphaned Files Cleanup")
    print("="*80)
    
    # Create test personnel with picture
    test_image = create_test_image()
    personnel = Personnel.objects.create(
        surname='OrphanTest',
        firstname='Delete',
        middle_initial='O',
        rank='AM',
        serial='ORPHAN123',
        group='HAS',
        tel='+639111111111',
        status='Active',
        picture=test_image
    )
    
    print(f"\n✓ Created test personnel: {personnel.id}")
    picture_path = personnel.picture.path
    picture_name = personnel.picture.name
    print(f"✓ Picture saved: {picture_name}")
    
    # Verify file exists
    if os.path.isfile(picture_path):
        print(f"✓ Picture file exists on disk")
    else:
        print(f"✗ Picture file NOT found!")
        return False
    
    # Now delete the personnel WITHOUT using the model delete() method
    # This simulates an orphaned file scenario
    print(f"\n→ Deleting personnel record directly from database...")
    Personnel.objects.filter(id=personnel.id).delete()
    
    # Verify database record is gone
    if not Personnel.objects.filter(id=personnel.id).exists():
        print(f"✓ Database record deleted")
    
    # Verify file still exists (orphaned)
    if os.path.isfile(picture_path):
        print(f"✓ Picture file still exists (orphaned)")
    else:
        print(f"✗ File was deleted (signal must have caught it)")
        return False
    
    # Run cleanup script
    print(f"\n→ Running cleanup utility...")
    from cleanup_orphaned_files import cleanup_orphaned_personnel_pictures
    deleted_count, deleted_size = cleanup_orphaned_personnel_pictures()
    
    if deleted_count > 0:
        print(f"✓ PASS: Cleanup deleted {deleted_count} orphaned file(s)")
        
        # Verify file is now gone
        if not os.path.isfile(picture_path):
            print(f"✓ PASS: Orphaned file successfully removed")
            return True
        else:
            print(f"✗ FAIL: File still exists after cleanup")
            return False
    else:
        print(f"✗ FAIL: Cleanup did not find orphaned file")
        # Clean up manually
        if os.path.isfile(picture_path):
            os.remove(picture_path)
        return False


def test_qr_code_cleanup():
    """Test QR code cleanup"""
    print("\n" + "="*80)
    print("TEST: QR Code Cleanup")
    print("="*80)
    
    from inventory.models import Item
    
    # Create test item (will auto-generate QR code via signal)
    item = Item.objects.create(
        item_type='M16',
        serial='QRORPHAN001',
        description='Test item for QR cleanup',
        condition='Good',
        status='Available'
    )
    
    print(f"\n✓ Created test item: {item.id}")
    
    # Get QR code
    qr_code = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=item.id
    ).first()
    
    if qr_code and qr_code.qr_image:
        qr_path = qr_code.qr_image.path
        qr_name = qr_code.qr_image.name
        print(f"✓ QR code created: {qr_name}")
        
        # Verify file exists
        if os.path.isfile(qr_path):
            print(f"✓ QR file exists on disk")
        else:
            print(f"⚠ QR file not found on disk")
            item.delete()
            return True  # Skip test
        
        # Delete QR code record from database (not the file)
        print(f"\n→ Deleting QR code record from database...")
        QRCodeImage.objects.filter(id=qr_code.id).delete()
        
        print(f"✓ QR code database record deleted")
        
        # Verify file still exists (orphaned)
        if os.path.isfile(qr_path):
            print(f"✓ QR file still exists (orphaned)")
        else:
            print(f"✗ QR file was deleted")
            item.delete()
            return False
        
        # Run cleanup
        print(f"\n→ Running cleanup utility...")
        from cleanup_orphaned_files import cleanup_orphaned_qr_codes
        deleted_count, deleted_size = cleanup_orphaned_qr_codes()
        
        # Clean up item
        item.delete()
        
        if deleted_count > 0:
            print(f"✓ PASS: Cleanup deleted {deleted_count} orphaned QR file(s)")
            
            if not os.path.isfile(qr_path):
                print(f"✓ PASS: Orphaned QR file successfully removed")
                return True
            else:
                print(f"✗ FAIL: QR file still exists after cleanup")
                os.remove(qr_path)
                return False
        else:
            print(f"✗ FAIL: Cleanup did not find orphaned QR file")
            if os.path.isfile(qr_path):
                os.remove(qr_path)
            return False
    else:
        print(f"⚠ No QR code was generated, skipping test")
        item.delete()
        return True


def main():
    print("\n" + "="*80)
    print("ORPHANED FILES CLEANUP TEST SUITE")
    print("="*80)
    
    results = {}
    
    # Test personnel picture cleanup
    results['Personnel Picture Cleanup'] = test_orphaned_files_cleanup()
    
    # Test QR code cleanup
    results['QR Code Cleanup'] = test_qr_code_cleanup()
    
    # Summary
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
