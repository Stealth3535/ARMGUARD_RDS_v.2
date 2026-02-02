# VPN Integration Settings for ArmGuard
# Add these settings to your core/settings.py file or import them

from decouple import config

# =============================================================================
# WIREGUARD VPN INTEGRATION SETTINGS
# =============================================================================

# Enable/disable VPN integration
WIREGUARD_ENABLED = config('WIREGUARD_ENABLED', default=True, cast=bool)

# VPN network configuration
WIREGUARD_NETWORK = config('WIREGUARD_NETWORK', default='10.0.0.0/24')
WIREGUARD_SERVER_IP = config('WIREGUARD_SERVER_IP', default='10.0.0.1')
WIREGUARD_INTERFACE = config('WIREGUARD_INTERFACE', default='wg0')
WIREGUARD_PORT = config('WIREGUARD_PORT', default=51820, cast=int)

# =============================================================================
# VPN ROLE-BASED ACCESS CONTROL
# =============================================================================

# VPN user roles and their IP ranges
VPN_ROLE_RANGES = {
    'commander': {
        'ip_range': ('10.0.0.10', '10.0.0.19'),
        'access_level': 'VPN_LAN',
        'session_timeout': 7200,  # 2 hours
        'description': 'Field Commander - Full LAN access for emergency operations'
    },
    'armorer': {
        'ip_range': ('10.0.0.20', '10.0.0.29'),
        'access_level': 'VPN_LAN',
        'session_timeout': 3600,  # 1 hour
        'description': 'Armorer - Complete armorer functions for off-site management'
    },
    'emergency': {
        'ip_range': ('10.0.0.30', '10.0.0.39'),
        'access_level': 'VPN_LAN_LIMITED',
        'session_timeout': 1800,  # 30 minutes
        'description': 'Emergency Operations - Limited LAN access for crisis response'
    },
    'personnel': {
        'ip_range': ('10.0.0.40', '10.0.0.49'),
        'access_level': 'VPN_WAN',
        'session_timeout': 900,   # 15 minutes
        'description': 'Personnel - WAN-level read-only access for status checking'
    }
}

# =============================================================================
# VPN SECURITY SETTINGS
# =============================================================================

# Rate limiting for VPN connections (requests per minute)
VPN_RATE_LIMITS = {
    'commander': 60,    # Higher limit for commanders
    'armorer': 60,      # Higher limit for armorers
    'emergency': 45,    # Moderate limit for emergency ops
    'personnel': 30,    # Lower limit for general personnel
}

# Emergency access time limits (hours)
EMERGENCY_ACCESS_TIME_LIMITS = {
    'emergency': 4,     # Emergency operations: 4 hours max
    'commander': 24,    # Field commanders: 24 hours max
    'armorer': 12,      # Armorers: 12 hours max
}

# VPN connection monitoring
VPN_MONITORING = {
    'log_all_connections': True,
    'log_failed_attempts': True,
    'alert_on_suspicious_activity': True,
    'max_concurrent_connections_per_user': 2,
    'connection_timeout_minutes': 30,
}

# =============================================================================
# ENHANCED NETWORK SETTINGS (Updates to existing settings)
# =============================================================================

# Update existing LAN networks to include VPN
LAN_NETWORKS = [
    '192.168.10.0/24',   # Physical LAN network
    '10.0.0.0/24',       # WireGuard VPN network
    '172.16.0.0/12',     # Private Class B
    '10.0.0.0/8',        # Private Class A
    '127.0.0.0/8',       # Loopback
]

# VPN-aware path restrictions
VPN_PATH_RESTRICTIONS = {
    # Paths requiring LAN-level access (includes VPN_LAN)
    'lan_required': [
        '/admin/register/',
        '/admin/users/create/',
        '/transactions/create/',
        '/transactions/qr-scanner/',
        '/inventory/add/',
        '/inventory/edit/',
        '/inventory/delete/',
        '/personnel/add/',
        '/personnel/edit/',
        '/personnel/delete/',
        '/qr_manager/generate/',
        '/print_handler/',
    ],
    
    # Paths available for emergency access (VPN_LAN_LIMITED)
    'emergency_allowed': [
        '/transactions/create/',
        '/transactions/qr-scanner/',
        '/inventory/view/',
        '/inventory/detail/',
        '/personnel/list/',
        '/personnel/detail/',
        '/dashboard/',
        '/reports/emergency/',
    ],
    
    # Paths available for WAN-level access (includes VPN_WAN)
    'wan_allowed': [
        '/dashboard/',
        '/personnel/list/',
        '/personnel/detail/',
        '/transactions/history/',
        '/transactions/status/',
        '/inventory/view/',
        '/reports/',
        '/users/profile/',
        '/static/',
        '/media/',
        '/users/login/',
        '/users/logout/',
    ],
}

# =============================================================================
# VPN MIDDLEWARE CONFIGURATION
# =============================================================================

# Add VPN middleware to existing MIDDLEWARE list
# Replace or update existing NetworkBasedAccessMiddleware
VPN_MIDDLEWARE = [
    'core.middleware.SecurityHeadersMiddleware',
    'vpn_integration.core_integration.vpn_middleware.VPNAwareNetworkMiddleware',
    'vpn_integration.core_integration.vpn_middleware.VPNConnectionLogMiddleware',
    'axes.middleware.AxesMiddleware',
]

# =============================================================================
# VPN LOGGING CONFIGURATION
# =============================================================================

VPN_LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'vpn_detailed': {
            'format': '[VPN] {asctime} {levelname} {name}: {message}',
            'style': '{',
        },
        'vpn_security': {
            'format': '[VPN-SEC] {asctime} {levelname}: {message} [IP:{extra[client_ip]} Role:{extra[vpn_role]} User:{extra[username]}]',
            'style': '{',
        },
    },
    'handlers': {
        'vpn_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/armguard/vpn_access.log',
            'formatter': 'vpn_detailed',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'vpn_security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/armguard/vpn_security.log',
            'formatter': 'vpn_security',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
        },
        'vpn_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'vpn_detailed',
        },
    },
    'loggers': {
        'armguard.vpn': {
            'handlers': ['vpn_file', 'vpn_console'],
            'level': 'INFO',
            'propagate': False,
        },
        'armguard.vpn.security': {
            'handlers': ['vpn_security', 'vpn_console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# =============================================================================
# VPN INTEGRATION WITH EXISTING FEATURES
# =============================================================================

# Update existing session settings for VPN awareness
SESSION_COOKIE_AGE = config('SESSION_COOKIE_AGE', default=3600, cast=int)  # Default 1 hour

# VPN-specific session settings
VPN_SESSION_SETTINGS = {
    'use_role_based_timeouts': True,
    'extend_on_activity': True,
    'force_logout_on_role_change': True,
    'log_session_events': True,
}

# Integration with existing security features
SECURITY_INTEGRATION = {
    'axes_vpn_aware': True,        # Make Django Axes VPN-aware
    'ratelimit_vpn_separate': True, # Separate rate limits for VPN
    'csrf_vpn_trusted': True,      # Trust VPN networks for CSRF
    'secure_headers_vpn': True,    # Apply security headers to VPN responses
}

# =============================================================================
# VPN OPERATIONAL SETTINGS
# =============================================================================

# VPN server operational parameters
VPN_SERVER_CONFIG = {
    'max_clients': 50,
    'keepalive_interval': 25,      # seconds
    'handshake_timeout': 5,        # seconds
    'key_rotation_days': 30,       # days
    'config_backup_retention': 7,  # days
}

# VPN client configuration defaults
VPN_CLIENT_DEFAULTS = {
    'dns_servers': ['10.0.0.1', '8.8.8.8', '8.8.4.4'],
    'persistent_keepalive': 25,
    'allowed_ips_lan': '192.168.10.0/24',
    'allowed_ips_wan': '192.168.10.1/32',
    'mtu': 1420,
}

# =============================================================================
# VPN MONITORING AND ALERTING
# =============================================================================

VPN_ALERTS = {
    'failed_authentication_threshold': 5,      # Alert after 5 failed attempts
    'unusual_access_pattern_threshold': 100,   # Alert after 100 requests/hour from single IP
    'concurrent_connections_threshold': 3,     # Alert if user has more than 3 connections
    'session_duration_threshold': 8,           # Alert if session exceeds 8 hours
    'data_transfer_threshold': 1073741824,     # Alert if transfer exceeds 1GB/session
}

# VPN health check configuration
VPN_HEALTH_CHECKS = {
    'interface_check_interval': 300,           # Check interface every 5 minutes
    'peer_check_interval': 60,                 # Check peers every minute
    'performance_check_interval': 600,         # Performance check every 10 minutes
    'log_health_status': True,
    'alert_on_interface_down': True,
    'alert_on_peer_disconnect': False,         # Don't alert on normal disconnects
}

# =============================================================================
# VPN BACKUP AND RECOVERY
# =============================================================================

VPN_BACKUP_CONFIG = {
    'auto_backup_configs': True,
    'backup_interval_hours': 24,
    'backup_retention_days': 30,
    'backup_location': '/etc/wireguard/backups',
    'encrypt_backups': True,
    'backup_keys_separately': True,
}

# =============================================================================
# ENVIRONMENT-SPECIFIC VPN SETTINGS
# =============================================================================

# Development environment
if config('DJANGO_DEBUG', default=False, cast=bool):
    VPN_DEVELOPMENT = {
        'allow_test_clients': True,
        'reduced_session_timeouts': True,
        'detailed_logging': True,
        'skip_ip_validation': False,  # Still validate IPs in development
    }

# Production environment overrides
VPN_PRODUCTION_OVERRIDES = {
    'enhanced_logging': True,
    'strict_session_timeouts': True,
    'enable_all_monitoring': True,
    'require_certificate_validation': True,
    'enable_intrusion_detection': True,
}

# =============================================================================
# USAGE EXAMPLES FOR VIEWS
# =============================================================================

"""
Example view decorators usage:

from vpn_integration.core_integration.vpn_decorators import (
    vpn_role_required, vpn_lan_required, emergency_access_only,
    commander_or_armorer_only
)

# Require commander or armorer VPN role
@vpn_role_required(['commander', 'armorer'])
def sensitive_inventory_view(request):
    # Only commanders and armorers via VPN can access
    pass

# Require LAN-level access (physical LAN or VPN LAN)
@vpn_lan_required
def transaction_create_view(request):
    # Requires LAN or VPN_LAN access level
    pass

# Emergency-only operations
@emergency_access_only(max_duration_hours=4)
def emergency_equipment_issue(request):
    # Only emergency role VPN users, time-limited to 4 hours
    pass

# Convenience decorator for admin operations
@commander_or_armorer_only
def admin_operation_view(request):
    # Commander or armorer role required
    pass
"""

# =============================================================================
# TEMPLATE CONTEXT INTEGRATION
# =============================================================================

# Add VPN context to templates
VPN_TEMPLATE_CONTEXT = {
    'show_vpn_status': True,
    'show_network_type': True,
    'show_role_info': True,
    'show_session_timeout': True,
}

# Template context processor addition
VPN_CONTEXT_PROCESSORS = [
    'vpn_integration.core_integration.vpn_context.vpn_template_context',
]