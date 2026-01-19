"""
Management command to create an admin user (non-superuser)
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create an admin user (staff user, not superuser)'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='Username for the admin user')
        parser.add_argument('--password', type=str, help='Password for the admin user', default='admin123')
        parser.add_argument('--email', type=str, help='Email for the admin user', default='')
        parser.add_argument('--first-name', type=str, help='First name', default='')
        parser.add_argument('--last-name', type=str, help='Last name', default='')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User "{username}" already exists!'))
            return

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )
        user.is_staff = True
        user.is_superuser = False
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{username}"'))
        self.stdout.write(self.style.SUCCESS(f'  - Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'  - Password: {password}'))
        self.stdout.write(self.style.SUCCESS(f'  - Is Staff: True'))
        self.stdout.write(self.style.SUCCESS(f'  - Is Superuser: False'))
        self.stdout.write(self.style.WARNING('  - This user can access /admin/ but NOT /superadmin/'))
