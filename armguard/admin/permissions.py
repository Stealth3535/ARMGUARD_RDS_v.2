"""
Admin Permissions and Restrictions System
"""
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps


def check_restricted_admin(user):
    """
    Check if a user is a restricted administrator
    Returns True if user is restricted (view-only), False if unrestricted
    """
    if not user.is_authenticated:
        return False
    
    # Check if user is in Admin group
    if not user.groups.filter(name='Admin').exists():
        return False
        
    # Check if user has restricted admin profile
    if hasattr(user, 'userprofile') and user.userprofile.is_restricted_admin:
        return True
        
    return False


def unrestricted_admin_required(view_func):
    """
    Decorator that requires unrestricted admin access
    Blocks restricted administrators from accessing certain views
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Allow superuser
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
            
        # Check if user is restricted admin
        if check_restricted_admin(request.user):
            messages.error(request, 'Access denied. You have restricted administrator privileges and can only view data.')
            return redirect(reverse('armguard_admin:dashboard'))
            
        # Allow if user is unrestricted admin or armorer
        if request.user.groups.filter(name__in=['Admin', 'Armorer']).exists():
            return view_func(request, *args, **kwargs)
            
        # Deny all others
        messages.error(request, 'Access denied. Administrator privileges required.')
        return redirect(reverse('armguard_admin:dashboard'))
        
    return _wrapped_view


def restricted_admin_permission_check(request):
    """
    Context processor to add restriction status to all templates
    """
    is_restricted_admin = False
    if request.user.is_authenticated:
        is_restricted_admin = check_restricted_admin(request.user)
    
    return {
        'is_restricted_admin': is_restricted_admin,
        'can_edit': not is_restricted_admin,  # Convenience flag
    }