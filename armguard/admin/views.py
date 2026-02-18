"""
Admin Views - System Administration and Management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.db.models import Q, Count
from django.conf import settings
from django.db import transaction, DatabaseError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.utils import timezone
from inventory.models import Item
from personnel.models import Personnel
from transactions.models import Transaction
from users.models import UserProfile
from .models import AuditLog, DeletedRecord
from core.network_decorators import lan_required, read_only_on_wan
import qrcode
from io import BytesIO
import base64
import logging
from pathlib import Path

from .forms import (
    UniversalForm, ItemRegistrationForm, SystemSettingsForm
)
from .permissions import unrestricted_admin_required, check_restricted_admin
from core.cache_utils import DashboardCache, invalidate_dashboard_cache
from core.decorators import handle_database_errors, safe_database_operation, with_audit_context

logger = logging.getLogger(__name__)

def is_admin_user(user):
    """Check if user is admin or superuser - only they can register users"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Admin').exists())


def is_superuser(user):
    """Check if user is superuser - required for critical operations like deletion"""
    return user.is_authenticated and user.is_superuser


def is_staff_or_superuser(user):
    """Check if user is staff or superuser - can delete items"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def is_admin_or_armorer(user):
    """Check if user is admin, superuser, or armorer - can add items"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Armorer').exists()
    )


def is_armorer(user):
    """Check if user is armorer - can issue items"""
    return user.is_authenticated and user.groups.filter(name='Armorer').exists()


@never_cache
@login_required
@user_passes_test(is_admin_or_armorer)
def dashboard(request):
    """Admin dashboard with system overview and centralized registration access"""
    # OPTIMIZED: Use cached statistics to reduce database queries
    stats = DashboardCache.get_stats()
    
    # Recent transactions (not cached as they change frequently)
    recent_transactions = Transaction.objects.select_related(
        'personnel', 'item'
    ).order_by('-date_time')[:10]
    
    context = {
        'enable_realtime': True,
        'total_items': stats['total_items'],
        'available_items': stats.get('available_items', 0),
        'issued_items': stats.get('issued_items', 0),
        'total_personnel': stats['total_personnel'],
        'active_personnel': stats['active_personnel'],
        'officers_count': stats['officers_count'],
        'enlisted_count': stats['enlisted_count'],
        'total_transactions': stats['total_transactions'],
        'total_users': stats['total_users'],
        'active_users': stats['active_users'],
        'administrators_count': stats['administrators_count'],
        'armorers_count': stats['armorers_count'],
        'unlinked_personnel': stats['unlinked_personnel'],
        'recent_transactions': recent_transactions,
        'items_by_type': stats['items_by_type'],
    }
    
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='/')
def personnel_registration(request):
    """Personnel-only registration using UniversalForm"""
    if request.method == 'POST':
        # Add operation_type for personnel-only creation
        data = request.POST.copy()
        data['operation_type'] = 'create_personnel_only'
        form = UniversalForm(data, request.FILES)
        if form.is_valid():
            user, personnel = form.save()
            messages.success(request, f'Personnel {personnel.firstname} {personnel.surname} has been registered successfully!')
            
            # Generate QR code if not already created
            from qr_manager.models import QRCodeImage
            if not QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_PERSONNEL, reference_id=personnel.id).exists():
                QRCodeImage.objects.create(
                    qr_type=QRCodeImage.TYPE_PERSONNEL,
                    reference_id=personnel.id,
                    data_content=f"Personnel: {personnel.firstname} {personnel.surname}\nRank: {personnel.rank}\nSerial: {personnel.serial}\nID: {personnel.id}"
                )
            
            return redirect('armguard_admin:personnel_registration_success', pk=personnel.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UniversalForm(initial={'operation_type': 'create_personnel_only'})
    
    context = {
        'form': form,
        'title': 'Personnel Registration',
        'subtitle': 'Add new military personnel to the system'
    }
    return render(request, 'admin/personnel_registration.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='/')
def personnel_registration_success(request, pk):
    """Success page after personnel registration"""
    personnel = get_object_or_404(Personnel, id=pk)
    
    # Get QR code
    qr_code_obj = None
    try:
        from qr_manager.models import QRCodeImage
        qr_code_obj = QRCodeImage.objects.get(qr_type=QRCodeImage.TYPE_PERSONNEL, reference_id=personnel.id)
    except QRCodeImage.DoesNotExist:
        qr_code_obj = None
    except DatabaseError:
        logger.exception("Database error fetching QR code for personnel %s", pk)
        qr_code_obj = None
    
    context = {
        'personnel': personnel,
        'qr_code_obj': qr_code_obj,
        'title': 'Registration Successful'
    }
    return render(request, 'admin/personnel_registration_success.html', context)


@login_required
@user_passes_test(is_admin_user)
@lan_required
def universal_registration(request):
    """Universal registration view - The centralized registration system (LAN only)"""
    if request.method == 'POST':
        # Security: Log form submission without sensitive data
        logger.debug("Registration form submitted by user: %s", request.user.username)
        form = UniversalForm(request.POST, request.FILES)
        if not form.is_valid():
            logger.debug("Registration form validation failed: %s", list(form.errors.keys()))
        if form.is_valid():
            try:
                with transaction.atomic():
                    user, personnel = form.save()
                    
                    # Generate single personnel QR code
                    qr_code = None
                    
                    if personnel:
                        # Generate personnel QR code (includes user link if exists)
                        # Use standard QR generator for consistent gray-on-black styling
                        from utils.qr_generator import generate_qr_code_to_buffer
                        user_info = f":{user.username}" if user else ""
                        personnel_data = f"PERSONNEL:{personnel.id}:{personnel.rank} {personnel.surname}, {personnel.firstname}:{personnel.serial}{user_info}"
                        
                        buffer_personnel = generate_qr_code_to_buffer(personnel_data, size=600)
                        qr_code = base64.b64encode(buffer_personnel.getvalue()).decode()
                    
                    # Success message based on what was created
                    operation_type = form.cleaned_data['operation_type']
                    if operation_type == 'create_personnel_only':
                        messages.success(request, f'Personnel record for "{personnel.rank} {personnel.surname}" created successfully with QR code.')
                    elif operation_type == 'create_user_with_personnel':
                        messages.success(request, f'User account "{user.username}" and personnel record for "{personnel.rank} {personnel.surname}" created successfully with QR code.')
                    elif operation_type in ['edit_user', 'edit_personnel', 'edit_both']:
                        messages.success(request, f'Records updated successfully.')
                    
                    # Store QR code in session for display
                    request.session['qr_code'] = qr_code
                    request.session['personnel_name'] = f"{personnel.rank} {personnel.surname}, {personnel.firstname}" if personnel else None
                    
                    return redirect('armguard_admin:registration_success')
                    
            except (DatabaseError, ValueError):
                logger.exception("Registration failed for user %s", request.user.username)
                messages.error(request, 'Error during registration. Please try again.')
    else:
        form = UniversalForm()
    
    context = {
        'form': form,
        'is_edit': False,
        'page_title': 'Universal Registration',
        'submit_text': 'Register',
        'enable_realtime': False,
    }
    return render(request, 'admin/universal_form.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
def registration_success(request):
    """Display success page with QR code"""
    qr_code = request.session.pop('qr_code', None)
    personnel_name = request.session.pop('personnel_name', None)
    return render(request, 'admin/registration_success.html', {
        'qr_code': qr_code,
        'personnel_name': personnel_name
    })


@never_cache
@login_required
@user_passes_test(is_admin_user)
def user_management(request):
    """User management interface"""
    # OPTIMIZED: Use Prefetch to avoid N+1 queries for personnel
    from django.db.models import Prefetch
    
    # Get ALL users with accounts for User Management section
    # Prefetch personnel to avoid N+1 queries
    admin_users = User.objects.select_related('userprofile').prefetch_related(
        'groups',
        Prefetch('personnel', queryset=Personnel.objects.all())
    ).distinct().order_by('-date_joined')
    
    # Get only personnel users (non-admin, non-staff) for Personnel Management section
    personnel_users = User.objects.select_related('userprofile').prefetch_related(
        'groups',
        Prefetch('personnel', queryset=Personnel.objects.all())
    ).filter(
        is_staff=False,
        is_superuser=False
    ).exclude(
        groups__name__in=['Admin', 'Armorer']
    ).order_by('-date_joined')
    
    # Filter options
    role_filter = request.GET.get('role')
    search_query = request.GET.get('search')
    
    if role_filter:
        if role_filter == 'admin':
            admin_users = admin_users.filter(groups__name='Admin')
        elif role_filter == 'superuser':
            admin_users = admin_users.filter(is_superuser=True)
        elif role_filter == 'armorer':
            admin_users = admin_users.filter(groups__name='Armorer')
        elif role_filter == 'personnel':
            # Show only users who are NOT superuser, admin, or armorer
            admin_users = admin_users.filter(
                is_superuser=False,
                is_staff=False
            ).exclude(groups__name__in=['Admin', 'Armorer'])
    
    if search_query:
        admin_users = admin_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
        personnel_users = personnel_users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Personnel search and sorting
    personnel_search = request.GET.get('personnel_search', '').strip()
    personnel_search_by = request.GET.get('personnel_search_by', 'name')
    personnel_qs = Personnel.objects.filter(user__isnull=True)
    if personnel_search:
        if personnel_search_by == 'name':
            personnel_qs = personnel_qs.filter(
                Q(firstname__icontains=personnel_search) |
                Q(surname__icontains=personnel_search) |
                Q(middle_initial__icontains=personnel_search)
            )
        elif personnel_search_by == 'id':
            personnel_qs = personnel_qs.filter(id__icontains=personnel_search)
        elif personnel_search_by == 'serial':
            personnel_qs = personnel_qs.filter(serial__icontains=personnel_search)
        elif personnel_search_by == 'group':
            personnel_qs = personnel_qs.filter(group__icontains=personnel_search)
    # Auto-sort by search type
    if personnel_search_by == 'name':
        personnel_qs = personnel_qs.order_by('surname', 'firstname')
    elif personnel_search_by == 'id':
        personnel_qs = personnel_qs.order_by('id')
    elif personnel_search_by == 'serial':
        personnel_qs = personnel_qs.order_by('serial')
    elif personnel_search_by == 'group':
        personnel_qs = personnel_qs.order_by('group', 'surname')
    else:
        personnel_qs = personnel_qs.order_by('surname', 'firstname')

    # Check if current user can edit (Admin or Superuser, and not restricted)
    can_edit_personnel = request.user.is_superuser or request.user.groups.filter(name='Admin').exists()
    can_edit = can_edit_personnel
    
    # Check if user is a restricted admin
    is_restricted_admin = False
    if request.user.groups.filter(name='Admin').exists():
        try:
            is_restricted_admin = request.user.userprofile.is_restricted_admin
        except:
            is_restricted_admin = False

    context = {
        'users': admin_users,  # All users with accounts (Superuser, Admin, Armorer, Personnel)
        'personnel_users': personnel_users,  # Personnel users with accounts (for backward compatibility)
        'user_count': admin_users.count(),
        'personnel_user_count': personnel_users.count(),
        'admin_count': admin_users.filter(groups__name='Admin').count(),
        'armorer_count': admin_users.filter(groups__name='Armorer').count(),
        'superuser_count': admin_users.filter(is_superuser=True).count(),
        'active_count': admin_users.filter(is_active=True).count(),
        'personnel': personnel_qs,  # Personnel without user accounts (filtered)
        'unlinked_personnel': personnel_qs,
        'role_filter': role_filter,
        'search_query': search_query,
        'can_edit_personnel': can_edit_personnel,
        'can_edit': can_edit,
        'is_restricted_admin': is_restricted_admin,
    }
    return render(request, 'admin/user_management.html', context)


# Legacy views for backward compatibility
@login_required
@user_passes_test(is_admin_user)
def create_user(request):
    """Redirect to the registration page"""
    return redirect('armguard_admin:registration')


@login_required
@user_passes_test(is_admin_user)
@unrestricted_admin_required
def edit_user(request, user_id):
    """Edit existing user"""
    edit_user_obj = get_object_or_404(User, id=user_id)
    
    # Prevent non-superusers from editing superusers
    if edit_user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Only superusers can edit other superusers.')
        return redirect('armguard_admin:user_management')
    
    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)
        logger.debug("Edit user form submitted for user_id: %s by: %s", user_id, request.user.username)
        
        # Set up data for UniversalForm edit operation
        data = request.POST.copy()
        # Check if user has linked personnel to determine operation type
        has_personnel = hasattr(edit_user_obj, 'personnel') and edit_user_obj.personnel
        if has_personnel:
            data['operation_type'] = 'edit_both'
            data['edit_personnel_id'] = edit_user_obj.personnel.id
        else:
            data['operation_type'] = 'edit_user'
        data['edit_user_id'] = edit_user_obj.id
        
        # Pass both edit_user and edit_personnel if personnel exists
        form_kwargs = {'edit_user': edit_user_obj, 'request_user': request.user, 'request': request}
        if has_personnel:
            form_kwargs['edit_personnel'] = edit_user_obj.personnel
        form = UniversalForm(data, request.FILES, **form_kwargs)
        
        if not form.is_valid():
            logger.debug("Edit user form validation failed: %s", list(form.errors.keys()))
        if form.is_valid():
            try:
                with transaction.atomic():
                    user, personnel = form.save()
                    messages.success(request, f'User \"{user.username}\" updated successfully!')
                    return redirect('armguard_admin:user_management')
                    
            except DatabaseError:
                logger.exception("Database error updating user %s by %s", edit_user_obj.id, request.user.username)
                messages.error(request, 'Error updating user. Please try again.')
        else:
            # Form has validation errors - errors will display inline in template
            messages.error(request, 'Please correct the errors below.')
    else:
        # Create form for editing - include personnel if linked
        has_personnel = hasattr(edit_user_obj, 'personnel') and edit_user_obj.personnel
        operation_type = 'edit_both' if has_personnel else 'edit_user'
        
        form_kwargs = {'edit_user': edit_user_obj, 'request': request}
        if has_personnel:
            form_kwargs['edit_personnel'] = edit_user_obj.personnel
        
        form = UniversalForm(initial={'operation_type': operation_type}, **form_kwargs)
    
    context = {
        'form': form,
        'edit_user': edit_user_obj,
        'is_edit': True,
        'page_title': f'Edit User: {edit_user_obj.username}',
        'submit_text': 'Save Changes',
        'is_superuser': request.user.is_superuser,
        'is_admin': request.user.groups.filter(name='Admin').exists(),
        'can_edit_role': request.user.is_superuser or request.user.groups.filter(name='Admin').exists(),
        'enable_realtime': False,  # Disable WebSocket on form pages
    }
    return render(request, 'admin/universal_form.html', context)



@login_required
@user_passes_test(is_admin_user)
@unrestricted_admin_required
def edit_personnel(request, personnel_id):
    """Edit personnel record - Admin and Superuser can edit"""
    from personnel.models import Personnel
    
    edit_personnel_obj = get_object_or_404(Personnel, id=personnel_id)
    
    if request.method == 'POST':
        # Set up data for UniversalForm edit operation
        data = request.POST.copy()
        data['operation_type'] = 'edit_personnel'
        data['edit_personnel_id'] = edit_personnel_obj.id
        
        form = UniversalForm(data, request.FILES, edit_personnel=edit_personnel_obj, request_user=request.user, request=request)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    user, personnel = form.save()
                    
                    # Log the update action
                    AuditLog.objects.create(
                        performed_by=request.user,
                        action='UPDATE',
                        target_model='Personnel',
                        target_id=personnel.id,
                        target_name=personnel.get_full_name(),
                        description=f'Updated personnel record: {personnel.get_full_name()}',
                        ip_address=request.META.get('REMOTE_ADDR')
                    )
                    
                    messages.success(request, f'Personnel record for "{personnel.get_full_name()}" updated successfully!')
                    return redirect('armguard_admin:user_management')
                    
            except DatabaseError:
                logger.exception("Database error updating personnel %s by %s", edit_personnel_obj.id, request.user.username)
                messages.error(request, 'Error updating personnel. Please try again.')
        else:
            # Form has validation errors - errors will display inline in template
            messages.error(request, 'Please correct the errors below.')
    else:
        # Create form for editing personnel only
        form = UniversalForm(
            initial={'operation_type': 'edit_personnel'}, 
            edit_personnel=edit_personnel_obj,
            request_user=request.user,
            request=request
        )
    
    context = {
        'form': form,
        'edit_personnel': edit_personnel_obj,
        'is_edit': True,
        'page_title': f'Edit Personnel: {edit_personnel_obj.get_full_name()}',
        'submit_text': 'Save Changes',
        'is_superuser': request.user.is_superuser,
        'is_admin': request.user.groups.filter(name='Admin').exists(),
        'can_edit_role': request.user.is_superuser or request.user.groups.filter(name='Admin').exists(),
        'enable_realtime': False,
    }
    return render(request, 'admin/universal_form.html', context)


@login_required
@user_passes_test(is_superuser)
@unrestricted_admin_required
@handle_database_errors(redirect_url='armguard_admin:user_management', error_message='Failed to delete personnel')
def delete_personnel(request, personnel_id):
    """Delete personnel record - Only Superuser can delete"""
    from personnel.models import Personnel
    
    personnel_obj = get_object_or_404(Personnel, id=personnel_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        if not reason:
            messages.error(request, 'Deletion reason is required.')
            return redirect('armguard_admin:delete_personnel', personnel_id=personnel_id)
        # Use atomic transaction for deletion
        with transaction.atomic():
            # Save personnel data before deletion
            personnel_data = {
                'id': personnel_obj.id,
                'firstname': personnel_obj.firstname,
                'surname': personnel_obj.surname,
                'middle_initial': personnel_obj.middle_initial,
                'rank': personnel_obj.rank,
                'serial': personnel_obj.serial,
                'group': personnel_obj.group,
                'has_user_account': hasattr(personnel_obj, 'user'),
            }
            
            # Create DeletedRecord
            DeletedRecord.objects.create(
                deleted_by=request.user,
                model_name='Personnel',
                record_id=personnel_obj.id,
                record_data=personnel_data,
                reason=reason
            )
            
            # Create AuditLog
            AuditLog.objects.create(
                performed_by=request.user,
                action='DELETE',
                target_model='Personnel',
                target_id=personnel_obj.id,
                target_name=personnel_obj.get_full_name(),
                description=f'Soft-deleted personnel record: {personnel_obj.get_full_name()}. Reason: {reason}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            # Soft delete the personnel record (keeps in DB, deletes QR)
            full_name = personnel_obj.get_full_name()
            personnel_obj.soft_delete()
            
            # Invalidate cache after deletion
            invalidate_dashboard_cache()
            
            messages.success(request, f'Personnel record for "{full_name}" has been archived. The record is kept for reference but QR code has been removed.')
            return redirect('armguard_admin:user_management')
    
    # GET request - show confirmation page
    context = {
        'personnel_to_delete': personnel_obj,
    }
    return render(request, 'admin/delete_personnel_confirm.html', context)


@login_required
@user_passes_test(is_admin_user)
def register_armorer(request):
    """Register new armorer (legacy view - redirects to universal registration)"""
    messages.info(request, 'Please use the Universal Registration system for registering armorers.')
    return redirect('armguard_admin:universal_registration')


@login_required
@user_passes_test(is_admin_user)
def register_personnel(request):
    """Register new personnel (legacy view - redirects to universal registration)"""
    messages.info(request, 'Please use the Universal Registration system for registering personnel.')
    return redirect('armguard_admin:universal_registration')


@login_required
@user_passes_test(is_admin_or_armorer)
@unrestricted_admin_required
def register_item(request):
    """Register new inventory item - Unrestricted Admin and Armorer only"""
    if request.method == 'POST':
        form = ItemRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Check if using existing QR code
                existing_qr = form.cleaned_data.get('existing_qr', '').strip()
                
                # Save item (don't commit yet to set existing QR)
                item = form.save(commit=False)
                
                if existing_qr:
                    # Use existing QR code as primary key
                    item._existing_qr = existing_qr
                    item.save()
                    
                    messages.success(request, f'Item "{item}" registered successfully using existing QR code!')
                    return render(request, 'admin/register_item.html', {
                        'form': ItemRegistrationForm(),
                        'item': item,
                        'success': True,
                        'used_existing_qr': True
                    })
                else:
                    # Generate new ID and QR code
                    item.save()
                    
                    # Generate QR code using standard generator for consistent gray-on-black styling
                    from utils.qr_generator import generate_qr_code_to_buffer
                    item_data = f"ITEM:{item.id}:{item.item_type}:{item.serial}"
                    
                    buffer = generate_qr_code_to_buffer(item_data, size=600)
                    qr_code = base64.b64encode(buffer.getvalue()).decode()
                    
                    messages.success(request, f'Item "{item}" registered successfully with QR code!')
                    return render(request, 'admin/register_item.html', {
                        'form': ItemRegistrationForm(),
                        'qr_code': qr_code,
                        'item': item,
                        'success': True
                    })
                
            except (DatabaseError, ValueError):
                logger.exception("Item registration failed for user %s", request.user.username)
                messages.error(request, 'Error registering item. Please try again.')
    else:
        form = ItemRegistrationForm()
    
    return render(request, 'admin/register_item.html', {'form': form})


@login_required
@user_passes_test(is_admin_user)
def system_settings(request):
    """System configuration settings"""
    from .models import DeviceAuthorizationRequest
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST)
        if form.is_valid():
            # Handle system settings updates here
            # This would typically update configuration files or database settings
            messages.success(request, 'System settings updated successfully!')
            return redirect('armguard_admin:system_settings')
    else:
        # Load current system settings
        initial_data = {
            'debug_mode': settings.DEBUG,
            'site_name': getattr(settings, 'SITE_NAME', 'ArmGuard'),
            'max_login_attempts': getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5),
            'session_timeout': getattr(settings, 'SESSION_COOKIE_AGE', 3600) //60,
        }
        form = SystemSettingsForm(initial=initial_data)
    
    # Get pending device authorization requests count
    pending_device_requests = DeviceAuthorizationRequest.objects.filter(
        status='pending'
    ).count() if request.user.is_superuser else 0
    
    context = {
        'form': form,
        'debug_mode': settings.DEBUG,
        'database_engine': settings.DATABASES['default']['ENGINE'],
        'pending_device_requests': pending_device_requests,
    }
    return render(request, 'admin/system_settings.html', context)


def request_device_authorization(request):
    """
    Request device authorization for current device
    """
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware
    from .models import DeviceAuthorizationRequest
    
    middleware = DeviceAuthorizationMiddleware(lambda req: None)
    device_fingerprint = middleware.get_device_fingerprint(request)
    ip_address = middleware.get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    if request.method == 'POST' and not request.user.is_authenticated:
        return redirect(f"/login/?next=/admin/device/request-authorization/")

    stale_approved_request = None

    # Check if request already exists
    try:
        existing_request = DeviceAuthorizationRequest.objects.filter(
            device_fingerprint=device_fingerprint
        ).first()
    except DatabaseError:
        logger.exception("Database error while loading device authorization requests")
        messages.error(
            request,
            'Device authorization database is not ready yet. Please contact your administrator to run migrations.'
        )
        existing_request = None
    
    if existing_request:
        fallback_username = getattr(settings, 'DEVICE_REQUEST_FALLBACK_USER', 'device_request_guest')
        if (
            request.user.is_authenticated
            and existing_request.status == 'pending'
            and existing_request.requested_by
            and existing_request.requested_by.username == fallback_username
        ):
            existing_request.requested_by = request.user
            existing_request.save(update_fields=['requested_by'])

        if existing_request.status == 'pending':
            # Keep user on request page and let template show pending state.
            # Avoid adding repeated flash messages that accumulate across redirects.
            pass
        elif existing_request.status == 'approved':
            is_currently_authorized = middleware.is_device_authorized(
                device_fingerprint,
                ip_address,
                request.path,
                getattr(request, 'user', None),
                required_security='HIGH_SECURITY',
            )

            if is_currently_authorized:
                if existing_request.issued_certificate_pem and not existing_request.issued_certificate_downloaded_at:
                    messages.success(request, 'This device is approved. Download your client certificate to complete enrollment.')
                    if not request.user.is_authenticated:
                        return redirect('/login/?next=/admin/device/request-authorization/')
                else:
                    messages.success(request, 'This device is already authorized.')
                    if request.user.is_authenticated:
                        return redirect('armguard_admin:dashboard')
                    return redirect('/login/?next=/admin/')
            else:
                stale_approved_request = existing_request
                existing_request = None
                messages.warning(request, 'Previous approval is no longer active. Please submit a new authorization request.')
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        device_name = request.POST.get('device_name', '')
        csr_pem = request.POST.get('csr_pem', '').strip()
        
        if not reason or not device_name:
            messages.error(request, 'Please provide both device name and reason.')
        elif csr_pem and 'BEGIN CERTIFICATE REQUEST' not in csr_pem:
            messages.error(request, 'CSR must be a valid PEM block starting with BEGIN CERTIFICATE REQUEST.')
        else:
            try:
                if stale_approved_request:
                    stale_approved_request.status = 'pending'
                    stale_approved_request.reviewed_by = None
                    stale_approved_request.reviewed_at = None
                    stale_approved_request.review_notes = ''
                    stale_approved_request.requested_by = request.user
                    stale_approved_request.reason = reason
                    stale_approved_request.device_name = device_name
                    stale_approved_request.hostname = device_name
                    stale_approved_request.ip_address = ip_address
                    stale_approved_request.user_agent = user_agent
                    stale_approved_request.csr_pem = csr_pem
                    stale_approved_request.issued_certificate_pem = ''
                    stale_approved_request.issued_certificate_serial = ''
                    stale_approved_request.issued_certificate_issued_at = None
                    stale_approved_request.issued_certificate_downloaded_at = None
                    stale_approved_request.save()
                else:
                    # Create authorization request
                    DeviceAuthorizationRequest.objects.create(
                        device_fingerprint=device_fingerprint,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        hostname=device_name,
                        requested_by=request.user,
                        reason=reason,
                        device_name=device_name,
                        csr_pem=csr_pem,
                    )
            except DatabaseError:
                logger.exception("Database error while creating device authorization request")
                messages.error(
                    request,
                    'Could not submit request because device authorization database is not ready. Please contact administrator.'
                )
                return redirect('armguard_admin:request_device_authorization')
            
            if csr_pem:
                messages.success(request, 'Device authorization request with CSR submitted successfully. Certificate will be issued automatically upon approval.')
            else:
                messages.success(request, 'Device authorization request submitted successfully. You can upload CSR for automated certificate issuance.')
            return redirect('armguard_admin:dashboard')
    
    context = {
        'device_fingerprint': device_fingerprint[:16] + '...',
        'ip_address': ip_address,
        'existing_request': existing_request,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'admin/request_device_auth.html', context)


@login_required
@user_passes_test(is_superuser)
def manage_device_requests(request):
    """
    View and manage device authorization requests (Superuser only)
    """
    from .models import DeviceAuthorizationRequest
    
    status_filter = request.GET.get('status', 'pending')
    
    requests_qs = DeviceAuthorizationRequest.objects.all()
    if status_filter and status_filter != 'all':
        requests_qs = requests_qs.filter(status=status_filter)

    pending_count = DeviceAuthorizationRequest.objects.filter(status='pending').count()
    approved_count = DeviceAuthorizationRequest.objects.filter(status='approved').count()
    rejected_count = DeviceAuthorizationRequest.objects.filter(status='rejected').count()
    
    context = {
        'device_requests': requests_qs,
        'requests': requests_qs,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    }
    return render(request, 'admin/manage_device_requests.html', context)


@login_required
@user_passes_test(is_superuser)
def approve_device_request(request, request_id):
    """Approve a device authorization request"""
    from .models import DeviceAuthorizationRequest
    
    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id)
    
    if request.method == 'POST':
        device_name = request.POST.get('device_name', auth_request.device_name)
        security_level = request.POST.get('security_level', 'STANDARD')
        notes = request.POST.get('notes', '')

        try:
            auth_request.approve(request.user, device_name, security_level, notes)
        except ValueError as cert_error:
            logger.exception("Certificate issuance failed for device request %s", auth_request.id)
            messages.error(request, f'Could not approve request due to certificate issuance error: {cert_error}')
            return render(request, 'admin/approve_device_request.html', {'auth_request': auth_request})
        except DatabaseError:
            logger.exception("Database error while approving device request %s", auth_request.id)
            messages.error(request, 'Database error occurred while approving the request.')
            return render(request, 'admin/approve_device_request.html', {'auth_request': auth_request})

        if auth_request.issued_certificate_pem:
            messages.success(request, f'Device "{device_name}" approved and certificate issued automatically.')
        else:
            messages.success(request, f'Device "{device_name}" has been authorized successfully.')
        return redirect('armguard_admin:manage_device_requests')
    
    context = {
        'auth_request': auth_request,
    }
    return render(request, 'admin/approve_device_request.html', context)


@login_required
@user_passes_test(is_superuser)
def reject_device_request(request, request_id):
    """Reject a device authorization request"""
    from .models import DeviceAuthorizationRequest
    
    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id)
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        auth_request.reject(request.user, notes)
        
        messages.warning(request, 'Device authorization request has been rejected.')
        return redirect('armguard_admin:manage_device_requests')
    
    context = {
        'auth_request': auth_request,
    }
    return render(request, 'admin/reject_device_request.html', context)


@login_required
@user_passes_test(is_superuser)
def view_device_request(request, request_id):
    """View details of a device authorization request."""
    from .models import DeviceAuthorizationRequest

    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id)
    context = {
        'auth_request': auth_request,
    }
    return render(request, 'admin/view_device_request.html', context)


@login_required
@user_passes_test(is_superuser)
def edit_approved_device_request(request, request_id):
    """Edit an approved device authorization request and re-sync authorized device config."""
    from .models import DeviceAuthorizationRequest
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware

    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id, status='approved')

    if request.method == 'POST':
        device_name = request.POST.get('device_name', auth_request.device_name).strip()
        security_level = request.POST.get('security_level', auth_request.security_level).strip()
        notes = request.POST.get('notes', auth_request.review_notes).strip()

        if not device_name:
            messages.error(request, 'Device name is required.')
        else:
            auth_request.device_name = device_name
            auth_request.security_level = security_level
            auth_request.review_notes = notes
            auth_request.save(update_fields=['device_name', 'security_level', 'review_notes'])

            middleware = DeviceAuthorizationMiddleware(lambda req: None)
            middleware.load_authorized_devices()
            middleware.authorize_device(
                device_fingerprint=auth_request.device_fingerprint,
                device_name=auth_request.device_name,
                ip_address=auth_request.ip_address,
                description=f"Requested by {auth_request.requested_by.username}: {auth_request.reason}",
                can_transact=auth_request.can_transact,
                security_level=auth_request.security_level,
                roles=[],
                max_daily_transactions=auth_request.max_daily_transactions
            )

            messages.success(request, f'Device request "{device_name}" updated successfully.')
            return redirect('armguard_admin:manage_device_requests')

    context = {
        'auth_request': auth_request,
    }
    return render(request, 'admin/edit_device_request.html', context)


@login_required
@user_passes_test(is_superuser)
@require_POST
def delete_device_request(request, request_id):
    """Delete a device authorization request (and revoke from authorized devices if approved)."""
    from .models import DeviceAuthorizationRequest
    from core.middleware.device_authorization import DeviceAuthorizationMiddleware

    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id)
    request_label = auth_request.device_name or auth_request.hostname or auth_request.device_fingerprint[:8]
    was_approved = auth_request.status == 'approved'
    device_fingerprint = auth_request.device_fingerprint

    auth_request.delete()

    if was_approved:
        middleware = DeviceAuthorizationMiddleware(lambda req: None)
        middleware.load_authorized_devices()
        middleware.revoke_device(device_fingerprint, reason='Deleted by admin from approved requests')

    messages.success(request, f'Device request "{request_label}" deleted successfully.')
    return redirect('armguard_admin:manage_device_requests')


@login_required
def download_device_certificate(request, request_id):
    """Allow requester (or superuser) to download issued client certificate once."""
    from .models import DeviceAuthorizationRequest

    auth_request = get_object_or_404(DeviceAuthorizationRequest, id=request_id, status='approved')

    if not (request.user.is_superuser or auth_request.requested_by_id == request.user.id):
        messages.error(request, 'You do not have permission to download this certificate.')
        return redirect('armguard_admin:dashboard')

    if not auth_request.issued_certificate_pem:
        messages.error(request, 'No issued certificate is available for this request.')
        return redirect('armguard_admin:request_device_authorization')

    if auth_request.issued_certificate_downloaded_at and not request.user.is_superuser:
        messages.warning(request, 'Certificate bundle has already been downloaded. Contact administrator for re-issue.')
        return redirect('armguard_admin:dashboard')

    bundle_parts = [auth_request.issued_certificate_pem.strip()]
    ca_cert_path = Path(getattr(settings, 'MTLS_CLIENT_CA_CERT_PATH', ''))
    if ca_cert_path.exists():
        bundle_parts.append(ca_cert_path.read_text(encoding='utf-8').strip())

    bundle_content = "\n\n".join(part for part in bundle_parts if part) + "\n"
    response = HttpResponse(bundle_content, content_type='application/x-pem-file')
    response['Content-Disposition'] = f'attachment; filename="armguard-device-{auth_request.id}.pem"'

    if not auth_request.issued_certificate_downloaded_at:
        auth_request.issued_certificate_downloaded_at = timezone.now()
        auth_request.save(update_fields=['issued_certificate_downloaded_at'])

    return response


@login_required
@user_passes_test(is_superuser)
@unrestricted_admin_required
def delete_user(request, user_id):
    """Delete user with audit logging (Superuser only)"""
    from .models import AuditLog, DeletedRecord
    import json
    
    user_obj = get_object_or_404(User, id=user_id)
    
    # Prevent self-deletion
    if user_obj == request.user:
        messages.error(request, 'Cannot delete your own account.')
        return redirect('armguard_admin:user_management')
    
    # Prevent deletion of last superuser
    if user_obj.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
        messages.error(request, 'Cannot delete the last superuser account.')
        return redirect('armguard_admin:user_management')
    
    if request.method == 'POST':
        try:
            # Collect all user data before deletion
            user_data = {
                'id': user_obj.id,
                'username': user_obj.username,
                'email': user_obj.email,
                'first_name': user_obj.first_name,
                'last_name': user_obj.last_name,
                'is_active': user_obj.is_active,
                'is_staff': user_obj.is_staff,
                'is_superuser': user_obj.is_superuser,
                'date_joined': user_obj.date_joined.isoformat(),
                'last_login': user_obj.last_login.isoformat() if user_obj.last_login else None,
            }
            
            # Check for linked personnel
            linked_personnel = None
            if hasattr(user_obj, 'personnel'):
                personnel = user_obj.personnel
                linked_personnel = {
                    'personnel_id': personnel.id,
                    'firstname': personnel.firstname,
                    'surname': personnel.surname,
                    'rank': personnel.rank,
                    'group': personnel.group,
                    'serial': personnel.serial,
                }
                user_data['linked_personnel'] = linked_personnel
            
            # Get deletion reason from form
            reason = request.POST.get('reason', 'No reason provided')
            
            # Create deleted record entry
            DeletedRecord.objects.create(
                deleted_by=request.user,
                model_name='User',
                record_id=user_obj.id,
                record_data=user_data,
                reason=reason
            )
            
            # Create audit log entry
            AuditLog.objects.create(
                performed_by=request.user,
                action='DELETE',
                target_model='User',
                target_id=user_obj.id,
                target_name=user_obj.username,
                description=f'Deleted user account: {user_obj.username}',
                changes={'deleted_data': user_data, 'reason': reason},
                ip_address=request.META.get('REMOTE_ADDR', ''),
            )
            
            username = user_obj.username
            
            # Soft delete linked personnel BEFORE deleting user (keeps record, deactivates QR)
            personnel_to_soft_delete = None
            if hasattr(user_obj, 'personnel') and user_obj.personnel:
                personnel_to_soft_delete = user_obj.personnel
            
            # Delete user (this will set personnel.user to NULL due to SET_NULL)
            user_obj.delete()
            
            # Now soft delete the personnel
            if personnel_to_soft_delete:
                personnel_to_soft_delete.soft_delete()
                messages.success(request, f'User "{username}" has been successfully deleted. Linked personnel record archived (kept for reference, QR deactivated).')
            else:
                messages.success(request, f'User "{username}" has been successfully deleted.')
            
            return redirect('armguard_admin:user_management')
            
        except DatabaseError:
            logger.exception("Database error deleting user %s by %s", user_obj.id, request.user.username)
            messages.error(request, 'Error deleting user. Please try again.')
            return redirect('armguard_admin:user_management')
    
    # GET request - show confirmation page
    context = {
        'user_to_delete': user_obj,
        'linked_personnel': None,
    }
    
    # Check for linked personnel
    if hasattr(user_obj, 'personnel'):
        context['linked_personnel'] = user_obj.personnel
    
    return render(request, 'admin/delete_user_confirm.html', context)


@login_required
@user_passes_test(is_admin_user)
@require_POST
def toggle_user_status(request, user_id):
    """Toggle user active status (AJAX endpoint)"""
    try:
        user_obj = get_object_or_404(User, id=user_id)
        
        # Prevent deactivating own account
        if user_obj == request.user:
            return JsonResponse({'success': False, 'message': 'Cannot deactivate your own account.'})
        
        user_obj.is_active = not user_obj.is_active
        user_obj.save()
        
        status = 'activated' if user_obj.is_active else 'deactivated'
        return JsonResponse({
            'success': True, 
            'message': f'User "{user_obj.username}" {status} successfully.',
            'is_active': user_obj.is_active
        })
        
    except DatabaseError:
        logger.exception("Database error toggling status for user %s", user_id)
        return JsonResponse({'success': False, 'message': 'Error updating user status. Please try again.'})


@login_required
@user_passes_test(is_admin_user)
def link_user_personnel(request):
    """Link existing users with existing personnel"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        personnel_id = request.POST.get('personnel_id')
        
        if user_id and personnel_id:
            try:
                with transaction.atomic():
                    user = get_object_or_404(User, id=user_id)
                    personnel = get_object_or_404(Personnel, id=personnel_id)
                    
                    # Check if personnel is already linked
                    if personnel.user:
                        messages.error(request, f'Personnel "{personnel.rank} {personnel.surname}" is already linked to user "{personnel.user.username}".')
                    else:
                        personnel.user = user
                        personnel.save()
                        messages.success(request, f'User "{user.username}" linked to personnel "{personnel.rank} {personnel.surname}" successfully.')
                        
            except DatabaseError:
                logger.exception("Database error linking user %s to personnel %s", user_id, personnel_id)
                messages.error(request, 'Error linking user and personnel. Please try again.')
        else:
            messages.error(request, 'Please select both user and personnel to link.')
        
        return redirect('armguard_admin:user_management')
    
    # GET request - show linking interface
    unlinked_users = User.objects.filter(personnel__isnull=True)
    unlinked_personnel = Personnel.objects.filter(user__isnull=True)
    
    context = {
        'unlinked_users': unlinked_users,
        'unlinked_personnel': unlinked_personnel,
    }
    return render(request, 'admin/link_user_personnel.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
@unrestricted_admin_required
def registration(request):
    """Main registration form - uses UniversalForm"""
    # Check if user is armorer (limited permissions)
    user_is_armorer = request.user.groups.filter(name='Armorer').exists() and not request.user.is_superuser and not request.user.groups.filter(name='Admin').exists()
    
    if request.method == 'POST':
        # Restrict armorers to personnel-only registration
        if user_is_armorer:
            data = request.POST.copy()
            operation_type = data.get('operation_type', '')
            # Only allow personnel-only operations for armorers
            if operation_type not in ['create_personnel_only']:
                messages.error(request, 'Armorers can only register personnel. Please contact an administrator for user account registration.')
                form = UniversalForm(initial={'operation_type': 'create_personnel_only'})
                context = {
                    'form': form,
                    'is_edit': False,
                    'page_title': 'Registration Form',
                    'submit_text': 'Register',
                    'user_is_armorer': user_is_armorer,
                }
                return render(request, 'admin/universal_form.html', context)
        
        form = UniversalForm(request.POST, request.FILES, request_user=request.user, request=request)
        if form.is_valid():
            try:
                with transaction.atomic():
                    user, personnel = form.save()
                    
                    # Generate single personnel QR code
                    qr_code = None
                    
                    if personnel:
                        # Generate personnel QR code (includes user link if exists)
                        # Use standard QR generator for consistent gray-on-black styling
                        from utils.qr_generator import generate_qr_code_to_buffer
                        user_info = f":{user.username}" if user else ""
                        personnel_data = f"PERSONNEL:{personnel.id}:{personnel.rank} {personnel.surname}, {personnel.firstname}:{personnel.serial}{user_info}"
                        
                        buffer_personnel = generate_qr_code_to_buffer(personnel_data, size=600)
                        qr_code = base64.b64encode(buffer_personnel.getvalue()).decode()
                    
                    # Success message based on what was created
                    operation_type = form.cleaned_data['operation_type']
                    if operation_type == 'create_personnel_only':
                        messages.success(request, f'Personnel record for "{personnel.firstname} {personnel.surname}" created successfully!')
                    elif operation_type == 'create_user_with_personnel':
                        messages.success(request, f'User "{user.username}" and personnel "{personnel.firstname} {personnel.surname}" created successfully!')
                    
                    # Store QR code in session for display
                    request.session['qr_code'] = qr_code
                    request.session['personnel_name'] = f"{personnel.rank} {personnel.surname}, {personnel.firstname}" if personnel else None
                    
                    return redirect('armguard_admin:registration_success')
                    
            except (DatabaseError, ValueError):
                logger.exception("Registration failed for user %s", request.user.username)
                messages.error(request, 'Error during registration. Please try again.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Set initial operation type based on user role
        if user_is_armorer:
            form = UniversalForm(initial={'operation_type': 'create_personnel_only'}, request_user=request.user, request=request)
        else:
            form = UniversalForm(initial={'operation_type': 'create_user_with_personnel'}, request_user=request.user, request=request)
    
    context = {
        'form': form,
        'is_edit': False,
        'page_title': 'Registration Form',
        'submit_text': 'Register',
        'user_is_armorer': user_is_armorer,
    }
    return render(request, 'admin/universal_form.html', context)


@login_required
@user_passes_test(is_superuser)
def audit_logs(request):
    """View audit logs and deleted records (Superuser only)"""
    from .models import AuditLog, DeletedRecord
    from django.db.models import Q
    
    # Get filter parameters
    action_filter = request.GET.get('action', '')
    search_query = request.GET.get('search', '')
    
    # Get audit logs
    logs = AuditLog.objects.select_related('performed_by').all()
    
    if action_filter:
        logs = logs.filter(action=action_filter)
    
    if search_query:
        logs = logs.filter(
            Q(target_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(performed_by__username__icontains=search_query)
        )
    
    logs = logs.order_by('-timestamp')[:100]  # Last 100 entries
    
    # Get deleted records
    deleted_records = DeletedRecord.objects.select_related('deleted_by').order_by('-deleted_at')[:50]
    
    context = {
        'audit_logs': logs,
        'deleted_records': deleted_records,
        'action_filter': action_filter,
        'search_query': search_query,
        'action_choices': AuditLog.ACTION_CHOICES,
    }
    
    return render(request, 'admin/audit_logs.html', context)


@login_required
@user_passes_test(is_admin_user)
@unrestricted_admin_required
def edit_item(request, item_id):
    """Edit inventory item details - Admin only"""
    from .forms import ItemEditForm
    from .models import AuditLog
    
    item = get_object_or_404(Item, pk=item_id)
    
    if request.method == 'POST':
        form = ItemEditForm(request.POST, instance=item)
        if form.is_valid():
            try:
                # Store old values for audit
                old_values = {
                    'item_type': item.item_type,
                    'serial': item.serial,
                    'condition': item.condition,
                    'status': item.status,
                }
                
                # Save updated item
                updated_item = form.save()
                
                # Log the changes
                changes = []
                for field, old_value in old_values.items():
                    new_value = getattr(updated_item, field)
                    if old_value != new_value:
                        changes.append(f"{field}: {old_value} → {new_value}")
                
                if changes:
                    AuditLog.objects.create(
                        action='ITEM_EDIT',
                        target_model='Item',
                        target_id=str(updated_item.id),
                        target_name=f"{updated_item.item_type} - {updated_item.serial}",
                        description=f"Updated item: {', '.join(changes)}",
                        performed_by=request.user,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                    )
                
                messages.success(request, f'Item "{updated_item.item_type} - {updated_item.serial}" updated successfully!')
                return redirect('inventory:item_detail', pk=updated_item.pk)
                
            except DatabaseError:
                logger.exception("Database error updating item %s by %s", item.id, request.user.username)
                messages.error(request, 'Error updating item. Please try again.')
    else:
        form = ItemEditForm(instance=item)
    
    context = {
        'form': form,
        'item': item,
        'is_edit': True,
    }
    return render(request, 'admin/edit_item.html', context)


@login_required
@user_passes_test(is_admin_user)
def delete_item(request, item_id):
    """Delete inventory item with audit logging - Admin/Superuser only"""
    from .models import AuditLog, DeletedRecord
    import json
    
    item = get_object_or_404(Item, pk=item_id)
    
    # Check if item is issued
    if item.status == Item.STATUS_ISSUED:
        messages.error(request, 'Cannot delete an issued item. Please return the item first.')
        return redirect('inventory:item_detail', pk=item_id)
    
    if request.method == 'POST':
        try:
            # Store item details before deletion
            item_data = {
                'id': item.id,
                'item_type': item.item_type,
                'serial': item.serial,
                'description': item.description,
                'condition': item.condition,
                'status': item.status,
                'registration_date': str(item.registration_date),
            }
            
            item_name = f"{item.item_type} - {item.serial}"
            item_id_str = str(item.id)
            
            # Create deleted record
            DeletedRecord.objects.create(
                model_name='Item',
                record_id=item_id_str,
                record_name=item_name,
                record_data=item_data,
                deleted_by=request.user,
                reason=request.POST.get('reason', ''),
                deletion_reason=request.POST.get('reason', '')
            )
            
            # Create audit log
            AuditLog.objects.create(
                action='ITEM_DELETE',
                target_model='Item',
                target_id=item_id_str,
                target_name=item_name,
                description=f"Deleted item: {item_name}. Reason: {request.POST.get('reason', 'Not specified')}",
                performed_by=request.user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            # Delete the item (signal will handle QR code cleanup)
            item.delete()
            
            messages.success(request, f'Item "{item_name}" deleted successfully.')
            return redirect('inventory:item_list')
            
        except DatabaseError:
            logger.exception("Database error deleting item %s by %s", item.id, request.user.username)
            messages.error(request, 'Error deleting item. Please try again.')
            return redirect('inventory:item_detail', pk=item_id)
    
    context = {
        'item': item,
        'item_type': 'Item',
    }
    return render(request, 'admin/delete_item_confirm.html', context)
