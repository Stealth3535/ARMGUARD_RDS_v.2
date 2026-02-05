"""
Core Views - Dashboard and Main Application Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Count, Q
from datetime import timedelta
from django.utils import timezone
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction


@login_required
def dashboard(request):
    """Main dashboard view with statistics - PERFORMANCE OPTIMIZED"""
    
    # Personnel Statistics - optimized queries
    personnel_stats = Personnel.objects.aggregate(
        total_personnel=Count('id'),
        active_personnel=Count('id', filter=Q(status='Active')),
        officers=Count('id', filter=Q(classification='OFFICER')),
        enlisted=Count('id', filter=Q(classification='ENLISTED PERSONNEL'))
    )
    
    # Inventory Statistics - optimized queries
    inventory_stats = Item.objects.aggregate(
        total_items=Count('id'),
        available_items=Count('id', filter=Q(status='Available')),
        issued_items=Count('id', filter=Q(status='Issued')),
        maintenance_items=Count('id', filter=Q(status='Maintenance'))
    )
    
    # Items by type - optimized aggregation
    items_by_type = Item.objects.values('item_type').annotate(count=Count('id'))
    
    # Recent Transactions - PERFORMANCE FIX: Use select_related to prevent N+1
    recent_transactions = Transaction.objects.select_related(
        'personnel', 'item'
    ).prefetch_related(
        'personnel__user'  # If needed for user info
    ).order_by('-date_time')[:10]
    
    # Transactions this week - optimized query
    week_ago = timezone.now() - timedelta(days=7)
    transactions_this_week = Transaction.objects.filter(
        date_time__gte=week_ago
    ).count()
    
    context = {
        # Unpack statistics dictionaries
        **personnel_stats,
        **inventory_stats,
        'items_by_type': items_by_type,
        'recent_transactions': recent_transactions,
        'transactions_this_week': transactions_this_week,
    }
    
    return render(request, 'dashboard.html', context)


def login_view(request):
    """Login page"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'auth/login.html')


def logout_view(request):
    """Logout user"""
    logout(request)
    return redirect('login')


def superuser_login(request, *args, **kwargs):
    """
    SECURITY FIX: Removed custom authentication logic.
    Redirect to Django's built-in admin login for security.
    """
    from django.shortcuts import redirect
    from django.contrib import messages
    
    messages.info(request, 'Please use the standard admin login.')
    return redirect('/admin/login/')
