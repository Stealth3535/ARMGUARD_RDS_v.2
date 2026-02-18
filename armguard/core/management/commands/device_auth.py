"""
Django management command for device authorization management
Usage: python manage.py device_auth [options]
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.middleware.device_authorization import DeviceAuthorizationMiddleware
from pathlib import Path
import json
from django.utils import timezone


class Command(BaseCommand):
    help = 'Manage device authorization system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list', '-l',
            action='store_true',
            help='List all authorized devices'
        )
        
        parser.add_argument(
            '--add', '-a',
            action='store_true', 
            help='Add a new authorized device'
        )
        
        parser.add_argument(
            '--revoke', '-r',
            type=str,
            help='Revoke device by fingerprint or IP'
        )
        
        parser.add_argument(
            '--status', '-s',
            action='store_true',
            help='Show device authorization system status'
        )
        
        parser.add_argument(
            '--production', '-p',
            action='store_true',
            help='Configure for production deployment'
        )
        
        parser.add_argument(
            '--name',
            type=str,
            help='Device name (for --add)'
        )
        
        parser.add_argument(
            '--ip', 
            type=str,
            help='Device IP address (for --add)'
        )
        
        parser.add_argument(
            '--description',
            type=str,
            help='Device description (for --add)'
        )
        
        parser.add_argument(
            '--can-transact',
            action='store_true',
            help='Allow device to perform transactions (for --add)'
        )
        
        parser.add_argument(
            '--security-level',
            choices=['STANDARD', 'HIGH', 'MILITARY'],
            default='STANDARD',
            help='Security level for device (for --add)'
        )

    def handle(self, *args, **options):
        try:
            middleware = DeviceAuthorizationMiddleware(lambda req: None)
            
            if options['list']:
                self._list_devices(middleware)
                
            elif options['add']:
                self._add_device(middleware, options)
                
            elif options['revoke']:
                self._revoke_device(middleware, options['revoke'])
                
            elif options['status']:
                self._show_status(middleware)
                
            elif options['production']:
                self._configure_production(middleware)
                
            else:
                self.stdout.write(self.style.WARNING('No action specified. Use --help for options.'))
                
        except Exception as e:
            raise CommandError(f'Device authorization management failed: {e}')

    def _list_devices(self, middleware):
        """List all authorized devices"""            
        self.stdout.write(self.style.SUCCESS('🛡️  AUTHORIZED DEVICES'))
        self.stdout.write('=' * 60)
        
        devices = middleware.authorized_devices.get('devices', [])
        
        if not devices:
            self.stdout.write(self.style.WARNING('No devices registered'))
            return
            
        for i, device in enumerate(devices, 1):
            name = device.get('name', 'Unknown')
            ip = device.get('ip', 'N/A')
            active = '✅' if device.get('active', True) else '❌'
            can_transact = '💳' if device.get('can_transact', False) else '🚫'
            security_level = device.get('security_level', 'STANDARD')
            
            self.stdout.write(f'\n{i}. {name}')
            self.stdout.write(f'   📍 IP: {ip}')
            self.stdout.write(f'   {active} Active: {device.get("active", True)}')
            self.stdout.write(f'   {can_transact} Transactions: {device.get("can_transact", False)}')
            self.stdout.write(f'   🔒 Security: {security_level}')
            self.stdout.write(f'   📋 Description: {device.get("description", "N/A")}')
            
            if device.get('roles'):
                self.stdout.write(f'   👤 Roles: {", ".join(device.get("roles", []))}')

    def _add_device(self, middleware, options):
        """Add new authorized device"""
        if not options['name'] or not options['ip']:
            raise CommandError('--name and --ip are required for adding devices')
            
        # Generate fingerprint placeholder (in real use, this would come from actual request)
        device_fingerprint = f"manual_{hash(options['name'] + options['ip'])}_{timezone.now().timestamp()}"[:32]
        
        success = middleware.authorize_device(
            device_fingerprint=device_fingerprint,
            device_name=options['name'],
            ip_address=options['ip'],
            description=options.get('description', ''),
            can_transact=options.get('can_transact', False),
            security_level=options.get('security_level', 'STANDARD'),
            roles=['manual_entry']
        )
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Device authorized: {options["name"]} ({options["ip"]})'
                )
            )
        else:
            raise CommandError('Failed to authorize device')

    def _revoke_device(self, middleware, identifier):
        """Revoke device authorization""" 
        revoked = False
        
        # Try to find device by fingerprint or IP
        for device in middleware.authorized_devices.get('devices', []):
            if (device.get('fingerprint', '').startswith(identifier) or 
                device.get('ip') == identifier or
                identifier in device.get('name', '')):
                
                fingerprint = device.get('fingerprint')
                name = device.get('name', 'Unknown')
                
                if middleware.revoke_device(fingerprint, f"Manual revocation via management command"):
                    self.stdout.write(
                        self.style.SUCCESS(f'✅ Device revoked: {name}')
                    )
                    revoked = True
                    break
        
        if not revoked:
            raise CommandError(f'Device not found: {identifier}')

    def _show_status(self, middleware):
        """Show device authorization system status"""
        self.stdout.write(self.style.SUCCESS('🛡️  DEVICE AUTHORIZATION SYSTEM STATUS'))
        self.stdout.write('=' * 60)
        
        # Basic configuration
        config = middleware.authorized_devices
        self.stdout.write(f'🔧 Security Mode: {config.get("security_mode", "UNKNOWN")}')
        self.stdout.write(f'🔓 Allow All: {config.get("allow_all", "NOT SET")}')
        self.stdout.write(f'🐛 DEBUG Mode: {settings.DEBUG}')
        
        # Device statistics
        if hasattr(middleware, 'get_device_stats'):
            stats = middleware.get_device_stats()
            self.stdout.write(f'\n📊 DEVICE STATISTICS:')
            self.stdout.write(f'   Total Devices: {stats["total_devices"]}')
            self.stdout.write(f'   Active Devices: {stats["active_devices"]}')
            self.stdout.write(f'   Transaction Enabled: {stats["transaction_enabled"]}')
            self.stdout.write(f'   Locked Out: {stats["locked_out_devices"]}')
            
            if stats['security_levels']:
                self.stdout.write(f'   Security Levels:')
                for level, count in stats['security_levels'].items():
                    self.stdout.write(f'     - {level}: {count}')
        
        # Path protection
        restricted_paths = config.get('restricted_paths', [])
        high_security_paths = config.get('high_security_paths', [])
        
        self.stdout.write(f'\n🚫 PROTECTED PATHS:')
        self.stdout.write(f'   Restricted: {len(restricted_paths)}')
        self.stdout.write(f'   High Security: {len(high_security_paths)}')
        
        # Security settings
        audit_settings = config.get('audit_settings', {})
        if audit_settings:
            self.stdout.write(f'\n📋 AUDIT SETTINGS:')
            self.stdout.write(f'   Log All Attempts: {audit_settings.get("log_all_attempts", False)}')
            self.stdout.write(f'   Alert on Unauthorized: {audit_settings.get("alert_on_unauthorized", False)}')
            self.stdout.write(f'   Retention Days: {audit_settings.get("retention_days", "N/A")}')

    def _configure_production(self, middleware):
        """Configure system for production deployment"""
        self.stdout.write(self.style.WARNING('🚀 CONFIGURING FOR PRODUCTION DEPLOYMENT'))
        self.stdout.write('=' * 60)
        
        config = middleware.authorized_devices
        
        # Set production flags
        changes_made = []
        
        if config.get('allow_all', True):
            config['allow_all'] = False
            changes_made.append('✅ Disabled allow_all mode')
            
        if config.get('security_mode') != 'PRODUCTION':
            config['security_mode'] = 'PRODUCTION'
            changes_made.append('✅ Set security_mode to PRODUCTION')
            
        if not config.get('require_device_registration'):
            config['require_device_registration'] = True
            changes_made.append('✅ Enabled mandatory device registration')
            
        # Ensure security settings
        if not config.get('audit_settings'):
            config['audit_settings'] = {
                'log_all_attempts': True,
                'alert_on_unauthorized': True,
                'retention_days': 90
            }
            changes_made.append('✅ Configured comprehensive audit settings')
            
        # Update timestamp
        config['last_updated'] = timezone.now().isoformat()
        config['configured_for_production'] = True
        
        # Save changes
        middleware.save_authorized_devices()
        
        # Display changes
        if changes_made:
            self.stdout.write(self.style.SUCCESS('\n📝 PRODUCTION CHANGES APPLIED:'))
            for change in changes_made:
                self.stdout.write(f'   {change}')
        else:
            self.stdout.write(self.style.SUCCESS('✅ System already configured for production'))
            
        self.stdout.write(self.style.SUCCESS('\n🎯 PRODUCTION DEPLOYMENT READY'))
        
        # Verify critical settings
        self.stdout.write('\n🔍 VERIFICATION:')
        self.stdout.write(f'  Allow All: {config.get("allow_all")} (should be False)')
        self.stdout.write(f'  Security Mode: {config.get("security_mode")} (should be PRODUCTION)')
        self.stdout.write(f'  DEBUG Mode: {settings.DEBUG} (should be False for production)')
        
        if settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  WARNING: Django DEBUG=True detected. '
                    'Set DEBUG=False in production settings!'
                )
            )