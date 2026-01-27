"""
Cleanup Orphaned Files - Remove unused QR codes and pictures
This script identifies and removes files that no longer have corresponding database records
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from personnel.models import Personnel
from users.models import UserProfile
from qr_manager.models import QRCodeImage


def scan_directory(directory_path):
    """Scan directory and return all files"""
    files = []
    if os.path.exists(directory_path):
        for root, dirs, filenames in os.walk(directory_path):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                # Get relative path from media root
                rel_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
                files.append((full_path, rel_path))
    return files


def cleanup_orphaned_qr_codes():
    """Remove QR code images that don't have database records"""
    print("\n" + "="*80)
    print("CLEANUP: Orphaned QR Codes")
    print("="*80)
    
    qr_directory = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
    
    if not os.path.exists(qr_directory):
        print("✓ No QR codes directory found")
        return 0, 0
    
    # Get all QR code files
    all_qr_files = scan_directory(qr_directory)
    print(f"\n📁 Found {len(all_qr_files)} QR code files on disk")
    
    # Get all QR code database records with images
    db_qr_codes = QRCodeImage.objects.filter(qr_image__isnull=False)
    db_qr_paths = set()
    
    for qr_code in db_qr_codes:
        if qr_code.qr_image:
            # Normalize path
            db_qr_paths.add(qr_code.qr_image.name.replace('\\', '/'))
    
    print(f"📊 Found {len(db_qr_paths)} QR codes in database")
    
    # Find orphaned files
    orphaned_files = []
    for full_path, rel_path in all_qr_files:
        # Normalize path for comparison
        normalized_rel = rel_path.replace('\\', '/')
        if normalized_rel not in db_qr_paths:
            orphaned_files.append((full_path, rel_path))
    
    if orphaned_files:
        print(f"\n🗑️  Found {len(orphaned_files)} orphaned QR code files:")
        deleted_count = 0
        deleted_size = 0
        
        for full_path, rel_path in orphaned_files:
            try:
                file_size = os.path.getsize(full_path)
                os.remove(full_path)
                deleted_count += 1
                deleted_size += file_size
                print(f"  ✓ Deleted: {rel_path} ({file_size} bytes)")
            except Exception as e:
                print(f"  ✗ Error deleting {rel_path}: {str(e)}")
        
        # Clean up empty directories
        for root, dirs, files in os.walk(qr_directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        print(f"  ✓ Removed empty directory: {os.path.relpath(dir_path, settings.MEDIA_ROOT)}")
                except:
                    pass
        
        print(f"\n✓ Deleted {deleted_count} orphaned QR files ({deleted_size / 1024:.2f} KB)")
        return deleted_count, deleted_size
    else:
        print("\n✓ No orphaned QR code files found")
        return 0, 0


def cleanup_orphaned_personnel_pictures():
    """Remove personnel pictures that don't have database records"""
    print("\n" + "="*80)
    print("CLEANUP: Orphaned Personnel Pictures")
    print("="*80)
    
    personnel_directory = os.path.join(settings.MEDIA_ROOT, 'personnel', 'pictures')
    
    if not os.path.exists(personnel_directory):
        print("✓ No personnel pictures directory found")
        return 0, 0
    
    # Get all personnel picture files
    all_picture_files = scan_directory(personnel_directory)
    print(f"\n📁 Found {len(all_picture_files)} personnel picture files on disk")
    
    # Get all personnel database records with pictures
    db_personnel = Personnel.objects.filter(picture__isnull=False).exclude(picture='')
    db_picture_paths = set()
    
    for personnel in db_personnel:
        if personnel.picture:
            db_picture_paths.add(personnel.picture.name.replace('\\', '/'))
    
    print(f"📊 Found {len(db_picture_paths)} personnel pictures in database")
    
    # Find orphaned files
    orphaned_files = []
    for full_path, rel_path in all_picture_files:
        normalized_rel = rel_path.replace('\\', '/')
        if normalized_rel not in db_picture_paths:
            orphaned_files.append((full_path, rel_path))
    
    if orphaned_files:
        print(f"\n🗑️  Found {len(orphaned_files)} orphaned personnel picture files:")
        deleted_count = 0
        deleted_size = 0
        
        for full_path, rel_path in orphaned_files:
            try:
                file_size = os.path.getsize(full_path)
                os.remove(full_path)
                deleted_count += 1
                deleted_size += file_size
                print(f"  ✓ Deleted: {rel_path} ({file_size} bytes)")
            except Exception as e:
                print(f"  ✗ Error deleting {rel_path}: {str(e)}")
        
        print(f"\n✓ Deleted {deleted_count} orphaned personnel pictures ({deleted_size / 1024:.2f} KB)")
        return deleted_count, deleted_size
    else:
        print("\n✓ No orphaned personnel picture files found")
        return 0, 0


def cleanup_orphaned_user_pictures():
    """Remove user profile pictures that don't have database records"""
    print("\n" + "="*80)
    print("CLEANUP: Orphaned User Profile Pictures")
    print("="*80)
    
    user_directory = os.path.join(settings.MEDIA_ROOT, 'users', 'profile_pictures')
    
    if not os.path.exists(user_directory):
        print("✓ No user profile pictures directory found")
        return 0, 0
    
    # Get all user picture files
    all_picture_files = scan_directory(user_directory)
    print(f"\n📁 Found {len(all_picture_files)} user profile picture files on disk")
    
    # Get all user profile database records with pictures
    db_profiles = UserProfile.objects.filter(profile_picture__isnull=False).exclude(profile_picture='')
    db_picture_paths = set()
    
    for profile in db_profiles:
        if profile.profile_picture:
            db_picture_paths.add(profile.profile_picture.name.replace('\\', '/'))
    
    print(f"📊 Found {len(db_picture_paths)} user profile pictures in database")
    
    # Find orphaned files
    orphaned_files = []
    for full_path, rel_path in all_picture_files:
        normalized_rel = rel_path.replace('\\', '/')
        if normalized_rel not in db_picture_paths:
            orphaned_files.append((full_path, rel_path))
    
    if orphaned_files:
        print(f"\n🗑️  Found {len(orphaned_files)} orphaned user profile picture files:")
        deleted_count = 0
        deleted_size = 0
        
        for full_path, rel_path in orphaned_files:
            try:
                file_size = os.path.getsize(full_path)
                os.remove(full_path)
                deleted_count += 1
                deleted_size += file_size
                print(f"  ✓ Deleted: {rel_path} ({file_size} bytes)")
            except Exception as e:
                print(f"  ✗ Error deleting {rel_path}: {str(e)}")
        
        print(f"\n✓ Deleted {deleted_count} orphaned user profile pictures ({deleted_size / 1024:.2f} KB)")
        return deleted_count, deleted_size
    else:
        print("\n✓ No orphaned user profile picture files found")
        return 0, 0


def show_statistics():
    """Show current media file statistics"""
    print("\n" + "="*80)
    print("MEDIA FILES STATISTICS")
    print("="*80)
    
    media_root = settings.MEDIA_ROOT
    
    # Count QR codes
    qr_dir = os.path.join(media_root, 'qr_codes')
    qr_count = len(scan_directory(qr_dir)) if os.path.exists(qr_dir) else 0
    
    # Count personnel pictures
    personnel_dir = os.path.join(media_root, 'personnel', 'pictures')
    personnel_count = len(scan_directory(personnel_dir)) if os.path.exists(personnel_dir) else 0
    
    # Count user pictures
    user_dir = os.path.join(media_root, 'users', 'profile_pictures')
    user_count = len(scan_directory(user_dir)) if os.path.exists(user_dir) else 0
    
    # Database counts
    qr_db_count = QRCodeImage.objects.filter(qr_image__isnull=False).count()
    personnel_db_count = Personnel.objects.filter(picture__isnull=False).exclude(picture='').count()
    user_db_count = UserProfile.objects.filter(profile_picture__isnull=False).exclude(profile_picture='').count()
    
    print(f"\n📁 Files on Disk:")
    print(f"   QR Codes: {qr_count} files")
    print(f"   Personnel Pictures: {personnel_count} files")
    print(f"   User Profile Pictures: {user_count} files")
    print(f"   Total: {qr_count + personnel_count + user_count} files")
    
    print(f"\n📊 Database Records:")
    print(f"   QR Codes: {qr_db_count} records")
    print(f"   Personnel Pictures: {personnel_db_count} records")
    print(f"   User Profile Pictures: {user_db_count} records")
    print(f"   Total: {qr_db_count + personnel_db_count + user_db_count} records")
    
    orphaned_total = (qr_count - qr_db_count) + (personnel_count - personnel_db_count) + (user_count - user_db_count)
    
    if orphaned_total > 0:
        print(f"\n⚠️  Potential orphaned files: {orphaned_total}")
    else:
        print(f"\n✓ All files have corresponding database records")


def main():
    print("\n" + "="*80)
    print("ORPHANED FILES CLEANUP UTILITY")
    print("="*80)
    print("\nScanning media directory for orphaned files...")
    
    # Show initial statistics
    show_statistics()
    
    # Cleanup orphaned files
    qr_deleted, qr_size = cleanup_orphaned_qr_codes()
    personnel_deleted, personnel_size = cleanup_orphaned_personnel_pictures()
    user_deleted, user_size = cleanup_orphaned_user_pictures()
    
    # Summary
    total_deleted = qr_deleted + personnel_deleted + user_deleted
    total_size = qr_size + personnel_size + user_size
    
    print("\n" + "="*80)
    print("CLEANUP SUMMARY")
    print("="*80)
    print(f"\n✓ Total files deleted: {total_deleted}")
    print(f"✓ Total space freed: {total_size / 1024:.2f} KB ({total_size / (1024*1024):.2f} MB)")
    
    # Show final statistics
    show_statistics()
    
    print("\n" + "="*80)
    if total_deleted > 0:
        print("✓ CLEANUP COMPLETED - Orphaned files removed")
    else:
        print("✓ NO CLEANUP NEEDED - All files are in use")
    print("="*80 + "\n")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
