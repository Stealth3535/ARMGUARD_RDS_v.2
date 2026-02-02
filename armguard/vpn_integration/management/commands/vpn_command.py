# VPN Management Django Command
# Usage: python manage.py vpn_command --action status|start|stop|list|add|remove|backup

import json
import asyncio
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils import timezone
import sys
import os

# Add VPN integration path
vpn_integration_path = os.path.join(settings.BASE_DIR, 'vpn_integration')
sys.path.append(vpn_integration_path)

try:
    from core_integration.vpn_utils import VPNManager, get_vpn_health_status, validate_vpn_client_name
    from monitoring.vpn_monitor import get_vpn_monitor, VPNMonitoringService
except ImportError as e:
    print(f"Error importing VPN modules: {e}")
    print("Make sure VPN integration is properly installed")
    sys.exit(1)

class Command(BaseCommand):
    help = 'Manage ArmGuard VPN integration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            required=True,
            choices=['status', 'start', 'stop', 'list', 'add', 'remove', 'backup', 'monitor', 'alerts', 'stats'],
            help='Action to perform'
        )
        
        parser.add_argument(
            '--client-name',
            type=str,
            help='Client name (for add/remove actions)'
        )
        
        parser.add_argument(
            '--role',
            type=str,
            choices=['commander', 'armorer', 'emergency', 'personnel'],
            help='VPN role (for add action)'
        )
        
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Hours to look back for stats/alerts (default: 24)'
        )
        
        parser.add_argument(
            '--output-format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format'
        )

    def handle(self, *args, **options):
        action = options['action']
        
        try:
            if action == 'status':
                self.handle_status(options)
            elif action == 'start':
                self.handle_start_vpn()
            elif action == 'stop':
                self.handle_stop_vpn()
            elif action == 'list':
                self.handle_list_clients(options)
            elif action == 'add':
                self.handle_add_client(options)
            elif action == 'remove':
                self.handle_remove_client(options)
            elif action == 'backup':
                self.handle_backup()
            elif action == 'monitor':
                self.handle_monitor()
            elif action == 'alerts':
                self.handle_alerts(options)
            elif action == 'stats':
                self.handle_stats(options)
                
        except Exception as e:
            raise CommandError(f'Error executing {action}: {str(e)}')

    def handle_status(self, options):
        """Show VPN status"""
        self.stdout.write(self.style.SUCCESS('=== ArmGuard VPN Status ==='))
        
        # Get VPN manager status
        vpn_manager = VPNManager()
        status = vpn_manager.get_vpn_status()
        health = get_vpn_health_status()
        
        if options['output_format'] == 'json':
            result = {
                'vpn_status': status,
                'health_status': health,
                'timestamp': timezone.now().isoformat()
            }
            self.stdout.write(json.dumps(result, indent=2, default=str))
            return
        
        # Text output
        if status.get('interface_active'):
            self.stdout.write(self.style.SUCCESS('✓ VPN Interface: Active'))
            if status.get('listening_port'):
                self.stdout.write(f'  Listening Port: {status["listening_port"]}')
        else:
            self.stdout.write(self.style.ERROR('✗ VPN Interface: Inactive'))
            
        # Peer information
        peers = status.get('peers', [])
        self.stdout.write(f'\nConnected Peers: {len(peers)}')
        
        if peers:
            connected_peers = vpn_manager.get_connected_peers()
            for peer in connected_peers:
                client_name = peer.get('client_name', 'Unknown')
                vpn_ip = peer.get('vpn_ip', 'Unknown')
                vpn_role = peer.get('vpn_role', 'unknown')
                handshake = peer.get('latest_handshake', 'Never')
                
                self.stdout.write(f'  • {client_name} ({vpn_ip}) - Role: {vpn_role}')
                self.stdout.write(f'    Last handshake: {handshake}')
        
        # Health status
        self.stdout.write(f'\nOverall Health: {health["overall_status"].upper()}')
        
        if health.get('errors'):
            self.stdout.write(self.style.ERROR('Errors:'))
            for error in health['errors']:
                self.stdout.write(f'  ✗ {error}')
        
        if health.get('warnings'):
            self.stdout.write(self.style.WARNING('Warnings:'))
            for warning in health['warnings']:
                self.stdout.write(f'  ⚠ {warning}')
        
        # Data transfer
        total_transfer = health.get('total_data_transfer', 0)
        if total_transfer > 0:
            transfer_mb = total_transfer / (1024 * 1024)
            self.stdout.write(f'\nTotal Data Transfer: {transfer_mb:.2f} MB')

    def handle_start_vpn(self):
        """Start VPN service"""
        self.stdout.write('Starting VPN service...')
        
        try:
            import subprocess
            result = subprocess.run(['sudo', 'wg-quick', 'up', 'wg0'], 
                                  capture_output=True, text=True, check=True)
            
            self.stdout.write(self.style.SUCCESS('✓ VPN service started successfully'))
            
        except subprocess.CalledProcessError as e:
            if 'already exists' in e.stderr:
                self.stdout.write(self.style.WARNING('VPN service is already running'))
            else:
                raise CommandError(f'Failed to start VPN: {e.stderr}')
        except FileNotFoundError:
            raise CommandError('WireGuard not installed. Please run setup first.')

    def handle_stop_vpn(self):
        """Stop VPN service"""
        self.stdout.write('Stopping VPN service...')
        
        try:
            import subprocess
            result = subprocess.run(['sudo', 'wg-quick', 'down', 'wg0'], 
                                  capture_output=True, text=True, check=True)
            
            self.stdout.write(self.style.SUCCESS('✓ VPN service stopped successfully'))
            
        except subprocess.CalledProcessError as e:
            if 'is not a WireGuard interface' in e.stderr:
                self.stdout.write(self.style.WARNING('VPN service is not running'))
            else:
                raise CommandError(f'Failed to stop VPN: {e.stderr}')

    def handle_list_clients(self, options):
        """List VPN clients"""
        self.stdout.write(self.style.SUCCESS('=== VPN Clients ==='))
        
        vpn_manager = VPNManager()
        connected_peers = vpn_manager.get_connected_peers()
        
        if options['output_format'] == 'json':
            self.stdout.write(json.dumps(connected_peers, indent=2, default=str))
            return
        
        if not connected_peers:
            self.stdout.write('No clients currently connected')
            return
        
        # Group by role
        by_role = {}
        for peer in connected_peers:
            role = peer.get('vpn_role', 'unknown')
            if role not in by_role:
                by_role[role] = []
            by_role[role].append(peer)
        
        for role, peers in by_role.items():
            self.stdout.write(f'\n{role.upper()} ({len(peers)} clients):')
            for peer in peers:
                client_name = peer.get('client_name', 'Unknown')
                vpn_ip = peer.get('vpn_ip', 'Unknown')
                endpoint = peer.get('endpoint', 'Unknown')
                handshake = peer.get('latest_handshake', 'Never')
                
                self.stdout.write(f'  • {client_name}')
                self.stdout.write(f'    IP: {vpn_ip}')
                self.stdout.write(f'    Endpoint: {endpoint}')
                self.stdout.write(f'    Last handshake: {handshake}')

    def handle_add_client(self, options):
        """Add new VPN client"""
        client_name = options.get('client_name')
        role = options.get('role')
        
        if not client_name:
            raise CommandError('Client name is required (--client-name)')
        
        if not role:
            raise CommandError('Role is required (--role)')
        
        # Validate client name
        try:
            validate_vpn_client_name(client_name)
        except Exception as e:
            raise CommandError(f'Invalid client name: {str(e)}')
        
        self.stdout.write(f'Creating VPN client: {client_name} (role: {role})')
        
        try:
            # Run client generation script
            import subprocess
            script_path = os.path.join(settings.BASE_DIR, 'vpn_integration', 'wireguard', 'scripts', 'generate-client-config.sh')
            
            result = subprocess.run([
                'sudo', 'bash', script_path, client_name, role
            ], capture_output=True, text=True, check=True)
            
            self.stdout.write(self.style.SUCCESS(f'✓ Client {client_name} created successfully'))
            self.stdout.write(f'Config file: /etc/wireguard/clients/{client_name}.conf')
            
            # Show QR code path if it was generated
            qr_path = f'/etc/wireguard/clients/{client_name}.png'
            if os.path.exists(qr_path):
                self.stdout.write(f'QR Code: {qr_path}')
            
        except subprocess.CalledProcessError as e:
            raise CommandError(f'Failed to create client: {e.stderr}')
        except FileNotFoundError:
            raise CommandError('Client generation script not found. Please check VPN integration setup.')

    def handle_remove_client(self, options):
        """Remove VPN client"""
        client_name = options.get('client_name')
        
        if not client_name:
            raise CommandError('Client name is required (--client-name)')
        
        self.stdout.write(f'Removing VPN client: {client_name}')
        
        # Confirm removal
        if not options.get('verbosity') or options['verbosity'] > 0:
            confirm = input(f'Are you sure you want to remove client "{client_name}"? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled')
                return
        
        try:
            # Remove client configuration
            client_config = f'/etc/wireguard/clients/{client_name}.conf'
            client_qr = f'/etc/wireguard/clients/{client_name}.png'
            
            if os.path.exists(client_config):
                os.remove(client_config)
                self.stdout.write(f'Removed: {client_config}')
            
            if os.path.exists(client_qr):
                os.remove(client_qr)
                self.stdout.write(f'Removed: {client_qr}')
            
            # TODO: Remove from server configuration and restart WireGuard
            self.stdout.write(self.style.WARNING('Note: Server configuration update not implemented yet'))
            self.stdout.write('You may need to manually remove the peer from wg0.conf and restart WireGuard')
            
            self.stdout.write(self.style.SUCCESS(f'✓ Client {client_name} removed'))
            
        except Exception as e:
            raise CommandError(f'Failed to remove client: {str(e)}')

    def handle_backup(self):
        """Create VPN configuration backup"""
        self.stdout.write('Creating VPN configuration backup...')
        
        try:
            from core_integration.vpn_utils import backup_vpn_configuration
            backup_path = backup_vpn_configuration()
            
            if backup_path:
                self.stdout.write(self.style.SUCCESS(f'✓ Backup created: {backup_path}'))
            else:
                raise CommandError('Backup failed')
                
        except Exception as e:
            raise CommandError(f'Backup error: {str(e)}')

    def handle_monitor(self):
        """Start VPN monitoring"""
        self.stdout.write('Starting VPN monitoring service...')
        self.stdout.write('Press Ctrl+C to stop')
        
        try:
            monitoring_service = VPNMonitoringService()
            monitoring_service.start()
            
            # Keep the command running
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stdout.write('\nStopping VPN monitoring...')
                monitoring_service.stop()
                
        except Exception as e:
            raise CommandError(f'Monitoring error: {str(e)}')

    def handle_alerts(self, options):
        """Show VPN alerts"""
        hours = options.get('hours', 24)
        
        self.stdout.write(f'=== VPN Alerts (Last {hours} hours) ===')
        
        try:
            monitor = get_vpn_monitor()
            summary = monitor.get_alert_summary(hours)
            
            if options['output_format'] == 'json':
                self.stdout.write(json.dumps(summary, indent=2, default=str))
                return
            
            # Text output
            total = summary['total_alerts']
            critical = summary['critical']
            warning = summary['warning']
            info = summary['info']
            
            self.stdout.write(f'Total Alerts: {total}')
            if critical > 0:
                self.stdout.write(self.style.ERROR(f'Critical: {critical}'))
            if warning > 0:
                self.stdout.write(self.style.WARNING(f'Warning: {warning}'))
            if info > 0:
                self.stdout.write(f'Info: {info}')
            
            if summary['alert_types']:
                self.stdout.write('\nAlert Types:')
                for alert_type, count in summary['alert_types'].items():
                    self.stdout.write(f'  {alert_type}: {count}')
            
            if summary['recent_alerts']:
                self.stdout.write('\nRecent Alerts:')
                for alert in summary['recent_alerts']:
                    severity_style = self.style.ERROR if alert.severity == 'critical' else \
                                   self.style.WARNING if alert.severity == 'warning' else \
                                   self.style.SUCCESS
                    
                    timestamp = alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    self.stdout.write(f'  {timestamp} [{alert.severity.upper()}] {alert.message}')
            
            if total == 0:
                self.stdout.write(self.style.SUCCESS('No alerts in the specified time period'))
                
        except Exception as e:
            raise CommandError(f'Error retrieving alerts: {str(e)}')

    def handle_stats(self, options):
        """Show VPN statistics"""
        hours = options.get('hours', 24)
        
        self.stdout.write(f'=== VPN Statistics (Last {hours} hours) ===')
        
        try:
            monitor = get_vpn_monitor()
            stats = monitor.get_connection_stats(hours)
            
            if options['output_format'] == 'json':
                self.stdout.write(json.dumps(stats, indent=2, default=str))
                return
            
            # Text output
            self.stdout.write(f'Total Connections: {stats["total_connections"]}')
            self.stdout.write(f'Total Disconnections: {stats["total_disconnections"]}')
            self.stdout.write(f'Unique Clients: {stats["unique_clients"]}')
            
            avg_duration = stats["average_duration"]
            if avg_duration > 0:
                mins, secs = divmod(int(avg_duration), 60)
                self.stdout.write(f'Average Session Duration: {mins}m {secs}s')
            
            if stats['role_distribution']:
                self.stdout.write('\nConnections by Role:')
                for role, count in stats['role_distribution'].items():
                    self.stdout.write(f'  {role}: {count}')
            
            if stats['hourly_distribution']:
                self.stdout.write('\nConnections by Hour:')
                for hour in sorted(stats['hourly_distribution'].keys()):
                    count = stats['hourly_distribution'][hour]
                    self.stdout.write(f'  {hour:02d}:00: {count}')
                    
        except Exception as e:
            raise CommandError(f'Error retrieving statistics: {str(e)}')