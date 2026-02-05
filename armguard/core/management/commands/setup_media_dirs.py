"""
Management command to set up media directories with proper permissions
Usage: python manage.py setup_media_dirs
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import sys
import stat


class Command(BaseCommand):
    help = 'Creates media directories with proper permissions for file uploads and QR codes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--owner',
            type=str,
            default='www-data',
            help='System user that should own the directories (default: www-data)',
        )
        parser.add_argument(
            '--group',
            type=str,
            default='www-data',
            help='System group that should own the directories (default: www-data)',
        )

    def handle(self, *args, **options):
        owner = options['owner']
        group = options['group']
        
        # Define all media subdirectories that need to be created
        media_dirs = [
            'qr_codes/personnel',
            'qr_codes/items',
            'personnel/pictures',
            'users/profile_pictures',
            'transaction_forms',
        ]
        
        self.stdout.write(self.style.SUCCESS('Setting up media directories...'))
        self.stdout.write(f'MEDIA_ROOT: {settings.MEDIA_ROOT}')
        
        # Create main media directory if it doesn't exist
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT, mode=0o775)
            self.stdout.write(self.style.SUCCESS(f'✓ Created {settings.MEDIA_ROOT}'))
        else:
            self.stdout.write(f'  {settings.MEDIA_ROOT} already exists')
        
        # Create all subdirectories
        created_count = 0
        for subdir in media_dirs:
            full_path = os.path.join(settings.MEDIA_ROOT, subdir)
            
            if not os.path.exists(full_path):
                os.makedirs(full_path, mode=0o775)
                self.stdout.write(self.style.SUCCESS(f'✓ Created {full_path}'))
                created_count += 1
            else:
                self.stdout.write(f'  {full_path} already exists')
            
            # Set permissions to 775 (rwxrwxr-x)
            try:
                os.chmod(full_path, 0o775)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not set permissions on {full_path}: {e}')
                )
        
        # Try to change ownership on Linux/Unix systems
        if sys.platform != 'win32':
            self.stdout.write('\nAttempting to set ownership...')
            try:
                import pwd
                import grp
                
                # Get UID and GID
                try:
                    uid = pwd.getpwnam(owner).pw_uid
                    gid = grp.getgrnam(group).gr_gid
                    
                    # Change ownership recursively
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        os.chown(root, uid, gid)
                        for dir_name in dirs:
                            os.chown(os.path.join(root, dir_name), uid, gid)
                        for file_name in files:
                            os.chown(os.path.join(root, file_name), uid, gid)
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Changed ownership to {owner}:{group}')
                    )
                except KeyError:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  User "{owner}" or group "{group}" not found. '
                            'Run this command with sudo and correct --owner/--group options.'
                        )
                    )
                except PermissionError:
                    self.stdout.write(
                        self.style.WARNING(
                            '  Permission denied. Run this command with sudo to change ownership:\n'
                            f'  sudo python manage.py setup_media_dirs --owner={owner} --group={group}'
                        )
                    )
            except ImportError:
                pass
        else:
            self.stdout.write(
                self.style.WARNING(
                    '\nNote: Running on Windows. Ownership settings are not applicable.'
                )
            )
        
        # Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('Media directories setup complete!'))
        self.stdout.write(f'Created: {created_count} new directories')
        self.stdout.write('Permissions: 775 (rwxrwxr-x)')
        
        if sys.platform != 'win32':
            self.stdout.write('\nFor production deployment, ensure you run:')
            self.stdout.write(
                self.style.WARNING(
                    f'sudo python manage.py setup_media_dirs --owner={owner} --group={group}'
                )
            )
        
        self.stdout.write('='*60)
