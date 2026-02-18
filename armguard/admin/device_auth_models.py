"""
Device Authorization Request Models
Stores device authorization requests and approval history
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


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
        middleware = DeviceAuthorizationMiddleware(lambda req: None)
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
