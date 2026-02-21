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


# ---------------------------------------------------------------------------
# Item Tag Print Manager
# ---------------------------------------------------------------------------

def _item_tag_img_url(request, item_id):
    """Return the URL for an item tag image served through the Django view."""
    from django.urls import reverse
    return reverse('print_handler:serve_item_tag_image', kwargs={'item_id': item_id})


@login_required
@user_passes_test(is_admin_or_armorer)
def serve_item_tag_image(request, item_id):
    """Serve an item tag PNG file directly through Django."""
    from django.http import FileResponse, Http404
    filepath = os.path.join(settings.MEDIA_ROOT, 'item_id_tags', f"{item_id}.png")
    if not os.path.exists(filepath):
        raise Http404('Item tag image not found')
    return FileResponse(open(filepath, 'rb'), content_type='image/png')


@login_required
@user_passes_test(is_admin_or_armorer)
def print_item_tags(request):
    """
    Item Tag Print Manager — lists all items, shows their tag thumbnail,
    and allows single/bulk printing and re-generation.
    """
    search_q = request.GET.get('q', '').strip()

    items_qs = Item.objects.all().order_by('item_type', 'serial')
    if search_q:
        from django.db.models import Q as DQ
        items_qs = items_qs.filter(
            DQ(serial__icontains=search_q) |
            DQ(item_type__icontains=search_q) |
            DQ(id__icontains=search_q)
        )

    item_tags = []
    for item in items_qs:
        tag_abs  = os.path.join(settings.MEDIA_ROOT, 'item_id_tags', f"{item.id}.png")
        has_tag  = os.path.exists(tag_abs)
        thumb_url = _item_tag_img_url(request, item.id) if has_tag else None
        item_tags.append({
            'item': item,
            'has_tag': has_tag,
            'thumb_url': thumb_url,
        })

    total      = len(item_tags)
    with_tag   = sum(1 for t in item_tags if t['has_tag'])

    context = {
        'item_tags': item_tags,
        'search_q': search_q,
        'total': total,
        'with_tag': with_tag,
        'without_tag': total - with_tag,
    }
    return render(request, 'print_handler/print_item_tags.html', context)


def _ensure_qr_record(item):
    """
    Ensure a QRCodeImage record exists for the item.
    For M4 (factory QR): qr_data = item.id  (the factory QR string itself).
    For all items:        qr_data = item.id  (item ID is the canonical scan value).
    Creates the record and generates the PNG if missing.
    """
    from qr_manager.models import QRCodeImage
    qr, created = QRCodeImage.all_objects.get_or_create(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=item.id,
        defaults={'qr_data': item.id}
    )
    if not qr.is_active:
        qr.is_active = True
        qr.deleted_at = None
        qr.save(update_fields=['is_active', 'deleted_at'])
    if not qr.qr_image:
        qr.generate_qr_code()
        qr.save()
    return qr


@login_required
@user_passes_test(is_admin_or_armorer)
@require_POST
def generate_item_tags(request):
    """
    Bulk-generate item tag PNGs.
    force=1 → regenerate ALL (even those that exist).
    Returns JSON {generated, skipped, errors}
    """
    from utils.item_tag_generator import generate_item_tag

    force     = request.POST.get('force', '0') == '1'
    generated = 0
    skipped   = 0
    errors    = []

    for item in Item.objects.all():
        tag_abs = os.path.join(settings.MEDIA_ROOT, 'item_id_tags', f"{item.id}.png")
        if not force and os.path.exists(tag_abs):
            skipped += 1
            continue
        try:
            _ensure_qr_record(item)
            generate_item_tag(item)
            generated += 1
        except Exception as exc:
            errors.append({'id': item.id, 'serial': item.serial, 'error': str(exc)})

    return JsonResponse({'success': True, 'generated': generated, 'skipped': skipped, 'errors': errors})


@login_required
@user_passes_test(is_admin_or_armorer)
@require_POST
def regenerate_item_tag(request, item_id):
    """Regenerate the tag PNG for a single item (AJAX POST)."""
    try:
        item = Item.objects.get(id=item_id)
    except Item.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'}, status=404)
    try:
        from utils.item_tag_generator import generate_item_tag
        _ensure_qr_record(item)
        generate_item_tag(item)
        thumb_url = _item_tag_img_url(request, item_id)
        return JsonResponse({'success': True, 'thumb_url': thumb_url})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)


@login_required
@user_passes_test(is_admin_or_armorer)
def print_item_tags_view(request):
    """Print-ready page for selected (or all) item tags."""
    ids_param = request.GET.get('ids', '')
    show_all  = request.GET.get('all', '')

    if show_all:
        items_qs = Item.objects.all().order_by('item_type', 'serial')
    elif ids_param:
        id_list  = [i.strip() for i in ids_param.split(',') if i.strip()]
        items_qs = Item.objects.filter(id__in=id_list)
    else:
        items_qs = Item.objects.none()

    try:
        stack = min(max(int(request.GET.get('stack', 1)), 1), 3)
    except (ValueError, TypeError):
        stack = 1

    from utils.item_tag_generator import get_stacked_tag_b64

    tags = []
    for item in items_qs:
        tag_abs = os.path.join(settings.MEDIA_ROOT, 'item_id_tags', f"{item.id}.png")
        if not os.path.exists(tag_abs):
            continue
        if stack == 1:
            tag_src = _item_tag_img_url(request, item.id)
        else:
            tag_src = get_stacked_tag_b64(item, stack)
        tags.append({'item': item, 'tag_url': tag_src, 'stack': stack})

    return render(request, 'print_handler/print_item_tags_printview.html', {'tags': tags, 'stack': stack})


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
    Bulk-generate ID cards for active personnel.
    POST body param  force=1  → regenerate ALL cards (even those that already exist).
    Default (force=0) → generate only personnel who have no card file yet.
    Returns JSON {generated, skipped, errors}
    """
    from utils.personnel_id_card_generator import generate_personnel_id_card

    force = request.POST.get('force', '0') == '1'

    generated = 0
    skipped   = 0
    errors    = []

    personnel_qs = Personnel.objects.filter(deleted_at__isnull=True)
    for p in personnel_qs:
        front_abs    = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}_front.png")
        combined_abs = os.path.join(settings.MEDIA_ROOT, 'personnel_id_cards', f"{p.id}.png")
        if not force and (os.path.exists(front_abs) or os.path.exists(combined_abs)):
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