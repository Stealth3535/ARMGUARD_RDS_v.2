from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    
    # Profile management
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # User management
    path('list/', views.user_list, name='user_list'),
    path('detail/<int:user_id>/', views.user_detail, name='user_detail'),
]
