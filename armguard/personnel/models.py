"""
Personnel Models for ArmGuard
Based on APP/app/backend/database.py personnel table
"""
from django.db import models
from django.core.validators import RegexValidator, FileExtensionValidator
from django.utils import timezone
from django.contrib.auth.models import User


class Personnel(models.Model):
    """Personnel model - Military personnel in the armory system"""
    
    # Status choices
    STATUS_ACTIVE = 'Active'
    STATUS_INACTIVE = 'Inactive'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
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
    
    # Office choices
    OFFICE_CHOICES = [
        ('HAS', 'HAS'),
        ('951', '951'),
        ('952', '952'),
        ('953', '953'),
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
    rank = models.CharField(max_length=20, choices=ALL_RANKS)
    serial = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Serial number (6 digits for enlisted, or O-XXXXXX for officers)"
    )
    office = models.CharField(max_length=10, choices=OFFICE_CHOICES)
    
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
    picture = models.ImageField(
        upload_to='personnel/pictures/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])]
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'personnel'
        ordering = ['surname', 'firstname']
        verbose_name = 'Personnel'
        verbose_name_plural = 'Personnel'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.rank})"
    
    def get_full_name(self):
        """Return full name with middle initial"""
        if self.middle_initial:
            return f"{self.firstname} {self.middle_initial}. {self.surname}"
        return f"{self.firstname} {self.surname}"
    
    def is_officer(self):
        """Check if personnel is an officer"""
        return self.serial.startswith('O-') or self.rank in [r[0] for r in self.RANKS_OFFICER]
    
    def get_personnel_class(self):
        """Return personnel class - EP for Enlisted, O for Officer"""
        return 'O' if self.is_officer() else 'EP'
    
    def save(self, *args, **kwargs):
        """Override save to generate ID if not set and capitalize officer names"""
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

        if not self.id:
            # Generate ID: PE/PO + serial + DDMMYY
            prefix = 'PO' if self.is_officer() else 'PE'
            date_suffix = timezone.now().strftime('%d%m%y')
            clean_serial = self.serial.replace('O-', '') if self.is_officer() else self.serial
            self.id = f"{prefix}-{clean_serial}{date_suffix}"
        # Set QR code to ID if not set
        if not self.qr_code:
            self.qr_code = self.id
        super().save(*args, **kwargs)

