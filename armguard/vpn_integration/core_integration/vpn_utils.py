# VPN Utility Functions for ArmGuard
# Helper functions for VPN integration and management

import ipaddress
import subprocess
import json
import re
import time
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

logger = logging.getLogger('armguard.vpn')

class VPNManager:
    """Main VPN management class"""
    
    def __init__(self):
        self.interface = getattr(settings, 'WIREGUARD_INTERFACE', 'wg0')
        self.config_path = f'/etc/wireguard/{self.interface}.conf'
        self.clients_path = '/etc/wireguard/clients'
        
    def get_vpn_status(self):
        """Get current VPN server status"""
        try:
            result = subprocess.run(['wg', 'show', self.interface], 
                                  capture_output=True, text=True, check=True)
            
            status = {
                'interface_active': True,
                'listening_port': None,
                'peers': [],
                'total_data_sent': 0,
                'total_data_received': 0
            }
            
            lines = result.stdout.strip().split('\n')
            current_peer = None
            
            for line in lines:
                line = line.strip()
                
                if line.startswith('listening port:'):
                    status['listening_port'] = int(line.split(':')[1].strip())
                
                elif line.startswith('peer:'):
                    if current_peer:
                        status['peers'].append(current_peer)
                    current_peer = {
                        'public_key': line.split(':')[1].strip(),
                        'endpoint': None,
                        'allowed_ips': [],
                        'latest_handshake': None,
                        'transfer_rx': 0,
                        'transfer_tx': 0,
                        'persistent_keepalive': None
                    }
                
                elif current_peer:
                    if line.startswith('endpoint:'):
                        current_peer['endpoint'] = line.split(':', 1)[1].strip()
                    elif line.startswith('allowed ips:'):
                        ips = line.split(':', 1)[1].strip()
                        current_peer['allowed_ips'] = [ip.strip() for ip in ips.split(',')]
                    elif line.startswith('latest handshake:'):
                        handshake = line.split(':', 1)[1].strip()
                        current_peer['latest_handshake'] = handshake
                    elif line.startswith('transfer:'):
                        transfer = line.split(':', 1)[1].strip()
                        # Parse "X.XX KiB received, Y.YY KiB sent"
                        parts = transfer.split(',')
                        if len(parts) == 2:
                            rx_part = parts[0].strip().split()
                            tx_part = parts[1].strip().split()
                            if len(rx_part) >= 2 and len(tx_part) >= 2:
                                current_peer['transfer_rx'] = self._parse_data_size(rx_part[0], rx_part[1])
                                current_peer['transfer_tx'] = self._parse_data_size(tx_part[0], tx_part[1])
                                status['total_data_received'] += current_peer['transfer_rx']
                                status['total_data_sent'] += current_peer['transfer_tx']
                    elif line.startswith('persistent keepalive:'):
                        keepalive = line.split(':', 1)[1].strip()
                        if keepalive != 'off':
                            current_peer['persistent_keepalive'] = keepalive
            
            if current_peer:
                status['peers'].append(current_peer)
                
            return status
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get VPN status: {e}")
            return {
                'interface_active': False,
                'error': str(e)
            }
    
    def _parse_data_size(self, value, unit):
        """Parse data size with unit to bytes"""
        try:
            value = float(value)
            unit = unit.lower()
            
            multipliers = {
                'b': 1,
                'kib': 1024,
                'mib': 1024**2,
                'gib': 1024**3,
                'kb': 1000,
                'mb': 1000**2,
                'gb': 1000**3
            }
            
            return int(value * multipliers.get(unit, 1))
        except (ValueError, KeyError):
            return 0
    
    def get_connected_peers(self):
        """Get list of currently connected peers"""
        status = self.get_vpn_status()
        if not status.get('interface_active'):
            return []
        
        connected_peers = []
        
        for peer in status.get('peers', []):
            # Consider peer connected if handshake within last 3 minutes
            if peer.get('latest_handshake'):
                try:
                    # Parse handshake time
                    if 'minute' in peer['latest_handshake'] or 'second' in peer['latest_handshake']:
                        # Recently active
                        peer_info = self._get_peer_info(peer['public_key'])
                        if peer_info:
                            connected_peers.append({
                                **peer,
                                **peer_info
                            })
                except:
                    pass
        
        return connected_peers
    
    def _get_peer_info(self, public_key):
        """Get peer information from configuration"""
        try:
            with open(self.config_path, 'r') as f:
                config = f.read()
            
            # Find peer block with this public key
            peer_pattern = r'\[Peer\].*?PublicKey\s*=\s*' + re.escape(public_key) + r'.*?(?=\[|\Z)'
            peer_match = re.search(peer_pattern, config, re.DOTALL | re.IGNORECASE)
            
            if peer_match:
                peer_block = peer_match.group(0)
                
                info = {}
                
                # Extract client name from comment
                name_match = re.search(r'#\s*Client:\s*(.+)', peer_block)
                if name_match:
                    info['client_name'] = name_match.group(1).strip()
                
                # Extract role
                role_match = re.search(r'#\s*Role:\s*(\w+)', peer_block)
                if role_match:
                    info['role'] = role_match.group(1).strip()
                
                # Extract IP
                ip_match = re.search(r'AllowedIPs\s*=\s*([0-9.]+)/32', peer_block)
                if ip_match:
                    info['vpn_ip'] = ip_match.group(1)
                    info['vpn_role'] = self._determine_role_from_ip(info['vpn_ip'])
                
                return info
                
        except Exception as e:
            logger.error(f"Error getting peer info: {e}")
        
        return None
    
    def _determine_role_from_ip(self, ip):
        """Determine VPN role from IP address"""
        try:
            addr = ipaddress.ip_address(ip)
            
            for role, (start_ip, end_ip) in settings.VPN_ROLE_RANGES.items():
                start_addr = ipaddress.ip_address(start_ip)
                end_addr = ipaddress.ip_address(end_ip)
                
                if start_addr <= addr <= end_addr:
                    return role
        except:
            pass
        
        return 'unknown'

def get_client_vpn_info(client_ip):
    """Get VPN information for a client IP"""
    try:
        addr = ipaddress.ip_address(client_ip)
        vpn_network = ipaddress.ip_network(getattr(settings, 'WIREGUARD_NETWORK', '10.0.0.0/24'))
        
        if addr not in vpn_network:
            return None
        
        # Determine role from IP range
        role_ranges = getattr(settings, 'VPN_ROLE_RANGES', {})
        for role, config in role_ranges.items():
            start_ip, end_ip = config['ip_range']
            start_addr = ipaddress.ip_address(start_ip)
            end_addr = ipaddress.ip_address(end_ip)
            
            if start_addr <= addr <= end_addr:
                return {
                    'vpn_ip': client_ip,
                    'vpn_role': role,
                    'access_level': config['access_level'],
                    'session_timeout': config['session_timeout'],
                    'description': config['description']
                }
        
        return {
            'vpn_ip': client_ip,
            'vpn_role': 'unknown',
            'access_level': 'VPN_UNKNOWN',
            'session_timeout': 900,
            'description': 'Unknown VPN role'
        }
        
    except (ValueError, ipaddress.AddressValueError):
        return None

def validate_vpn_client_name(client_name):
    """Validate VPN client name"""
    if not client_name:
        raise ValidationError("Client name cannot be empty")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', client_name):
        raise ValidationError("Client name can only contain letters, numbers, hyphens, and underscores")
    
    if len(client_name) < 3 or len(client_name) > 50:
        raise ValidationError("Client name must be between 3 and 50 characters")
    
    # Check if client already exists
    clients_path = '/etc/wireguard/clients'
    client_config = f'{clients_path}/{client_name}.conf'
    
    if os.path.exists(client_config):
        raise ValidationError(f"Client '{client_name}' already exists")

def get_next_available_ip(role):
    """Get next available IP address for a role"""
    role_ranges = getattr(settings, 'VPN_ROLE_RANGES', {})
    
    if role not in role_ranges:
        raise ValidationError(f"Invalid role: {role}")
    
    start_ip, end_ip = role_ranges[role]['ip_range']
    start_addr = ipaddress.ip_address(start_ip)
    end_addr = ipaddress.ip_address(end_ip)
    
    # Read current configuration to see which IPs are taken
    config_path = '/etc/wireguard/wg0.conf'
    taken_ips = set()
    
    try:
        with open(config_path, 'r') as f:
            config = f.read()
        
        # Find all AllowedIPs entries
        ip_matches = re.findall(r'AllowedIPs\s*=\s*([0-9.]+)/32', config)
        taken_ips = set(ip_matches)
        
    except Exception as e:
        logger.error(f"Error reading VPN config: {e}")
    
    # Find next available IP in range
    current_addr = start_addr
    while current_addr <= end_addr:
        ip_str = str(current_addr)
        if ip_str not in taken_ips:
            return ip_str
        current_addr += 1
    
    raise ValidationError(f"No available IP addresses in range for role: {role}")

def log_vpn_event(event_type, client_ip, user=None, details=None):
    """Log VPN events for audit purposes"""
    vpn_info = get_client_vpn_info(client_ip) if client_ip else None
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'client_ip': client_ip,
        'vpn_role': vpn_info.get('vpn_role') if vpn_info else None,
        'user': user.username if user else None,
        'details': details or {}
    }
    
    logger.info(f"VPN Event: {json.dumps(log_entry)}")

def check_vpn_rate_limit(client_ip, role=None):
    """Check if client has exceeded VPN rate limit"""
    if not role:
        vpn_info = get_client_vpn_info(client_ip)
        role = vpn_info.get('vpn_role') if vpn_info else 'personnel'
    
    rate_limits = getattr(settings, 'VPN_RATE_LIMITS', {})
    limit = rate_limits.get(role, 30)  # Default to 30 requests/minute
    
    # Simple in-memory rate limiting (consider Redis for production)
    from collections import defaultdict
    import time
    
    if not hasattr(check_vpn_rate_limit, 'request_times'):
        check_vpn_rate_limit.request_times = defaultdict(list)
    
    current_time = time.time()
    minute_ago = current_time - 60
    
    # Clean old requests
    check_vpn_rate_limit.request_times[client_ip] = [
        t for t in check_vpn_rate_limit.request_times[client_ip] if t > minute_ago
    ]
    
    # Check if over limit
    current_count = len(check_vpn_rate_limit.request_times[client_ip])
    if current_count >= limit:
        return False, current_count, limit
    
    # Record this request
    check_vpn_rate_limit.request_times[client_ip].append(current_time)
    return True, current_count + 1, limit

def generate_vpn_qr_code(client_config_path):
    """Generate QR code for mobile VPN client setup"""
    try:
        import qrcode
        from io import BytesIO
        import base64
        
        with open(client_config_path, 'r') as f:
            config_content = f.read()
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(config_content)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for web display
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return qr_code_base64
        
    except ImportError:
        logger.error("qrcode package not installed. Install with: pip install qrcode[pil]")
        return None
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        return None

def get_vpn_health_status():
    """Get comprehensive VPN health status"""
    manager = VPNManager()
    status = manager.get_vpn_status()
    
    health = {
        'overall_status': 'healthy',
        'interface_active': status.get('interface_active', False),
        'listening_port': status.get('listening_port'),
        'connected_peers': len(status.get('peers', [])),
        'total_data_transfer': status.get('total_data_sent', 0) + status.get('total_data_received', 0),
        'warnings': [],
        'errors': []
    }
    
    # Check for issues
    if not health['interface_active']:
        health['overall_status'] = 'critical'
        health['errors'].append('VPN interface is not active')
    
    if health['connected_peers'] == 0:
        health['warnings'].append('No peers currently connected')
    
    # Check system resources
    try:
        import psutil
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            health['warnings'].append(f'High CPU usage: {cpu_percent}%')
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            health['warnings'].append(f'High memory usage: {memory.percent}%')
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            health['warnings'].append(f'High disk usage: {disk.percent}%')
            
    except ImportError:
        health['warnings'].append('psutil not available for system monitoring')
    
    # Determine overall status
    if health['errors']:
        health['overall_status'] = 'critical'
    elif health['warnings']:
        health['overall_status'] = 'warning'
    
    return health

def backup_vpn_configuration():
    """Create backup of VPN configuration"""
    import shutil
    import os
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = f'/etc/wireguard/backups/backup_{timestamp}'
    
    try:
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup main configuration
        shutil.copy2('/etc/wireguard/wg0.conf', f'{backup_dir}/wg0.conf')
        
        # Backup client configurations
        clients_dir = '/etc/wireguard/clients'
        if os.path.exists(clients_dir):
            shutil.copytree(clients_dir, f'{backup_dir}/clients')
        
        # Backup keys
        keys_dir = '/etc/wireguard/keys'
        if os.path.exists(keys_dir):
            shutil.copytree(keys_dir, f'{backup_dir}/keys')
        
        logger.info(f"VPN configuration backed up to: {backup_dir}")
        return backup_dir
        
    except Exception as e:
        logger.error(f"Error creating VPN backup: {e}")
        return None

# Import required modules at runtime to avoid circular imports
import os
import time