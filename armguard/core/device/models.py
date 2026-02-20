"""
ARMGUARD Enterprise Device Authorization Models
================================================
Replaces the flat authorized_devices.json store with a fully relational,
auditable, lifecycle-aware database schema.

Design Principles:
  - Zero Trust: every request re-evaluated; no implicit persistent trust
  - NIST SP 800-63B / NIST SP 800-207 alignment
  - OWASP ASVS v4.0 Level-2 compliance target
  - Full audit trail on every state transition
"""

import uuid
import secrets
import hashlib
from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

def _default_expires_at():
    """Default expiry: 90 days from now (configurable via DEVICE_AUTH_EXPIRY_DAYS)."""
    days = getattr(settings, 'DEVICE_AUTH_EXPIRY_DAYS', 90)
    return timezone.now() + timedelta(days=days)


def _generate_device_token():
    """Cryptographically secure 64-char hex token used as the device identity anchor."""
    return secrets.token_hex(32)


# ---------------------------------------------------------------------------
# AuthorizedDevice — core entity
# ---------------------------------------------------------------------------

class AuthorizedDevice(models.Model):
    """
    Represents a single physical device that has been granted access.

    Lifecycle states:
        PENDING_MFA  → awaiting MFA verification by the requesting user
        PENDING      → MFA passed; awaiting admin approval
        ACTIVE       → approved and within expiry window
        EXPIRED      → past expires_at; requires re-validation
        REVOKED      → manually or automatically revoked
        SUSPENDED    → temporarily disabled pending review
    """

    class Status(models.TextChoices):
        PENDING_MFA  = 'PENDING_MFA',  'Pending MFA Verification'
        PENDING      = 'PENDING',      'Pending Admin Approval'
        ACTIVE       = 'ACTIVE',       'Active'
        EXPIRED      = 'EXPIRED',      'Expired'
        REVOKED      = 'REVOKED',      'Revoked'
        SUSPENDED    = 'SUSPENDED',    'Suspended'

    class SecurityTier(models.TextChoices):
        STANDARD      = 'STANDARD',      'Standard'
        RESTRICTED    = 'RESTRICTED',    'Restricted'
        HIGH_SECURITY = 'HIGH_SECURITY', 'High Security'
        MILITARY      = 'MILITARY',      'Military Grade'

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Stable token set on enrollment; rotatable on compromise.
    # This is the cryptographic anchor — replaces cookie + header fingerprint.
    device_token = models.CharField(
        max_length=64,
        unique=True,
        default=_generate_device_token,
        help_text="Server-issued device identity token (64-char hex). Never transmitted in plain URL."
    )

    # Optional: base64-encoded DER public key from device-generated key pair.
    # When present, all auth challenges are verified with this key.
    public_key_pem = models.TextField(
        blank=True,
        help_text="PEM public key for challenge-response cryptographic binding (optional)."
    )

    # SHA-256 hash of the public key DER for quick lookup
    public_key_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)

    device_name = models.CharField(max_length=255)
    device_type = models.CharField(
        max_length=64, blank=True,
        help_text="E.g. 'workstation', 'armory-terminal', 'mobile'"
    )

    # ------------------------------------------------------------------
    # Ownership
    # ------------------------------------------------------------------
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authorized_devices',
        help_text="User who enrolled this device."
    )

    # ------------------------------------------------------------------
    # Network identity (informational; NOT used as sole auth factor)
    # ------------------------------------------------------------------
    ip_first_seen = models.GenericIPAddressField(null=True, blank=True)
    ip_last_seen  = models.GenericIPAddressField(null=True, blank=True)

    # Optional strict IP binding (e.g., for fixed armory terminals)
    ip_binding = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="If set, device is only authorized from this exact IP."
    )

    user_agent_hash = models.CharField(
        max_length=64, blank=True,
        help_text="SHA-256[:16] of HTTP_USER_AGENT at registration time."
    )

    # ------------------------------------------------------------------
    # Lifecycle timestamps
    # ------------------------------------------------------------------
    enrolled_at   = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    expires_at    = models.DateTimeField(default=_default_expires_at)
    last_used     = models.DateTimeField(null=True, blank=True)
    revoked_at    = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Authorization state
    # ------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_MFA,
        db_index=True
    )
    security_tier = models.CharField(
        max_length=20,
        choices=SecurityTier.choices,
        default=SecurityTier.HIGH_SECURITY
    )

    # ------------------------------------------------------------------
    # Policy
    # ------------------------------------------------------------------
    can_transact           = models.BooleanField(default=False)
    max_daily_transactions = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(10000)]
    )
    active_hours_start = models.TimeField(null=True, blank=True)
    active_hours_end   = models.TimeField(null=True, blank=True)
    authorized_roles   = models.JSONField(
        default=list, blank=True,
        help_text="List of role names permitted on this device."
    )

    # ------------------------------------------------------------------
    # Risk / anomaly
    # ------------------------------------------------------------------
    risk_score = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="0=clean, 100=maximum risk. Auto-updated by anomaly detection."
    )
    failed_auth_count = models.PositiveIntegerField(default=0)
    locked_until      = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------
    enrollment_reason = models.TextField(
        blank=True, help_text="Requester-provided justification."
    )
    reviewed_by    = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='device_approvals'
    )
    reviewed_at    = models.DateTimeField(null=True, blank=True)
    review_notes   = models.TextField(blank=True)
    revoke_reason  = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Re-validation tracking
    # ------------------------------------------------------------------
    last_revalidated_at    = models.DateTimeField(null=True, blank=True)
    revalidation_required  = models.BooleanField(default=False)

    class Meta:
        app_label           = 'core'
        ordering = ['-enrolled_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['device_token']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['ip_last_seen', '-last_used']),
            models.Index(fields=['risk_score', 'status']),
        ]
        verbose_name        = 'Authorized Device'
        verbose_name_plural = 'Authorized Devices'

    def __str__(self):
        return f"{self.device_name} ({self.user.username}) [{self.status}]"

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        """True only if status is ACTIVE and not expired."""
        if self.status != self.Status.ACTIVE:
            return False
        if timezone.now() > self.expires_at:
            return False
        return True

    @property
    def is_locked(self) -> bool:
        """True if temporary brute-force lockout is in effect."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    @property
    def days_until_expiry(self) -> int | None:
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)

    @property
    def is_expiring_soon(self) -> bool:
        """Within the warning window (default: 14 days)."""
        warning_days = getattr(settings, 'DEVICE_EXPIRY_WARNING_DAYS', 14)
        d = self.days_until_expiry
        return d is not None and d <= warning_days

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def activate(self, reviewer: User, tier: str = None, notes: str = '') -> None:
        """Admin approves the device."""
        self.status        = self.Status.ACTIVE
        self.authorized_at = timezone.now()
        self.reviewed_by   = reviewer
        self.reviewed_at   = timezone.now()
        self.review_notes  = notes
        if tier:
            self.security_tier = tier
        self.save()
        DeviceAuditEvent.log(self, 'ACTIVATED', reviewer, notes)

    def revoke(self, actor: User, reason: str = 'Manual revocation') -> None:
        """Revoke device authorization."""
        self.status       = self.Status.REVOKED
        self.revoked_at   = timezone.now()
        self.revoke_reason = reason
        self.save()
        DeviceAuditEvent.log(self, 'REVOKED', actor, reason)

    def suspend(self, actor: User, reason: str = '') -> None:
        """Temporarily suspend authorization pending review."""
        self.status = self.Status.SUSPENDED
        self.save()
        DeviceAuditEvent.log(self, 'SUSPENDED', actor, reason)

    def expire(self) -> None:
        """Mark as expired (called by management command / celery task)."""
        self.status = self.Status.EXPIRED
        self.save()
        DeviceAuditEvent.log(self, 'EXPIRED', actor=None, notes='Automated expiry')

    def revalidate(self, actor: User) -> None:
        """Reset expiry clock after re-authentication/MFA."""
        days = getattr(settings, 'DEVICE_AUTH_EXPIRY_DAYS', 90)
        self.expires_at           = timezone.now() + timedelta(days=days)
        self.last_revalidated_at  = timezone.now()
        self.revalidation_required = False
        self.status               = self.Status.ACTIVE
        self.risk_score           = max(0, self.risk_score - 10)
        self.save()
        DeviceAuditEvent.log(self, 'REVALIDATED', actor, f'Expiry extended +{days}d')

    def record_use(self, ip: str) -> None:
        """Update last-seen fields on every successful authorization."""
        self.last_used    = timezone.now()
        self.ip_last_seen = ip
        self.save(update_fields=['last_used', 'ip_last_seen'])

    def record_failed_attempt(self, ip: str) -> None:
        """Increment fail counter and apply lockout if threshold reached."""
        self.failed_auth_count += 1
        max_attempts = getattr(settings, 'DEVICE_MAX_FAILED_ATTEMPTS', 5)
        if self.failed_auth_count >= max_attempts:
            lockout_minutes = getattr(settings, 'DEVICE_LOCKOUT_MINUTES', 30)
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
            DeviceAuditEvent.log(
                self, 'LOCKED_OUT', actor=None,
                notes=f'After {self.failed_auth_count} failures from {ip}'
            )
        self.save(update_fields=['failed_auth_count', 'locked_until'])

    def clear_lockout(self) -> None:
        """Manually clear lockout (admin action)."""
        self.locked_until      = None
        self.failed_auth_count = 0
        self.save(update_fields=['locked_until', 'failed_auth_count'])

    def bump_risk(self, delta: int, reason: str = '') -> None:
        """Increase risk score, capped at 100."""
        self.risk_score = min(100, self.risk_score + delta)
        self.save(update_fields=['risk_score'])
        if reason:
            DeviceAuditEvent.log(self, 'RISK_UPDATED', actor=None, notes=reason)

    def rotate_token(self, actor: User) -> str:
        """Generate a new device token, invalidating the old one."""
        old_token         = self.device_token
        self.device_token = _generate_device_token()
        self.save(update_fields=['device_token'])
        DeviceAuditEvent.log(
            self, 'TOKEN_ROTATED', actor,
            notes=f'Old token prefix: {old_token[:8]}...'
        )
        return self.device_token


# ---------------------------------------------------------------------------
# DeviceAuditEvent — immutable audit trail
# ---------------------------------------------------------------------------

class DeviceAuditEvent(models.Model):
    """
    Append-only log of every state transition and notable event on a device.
    Never modify rows — only INSERT.
    """

    EVENT_CHOICES = [
        ('ENROLLED',       'Device Enrolled'),
        ('MFA_PASSED',     'MFA Challenge Passed'),
        ('MFA_FAILED',     'MFA Challenge Failed'),
        ('ACTIVATED',      'Device Activated'),
        ('REVOKED',        'Device Revoked'),
        ('SUSPENDED',      'Device Suspended'),
        ('EXPIRED',        'Authorization Expired'),
        ('REVALIDATED',    'Device Re-validated'),
        ('LOCKED_OUT',     'Device Locked Out'),
        ('LOCK_CLEARED',   'Lockout Cleared'),
        ('TOKEN_ROTATED',  'Token Rotated'),
        ('RISK_UPDATED',   'Risk Score Updated'),
        ('IP_ANOMALY',     'IP Anomaly Detected'),
        ('AUTH_SUCCESS',   'Authorization Success'),
        ('AUTH_DENIED',    'Authorization Denied'),
    ]

    id         = models.BigAutoField(primary_key=True)
    device     = models.ForeignKey(
        AuthorizedDevice, on_delete=models.CASCADE, related_name='audit_events'
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES, db_index=True)
    actor      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='core_device_audit_events',
        help_text="User who triggered this event (null for automated events)."
    )
    notes      = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)

    # SIEM-compatible structured metadata
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'core'
        ordering = ['-occurred_at']
        indexes  = [
            models.Index(fields=['device', '-occurred_at']),
            models.Index(fields=['event_type', '-occurred_at']),
            models.Index(fields=['actor', '-occurred_at']),
        ]

    def __str__(self):
        return f"{self.event_type} on {self.device_id} at {self.occurred_at}"

    @classmethod
    def log(
        cls,
        device: 'AuthorizedDevice',
        event_type: str,
        actor: User | None = None,
        notes: str = '',
        ip_address: str = None,
        metadata: dict = None,
    ) -> 'DeviceAuditEvent':
        return cls.objects.create(
            device=device,
            event_type=event_type,
            actor=actor,
            notes=notes,
            ip_address=ip_address,
            metadata=metadata or {},
        )


# ---------------------------------------------------------------------------
# DeviceMFAChallenge — TOTP / email OTP enrollment gate
# ---------------------------------------------------------------------------

class DeviceMFAChallenge(models.Model):
    """
    One-time MFA challenge that must be completed before a new device moves
    from PENDING_MFA → PENDING (admin queue).

    Supports:
        TOTP  — user's authenticator app
        EMAIL — one-time code sent to user's email
    """

    class Method(models.TextChoices):
        TOTP  = 'TOTP',  'Authenticator App (TOTP)'
        EMAIL = 'EMAIL', 'Email OTP'

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device     = models.OneToOneField(
        AuthorizedDevice, on_delete=models.CASCADE, related_name='mfa_challenge'
    )
    method     = models.CharField(max_length=10, choices=Method.choices, default=Method.TOTP)

    # For EMAIL method: hashed OTP token
    otp_hash   = models.CharField(max_length=64, blank=True)
    otp_salt   = models.CharField(max_length=32, blank=True)

    attempts   = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'core'
        ordering = ['-created_at']

    def __str__(self):
        return f"MFA challenge ({self.method}) for {self.device}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None

    @property
    def is_exhausted(self) -> bool:
        return self.attempts >= self.max_attempts

    def set_email_otp(self, plaintext_otp: str) -> None:
        """Hash and store an email OTP."""
        self.otp_salt = secrets.token_hex(16)
        self.otp_hash = hashlib.sha256(
            (plaintext_otp + self.otp_salt).encode()
        ).hexdigest()
        self.save(update_fields=['otp_hash', 'otp_salt'])

    def verify_email_otp(self, plaintext_otp: str) -> bool:
        """Verify a submitted OTP. Increments attempt counter on failure."""
        if self.is_expired or self.is_exhausted or self.is_verified:
            return False
        candidate = hashlib.sha256(
            (plaintext_otp + self.otp_salt).encode()
        ).hexdigest()
        if secrets.compare_digest(candidate, self.otp_hash):
            self.verified_at = timezone.now()
            self.save(update_fields=['verified_at'])
            return True
        self.attempts += 1
        self.save(update_fields=['attempts'])
        return False


# ---------------------------------------------------------------------------
# DeviceAccessLog — per-request forensic log (retained from v1)
# ---------------------------------------------------------------------------

class DeviceAccessLog(models.Model):
    """
    Persistent per-request log for forensic analysis and SIEM export.
    One row per authorization check.
    """

    checked_at        = models.DateTimeField(default=timezone.now, db_index=True)
    device            = models.ForeignKey(
        AuthorizedDevice, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='access_logs'
    )
    user              = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='core_device_access_logs'
    )
    path              = models.CharField(max_length=500)
    method            = models.CharField(max_length=10)
    ip_address        = models.GenericIPAddressField(null=True, blank=True)
    device_token_prefix = models.CharField(max_length=8, blank=True,
        help_text="First 8 chars of device_token for correlation without exposing full secret.")
    user_agent        = models.TextField(blank=True)
    security_level    = models.CharField(max_length=20, default='RESTRICTED')
    is_authorized     = models.BooleanField(default=False)
    denial_reason     = models.CharField(max_length=255, blank=True)
    response_status   = models.PositiveSmallIntegerField(default=200)
    risk_score_at_check = models.PositiveSmallIntegerField(default=0)

    # SIEM-compatible JSON blob for structured log export
    siem_metadata     = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = 'core'
        ordering = ['-checked_at']
        indexes  = [
            models.Index(fields=['-checked_at']),
            models.Index(fields=['device', '-checked_at']),
            models.Index(fields=['is_authorized', '-checked_at']),
            models.Index(fields=['ip_address', '-checked_at']),
            models.Index(fields=['user', '-checked_at']),
        ]

    def __str__(self):
        verdict = 'AUTHORIZED' if self.is_authorized else 'BLOCKED'
        return f"{verdict} {self.method} {self.path} ({self.ip_address})"


# ---------------------------------------------------------------------------
# DeviceRiskEvent — anomaly detection events
# ---------------------------------------------------------------------------

class DeviceRiskEvent(models.Model):
    """Records anomalies that feed into the device risk score."""

    class RiskType(models.TextChoices):
        NEW_IP          = 'NEW_IP',        'New IP Address'
        IP_OUTSIDE_RANGE = 'IP_OUTSIDE',   'IP Outside Expected Range'
        OFF_HOURS_ACCESS = 'OFF_HOURS',    'Access Outside Active Hours'
        HIGH_VELOCITY   = 'HIGH_VELOCITY', 'High Request Velocity'
        FAILED_ATTEMPTS = 'FAILED_ATTEMPTS', 'Repeated Failed Attempts'
        CONCURRENT_IP   = 'CONCURRENT_IP', 'Concurrent Access from Different IPs'
        USER_AGENT_CHANGE = 'UA_CHANGE',   'User-Agent Changed'
        SUSPICIOUS_PATH = 'SUSPICIOUS_PATH', 'Access to Sensitive Path'

    id         = models.BigAutoField(primary_key=True)
    device     = models.ForeignKey(
        AuthorizedDevice, on_delete=models.CASCADE, related_name='risk_events'
    )
    risk_type  = models.CharField(max_length=30, choices=RiskType.choices, db_index=True)
    severity   = models.PositiveSmallIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="Points added to device risk score (1-50)."
    )
    detail     = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    detected_at = models.DateTimeField(default=timezone.now, db_index=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acknowledged_risk_events'
    )

    class Meta:
        app_label = 'core'
        ordering = ['-detected_at']
        indexes  = [
            models.Index(fields=['device', 'acknowledged', '-detected_at']),
            models.Index(fields=['risk_type', '-detected_at']),
        ]

    def __str__(self):
        return f"{self.risk_type} on {self.device} @ {self.detected_at}"
