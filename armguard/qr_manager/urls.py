from django.urls import path
from . import views

app_name = 'qr_manager'

urlpatterns = [
    path('personnel/', views.personnel_qr_codes, name='personnel_qr_codes'),
    path('item/', views.item_qr_codes, name='item_qr_codes'),
]
