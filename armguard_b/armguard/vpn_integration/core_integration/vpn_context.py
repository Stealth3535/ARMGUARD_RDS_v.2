# VPN Template Context Processor
# Provides VPN connection information to templates

def vpn_context(request):
    """Add VPN context to templates for displaying VPN connection status and role information"""
    context = {
        'is_vpn_access': False,
        'vpn_role': None,
        'vpn_client_info': None,
        'vpn_enabled': False,
    }
    
    # Check if VPN is enabled in settings
    from django.conf import settings
    context['vpn_enabled'] = getattr(settings, 'WIREGUARD_ENABLED', False)
    
    # Add VPN client information if available
    if hasattr(request, 'vpn_client') and request.vpn_client:
        context.update({
            'is_vpn_access': True,
            'vpn_role': request.vpn_client.get('vpn_role'),
            'vpn_client_info': request.vpn_client,
            'vpn_ip': request.vpn_client.get('vpn_ip'),
            'access_level': request.vpn_client.get('access_level'),
        })
    
    return context