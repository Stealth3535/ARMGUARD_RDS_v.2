"""
Inventory Models for ArmGuard
Based on APP/app/backend/database.py items table
"""

from django.db import models
from django.utils import timezone
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
    serial = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    
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
        errors = validate_item_data(self)
        if errors:
            raise ValueError(f"Item validation failed: {errors}")
        if not self.id:
            # Generate ID: I + R/P + serial + DDMMYY
            category = self.get_item_category()
            date_suffix = timezone.now().strftime('%d%m%y')
            self.id = f"I{category}-{self.serial}{date_suffix}"
        # Set QR code to ID if not set
        if not self.qr_code:
            self.qr_code = self.id
        super().save(*args, **kwargs)

