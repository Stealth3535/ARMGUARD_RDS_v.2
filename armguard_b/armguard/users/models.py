from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from core.file_security import user_profile_upload_path, validate_image_file


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
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
    profile_picture = models.ImageField(
        upload_to=user_profile_upload_path,  # Secure upload path
        blank=True, 
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif']),
            validate_image_file  # Content validation
        ],
        help_text='Profile picture (JPG, PNG, or GIF format, max 5MB)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Profile"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


# Signal handlers moved to admin/signals.py for centralized management
