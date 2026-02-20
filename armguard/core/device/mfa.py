"""
ARMGUARD Device MFA Integration
=================================
Provides TOTP (RFC 6238) and Email OTP support for device enrollment.

Dependencies:
    pip install pyotp qrcode[pil]

Usage in view (TOTP):
    from core.device.mfa import TOTPService
    service = TOTPService(user)
    uri = service.get_provisioning_uri()   # → scan in authenticator app
    valid = service.verify(request.POST['code'])

Usage in view (Email OTP):
    from core.device.mfa import EmailOTPService
    EmailOTPService.issue(device, challenge)   # sends email
    valid = EmailOTPService.verify(challenge, request.POST['code'])
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger('armguard.device.mfa')


# ---------------------------------------------------------------------------
# TOTP Service  (wraps pyotp — installed separately)
# ---------------------------------------------------------------------------

class TOTPService:
    """
    Per-user TOTP secrets stored in the user's profile or a dedicated model.

    For ARMGUARD, the TOTP secret is stored in the user's profile
    under profile.totp_secret (CharField added via migration).
    If the profile field doesn't exist yet, set DEVICE_TOTP_CACHE_FALLBACK=True
    in settings to use encrypted cache as a temporary fallback.
    """

    def __init__(self, user: User):
        self.user = user
        self._pyotp = self._import_pyotp()

    @staticmethod
    def _import_pyotp():
        try:
            import pyotp
            return pyotp
        except ImportError:
            raise ImportError(
                "pyotp is required for TOTP support. "
                "Install it: pip install pyotp"
            )

    def get_or_create_secret(self) -> str:
        """Return existing TOTP secret or generate and persist a new one."""
        secret = self._load_secret()
        if not secret:
            secret = self._pyotp.random_base32()
            self._save_secret(secret)
        return secret

    def get_provisioning_uri(self, issuer: str = 'ARMGUARD RDS') -> str:
        """
        Returns an otpauth:// URI that can be encoded into a QR code
        for the user to scan with their authenticator app.
        """
        secret = self.get_or_create_secret()
        totp = self._pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=self.user.username,
            issuer_name=issuer,
        )

    def verify(self, code: str, window: int = 1) -> bool:
        """
        Verify a TOTP code.
        window=1 allows ±1 time step (±30 s) for clock drift.
        """
        secret = self._load_secret()
        if not secret:
            logger.warning('TOTP verify called for user %s with no secret', self.user.username)
            return False
        # Strip spaces (some apps display XXXXXX as XXX XXX)
        code = code.replace(' ', '').strip()
        totp = self._pyotp.TOTP(secret)
        return totp.verify(code, valid_window=window)

    def reset_secret(self) -> str:
        """Rotate the TOTP secret — call this after suspected compromise."""
        new_secret = self._pyotp.random_base32()
        self._save_secret(new_secret)
        logger.warning('TOTP secret rotated for user %s', self.user.username)
        return new_secret

    # ------------------------------------------------------------------
    # Secret storage helpers — override for custom profile models
    # ------------------------------------------------------------------

    def _load_secret(self) -> str:
        """Load TOTP secret. Tries profile field first, then cache fallback."""
        try:
            return self.user.profile.totp_secret or ''
        except AttributeError:
            pass
        if getattr(settings, 'DEVICE_TOTP_CACHE_FALLBACK', False):
            return cache.get(f'totp_secret_{self.user.id}', '')
        return ''

    def _save_secret(self, secret: str) -> None:
        try:
            profile = self.user.profile
            profile.totp_secret = secret
            profile.save(update_fields=['totp_secret'])
            return
        except AttributeError:
            pass
        if getattr(settings, 'DEVICE_TOTP_CACHE_FALLBACK', False):
            cache.set(f'totp_secret_{self.user.id}', secret, timeout=None)
        else:
            raise RuntimeError(
                'Cannot persist TOTP secret: user.profile.totp_secret field not found '
                'and DEVICE_TOTP_CACHE_FALLBACK is not enabled.'
            )

    @staticmethod
    def generate_qr_data_uri(provisioning_uri: str) -> str:
        """
        Returns a data:image/png;base64,... string for embedding in <img src=...>.
        Requires:  pip install qrcode[pil]
        """
        try:
            import qrcode
            import base64
            import io
            img = qrcode.make(provisioning_uri)
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            encoded = base64.b64encode(buf.getvalue()).decode()
            return f'data:image/png;base64,{encoded}'
        except ImportError:
            logger.warning('qrcode not installed; returning provisioning URI as text')
            return provisioning_uri


# ---------------------------------------------------------------------------
# Email OTP Service
# ---------------------------------------------------------------------------

class EmailOTPService:
    """
    Generates and validates time-limited numeric OTPs sent by email.

    Flow:
        1. View calls EmailOTPService.issue(device, challenge)  → sends OTP to user's email
        2. User submits the code from their inbox
        3. View calls EmailOTPService.verify(challenge, submitted_code) → True/False
    """

    CODE_LENGTH = 6  # digits
    RATE_LIMIT_WINDOW = 120   # seconds between re-sends
    RATE_LIMIT_MAX    = 3     # max emails per window

    @classmethod
    def issue(cls, device, challenge) -> bool:
        """
        Generate OTP, store hashed copy on challenge, send email.
        Returns True on success, False if rate-limited.
        """
        from .models import DeviceMFAChallenge  # avoid circular if needed

        user = device.user

        # Rate limiting: prevent OTP email flooding
        rate_key = f'otp_email_rate_{user.id}'
        count = cache.get(rate_key, 0)
        if count >= cls.RATE_LIMIT_MAX:
            logger.warning('OTP email rate limit hit for user %s', user.username)
            return False

        # Generate 6-digit code
        otp = ''.join(secrets.choice(string.digits) for _ in range(cls.CODE_LENGTH))

        # Store hashed OTP on the challenge record
        challenge.set_email_otp(otp)

        # Send email
        subject = '[ARMGUARD RDS] Device Authorization Code'
        ttl_minutes = getattr(settings, 'DEVICE_MFA_CHALLENGE_TTL_MINUTES', 15)
        body = (
            f'Your device authorization code is:\n\n'
            f'    {otp}\n\n'
            f'This code expires in {ttl_minutes} minutes.\n\n'
            f'Device: {device.device_name}\n'
            f'If you did not request this, contact your administrator immediately.\n\n'
            f'ARMGUARD RDS Security System'
        )

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            # Increment rate counter
            cache.set(rate_key, count + 1, timeout=cls.RATE_LIMIT_WINDOW)
            logger.info('OTP email sent to %s for device %s', user.email, device.device_name)
            return True
        except Exception as exc:
            logger.error('Failed to send OTP email to %s: %s', user.email, exc)
            return False

    @classmethod
    def verify(cls, challenge, submitted_code: str) -> bool:
        """Verify the submitted OTP against the stored hash."""
        return challenge.verify_email_otp(submitted_code)


# ---------------------------------------------------------------------------
# MFA Setup Check Utility
# ---------------------------------------------------------------------------

class MFAReadinessCheck:
    """
    Checks whether the requesting user has MFA configured before
    allowing device enrollment.  Prevents enrollment without any
    second factor.
    """

    @staticmethod
    def user_has_totp(user: User) -> bool:
        try:
            return bool(user.profile.totp_secret)
        except AttributeError:
            if getattr(settings, 'DEVICE_TOTP_CACHE_FALLBACK', False):
                return bool(cache.get(f'totp_secret_{user.id}'))
        return False

    @staticmethod
    def user_has_email(user: User) -> bool:
        return bool(user.email)

    @classmethod
    def available_methods(cls, user: User) -> list[str]:
        methods = []
        if cls.user_has_totp(user):
            methods.append('TOTP')
        if cls.user_has_email(user):
            methods.append('EMAIL')
        return methods

    @classmethod
    def is_ready(cls, user: User) -> bool:
        return bool(cls.available_methods(user))
