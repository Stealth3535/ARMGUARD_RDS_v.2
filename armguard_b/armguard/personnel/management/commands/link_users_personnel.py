"""
Management command to link existing User accounts to Personnel records
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from personnel.models import Personnel


class Command(BaseCommand):
    help = 'Link existing User accounts to Personnel records by matching serial number to username'

    def handle(self, *args, **options):
        self.stdout.write('Linking users to personnel...')
        
        linked_count = 0
        not_found_count = 0
        already_linked_count = 0
        
        # Get all users
        users = User.objects.all()
        
        for user in users:
            # Skip if already has personnel
            try:
                if user.personnel:
                    self.stdout.write(f'  ✓ User "{user.username}" already linked to personnel {user.personnel.id}')
                    already_linked_count += 1
                    continue
            except Personnel.DoesNotExist:
                pass
            
            # Try to find personnel by serial matching username
            personnel = Personnel.objects.filter(serial=user.username).first()
            
            if personnel:
                if not personnel.user:
                    # Link them
                    personnel.user = user
                    personnel.save()
                    self.stdout.write(self.style.SUCCESS(
                        f'  ✓ Linked user "{user.username}" to personnel {personnel.id} ({personnel.get_full_name()})'
                    ))
                    linked_count += 1
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  ! Personnel {personnel.id} already linked to another user'
                    ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'  ! No personnel found with serial "{user.username}"'
                ))
                not_found_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Summary:'))
        self.stdout.write(f'  Already linked: {already_linked_count}')
        self.stdout.write(f'  Newly linked: {linked_count}')
        self.stdout.write(f'  Not found: {not_found_count}')
        self.stdout.write(self.style.SUCCESS('Done!'))
