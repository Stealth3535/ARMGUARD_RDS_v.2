"""
QR Manager Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import QRCodeImage
from personnel.models import Personnel
from inventory.models import Item


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
    
    # Attach QR code object to each personnel
    for person in personnel_list:
        try:
            person.qr_code_obj = QRCodeImage.objects.get(qr_type=QRCodeImage.TYPE_PERSONNEL, reference_id=person.id)
        except QRCodeImage.DoesNotExist:
            person.qr_code_obj = None
    
    context = {
        'personnel_list': personnel_list,
    }
    return render(request, 'qr_codes/personnel_qr_codes.html', context)


@login_required
def item_qr_codes(request):
    """View item QR codes"""
    items = Item.objects.all().order_by('item_type', 'serial')
    
    # Attach QR code object to each item
    for item in items:
        try:
            item.qr_code_obj = QRCodeImage.objects.get(qr_type=QRCodeImage.TYPE_ITEM, reference_id=item.id)
        except QRCodeImage.DoesNotExist:
            item.qr_code_obj = None
    
    context = {
        'items': items,
    }
    return render(request, 'qr_codes/item_qr_codes.html', context)


