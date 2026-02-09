"""
Flush All Sessions Management Command

Usage:
    python manage.py flush_sessions

Deletes all session records from the database, effectively logging out all users.
Use this when troubleshooting session issues or when you need to force all users to re-login.
"""
from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session


class Command(BaseCommand):
    help = 'Delete all session records (logs out all users)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        if not options['yes']:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  WARNING: This will delete ALL sessions and log out ALL users!\n'
            ))
            confirm = input('Are you sure you want to continue? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return
        
        # Count sessions before deletion
        total_sessions = Session.objects.count()
        
        # Delete all sessions
        Session.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Successfully deleted {total_sessions} session(s).\n'
            f'All users have been logged out and will need to re-login.\n'
        ))
