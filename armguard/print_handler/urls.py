from django.urls import path
from . import views

app_name = 'print_handler'

urlpatterns = [
    # Personnel ID Card Print Manager (new default)
    path('', views.print_id_cards, name='index'),
    path('id-cards/', views.print_id_cards, name='print_id_cards'),
    path('id-cards/regenerate/<str:personnel_id>/', views.regenerate_id_card, name='regenerate_id_card'),
    path('id-cards/print/', views.print_id_cards_view, name='print_id_cards_view'),
    path('id-cards/image/<str:personnel_id>/<str:side>/', views.serve_id_card_image, name='serve_id_card_image'),
    path('id-cards/diagnostics/', views.id_card_diagnostics, name='id_card_diagnostics'),

    # Legacy QR code printing
    path('qr-codes/', views.print_qr_codes, name='print_qr_codes'),
    path('single/<int:qr_id>/', views.print_single_qr, name='print_single_qr'),

    # Transaction printing
    path('transaction/<int:transaction_id>/', views.print_transaction_form, name='print_transaction_form'),
    path('transaction/<int:transaction_id>/pdf/', views.download_transaction_pdf, name='download_transaction_pdf'),
    path('transaction/<int:transaction_id>/print/', views.print_transaction_pdf, name='print_transaction_pdf'),
    path('transactions/', views.print_transactions, name='print_transactions'),
]
