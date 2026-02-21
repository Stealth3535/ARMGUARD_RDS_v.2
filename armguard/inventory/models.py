"""
Inventory Models for ArmGuard
Based on APP/app/backend/database.py items table
"""

from django.db import models
from django.db.models import Max
from django.utils import timezone
from django.db.models.signals import post_delete
from django.dispatch import receiver
from core.validator import validate_item_data


class Item(models.Model):
    """Item model - Firearms and equipment in the armory"""
    
    # Item Type choices
    ITEM_TYPE_M14 = 'M14'
    ITEM_TYPE_M16 = 'M16'
    ITEM_TYPE_M4 = 'M4'
    ITEM_TYPE_GLOCK = 'GLOCK'
    ITEM_TYPE_45 = '45'
    
    ITEM_TYPE_CHOICES = [
        (ITEM_TYPE_M14, 'M14 Rifle'),
        (ITEM_TYPE_M16, 'M16 Rifle'),
        (ITEM_TYPE_M4, 'M4 Carbine'),
        (ITEM_TYPE_GLOCK, 'Glock Pistol'),
        (ITEM_TYPE_45, '.45 Pistol'),
    ]
    
    # Status choices
    STATUS_AVAILABLE = 'Available'
    STATUS_ISSUED = 'Issued'
    STATUS_MAINTENANCE = 'Maintenance'
    STATUS_RETIRED = 'Retired'
    
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_ISSUED, 'Issued'),
        (STATUS_MAINTENANCE, 'Maintenance'),
        (STATUS_RETIRED, 'Retired'),
    ]
    
    # Condition choices
    CONDITION_GOOD = 'Good'
    CONDITION_FAIR = 'Fair'
    CONDITION_POOR = 'Poor'
    CONDITION_DAMAGED = 'Damaged'
    
    CONDITION_CHOICES = [
        (CONDITION_GOOD, 'Good'),
        (CONDITION_FAIR, 'Fair'),
        (CONDITION_POOR, 'Poor'),
        (CONDITION_DAMAGED, 'Damaged'),
    ]
    
    # ID format: I + R/P + serial + DDMMYY
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    
    # Item Information
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    item_number = models.PositiveIntegerField(blank=True, null=True, help_text='Item number (e.g. 1, 2, 3) within the same item type')
    serial = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    stencil_picture = models.ImageField(upload_to='inventory/stencils/', blank=True, null=True)
    
    # Item Status
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default=CONDITION_GOOD)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE)
    
    # System fields
    registration_date = models.DateField(default=timezone.now)
    qr_code = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'items'
        ordering = ['item_type', 'serial']
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
    
    def __str__(self):
        return f"{self.item_type} - {self.serial}"
    
    def is_rifle(self):
        """Check if item is a rifle"""
        return self.item_type in [self.ITEM_TYPE_M14, self.ITEM_TYPE_M16, self.ITEM_TYPE_M4]
    
    def is_pistol(self):
        """Check if item is a pistol"""
        return self.item_type in [self.ITEM_TYPE_GLOCK, self.ITEM_TYPE_45]
    
    def get_item_category(self):
        """Return R for rifle or P for pistol"""
        return 'R' if self.is_rifle() else 'P'
    
    def save(self, *args, **kwargs):
        """Override save to validate and generate ID if not set"""
        previous_stencil = None
        if self.pk:
            previous_item = Item.objects.filter(pk=self.pk).only('stencil_picture').first()
            if previous_item and previous_item.stencil_picture:
                previous_stencil = previous_item.stencil_picture

        errors = validate_item_data(self)
        if errors:
            raise ValueError(f"Item validation failed: {errors}")
        # Auto-assign item_number per item_type if not set
        if not self.item_number:
            max_num = Item.objects.filter(item_type=self.item_type).aggregate(
                Max('item_number'))['item_number__max']
            self.item_number = (max_num or 0) + 1

        if not self.id:
            # Check if using existing QR code (passed via _existing_qr attribute)
            if hasattr(self, '_existing_qr') and self._existing_qr:
                # Use existing QR code as primary key
                self.id = self._existing_qr
                self.qr_code = self._existing_qr
            else:
                # Generate ID: I + R/P + serial + DDMMYY
                category = self.get_item_category()
                date_suffix = timezone.now().strftime('%d%m%y')
                self.id = f"I{category}-{self.serial}{date_suffix}"
        # Set QR code to ID if not set
        if not self.qr_code:
            self.qr_code = self.id
        super().save(*args, **kwargs)

        if previous_stencil:
            stencil_changed = not self.stencil_picture or previous_stencil.name != self.stencil_picture.name
            if stencil_changed:
                previous_stencil.delete(save=False)


@receiver(post_delete, sender=Item)
def delete_item_stencil_on_item_delete(sender, instance, **kwargs):
    if instance.stencil_picture:
        instance.stencil_picture.delete(save=False)


@receiver(post_delete, sender=Item)
def delete_item_qr_on_item_delete(sender, instance, **kwargs):
    """Delete the QRCodeImage record (and its file) when an Item is deleted."""
    try:
        from qr_manager.models import QRCodeImage
        qr = QRCodeImage.all_objects.get(qr_type=QRCodeImage.TYPE_ITEM, reference_id=instance.id)
        if qr.qr_image:
            qr.qr_image.delete(save=False)
        qr.delete()
    except Exception:
        pass

