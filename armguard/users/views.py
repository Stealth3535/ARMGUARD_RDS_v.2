"""
Users Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView
from .forms import UserRegistrationForm, UserProfileForm


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
    """User registration view"""
    model = User
    form_class = UserRegistrationForm
    template_name = 'users/register.html'
    success_url = reverse_lazy('users:login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Account created successfully! You can now log in.')
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


def user_list(request):
    """List all users - for admin use"""
    users = User.objects.all().order_by('username')
    return render(request, 'users/user_list.html', {'users': users})


def user_detail(request, user_id):
    """User detail view"""
    user = User.objects.get(id=user_id)
    return render(request, 'users/user_detail.html', {'user': user})

