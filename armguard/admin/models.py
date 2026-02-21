"""
Admin Models - Audit logging and tracking
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import subprocess
import tempfile
from pathlib import Path


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
    mac_address = models.CharField(max_length=64, blank=True, help_text="MAC address of the requesting network interface")
    pc_username = models.CharField(max_length=255, blank=True, help_text="OS login username of the requesting PC")
    system_specs = models.JSONField(default=dict, blank=True, help_text="Auto-collected hardware/OS specs (CPU cores, RAM, OS, screen, etc.)")

    # Request Information
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    reason = models.TextField(help_text="Why do you need authorization for this device?")
    csr_pem = models.TextField(blank=True, help_text="Optional PEM CSR submitted by requesting device")
    
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
    issued_certificate_pem = models.TextField(blank=True)
    issued_certificate_serial = models.CharField(max_length=128, blank=True)
    issued_certificate_issued_at = models.DateTimeField(null=True, blank=True)
    issued_certificate_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name = 'Device Authorization Request'
        verbose_name_plural = 'Device Authorization Requests'
    
    def __str__(self):
        return f"{self.device_fingerprint[:16]}... - {self.status}"

    def _run_openssl(self, command_args):
        try:
            return subprocess.run(
                command_args,
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as command_error:
            raise ValueError("OpenSSL binary is not installed on the server") from command_error
        except subprocess.CalledProcessError as command_error:
            stderr = (command_error.stderr or '').strip()
            raise ValueError(f"OpenSSL command failed: {stderr}") from command_error

    def _issue_client_certificate_from_csr(self):
        csr_content = (self.csr_pem or '').strip()
        if not csr_content:
            return None, None

        ca_cert_path = Path(getattr(settings, 'MTLS_CLIENT_CA_CERT_PATH', ''))
        ca_key_path = Path(getattr(settings, 'MTLS_CLIENT_CA_KEY_PATH', ''))
        validity_days = int(getattr(settings, 'MTLS_CLIENT_CERT_VALIDITY_DAYS', 365))

        if not ca_cert_path.exists() or not ca_key_path.exists():
            raise ValueError(
                f"mTLS CA files are not configured correctly. Expected cert at {ca_cert_path} and key at {ca_key_path}."
            )

        with tempfile.TemporaryDirectory() as work_dir:
            work_dir_path = Path(work_dir)
            csr_path = work_dir_path / 'device.csr'
            cert_path = work_dir_path / 'device.crt'
            ext_path = work_dir_path / 'client.ext'

            csr_path.write_text(csr_content, encoding='utf-8')
            ext_path.write_text(
                "\n".join([
                    "basicConstraints=CA:FALSE",
                    "keyUsage = digitalSignature, keyEncipherment",
                    "extendedKeyUsage = clientAuth",
                    f"subjectAltName = URI:armguard-device:{self.device_fingerprint}",
                ]),
                encoding='utf-8',
            )

            self._run_openssl(['openssl', 'req', '-in', str(csr_path), '-noout'])
            self._run_openssl([
                'openssl', 'x509', '-req',
                '-in', str(csr_path),
                '-CA', str(ca_cert_path),
                '-CAkey', str(ca_key_path),
                '-CAcreateserial',
                '-out', str(cert_path),
                '-days', str(validity_days),
                '-sha256',
                '-extfile', str(ext_path),
            ])

            cert_pem = cert_path.read_text(encoding='utf-8')
            serial_output = self._run_openssl([
                'openssl', 'x509', '-in', str(cert_path), '-noout', '-serial'
            ]).stdout.strip()
            cert_serial = serial_output.split('=', 1)[1] if '=' in serial_output else serial_output

        return cert_pem, cert_serial
    
    def approve(self, reviewer, device_name, security_level='STANDARD', notes=''):
        """Approve the device authorization request"""
        self.status = 'approved'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.device_name = device_name
        self.security_level = security_level

        cert_pem, cert_serial = self._issue_client_certificate_from_csr()
        if cert_pem:
            self.issued_certificate_pem = cert_pem
            self.issued_certificate_serial = cert_serial or ''
            self.issued_certificate_issued_at = timezone.now()
            self.issued_certificate_downloaded_at = None

        self.save()

        # v2: create or activate the matching AuthorizedDevice record.
        from core.device.models import AuthorizedDevice as _V2Dev, DeviceAuditEvent as _V2Audit
        import secrets as _sec
        _tier_map = {
            'DEVELOPMENT':   _V2Dev.SecurityTier.STANDARD,
            'STANDARD':      _V2Dev.SecurityTier.STANDARD,
            'HIGH':          _V2Dev.SecurityTier.HIGH_SECURITY,
            'HIGH_SECURITY': _V2Dev.SecurityTier.HIGH_SECURITY,
            'MILITARY':      _V2Dev.SecurityTier.MILITARY,
        }
        v2_tier = _tier_map.get(self.security_level, _V2Dev.SecurityTier.STANDARD)
        try:
            v2_dev = _V2Dev.objects.filter(
                ip_last_seen=self.ip_address,
            ).order_by('-enrolled_at').first()
            if v2_dev:
                v2_dev.status        = _V2Dev.Status.ACTIVE
                v2_dev.device_name   = self.device_name
                v2_dev.security_tier = v2_tier
                v2_dev.can_transact  = self.can_transact
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

        # Clear any stale lockout/attempt counters for this device after approval.
        cache.delete(f"device_lockout_{self.device_fingerprint}")
        cache.delete(f"device_attempts_{self.device_fingerprint}")
    
    def reject(self, reviewer, notes=''):
        """Reject the device authorization request"""
        self.status = 'rejected'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()


class DeviceAccessLog(models.Model):
    """Persistent forensic log of device authorization checks."""

    SECURITY_LEVEL_CHOICES = [
        ('STANDARD', 'Standard'),
        ('RESTRICTED', 'Restricted'),
        ('HIGH_SECURITY', 'High Security'),
    ]

    checked_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='device_access_logs'
    )

    path = models.CharField(max_length=500)
    method = models.CharField(max_length=10)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_fingerprint = models.CharField(max_length=64)
    user_agent = models.TextField(blank=True)

    security_level = models.CharField(max_length=20, choices=SECURITY_LEVEL_CHOICES, default='RESTRICTED')
    is_authorized = models.BooleanField(default=False)
    reason = models.CharField(max_length=255, blank=True)
    response_status = models.PositiveSmallIntegerField(default=200)

    class Meta:
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['-checked_at']),
            models.Index(fields=['device_fingerprint', '-checked_at']),
            models.Index(fields=['is_authorized', '-checked_at']),
            models.Index(fields=['ip_address', '-checked_at']),
        ]

    def __str__(self):
        decision = 'AUTHORIZED' if self.is_authorized else 'BLOCKED'
        return f"{decision} {self.method} {self.path} ({self.ip_address})"
