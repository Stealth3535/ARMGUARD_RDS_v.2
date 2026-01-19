from django.urls import path
from . import views

app_name = 'print_handler'

urlpatterns = [
    path('', views.print_qr_codes, name='index'),  # Main page
    path('qr-codes/', views.print_qr_codes, name='print_qr_codes'),
    path('single/<int:qr_id>/', views.print_single_qr, name='print_single_qr'),
    path('transaction/<int:transaction_id>/', views.print_transaction_form, name='print_transaction_form'),
]
