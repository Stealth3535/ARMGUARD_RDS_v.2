from django.urls import path
from . import views

app_name = 'transactions'

urlpatterns = [
    # Main transaction list with inline form
    path('', views.TransactionListView.as_view(), name='list'),
    path('<int:pk>/', views.TransactionDetailView.as_view(), name='detail'),
    
    # Legacy URLs
    path('personnel/', views.personnel_transactions, name='personnel_transactions'),
    path('item/', views.item_transactions, name='item_transactions'),
    
    # QR Scanner features
    path('qr-scanner/', views.qr_transaction_scanner, name='qr_scanner'),
    path('verify-qr/', views.verify_qr_code, name='verify_qr'),
    path('create-qr-transaction/', views.create_qr_transaction, name='create_qr_transaction'),
    path('lookup/', views.lookup_transactions, name='lookup_transactions'),
]
