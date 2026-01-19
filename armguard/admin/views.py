"""
Admin Views - System Administration and Management
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.db.models import Q, Count
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from inventory.models import Item
from personnel.models import Personnel
from transactions.models import Transaction
from users.models import UserProfile
import qrcode
from io import BytesIO
import base64

from .forms import (
    UniversalRegistrationForm, AdminUserForm, ArmorerRegistrationForm, 
    PersonnelRegistrationForm, ItemRegistrationForm, SystemSettingsForm
)


def is_admin_user(user):
    """Check if user is admin or superuser - only they can register users"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Admin').exists())


@login_required
@user_passes_test(is_admin_user)
def dashboard(request):
    """Admin dashboard with system overview and centralized registration access"""
    # Get statistics
    total_items = Item.objects.count()
    total_personnel = Personnel.objects.count()
    total_transactions = Transaction.objects.count()
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    
    # Recent transactions
    recent_transactions = Transaction.objects.select_related(
        'personnel', 'item'
    ).order_by('-date_time')[:10]
    
    # Items by type
    items_by_type = Item.objects.values('item_type').annotate(count=Count('id'))
    
    # Users by role
    admins_count = User.objects.filter(groups__name='Admin').count()
    superusers_count = User.objects.filter(is_superuser=True).count()
    armorers_count = User.objects.filter(groups__name='Armorer').count()
    
    # Unlinked personnel count
    unlinked_personnel = Personnel.objects.filter(user__isnull=True).count()
    
    context = {
        'total_items': total_items,
        'total_personnel': total_personnel,
        'total_transactions': total_transactions,
        'total_users': total_users,
        'active_users': active_users,
        'admins_count': admins_count,
        'superusers_count': superusers_count,
        'armorers_count': armorers_count,
        'unlinked_personnel': unlinked_personnel,
        'recent_transactions': recent_transactions,
        'items_by_type': items_by_type,
    }
    
    return render(request, 'admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin_user, login_url='/')
def personnel_registration(request):
    """Traditional Personnel Registration Form"""
    if request.method == 'POST':
        form = PersonnelRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            personnel = form.save()
            messages.success(request, f'Personnel {personnel.get_full_name()} has been registered successfully!')
            
            # Generate QR code if not already created
            from qr_manager.models import QRCodeImage
            if not QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_PERSONNEL, reference_id=personnel.id).exists():
                QRCodeImage.objects.create(
                    qr_type=QRCodeImage.TYPE_PERSONNEL,
                    reference_id=personnel.id,
                    data_content=f"Personnel: {personnel.get_full_name()}\nRank: {personnel.rank}\nSerial: {personnel.serial}\nID: {personnel.id}"
                )
            
            return redirect('armguard_admin:personnel_registration_success', pk=personnel.id)
    else:
        form = PersonnelRegistrationForm()
    
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
    except:
        pass
    
    context = {
        'personnel': personnel,
        'qr_code_obj': qr_code_obj,
        'title': 'Registration Successful'
    }
    return render(request, 'admin/personnel_registration_success.html', context)


@login_required
@user_passes_test(is_admin_user)
def universal_registration(request):
    """Universal registration view - The centralized registration system"""
    if request.method == 'POST':
        print(f"DEBUG: Registration POST data: {request.POST}")
        print(f"DEBUG: Registration FILES data: {request.FILES}")
        form = UniversalRegistrationForm(request.POST, request.FILES)
        print(f"DEBUG: Registration form is_valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"DEBUG: Registration form errors: {form.errors}")
        if form.is_valid():
            try:
                with transaction.atomic():
                    user, personnel = form.save()
                    
                    # Generate QR codes if applicable
                    qr_codes = {}
                    
                    if user:
                        # Generate user QR code
                        user_data = f"USER:{user.id}:{user.username}:{user.email}"
                        qr_user = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr_user.add_data(user_data)
                        qr_user.make(fit=True)
                        
                        img_user = qr_user.make_image(fill_color="black", back_color="white")
                        buffer_user = BytesIO()
                        img_user.save(buffer_user, format='PNG')
                        qr_codes['user'] = base64.b64encode(buffer_user.getvalue()).decode()
                    
                    if personnel:
                        # Generate personnel QR code
                        personnel_data = f"PERSONNEL:{personnel.id}:{personnel.rank} {personnel.surname}, {personnel.firstname}:{personnel.serial}"
                        qr_personnel = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr_personnel.add_data(personnel_data)
                        qr_personnel.make(fit=True)
                        
                        img_personnel = qr_personnel.make_image(fill_color="black", back_color="white")
                        buffer_personnel = BytesIO()
                        img_personnel.save(buffer_personnel, format='PNG')
                        qr_codes['personnel'] = base64.b64encode(buffer_personnel.getvalue()).decode()
                    
                    # Success message based on what was created
                    registration_type = form.cleaned_data['registration_type']
                    if registration_type == 'user_only':
                        messages.success(request, f'User account "{user.username}" created successfully with QR code.')
                    elif registration_type == 'personnel_only':
                        messages.success(request, f'Personnel record for "{personnel.rank} {personnel.surname}" created successfully with QR code.')
                    elif registration_type == 'user_with_personnel':
                        messages.success(request, f'User account "{user.username}" and personnel record for "{personnel.rank} {personnel.surname}" created successfully with QR codes.')
                    elif registration_type == 'link_existing':
                        messages.success(request, f'User account "{user.username}" linked to personnel "{personnel.rank} {personnel.surname}" successfully.')
                    
                    # Store QR codes in session for display
                    request.session['qr_codes'] = qr_codes
                    
                    return redirect('armguard_admin:registration_success')
                    
            except Exception as e:
                messages.error(request, f'Error during registration: {str(e)}')
    else:
        form = UniversalRegistrationForm()
    
    return render(request, 'admin/universal_registration.html', {'form': form})


@login_required
@user_passes_test(is_admin_user)
def registration_success(request):
    """Display success page with QR codes"""
    qr_codes = request.session.pop('qr_codes', {})
    return render(request, 'admin/registration_success.html', {'qr_codes': qr_codes})


@login_required
@user_passes_test(is_admin_user)
def user_management(request):
    """User management interface"""
    users = User.objects.select_related('userprofile').prefetch_related('groups').order_by('-date_joined')
    
    # Add personnel linking info
    for user in users:
        try:
            user.personnel = Personnel.objects.get(user=user)
        except Personnel.DoesNotExist:
            user.personnel = None
    
    # Filter options
    role_filter = request.GET.get('role')
    search_query = request.GET.get('search')
    
    if role_filter:
        if role_filter == 'admin':
            users = users.filter(groups__name='Admin')
        elif role_filter == 'superuser':
            users = users.filter(is_superuser=True)
        elif role_filter == 'armorer':
            users = users.filter(groups__name='Armorer')
        elif role_filter == 'regular':
            users = users.filter(is_staff=False, is_superuser=False)
    
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    context = {
        'users': users,
        'user_count': users.count(),
        'admin_count': users.filter(groups__name='Admin').count(),
        'armorer_count': users.filter(groups__name='Armorer').count(),
        'active_count': users.filter(is_active=True).count(),
        'unlinked_personnel': Personnel.objects.filter(user__isnull=True),
        'role_filter': role_filter,
        'search_query': search_query,
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
def edit_user(request, user_id):
    """Edit existing user"""
    edit_user_obj = get_object_or_404(User, id=user_id)
    
    # Prevent non-superusers from editing superusers
    if edit_user_obj.is_superuser and not request.user.is_superuser:
        messages.error(request, 'Only superusers can edit other superusers.')
        return redirect('armguard_admin:user_management')
    
    if request.method == 'POST':
        print(f"DEBUG: POST data: {request.POST}")
        print(f"DEBUG: FILES data: {request.FILES}")
        form = AdminUserForm(request.POST, request.FILES, instance=edit_user_obj)
        print(f"DEBUG: Form is_valid: {form.is_valid()}")
        if not form.is_valid():
            print(f"DEBUG: Form errors: {form.errors}")
        if form.is_valid():
            try:
                with transaction.atomic():
                    user = form.save(commit=False)
                    
                    # Update password if provided
                    new_password = form.cleaned_data.get('password')
                    if new_password:
                        user.set_password(new_password)
                    
                    # Update role-based permissions
                    role = form.cleaned_data['role']
                    user.groups.clear()  # Clear existing groups
                    
                    if role == 'admin':
                        user.is_staff = True
                        user.is_superuser = False
                        admin_group, _ = Group.objects.get_or_create(name='Admin')
                        user.groups.add(admin_group)
                    elif role == 'superuser':
                        user.is_staff = True
                        user.is_superuser = True
                    elif role == 'armorer':
                        user.is_staff = True
                        user.is_superuser = False
                        armorer_group, _ = Group.objects.get_or_create(name='Armorer')
                        user.groups.add(armorer_group)
                    else:
                        user.is_staff = False
                        user.is_superuser = False
                    
                    user.save()
                    
                    # Update or create user profile
                    try:
                        profile = user.userprofile
                    except:
                        # Import UserProfile model to create one if it doesn't exist
                        from users.models import UserProfile
                        profile = UserProfile.objects.create(user=user)
                    
                    profile.department = form.cleaned_data.get('department', '')
                    profile.phone_number = form.cleaned_data.get('phone_number', '')
                    profile.badge_number = form.cleaned_data.get('badge_number', '')
                    profile.is_armorer = (role == 'armorer')
                    

                    # Handle profile picture upload (UserProfile)
                    uploaded_file = form.cleaned_data.get('profile_picture')
                    if uploaded_file:
                        print(f"DEBUG: Processing uploaded file: {uploaded_file.name}, size: {uploaded_file.size}")
                        profile.profile_picture = uploaded_file
                        print(f"DEBUG: Set profile_picture to: {profile.profile_picture}")
                    profile.save()
                    print(f"DEBUG: UserProfile saved, profile_picture: {profile.profile_picture}")

                    # Also update Personnel.picture if user is linked to Personnel
                    try:
                        from personnel.models import Personnel
                        personnel = getattr(user, 'personnel', None)
                        if not personnel:
                            # Try to find Personnel by serial or username, or create if missing
                            personnel = Personnel.objects.filter(serial=user.username).first()
                            if not personnel:
                                # Create a minimal Personnel record if none exists
                                personnel = Personnel.objects.create(
                                    serial=user.username,
                                    surname=user.last_name or 'Unknown',
                                    firstname=user.first_name or 'User',
                                    rank='AM',  # Default rank
                                    office='HAS',  # Default office
                                    tel='+639000000000',  # Default phone
                                    status='ACTIVE',
                                )
                                personnel.user = user
                                personnel.save()
                                print(f"DEBUG: Created new personnel: {personnel.id}")
                            else:
                                personnel.user = user
                                personnel.save()
                                print(f"DEBUG: Linked existing personnel: {personnel.id}")
                        
                        # Save the uploaded image to Personnel.picture
                        if uploaded_file:
                            personnel.picture = uploaded_file
                            personnel.save()
                            print(f"DEBUG: Saved image to personnel {personnel.id}, picture: {personnel.picture}")
                    except Exception as e:
                        print(f"DEBUG: Error updating personnel: {str(e)}")
                        import traceback
                        traceback.print_exc()
                    
                    messages.success(request, f'User \"{user.username}\" updated successfully!')
                    return redirect('armguard_admin:user_management')
                    
            except Exception as e:
                messages.error(request, f'Error updating user: {str(e)}')
        else:
            # Form has validation errors
            messages.error(request, 'Please correct the errors below.')
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # Create form with instance - form will auto-populate from __init__
        form = AdminUserForm(instance=edit_user_obj)
    
    context = {
        'form': form,
        'edit_user': edit_user_obj,
        'is_edit': True,
    }
    return render(request, 'admin/edit_user.html', context)


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
@user_passes_test(is_admin_user)
def register_item(request):
    """Register new inventory item"""
    if request.method == 'POST':
        form = ItemRegistrationForm(request.POST)
        if form.is_valid():
            try:
                item = form.save()
                
                # Generate QR code
                item_data = f"ITEM:{item.id}:{item.item_type}:{item.serial}"
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(item_data)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                qr_code = base64.b64encode(buffer.getvalue()).decode()
                
                messages.success(request, f'Item "{item}" registered successfully with QR code!')
                return render(request, 'admin/register_item.html', {
                    'form': ItemRegistrationForm(),
                    'qr_code': qr_code,
                    'item': item,
                    'success': True
                })
                
            except Exception as e:
                messages.error(request, f'Error registering item: {str(e)}')
    else:
        form = ItemRegistrationForm()
    
    return render(request, 'admin/register_item.html', {'form': form})


@login_required
@user_passes_test(is_admin_user)
def system_settings(request):
    """System configuration settings"""
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
            'session_timeout': getattr(settings, 'SESSION_COOKIE_AGE', 3600) // 60,
        }
        form = SystemSettingsForm(initial=initial_data)
    
    context = {
        'form': form,
        'debug_mode': settings.DEBUG,
        'database_engine': settings.DATABASES['default']['ENGINE'],
    }
    return render(request, 'admin/system_settings.html', context)


@login_required
@user_passes_test(is_admin_user)
@require_POST
def delete_user(request, user_id):
    """Delete user (AJAX endpoint)"""
    try:
        user_obj = get_object_or_404(User, id=user_id)
        
        # Prevent self-deletion
        if user_obj == request.user:
            return JsonResponse({'success': False, 'message': 'Cannot delete your own account.'})
        
        # Prevent deletion of last superuser
        if user_obj.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            return JsonResponse({'success': False, 'message': 'Cannot delete the last superuser account.'})
        
        username = user_obj.username
        user_obj.delete()
        
        return JsonResponse({'success': True, 'message': f'User "{username}" deleted successfully.'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error deleting user: {str(e)}'})


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
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error updating user status: {str(e)}'})


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
                        
            except Exception as e:
                messages.error(request, f'Error linking user and personnel: {str(e)}')
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
@user_passes_test(is_admin_user)
def registration(request):
    """Registration form for all user types"""
    from consolidated_forms import UserRegistrationForm
    from personnel.models import Personnel
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        user_type = request.POST.get('user_type')
        
        if user_type == 'personnel':
            # Create personnel only (no user account)
            try:
                personnel = Personnel.objects.create(
                    surname=request.POST.get('last_name', ''),
                    firstname=request.POST.get('first_name', ''),
                    middle_initial=request.POST.get('middle_initial', ''),
                    rank=request.POST.get('rank', ''),
                    serial=request.POST.get('serial', ''),
                    office=request.POST.get('office', ''),
                    tel=request.POST.get('phone', ''),
                    status=request.POST.get('status', 'ACTIVE'),
                    picture=request.FILES.get('profile_picture') if 'profile_picture' in request.FILES else None
                )
                messages.success(request, f'Personnel {personnel.get_full_name()} has been registered successfully!')
                return redirect('armguard_admin:dashboard')
            except Exception as e:
                messages.error(request, f'Error creating personnel: {str(e)}')
        else:
            # Create user account
            form = UserRegistrationForm(request.POST, request.FILES)
            if form.is_valid():
                user = form.save(commit=True)  # Let the form handle profile picture creation
                
                # Set user permissions based on type
                if user_type == 'admin':
                    user.is_staff = True
                    user.is_superuser = False
                elif user_type == 'armorer':
                    user.is_staff = True
                    user.is_superuser = False
                
                user.save()
                
                # Add user to appropriate groups
                if user_type == 'admin':
                    admin_group, created = Group.objects.get_or_create(name='Administrators')
                    user.groups.add(admin_group)
                elif user_type == 'armorer':
                    armorer_group, created = Group.objects.get_or_create(name='Armorers')
                    user.groups.add(armorer_group)
                
                # Create personnel record if personnel data provided
                rank = request.POST.get('rank')
                serial = request.POST.get('serial')
                if rank or serial:
                    try:
                        personnel = Personnel.objects.create(
                            user=user,
                            surname=user.last_name,
                            firstname=user.first_name,
                            middle_initial=request.POST.get('middle_initial', ''),
                            rank=rank or '',
                            serial=serial or '',
                            office=request.POST.get('office', ''),
                            tel=request.POST.get('phone', ''),
                            status=request.POST.get('status', 'ACTIVE')
                        )
                        # Copy profile picture from user profile to personnel if it exists
                        if hasattr(user, 'userprofile') and user.userprofile.profile_picture:
                            personnel.picture = user.userprofile.profile_picture
                            personnel.save()
                    except Exception as e:
                        messages.warning(request, f'User created but personnel record failed: {str(e)}')
                
                user_type_names = {
                    'admin': 'Administrator',
                    'armorer': 'Armorer',
                    'user': 'User'
                }
                messages.success(request, f'{user_type_names.get(user_type, "User")} "{user.username}" has been registered successfully!')
                return redirect('armguard_admin:dashboard')
    else:
        form = UserRegistrationForm()
    
    context = {
        'form': form,
    }
    return render(request, 'admin/registration.html', context)
