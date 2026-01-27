"""
Test File Deletion - Verify that pictures and QR codes are deleted when users/personnel are deleted
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

from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from personnel.models import Personnel
from users.models import UserProfile
from inventory.models import Item
from qr_manager.models import QRCodeImage


def create_test_image():
    """Create a test image file"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return SimpleUploadedFile("test_image.jpg", img_io.read(), content_type="image/jpeg")


def test_personnel_file_deletion():
    """Test that personnel pictures and QR codes are deleted"""
    print("\n" + "="*80)
    print("TEST 1: Personnel File Deletion")
    print("="*80)
    
    # Create test personnel with picture
    test_image = create_test_image()
    personnel = Personnel.objects.create(
        surname='TestUser',
        firstname='Delete',
        middle_initial='T',
        rank='AM',
        serial='DELTEST123',
        group='HAS',
        tel='+639123456789',
        status='Active',
        picture=test_image
    )
    
    print(f"\n✓ Created personnel: {personnel.id}")
    
    # Check if picture file exists
    picture_path = personnel.picture.path if personnel.picture else None
    if picture_path and os.path.isfile(picture_path):
        print(f"✓ Picture file exists: {picture_path}")
    else:
        print(f"✗ Picture file NOT found!")
        return False
    
    # Check if QR code was created
    qr_codes = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_PERSONNEL,
        reference_id=personnel.id
    )
    
    if qr_codes.exists():
        print(f"✓ QR code record created: {qr_codes.count()} record(s)")
        qr_image_paths = []
        for qr in qr_codes:
            if qr.qr_image:
                qr_path = qr.qr_image.path
                qr_image_paths.append(qr_path)
                if os.path.isfile(qr_path):
                    print(f"✓ QR image file exists: {qr_path}")
                else:
                    print(f"✗ QR image file NOT found: {qr_path}")
    else:
        print("⚠ No QR code records found (might be generated asynchronously)")
        qr_image_paths = []
    
    # Delete personnel
    print(f"\n→ Deleting personnel {personnel.id}...")
    personnel.delete()
    print("✓ Personnel deleted from database")
    
    # Check if files were deleted
    if picture_path and os.path.isfile(picture_path):
        print(f"✗ FAIL: Picture file still exists: {picture_path}")
        return False
    else:
        print(f"✓ PASS: Picture file deleted")
    
    for qr_path in qr_image_paths:
        if os.path.isfile(qr_path):
            print(f"✗ FAIL: QR image file still exists: {qr_path}")
            return False
    
    if qr_image_paths:
        print(f"✓ PASS: All QR image files deleted")
    
    # Check if QR code records were deleted
    remaining_qr = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_PERSONNEL,
        reference_id=personnel.id
    )
    if remaining_qr.exists():
        print(f"✗ FAIL: QR code records still exist: {remaining_qr.count()}")
        return False
    else:
        print(f"✓ PASS: QR code records deleted")
    
    return True


def test_user_profile_picture_deletion():
    """Test that user profile pictures are deleted"""
    print("\n" + "="*80)
    print("TEST 2: User Profile Picture Deletion")
    print("="*80)
    
    # Create test user with profile picture
    user = User.objects.create_user(
        username='testdelete_user',
        email='testdelete@test.com',
        password='TestPass123!'
    )
    
    print(f"\n✓ Created user: {user.username}")
    
    # Add profile picture
    test_image = create_test_image()
    user.userprofile.profile_picture = test_image
    user.userprofile.save()
    
    picture_path = user.userprofile.profile_picture.path
    if os.path.isfile(picture_path):
        print(f"✓ Profile picture exists: {picture_path}")
    else:
        print(f"✗ Profile picture NOT found!")
        return False
    
    # Delete user (should cascade to UserProfile)
    print(f"\n→ Deleting user {user.username}...")
    user.delete()
    print("✓ User deleted from database")
    
    # Check if picture was deleted
    if os.path.isfile(picture_path):
        print(f"✗ FAIL: Profile picture still exists: {picture_path}")
        return False
    else:
        print(f"✓ PASS: Profile picture deleted")
    
    return True


def test_user_with_personnel_deletion():
    """Test deletion of user with linked personnel"""
    print("\n" + "="*80)
    print("TEST 3: User with Personnel Deletion")
    print("="*80)
    
    # Create user with personnel
    user = User.objects.create_user(
        username='testdelete_combo',
        email='testcombo@test.com',
        password='TestPass123!'
    )
    
    test_profile_pic = create_test_image()
    user.userprofile.profile_picture = test_profile_pic
    user.userprofile.save()
    
    test_personnel_pic = create_test_image()
    personnel = Personnel.objects.create(
        user=user,
        surname='Combo',
        firstname='Test',
        middle_initial='D',
        rank='SGT',
        serial='COMBO456',
        group='HAS',
        tel='+639987654321',
        status='Active',
        picture=test_personnel_pic
    )
    
    print(f"\n✓ Created user: {user.username}")
    print(f"✓ Created personnel: {personnel.id}")
    
    profile_pic_path = user.userprofile.profile_picture.path
    personnel_pic_path = personnel.picture.path
    
    print(f"✓ Profile picture: {profile_pic_path}")
    print(f"✓ Personnel picture: {personnel_pic_path}")
    
    # Get QR codes
    qr_codes = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_PERSONNEL,
        reference_id=personnel.id
    )
    qr_image_paths = [qr.qr_image.path for qr in qr_codes if qr.qr_image]
    
    if qr_image_paths:
        print(f"✓ QR codes: {len(qr_image_paths)} file(s)")
    
    # Delete personnel first
    print(f"\n→ Deleting personnel {personnel.id}...")
    personnel.delete()
    print("✓ Personnel deleted")
    
    # Check personnel files deleted
    if os.path.isfile(personnel_pic_path):
        print(f"✗ FAIL: Personnel picture still exists")
        return False
    else:
        print(f"✓ PASS: Personnel picture deleted")
    
    for qr_path in qr_image_paths:
        if os.path.isfile(qr_path):
            print(f"✗ FAIL: QR file still exists: {qr_path}")
            return False
    
    if qr_image_paths:
        print(f"✓ PASS: QR files deleted")
    
    # Delete user
    print(f"\n→ Deleting user {user.username}...")
    user.delete()
    print("✓ User deleted")
    
    # Check profile picture deleted
    if os.path.isfile(profile_pic_path):
        print(f"✗ FAIL: Profile picture still exists")
        return False
    else:
        print(f"✓ PASS: Profile picture deleted")
    
    return True


def test_item_qr_deletion():
    """Test that item QR codes are deleted"""
    print("\n" + "="*80)
    print("TEST 4: Item QR Code Deletion")
    print("="*80)
    
    # Create test item
    item = Item.objects.create(
        item_type='M16',
        serial='RIFLE123',
        status='Available',
        description='Test item for QR deletion'
    )
    
    print(f"\n✓ Created item: {item.id}")
    
    # Check if QR code was created
    qr_codes = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=item.id
    )
    
    if qr_codes.exists():
        print(f"✓ QR code record created: {qr_codes.count()} record(s)")
        qr_image_paths = []
        for qr in qr_codes:
            if qr.qr_image:
                qr_path = qr.qr_image.path
                qr_image_paths.append(qr_path)
                if os.path.isfile(qr_path):
                    print(f"✓ QR image file exists: {qr_path}")
    else:
        print("⚠ No QR code records found")
        qr_image_paths = []
    
    # Delete item
    print(f"\n→ Deleting item {item.id}...")
    item.delete()
    print("✓ Item deleted from database")
    
    # Check if QR files were deleted
    for qr_path in qr_image_paths:
        if os.path.isfile(qr_path):
            print(f"✗ FAIL: QR file still exists: {qr_path}")
            return False
    
    if qr_image_paths:
        print(f"✓ PASS: All QR files deleted")
    
    # Check if QR records were deleted
    remaining_qr = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=item.id
    )
    if remaining_qr.exists():
        print(f"✗ FAIL: QR records still exist: {remaining_qr.count()}")
        return False
    else:
        print(f"✓ PASS: QR records deleted")
    
    return True


def main():
    print("\n" + "="*80)
    print("FILE DELETION TEST SUITE")
    print("="*80)
    print("\nTesting automatic file deletion on model deletion...")
    
    results = {
        'Personnel File Deletion': test_personnel_file_deletion(),
        'User Profile Picture Deletion': test_user_profile_picture_deletion(),
        'User with Personnel Deletion': test_user_with_personnel_deletion(),
        'Item QR Code Deletion': test_item_qr_deletion(),
    }
    
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
