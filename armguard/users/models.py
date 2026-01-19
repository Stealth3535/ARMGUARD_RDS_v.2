from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import FileExtensionValidator


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    badge_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    is_armorer = models.BooleanField(default=False)
    profile_picture = models.ImageField(
        upload_to='users/profile_pictures/', 
        blank=True, 
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif'])],
        help_text='Profile picture (JPG, PNG, or GIF format)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - Profile"
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
