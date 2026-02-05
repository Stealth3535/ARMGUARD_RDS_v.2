"""
Personnel Models for ArmGuard
Based on APP/app/backend/database.py personnel table
"""
from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.contrib.auth.models import User
from core.file_security import personnel_photo_upload_path, validate_image_file


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
        upload_to=personnel_photo_upload_path,  # Secure upload path
        blank=True, 
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif']),
            validate_image_file  # Content validation
        ],
        help_text='Personnel photo (JPG, PNG, or GIF format, max 5MB)'
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
        # PERFORMANCE FIX: Add indexes for frequently queried fields
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['classification']),
            models.Index(fields=['rank']),
            models.Index(fields=['serial']),
            models.Index(fields=['group']),
            models.Index(fields=['surname', 'firstname']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),    # OneToOne lookups
            models.Index(fields=['deleted_at']),  # Soft delete queries
            models.Index(fields=['status', 'deleted_at']),  # Combined active user queries
            models.Index(fields=['group', 'rank']),  # Common filtering combination
        ]
    
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
    
    def clean(self):
        """Validate personnel data and enforce business rules"""
        from django.core.exceptions import ValidationError
        
        # Validate serial uniqueness (including soft-deleted records)
        if self.serial:
            existing_query = Personnel.all_objects.filter(serial=self.serial)
            if self.pk:
                existing_query = existing_query.exclude(pk=self.pk)
            existing = existing_query.first()
            
            if existing:
                if existing.deleted_at:
                    raise ValidationError(
                        f'Serial {self.serial} was previously assigned to '
                        f'{existing.get_full_name()} (deleted {existing.deleted_at.strftime("%Y-%m-%d")}). '
                        'Please use a different serial number or restore the existing record.'
                    )
                else:
                    raise ValidationError(
                        f'Serial {self.serial} is already assigned to {existing.get_full_name()}.'
                    )
        
        # Validate user link uniqueness (prevent multiple personnel per user)
        if self.user:
            existing_personnel = Personnel.objects.filter(user=self.user)
            if self.pk:
                existing_personnel = existing_personnel.exclude(pk=self.pk)
            if existing_personnel.exists():
                existing = existing_personnel.first()
                raise ValidationError(
                    f'User {self.user.username} is already linked to personnel '
                    f'{existing.get_full_name()} (ID: {existing.id}). '
                    'Each user can only be linked to one personnel record.'
                )
        
        # Validate rank and classification consistency
        if self.rank:
            officer_ranks = [rank_code for rank_code, _ in self.RANKS_OFFICER]
            is_officer_rank = self.rank in officer_ranks
            
            if is_officer_rank and self.classification not in ['OFFICER', 'SUPERUSER']:
                self.classification = 'OFFICER'
            elif not is_officer_rank and self.classification == 'OFFICER':
                self.classification = 'ENLISTED PERSONNEL'
    
    def save(self, *args, **kwargs):
        """Override save to generate ID, auto-set classification, and format names"""
        from django.db import transaction
        
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

        # Generate ID if not set (with atomic transaction to prevent race conditions)
        with transaction.atomic():
            if not self.id:
                prefix = 'PO' if self.is_officer() else 'PE'
                date_suffix = timezone.now().strftime('%d%m%y')
                
                # Find highest existing serial for today with locking
                existing_personnel = Personnel.objects.select_for_update().filter(
                    id__startswith=f"{prefix}-",
                    id__endswith=date_suffix
                ).values_list('id', flat=True)
                
                # Extract numeric part and find next available serial
                max_serial = 0
                for existing_id in existing_personnel:
                    try:
                        # Extract serial: PE-0001250126 -> 0001
                        id_parts = existing_id.split('-')[1]  # Remove PE- or PO-
                        serial_part = id_parts[:-6]  # Remove DDMMYY suffix
                        if serial_part.isdigit():
                            max_serial = max(max_serial, int(serial_part))
                    except (IndexError, ValueError):
                        continue
                
                next_serial = max_serial + 1
                clean_serial = str(next_serial).zfill(4)  # Pad to 4 digits: 0001
                self.id = f"{prefix}-{clean_serial}{date_suffix}"
                
                # Verify uniqueness (double-check)
                if Personnel.objects.filter(id=self.id).exists():
                    # Fallback: add timestamp microseconds for absolute uniqueness
                    timestamp = timezone.now().strftime('%H%M%S')
                    self.id = f"{prefix}-{clean_serial}{timestamp}"
            
            # Set QR code to ID if not set
            if not self.qr_code:
                self.qr_code = self.id
            
            super().save(*args, **kwargs)
            
            # Add audit logging for personnel creation/updates
            try:
                from admin.models import AuditLog
                from django.contrib.auth import get_user
                from threading import local
                
                # Get current request user if available (set by middleware)
                current_user = getattr(local(), 'user', None) if hasattr(local(), 'user') else None
                
                # Determine action type
                was_created = not bool(kwargs.get('force_insert', False)) and not hasattr(self, '_state') or self._state.adding
                action = 'PERSONNEL_CREATE' if was_created else 'PERSONNEL_EDIT'
                
                AuditLog.objects.create(
                    performed_by=current_user,
                    action=action,
                    target_model='Personnel',
                    target_id=self.id,
                    target_name=self.get_full_name(),
                    description=f'Personnel {action.lower().replace("_", " ")}: {self.get_full_name()} (ID: {self.id})',
                    changes={
                        'rank': self.rank,
                        'classification': self.classification,
                        'status': self.status,
                        'user_linked': bool(self.user)
                    }
                )
            except ImportError:
                pass  # AuditLog not available
    
    def soft_delete(self, reason="Manual deletion"):
        """Soft delete: Mark as deleted and inactive, keep record for reference with proper cascading"""
        from django.db import transaction
        
        with transaction.atomic():
            # Mark personnel as deleted
            self.deleted_at = timezone.now()
            self.status = self.STATUS_INACTIVE
            self.save()
            
            # Deactivate associated QR code (keep in DB but mark as inactive)
            from qr_manager.models import QRCodeImage
            QRCodeImage.objects.filter(
                qr_type='personnel', 
                reference_id=self.id
            ).update(
                is_active=False,
                deleted_at=timezone.now()
            )
            
            # Soft delete associated user account if exists
            if hasattr(self, 'user') and self.user:
                self.user.is_active = False
                self.user.save()
                
            # Log the deletion for audit trail
            try:
                from admin.models import AuditLog
                AuditLog.objects.create(
                    action='PERSONNEL_DELETE',
                    details=f'Personnel {self.id} ({self.get_full_name()}) soft deleted: {reason}',
                    user=None  # System action
                )
            except ImportError:
                pass  # AuditLog model might not exist
    
    def restore(self):
        """Restore soft-deleted personnel"""
        from django.db import transaction
        
        with transaction.atomic():
            # Restore personnel
            self.deleted_at = None
            self.status = self.STATUS_ACTIVE
            self.save()
            
            # Reactivate QR codes
            from qr_manager.models import QRCodeImage
            QRCodeImage.objects.filter(
                qr_type='personnel',
                reference_id=self.id
            ).update(is_active=True, deleted_at=None)
            
            # Reactivate user account if exists
            if hasattr(self, 'user') and self.user:
                self.user.is_active = True
                self.user.save()



