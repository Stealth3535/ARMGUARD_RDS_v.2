# Example view updates to use network-aware decorators
# These examples show how to update your existing views

from core.network_decorators import lan_required, read_only_on_wan, network_aware_permission_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

# =============================================================================
# TRANSACTION VIEWS (Require LAN Access)
# =============================================================================

@login_required
@lan_required  # NEW: Force LAN access for transactions
@require_http_methods(["POST"])
def create_transaction(request):
    """Create new transaction - LAN ONLY for security"""
    # Your existing transaction creation code
    pass

# =============================================================================
# PERSONNEL VIEWS (LAN for writes, WAN for reads)
# =============================================================================

@login_required
@lan_required  # NEW: Registration requires LAN
def register_personnel(request):
    """Register new personnel - LAN ONLY"""
    # Your existing registration code
    pass

@login_required
@read_only_on_wan  # NEW: Allow WAN viewing, but not editing
def personnel_detail(request, personnel_id):
    """View personnel details - WAN can view, only LAN can edit"""
    # Your existing personnel detail code
    pass

# =============================================================================
# INVENTORY VIEWS (Network-aware permissions)
# =============================================================================

@login_required
@network_aware_permission_required('inventory.change_item', lan_only=True)
def update_inventory(request, item_id):
    """Update inventory - requires permission AND LAN access"""
    # Your existing inventory update code
    pass

@login_required  
@read_only_on_wan
def view_inventory(request):
    """View inventory - WAN can view, LAN can manage"""
    # Your existing inventory view code
    pass

# =============================================================================
# API VIEWS (Enhanced with network checks)
# =============================================================================

@require_http_methods(["GET"])
@login_required
@read_only_on_wan  # NEW: API reads allowed from WAN
def get_personnel_api(request, personnel_id):
    """Get personnel data - WAN can access for status checking"""
    # Your existing API code
    pass

@require_http_methods(["POST"])
@login_required
@lan_required  # NEW: API writes require LAN
def create_transaction_api(request):
    """Create transaction via API - LAN ONLY"""
    # Your existing API transaction code
    pass

# =============================================================================
# ADMIN VIEWS (LAN required for sensitive operations)
# =============================================================================

@login_required
@lan_required  # NEW: User creation requires LAN
def create_user(request):
    """Create new user - LAN ONLY for security"""
    # Your existing user creation code
    pass

@login_required
@read_only_on_wan  # NEW: Reports can be viewed from WAN
def generate_report(request):
    """Generate reports - WAN can view, LAN can create/modify"""
    # Your existing report code
    pass