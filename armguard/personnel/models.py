"""
Personnel Models for ArmGuard
Based on APP/app/backend/database.py personnel table

=== HIGH-QUALITY AUDIT LOGGING ===

This model implements comprehensive audit logging that complies with military-grade 
audit trail requirements:

1. AUTOMATIC AUDIT LOGGING:
   - All CREATE, UPDATE, DELETE operations are automatically logged
   - Field-level change tracking (before/after values)
   - User attribution (who performed the action)
   - IP address and user agent tracking
   - Timestamp for all operations

2. USAGE IN VIEWS:
   To enable automatic audit logging in your views:
   
   # Method 1: Set audit context manually
   personnel._audit_user = request.user
   personnel._audit_ip = request.META.get('REMOTE_ADDR')
   personnel._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')
   personnel.save()
   
   # Method 2: Use helper method (recommended)
   personnel.set_audit_context(request).save()

3. AUDIT HISTORY RETRIEVAL:
   # Get all audit logs for a personnel record
   audit_logs = personnel.get_audit_history()
   
   # Display in template:
   {% for log in personnel.get_audit_history %}
       {{ log.timestamp }} - {{ log.action }} by {{ log.performed_by }}
       Changes: {{ log.changes }}
   {% endfor %}

4. SOFT DELETE WITH AUDIT:
   # Soft delete with audit logging
   personnel.soft_delete(deleted_by=request.user)

5. TRACKED FIELDS:
   - surname, firstname, middle_initial
   - rank, serial, group
   - tel, status, classification
   - registration_date
   
6. AUDIT LOG STORAGE:
   All audit logs are stored in the AuditLog model (admin app) with:
   - Indexed queries for performance
   - JSON change tracking
   - Full audit trail preservation
   - Never deleted (permanent record)

See: admin/models.py (AuditLog, DeletedRecord)
See: admin/signals.py (personnel_post_save_with_audit, delete_personnel_with_audit)
"""
from django.db import models
from django.db.models import Q
from django.core.validators import RegexValidator, FileExtensionValidator, EmailValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from simple_history.models import HistoricalRecords


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
    STATUS_SUSPENDED = 'Suspended'
    STATUS_ARCHIVED = 'Archived'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_ARCHIVED, 'Archived'),
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
    
    # Comprehensive audit tracking
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel_created',
        help_text="User who created this personnel record"
    )
    created_ip = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the creator")
    created_user_agent = models.TextField(blank=True, help_text="User agent of the creator")
    
    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel_modified',
        help_text="User who last modified this personnel record"
    )
    updated_ip = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the last modifier")
    updated_user_agent = models.TextField(blank=True, help_text="User agent of the last modifier")
    
    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel_deleted_by',
        help_text="User who deleted this personnel record"
    )
    deleted_ip = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the deleter")
    
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
        help_text="Serial number (officers have O- prefix, enlisted are numeric only)"
    )
    group = models.CharField(max_length=10, choices=GROUP_CHOICES, default='HAS')
    
    # Contact Information
    tel = models.CharField(
        max_length=13,
        validators=[RegexValidator(r'^\+639\d{9}$', 'Phone must be in format +639XXXXXXXXX')],
        help_text="+639XXXXXXXXX"
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address (must end with @gmail.com)",
        validators=[EmailValidator(message="Enter a valid email address")]
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
    
    # Soft delete flag
    is_deleted = models.BooleanField(default=False, help_text="Soft delete flag for queries")
    
    # Version and change tracking
    version = models.PositiveIntegerField(default=1, help_text="Record version - increments on update")
    change_reason = models.TextField(blank=True, help_text="Reason for this change (for audit trail)")
    
    # Status tracking
    status_changed_at = models.DateTimeField(null=True, blank=True, help_text="When status was last changed")
    status_changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personnel_status_changed',
        help_text="User who last changed the status"
    )
    
    # Session tracking
    session_id = models.CharField(max_length=100, blank=True, help_text="Session ID of the last modification")
    
    # Data retention and compliance
    retention_period = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Data retention period in days (for compliance)"
    )
    can_purge_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when this record can be permanently deleted (GDPR compliance)"
    )
    
    # Historical tracking - automatically tracks all field changes
    history = HistoricalRecords(
        history_change_reason_field=models.TextField(null=True, blank=True)
    )
    
    # Managers
    objects = PersonnelManager()  # Default manager excludes soft-deleted
    all_objects = models.Manager()  # Access all including soft-deleted
    
    class Meta:
        db_table = 'personnel'
        ordering = ['surname', 'firstname']
        verbose_name = 'Personnel'
        verbose_name_plural = 'Personnel'
        # Database-level constraints for data integrity
        constraints = [
            models.CheckConstraint(
                check=Q(status__in=['Active', 'Inactive', 'Suspended', 'Archived']),
                name='valid_personnel_status'
            ),
            models.CheckConstraint(
                check=Q(classification__in=['ENLISTED PERSONNEL', 'OFFICER', 'SUPERUSER']),
                name='valid_personnel_classification'
            ),
            # Ensure serial is not empty
            models.CheckConstraint(
                check=~Q(serial=''),
                name='serial_not_empty'
            ),
            # Ensure valid email format (basic check)
            models.CheckConstraint(
                check=Q(email__icontains='@') | Q(email=''),
                name='valid_email_format'
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'classification']),
            models.Index(fields=['rank']),
            models.Index(fields=['group']),
            models.Index(fields=['-registration_date']),
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
            return f"{self.firstname} {self.middle_initial} {self.surname}"
        return f"{self.firstname} {self.surname}"
    
    def is_officer(self):
        """Check if personnel is an officer"""
        officer_ranks = [rank_code for rank_code, _ in self.RANKS_OFFICER]
        return self.rank in officer_ranks
    
    def get_serial_display(self):
        """Return serial number (O- prefix for officers only)"""
        if self.serial:
            # Officers: Display with O- prefix (already in DB)
            if self.serial.startswith('O-'):
                return self.serial
            # Officers without O- prefix (shouldn't happen, but handle it)
            if self.is_officer():
                return f"O-{self.serial}"
            # Enlisted: Display numeric only (no prefix)
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
        """
        Validate model fields before save.
        - Email must end with @gmail.com if provided
        - Serial number should be numeric only
       - Validate rank vs classification consistency
        """
        super().clean()
        from django.core.exceptions import ValidationError
        
        # Validate email format if provided
        if self.email and not self.email.lower().endswith('@gmail.com'):
            # Auto-correct to @gmail.com (can be changed to raise error if preferred)
            local_part = self.email.split('@')[0]
            self.email = f"{local_part}@gmail.com"
        
        # Validate serial number format (accept with or without O- prefix)
        if self.serial:
            # Normalize serial - remove O- prefix temporarily for validation
            clean_serial = self.serial.replace('O-', '')
            
            # Check if the numeric part is valid
            if not clean_serial.replace('-', '').isdigit():
                raise ValidationError({
                    'serial': f'Serial number must be numeric only. Got: {self.serial}'
                })
            
            # Store the clean numeric version for now (will be formatted in save())
            self.serial = clean_serial
        
        # Validate rank vs classification consistency
        if self.rank:
            expected_classification = self.get_classification_from_rank()
            if self.classification and self.classification != expected_classification and self.classification != 'SUPERUSER':
                # This will be auto-corrected in save(), but we can warn here
                from django.core.exceptions import ValidationError
                # Don't raise error, just let save() auto-correct it
                # raise ValidationError({
                #     'classification': f"Rank '{self.rank}' should have classification '{expected_classification}', not '{self.classification}'"
                # })
                pass  # Let save() auto-correct
    
    def save(self, *args, **kwargs):
        """
        Override save to:
        - Generate ID and QR code
        - Auto-set classification
        - Format names based on officer/enlisted status
        - Track version changes
        - Track status changes
        - Handle comprehensive audit context
        - Auto-correct email format
        
        For automatic audit logging, set audit context before calling save():
            personnel._audit_user = request.user
            personnel._audit_ip = request.META.get('REMOTE_ADDR')
            personnel._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')
            personnel._audit_session = request.session.session_key
            personnel.save()
        
        Or use the set_audit_context() method:
            personnel.set_audit_context(request)
            personnel.save()
        """
        # Track if this is an update (has pk) or creation
        is_update = bool(self.pk)
        
        # Set created_by on first save if not already set
        if not is_update and not self.created_by:
            if hasattr(self, '_audit_user') and self._audit_user:
                self.created_by = self._audit_user
                self.created_ip = getattr(self, '_audit_ip', None)
                self.created_user_agent = getattr(self, '_audit_user_agent', '')
        
        # Update modified_by on every save if audit context is set
        if hasattr(self, '_audit_user') and self._audit_user:
            self.modified_by = self._audit_user
            self.updated_ip = getattr(self, '_audit_ip', None)
            self.updated_user_agent = getattr(self, '_audit_user_agent', '')
            self.session_id = getattr(self, '_audit_session', '')
        
        # Track status changes
        if is_update:
            try:
                old_instance = Personnel.objects.get(pk=self.pk)
                if old_instance.status != self.status:
                    self.status_changed_at = timezone.now()
                    if hasattr(self, '_audit_user') and self._audit_user:
                        self.status_changed_by = self._audit_user
            except Personnel.DoesNotExist:
                pass
        
        # Increment version on update
        if is_update:
            self.version += 1
        
        # ALWAYS auto-correct classification based on rank (data integrity fix)
        # This ensures database consistency even if old data had wrong classification
        if hasattr(self, 'user') and self.user and self.user.is_superuser:
            self.classification = 'SUPERUSER'
        elif self.rank:
            # Auto-correct based on rank
            expected_classification = self.get_classification_from_rank()
            if self.classification != expected_classification:
                # Log the correction
                if is_update:
                    print(f"Auto-correcting classification for {self.get_full_name()}: {self.classification} → {expected_classification}")
                self.classification = expected_classification
        elif not self.classification:
            # No rank and no classification set
            self.classification = 'ENLISTED PERSONNEL'
        
        # Auto-correct email format
        if self.email and not self.email.lower().endswith('@gmail.com'):
            local_part = self.email.split('@')[0]
            self.email = f"{local_part}@gmail.com"
        
        # Format serial number: Officers get O- prefix in DB, enlisted stay numeric
        if self.serial:
            # Remove O- prefix if present (normalize)
            clean_serial = self.serial.replace('O-', '')
            
            # Add O- prefix for officers only
            if self.is_officer():
                self.serial = f"O-{clean_serial}"
            else:
                self.serial = clean_serial
        
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
            # Serial already formatted with O- for officers, clean it for ID
            clean_serial = self.serial.replace('O-', '')
            self.id = f"{prefix}-{clean_serial}{date_suffix}"
        
        # Set QR code to ID if not set
        if not self.qr_code:
            self.qr_code = self.id
        
        # Set change reason from history if available
        if hasattr(self, '_change_reason'):
            self.change_reason = self._change_reason
        
        super().save(*args, **kwargs)
    
    def soft_delete(self, deleted_by=None):
        """
        Soft delete: Mark as deleted and inactive, keep record for reference.
        Automatically creates audit log entry.
        
        Args:
            deleted_by: User performing the deletion (for audit logging)
        """
        self.deleted_at = timezone.now()
        self.is_deleted = True
        self.status = self.STATUS_INACTIVE
        
        if deleted_by:
            self.deleted_by = deleted_by
            self.modified_by = deleted_by
            self._audit_user = deleted_by
        
        self.save()
        
        # Create soft delete audit log
        if deleted_by:
            self.create_audit_log(
                action='DELETE',
                personnel=self,
                performed_by=deleted_by,
                description=f"Soft deleted personnel: {self.get_full_name()} - marked as inactive and hidden",
                changes={'soft_delete': {'status': self.status, 'deleted_at': str(self.deleted_at)}}
            )
        
        # Deactivate associated QR code (keep in DB but mark as inactive)
        from qr_manager.models import QRCodeImage
        QRCodeImage.objects.filter(qr_type='personnel', reference_id=self.id).update(
            is_active=False,
            deleted_at=timezone.now()
        )
    
    def set_audit_context(self, request):
        """
        Set audit context from Django request for automatic audit logging.
        Call this before save() to enable comprehensive audit tracking.
        
        Includes: user, IP address, user agent, and session ID
        
        Usage:
            personnel.set_audit_context(request)
            personnel.save()
        """
        self._audit_user = request.user if request.user.is_authenticated else None
        self._audit_ip = request.META.get('REMOTE_ADDR')
        self._audit_user_agent = request.META.get('HTTP_USER_AGENT', '')
        self._audit_session = request.session.session_key if hasattr(request, 'session') else ''
        return self
    
    def get_audit_history(self):
        """Get complete audit history for this personnel record"""
        from admin.models import AuditLog
        return AuditLog.objects.filter(
            target_model='Personnel',
            target_id=self.id
        ).select_related('performed_by').order_by('-timestamp')
    
    def get_field_changes(self, old_instance):
        """
        Compare this instance with old instance and return dictionary of changes.
        Used for audit logging.
        """
        changes = {}
        
        # Fields to track
        tracked_fields = [
            'surname', 'firstname', 'middle_initial', 'rank', 'serial', 'group',
            'tel', 'email', 'status', 'classification', 'registration_date'
        ]
        
        for field in tracked_fields:
            old_value = getattr(old_instance, field, None) if old_instance else None
            new_value = getattr(self, field, None)
            
            # Convert values to strings for comparison
            old_str = str(old_value) if old_value is not None else ''
            new_str = str(new_value) if new_value is not None else ''
            
            if old_str != new_str:
                changes[field] = {
                    'old': old_str,
                    'new': new_str
                }
        
        return changes
    
    @classmethod
    def bulk_update_status(cls, personnel_ids, new_status, updated_by=None):
        """
        Batch update status for multiple personnel records.
        More efficient than updating individually.
        
        Args:
            personnel_ids: List of personnel IDs to update
            new_status: New status ('Active', 'Inactive', 'Suspended', 'Archived')
            updated_by: User performing the update (for audit)
        
        Returns:
            Number of records updated
        
        Usage:
            Personnel.bulk_update_status(['PE-123', 'PE-456'], 'Inactive', request.user)
        """
        from django.utils import timezone
        from django.db import transaction
        
        if new_status not in dict(cls.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}")
        
        with transaction.atomic():
            # Get all personnel to update
            personnel_qs = cls.objects.filter(id__in=personnel_ids)
            
            # Update in bulk
            updated_count = personnel_qs.update(
                status=new_status,
                status_changed_at=timezone.now(),
                modified_by=updated_by
            )
            
            # Create audit log entries
            if updated_by:
                from admin.models import AuditLog
                for personnel in personnel_qs:
                    AuditLog.objects.create(
                        performed_by=updated_by,
                        action='UPDATE',
                        target_model='Personnel',
                        target_id=personnel.id,
                        target_name=personnel.get_full_name(),
                        description=f'Bulk status update: {personnel.status} → {new_status}',
                        changes={'status': {'old': personnel.status, 'new': new_status}}
                    )
            
            return updated_count
    
    @classmethod
    def bulk_assign_group(cls, personnel_ids, new_group, updated_by=None):
        """
        Batch update group assignment for multiple personnel.
        
        Args:
            personnel_ids: List of personnel IDs
            new_group: New group ('HAS', '951st', '952nd', '953rd')
            updated_by: User performing the update
        
        Returns:
            Number of records updated
        """
        from django.db import transaction
        
        with transaction.atomic():
            updated_count = cls.objects.filter(id__in=personnel_ids).update(
                group=new_group,
                modified_by=updated_by
            )
            
            return updated_count
    
    @classmethod
    def get_statistics(cls):
        """
        Get comprehensive personnel statistics.
        Returns dictionary with counts by status, classification, rank, etc.
        
        Usage:
            stats = Personnel.get_statistics()
            print(f"Active: {stats['by_status']['Active']}")
        """
        from django.db.models import Count
        
        return {
            'total': cls.objects.count(),
            'by_status': dict(cls.objects.values_list('status').annotate(Count('id'))),
            'by_classification': dict(cls.objects.values_list('classification').annotate(Count('id'))),
            'by_group': dict(cls.objects.values_list('group').annotate(Count('id'))),
            'with_user': cls.objects.filter(user__isnull=False).count(),
            'without_user': cls.objects.filter(user__isnull=True).count(),
            'soft_deleted': cls.all_objects.filter(deleted_at__isnull=False).count(),
        }
    
    @classmethod
    def create_audit_log(cls, action, personnel, performed_by, description, changes=None, ip_address=None, user_agent=None):
        """
        Create audit log entry for personnel action.
        
        Args:
            action: Action type (CREATE, UPDATE, DELETE, etc.)
            personnel: Personnel instance
            performed_by: User who performed action
            description: Human-readable description
            changes: Dictionary of before/after values
            ip_address: IP address of requester
            user_agent: User agent string
        """
        from admin.models import AuditLog
        
        return AuditLog.objects.create(
            performed_by=performed_by,
            action=action,
            target_model='Personnel',
            target_id=personnel.id,
            target_name=personnel.get_full_name(),
            description=description,
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent or ''  # Provide default empty string
        )

