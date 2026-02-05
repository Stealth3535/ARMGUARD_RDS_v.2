"""
Print Handler Views - Super Simple
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from qr_manager.models import QRCodeImage
from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item
from .print_config import QR_SIZE_MM, CARDS_PER_ROW, CARD_WIDTH_MM, CARD_HEIGHT_MM, FONT_SIZE_ID, FONT_SIZE_NAME, FONT_SIZE_BADGE
from .pdf_filler.form_filler import TransactionFormFiller


def is_admin_or_armorer(user):
    """Check if user is admin, superuser, or armorer - can print QR codes"""
    return user.is_authenticated and (
        user.is_superuser or 
        user.groups.filter(name='Admin').exists() or 
        user.groups.filter(name='Armorer').exists()
    )


@login_required
@user_passes_test(is_admin_or_armorer)
def print_qr_codes(request):
    """Simple QR code printing - only shows valid QR codes with existing records"""
    qr_type = request.GET.get('type', 'all')
    
    # Optimize with select_related to avoid N+1 queries
    personnel_qrcodes = []
    item_qrcodes = []
    
    if qr_type in ['all', 'personnel']:
        # Get all personnel QR codes with active status
        personnel_qr_ids = QRCodeImage.objects.filter(
            qr_type='personnel',
            is_active=True
        ).exclude(qr_image='').values_list('reference_id', flat=True)
        
        # Get active personnel matching these QR codes
        active_personnel = Personnel.objects.filter(
            id__in=personnel_qr_ids,
            deleted_at__isnull=True
        ).values('id', 'firstname', 'surname', 'middle_initial', 'rank')
        
        # Create lookup dict for fast access
        personnel_dict = {p['id']: p for p in active_personnel}
        
        # Build QR code list with names
        for qr in QRCodeImage.objects.filter(reference_id__in=personnel_dict.keys(), qr_type='personnel', is_active=True).exclude(qr_image=''):
            person = personnel_dict.get(qr.reference_id)
            if person:
                mi = f" {person['middle_initial']}." if person['middle_initial'] else ""
                qr.name = f"{person['rank']} {person['firstname']}{mi} {person['surname']}"
                personnel_qrcodes.append(qr)
    
    if qr_type in ['all', 'items']:
        # Get all item QR codes with active status
        item_qr_ids = QRCodeImage.objects.filter(
            qr_type='item',
            is_active=True
        ).exclude(qr_image='').values_list('reference_id', flat=True)
        
        # Get items matching these QR codes
        active_items = Item.objects.filter(
            id__in=item_qr_ids
        ).values('id', 'item_type', 'serial')
        
        # Create lookup dict
        items_dict = {i['id']: i for i in active_items}
        
        # Build QR code list with names
        for qr in QRCodeImage.objects.filter(reference_id__in=items_dict.keys(), qr_type='item', is_active=True).exclude(qr_image=''):
            item = items_dict.get(qr.reference_id)
            if item:
                qr.name = f"{item['item_type']} - {item['serial']}"
                item_qrcodes.append(qr)
    
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
@user_passes_test(is_admin_or_armorer)
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
@user_passes_test(is_admin_or_armorer)
def print_transaction_form(request, transaction_id=None):
    """Print transaction form"""
    transaction = None
    if transaction_id:
        transaction = get_object_or_404(Transaction, id=transaction_id)
    
    context = {
        'transaction': transaction,
    }
    return render(request, 'print_handler/print_transaction_form.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
def print_transactions(request):
    """Print transaction history report"""
    personnel_id = request.GET.get('personnel_id')
    item_id = request.GET.get('item_id')
    
    transactions = Transaction.objects.select_related('personnel', 'item').order_by('-date_time')
    
    # Filter by personnel or item if specified
    if personnel_id:
        try:
            personnel = Personnel.objects.get(id=personnel_id)
            transactions = transactions.filter(personnel=personnel)
        except Personnel.DoesNotExist:
            messages.error(request, 'Personnel not found')
            
    if item_id:
        try:
            item = Item.objects.get(id=item_id)
            transactions = transactions.filter(item=item)
        except Item.DoesNotExist:
            messages.error(request, 'Item not found')
    
    context = {
        'transactions': transactions,
        'personnel_id': personnel_id,
        'item_id': item_id,
    }
    return render(request, 'print_handler/print_transactions.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
def download_transaction_pdf(request, transaction_id):
    """Download filled PDF form for a transaction with print preview"""
    import os
    from django.conf import settings
    
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    try:
        # Fill the PDF form
        form_filler = TransactionFormFiller()
        filled_pdf = form_filler.fill_transaction_form(transaction)
        
        # Save to media folder for review
        filename = f"Transaction_{transaction.id}_{transaction.date_time.strftime('%Y%m%d_%H%M%S')}.pdf"
        output_dir = os.path.join(settings.MEDIA_ROOT, 'transaction_forms')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, filename)
        
        # Write PDF to file
        with open(output_path, 'wb') as f:
            f.write(filled_pdf.read())
        
        # Read back for display
        with open(output_path, 'rb') as f:
            pdf_content = f.read()
            response = HttpResponse(pdf_content, content_type='application/pdf')
            # Use inline to display in browser instead of download
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            # Add header to suggest legal paper size
            response['X-Print-Page-Size'] = 'legal'
            
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('transactions:detail', pk=transaction_id)


@login_required
@user_passes_test(is_admin_or_armorer)
def print_transaction_pdf(request, transaction_id):
    """Show print-ready page for transaction PDF with legal paper size"""
    transaction = get_object_or_404(Transaction, id=transaction_id)
    pdf_url = f'/print/transaction/{transaction_id}/pdf/'
    
    return render(request, 'print_handler/pdf_print.html', {
        'transaction': transaction,
        'pdf_url': pdf_url
    })