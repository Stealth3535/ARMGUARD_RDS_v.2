"""
Admin Models - Audit logging and tracking
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class AuditLog(models.Model):
    """Track all administrative actions for accountability"""
    
    ACTION_CREATE = 'CREATE'
    ACTION_UPDATE = 'UPDATE'
    ACTION_DELETE = 'DELETE'
    ACTION_LOGIN = 'LOGIN'
    ACTION_LOGOUT = 'LOGOUT'
    ACTION_STATUS_CHANGE = 'STATUS_CHANGE'
    ACTION_ITEM_EDIT = 'ITEM_EDIT'
    ACTION_ITEM_DELETE = 'ITEM_DELETE'
    ACTION_USER_EDIT = 'USER_EDIT'
    ACTION_USER_DELETE = 'USER_DELETE'
    ACTION_PERSONNEL_EDIT = 'PERSONNEL_EDIT'
    ACTION_PERSONNEL_DELETE = 'PERSONNEL_DELETE'
    
    ACTION_CHOICES = [
        (ACTION_CREATE, 'Create'),
        (ACTION_UPDATE, 'Update'),
        (ACTION_DELETE, 'Delete'),
        (ACTION_LOGIN, 'Login'),
        (ACTION_LOGOUT, 'Logout'),
        (ACTION_STATUS_CHANGE, 'Status Change'),
        (ACTION_ITEM_EDIT, 'Item Edit'),
        (ACTION_ITEM_DELETE, 'Item Delete'),
        (ACTION_USER_EDIT, 'User Edit'),
        (ACTION_USER_DELETE, 'User Delete'),
        (ACTION_PERSONNEL_EDIT, 'Personnel Edit'),
        (ACTION_PERSONNEL_DELETE, 'Personnel Delete'),
    ]
    
    # Who performed the action
    performed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='audit_logs_performed'
    )
    
    # What action was performed
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # What was affected
    target_model = models.CharField(max_length=100, help_text="Model name (User, Personnel, etc.)")
    target_id = models.CharField(max_length=100, help_text="ID of the affected record")
    target_name = models.CharField(max_length=255, help_text="Name/identifier of the affected record")
    
    # Details
    description = models.TextField(help_text="Detailed description of the action")
    changes = models.JSONField(null=True, blank=True, help_text="Before/after values for updates")
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['target_model', 'target_id']),
            models.Index(fields=['performed_by', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} on {self.target_model} by {self.performed_by} at {self.timestamp}"


class DeletedRecord(models.Model):
    """Store information about deleted records for recovery/audit purposes"""
    
    # Deletion metadata
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    deleted_at = models.DateTimeField(default=timezone.now)
    
    # Record information
    model_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    record_name = models.CharField(max_length=255, default='', help_text="Name/identifier of deleted record")
    record_data = models.JSONField(help_text="Complete record data before deletion")
    
    # Reason for deletion
    reason = models.TextField(blank=True)
    deletion_reason = models.TextField(blank=True, help_text="Reason for deletion (alias for compatibility)")
    
    class Meta:
        ordering = ['-deleted_at']
        indexes = [
            models.Index(fields=['-deleted_at']),
            models.Index(fields=['model_name', 'record_id']),
        ]
    
    def __str__(self):
        return f"{self.model_name} (ID: {self.record_id}) deleted by {self.deleted_by} at {self.deleted_at}"
