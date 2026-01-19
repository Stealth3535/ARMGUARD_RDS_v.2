"""
URL configuration for ArmGuard project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from decouple import config
from . import views
from . import api_views

# Admin URL obfuscation - use environment variable
ADMIN_URL = config('DJANGO_ADMIN_URL', default='superadmin')

urlpatterns = [
    # Django Admin (Superuser only) - Obfuscated URL
    path(f'{ADMIN_URL}/', admin.site.urls),
    
    # Custom Admin (Staff users)
    path('admin/', include('admin.urls', namespace='armguard_admin')),
    
    # Authentication
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # API endpoints
    path('api/personnel/<str:personnel_id>/', api_views.get_personnel, name='api_personnel'),
    path('api/items/<str:item_id>/', api_views.get_item, name='api_item'),
    path('api/transactions/', api_views.create_transaction, name='api_create_transaction'),
    
    # App URLs
    path('personnel/', include('personnel.urls')),
    path('inventory/', include('inventory.urls')),
    path('transactions/', include('transactions.urls')),
    path('qr/', include('qr_manager.urls')),
    path('users/', include('users.urls')),
    path('print/', include('print_handler.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
