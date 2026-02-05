# Template Context Processor for Network-Aware UI

def network_context(request):
    """
    Add network-aware context to all templates
    Shows/hides UI elements based on network access type
    """
    context = {
        'network_type': getattr(request, 'network_type', 'UNKNOWN'),
        'allow_write_operations': getattr(request, 'allow_write_operations', False),
        'is_lan_access': getattr(request, 'network_type', 'UNKNOWN') == 'LAN',
        'is_wan_access': getattr(request, 'network_type', 'UNKNOWN') == 'WAN',
    }
    return context