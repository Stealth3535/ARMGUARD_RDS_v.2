"""
Management command to setup media directories with proper structure
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Setup media directories for profile pictures and personnel photos'
    
    def handle(self, *args, **options):
        media_dirs = [
            'users/profile_pictures',
            'personnel/pictures',
            'qr_codes/personnel',
            'qr_codes/items',
            'temp'
        ]
        
        created_dirs = []
        
        for dir_path in media_dirs:
            full_path = os.path.join(settings.MEDIA_ROOT, dir_path)
            try:
                os.makedirs(full_path, exist_ok=True)
                created_dirs.append(dir_path)
                self.stdout.write(f"✓ Created/verified: {full_path}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to create {full_path}: {e}")
                )
        
        if created_dirs:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Successfully setup {len(created_dirs)} media directories")
            )
        else:
            self.stdout.write(
                self.style.WARNING("No directories were created (they may already exist)")
            )