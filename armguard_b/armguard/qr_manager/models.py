"""
QR Code Models for ArmGuard
Handles QR code generation and management using unified qr_generator
"""
from django.db import models
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.core.files import File
from utils.qr_generator import generate_qr_code_to_buffer
import os


def qr_upload_path(instance, filename):
    """Dynamic upload path based on QR type - sanitized to prevent path traversal"""
    # Sanitize filename to prevent path traversal attacks
    safe_filename = get_valid_filename(os.path.basename(filename))
    
    if instance.qr_type == 'item':
        return f'qr_codes/items/{safe_filename}'
    else:
        return f'qr_codes/{instance.qr_type}/{safe_filename}'


class QRCodeManager(models.Manager):
    """Custom manager to filter active QR codes by default"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)
    
    def with_inactive(self):
        """Include inactive QR codes"""
        return super().get_queryset()
    
    def inactive_only(self):
        """Get only inactive QR codes"""
        return super().get_queryset().filter(is_active=False)


class QRCodeImage(models.Model):
    """QR Code storage model"""
    
    # QR Code type
    TYPE_PERSONNEL = 'personnel'
    TYPE_ITEM = 'item'
    
    TYPE_CHOICES = [
        (TYPE_PERSONNEL, 'Personnel'),
        (TYPE_ITEM, 'Item'),
    ]
    
    # Fields
    qr_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    reference_id = models.CharField(max_length=100, help_text="Personnel ID or Item ID")
    qr_data = models.CharField(max_length=255, help_text="Data encoded in QR code")
    qr_image = models.ImageField(upload_to=qr_upload_path, blank=True, null=True)
    
    # Status tracking
    is_active = models.BooleanField(default=True, help_text="QR code is active and can be used for transactions")
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="When QR was deactivated (soft delete)")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Managers
    objects = QRCodeManager()  # Default manager returns only active QR codes
    all_objects = models.Manager()  # Access all including inactive
    
    class Meta:
        db_table = 'qr_codes'
        ordering = ['-created_at']
        verbose_name = 'QR Code'
        verbose_name_plural = 'QR Codes'
        unique_together = ['qr_type', 'reference_id']
    
    def __str__(self):
        return f"{self.qr_type} QR: {self.reference_id}"
    
    def generate_qr_code(self, size=600, box_size=20, border=2):
        """Generate HIGH-RESOLUTION QR code image for crisp printing"""
        # Use unified QR generator with HD settings for print quality
        buffer = generate_qr_code_to_buffer(self.qr_data, size=size)
        
        # Save to model - filename is just the reference_id (e.g., IP-854643041125.png)
        filename = f"{self.reference_id}.png"
        self.qr_image.save(filename, File(buffer), save=False)
        
        return self.qr_image
    
    def clean(self):
        """Validate QR code data and ensure referenced entity exists"""
        from django.core.exceptions import ValidationError
        from personnel.models import Personnel
        from inventory.models import Item
        
        # Validate reference_id corresponds to actual entity
        if self.qr_type == self.TYPE_PERSONNEL:
            try:
                Personnel.all_objects.get(id=self.reference_id)
            except Personnel.DoesNotExist:
                raise ValidationError(f'Personnel with ID {self.reference_id} does not exist.')
        elif self.qr_type == self.TYPE_ITEM:
            try:
                Item.objects.get(id=self.reference_id)
            except Item.DoesNotExist:
                raise ValidationError(f'Item with ID {self.reference_id} does not exist.')
        
        # Validate qr_data is properly formatted
        if self.qr_data and not self.qr_data == self.reference_id:
            # QR data should match reference_id for simple format
            if not self.qr_data.startswith(f'{self.qr_type.upper()}:{self.reference_id}'):
                # Allow legacy format but warn
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f'QR code {self.reference_id} has non-standard qr_data: {self.qr_data}')
    
    def save(self, *args, **kwargs):
        """Override save to generate QR code if not exists"""
        # Set qr_data to reference_id if not provided (simple format)
        if not self.qr_data:
            self.qr_data = self.reference_id
        
        if not self.qr_image:
            self.generate_qr_code()
        super().save(*args, **kwargs)
    
    def is_valid_for_transaction(self):
        """Check if QR code can be used for transactions"""
        if not self.is_active:
            return False, "QR code is inactive (personnel/item has been deleted)"
        if self.deleted_at:
            return False, "QR code has been deactivated"
        return True, "QR code is valid"
    
    def deactivate(self):
        """Deactivate QR code (soft delete)"""
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save()
    
    def reactivate(self):
        """Reactivate QR code"""
        self.is_active = True
        self.deleted_at = None
        self.save()

