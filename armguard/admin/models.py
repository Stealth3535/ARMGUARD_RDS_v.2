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


class DeviceAuthorizationRequest(models.Model):
    """Model to store device authorization requests"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    SECURITY_LEVEL_CHOICES = [
        ('DEVELOPMENT', 'Development'),
        ('STANDARD', 'Standard'),
        ('HIGH', 'High Security'),
        ('MILITARY', 'Military Grade'),
    ]
    
    # Device Information
    device_fingerprint = models.CharField(max_length=64, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    hostname = models.CharField(max_length=255, blank=True)
    
    # Request Information
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(help_text="Why do you need authorization for this device?")
    
    # Approval Information
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='device_reviews')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    
    # Device Configuration (set upon approval)
    device_name = models.CharField(max_length=255, blank=True)
    security_level = models.CharField(max_length=20, choices=SECURITY_LEVEL_CHOICES, default='STANDARD')
    can_transact = models.BooleanField(default=True)
    max_daily_transactions = models.IntegerField(default=50)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Device Authorization Request'
        verbose_name_plural = 'Device Authorization Requests'
    
    def __str__(self):
        return f"{self.device_fingerprint[:16]}... - {self.status}"
    
    def approve(self, reviewer, device_name, security_level='STANDARD', notes=''):
        """Approve the device authorization request"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.device_name = device_name
        self.security_level = security_level
        self.save()
        
        # Add device to authorized_devices.json
        from core.middleware.device_authorization import DeviceAuthorizationMiddleware
        middleware = DeviceAuthorizationMiddleware(None)
        middleware.load_authorized_devices()
        middleware.authorize_device(
            device_fingerprint=self.device_fingerprint,
            device_name=self.device_name,
            ip_address=self.ip_address,
            description=f"Requested by {self.requested_by.username}: {self.reason}",
            can_transact=self.can_transact,
            security_level=self.security_level,
            roles=[],
            max_daily_transactions=self.max_daily_transactions
        )
    
    def reject(self, reviewer, notes=''):
        """Reject the device authorization request"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
