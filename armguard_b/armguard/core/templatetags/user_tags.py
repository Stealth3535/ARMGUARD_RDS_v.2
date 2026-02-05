"""
Custom template tags for user-related functionality
"""
from django import template

register = template.Library()


@register.filter(name='get_user_role')
def get_user_role(user):
    """
    Get the user's role based on permissions and groups
    Returns: 'Superuser', 'Admin', 'Armorer', or 'Personnel'
    """
    if not user.is_authenticated:
        return 'Guest'
    
    if user.is_superuser:
        return 'Superuser'
    
    # Check groups
    if user.groups.filter(name='Admin').exists():
        return 'Admin'
    
    if user.groups.filter(name='Armorer').exists():
        return 'Armorer'
    
    # Default for personnel
    return 'Personnel'


@register.filter(name='is_armorer')
def is_armorer(user):
    """
    Check if user is in the Armorer group
    Returns: True if user is an armorer, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    return user.groups.filter(name='Armorer').exists()
