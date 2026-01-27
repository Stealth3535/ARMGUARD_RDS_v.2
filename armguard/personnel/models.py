"""
Personnel Models for ArmGuard
Based on APP/app/backend/database.py personnel table
"""
from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.contrib.auth.models import User


class PersonnelManager(models.Manager):
    """Custom manager to filter out soft-deleted personnel by default"""
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)
    
    def with_deleted(self):
        """Include soft-deleted personnel"""
        return super().get_queryset()
    
    def deleted_only(self):
        """Get only soft-deleted personnel"""
        return super().get_queryset().filter(deleted_at__isnull=False)


class Personnel(models.Model):
    """Personnel model - Military personnel in the armory system"""
    
    # Status choices
    STATUS_ACTIVE = 'Active'
    STATUS_INACTIVE = 'Inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
    ]
    
    # Classification choices
    CLASSIFICATION_CHOICES = [
        ('ENLISTED PERSONNEL', 'Enlisted Personnel'),
        ('OFFICER', 'Officer'),
        ('SUPERUSER', 'Superuser'),
    ]
    
    # Rank choices - Enlisted
    RANKS_ENLISTED = [
        ('AM', 'Airman'),
        ('AW', 'Airwoman'),
        ('A2C', 'Airman 2nd Class'),
        ('AW2C', 'Airwoman 2nd Class'),
        ('A1C', 'Airman 1st Class'),
        ('AW1C', 'Airwoman 1st Class'),
        ('SGT', 'Sergeant'),
        ('SSGT', 'Staff Sergeant'),
        ('TSGT', 'Technical Sergeant'),
        ('MSGT', 'Master Sergeant'),
        ('SMSGT', 'Senior Master Sergeant'),
        ('CMSGT', 'Chief Master Sergeant'),
    ]
    
    # Rank choices - Officers
    RANKS_OFFICER = [
        ('2LT', 'Second Lieutenant'),
        ('1LT', 'First Lieutenant'),
        ('CPT', 'Captain'),
        ('MAJ', 'Major'),
        ('LTCOL', 'Lieutenant Colonel'),
        ('COL', 'Colonel'),
        ('BGEN', 'Brigadier General'),
        ('MGEN', 'Major General'),
        ('LTGEN', 'Lieutenant General'),
        ('GEN', 'General'),
    ]
    
    ALL_RANKS = RANKS_ENLISTED + RANKS_OFFICER
    
    # Group choices
    GROUP_CHOICES = [
        ('HAS', 'HAS'),
        ('951st', '951st'),
        ('952nd', '952nd'),
        ('953rd', '953rd'),
    ]
    
    # ID format: PE/PO + serial + DDMMYY
    id = models.CharField(max_length=50, primary_key=True, editable=False)
    
    # Link to User account (optional - personnel without login won't have this)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='personnel')
    
    # Personal Information
    surname = models.CharField(max_length=100)
    firstname = models.CharField(max_length=100)
    middle_initial = models.CharField(max_length=10, blank=True, null=True)
    
    # Military Information
    rank = models.CharField(
        max_length=20, 
        choices=ALL_RANKS,
        blank=True,
        null=True,
        help_text="Military rank (not required for superusers)"
    )
    serial = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Serial number (6 digits for enlisted, or O-XXXXXX for officers)"
    )
    group = models.CharField(max_length=10, choices=GROUP_CHOICES, default='HAS')
    
    # Contact Information
    tel = models.CharField(
        max_length=13,
        validators=[RegexValidator(r'^\+639\d{9}$', 'Phone must be in format +639XXXXXXXXX')],
        help_text="+639XXXXXXXXX"
    )
    
    # System fields
    registration_date = models.DateField(default=timezone.now)
    qr_code = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    classification = models.CharField(
        max_length=20, 
        choices=CLASSIFICATION_CHOICES, 
        default='ENLISTED PERSONNEL',
        help_text="Personnel classification (ENLISTED PERSONNEL, OFFICER, SUPERUSER)"
    )
    picture = models.ImageField(
        upload_to='personnel/pictures/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text="Soft delete timestamp - record kept for reference")
    
    # Managers
    objects = PersonnelManager()  # Default manager excludes soft-deleted
    all_objects = models.Manager()  # Access all including soft-deleted
    
    class Meta:
        db_table = 'personnel'
        ordering = ['surname', 'firstname']
        verbose_name = 'Personnel'
        verbose_name_plural = 'Personnel'
    
    def __str__(self):
        if self.rank:
            return f"{self.get_full_name()} ({self.rank})"
        elif self.classification == 'SUPERUSER':
            return f"{self.get_full_name()} (SUPERUSER)"
        else:
            return f"{self.get_full_name()}"
    
    def get_full_name(self):
        """Return full name with middle initial"""
        if self.middle_initial:
            return f"{self.firstname} {self.middle_initial}. {self.surname}"
        return f"{self.firstname} {self.surname}"
    
    def is_officer(self):
        """Check if personnel is an officer"""
        officer_ranks = [rank_code for rank_code, _ in self.RANKS_OFFICER]
        return self.rank in officer_ranks
    
    def get_serial_display(self):
        """Return formatted serial number with O- prefix for officers"""
        if self.is_officer():
            # Add O- prefix if not already present
            if not self.serial.startswith('O-'):
                return f"O-{self.serial}"
            return self.serial
        return self.serial
    
    def get_classification_from_rank(self):
        """Auto-determine classification based on rank"""
        if not self.rank:
            return 'SUPERUSER'  # No rank means superuser
        elif self.is_officer():
            return 'OFFICER'
        else:
            return 'ENLISTED PERSONNEL'
    
    def get_personnel_class(self):
        """Return personnel class - EP for Enlisted, O for Officer"""
        return 'O' if self.is_officer() else 'EP'
    
    def save(self, *args, **kwargs):
        """Override save to generate ID, auto-set classification, and format names"""
        # Auto-determine classification if not set or using old values
        if not self.classification or self.classification in ['REGULAR', 'ADMIN']:
            if hasattr(self, 'user') and self.user and self.user.is_superuser:
                self.classification = 'SUPERUSER'
            else:
                self.classification = self.get_classification_from_rank()
        
        # Format names based on classification
        if self.is_officer():
            self.surname = self.surname.upper()
            self.firstname = self.firstname.upper()
            if self.middle_initial:
                self.middle_initial = self.middle_initial.upper()
            if self.rank:
                self.rank = self.rank.upper()
        else:
            self.surname = self.surname.title()
            self.firstname = self.firstname.title()
            if self.middle_initial:
                self.middle_initial = self.middle_initial.upper()
            if self.rank:
                self.rank = self.rank.upper()

        # Generate ID if not set
        if not self.id:
            prefix = 'PO' if self.is_officer() else 'PE'
            date_suffix = timezone.now().strftime('%d%m%y')
            clean_serial = self.serial.replace('O-', '') if self.is_officer() else self.serial
            self.id = f"{prefix}-{clean_serial}{date_suffix}"
        
        # Set QR code to ID if not set
        if not self.qr_code:
            self.qr_code = self.id
        
        super().save(*args, **kwargs)
    
    def soft_delete(self):
        """Soft delete: Mark as deleted and inactive, keep record for reference"""
        self.deleted_at = timezone.now()
        self.status = self.STATUS_INACTIVE
        self.save()
        
        # Deactivate associated QR code (keep in DB but mark as inactive)
        from qr_manager.models import QRCodeImage
        QRCodeImage.objects.filter(qr_type='personnel', reference_id=self.id).update(
            is_active=False,
            deleted_at=timezone.now()
        )

