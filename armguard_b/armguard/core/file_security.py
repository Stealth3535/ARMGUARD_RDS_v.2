"""
Secure file upload utilities for ArmGuard
Prevents path traversal attacks and validates file uploads
"""
import os
import uuid
from django.utils.text import get_valid_filename
from django.core.exceptions import ValidationError
from PIL import Image


def secure_upload_path(instance, filename, subfolder=''):
    """
    Generate secure upload path to prevent path traversal attacks
    
    Args:
        instance: Model instance
        filename: Original filename
        subfolder: Optional subfolder for organization
    
    Returns:
        Safe upload path
    """
    # Sanitize filename to prevent path traversal
    filename = get_valid_filename(filename)
    
    # Remove any remaining path separators
    filename = os.path.basename(filename)
    
    # Generate unique filename to prevent conflicts and reduce guessability
    name, ext = os.path.splitext(filename)
    unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
    
    # Build safe path
    if subfolder:
        subfolder = get_valid_filename(subfolder)
        return os.path.join(subfolder, str(instance.pk) if instance.pk else 'temp', unique_name)
    else:
        return os.path.join(str(instance.pk) if instance.pk else 'temp', unique_name)


def validate_image_file(uploaded_file):
    """
    Validate uploaded image files to prevent malicious uploads
    
    Args:
        uploaded_file: Django UploadedFile instance
        
    Raises:
        ValidationError: If file is invalid or potentially malicious
    """
    # Check file size (5MB max)
    max_size = 5 * 1024 * 1024  # 5MB
    if uploaded_file.size > max_size:
        raise ValidationError(f"File too large. Maximum size is {max_size / (1024*1024):.1f}MB.")
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        raise ValidationError("Only JPG, JPEG, PNG, and GIF files are allowed.")
    
    # Validate actual file content (not just extension)
    try:
        # Reset file pointer
        uploaded_file.seek(0)
        
        # Try to open and verify image
        with Image.open(uploaded_file) as img:
            # Verify image format matches extension
            if img.format not in ['JPEG', 'PNG', 'GIF']:
                raise ValidationError("Invalid image format.")
            
            # Check image dimensions (prevent extremely large images)
            max_width, max_height = 2048, 2048
            if img.width > max_width or img.height > max_height:
                raise ValidationError(f"Image too large. Maximum dimensions: {max_width}x{max_height}px.")
        
        # Reset file pointer for further processing
        uploaded_file.seek(0)
        
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError("Invalid image file or corrupted data.")


# Secure upload path functions for specific models
def user_profile_upload_path(instance, filename):
    """Secure upload path for user profile pictures"""
    return secure_upload_path(instance, filename, 'profile_pictures')


def personnel_photo_upload_path(instance, filename):
    """Secure upload path for personnel photos"""
    return secure_upload_path(instance, filename, 'personnel_photos')


def qr_code_upload_path(instance, filename):
    """Secure upload path for QR code images"""
    return secure_upload_path(instance, filename, 'qr_codes')