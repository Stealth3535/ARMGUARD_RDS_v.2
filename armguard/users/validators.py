"""
Custom validators for user input
"""
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import re


def validate_username(username):
    """Validate username format"""
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValidationError('Username can only contain letters, numbers, and underscores.')
    
    if len(username) < 3:
        raise ValidationError('Username must be at least 3 characters long.')


def validate_phone_number(phone_number):
    """Validate phone number format"""
    if phone_number:
        pattern = r'^\+?1?\d{9,15}$'
        if not re.match(pattern, phone_number):
            raise ValidationError('Enter a valid phone number.')


def validate_badge_number(badge_number):
    """Validate badge number format"""
    if badge_number:
        if not re.match(r'^[A-Z0-9]+$', badge_number):
            raise ValidationError('Badge number must contain only uppercase letters and numbers.')
        
        if len(badge_number) < 3:
            raise ValidationError('Badge number must be at least 3 characters long.')


def validate_unique_email(email):
    """Validate email uniqueness"""
    if User.objects.filter(email=email).exists():
        raise ValidationError('A user with this email already exists.')