"""
ARMGUARD Device Authorization — Security Test Suite
=====================================================
Covers:
  - Unit tests: identity, risk, decision logic
  - Integration tests: full request authorization pipeline
  - Security / penetration tests: spoofing, brute force, expiry bypass

Run:
    python manage.py test core.device.tests --verbosity=2
"""

from __future__ import annotations

import uuid
import secrets
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone

from core.device.models import (
    AuthorizedDevice, DeviceAuditEvent, DeviceMFAChallenge, DeviceRiskEvent
)
from core.device.service import (
    DeviceService, DeviceIdentityService, PathSecurityResolver,
    AuthorizationDecisionEngine, DeviceRiskEvaluator, PathTier
)
from core.device.mfa import TOTPService, EmailOTPService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username='testuser', superuser=False) -> User:
    return User.objects.create_user(
        username=username, password='testpass123',
        email=f'{username}@armguard.test',
        is_superuser=superuser,
    )


def _make_active_device(user: User, **kwargs) -> AuthorizedDevice:
    defaults = dict(
        device_name='Test Terminal',
        status=AuthorizedDevice.Status.ACTIVE,
        security_tier=AuthorizedDevice.SecurityTier.HIGH_SECURITY,
        can_transact=True,
        expires_at=timezone.now() + timedelta(days=90),
    )
    defaults.update(kwargs)
    return AuthorizedDevice.objects.create(user=user, **defaults)


def _make_request(path='/', method='GET', cookie_token=None) -> MagicMock:
    factory = RequestFactory()
    req = factory.get(path)
    req.META['HTTP_USER_AGENT'] = 'TestBrowser/1.0'
    if cookie_token:
        req.COOKIES[DeviceIdentityService.COOKIE_NAME] = cookie_token
    req.user = MagicMock(is_authenticated=False, is_superuser=False, groups=MagicMock())
    req.user.groups.all.return_value = []
    return req


# ===========================================================================
# 1. Path Security Resolver Tests
# ===========================================================================

class PathSecurityResolverTests(TestCase):

    def setUp(self):
        self.resolver = PathSecurityResolver()

    def test_static_is_exempt(self):
        self.assertIsNone(self.resolver.resolve('/static/css/base.css'))

    def test_login_is_exempt(self):
        self.assertIsNone(self.resolver.resolve('/login/'))

    def test_admin_is_high_security(self):
        self.assertEqual(self.resolver.resolve('/admin/'), PathTier.HIGH_SECURITY)

    def test_transaction_api_is_restricted(self):
        self.assertEqual(
            self.resolver.resolve('/transactions/api/create/'),
            PathTier.RESTRICTED
        )

    @override_settings(DEVICE_PATH_CONFIG={'protect_root_path': True})
    def test_unknown_path_is_high_security_when_protect_root(self):
        resolver = PathSecurityResolver()
        self.assertEqual(resolver.resolve('/some/new/path/'), PathTier.HIGH_SECURITY)

    def test_request_auth_page_is_exempt(self):
        self.assertIsNone(self.resolver.resolve('/admin/device/request-authorization/'))


# ===========================================================================
# 2. Identity Service Tests
# ===========================================================================

class DeviceIdentityServiceTests(TestCase):

    def setUp(self):
        self.svc = DeviceIdentityService()

    def test_valid_token_format(self):
        token = secrets.token_hex(32)
        self.assertTrue(DeviceIdentityService._is_valid_token_format(token))

    def test_short_token_invalid(self):
        self.assertFalse(DeviceIdentityService._is_valid_token_format('abc123'))

    def test_non_hex_token_invalid(self):
        self.assertFalse(DeviceIdentityService._is_valid_token_format('x' * 64))

    def test_missing_cookie_returns_new_token(self):
        req = _make_request()
        req.COOKIES = {}
        token, is_new = self.svc.get_or_generate_token(req)
        self.assertTrue(is_new)
        self.assertEqual(len(token), 64)

    def test_existing_valid_cookie_returned(self):
        existing = secrets.token_hex(32)
        req = _make_request(cookie_token=existing)
        token, is_new = self.svc.get_or_generate_token(req)
        self.assertFalse(is_new)
        self.assertEqual(token, existing)

    def test_resolve_known_device(self):
        user = _make_user()
        device = _make_active_device(user)
        found = self.svc.resolve_device(device.device_token)
        self.assertEqual(found.id, device.id)

    def test_resolve_unknown_token_returns_none(self):
        result = self.svc.resolve_device(secrets.token_hex(32))
        self.assertIsNone(result)


# ===========================================================================
# 3. Authorization Decision Engine Tests
# ===========================================================================

class AuthorizationDecisionEngineTests(TestCase):

    def setUp(self):
        self.engine = AuthorizationDecisionEngine()
        self.user = _make_user()
        self.ip = '192.168.1.10'

    def _decide(self, device, tier='RESTRICTED'):
        return self.engine.decide(device, self.ip, '/transactions/api/', tier)

    # ---- None device ----
    def test_no_device_denied(self):
        allowed, reason = self._decide(None)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_token_not_registered')

    # ---- Active device ----
    def test_active_device_allowed(self):
        device = _make_active_device(self.user)
        allowed, reason = self._decide(device)
        self.assertTrue(allowed)
        self.assertEqual(reason, 'authorized')

    # ---- Status checks ----
    def test_pending_mfa_denied(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.PENDING_MFA)
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_pending_mfa')

    def test_revoked_denied(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.REVOKED)
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_revoked')

    def test_expired_denied(self):
        device = _make_active_device(self.user, expires_at=timezone.now() - timedelta(days=1))
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)

    # ---- Security tier ----
    def test_standard_device_blocked_from_high_security_path(self):
        device = _make_active_device(self.user,
                                     security_tier=AuthorizedDevice.SecurityTier.STANDARD)
        allowed, reason = self._decide(device, tier='HIGH_SECURITY')
        self.assertFalse(allowed)
        self.assertIn('insufficient_tier', reason)

    def test_military_device_allowed_high_security_path(self):
        device = _make_active_device(self.user,
                                     security_tier=AuthorizedDevice.SecurityTier.MILITARY)
        allowed, reason = self._decide(device, tier='HIGH_SECURITY')
        self.assertTrue(allowed)

    # ---- IP binding ----
    def test_ip_binding_mismatch_denied(self):
        device = _make_active_device(self.user, ip_binding='10.0.0.1')
        allowed, reason = self.engine.decide(
            device, '192.168.99.99', '/admin/', 'HIGH_SECURITY'
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, 'ip_binding_mismatch')

    def test_ip_binding_match_allowed(self):
        device = _make_active_device(self.user, ip_binding=self.ip)
        allowed, reason = self.engine.decide(device, self.ip, '/admin/', 'HIGH_SECURITY')
        self.assertTrue(allowed)

    # ---- Lockout ----
    def test_locked_device_denied(self):
        device = _make_active_device(
            self.user,
            locked_until=timezone.now() + timedelta(minutes=29)
        )
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_locked_out')

    # ---- Risk score ----
    @override_settings(DEVICE_RISK_BLOCK_THRESHOLD=75)
    def test_high_risk_score_blocked(self):
        device = _make_active_device(self.user, risk_score=80)
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)
        self.assertIn('risk_score_too_high', reason)

    @override_settings(DEVICE_RISK_BLOCK_THRESHOLD=75)
    def test_borderline_risk_score_allowed(self):
        device = _make_active_device(self.user, risk_score=74)
        allowed, reason = self._decide(device)
        self.assertTrue(allowed)

    # ---- Re-validation required ----
    def test_revalidation_required_denied(self):
        device = _make_active_device(self.user, revalidation_required=True)
        allowed, reason = self._decide(device)
        self.assertFalse(allowed)
        self.assertEqual(reason, 'revalidation_required')

    # ---- Active hours ----
    def test_outside_active_hours_denied(self):
        # Force active hours to a 1-minute window in the past
        from datetime import time as dtime
        t = (timezone.now() - timedelta(hours=12)).time()
        start = dtime((t.hour) % 24, 0, 0)
        end   = dtime((t.hour) % 24, 1, 0)
        device = _make_active_device(
            self.user, active_hours_start=start, active_hours_end=end
        )
        # Current time is not in [start, end] with high probability
        if not (start <= timezone.now().time() <= end):
            allowed, reason = self._decide(device)
            self.assertFalse(allowed)
            self.assertEqual(reason, 'outside_active_hours')


# ===========================================================================
# 4. Device Model Lifecycle Tests
# ===========================================================================

class AuthorizedDeviceLifecycleTests(TestCase):

    def setUp(self):
        self.user     = _make_user()
        self.reviewer = _make_user('reviewer', superuser=True)

    def test_activate_changes_status(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.PENDING)
        device.activate(self.reviewer, tier='HIGH_SECURITY', notes='Approved')
        device.refresh_from_db()
        self.assertEqual(device.status, AuthorizedDevice.Status.ACTIVE)
        self.assertIsNotNone(device.authorized_at)

    def test_revoke_changes_status(self):
        device = _make_active_device(self.user)
        device.revoke(self.reviewer, reason='Laptop stolen')
        device.refresh_from_db()
        self.assertEqual(device.status, AuthorizedDevice.Status.REVOKED)
        self.assertIsNotNone(device.revoked_at)

    def test_expire_changes_status(self):
        device = _make_active_device(self.user)
        device.expire()
        device.refresh_from_db()
        self.assertEqual(device.status, AuthorizedDevice.Status.EXPIRED)

    def test_revalidate_extends_expiry(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.EXPIRED)
        device.revalidate(self.user)
        device.refresh_from_db()
        self.assertEqual(device.status, AuthorizedDevice.Status.ACTIVE)
        self.assertGreater(device.expires_at, timezone.now())

    def test_rotate_token_changes_token(self):
        device = _make_active_device(self.user)
        old_token = device.device_token
        new_token = device.rotate_token(self.user)
        device.refresh_from_db()
        self.assertNotEqual(device.device_token, old_token)
        self.assertEqual(device.device_token, new_token)

    def test_lockout_after_max_attempts(self):
        with self.settings(DEVICE_MAX_FAILED_ATTEMPTS=3, DEVICE_LOCKOUT_MINUTES=30):
            device = _make_active_device(self.user, failed_auth_count=0)
            for _ in range(3):
                device.record_failed_attempt('1.2.3.4')
            device.refresh_from_db()
            self.assertTrue(device.is_locked)

    def test_is_expiring_soon(self):
        with self.settings(DEVICE_EXPIRY_WARNING_DAYS=14):
            device = _make_active_device(
                self.user, expires_at=timezone.now() + timedelta(days=10)
            )
            self.assertTrue(device.is_expiring_soon)

    def test_audit_event_created_on_activate(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.PENDING)
        initial_count = DeviceAuditEvent.objects.filter(device=device).count()
        device.activate(self.reviewer)
        self.assertEqual(
            DeviceAuditEvent.objects.filter(device=device).count(),
            initial_count + 1
        )


# ===========================================================================
# 5. MFA Tests
# ===========================================================================

class DeviceMFAChallengeTests(TestCase):

    def setUp(self):
        self.user = _make_user()
        self.device = _make_active_device(self.user, status=AuthorizedDevice.Status.PENDING_MFA)
        self.challenge = DeviceMFAChallenge.objects.create(
            device=self.device,
            method='EMAIL',
            expires_at=timezone.now() + timedelta(minutes=15),
        )

    def test_correct_otp_verifies(self):
        otp = '123456'
        self.challenge.set_email_otp(otp)
        self.assertTrue(self.challenge.verify_email_otp(otp))
        self.assertIsNotNone(self.challenge.verified_at)

    def test_wrong_otp_fails(self):
        self.challenge.set_email_otp('999999')
        self.assertFalse(self.challenge.verify_email_otp('000000'))
        self.challenge.refresh_from_db()
        self.assertEqual(self.challenge.attempts, 1)

    def test_expired_challenge_fails(self):
        self.challenge.expires_at = timezone.now() - timedelta(seconds=1)
        self.challenge.save()
        self.assertFalse(self.challenge.verify_email_otp('123456'))

    def test_exhausted_challenge_fails(self):
        self.challenge.attempts    = self.challenge.max_attempts
        self.challenge.set_email_otp('123456')
        self.challenge.save()
        self.assertFalse(self.challenge.verify_email_otp('123456'))

    def test_otp_replay_after_verify_fails(self):
        otp = '654321'
        self.challenge.set_email_otp(otp)
        self.challenge.verify_email_otp(otp)   # first verify succeeds
        self.assertFalse(self.challenge.verify_email_otp(otp))  # replay denied


# ===========================================================================
# 6. Security / Penetration Tests
# ===========================================================================

class SecurityPenetrationTests(TestCase):
    """
    Tests simulate adversarial scenarios an attacker might attempt.
    Each test should result in a DENIED decision.
    """

    def setUp(self):
        self.user   = _make_user()
        self.engine = AuthorizationDecisionEngine()

    def test_replay_revoked_device_token(self):
        """Attacker reuses a valid token from a revoked device."""
        device = _make_active_device(
            self.user,
            status=AuthorizedDevice.Status.REVOKED
        )
        allowed, _ = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed, 'Revoked device should be denied')

    def test_expired_token_denied(self):
        """Attacker uses a token whose authorization has expired."""
        device = _make_active_device(
            self.user,
            expires_at=timezone.now() - timedelta(seconds=1)
        )
        allowed, _ = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed, 'Expired device should be denied')

    def test_downgrade_attack(self):
        """Attacker tries to access a HIGH_SECURITY path with a STANDARD-tier device."""
        device = _make_active_device(
            self.user,
            security_tier=AuthorizedDevice.SecurityTier.STANDARD
        )
        allowed, reason = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed, 'Tier downgrade attack should be denied')
        self.assertIn('insufficient_tier', reason)

    def test_ip_spoofing_with_bound_device(self):
        """Attacker spoofs a request from a different IP for an IP-bound device."""
        device = _make_active_device(self.user, ip_binding='10.0.0.50')
        allowed, reason = self.engine.decide(device, '10.0.0.99', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed, 'Wrong IP for IP-bound device should be denied')
        self.assertEqual(reason, 'ip_binding_mismatch')

    def test_brute_force_lockout_persists(self):
        """After lockout threshold, even a valid token should be denied."""
        device = _make_active_device(
            self.user,
            locked_until=timezone.now() + timedelta(minutes=15)
        )
        allowed, reason = self.engine.decide(device, '5.6.7.8', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_locked_out')

    def test_high_risk_score_blocks_access(self):
        """Device with anomalous risk score should be denied."""
        with self.settings(DEVICE_RISK_BLOCK_THRESHOLD=75):
            device = _make_active_device(self.user, risk_score=90)
            allowed, reason = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
            self.assertFalse(allowed)
            self.assertIn('risk_score', reason)

    def test_pending_mfa_cannot_access_restricted(self):
        """Device that has not completed MFA should be denied even on RESTRICTED paths."""
        device = _make_active_device(
            self.user,
            status=AuthorizedDevice.Status.PENDING_MFA
        )
        allowed, reason = self.engine.decide(device, '1.2.3.4', '/transactions/api/', 'RESTRICTED')
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_pending_mfa')

    def test_force_revalidation_blocks_access(self):
        """When revalidation_required is True, access is blocked until re-auth."""
        device = _make_active_device(self.user, revalidation_required=True)
        allowed, reason = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed)
        self.assertEqual(reason, 'revalidation_required')

    def test_unknown_token_denied(self):
        """A token not in the database should always be denied."""
        fake_token = secrets.token_hex(32)
        identity = DeviceIdentityService()
        device = identity.resolve_device(fake_token)
        self.assertIsNone(device)
        allowed, reason = self.engine.decide(device, '1.2.3.4', '/admin/', 'HIGH_SECURITY')
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_token_not_registered')


# ===========================================================================
# 7. Risk Evaluator Tests
# ===========================================================================

class DeviceRiskEvaluatorTests(TestCase):

    def setUp(self):
        self.user    = _make_user()
        self.evaluator = DeviceRiskEvaluator()

    def test_new_ip_triggers_alert(self):
        device = _make_active_device(self.user, ip_first_seen='10.0.0.1')
        req = _make_request()
        with patch('core.device.service.cache') as mock_cache:
            mock_cache.get.return_value = set()
            alerts = self.evaluator._check_new_ip(device, '10.0.0.99')
        self.assertTrue(any('new ip' in a.lower() for a in alerts))

    def test_same_ip_no_alert(self):
        device = _make_active_device(self.user, ip_first_seen='10.0.0.1')
        with patch('core.device.service.cache') as mock_cache:
            mock_cache.get.return_value = {'10.0.0.1'}
            alerts = self.evaluator._check_new_ip(device, '10.0.0.1')
        self.assertEqual(alerts, [])


# ===========================================================================
# 8. Device Service Integration Tests
# ===========================================================================

class DeviceServiceIntegrationTests(TestCase):

    def setUp(self):
        self.user    = _make_user()
        self.service = DeviceService()

    def test_exempt_path_always_allowed(self):
        req = _make_request(path='/static/css/main.css')
        decision = self.service.authorize_request(req)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, 'exempt_path')

    def test_active_device_on_admin_path_allowed(self):
        device = _make_active_device(
            self.user,
            security_tier=AuthorizedDevice.SecurityTier.HIGH_SECURITY
        )
        req = _make_request(path='/admin/', cookie_token=device.device_token)
        req.user = self.user
        decision = self.service.authorize_request(req)
        self.assertTrue(decision.allowed, f'Expected allowed, got: {decision.reason}')

    def test_missing_cookie_denied_on_restricted(self):
        req = _make_request(path='/admin/')
        req.COOKIES = {}
        decision = self.service.authorize_request(req)
        self.assertFalse(decision.allowed)

    @override_settings(DEBUG=True)
    def test_superuser_debug_bypass(self):
        superuser = _make_user('super', superuser=True)
        req = _make_request(path='/admin/')
        req.user = superuser   # real User instance; is_authenticated is always True
        decision = self.service.authorize_request(req)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, 'superuser_debug_bypass')

    def test_enrollment_creates_pending_mfa_device(self):
        device, challenge = self.service.enroll_device(
            user=self.user,
            device_name='New Laptop',
            reason='Admin work',
            ip='192.168.1.5',
            user_agent_hash='abc123',
            mfa_method='EMAIL',
        )
        self.assertEqual(device.status, AuthorizedDevice.Status.PENDING_MFA)
        self.assertIsNotNone(challenge)
        self.assertEqual(challenge.method, 'EMAIL')

    def test_complete_mfa_advances_to_pending(self):
        device, challenge = self.service.enroll_device(
            user=self.user,
            device_name='New Laptop',
            reason='Testing',
            ip='192.168.1.5',
            user_agent_hash='abc123',
            mfa_method='EMAIL',
        )
        otp = '112233'
        challenge.set_email_otp(otp)
        result = self.service.complete_mfa(device, otp=otp)
        self.assertTrue(result)
        device.refresh_from_db()
        self.assertEqual(device.status, AuthorizedDevice.Status.PENDING)


# ===========================================================================
# 9. RELIABILITY TESTS — same input, always same output
# ===========================================================================

class ReliabilityTests(TestCase):
    """
    Each check is repeated multiple times to confirm deterministic behaviour
    under identical conditions (no state bleed, no race).
    """

    def setUp(self):
        self.user = _make_user('reliability_user')
        self.resolver = PathSecurityResolver()
        self.engine = AuthorizationDecisionEngine()
        self.service = DeviceService()

    def test_path_resolver_is_deterministic(self):
        paths_and_expected = [
            ('/admin/', PathTier.HIGH_SECURITY),
            ('/login/', None),
            ('/transactions/api/', PathTier.RESTRICTED),
            ('/admin/device/request-authorization/', None),
        ]
        for path, expected in paths_and_expected:
            results = [self.resolver.resolve(path) for _ in range(10)]
            self.assertTrue(
                all(r == expected for r in results),
                f'Path {path} produced inconsistent results: {set(results)}'
            )

    def test_decision_engine_is_deterministic(self):
        device = _make_active_device(self.user)
        results = [
            self.engine.decide(device, '10.0.0.1', '/admin/', 'HIGH_SECURITY')
            for _ in range(10)
        ]
        self.assertTrue(
            all(r == results[0] for r in results),
            'Decision engine produced inconsistent results'
        )

    def test_repeated_valid_auth_always_succeeds(self):
        device = _make_active_device(self.user)
        for i in range(10):
            req = _make_request(path='/admin/', cookie_token=device.device_token)
            req.user = self.user
            decision = self.service.authorize_request(req)
            self.assertTrue(decision.allowed,
                            f'Request {i+1} unexpectedly denied: {decision.reason}')

    def test_repeated_invalid_auth_always_fails(self):
        for i in range(10):
            req = _make_request(path='/admin/', cookie_token=secrets.token_hex(32))
            req.COOKIES = {}
            decision = self.service.authorize_request(req)
            self.assertFalse(decision.allowed,
                             f'Request {i+1} unexpectedly allowed')

    def test_revoked_device_consistently_denied(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.REVOKED)
        for _ in range(5):
            allowed, reason = self.engine.decide(
                device, '10.0.0.1', '/admin/', 'HIGH_SECURITY'
            )
            self.assertFalse(allowed)
            self.assertEqual(reason, 'device_revoked')


# ===========================================================================
# 10. AUDIT TRAIL INTEGRITY TESTS
# ===========================================================================

class AuditTrailIntegrityTests(TestCase):
    """
    Every state transition must produce an immutable audit record.
    """

    def setUp(self):
        self.actor = _make_user('auditor', superuser=True)
        self.user = _make_user('auditee')

    def test_every_transition_logs_event(self):
        device = _make_active_device(self.user, status=AuthorizedDevice.Status.PENDING)
        device.activate(self.actor, notes='Approved')
        device.suspend(self.actor, 'Suspicious activity')
        device.revoke(self.actor, 'Policy violation')

        event_types = list(
            DeviceAuditEvent.objects.filter(device=device)
            .values_list('event_type', flat=True)
        )
        self.assertIn('ACTIVATED', event_types)
        self.assertIn('SUSPENDED', event_types)
        self.assertIn('REVOKED', event_types)

    def test_token_rotation_logged(self):
        device = _make_active_device(self.user)
        device.rotate_token(self.actor)
        events = DeviceAuditEvent.objects.filter(device=device, event_type='TOKEN_ROTATED')
        self.assertEqual(events.count(), 1)

    def test_lockout_event_created_at_threshold(self):
        device = _make_active_device(self.user)
        with self.settings(DEVICE_MAX_FAILED_ATTEMPTS=2, DEVICE_LOCKOUT_MINUTES=30):
            device.record_failed_attempt('1.2.3.4')
            device.record_failed_attempt('1.2.3.4')
        events = DeviceAuditEvent.objects.filter(device=device, event_type='LOCKED_OUT')
        self.assertEqual(events.count(), 1)

    def test_access_log_created_for_each_request(self):
        from core.device.models import DeviceAccessLog
        device = _make_active_device(self.user)
        service = DeviceService()
        initial = DeviceAccessLog.objects.count()
        for _ in range(5):
            req = _make_request(path='/admin/', cookie_token=device.device_token)
            req.user = self.user
            service.authorize_request(req)
        self.assertEqual(DeviceAccessLog.objects.count(), initial + 5)

    def test_access_log_records_correct_verdict(self):
        from core.device.models import DeviceAccessLog
        device = _make_active_device(self.user)
        service = DeviceService()

        # Authorized request
        req_ok = _make_request(path='/admin/', cookie_token=device.device_token)
        req_ok.user = self.user
        d_ok = service.authorize_request(req_ok)
        self.assertTrue(DeviceAccessLog.objects.get(pk=d_ok.log_entry.pk).is_authorized)

        # Denied request
        req_bad = _make_request(path='/admin/')
        req_bad.COOKIES = {}
        d_bad = service.authorize_request(req_bad)
        self.assertFalse(DeviceAccessLog.objects.get(pk=d_bad.log_entry.pk).is_authorized)


# ===========================================================================
# 11. BRUTE FORCE PROTECTION TESTS
# ===========================================================================

class BruteForceProtectionTests(TestCase):

    def setUp(self):
        self.user = _make_user('bf_target')
        self.engine = AuthorizationDecisionEngine()

    def test_failed_attempts_do_not_affect_other_devices(self):
        """Hammering fake tokens must not pollute other devices' counters."""
        real_device = _make_active_device(self.user)
        service = DeviceService()
        for _ in range(20):
            req = _make_request(path='/admin/', cookie_token=secrets.token_hex(32))
            req.COOKIES = {}
            service.authorize_request(req)
        real_device.refresh_from_db()
        self.assertEqual(real_device.failed_auth_count, 0)

    def test_locked_device_denied_with_valid_token(self):
        device = _make_active_device(
            self.user,
            locked_until=timezone.now() + timedelta(minutes=30),
            failed_auth_count=5,
        )
        allowed, reason = self.engine.decide(
            device, '10.0.0.1', '/admin/', 'HIGH_SECURITY'
        )
        self.assertFalse(allowed)
        self.assertEqual(reason, 'device_locked_out')

    def test_lockout_expires_naturally(self):
        """After locked_until passes, device should be accessible again."""
        device = _make_active_device(
            self.user,
            locked_until=timezone.now() - timedelta(seconds=1),  # already past
            failed_auth_count=3,
        )
        self.assertFalse(device.is_locked)
        allowed, reason = self.engine.decide(
            device, '10.0.0.1', '/admin/', 'HIGH_SECURITY'
        )
        self.assertTrue(allowed)

    def test_workflow_denials_do_not_increment_failed_count(self):
        """PENDING, REVOKED, SUSPENDED must not trigger brute-force counter."""
        service = DeviceService()
        for status in [
            AuthorizedDevice.Status.PENDING,
            AuthorizedDevice.Status.REVOKED,
            AuthorizedDevice.Status.SUSPENDED,
            AuthorizedDevice.Status.PENDING_MFA,
        ]:
            user = _make_user(f'wf_{status}_{secrets.token_hex(4)}')
            device = _make_active_device(user, status=status)
            req = _make_request(path='/admin/', cookie_token=device.device_token)
            service.authorize_request(req)
            device.refresh_from_db()
            self.assertEqual(
                device.failed_auth_count, 0,
                f'Status {status} should not increment failed_auth_count'
            )


# ===========================================================================
# 12. GUI FLOW SIMULATION (approval creates v2 AuthorizedDevice)
# ===========================================================================

class GUIApprovalFlowTests(TestCase):
    """
    Simulates the full admin approval flow:
      Request form submission → superuser approves → AuthorizedDevice created.
    """

    def setUp(self):
        self.admin = _make_user('gui_admin', superuser=True)
        self.officer = _make_user('gui_officer')

    def test_approval_creates_active_v2_device(self):
        from admin.models import DeviceAuthorizationRequest
        req = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.10.10.50',
            user_agent='Officer/Chrome',
            requested_by=self.officer,
            reason='Need access to admin panel',
            device_name='Officer Station',
            security_level='HIGH_SECURITY',
        )
        count_before = AuthorizedDevice.objects.count()
        req.approve(
            reviewer=self.admin,
            device_name='Officer Station',
            security_level='HIGH_SECURITY',
            notes='Approved in test',
        )
        count_after = AuthorizedDevice.objects.count()
        self.assertEqual(count_after, count_before + 1)

        v2 = AuthorizedDevice.objects.filter(ip_last_seen='10.10.10.50').last()
        self.assertIsNotNone(v2)
        self.assertEqual(v2.status, AuthorizedDevice.Status.ACTIVE)
        self.assertEqual(v2.security_tier, AuthorizedDevice.SecurityTier.HIGH_SECURITY)
        self.assertEqual(v2.reviewed_by, self.admin)

    def test_approved_token_grants_middleware_access(self):
        """Token from the approved v2 device passes the decision engine."""
        from admin.models import DeviceAuthorizationRequest
        req = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.10.10.55',
            user_agent='Officer/Firefox',
            requested_by=self.officer,
            reason='Test access',
            device_name='Test Station',
            security_level='HIGH_SECURITY',
        )
        req.approve(self.admin, 'Test Station', 'HIGH_SECURITY')

        v2 = AuthorizedDevice.objects.filter(ip_last_seen='10.10.10.55').last()
        self.assertIsNotNone(v2)

        service = DeviceService()
        http_req = _make_request(path='/admin/', cookie_token=v2.device_token)
        http_req.user = self.officer
        decision = service.authorize_request(http_req)
        self.assertTrue(decision.allowed, f'Expected allowed, got: {decision.reason}')

    def test_rejection_does_not_create_v2_device(self):
        from admin.models import DeviceAuthorizationRequest
        req = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.10.10.60',
            user_agent='BadActor/1.0',
            requested_by=self.officer,
            reason='Suspicious',
            device_name='Unknown PC',
            security_level='STANDARD',
        )
        count_before = AuthorizedDevice.objects.count()
        req.reject(reviewer=self.admin, notes='Rejected in test')
        self.assertEqual(AuthorizedDevice.objects.count(), count_before)
