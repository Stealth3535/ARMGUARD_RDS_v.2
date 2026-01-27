"""
Admin Signals - Centralized signal handlers for all apps
Handles QR code generation and file cleanup on deletion
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
import os


@receiver(post_save, sender='personnel.Personnel')
def generate_personnel_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for personnel after save"""
    from qr_manager.models import QRCodeImage
    
    # Create/update QRCodeImage for this personnel
    # Use all_objects to check for inactive QR codes too
    qr_obj, created_qr = QRCodeImage.all_objects.get_or_create(
        qr_type=QRCodeImage.TYPE_PERSONNEL,
        reference_id=instance.id,
        defaults={
            'qr_data': instance.id,
            'is_active': True if not instance.deleted_at else False,
        }
    )
    
    # Update qr_data and reactivate if personnel was restored
    if qr_obj.qr_data != instance.id or (not instance.deleted_at and not qr_obj.is_active):
        qr_obj.qr_data = instance.id
        if not instance.deleted_at:
            qr_obj.is_active = True
            qr_obj.deleted_at = None
        qr_obj.save()


@receiver(pre_delete, sender='personnel.Personnel')
def delete_personnel_files(sender, instance, **kwargs):
    """Delete personnel picture and QR codes before personnel deletion"""
    from qr_manager.models import QRCodeImage
    
    # Delete personnel picture file if it exists
    if instance.picture:
        if os.path.isfile(instance.picture.path):
            os.remove(instance.picture.path)
    
    # Delete all QR codes associated with this personnel
    qr_codes = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_PERSONNEL,
        reference_id=instance.id
    )
    for qr_code in qr_codes:
        # Delete QR image file if it exists
        if qr_code.qr_image:
            if os.path.isfile(qr_code.qr_image.path):
                os.remove(qr_code.qr_image.path)
        # Delete QR code record
        qr_code.delete()


@receiver(post_save, sender='inventory.Item')
def generate_item_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for item after save"""
    from qr_manager.models import QRCodeImage
    
    # Create/update QRCodeImage for this item
    # Use all_objects to check for inactive QR codes too
    qr_obj, created_qr = QRCodeImage.all_objects.get_or_create(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=instance.id,
        defaults={
            'qr_data': instance.id,
        }
    )
    # Update qr_data if needed
    if qr_obj.qr_data != instance.id:
        qr_obj.qr_data = instance.id
        qr_obj.save()


@receiver(pre_delete, sender='inventory.Item')
def delete_item_qr_codes(sender, instance, **kwargs):
    """Delete QR codes before item deletion"""
    from qr_manager.models import QRCodeImage
    
    # Delete all QR codes associated with this item
    qr_codes = QRCodeImage.objects.filter(
        qr_type=QRCodeImage.TYPE_ITEM,
        reference_id=instance.id
    )
    for qr_code in qr_codes:
        # Delete QR image file if it exists
        if qr_code.qr_image:
            if os.path.isfile(qr_code.qr_image.path):
                os.remove(qr_code.qr_image.path)
        # Delete QR code record
        qr_code.delete()


@receiver(pre_delete, sender='users.UserProfile')
def delete_userprofile_picture(sender, instance, **kwargs):
    """Delete profile picture file before UserProfile deletion"""
    if instance.profile_picture:
        if os.path.isfile(instance.profile_picture.path):
            os.remove(instance.profile_picture.path)


@receiver(pre_delete, sender=User)
def soft_delete_personnel_on_user_delete(sender, instance, **kwargs):
    """Soft delete linked personnel when user is deleted"""
    from personnel.models import Personnel
    
    # Check if user has linked personnel
    try:
        personnel = Personnel.all_objects.get(user=instance)
        # Soft delete the personnel (keeps record, deactivates QR)
        personnel.soft_delete()
    except Personnel.DoesNotExist:
        pass


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create user profile when user is created"""
    from users.models import UserProfile
    
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    from users.models import UserProfile
    
    if hasattr(instance, 'userprofile'):
        instance.userprofile.save()
