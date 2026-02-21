"""
Print Handler Views - Super Simple
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
import os
from django.conf import settings
from qr_manager.models import QRCodeImage
from transactions.models import Transaction
from personnel.models import Personnel
from inventory.models import Item
from .print_config import QR_SIZE_MM, CARDS_PER_ROW, CARD_WIDTH_MM, CARD_HEIGHT_MM, FONT_SIZE_ID, FONT_SIZE_NAME, FONT_SIZE_BADGE
from .pdf_filler.form_filler import TransactionFormFiller
from django.utils import timezone
from datetime import timedelta


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
                mi = f" {person['middle_initial']}" if person['middle_initial'] else ""
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
    mode = (request.GET.get('mode') or '').strip().lower()
    range_filter = (request.GET.get('range') or '').strip().lower()
    
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

    if mode in {Transaction.MODE_DEFCON, Transaction.MODE_NORMAL}:
        transactions = transactions.filter(transaction_mode=mode)

    range_days = {
        'day': 1,
        'week': 7,
        'month': 30,
    }
    if range_filter in range_days:
        since = timezone.now() - timedelta(days=range_days[range_filter])
        transactions = transactions.filter(date_time__gte=since)

    summary_counts = {
        'defcon_released': transactions.filter(transaction_mode=Transaction.MODE_DEFCON, action=Transaction.ACTION_TAKE).count(),
        'defcon_returned': transactions.filter(transaction_mode=Transaction.MODE_DEFCON, action=Transaction.ACTION_RETURN).count(),
        'normal_released': transactions.filter(transaction_mode=Transaction.MODE_NORMAL, action=Transaction.ACTION_TAKE).count(),
        'normal_returned': transactions.filter(transaction_mode=Transaction.MODE_NORMAL, action=Transaction.ACTION_RETURN).count(),
    }
    
    context = {
        'transactions': transactions,
        'personnel_id': personnel_id,
        'item_id': item_id,
        'selected_mode': mode,
        'selected_range': range_filter,
        'summary_counts': summary_counts,
    }
    return render(request, 'print_handler/print_transactions.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
def download_transaction_pdf(request, transaction_id):
    """Serve the filled PDF form for a transaction (create if doesn't exist)"""
    import os
    from django.conf import settings
    from django.http import FileResponse
    
    transaction = get_object_or_404(Transaction, id=transaction_id)
    
    # Check if filled PDF already exists (from auto-generation during transaction)
    filename = f"Transaction_{transaction.id}_{transaction.date_time.strftime('%Y%m%d_%H%M%S')}.pdf"
    output_dir = os.path.join(settings.MEDIA_ROOT, 'transaction_forms')
    output_path = os.path.join(output_dir, filename)
    
    # If PDF exists and is valid, serve it directly (faster, avoids regeneration)
    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:  # File exists and > 1KB
        try:
            # Use FileResponse for better performance and reliability
            response = FileResponse(
                open(output_path, 'rb'),
                content_type='application/pdf',
                filename=filename
            )
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['X-Print-Page-Size'] = 'legal'
            response['Cache-Control'] = 'no-cache, must-revalidate'
            return response
        except Exception as e:
            # If reading existing PDF fails, continue to regeneration
            print(f"Error serving existing PDF: {e}")
    
    # Generate PDF if it doesn't exist or is corrupted
    try:
        form_filler = TransactionFormFiller()
        filled_pdf = form_filler.fill_transaction_form(transaction)
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get PDF bytes properly
        filled_pdf.seek(0)  # Reset pointer to beginning
        pdf_bytes = filled_pdf.read()
        
        # Write PDF to file for future use
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)
        
        # Serve the PDF directly from memory (more reliable)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['X-Print-Page-Size'] = 'legal'
        response['Cache-Control'] = 'no-cache, must-revalidate'
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


# ---------------------------------------------------------------------------
# Personnel ID Card Print Manager
# ---------------------------------------------------------------------------

@login_required
@user_passes_test(is_admin_or_armorer)
def serve_id_card_image(request, personnel_id, side):
    """
    Serve an ID card PNG file directly through Django (works in production
    without relying on nginx media-file configuration).
    side: 'front' | 'back' | 'combined'
    """
    from django.http import FileResponse, Http404
    if side == 'front':
        filename = f"{personnel_id}_front.png"
    elif side == 'back':
        filename = f"{personnel_id}_back.png"
    else:
        filename = f"{personnel_id}.png"

    filepath = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', filename)
    if not os.path.exists(filepath):
        raise Http404('ID card image not found')
    return FileResponse(open(filepath, 'rb'), content_type='image/png')


@login_required
@user_passes_test(lambda u: u.is_superuser)
def id_card_diagnostics(request):
    """Superuser-only diagnostic page — shows exactly what paths Django is checking."""
    from django.http import HttpResponse
    import glob

    media_root = settings.MEDIA_ROOT
    id_cards_dir = os.path.join(media_root, 'personnel_id_cards')

    # List actual files on disk
    actual_files = []
    if os.path.isdir(id_cards_dir):
        actual_files = sorted(os.listdir(id_cards_dir))

    # Check each personnel
    rows = []
    for p in Personnel.objects.filter(deleted_at__isnull=True).order_by('surname')[:5]:
        front_path = os.path.join(id_cards_dir, f"{p.id}_front.png")
        combined_path = os.path.join(id_cards_dir, f"{p.id}.png")
        rows.append(
            f"<tr><td>{p.id}</td>"
            f"<td>{front_path}</td>"
            f"<td>{'EXISTS' if os.path.exists(front_path) else 'MISSING'}</td>"
            f"<td>{combined_path}</td>"
            f"<td>{'EXISTS' if os.path.exists(combined_path) else 'MISSING'}</td></tr>"
        )

    html = f"""
    <html><head><title>ID Card Diagnostics</title>
    <style>body{{font-family:monospace;padding:2rem}}table{{border-collapse:collapse}}
    td,th{{border:1px solid #ccc;padding:6px 12px}}</style></head><body>
    <h2>ID Card Path Diagnostics</h2>
    <p><strong>MEDIA_ROOT</strong> = <code>{media_root}</code></p>
    <p><strong>personnel_id_cards dir</strong> = <code>{id_cards_dir}</code></p>
    <p><strong>Dir exists?</strong> {os.path.isdir(id_cards_dir)}</p>
    <p><strong>Files in dir ({len(actual_files)} total)</strong></p>
    <pre>{'<br>'.join(actual_files[:30]) or '(empty)'}</pre>
    <h3>First 5 personnel path check:</h3>
    <table><tr><th>ID</th><th>Front path</th><th>Front</th><th>Combined path</th><th>Combined</th></tr>
    {''.join(rows)}
    </table>
    </body></html>
    """
    return HttpResponse(html)


def _id_card_img_url(request, personnel_id, side='front'):
    """Return the URL for an ID card image served through the Django view."""
    from django.urls import reverse
    return reverse('print_handler:serve_id_card_image',
                   kwargs={'personnel_id': personnel_id, 'side': side})


@login_required
@user_passes_test(is_admin_or_armorer)
def print_id_cards(request):
    """
    Personnel ID Card Print Manager.
    Lists all active personnel, shows their ID card thumbnail,
    and allows single/bulk printing and card regeneration.
    """
    search_q = request.GET.get('q', '').strip()

    personnel_qs = Personnel.objects.filter(deleted_at__isnull=True).order_by('surname', 'firstname')
    if search_q:
        from django.db.models import Q as DQ
        personnel_qs = personnel_qs.filter(
            DQ(surname__icontains=search_q) |
            DQ(firstname__icontains=search_q) |
            DQ(id__icontains=search_q) |
            DQ(rank__icontains=search_q)
        )

    personnel_cards = []
    for p in personnel_qs:
        front_abs    = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}_front.png")
        combined_abs = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}.png")

        has_card = os.path.exists(front_abs) or os.path.exists(combined_abs)
        if has_card:
            side = 'front' if os.path.exists(front_abs) else 'combined'
            thumb_url = _id_card_img_url(request, p.id, side)
        else:
            thumb_url = None

        personnel_cards.append({
            'personnel': p,
            'has_card': has_card,
            'thumb_url': thumb_url,
        })

    total = len(personnel_cards)
    with_card = sum(1 for c in personnel_cards if c['has_card'])

    context = {
        'personnel_cards': personnel_cards,
        'search_q': search_q,
        'total': total,
        'with_card': with_card,
        'without_card': total - with_card,
    }
    return render(request, 'print_handler/print_id_cards.html', context)


@login_required
@user_passes_test(is_admin_or_armorer)
@require_POST
def generate_missing_cards(request):
    """
    Bulk-generate ID cards for all active personnel who don't have card files yet.
    Called from the Print Manager's 'Generate Missing' button.
    Returns JSON {generated: N, skipped: N, errors: [...]}
    """
    from utils.personnel_id_card_generator import generate_personnel_id_card

    generated = 0
    skipped   = 0
    errors    = []

    personnel_qs = Personnel.objects.filter(deleted_at__isnull=True)
    for p in personnel_qs:
        front_abs    = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}_front.png")
        combined_abs = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}.png")
        if os.path.exists(front_abs) or os.path.exists(combined_abs):
            skipped += 1
            continue
        try:
            generate_personnel_id_card(p)
            generated += 1
        except Exception as exc:
            errors.append({'id': p.id, 'name': str(p), 'error': str(exc)})

    return JsonResponse({'success': True, 'generated': generated, 'skipped': skipped, 'errors': errors})


@login_required
@user_passes_test(is_admin_or_armorer)
@require_POST
def regenerate_id_card(request, personnel_id):
    """Regenerate the ID card PNG for a single personnel (AJAX POST)."""
    try:
        personnel = Personnel.objects.get(id=personnel_id)
    except Personnel.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Personnel not found'}, status=404)

    try:
        from utils.personnel_id_card_generator import generate_personnel_id_card
        paths = generate_personnel_id_card(personnel)
        side = 'front' if paths.get('front') else 'combined'
        thumb_url = _id_card_img_url(request, personnel_id, side)
        return JsonResponse({'success': True, 'thumb_url': thumb_url})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@login_required
@user_passes_test(is_admin_or_armorer)
def print_id_cards_view(request):
    """
    Print-ready page for selected (or all) personnel ID cards.
    Accepts ?ids=PO-xxx,PE-xxx,... or ?all=1
    """
    ids_param = request.GET.get('ids', '')
    show_all  = request.GET.get('all', '')

    if show_all:
        personnel_qs = Personnel.objects.filter(deleted_at__isnull=True).order_by('surname', 'firstname')
    elif ids_param:
        id_list = [i.strip() for i in ids_param.split(',') if i.strip()]
        personnel_qs = Personnel.objects.filter(id__in=id_list, deleted_at__isnull=True)
    else:
        personnel_qs = Personnel.objects.none()

    cards = []
    for p in personnel_qs:
        front_abs    = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}_front.png")
        back_abs     = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}_back.png")
        combined_abs = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}.png")

        if os.path.exists(front_abs):
            front_url = _id_card_img_url(request, p.id, 'front')
        elif os.path.exists(combined_abs):
            front_url = _id_card_img_url(request, p.id, 'combined')
        else:
            front_url = None

        back_url = _id_card_img_url(request, p.id, 'back') if os.path.exists(back_abs) else None

        if front_url:
            cards.append({'personnel': p, 'front_url': front_url, 'back_url': back_url})

    return render(request, 'print_handler/print_id_cards_printview.html', {'cards': cards})