"""
QR Manager Views
"""
import os
import logging
from django.shortcuts import render
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import QRCodeImage
from personnel.models import Personnel
from inventory.models import Item

logger = logging.getLogger(__name__)


def _heal_qr(qr, label=''):
    """
    Ensure the QR image file exists on disk and has no dots in the stem.
    Returns the (possibly updated) qr object.
    """
    try:
        needs_regen = False
        if not qr.qr_image:
            needs_regen = True
        else:
            stem = os.path.splitext(os.path.basename(qr.qr_image.name))[0]
            if '.' in stem:
                needs_regen = True
            else:
                full_path = os.path.join(settings.MEDIA_ROOT, qr.qr_image.name)
                if not os.path.exists(full_path):
                    needs_regen = True

        if needs_regen:
            if qr.qr_image:
                qr.qr_image.delete(save=False)
            qr.qr_image = None
            qr.generate_qr_code()
            qr.save()
            logger.info('_heal_qr: regenerated QR for %s %s', label, qr.reference_id)
    except Exception as e:
        logger.error('_heal_qr: failed for %s %s — %s', label, qr.reference_id, e)
    return qr


@login_required
def qr_code_management_view(request):
    """View QR codes for personnel and items"""
    personnel_qrcodes = QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_PERSONNEL)
    item_qrcodes = QRCodeImage.objects.filter(qr_type=QRCodeImage.TYPE_ITEM)
    context = {
        'personnel_qrcodes': personnel_qrcodes,
        'item_qrcodes': item_qrcodes,
    }
    return render(request, 'qr_codes/qr_code_management.html', context)


@login_required
def personnel_qr_codes(request):
    """View personnel QR codes"""
    personnel_list = Personnel.objects.all().order_by('rank', 'surname')

    for person in personnel_list:
        try:
            qr = QRCodeImage.objects.get(qr_type=QRCodeImage.TYPE_PERSONNEL, reference_id=person.id)
            person.qr_code_obj = _heal_qr(qr, 'personnel')
        except QRCodeImage.DoesNotExist:
            try:
                qr, _ = QRCodeImage.all_objects.get_or_create(
                    qr_type=QRCodeImage.TYPE_PERSONNEL,
                    reference_id=person.id,
                    defaults={'qr_data': person.id, 'is_active': True},
                )
                if not qr.is_active:
                    qr.is_active = True
                    qr.deleted_at = None
                    qr.save()
                person.qr_code_obj = _heal_qr(qr, 'personnel')
            except Exception:
                person.qr_code_obj = None

    context = {'personnel_list': personnel_list}
    return render(request, 'qr_codes/personnel_qr_codes.html', context)


@login_required
def item_qr_codes(request):
    """View item QR codes"""
    items = Item.objects.all().order_by('item_type', 'serial')

    for item in items:
        try:
            qr = QRCodeImage.objects.get(qr_type=QRCodeImage.TYPE_ITEM, reference_id=item.id)
            item.qr_code_obj = _heal_qr(qr, 'item')
        except QRCodeImage.DoesNotExist:
            try:
                qr, _ = QRCodeImage.all_objects.get_or_create(
                    qr_type=QRCodeImage.TYPE_ITEM,
                    reference_id=item.id,
                    defaults={'qr_data': item.id, 'is_active': True},
                )
                if not qr.is_active:
                    qr.is_active = True
                    qr.deleted_at = None
                    qr.save()
                item.qr_code_obj = _heal_qr(qr, 'item')
            except Exception:
                item.qr_code_obj = None

    context = {'items': items}
    return render(request, 'qr_codes/item_qr_codes.html', context)


