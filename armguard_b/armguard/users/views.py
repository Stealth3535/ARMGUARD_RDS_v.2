"""
Users Views
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from django.core.exceptions import PermissionDenied
from .forms import UserRegistrationForm, UserProfileForm
from core.network_decorators import lan_required, read_only_on_wan

logger = logging.getLogger(__name__)


def is_admin_user(user):
    """Check if user is admin or superuser"""
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Admin').exists())


class CustomLoginView(LoginView):
    """Custom login view"""
    template_name = 'users/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('armguard_admin:dashboard')


class CustomLogoutView(LogoutView):
    """Custom logout view"""
    next_page = 'users:login'


class UserRegistrationView(CreateView):
    """
    User registration view - RESTRICTED TO ADMIN USERS ONLY
    
    Security Note: This is a military armory system. Public registration
    is disabled. Only administrators can create user accounts via the
    admin panel's Universal Registration system.
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')
    
    @lan_required
    def dispatch(self, request, *args, **kwargs):
        """Restrict registration to admin users only and require LAN access"""
        # Check if public registration is enabled via settings
        from django.conf import settings
        allow_public_registration = getattr(settings, 'ALLOW_PUBLIC_REGISTRATION', False)
        
        if not allow_public_registration:
            # Only allow if user is admin/superuser
            if not request.user.is_authenticated:
                messages.error(request, 'Public registration is disabled. Please contact an administrator.')
                return redirect('login')
            
            if not is_admin_user(request.user):
                messages.error(request, 'Only administrators can register new users.')
                return redirect('dashboard')
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! You can now log in.')
        logger.info("New user registered: %s by %s", self.object.username, 
                   self.request.user.username if self.request.user.is_authenticated else 'public')
        return response


@login_required
def profile(request):
    """User profile page"""
    return render(request, 'users/profile.html', {'user': request.user})


@login_required
def edit_profile(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('users:profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'users/edit_profile.html', {'form': form})


@login_required
@user_passes_test(is_admin_user, login_url='/')
def user_list(request):
    """List all users - for admin use only"""
    logger.info("User list accessed by: %s", request.user.username)
    users = User.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
def user_detail(request, user_id):
    """User detail view with IDOR protection"""
    user = get_object_or_404(User, id=user_id)
    
    # IDOR Protection: Users can only view their own details unless admin/staff
    if not request.user.is_staff and not request.user.is_superuser:
        if request.user.id != user_id:
            logger.warning(
                "IDOR attempt: User %s tried to access user %s details",
                request.user.username, user_id
            )
            raise PermissionDenied("You don't have permission to view this user's details.")
    
    logger.info("User detail accessed for user_id=%s by %s", user_id, request.user.username)
    return render(request, 'users/user_detail.html', {'user': user})

