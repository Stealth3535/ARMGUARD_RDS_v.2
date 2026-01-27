"""
Management command to cleanup orphaned media files
Usage: python manage.py cleanup_media
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
from pathlib import Path

from personnel.models import Personnel
from users.models import UserProfile
from qr_manager.models import QRCodeImage


class Command(BaseCommand):
    help = 'Remove orphaned QR codes and pictures that no longer have database records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No files will be deleted'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('ORPHANED FILES CLEANUP'))
        self.stdout.write(self.style.SUCCESS('='*70))
        
        # Cleanup QR codes
        qr_deleted, qr_size = self.cleanup_qr_codes(dry_run, verbose)
        
        # Cleanup personnel pictures
        personnel_deleted, personnel_size = self.cleanup_personnel_pictures(dry_run, verbose)
        
        # Cleanup user pictures
        user_deleted, user_size = self.cleanup_user_pictures(dry_run, verbose)
        
        # Summary
        total_deleted = qr_deleted + personnel_deleted + user_deleted
        total_size = qr_size + personnel_size + user_size
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('CLEANUP SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(f'Total files {"would be " if dry_run else ""}deleted: {total_deleted}')
        self.stdout.write(f'Total space {"would be " if dry_run else ""}freed: {total_size / 1024:.2f} KB')
        
        if total_deleted > 0:
            if dry_run:
                self.stdout.write(self.style.WARNING('\nRun without --dry-run to actually delete files'))
            else:
                self.stdout.write(self.style.SUCCESS('\n✓ Cleanup completed successfully'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✓ No orphaned files found'))
    
    def scan_directory(self, directory_path):
        """Scan directory and return all files"""
        files = []
        if os.path.exists(directory_path):
            for root, dirs, filenames in os.walk(directory_path):
                for filename in filenames:
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, settings.MEDIA_ROOT)
                    files.append((full_path, rel_path))
        return files
    
    def cleanup_qr_codes(self, dry_run, verbose):
        """Remove orphaned QR code images"""
        self.stdout.write('\n' + '-'*70)
        self.stdout.write('QR Codes')
        self.stdout.write('-'*70)
        
        qr_directory = os.path.join(settings.MEDIA_ROOT, 'qr_codes')
        
        if not os.path.exists(qr_directory):
            self.stdout.write('No QR codes directory found')
            return 0, 0
        
        all_files = self.scan_directory(qr_directory)
        db_qr_codes = QRCodeImage.objects.filter(qr_image__isnull=False)
        db_paths = set(qr.qr_image.name.replace('\\', '/') for qr in db_qr_codes if qr.qr_image)
        
        orphaned = [(fp, rp) for fp, rp in all_files if rp.replace('\\', '/') not in db_paths]
        
        if verbose or orphaned:
            self.stdout.write(f'Files on disk: {len(all_files)}')
            self.stdout.write(f'Database records: {len(db_paths)}')
        
        if orphaned:
            self.stdout.write(self.style.WARNING(f'Found {len(orphaned)} orphaned QR files'))
            return self.delete_files(orphaned, dry_run, verbose)
        else:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned QR files'))
            return 0, 0
    
    def cleanup_personnel_pictures(self, dry_run, verbose):
        """Remove orphaned personnel pictures"""
        self.stdout.write('\n' + '-'*70)
        self.stdout.write('Personnel Pictures')
        self.stdout.write('-'*70)
        
        directory = os.path.join(settings.MEDIA_ROOT, 'personnel', 'pictures')
        
        if not os.path.exists(directory):
            self.stdout.write('No personnel pictures directory found')
            return 0, 0
        
        all_files = self.scan_directory(directory)
        db_personnel = Personnel.objects.filter(picture__isnull=False).exclude(picture='')
        db_paths = set(p.picture.name.replace('\\', '/') for p in db_personnel if p.picture)
        
        orphaned = [(fp, rp) for fp, rp in all_files if rp.replace('\\', '/') not in db_paths]
        
        if verbose or orphaned:
            self.stdout.write(f'Files on disk: {len(all_files)}')
            self.stdout.write(f'Database records: {len(db_paths)}')
        
        if orphaned:
            self.stdout.write(self.style.WARNING(f'Found {len(orphaned)} orphaned personnel pictures'))
            return self.delete_files(orphaned, dry_run, verbose)
        else:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned personnel pictures'))
            return 0, 0
    
    def cleanup_user_pictures(self, dry_run, verbose):
        """Remove orphaned user profile pictures"""
        self.stdout.write('\n' + '-'*70)
        self.stdout.write('User Profile Pictures')
        self.stdout.write('-'*70)
        
        directory = os.path.join(settings.MEDIA_ROOT, 'users', 'profile_pictures')
        
        if not os.path.exists(directory):
            self.stdout.write('No user pictures directory found')
            return 0, 0
        
        all_files = self.scan_directory(directory)
        db_profiles = UserProfile.objects.filter(profile_picture__isnull=False).exclude(profile_picture='')
        db_paths = set(p.profile_picture.name.replace('\\', '/') for p in db_profiles if p.profile_picture)
        
        orphaned = [(fp, rp) for fp, rp in all_files if rp.replace('\\', '/') not in db_paths]
        
        if verbose or orphaned:
            self.stdout.write(f'Files on disk: {len(all_files)}')
            self.stdout.write(f'Database records: {len(db_paths)}')
        
        if orphaned:
            self.stdout.write(self.style.WARNING(f'Found {len(orphaned)} orphaned user pictures'))
            return self.delete_files(orphaned, dry_run, verbose)
        else:
            self.stdout.write(self.style.SUCCESS('✓ No orphaned user pictures'))
            return 0, 0
    
    def delete_files(self, files, dry_run, verbose):
        """Delete files and return count and size"""
        deleted_count = 0
        deleted_size = 0
        
        for full_path, rel_path in files:
            try:
                file_size = os.path.getsize(full_path)
                
                if not dry_run:
                    os.remove(full_path)
                
                deleted_count += 1
                deleted_size += file_size
                
                if verbose:
                    action = 'Would delete' if dry_run else 'Deleted'
                    self.stdout.write(f'  {action}: {rel_path} ({file_size} bytes)')
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error with {rel_path}: {str(e)}'))
        
        return deleted_count, deleted_size
