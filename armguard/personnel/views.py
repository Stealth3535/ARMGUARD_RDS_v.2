"""
Personnel Views - Display and Search Only
Note: Personnel CRUD operations are now centralized in admin.views.UniversalRegistrationForm
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import JsonResponse
from .models import Personnel
from .forms import PersonnelSearchForm


@login_required
def personnel_profile_list(request):
    """Display list of all personnel with search functionality"""
    personnel_list = Personnel.objects.all().order_by('rank', 'surname', 'firstname')
    search_form = PersonnelSearchForm(request.GET)
    
    # Apply search filters
    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search_query')
        status = search_form.cleaned_data.get('status')
        rank_type = search_form.cleaned_data.get('rank_type')
        office = search_form.cleaned_data.get('office')
        
        if search_query:
            personnel_list = personnel_list.filter(
                Q(surname__icontains=search_query) |
                Q(firstname__icontains=search_query) |
                Q(rank__icontains=search_query) |
                Q(serial__icontains=search_query) |
                Q(office__icontains=search_query)
            )
        
        if status:
            personnel_list = personnel_list.filter(status=status)
        
        if rank_type:
            if rank_type == 'officer':
                personnel_list = personnel_list.filter(rank__in=[r[0] for r in Personnel.RANKS_OFFICER])
            elif rank_type == 'enlisted':
                personnel_list = personnel_list.filter(rank__in=[r[0] for r in Personnel.RANKS_ENLISTED])
        
        if office:
            personnel_list = personnel_list.filter(office=office)
    
    # Pagination
    paginator = Paginator(personnel_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_count': personnel_list.count(),
        'officer_count': personnel_list.filter(rank__in=[r[0] for r in Personnel.RANKS_OFFICER]).count(),
        'enlisted_count': personnel_list.filter(rank__in=[r[0] for r in Personnel.RANKS_ENLISTED]).count(),
        'active_count': personnel_list.filter(status=Personnel.STATUS_ACTIVE).count(),
        'with_user_count': personnel_list.filter(user__isnull=False).count(),
        'without_user_count': personnel_list.filter(user__isnull=True).count(),
    }
    
    return render(request, 'personnel/personnel_profile_list.html', context)


@login_required
def personnel_profile_detail(request, pk):
    """Display detailed view of a single personnel record"""
    personnel = get_object_or_404(Personnel, id=pk)
    
    # Get related user information if linked
    user_info = None
    if personnel.user:
        user_info = {
            'username': personnel.user.username,
            'email': personnel.user.email,
            'date_joined': personnel.user.date_joined,
            'last_login': personnel.user.last_login,
            'is_active': personnel.user.is_active,
            'profile': personnel.user.userprofile if hasattr(personnel.user, 'userprofile') else None
        }
    
    # Get recent transactions if any
    recent_transactions = []
    if hasattr(personnel, 'transaction_set'):
        recent_transactions = personnel.transaction_set.all().order_by('-date_time')[:5]
    
    # Get QR code if exists
    qr_code_obj = None
    try:
        from qr_manager.models import QRCodeImage
        qr_code_obj = QRCodeImage.objects.get(
            qr_type=QRCodeImage.TYPE_PERSONNEL,
            reference_id=personnel.id
        )
    except:
        pass
    
    context = {
        'personnel': personnel,
        'user_info': user_info,
        'recent_transactions': recent_transactions,
        'qr_code_obj': qr_code_obj,
        'is_officer': personnel.rank in [r[0] for r in Personnel.RANKS_OFFICER],
        'can_edit': request.user.is_superuser or request.user.groups.filter(name='Admin').exists(),
    }
    
    return render(request, 'personnel/personnel_profile_detail.html', context)


@login_required
def personnel_search_api(request):
    """AJAX API for personnel search (for autocomplete, etc.)"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    personnel = Personnel.objects.filter(
        Q(surname__icontains=query) |
        Q(firstname__icontains=query) |
        Q(rank__icontains=query) |
        Q(serial__icontains=query)
    )[:10]
    
    results = []
    for p in personnel:
        results.append({
            'id': p.id,
            'text': f"{p.rank} {p.get_full_name()}",
            'serial': p.serial,
            'office': p.office,
            'status': p.status,
            'has_user': bool(p.user)
        })
    
    return JsonResponse({'results': results})


# Alias for the function-based view versions to maintain URL compatibility
personnel_profile_list.as_view = lambda: personnel_profile_list
personnel_profile_detail.as_view = lambda: personnel_profile_detail

