# Template Context Processor for Network-Aware UI

def network_context(request):
    """
    Add network-aware context to all templates
    Shows/hides UI elements based on network access type
    """
    # Get network type from request attributes set by middleware
    network_type = getattr(request, 'network_type', 'lan')
    is_lan = getattr(request, 'is_lan_access', True)
    is_wan = getattr(request, 'is_wan_access', False)
    
    context = {
        'network_type': network_type,
        'allow_write_operations': is_lan,
        'is_lan_access': is_lan,
        'is_wan_access': is_wan,
    }
    return context