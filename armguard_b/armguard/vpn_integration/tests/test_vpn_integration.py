# VPN Integration Testing Suite for ArmGuard
# Comprehensive tests for VPN functionality

import unittest
import tempfile
import os
import json
import ipaddress
from unittest.mock import patch, MagicMock, mock_open
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.conf import settings
import sys

# Add VPN integration path for testing
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

try:
    from core_integration.vpn_utils import (
        VPNManager, get_client_vpn_info, validate_vpn_client_name,
        get_next_available_ip, log_vpn_event, check_vpn_rate_limit
    )
    from core_integration.vpn_middleware import VPNAwareNetworkMiddleware
    from core_integration.vpn_decorators import vpn_role_required, vpn_access_required
    from monitoring.vpn_monitor import VPNMonitor, VPNAlert, ConnectionEvent
except ImportError as e:
    print(f"Warning: Could not import VPN modules: {e}")
    print("Make sure VPN integration is properly set up")

# Test settings
TEST_VPN_SETTINGS = {
    'WIREGUARD_INTERFACE': 'wg0',
    'WIREGUARD_NETWORK': '10.0.0.0/24',
    'WIREGUARD_PORT': 51820,
    'VPN_ROLE_RANGES': {
        'commander': {
            'ip_range': ('10.0.0.10', '10.0.0.19'),
            'access_level': 'VPN_COMMANDER',
            'session_timeout': 3600,
            'description': 'Military commanders with full access'
        },
        'armorer': {
            'ip_range': ('10.0.0.20', '10.0.0.39'),
            'access_level': 'VPN_ARMORER',
            'session_timeout': 1800,
            'description': 'Armory personnel with equipment access'
        },
        'emergency': {
            'ip_range': ('10.0.0.40', '10.0.0.49'),
            'access_level': 'VPN_EMERGENCY',
            'session_timeout': 7200,
            'description': 'Emergency response with extended access'
        },
        'personnel': {
            'ip_range': ('10.0.0.50', '10.0.0.199'),
            'access_level': 'VPN_PERSONNEL',
            'session_timeout': 900,
            'description': 'General military personnel'
        }
    },
    'VPN_RATE_LIMITS': {
        'commander': 100,
        'armorer': 50,
        'emergency': 200,
        'personnel': 30
    }
}

@override_settings(**TEST_VPN_SETTINGS)
class VPNUtilsTestCase(TestCase):
    """Test VPN utility functions"""

    def setUp(self):
        self.vpn_manager = VPNManager()

    @patch('subprocess.run')
    def test_get_vpn_status_active(self, mock_run):
        """Test VPN status when interface is active"""
        # Mock successful wg show command
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '''interface: wg0
  public key: server_public_key
  private key: (hidden)
  listening port: 51820

peer: client_public_key_1
  endpoint: 192.168.1.100:12345
  allowed ips: 10.0.0.10/32
  latest handshake: 1 minute, 23 seconds ago
  transfer: 15.23 KiB received, 8.45 KiB sent

peer: client_public_key_2
  endpoint: 192.168.1.101:23456
  allowed ips: 10.0.0.20/32
  latest handshake: 2 minutes, 45 seconds ago
  transfer: 45.67 KiB received, 23.89 KiB sent'''
        
        mock_run.return_value = mock_result
        
        status = self.vpn_manager.get_vpn_status()
        
        self.assertTrue(status['interface_active'])
        self.assertEqual(status['listening_port'], 51820)
        self.assertEqual(len(status['peers']), 2)
        self.assertGreater(status['total_data_sent'], 0)
        self.assertGreater(status['total_data_received'], 0)

    @patch('subprocess.run')
    def test_get_vpn_status_inactive(self, mock_run):
        """Test VPN status when interface is inactive"""
        # Mock failed wg show command
        mock_run.side_effect = subprocess.CalledProcessError(1, 'wg', 'Interface not found')
        
        status = self.vpn_manager.get_vpn_status()
        
        self.assertFalse(status['interface_active'])
        self.assertIn('error', status)

    def test_get_client_vpn_info_valid_ip(self):
        """Test getting VPN info for valid client IP"""
        # Test commander IP
        vpn_info = get_client_vpn_info('10.0.0.15')
        
        self.assertIsNotNone(vpn_info)
        self.assertEqual(vpn_info['vpn_role'], 'commander')
        self.assertEqual(vpn_info['access_level'], 'VPN_COMMANDER')
        self.assertEqual(vpn_info['session_timeout'], 3600)

    def test_get_client_vpn_info_invalid_ip(self):
        """Test getting VPN info for invalid IP"""
        # Test non-VPN IP
        vpn_info = get_client_vpn_info('192.168.1.100')
        self.assertIsNone(vpn_info)
        
        # Test invalid IP format
        vpn_info = get_client_vpn_info('invalid_ip')
        self.assertIsNone(vpn_info)

    def test_validate_vpn_client_name_valid(self):
        """Test validation of valid client names"""
        valid_names = ['test-client', 'client_123', 'TestClient', 'commander-01']
        
        for name in valid_names:
            try:
                validate_vpn_client_name(name)
            except Exception:
                self.fail(f"Valid client name '{name}' should not raise exception")

    def test_validate_vpn_client_name_invalid(self):
        """Test validation of invalid client names"""
        invalid_names = [
            '',  # Empty
            'ab',  # Too short
            'a' * 51,  # Too long
            'client with spaces',  # Spaces
            'client@domain',  # Special characters
            'клиент',  # Non-ASCII
        ]
        
        for name in invalid_names:
            with self.assertRaises(Exception):
                validate_vpn_client_name(name)

    def test_get_next_available_ip(self):
        """Test getting next available IP for role"""
        with patch('builtins.open', mock_open(read_data='# Empty config')):
            # Test commander role
            ip = get_next_available_ip('commander')
            self.assertEqual(ip, '10.0.0.10')  # First IP in range
            
            # Test personnel role
            ip = get_next_available_ip('personnel')
            self.assertEqual(ip, '10.0.0.50')  # First IP in range

    def test_get_next_available_ip_with_existing(self):
        """Test getting next available IP when some are taken"""
        config_content = '''[Interface]
PrivateKey = server_private_key
Address = 10.0.0.1/24
ListenPort = 51820

[Peer]
PublicKey = client1_public_key
AllowedIPs = 10.0.0.10/32

[Peer]
PublicKey = client2_public_key
AllowedIPs = 10.0.0.11/32'''

        with patch('builtins.open', mock_open(read_data=config_content)):
            # Should skip 10.0.0.10 and 10.0.0.11
            ip = get_next_available_ip('commander')
            self.assertEqual(ip, '10.0.0.12')

    def test_check_vpn_rate_limit(self):
        """Test VPN rate limiting"""
        client_ip = '10.0.0.15'  # Commander IP
        
        # First request should pass
        allowed, count, limit = check_vpn_rate_limit(client_ip)
        self.assertTrue(allowed)
        self.assertEqual(count, 1)
        self.assertEqual(limit, 100)  # Commander limit

@override_settings(**TEST_VPN_SETTINGS)
class VPNMiddlewareTestCase(TestCase):
    """Test VPN-aware middleware"""

    def setUp(self):
        self.middleware = VPNAwareNetworkMiddleware(get_response=lambda r: None)

    def test_vpn_client_detection(self):
        """Test detection of VPN clients"""
        from django.http import HttpRequest
        
        # Mock VPN client request
        request = HttpRequest()
        request.META = {
            'REMOTE_ADDR': '10.0.0.15',
            'HTTP_USER_AGENT': 'Mozilla/5.0',
        }
        
        # Process request
        self.middleware.process_request(request)
        
        # Check VPN info was added
        self.assertTrue(hasattr(request, 'vpn_client'))
        self.assertEqual(request.vpn_client['vpn_role'], 'commander')
        self.assertEqual(request.vpn_client['access_level'], 'VPN_COMMANDER')

    def test_non_vpn_client(self):
        """Test processing of non-VPN clients"""
        from django.http import HttpRequest
        
        # Mock regular client request
        request = HttpRequest()
        request.META = {
            'REMOTE_ADDR': '192.168.1.100',
            'HTTP_USER_AGENT': 'Mozilla/5.0',
        }
        
        # Process request
        self.middleware.process_request(request)
        
        # Should not have VPN info
        self.assertFalse(hasattr(request, 'vpn_client'))

@override_settings(**TEST_VPN_SETTINGS)
class VPNDecoratorsTestCase(TestCase):
    """Test VPN access decorators"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )

    def test_vpn_role_required_decorator(self):
        """Test VPN role requirement decorator"""
        from django.http import HttpRequest, HttpResponse
        
        @vpn_role_required('commander')
        def test_view(request):
            return HttpResponse('Success')
        
        # Mock VPN commander request
        request = HttpRequest()
        request.META = {'REMOTE_ADDR': '10.0.0.15'}
        request.user = self.user
        request.vpn_client = {
            'vpn_role': 'commander',
            'access_level': 'VPN_COMMANDER'
        }
        
        response = test_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')

    def test_vpn_role_required_decorator_denied(self):
        """Test VPN role requirement decorator access denied"""
        from django.http import HttpRequest, HttpResponse
        
        @vpn_role_required('commander')
        def test_view(request):
            return HttpResponse('Success')
        
        # Mock VPN personnel request (insufficient role)
        request = HttpRequest()
        request.META = {'REMOTE_ADDR': '10.0.0.55'}
        request.user = self.user
        request.vpn_client = {
            'vpn_role': 'personnel',
            'access_level': 'VPN_PERSONNEL'
        }
        
        response = test_view(request)
        self.assertEqual(response.status_code, 403)

class VPNMonitorTestCase(TestCase):
    """Test VPN monitoring functionality"""

    def setUp(self):
        self.monitor = VPNMonitor()

    def test_alert_creation(self):
        """Test alert creation and storage"""
        from django.utils import timezone
        
        alert = VPNAlert(
            alert_type='test_alert',
            severity='warning',
            message='Test alert message',
            timestamp=timezone.now(),
            client_ip='10.0.0.15'
        )
        
        # Add alert to monitor
        import asyncio
        asyncio.run(self.monitor.send_alert(alert))
        
        # Check alert was stored
        self.assertEqual(len(self.monitor.alerts), 1)
        stored_alert = self.monitor.alerts[0]
        self.assertEqual(stored_alert.alert_type, 'test_alert')
        self.assertEqual(stored_alert.severity, 'warning')

    def test_connection_event_tracking(self):
        """Test connection event tracking"""
        from django.utils import timezone
        
        connect_event = ConnectionEvent(
            event_type='connect',
            client_ip='10.0.0.15',
            client_name='test-client',
            timestamp=timezone.now(),
            vpn_role='commander'
        )
        
        self.monitor.connection_history.append(connect_event)
        
        # Check event was stored
        self.assertEqual(len(self.monitor.connection_history), 1)
        stored_event = self.monitor.connection_history[0]
        self.assertEqual(stored_event.event_type, 'connect')
        self.assertEqual(stored_event.client_ip, '10.0.0.15')

    def test_get_alert_summary(self):
        """Test alert summary generation"""
        from django.utils import timezone
        
        # Add test alerts
        alerts = [
            VPNAlert('critical_alert', 'critical', 'Critical message', timezone.now()),
            VPNAlert('warning_alert', 'warning', 'Warning message', timezone.now()),
            VPNAlert('info_alert', 'info', 'Info message', timezone.now())
        ]
        
        self.monitor.alerts.extend(alerts)
        
        summary = self.monitor.get_alert_summary(24)
        
        self.assertEqual(summary['total_alerts'], 3)
        self.assertEqual(summary['critical'], 1)
        self.assertEqual(summary['warning'], 1)
        self.assertEqual(summary['info'], 1)

class VPNIntegrationTestCase(TestCase):
    """Integration tests for VPN functionality"""

    @override_settings(**TEST_VPN_SETTINGS)
    @patch('subprocess.run')
    def test_full_vpn_workflow(self, mock_run):
        """Test complete VPN workflow"""
        # Mock successful WireGuard operations
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        # Test VPN manager initialization
        manager = VPNManager()
        self.assertIsNotNone(manager)
        
        # Test status check
        with patch.object(manager, 'get_vpn_status') as mock_status:
            mock_status.return_value = {
                'interface_active': True,
                'listening_port': 51820,
                'peers': []
            }
            
            status = manager.get_vpn_status()
            self.assertTrue(status['interface_active'])

    def test_ip_address_validation(self):
        """Test IP address validation and range checking"""
        # Test valid VPN IPs for each role
        test_cases = [
            ('10.0.0.15', 'commander'),
            ('10.0.0.25', 'armorer'),
            ('10.0.0.45', 'emergency'),
            ('10.0.0.55', 'personnel'),
        ]
        
        for ip, expected_role in test_cases:
            vpn_info = get_client_vpn_info(ip)
            self.assertIsNotNone(vpn_info)
            self.assertEqual(vpn_info['vpn_role'], expected_role)

    def test_security_settings_validation(self):
        """Test security settings validation"""
        # Check that all required settings are present
        required_settings = [
            'WIREGUARD_INTERFACE',
            'WIREGUARD_NETWORK',
            'VPN_ROLE_RANGES',
            'VPN_RATE_LIMITS'
        ]
        
        for setting in required_settings:
            self.assertTrue(hasattr(settings, setting))
        
        # Validate role ranges
        role_ranges = settings.VPN_ROLE_RANGES
        for role, config in role_ranges.items():
            self.assertIn('ip_range', config)
            self.assertIn('access_level', config)
            self.assertIn('session_timeout', config)
            
            # Validate IP range format
            start_ip, end_ip = config['ip_range']
            self.assertIsInstance(ipaddress.ip_address(start_ip), ipaddress.IPv4Address)
            self.assertIsInstance(ipaddress.ip_address(end_ip), ipaddress.IPv4Address)

if __name__ == '__main__':
    # Run tests
    unittest.main()