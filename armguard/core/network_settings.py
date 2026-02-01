# Settings additions for LAN/WAN Network Security
# Add these to your core/settings.py file

# =============================================================================
# NETWORK-BASED ACCESS CONTROL SETTINGS
# =============================================================================

# Enable network-based access control
ENABLE_NETWORK_ACCESS_CONTROL = config('ENABLE_NETWORK_ACCESS_CONTROL', default=True, cast=bool)

# Network configuration
LAN_PORT = config('LAN_PORT', default='8443')
WAN_PORT = config('WAN_PORT', default='443')

# LAN network ranges (customize for your military network)
LAN_NETWORKS = [
    '192.168.1.0/24',    # Your Raspberry Pi network
    '192.168.0.0/16',    # Standard private Class C
    '172.16.0.0/12',     # Standard private Class B
    '10.0.0.0/8',        # Standard private Class A
    '127.0.0.0/8',       # Loopback
]

# =============================================================================
# MIDDLEWARE UPDATES
# =============================================================================

# Add network security middleware (add to existing MIDDLEWARE list)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # ArmGuard Security Middleware
    'core.middleware.RateLimitMiddleware',
    'core.middleware.SecurityHeadersMiddleware', 
    'core.middleware.AdminIPWhitelistMiddleware',
    
    # NEW: Network-based access control
    'core.network_middleware.NetworkBasedAccessMiddleware',
    'core.network_middleware.UserRoleNetworkMiddleware',
    
    # Axes middleware for failed login tracking
    'axes.middleware.AxesMiddleware',
]

# =============================================================================
# TEMPLATE CONTEXT PROCESSORS
# =============================================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                
                # NEW: Network-aware context processor
                'core.network_context.network_context',
            ],
        },
    },
]

# =============================================================================
# LOGGING FOR NETWORK ACCESS MONITORING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'network': {
            'format': '[NETWORK] {asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'armguard.log',
            'formatter': 'verbose',
        },
        'network_file': {
            'level': 'INFO', 
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'network_access.log',
            'formatter': 'network',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
        },
        'armguard': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
        'core.network_middleware': {
            'handlers': ['network_file', 'console'],
            'level': 'INFO',
        },
    },
}

# =============================================================================
# NETWORK-AWARE FEATURE FLAGS
# =============================================================================

# Features available based on network access
NETWORK_FEATURES = {
    'LAN': {
        'user_registration': True,
        'transaction_creation': True, 
        'inventory_management': True,
        'personnel_management': True,
        'print_operations': True,
        'qr_generation': True,
        'admin_operations': True,
    },
    'WAN': {
        'user_registration': False,
        'transaction_creation': False,
        'inventory_management': False, 
        'personnel_management': False,
        'print_operations': False,
        'qr_generation': False,
        'admin_operations': False,
        'status_checking': True,
        'reports_viewing': True,
        'dashboard_access': True,
    }
}