"""
Print Handler Views - Super Simple
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from qr_manager.models import QRCodeImage
from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item
from .print_config import QR_SIZE_MM, CARDS_PER_ROW, CARD_WIDTH_MM, CARD_HEIGHT_MM, FONT_SIZE_ID, FONT_SIZE_NAME, FONT_SIZE_BADGE


@login_required
def print_qr_codes(request):
    """Simple QR code printing"""
    qr_type = request.GET.get('type', 'all')
    
    personnel_qrcodes = QRCodeImage.objects.filter(qr_type='personnel') if qr_type in ['all', 'personnel'] else QRCodeImage.objects.none()
    item_qrcodes = QRCodeImage.objects.filter(qr_type='item') if qr_type in ['all', 'items'] else QRCodeImage.objects.none()
    
    # Add names to QR codes
    for qr in personnel_qrcodes:
        try:
            person = Personnel.objects.get(id=qr.reference_id)
            qr.name = person.get_full_name()
        except Personnel.DoesNotExist:
            qr.name = "Unknown"
    
    for qr in item_qrcodes:
        try:
            item = Item.objects.get(id=qr.reference_id)
            qr.name = f"{item.item_type} - {item.serial}"
        except Item.DoesNotExist:
            qr.name = "Unknown"
    
    context = {
        'personnel_qrcodes': personnel_qrcodes,
        'item_qrcodes': item_qrcodes,
        'qr_type': qr_type,
        'qr_size_mm': QR_SIZE_MM,
        'cards_per_row': CARDS_PER_ROW,
        'card_width_mm': CARD_WIDTH_MM,
        'card_height_mm': CARD_HEIGHT_MM,
        'font_size_id': FONT_SIZE_ID,
        'font_size_name': FONT_SIZE_NAME,
        'font_size_badge': FONT_SIZE_BADGE,
    }
    return render(request, 'print_handler/print_qr_codes.html', context)


@login_required
def print_single_qr(request, qr_id):
    """Print one QR code"""
    qr_code = get_object_or_404(QRCodeImage, id=qr_id)
    
    context = {
        'qr_code': qr_code,
        'qr_size_mm': QR_SIZE_MM,
        'card_width_mm': CARD_WIDTH_MM,
        'card_height_mm': CARD_HEIGHT_MM,
        'font_size_id': FONT_SIZE_ID,
        'font_size_name': FONT_SIZE_NAME,
        'font_size_badge': FONT_SIZE_BADGE,
    }
    return render(request, 'print_handler/print_single_qr.html', context)


@login_required
def print_transaction_form(request, transaction_id=None):
    """Print transaction form"""
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'print_handler/print_transaction_form.html', context)