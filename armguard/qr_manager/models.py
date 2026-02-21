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
    base = get_valid_filename(os.path.basename(filename))
    # Replace dots in the stem (all but the final extension dot) with underscores
    # so filenames like DASAN2024.10.02.png don't confuse web servers
    stem, ext = os.path.splitext(base)
    safe_filename = stem.replace('.', '_') + ext

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
        
        # Build a safe filename: replace any dots in the stem with underscores so
        # web servers (nginx/Apache) don't misinterpret the extension.
        safe_stem = self.reference_id.replace('.', '_')
        filename = f"{safe_stem}.png"
        self.qr_image.save(filename, File(buffer), save=False)
        
        return self.qr_image
    
    def save(self, *args, **kwargs):
        """Override save to generate QR code if not exists"""
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
