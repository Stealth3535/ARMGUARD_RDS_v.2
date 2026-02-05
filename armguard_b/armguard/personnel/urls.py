"""
Personnel URL Configuration - Display Only
Note: Personnel creation/editing is now handled by admin.views.UniversalRegistrationForm
"""
from django.urls import path
from . import views

app_name = 'personnel'

urlpatterns = [
    # Personnel display views
    path('', views.personnel_profile_list, name='personnel_profile_list'),
    path('<str:pk>/', views.personnel_profile_detail, name='personnel_profile_detail'),
    
    # API endpoints
    path('api/search/', views.personnel_search_api, name='personnel_search_api'),
]

