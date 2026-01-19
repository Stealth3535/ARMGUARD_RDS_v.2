"""
Core Views - Dashboard and Main Application Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib import messages
from django.db.models import Count
from datetime import datetime, timedelta
from personnel.models import Personnel
from inventory.models import Item
from transactions.models import Transaction


@login_required
def dashboard(request):
    """Main dashboard view with statistics"""
    
    # Personnel Statistics
    total_personnel = Personnel.objects.count()
    active_personnel = Personnel.objects.filter(status='Active').count()
    officers = Personnel.objects.filter(serial__startswith='O-').count()
    enlisted = total_personnel - officers
    
    # Inventory Statistics
    total_items = Item.objects.count()
    available_items = Item.objects.filter(status='Available').count()
    issued_items = Item.objects.filter(status='Issued').count()
    maintenance_items = Item.objects.filter(status='Maintenance').count()
    
    # Items by type
    items_by_type = Item.objects.values('item_type').annotate(count=Count('id'))
    
    # Recent Transactions
    recent_transactions = Transaction.objects.select_related('personnel', 'item').order_by('-date_time')[:10]
    
    # Transactions this week
    week_ago = datetime.now() - timedelta(days=7)
    transactions_this_week = Transaction.objects.filter(date_time__gte=week_ago).count()
    
    context = {
        'total_personnel': total_personnel,
        'active_personnel': active_personnel,
        'officers': officers,
        'enlisted': enlisted,
        'total_items': total_items,
        'available_items': available_items,
        'issued_items': issued_items,
        'maintenance_items': maintenance_items,
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
    """Custom login for Django admin - only allow superusers"""
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('/superadmin/')
        else:
            messages.error(request, 'Only superusers can access the Django admin site.')
            return redirect('login')
    
    return redirect('login')
