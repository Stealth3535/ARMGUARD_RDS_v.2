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
        
        # v2: create or activate an AuthorizedDevice record.
        from core.device.models import AuthorizedDevice as _V2Dev, DeviceAuditEvent as _V2Audit
        import secrets as _sec
        _tier_map = {
            'DEVELOPMENT': _V2Dev.SecurityTier.STANDARD,
            'STANDARD':    _V2Dev.SecurityTier.STANDARD,
            'HIGH':        _V2Dev.SecurityTier.HIGH_SECURITY,
            'HIGH_SECURITY': _V2Dev.SecurityTier.HIGH_SECURITY,
            'MILITARY':    _V2Dev.SecurityTier.MILITARY,
        }
        v2_tier = _tier_map.get(self.security_level, _V2Dev.SecurityTier.STANDARD)
        try:
            v2_dev = _V2Dev.objects.filter(
                ip_last_seen=self.ip_address,
            ).order_by('-enrolled_at').first()
            if v2_dev:
                v2_dev.status       = _V2Dev.Status.ACTIVE
                v2_dev.device_name  = self.device_name
                v2_dev.security_tier = v2_tier
                v2_dev.can_transact = self.can_transact
                v2_dev.max_daily_transactions = self.max_daily_transactions
                v2_dev.authorized_at = timezone.now()
                v2_dev.reviewed_by   = reviewer
                v2_dev.reviewed_at   = timezone.now()
                v2_dev.save(update_fields=[
                    'status', 'device_name', 'security_tier', 'can_transact',
                    'max_daily_transactions', 'authorized_at', 'reviewed_by', 'reviewed_at',
                ])
                _V2Audit.log(v2_dev, 'ACTIVATED', reviewer,
                             notes=f'Approved via DeviceAuthorizationRequest #{self.pk}')
            else:
                v2_dev = _V2Dev.objects.create(
                    device_token=_sec.token_hex(32),
                    device_name=self.device_name,
                    user=self.requested_by,
                    ip_first_seen=self.ip_address,
                    ip_last_seen=self.ip_address,
                    status=_V2Dev.Status.ACTIVE,
                    security_tier=v2_tier,
                    can_transact=self.can_transact,
                    max_daily_transactions=self.max_daily_transactions,
                    authorized_at=timezone.now(),
                    reviewed_by=reviewer,
                    reviewed_at=timezone.now(),
                    enrollment_reason=(
                        f'Approved DeviceAuthorizationRequest #{self.pk}: {self.reason}'
                    ),
                )
                _V2Audit.log(v2_dev, 'ACTIVATED', reviewer,
                             notes=f'Created via DeviceAuthorizationRequest #{self.pk}')
        except Exception:
            pass
    
    def reject(self, reviewer, notes=''):
        """Reject the device authorization request"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
