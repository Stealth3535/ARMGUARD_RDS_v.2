"""
Manual Orphaned Files Test
Creates orphaned files without using models
"""
import os
import sys
from pathlib import Path
from io import BytesIO
from PIL import Image

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from django.conf import settings


def create_test_image(filename):
    """Create a test image file directly on disk"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io.read()


def test_manual_orphaned_files():
    """Create orphaned files manually and test cleanup"""
    print("\n" + "="*80)
    print("MANUAL ORPHANED FILES TEST")
    print("="*80)
    
    media_root = Path(settings.MEDIA_ROOT)
    
    # Create orphaned personnel picture
    personnel_dir = media_root / 'personnel' / 'pictures'
    personnel_dir.mkdir(parents=True, exist_ok=True)
    orphan_pic = personnel_dir / 'manual_orphan_test.jpg'
    
    with open(orphan_pic, 'wb') as f:
        f.write(create_test_image('manual_orphan_test.jpg'))
    
    print(f"\n✓ Created orphaned personnel picture: {orphan_pic}")
    
    # Create orphaned user profile picture
    users_dir = media_root / 'users' / 'profile_pictures'
    users_dir.mkdir(parents=True, exist_ok=True)
    orphan_user_pic = users_dir / 'manual_orphan_user.jpg'
    
    with open(orphan_user_pic, 'wb') as f:
        f.write(create_test_image('manual_orphan_user.jpg'))
    
    print(f"✓ Created orphaned user picture: {orphan_user_pic}")
    
    # Create orphaned QR code
    qr_dir = media_root / 'qr_codes' / 'items'
    qr_dir.mkdir(parents=True, exist_ok=True)
    orphan_qr = qr_dir / 'manual_orphan_qr.png'
    
    with open(orphan_qr, 'wb') as f:
        f.write(create_test_image('manual_orphan_qr.png'))
    
    print(f"✓ Created orphaned QR code: {orphan_qr}")
    
    # Verify files exist
    files = [orphan_pic, orphan_user_pic, orphan_qr]
    for file in files:
        if os.path.isfile(file):
            print(f"  ✓ {file.name} exists")
        else:
            print(f"  ✗ {file.name} NOT found")
    
    # Run cleanup
    print(f"\n→ Running cleanup utility...")
    from cleanup_orphaned_files import (
        cleanup_orphaned_qr_codes,
        cleanup_orphaned_personnel_pictures,
        cleanup_orphaned_user_pictures
    )
    
    qr_count, qr_size = cleanup_orphaned_qr_codes()
    personnel_count, personnel_size = cleanup_orphaned_personnel_pictures()
    user_count, user_size = cleanup_orphaned_user_pictures()
    
    total_count = qr_count + personnel_count + user_count
    total_size = qr_size + personnel_size + user_size
    
    print(f"\n" + "="*80)
    print(f"CLEANUP SUMMARY")
    print(f"="*80)
    print(f"QR Codes deleted: {qr_count} files ({qr_size/1024:.2f} KB)")
    print(f"Personnel pictures deleted: {personnel_count} files ({personnel_size/1024:.2f} KB)")
    print(f"User pictures deleted: {user_count} files ({user_size/1024:.2f} KB)")
    print(f"Total deleted: {total_count} files ({total_size/1024:.2f} KB)")
    
    # Verify files are gone
    print(f"\n" + "="*80)
    print(f"VERIFICATION")
    print(f"="*80)
    all_deleted = True
    for file in files:
        if not os.path.isfile(file):
            print(f"✓ {file.name} successfully deleted")
        else:
            print(f"✗ {file.name} still exists!")
            all_deleted = False
    
    print(f"\n" + "="*80)
    if all_deleted and total_count == 3:
        print("✓ ALL ORPHANED FILES CLEANED UP SUCCESSFULLY")
        result = True
    else:
        print("✗ CLEANUP INCOMPLETE")
        result = False
    print("="*80 + "\n")
    
    return result


if __name__ == '__main__':
    result = test_manual_orphaned_files()
    sys.exit(0 if result else 1)
