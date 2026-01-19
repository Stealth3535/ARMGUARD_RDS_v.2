"""
Inventory Signals - Generate QR codes when items are created/updated
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path
import qrcode
from PIL import Image
from .models import Item
from qr_manager.models import QRCodeImage


@receiver(post_save, sender=Item)
def generate_item_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for item after save"""
    # Create/update QRCodeImage for this item
    # The QRCodeImage model's save() method will automatically generate the PNG file
    qr_obj, _ = QRCodeImage.objects.get_or_create(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=instance.id,
        defaults={
            'qr_data': instance.id,
        }
    )
    # Update qr_data if needed
    if qr_obj.qr_data != instance.id:
        qr_obj.qr_data = instance.id
        qr_obj.save()

