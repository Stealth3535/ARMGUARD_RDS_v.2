"""
ARMGUARD Device Service Layer
==============================
Clean service-layer pattern — all device authorization logic lives here.
Middleware is a thin adapter that calls this service.

Architecture:
    Request
      → DeviceMiddlewareAdapter (thin Django layer in middleware/)
          → DeviceService.authorize_request()
              → DeviceIdentityService  (resolve token → AuthorizedDevice)
              → DeviceRiskEvaluator    (compute risk, detect anomalies)
              → DeviceAuthorizationDecision (final pass/deny)
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import (
    AuthorizedDevice,
    DeviceAccessLog,
    DeviceAuditEvent,
    DeviceMFAChallenge,
    DeviceRiskEvent,
)

logger = logging.getLogger('armguard.device')


# ---------------------------------------------------------------------------
# Path tier constants (moved OUT of middleware into service)
# ---------------------------------------------------------------------------

class PathTier:
    EXEMPT       = None
    RESTRICTED   = 'RESTRICTED'
    HIGH_SECURITY = 'HIGH_SECURITY'


# ---------------------------------------------------------------------------
# Decision dataclass
# ---------------------------------------------------------------------------

@dataclass
class AuthDecision:
    """Value object returned by DeviceService.authorize_request()."""
    allowed:        bool
    reason:         str
    device:         Optional[AuthorizedDevice] = None
    security_tier:  str = 'RESTRICTED'
    risk_score:     int = 0
    log_entry:      Optional[DeviceAccessLog] = None
    alerts:         list = field(default_factory=list)
    # When a brand-new token is issued, store it here so the middleware
    # can set it as a cookie on the outbound response.
    _new_token:     Optional[str] = None


# ---------------------------------------------------------------------------
# Path Security Resolver
# ---------------------------------------------------------------------------

class PathSecurityResolver:
    """
    Determines which security tier a URL path falls under.
    Reads config from settings.DEVICE_PATH_CONFIG or uses hard defaults.
    Moving this to a service means the middleware no longer owns security policy.
    """

    _DEFAULT_EXEMPT = [
        '/static/', '/media/', '/favicon.ico', '/robots.txt',
        '/login/', '/accounts/login/', '/logout/',
        '/admin/device/request-authorization/',
    ]

    _DEFAULT_RESTRICTED = [
        '/transactions/create/', '/transactions/api/', '/inventory/api/',
        '/admin/transactions/', '/admin/inventory/', '/qr_manager/generate/',
        '/personnel/api/create/', '/admin/core/', '/admin/users/', '/api/',
        '/core/api/', '/inventory/api/delete/', '/transactions/api/delete/',
        '/users/api/', '/personnel/api/delete/',
    ]

    _DEFAULT_HIGH_SECURITY = [
        '/admin/', '/transactions/delete/', '/users/delete/', '/inventory/delete/',
        '/admin/auth/', '/personnel/delete/', '/core/settings/',
    ]

    def __init__(self):
        cfg = getattr(settings, 'DEVICE_PATH_CONFIG', {})
        self._exempt        = cfg.get('exempt', self._DEFAULT_EXEMPT)
        self._restricted    = cfg.get('restricted', self._DEFAULT_RESTRICTED)
        self._high_security = cfg.get('high_security', self._DEFAULT_HIGH_SECURITY)
        self._protect_all   = cfg.get('protect_root_path', not settings.DEBUG)

    def resolve(self, path: str) -> str | None:
        p = path or '/'
        for ep in self._exempt:
            if p.startswith(ep):
                return PathTier.EXEMPT
        # Always check explicit lists first so configured tiers are respected
        # even when protect_all is True.
        for hp in self._high_security:
            if p.startswith(hp):
                return PathTier.HIGH_SECURITY
        for rp in self._restricted:
            if p.startswith(rp):
                return PathTier.RESTRICTED
        # Catch-all: if protect_all is set, unknown paths get HIGH_SECURITY
        if self._protect_all:
            return PathTier.HIGH_SECURITY
        return PathTier.EXEMPT


# ---------------------------------------------------------------------------
# Device Identity Service
# ---------------------------------------------------------------------------

class DeviceIdentityService:
    """
    Resolves a raw request into an AuthorizedDevice instance.

    Identity is established via the `armguard_device_token` cookie.  The token
    is a 64-char hex secret generated during enrollment — NOT derived from
    request headers.  This replaces the previous SHA-256(UA|IP|cookie) approach
    which was trivially spoofable.
    """

    COOKIE_NAME = getattr(settings, 'DEVICE_TOKEN_COOKIE', 'armguard_device_token')

    def get_or_generate_token(self, request) -> tuple[str, bool]:
        """
        Return (token, is_new). is_new=True means a new token was generated
        and must be set on the response cookie.
        """
        raw = request.COOKIES.get(self.COOKIE_NAME, '')
        if raw and self._is_valid_token_format(raw):
            return raw, False
        new_token = secrets.token_hex(32)
        return new_token, True

    def resolve_device(self, token: str) -> Optional[AuthorizedDevice]:
        """Look up the AuthorizedDevice for a given token. Returns None if not found."""
        try:
            return AuthorizedDevice.objects.select_related('user').get(device_token=token)
        except AuthorizedDevice.DoesNotExist:
            return None

    def get_client_ip(self, request) -> str:
        xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

    @staticmethod
    def _is_valid_token_format(token: str) -> bool:
        return (
            isinstance(token, str)
            and len(token) == 64
            and all(c in '0123456789abcdefABCDEF' for c in token)
        )

    @staticmethod
    def build_user_agent_hash(request) -> str:
        ua = request.META.get('HTTP_USER_AGENT', '')
        return hashlib.sha256(ua.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Risk Evaluator
# ---------------------------------------------------------------------------

class DeviceRiskEvaluator:
    """
    Evaluates behavioral risk signals and updates device risk score.
    Runs AFTER identity is resolved (device object available).
    """

    KNOWN_IP_CACHE_TTL = 3600 * 24  # 24h

    def evaluate(self, device: AuthorizedDevice, ip: str, path: str, request) -> list[str]:
        """
        Returns a list of alert strings. Also updates device.risk_score if needed.
        """
        alerts = []

        alerts += self._check_new_ip(device, ip)
        alerts += self._check_ua_change(device, request)
        alerts += self._check_high_velocity(device, ip)
        alerts += self._check_concurrent_ips(device, ip)

        return alerts

    def _check_new_ip(self, device: AuthorizedDevice, ip: str) -> list[str]:
        cache_key = f'device_known_ips_{device.id}'
        known_ips: set = cache.get(cache_key, set())

        if not device.ip_first_seen:
            return []

        if ip not in known_ips and ip != device.ip_first_seen:
            known_ips.add(ip)
            cache.set(cache_key, known_ips, self.KNOWN_IP_CACHE_TTL)
            device.bump_risk(5, f'New IP: {ip}')
            DeviceRiskEvent.objects.create(
                device=device,
                risk_type=DeviceRiskEvent.RiskType.NEW_IP,
                severity=5,
                detail=f'First access from {ip} (known: {device.ip_first_seen})',
                ip_address=ip,
            )
            return [f'Device "{device.device_name}" accessed from new IP {ip}']

        known_ips.add(ip)
        cache.set(cache_key, known_ips, self.KNOWN_IP_CACHE_TTL)
        return []

    def _check_ua_change(self, device: AuthorizedDevice, request) -> list[str]:
        if not device.user_agent_hash:
            return []
        current = DeviceIdentityService.build_user_agent_hash(request)
        if current != device.user_agent_hash:
            device.bump_risk(10, f'UA changed from {device.user_agent_hash} to {current}')
            DeviceRiskEvent.objects.create(
                device=device,
                risk_type=DeviceRiskEvent.RiskType.USER_AGENT_CHANGE,
                severity=10,
                detail=f'UA hash changed to {current}',
            )
            return [f'Device "{device.device_name}" user-agent changed']
        return []

    def _check_high_velocity(self, device: AuthorizedDevice, ip: str) -> list[str]:
        cache_key = f'device_velocity_{device.id}'
        count = cache.get(cache_key, 0)
        count += 1
        cache.set(cache_key, count, timeout=60)  # per-minute window
        threshold = getattr(settings, 'DEVICE_VELOCITY_THRESHOLD', 120)  # req/min
        if count > threshold:
            device.bump_risk(15, f'Velocity {count} req/min from {ip}')
            DeviceRiskEvent.objects.create(
                device=device,
                risk_type=DeviceRiskEvent.RiskType.HIGH_VELOCITY,
                severity=15,
                detail=f'{count} requests in 60s',
                ip_address=ip,
            )
            return [f'HIGH VELOCITY: {count} req/min from device "{device.device_name}"']
        return []

    def _check_concurrent_ips(self, device: AuthorizedDevice, ip: str) -> list[str]:
        """Detect if device is being accessed from >1 IP simultaneously."""
        window_key = f'device_active_ips_{device.id}'
        active: set = cache.get(window_key, set())
        active.add(ip)
        cache.set(window_key, active, timeout=300)  # 5-min window
        if len(active) > 1:
            device.bump_risk(20, f'Concurrent IPs: {active}')
            DeviceRiskEvent.objects.create(
                device=device,
                risk_type=DeviceRiskEvent.RiskType.CONCURRENT_IP,
                severity=20,
                detail=f'Active IPs in 5-min window: {list(active)}',
                ip_address=ip,
            )
            return [f'CONCURRENT IP ACCESS on device "{device.device_name}": {list(active)}']
        return []


# ---------------------------------------------------------------------------
# Authorization Decision Engine
# ---------------------------------------------------------------------------

class AuthorizationDecisionEngine:
    """
    Pure decision logic — no DB writes (other than audit log).
    Given a resolved device and context, returns AuthDecision.
    """

    TIER_RANK = {
        'STANDARD':      1,
        'RESTRICTED':    2,
        'HIGH_SECURITY': 3,
        'MILITARY':      3,
        'DEVELOPMENT':   1,
    }

    def decide(
        self,
        device: Optional[AuthorizedDevice],
        ip: str,
        path: str,
        required_tier: str,
        user: Optional[User] = None,
        alerts: list = None,
    ) -> tuple[bool, str]:
        """Returns (allowed: bool, reason: str)."""

        if device is None:
            return False, 'device_token_not_registered'

        if device.is_locked:
            return False, 'device_locked_out'

        if not device.is_active:
            if device.status == AuthorizedDevice.Status.PENDING_MFA:
                return False, 'device_pending_mfa'
            if device.status == AuthorizedDevice.Status.PENDING:
                return False, 'device_pending_approval'
            if device.status == AuthorizedDevice.Status.EXPIRED:
                return False, 'device_authorization_expired'
            if device.status == AuthorizedDevice.Status.REVOKED:
                return False, 'device_revoked'
            if device.status == AuthorizedDevice.Status.SUSPENDED:
                return False, 'device_suspended'
            return False, 'device_not_active'

        # Security tier check
        required_rank = self.TIER_RANK.get(required_tier, 1)
        device_rank   = self.TIER_RANK.get(device.security_tier, 1)
        if device_rank < required_rank:
            return False, f'insufficient_tier_{device.security_tier}_for_{required_tier}'

        # IP binding
        if device.ip_binding and device.ip_binding != ip:
            return False, 'ip_binding_mismatch'

        # Active hours
        if device.active_hours_start and device.active_hours_end:
            now_time = timezone.now().time()
            s, e = device.active_hours_start, device.active_hours_end
            in_window = (
                s <= now_time <= e if s <= e
                else now_time >= s or now_time <= e  # overnight
            )
            if not in_window:
                return False, 'outside_active_hours'

        # Re-validation required
        if device.revalidation_required:
            return False, 'revalidation_required'

        # Risk threshold
        risk_block = getattr(settings, 'DEVICE_RISK_BLOCK_THRESHOLD', 75)
        if device.risk_score >= risk_block:
            return False, f'risk_score_too_high_{device.risk_score}'

        # User binding (optional per-device list of authorized roles)
        if user and device.authorized_roles:
            user_groups = {g.name.lower() for g in user.groups.all()}
            allowed     = {r.lower() for r in device.authorized_roles}
            if not user_groups & allowed and user.username.lower() not in allowed:
                return False, 'user_not_authorized_for_device'

        return True, 'authorized'


# ---------------------------------------------------------------------------
# Main Device Service  (facade — the one thing middleware calls)
# ---------------------------------------------------------------------------

class DeviceService:
    """
    Facade integrating all device authorization sub-services.

    Callers (middleware, views) use ONLY this class.
    """

    def __init__(self):
        self.identity    = DeviceIdentityService()
        self.paths       = PathSecurityResolver()
        self.risk        = DeviceRiskEvaluator()
        self.decision    = AuthorizationDecisionEngine()

    # ------------------------------------------------------------------
    # Core: check a request
    # ------------------------------------------------------------------

    def authorize_request(self, request) -> AuthDecision:
        """
        Full authorization check for a Django request.
        Returns AuthDecision; middleware acts on .allowed.
        """
        path = request.path

        # 1. Resolve path tier
        required_tier = self.paths.resolve(path)
        if required_tier is PathTier.EXEMPT:
            return AuthDecision(allowed=True, reason='exempt_path')

        # 2. DEBUG superuser bypass
        if settings.DEBUG:
            user = getattr(request, 'user', None)
            if user and user.is_authenticated and user.is_superuser:
                return AuthDecision(allowed=True, reason='superuser_debug_bypass')

        # 3. Resolve device token → AuthorizedDevice
        token, is_new = self.identity.get_or_generate_token(request)
        ip = self.identity.get_client_ip(request)
        device = None if is_new else self.identity.resolve_device(token)
        new_token = token if is_new else None

        # 4. Risk evaluation (only if device resolved)
        alerts = []
        if device:
            alerts = self.risk.evaluate(device, ip, path, request)

        # 5. Authorization decision
        user    = getattr(request, 'user', None)
        allowed, reason = self.decision.decide(
            device, ip, path, required_tier, user, alerts
        )

        # 6. Record use
        if allowed and device:
            device.record_use(ip)

        # 7. Record failed attempt — only for genuine auth failures, not workflow/policy states
        _WORKFLOW_DENY_REASONS = {
            'device_pending_mfa', 'device_pending_approval', 'device_authorization_expired',
            'device_revoked', 'device_suspended', 'device_not_active',
            'outside_active_hours', 'revalidation_required',
        }
        if (
            not allowed
            and device
            and reason != 'device_locked_out'
            and reason not in _WORKFLOW_DENY_REASONS
            and 'risk_score_too_high' not in reason
            and 'insufficient_tier' not in reason
        ):
            device.record_failed_attempt(ip)

        # 8. Persist access log
        log_entry = self._persist_log(
            device=device,
            request=request,
            ip=ip,
            path=path,
            required_tier=required_tier,
            allowed=allowed,
            reason=reason,
        )

        # 9. Send alerts
        if alerts:
            self._dispatch_alerts(device, alerts)

        return AuthDecision(
            allowed=allowed,
            reason=reason,
            device=device,
            security_tier=required_tier,
            risk_score=device.risk_score if device else 0,
            log_entry=log_entry,
            alerts=alerts,
            _new_token=new_token,
        )

    # ------------------------------------------------------------------
    # Enrollment
    # ------------------------------------------------------------------

    @transaction.atomic
    def enroll_device(
        self,
        user: User,
        device_name: str,
        reason: str,
        ip: str,
        user_agent_hash: str,
        mfa_method: str = 'TOTP',
    ) -> tuple[AuthorizedDevice, DeviceMFAChallenge]:
        """
        Stage 1 of enrollment: create device in PENDING_MFA state
        and issue an MFA challenge.
        """
        device = AuthorizedDevice.objects.create(
            user=user,
            device_name=device_name,
            enrollment_reason=reason,
            ip_first_seen=ip,
            ip_last_seen=ip,
            user_agent_hash=user_agent_hash,
            status=AuthorizedDevice.Status.PENDING_MFA,
        )
        DeviceAuditEvent.log(device, 'ENROLLED', user, f'MFA method: {mfa_method}', ip)

        ttl_minutes = getattr(settings, 'DEVICE_MFA_CHALLENGE_TTL_MINUTES', 15)
        challenge = DeviceMFAChallenge.objects.create(
            device=device,
            method=mfa_method,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )
        return device, challenge

    @transaction.atomic
    def complete_mfa(
        self,
        device: AuthorizedDevice,
        otp: str = None,
        totp_valid: bool = False,
    ) -> bool:
        """
        Stage 2: verify MFA.  For TOTP, caller validates with pyotp and passes
        totp_valid=True.  For EMAIL, this method validates the OTP itself.
        Returns True on success.
        """
        challenge = device.mfa_challenge
        if challenge.is_expired or challenge.is_exhausted:
            return False
        if challenge.is_verified:
            return True

        if challenge.method == DeviceMFAChallenge.Method.TOTP:
            success = totp_valid
        else:
            success = challenge.verify_email_otp(otp or '')

        if success:
            device.status = AuthorizedDevice.Status.PENDING
            device.save(update_fields=['status'])
            DeviceAuditEvent.log(device, 'MFA_PASSED', device.user)
        else:
            DeviceAuditEvent.log(device, 'MFA_FAILED', device.user,
                                 f'Attempts: {challenge.attempts}')
        return success

    # ------------------------------------------------------------------
    # Token cookie helpers
    # ------------------------------------------------------------------

    def attach_token_cookie(self, response, token: str) -> None:
        max_age = getattr(settings, 'DEVICE_COOKIE_MAX_AGE', 60 * 60 * 24 * 365 * 2)
        response.set_cookie(
            DeviceIdentityService.COOKIE_NAME,
            token,
            max_age=max_age,
            secure=not settings.DEBUG,
            httponly=True,
            samesite='Lax',
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _persist_log(
        self,
        device, request, ip, path, required_tier, allowed, reason
    ) -> DeviceAccessLog:
        user = getattr(request, 'user', None)
        if user and not user.is_authenticated:
            user = None
        return DeviceAccessLog.objects.create(
            device=device,
            user=user,
            path=path,
            method=request.method,
            ip_address=ip,
            device_token_prefix=device.device_token[:8] if device else '',
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            security_level=required_tier or 'EXEMPT',
            is_authorized=allowed,
            denial_reason='' if allowed else reason,
            response_status=200 if allowed else 403,
            risk_score_at_check=device.risk_score if device else 0,
            siem_metadata={
                'user': getattr(user, 'username', 'anonymous'),
                'device_id': str(device.id) if device else None,
                'device_name': device.device_name if device else None,
                'security_tier': required_tier,
                'reason': reason,
            },
        )

    def _dispatch_alerts(self, device: AuthorizedDevice, alerts: list) -> None:
        """Send email/log alerts for high-risk events."""
        if not alerts:
            return
        logger.warning(
            'SECURITY ALERT device=%s user=%s alerts=%s',
            device.device_name, device.user.username, alerts
        )
        notify_email = getattr(settings, 'DEVICE_ALERT_EMAIL', None)
        if notify_email:
            try:
                send_mail(
                    subject=f'[ARMGUARD] Device Risk Alert: {device.device_name}',
                    message='\n'.join(alerts),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[notify_email],
                    fail_silently=True,
                )
            except Exception as exc:
                logger.error('Failed to send device alert email: %s', exc)


# ---------------------------------------------------------------------------
# Module-level singleton (import and reuse — thread-safe for stateless service)
# ---------------------------------------------------------------------------

device_service = DeviceService()
