"""
Admin Signals - Centralized signal handlers for all apps
Handles QR code generation, file cleanup, and comprehensive audit logging
"""

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
import os

# Import cache invalidation
try:
    from core.cache_utils import invalidate_dashboard_cache
except ImportError:
    # Fallback if cache_utils not available
    def invalidate_dashboard_cache():
        pass


# ============================================================================
# Personnel Signals with Audit Logging
# ============================================================================

@receiver(pre_save, sender='personnel.Personnel')
def personnel_pre_save_handler(sender, instance, **kwargs):
    """
    Store old instance data before save for change tracking.
    This is called before the save() method.
    """
    if instance.pk:
        # Existing record - fetch old data for comparison
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            # Store old instance as temporary attribute for post_save signal
            instance._old_instance = old_instance
        except sender.DoesNotExist:
            instance._old_instance = None
    else:
        # New record
        instance._old_instance = None


@receiver(post_save, sender='personnel.Personnel')
def personnel_post_save_with_audit(sender, instance, created, **kwargs):
    """
    Generate QR code and create audit log after personnel save.
    This integrates audit logging with QR code generation.
    """
    # Skip if this is a recursive call from QR save
    if getattr(instance, '_skip_post_save', False):
        return
        
    from qr_manager.models import QRCodeImage
    from admin.models import AuditLog
    
    # 1. Generate/update QR code (existing functionality)
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
        # Use update_fields to avoid triggering additional signals
        qr_obj.save(update_fields=['qr_data', 'is_active', 'deleted_at'])
    
    # 2. Create audit log entry
    try:
        if created:
            # New personnel created
            action = AuditLog.ACTION_CREATE
            description = f"Created personnel: {instance.get_full_name()} ({instance.rank or 'No Rank'}) - {instance.serial}"
            changes = {
                'created': {
                    'surname': instance.surname,
                    'firstname': instance.firstname,
                    'middle_initial': instance.middle_initial or '',
                    'rank': instance.rank or '',
                    'serial': instance.serial,
                    'group': instance.group,
                    'classification': instance.classification,
                    'tel': instance.tel,
                    'status': instance.status,
                }
            }
        else:
            # Existing personnel updated
            action = AuditLog.ACTION_PERSONNEL_EDIT
            old_instance = getattr(instance, '_old_instance', None)
            
            if old_instance:
                # Get field-level changes
                changes = instance.get_field_changes(old_instance)
                
                if changes:
                    # Build description from changes
                    change_list = [f"{field}: '{changes[field]['old']}' → '{changes[field]['new']}'" 
                                   for field in changes.keys()]
                    description = f"Updated personnel: {instance.get_full_name()}. Changes: {', '.join(change_list[:3])}"
                    if len(change_list) > 3:
                        description += f" and {len(change_list) - 3} more fields"
                else:
                    # No actual changes detected (probably just save() called)
                    description = f"Personnel record accessed/saved: {instance.get_full_name()}"
                    changes = {}
            else:
                description = f"Updated personnel: {instance.get_full_name()}"
                changes = {}
        
        # Create the audit log (only if we have a performer)
        if hasattr(instance, '_audit_user') and instance._audit_user:
            AuditLog.objects.create(
                performed_by=instance._audit_user,
                action=action,
                target_model='Personnel',
                target_id=instance.id,
                target_name=instance.get_full_name(),
                description=description,
                changes=changes,
                ip_address=getattr(instance, '_audit_ip', None),
                user_agent=getattr(instance, '_audit_user_agent', '')
            )
        elif instance.modified_by:
            # Fallback to modified_by field
            AuditLog.objects.create(
                performed_by=instance.modified_by,
                action=action,
                target_model='Personnel',
                target_id=instance.id,
                target_name=instance.get_full_name(),
                description=description,
                changes=changes,
                ip_address=None,
                user_agent=''
            )
        
        # Invalidate dashboard cache when personnel changes
        invalidate_dashboard_cache()
        
    except Exception as e:
        # Don't let audit logging failure break the save operation
        import logging
        logger = logging.getLogger('admin.signals')
        logger.error(f"Failed to create audit log for personnel {instance.id}: {e}")
    
    # Clean up temporary attribute
    if hasattr(instance, '_old_instance'):
        delattr(instance, '_old_instance')


@receiver(pre_delete, sender='personnel.Personnel')
def delete_personnel_with_audit(sender, instance, **kwargs):
    """
    Delete personnel files and create audit log before personnel deletion.
    This is a HARD delete - rarely used since soft delete is preferred.
    """
    from qr_manager.models import QRCodeImage
    from admin.models import AuditLog, DeletedRecord
    
    # 1. Create audit log for deletion
    try:
        performed_by = getattr(instance, '_audit_user', None) or instance.modified_by
        
        if performed_by:
            AuditLog.objects.create(
                performed_by=performed_by,
                action=AuditLog.ACTION_PERSONNEL_DELETE,
                target_model='Personnel',
                target_id=instance.id,
                target_name=instance.get_full_name(),
                description=f"HARD DELETE of personnel: {instance.get_full_name()} ({instance.rank or 'No Rank'}) - {instance.serial}",
                changes={
                    'deleted_record': {
                        'id': instance.id,
                        'name': instance.get_full_name(),
                        'rank': instance.rank or '',
                        'serial': instance.serial,
                        'classification': instance.classification,
                        'status': instance.status,
                    }
                },
                ip_address=getattr(instance, '_audit_ip', None),
                user_agent=getattr(instance, '_audit_user_agent', '')
            )
            
            # 2. Store in DeletedRecord for recovery
            DeletedRecord.objects.create(
                deleted_by=performed_by,
                deleted_at=timezone.now(),
                model_name='Personnel',
                record_id=instance.id,
                record_name=instance.get_full_name(),
                record_data={
                    'id': instance.id,
                    'surname': instance.surname,
                    'firstname': instance.firstname,
                    'middle_initial': instance.middle_initial,
                    'rank': instance.rank,
                    'serial': instance.serial,
                    'group': instance.group,
                    'tel': instance.tel,
                    'classification': instance.classification,
                    'status': instance.status,
                    'registration_date': str(instance.registration_date),
                    'qr_code': instance.qr_code,
                },
                reason=getattr(instance, '_deletion_reason', 'Hard delete - personnel permanently removed')
            )
    except Exception as e:
        import logging
        logger = logging.getLogger('admin.signals')
        logger.error(f"Failed to create deletion audit log for personnel {instance.id}: {e}")
    
    # 3. Delete personnel picture file if it exists
    if instance.picture:
        if os.path.isfile(instance.picture.path):
            os.remove(instance.picture.path)
    
    # 4. Delete all QR codes associated with this personnel
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


# ============================================================================
# Inventory/Item Signals with Audit Logging
# ============================================================================


@receiver(post_save, sender='inventory.Item')
def generate_item_qr_code(sender, instance, created, **kwargs):
    """Generate QR code for item after save"""
    # Skip if this is a recursive call
    if getattr(instance, '_skip_post_save', False):
        return
        
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
        qr_obj.save(update_fields=['qr_data'])
    
    # Invalidate dashboard cache when items change
    invalidate_dashboard_cache()


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
    
    # Skip if this is a recursive call
    if getattr(instance, '_skip_profile_save', False):
        return
    
    if hasattr(instance, 'userprofile'):
        # Prevent recursive signal firing
        instance._skip_profile_save = True
        try:
            instance.userprofile.save()
        finally:
            instance._skip_profile_save = False
