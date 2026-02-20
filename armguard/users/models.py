from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone_number = models.CharField(
        max_length=11, 
        blank=True, 
        null=True,
        help_text="11-digit mobile number (e.g., 09171234567)"
    )
    GROUP_CHOICES = [
        ('HAS', 'HAS'),
        ('951st', '951st'),
        ('952nd', '952nd'),
        ('953rd', '953rd'),
    ]
    group = models.CharField(
        max_length=10, 
        choices=GROUP_CHOICES,
        blank=True, 
        null=True
    )
    badge_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    is_armorer = models.BooleanField(default=False)
    is_restricted_admin = models.BooleanField(
        default=False,
        help_text="If True, administrator can only view but not edit/delete/create"
    )
    last_session_key = models.CharField(
        max_length=40,
        blank=True,
        null=True,
        help_text="Track last session for single session enforcement"
    )
    profile_picture = models.ImageField(
        upload_to='users/profile_pictures/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])],
        help_text='Profile picture (JPG, PNG, or GIF format)'
    )
    # TOTP secret for device enrollment MFA (base32 encoded, set by TOTPService)
    totp_secret = models.CharField(max_length=64, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Profile"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# Signal handlers moved to admin/signals.py for centralized management
