"""
Admin URLs - Centralized Administration and Management
"""
from django.urls import path
from . import views

app_name = 'armguard_admin'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Registration - Main Registration System
    path('register/', views.registration, name='registration'),
    path('register/success/', views.registration_success, name='registration_success'),
    
    # Traditional Personnel Registration
    path('register/personnel-form/', views.personnel_registration, name='personnel_registration'),
    path('register/personnel-success/<str:pk>/', views.personnel_registration_success, name='personnel_registration_success'),
    
    # User Management
    path('users/', views.user_management, name='user_management'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/link-personnel/', views.link_user_personnel, name='link_user_personnel'),
    
    # Legacy Registration URLs (redirects to universal registration)
    path('users/create/', views.create_user, name='create_user'),
    path('register/armorer/', views.register_armorer, name='register_armorer'),
    path('register/personnel/', views.register_personnel, name='register_personnel'),
    
    # Item Registration (separate from user/personnel)
    path('register/item/', views.register_item, name='register_item'),
    
    # System Settings
    path('settings/', views.system_settings, name='system_settings'),
]
