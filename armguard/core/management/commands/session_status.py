"""
Session Status Management Command

Usage:
    python manage.py session_status

Shows current session configuration and active sessions.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Display current session configuration and active sessions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== ArmGuard Session Configuration ===\n'))
        
        # Display session settings
        self.stdout.write(f"SESSION_ENGINE: {settings.SESSION_ENGINE}")
        self.stdout.write(f"SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE} seconds ({settings.SESSION_COOKIE_AGE/60} minutes)")
        self.stdout.write(f"SESSION_SAVE_EVERY_REQUEST: {settings.SESSION_SAVE_EVERY_REQUEST}")
        self.stdout.write(f"SESSION_EXPIRE_AT_BROWSER_CLOSE: {settings.SESSION_EXPIRE_AT_BROWSER_CLOSE}")
        self.stdout.write(f"SESSION_COOKIE_NAME: {getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')}")
        self.stdout.write(f"SESSION_COOKIE_HTTPONLY: {settings.SESSION_COOKIE_HTTPONLY}")
        self.stdout.write(f"SESSION_COOKIE_SECURE: {settings.SESSION_COOKIE_SECURE}")
        
        self.stdout.write(self.style.SUCCESS('\n=== Active Sessions ===\n'))
        
        # Count active sessions
        now = timezone.now()
        active_sessions = Session.objects.filter(expire_date__gte=now)
        expired_sessions = Session.objects.filter(expire_date__lt=now)
        
        self.stdout.write(f"Active sessions: {active_sessions.count()}")
        self.stdout.write(f"Expired sessions: {expired_sessions.count()}")
        
        if active_sessions.count() > 0:
            self.stdout.write(self.style.SUCCESS('\n=== Active Session Details ===\n'))
            for session in active_sessions[:10]:  # Show first 10
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        username = user.username
                    except User.DoesNotExist:
                        username = 'Unknown'
                else:
                    username = 'Anonymous'
                
                time_left = (session.expire_date - now).total_seconds() / 60
                
                self.stdout.write(
                    f"  Session: {session.session_key[:20]}... | "
                    f"User: {username} | "
                    f"Expires: {session.expire_date.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"Time left: {time_left:.1f} min"
                )
        
        self.stdout.write(self.style.SUCCESS('\n=== Recommendations ===\n'))
        
        if not settings.SESSION_SAVE_EVERY_REQUEST:
            self.stdout.write(self.style.ERROR(
                '⚠️  WARNING: SESSION_SAVE_EVERY_REQUEST is False. '
                'Sessions will expire even if user is active!'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '✓ SESSION_SAVE_EVERY_REQUEST is True. Sessions will refresh on each request.'
            ))
        
        if 'cache' in settings.SESSION_ENGINE:
            self.stdout.write(self.style.WARNING(
                '⚠️  WARNING: Using cache backend for sessions. Cache may clear causing session loss. '
                'Consider using database backend for reliability.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                '✓ Using database backend for sessions. More reliable than cache.'
            ))
        
        self.stdout.write(self.style.SUCCESS('\n=== Cleanup Commands ===\n'))
        self.stdout.write('Clear expired sessions: python manage.py clearsessions')
        self.stdout.write('Clear all sessions (logout everyone): python manage.py flush_sessions')
        
        self.stdout.write('')
