# VPN Monitoring Service for ArmGuard
# Real-time monitoring and alerting for VPN connections

import asyncio
import logging
import json
import time
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.models import User
from django.utils import timezone

# Import VPN utilities
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from core_integration.vpn_utils import VPNManager, get_vpn_health_status

logger = logging.getLogger('armguard.vpn.monitor')

@dataclass
class VPNAlert:
    """VPN alert data structure"""
    alert_type: str
    severity: str  # critical, warning, info
    message: str
    timestamp: datetime
    client_ip: Optional[str] = None
    client_name: Optional[str] = None
    details: Optional[Dict] = None

@dataclass
class ConnectionEvent:
    """Connection event data structure"""
    event_type: str  # connect, disconnect, failed_auth
    client_ip: str
    client_name: str
    timestamp: datetime
    vpn_role: str
    duration: Optional[int] = None  # seconds

class VPNMonitor:
    """Main VPN monitoring class"""
    
    def __init__(self):
        self.vpn_manager = VPNManager()
        self.alerts = []
        self.connection_history = []
        self.last_status = None
        self.monitoring = False
        
        # Alert thresholds
        self.max_failed_attempts = getattr(settings, 'VPN_MAX_FAILED_ATTEMPTS', 5)
        self.connection_timeout = getattr(settings, 'VPN_CONNECTION_TIMEOUT', 300)  # 5 minutes
        self.max_concurrent_connections = getattr(settings, 'VPN_MAX_CONCURRENT_CONNECTIONS', 50)
        
        # Email alert settings
        self.enable_email_alerts = getattr(settings, 'VPN_EMAIL_ALERTS_ENABLED', False)
        self.alert_emails = getattr(settings, 'VPN_ALERT_EMAILS', [])
        
    async def start_monitoring(self, interval=30):
        """Start continuous VPN monitoring"""
        logger.info("Starting VPN monitoring service...")
        self.monitoring = True
        
        try:
            while self.monitoring:
                await self.check_vpn_status()
                await self.check_connection_events()
                await self.check_security_threats()
                await self.cleanup_old_alerts()
                
                await asyncio.sleep(interval)
                
        except Exception as e:
            logger.error(f"VPN monitoring error: {e}")
            await self.send_alert(VPNAlert(
                alert_type='monitoring_error',
                severity='critical',
                message=f'VPN monitoring service error: {str(e)}',
                timestamp=timezone.now()
            ))
        
        logger.info("VPN monitoring service stopped")
    
    def stop_monitoring(self):
        """Stop VPN monitoring"""
        self.monitoring = False
        logger.info("Stopping VPN monitoring service...")
    
    async def check_vpn_status(self):
        """Check overall VPN status and generate alerts"""
        try:
            current_status = self.vpn_manager.get_vpn_status()
            health_status = get_vpn_health_status()
            
            # Check if VPN interface went down
            if self.last_status and self.last_status.get('interface_active'):
                if not current_status.get('interface_active'):
                    await self.send_alert(VPNAlert(
                        alert_type='interface_down',
                        severity='critical',
                        message='VPN interface has gone offline',
                        timestamp=timezone.now(),
                        details=current_status
                    ))
            
            # Check for interface recovery
            elif self.last_status and not self.last_status.get('interface_active'):
                if current_status.get('interface_active'):
                    await self.send_alert(VPNAlert(
                        alert_type='interface_recovery',
                        severity='info',
                        message='VPN interface has recovered and is online',
                        timestamp=timezone.now()
                    ))
            
            # Check peer count limits
            peer_count = len(current_status.get('peers', []))
            if peer_count >= self.max_concurrent_connections:
                await self.send_alert(VPNAlert(
                    alert_type='max_connections',
                    severity='warning',
                    message=f'Maximum concurrent connections reached: {peer_count}',
                    timestamp=timezone.now(),
                    details={'peer_count': peer_count}
                ))
            
            # Check health status warnings and errors
            if health_status['errors']:
                for error in health_status['errors']:
                    await self.send_alert(VPNAlert(
                        alert_type='health_error',
                        severity='critical',
                        message=f'VPN Health Error: {error}',
                        timestamp=timezone.now()
                    ))
            
            if health_status['warnings']:
                for warning in health_status['warnings']:
                    await self.send_alert(VPNAlert(
                        alert_type='health_warning',
                        severity='warning',
                        message=f'VPN Health Warning: {warning}',
                        timestamp=timezone.now()
                    ))
            
            self.last_status = current_status
            
        except Exception as e:
            logger.error(f"Error checking VPN status: {e}")
    
    async def check_connection_events(self):
        """Monitor connection events and detect anomalies"""
        try:
            connected_peers = self.vpn_manager.get_connected_peers()
            current_time = timezone.now()
            
            # Track new connections
            current_ips = set()
            for peer in connected_peers:
                client_ip = peer.get('vpn_ip')
                if client_ip:
                    current_ips.add(client_ip)
                    
                    # Check if this is a new connection
                    if not self._is_known_connection(client_ip):
                        event = ConnectionEvent(
                            event_type='connect',
                            client_ip=client_ip,
                            client_name=peer.get('client_name', 'Unknown'),
                            timestamp=current_time,
                            vpn_role=peer.get('vpn_role', 'unknown')
                        )
                        
                        self.connection_history.append(event)
                        
                        # Send connection alert
                        await self.send_alert(VPNAlert(
                            alert_type='new_connection',
                            severity='info',
                            message=f'New VPN connection: {peer.get("client_name", "Unknown")}',
                            timestamp=current_time,
                            client_ip=client_ip,
                            client_name=peer.get('client_name'),
                            details=peer
                        ))
            
            # Track disconnections
            for event in reversed(self.connection_history[-50:]):  # Check recent connections
                if (event.event_type == 'connect' and 
                    event.client_ip not in current_ips and
                    not self._has_disconnect_event(event.client_ip, event.timestamp)):
                    
                    # Calculate connection duration
                    duration = int((current_time - event.timestamp).total_seconds())
                    
                    disconnect_event = ConnectionEvent(
                        event_type='disconnect',
                        client_ip=event.client_ip,
                        client_name=event.client_name,
                        timestamp=current_time,
                        vpn_role=event.vpn_role,
                        duration=duration
                    )
                    
                    self.connection_history.append(disconnect_event)
                    
                    # Send disconnect alert for short connections (potential issues)
                    if duration < 60:  # Less than 1 minute
                        await self.send_alert(VPNAlert(
                            alert_type='short_connection',
                            severity='warning',
                            message=f'Very short VPN connection: {event.client_name} ({duration}s)',
                            timestamp=current_time,
                            client_ip=event.client_ip,
                            client_name=event.client_name,
                            details={'duration': duration}
                        ))
            
        except Exception as e:
            logger.error(f"Error checking connection events: {e}")
    
    async def check_security_threats(self):
        """Check for potential security threats"""
        try:
            current_time = timezone.now()
            
            # Check for multiple failed connections from same IP
            failed_attempts = self._count_failed_attempts()
            for client_ip, count in failed_attempts.items():
                if count >= self.max_failed_attempts:
                    await self.send_alert(VPNAlert(
                        alert_type='brute_force_attempt',
                        severity='critical',
                        message=f'Multiple failed VPN attempts from {client_ip}: {count} attempts',
                        timestamp=current_time,
                        client_ip=client_ip,
                        details={'attempt_count': count}
                    ))
            
            # Check for suspicious connection patterns
            await self._check_connection_patterns()
            
            # Check for unauthorized role access attempts
            await self._check_unauthorized_access()
            
        except Exception as e:
            logger.error(f"Error checking security threats: {e}")
    
    async def _check_connection_patterns(self):
        """Check for suspicious connection patterns"""
        current_time = timezone.now()
        hour_ago = current_time - timedelta(hours=1)
        
        # Get recent connections
        recent_connections = [
            event for event in self.connection_history
            if event.timestamp >= hour_ago and event.event_type == 'connect'
        ]
        
        # Check for rapid connections from same client
        client_connections = {}
        for event in recent_connections:
            client_key = f"{event.client_ip}_{event.client_name}"
            if client_key not in client_connections:
                client_connections[client_key] = []
            client_connections[client_key].append(event)
        
        for client_key, connections in client_connections.items():
            if len(connections) > 10:  # More than 10 connections in an hour
                client_ip = connections[0].client_ip
                client_name = connections[0].client_name
                
                await self.send_alert(VPNAlert(
                    alert_type='excessive_connections',
                    severity='warning',
                    message=f'Excessive VPN connections from {client_name}: {len(connections)} in 1 hour',
                    timestamp=current_time,
                    client_ip=client_ip,
                    client_name=client_name,
                    details={'connection_count': len(connections)}
                ))
    
    async def _check_unauthorized_access(self):
        """Check for unauthorized role access attempts"""
        # This would integrate with ArmGuard's access logs
        # For now, we'll check VPN role vs attempted access patterns
        
        try:
            connected_peers = self.vpn_manager.get_connected_peers()
            
            for peer in connected_peers:
                client_ip = peer.get('vpn_ip')
                vpn_role = peer.get('vpn_role', 'unknown')
                
                if vpn_role == 'unknown':
                    await self.send_alert(VPNAlert(
                        alert_type='unknown_role',
                        severity='warning',
                        message=f'Client with unknown VPN role connected: {peer.get("client_name")}',
                        timestamp=timezone.now(),
                        client_ip=client_ip,
                        client_name=peer.get('client_name'),
                        details=peer
                    ))
        
        except Exception as e:
            logger.error(f"Error checking unauthorized access: {e}")
    
    def _is_known_connection(self, client_ip):
        """Check if client IP has an active connection event"""
        for event in reversed(self.connection_history[-20:]):
            if (event.client_ip == client_ip and 
                event.event_type == 'connect' and
                not self._has_disconnect_event(client_ip, event.timestamp)):
                return True
        return False
    
    def _has_disconnect_event(self, client_ip, connect_timestamp):
        """Check if there's a disconnect event after the connect timestamp"""
        for event in reversed(self.connection_history):
            if (event.client_ip == client_ip and 
                event.event_type == 'disconnect' and
                event.timestamp >= connect_timestamp):
                return True
        return False
    
    def _count_failed_attempts(self):
        """Count failed connection attempts by IP"""
        # This would integrate with system logs or VPN logs
        # For now, return empty dict - implement based on log analysis
        return {}
    
    async def send_alert(self, alert: VPNAlert):
        """Send alert via configured channels"""
        try:
            # Add to alert history
            self.alerts.append(alert)
            
            # Log the alert
            logger.warning(f"VPN Alert [{alert.severity.upper()}]: {alert.message}")
            
            # Send email alerts if configured
            if self.enable_email_alerts and self.alert_emails:
                await self._send_email_alert(alert)
            
            # Could add other alert channels here (Slack, Discord, etc.)
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    async def _send_email_alert(self, alert: VPNAlert):
        """Send email alert"""
        try:
            subject = f"ArmGuard VPN Alert [{alert.severity.upper()}]: {alert.alert_type}"
            
            message_lines = [
                f"VPN Alert Details:",
                f"Type: {alert.alert_type}",
                f"Severity: {alert.severity}",
                f"Message: {alert.message}",
                f"Timestamp: {alert.timestamp}",
            ]
            
            if alert.client_ip:
                message_lines.append(f"Client IP: {alert.client_ip}")
            
            if alert.client_name:
                message_lines.append(f"Client Name: {alert.client_name}")
            
            if alert.details:
                message_lines.append(f"Details: {json.dumps(alert.details, indent=2)}")
            
            message = "\n".join(message_lines)
            
            # Send email using Django's email backend
            send_mail(
                subject=subject,
                message=message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'armguard@localhost'),
                recipient_list=self.alert_emails,
                fail_silently=False
            )
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    async def cleanup_old_alerts(self):
        """Clean up old alerts to prevent memory issues"""
        cutoff_time = timezone.now() - timedelta(days=7)
        
        # Keep only recent alerts
        self.alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time
        ]
        
        # Keep only recent connection history
        self.connection_history = [
            event for event in self.connection_history
            if event.timestamp >= cutoff_time
        ]
    
    def get_alert_summary(self, hours=24):
        """Get alert summary for specified time period"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        recent_alerts = [
            alert for alert in self.alerts
            if alert.timestamp >= cutoff_time
        ]
        
        summary = {
            'total_alerts': len(recent_alerts),
            'critical': len([a for a in recent_alerts if a.severity == 'critical']),
            'warning': len([a for a in recent_alerts if a.severity == 'warning']),
            'info': len([a for a in recent_alerts if a.severity == 'info']),
            'alert_types': {},
            'recent_alerts': recent_alerts[-10:]  # Last 10 alerts
        }
        
        for alert in recent_alerts:
            alert_type = alert.alert_type
            if alert_type not in summary['alert_types']:
                summary['alert_types'][alert_type] = 0
            summary['alert_types'][alert_type] += 1
        
        return summary
    
    def get_connection_stats(self, hours=24):
        """Get connection statistics"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        recent_events = [
            event for event in self.connection_history
            if event.timestamp >= cutoff_time
        ]
        
        connects = [e for e in recent_events if e.event_type == 'connect']
        disconnects = [e for e in recent_events if e.event_type == 'disconnect']
        
        stats = {
            'total_connections': len(connects),
            'total_disconnections': len(disconnects),
            'unique_clients': len(set(e.client_ip for e in connects)),
            'average_duration': 0,
            'role_distribution': {},
            'hourly_distribution': {}
        }
        
        # Calculate average duration
        if disconnects:
            durations = [e.duration for e in disconnects if e.duration]
            if durations:
                stats['average_duration'] = sum(durations) / len(durations)
        
        # Role distribution
        for event in connects:
            role = event.vpn_role
            if role not in stats['role_distribution']:
                stats['role_distribution'][role] = 0
            stats['role_distribution'][role] += 1
        
        # Hourly distribution
        for event in connects:
            hour = event.timestamp.hour
            if hour not in stats['hourly_distribution']:
                stats['hourly_distribution'][hour] = 0
            stats['hourly_distribution'][hour] += 1
        
        return stats

# Global monitor instance
vpn_monitor = None

def get_vpn_monitor():
    """Get global VPN monitor instance"""
    global vpn_monitor
    if vpn_monitor is None:
        vpn_monitor = VPNMonitor()
    return vpn_monitor

async def start_vpn_monitoring():
    """Start VPN monitoring service"""
    monitor = get_vpn_monitor()
    await monitor.start_monitoring()

def stop_vpn_monitoring():
    """Stop VPN monitoring service"""
    monitor = get_vpn_monitor()
    monitor.stop_monitoring()

# Background task runner for Django
class VPNMonitoringService:
    """Service class for running VPN monitoring as background task"""
    
    def __init__(self):
        self.task = None
        self.loop = None
    
    def start(self):
        """Start monitoring in background"""
        try:
            import asyncio
            
            # Get or create event loop
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
            
            # Start monitoring task
            self.task = self.loop.create_task(start_vpn_monitoring())
            logger.info("VPN monitoring service started")
            
        except Exception as e:
            logger.error(f"Error starting VPN monitoring service: {e}")
    
    def stop(self):
        """Stop monitoring"""
        try:
            if self.task:
                self.task.cancel()
            
            stop_vpn_monitoring()
            logger.info("VPN monitoring service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping VPN monitoring service: {e}")

# Django management command helper
def run_monitoring_command():
    """Run monitoring as Django management command"""
    try:
        import asyncio
        asyncio.run(start_vpn_monitoring())
    except KeyboardInterrupt:
        logger.info("VPN monitoring stopped by user")
    except Exception as e:
        logger.error(f"VPN monitoring error: {e}")