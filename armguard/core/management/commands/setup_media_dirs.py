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
            
            # Set permissions to 775 (rwxrwxr-x) immediately after creation
            try:
                os.chmod(full_path, 0o775)
                # Also set permissions on all parent directories up to MEDIA_ROOT
                parent = os.path.dirname(full_path)
                while parent != settings.MEDIA_ROOT and parent != '/':
                    os.chmod(parent, 0o775)
                    parent = os.path.dirname(parent)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Could not set permissions on {full_path}: {e}')
                )
        
        # Set permissions on root media directory
        try:
            os.chmod(settings.MEDIA_ROOT, 0o775)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'Could not set permissions on {settings.MEDIA_ROOT}: {e}')
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
                    
                    # Change ownership on each created subdirectory immediately
                    self.stdout.write(f'Setting ownership to {owner}:{group} on each directory...')
                    for subdir in subdirs:
                        full_path = os.path.join(settings.MEDIA_ROOT, subdir)
                        if os.path.exists(full_path):
                            os.chown(full_path, uid, gid)
                            # Set ownership on parent directories too
                            parent = os.path.dirname(full_path)
                            while parent != settings.MEDIA_ROOT and parent != '/':
                                try:
                                    os.chown(parent, uid, gid)
                                except:
                                    pass
                                parent = os.path.dirname(parent)
                    
                    # Set ownership on root media directory
                    os.chown(settings.MEDIA_ROOT, uid, gid)
                    
                    # Final recursive pass to ensure everything is correct
                    self.stdout.write('Applying final recursive ownership pass...')
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        os.chown(root, uid, gid)
                        for dir_name in dirs:
                            try:
                                os.chown(os.path.join(root, dir_name), uid, gid)
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f'  Could not chown {dir_name}: {e}')
                                )
                        for file_name in files:
                            try:
                                os.chown(os.path.join(root, file_name), uid, gid)
                            except Exception as e:
                                self.stdout.write(
                                    self.style.WARNING(f'  Could not chown {file_name}: {e}')
                                )
                    
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
