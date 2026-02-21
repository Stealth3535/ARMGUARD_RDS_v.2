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
    
    # Personnel Management
    path('personnel/<str:personnel_id>/edit/', views.edit_personnel, name='edit_personnel'),
    path('personnel/<str:personnel_id>/delete/', views.delete_personnel, name='delete_personnel'),
    
    # Legacy Registration URLs (redirects to universal registration)
    path('users/create/', views.create_user, name='create_user'),
    path('register/armorer/', views.register_armorer, name='register_armorer'),
    path('register/personnel/', views.register_personnel, name='register_personnel'),
    
    # Item Management
    path('register/item/', views.register_item, name='register_item'),
    path('items/<str:item_id>/edit/', views.edit_item, name='edit_item'),
    path('items/<str:item_id>/delete/', views.delete_item, name='delete_item'),
    
    # System Settings
    path('settings/', views.system_settings, name='system_settings'),
    
    # Device Authorization
    path('device/request-authorization/', views.request_device_authorization, name='request_device_authorization'),
    path('device/toggle-auth/', views.toggle_device_auth, name='toggle_device_auth'),
    path('device/requests/', views.manage_device_requests, name='manage_device_requests'),
    path('device/requests/<int:request_id>/view/', views.view_device_request, name='view_device_request'),
    path('device/requests/<int:request_id>/edit/', views.edit_approved_device_request, name='edit_device_request'),
    path('device/requests/<int:request_id>/delete/', views.delete_device_request, name='delete_device_request'),
    path('device/requests/<int:request_id>/approve/', views.approve_device_request, name='approve_device_request'),
    path('device/requests/<int:request_id>/reject/', views.reject_device_request, name='reject_device_request'),
    path('device/requests/<int:request_id>/attach-csr/', views.attach_csr_to_device, name='attach_csr_to_device'),
    path('device/requests/<int:request_id>/certificate/', views.download_device_certificate, name='download_device_certificate'),
    
    # Audit Logs
    path('audit-logs/', views.audit_logs, name='audit_logs'),
]
