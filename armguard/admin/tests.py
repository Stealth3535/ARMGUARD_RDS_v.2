"""
CSR Feature Tests — admin views / device authorization
=======================================================
Tests for:
  1. attach_csr_to_device view   (POST validation, save, redirect)
  2. request_device_auth view    (GET renders hidden CSR field, no textarea)
  3. view_device_request         (attach panel shown/hidden based on csr_pem)
  4. Full flow: submit-with-CSR → approve → v2 AuthorizedDevice created
  5. Re-attach: panel hidden once CSR already present

Run:
    python manage.py test admin.tests --verbosity=2
"""
import re
import secrets
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, Client, modify_settings
from django.urls import reverse

from admin.models import DeviceAuthorizationRequest
from core.device.models import AuthorizedDevice

# ── Constants ─────────────────────────────────────────────────────────────────

FAKE_CSR = (
    "-----BEGIN CERTIFICATE REQUEST-----\n"
    "MIICXzCCAUcCAQAwGjEYMBYGA1UEAxMPVGVzdCBEZXZpY2UgUEMwggEiMA0GCSqG\n"
    "SIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7o4qne60TB3wolGUk1I4zwBEHcFAjUqb/\n"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgIDAQABoAAwDQYJKoZI\n"
    "hvcNAQELBQADggEBAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n"
    "-----END CERTIFICATE REQUEST-----"
)

INVALID_CSR = "NOT_A_VALID_CSR_BLOCK"

# Remove device auth middleware for all test requests so we test view logic only
NO_DEVICE_MIDDLEWARE = modify_settings(
    MIDDLEWARE={'remove': ['core.device.middleware.DeviceAuthMiddleware']}
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_approved_request(user, fingerprint=None, csr_pem='', device_name='Test PC'):
    """Create an approved DeviceAuthorizationRequest."""
    fp = fingerprint or secrets.token_hex(16)
    return DeviceAuthorizationRequest.objects.create(
        device_fingerprint=fp,
        ip_address='192.168.1.50',
        user_agent='TestBrowser/1.0',
        hostname='test-pc',
        requested_by=user,
        reason='Testing',
        device_name=device_name,
        security_level='STANDARD',
        status='approved',
        csr_pem=csr_pem,
    )


def _decode(resp):
    """Return decoded response content, handling gzip transparently."""
    import gzip as _gzip
    content = resp.content
    if content[:2] == b'\x1f\x8b':
        content = _gzip.decompress(content)
    return content.decode('utf-8')


# ── AttachCSRViewTests ────────────────────────────────────────────────────────

@NO_DEVICE_MIDDLEWARE
class AttachCSRViewTests(TestCase):
    """Tests for admin.views.attach_csr_to_device."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_csr', password='pass', email='a@b.com'
        )
        self.regular_user = User.objects.create_user(
            username='regular_csr', password='pass'
        )

    # ── access control ─────────────────────────────────────────────

    def test_non_superuser_cannot_attach_csr(self):
        """Regular user is redirected away (superuser check) — CSR must not save."""
        req = _make_approved_request(self.regular_user)
        self.client.force_login(self.regular_user)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        resp = self.client.post(url, {'csr_pem': FAKE_CSR})
        self.assertIn(resp.status_code, [302, 403])
        req.refresh_from_db()
        self.assertEqual(req.csr_pem, '')

    def test_get_not_allowed(self):
        """GET to attach_csr endpoint must be rejected by require_POST (405)."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)

    # ── validation ─────────────────────────────────────────────────

    def test_invalid_csr_rejected_with_error(self):
        """POST with invalid PEM block must not save and must show error message."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        resp = self.client.post(url, {'csr_pem': INVALID_CSR}, follow=True)
        req.refresh_from_db()
        self.assertEqual(req.csr_pem, '', 'Invalid CSR must not be saved')
        messages_text = [str(m) for m in resp.context['messages']]
        self.assertTrue(
            any('invalid' in m.lower() or 'valid' in m.lower() for m in messages_text),
            f'Expected error message, got: {messages_text}',
        )

    def test_empty_csr_rejected(self):
        """POST with blank csr_pem must not save."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        self.client.post(url, {'csr_pem': '   '}, follow=True)
        req.refresh_from_db()
        self.assertEqual(req.csr_pem, '')

    def test_non_approved_request_returns_404(self):
        """attach_csr requires status=approved; pending request must 404."""
        pending = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.0.0.1',
            user_agent='Test/1.0',
            requested_by=self.superuser,
            reason='Test',
            device_name='Pending PC',
            status='pending',
        )
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[pending.id])
        resp = self.client.post(url, {'csr_pem': FAKE_CSR})
        self.assertEqual(resp.status_code, 404)

    # ── happy path ─────────────────────────────────────────────────

    def test_valid_csr_saved_to_db(self):
        """POST with valid PEM CSR must persist in csr_pem field."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        self.client.post(url, {'csr_pem': FAKE_CSR}, follow=True)
        req.refresh_from_db()
        self.assertIn('BEGIN CERTIFICATE REQUEST', req.csr_pem)

    def test_valid_csr_redirects_to_view_page(self):
        """After saving CSR, must redirect to view_device_request."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        resp = self.client.post(url, {'csr_pem': FAKE_CSR})
        self.assertRedirects(
            resp,
            reverse('armguard_admin:view_device_request', args=[req.id]),
        )

    def test_success_message_shown(self):
        """Success message must appear after valid attach."""
        req = _make_approved_request(self.superuser)
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        resp = self.client.post(url, {'csr_pem': FAKE_CSR}, follow=True)
        messages_text = [str(m) for m in resp.context['messages']]
        self.assertTrue(
            any('certificate' in m.lower() or 'attached' in m.lower() for m in messages_text),
            f'Expected success message, got: {messages_text}',
        )

    # ── idempotency ────────────────────────────────────────────────

    def test_overwrite_existing_csr(self):
        """Attaching a new CSR to an existing-CSR device must overwrite it."""
        req = _make_approved_request(self.superuser, csr_pem=FAKE_CSR)
        new_csr = FAKE_CSR.replace(
            'MIICXzCCAUcCAQAwGj',
            'MIICXzCCAUcCAQAwAA',
        )
        self.client.force_login(self.superuser)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        self.client.post(url, {'csr_pem': new_csr})
        req.refresh_from_db()
        self.assertIn('BEGIN CERTIFICATE REQUEST', req.csr_pem)
        self.assertIn('MIICXzCCAUcCAQAwAA', req.csr_pem)


# ── ViewDeviceRequestTemplateTests ───────────────────────────────────────────

@NO_DEVICE_MIDDLEWARE
class ViewDeviceRequestTemplateTests(TestCase):
    """Tests that view_device_request.html shows/hides the attach panel correctly."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_view', password='pass', email='v@b.com'
        )
        self.client.force_login(self.superuser)

    def test_attach_panel_shown_when_no_csr(self):
        """Green attach-CSR panel must appear for approved devices with no CSR."""
        req = _make_approved_request(self.superuser, csr_pem='')
        url = reverse('armguard_admin:view_device_request', args=[req.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        html = _decode(resp)
        self.assertIn('csr-panel', html)
        self.assertIn('Attach Client Certificate', html)

    def test_attach_panel_hidden_when_csr_present(self):
        """Green panel must NOT appear if CSR is already attached."""
        req = _make_approved_request(self.superuser, csr_pem=FAKE_CSR)
        url = reverse('armguard_admin:view_device_request', args=[req.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        html = _decode(resp)
        self.assertNotIn('csr-panel', html)

    def test_attach_panel_hidden_for_pending_request(self):
        """Pending requests must not show the attach panel."""
        pending = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.0.0.2',
            user_agent='Test/1.0',
            requested_by=self.superuser,
            reason='Test',
            device_name='Pending PC',
            status='pending',
        )
        url = reverse('armguard_admin:view_device_request', args=[pending.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        html = _decode(resp)
        self.assertNotIn('csr-panel', html)

    def test_warning_text_present_in_attach_panel(self):
        """Deletion warning must be present in the attach panel HTML."""
        req = _make_approved_request(self.superuser, csr_pem='')
        url = reverse('armguard_admin:view_device_request', args=[req.id])
        resp = self.client.get(url)
        html = _decode(resp)
        self.assertIn('DO NOT delete', html)
        self.assertIn('armguard_device.key', html)
        self.assertIn('only recovery option', html)


# ── RequestDeviceAuthTemplateTests ───────────────────────────────────────────

@NO_DEVICE_MIDDLEWARE
class RequestDeviceAuthTemplateTests(TestCase):
    """Tests that request_device_auth.html uses a hidden CSR field (no visible textarea)."""

    def setUp(self):
        self.user = User.objects.create_user(username='req_user', password='pass')
        self.client.force_login(self.user)

    def _get_html(self):
        url = reverse('armguard_admin:request_device_authorization')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        return _decode(resp)

    def test_page_renders_200(self):
        url = reverse('armguard_admin:request_device_authorization')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    def test_csr_field_is_hidden_input(self):
        """CSR field must be <input type="hidden" name="csr_pem">, not a textarea."""
        html = self._get_html()
        self.assertIn('type="hidden"', html)
        self.assertIn('name="csr_pem"', html)
        visible_textarea = re.search(r'<textarea[^>]*name=["\']csr_pem["\']', html)
        self.assertIsNone(visible_textarea, 'CSR textarea must be hidden, not a visible textarea')

    def test_webcrypto_script_present(self):
        """Page must include the WebCrypto CSR generation script markers."""
        html = self._get_html()
        self.assertIn('armguard-keystore', html)   # IndexedDB DB name
        self.assertIn('CERTIFICATE REQUEST', html)  # PEM label in JS template
        self.assertIn('generateCSR', html)

    def test_localstorage_backup_present(self):
        """Page must include the localStorage backup key constant."""
        html = self._get_html()
        self.assertIn('armguard.device.keypair', html)

    def test_deletion_warning_in_page(self):
        """Warning about not deleting the key must be visible in the page."""
        html = self._get_html()
        self.assertIn('DO NOT delete', html)
        self.assertIn('only recovery option', html)

    def test_submit_button_present(self):
        """Submit button with btn-submit class must be present."""
        html = self._get_html()
        self.assertIn('btn-submit', html)
        self.assertIn('Submit Authorization Request', html)


# ── CSRFullFlowTests ─────────────────────────────────────────────────────────

@NO_DEVICE_MIDDLEWARE
class CSRFullFlowTests(TestCase):
    """End-to-end: submit request with CSR → approve → v2 AuthorizedDevice active."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='flow_admin', password='pass', email='f@b.com'
        )
        self.officer = User.objects.create_user(
            username='flow_officer', password='pass'
        )

    def test_submit_with_csr_stores_it(self):
        """DeviceAuthorizationRequest created via POST stores csr_pem."""
        client = Client()
        client.force_login(self.officer)
        url = reverse('armguard_admin:request_device_authorization')
        client.post(url, {
            'device_name': 'Flow Test PC',
            'reason':      'Integration test',
            'csr_pem':     FAKE_CSR,
        }, follow=True)
        req = DeviceAuthorizationRequest.objects.filter(
            requested_by=self.officer,
            device_name='Flow Test PC',
        ).first()
        self.assertIsNotNone(req, 'DeviceAuthorizationRequest must be created')
        self.assertIn('BEGIN CERTIFICATE REQUEST', req.csr_pem)

    def test_approve_with_csr_creates_active_v2_device(self):
        """approve() with CSR creates an ACTIVE AuthorizedDevice in v2 DB.

        The mTLS CA files don't exist on dev machines, so we mock the cert
        issuance step — the important thing is that the v2 device is created.
        """
        req = _make_approved_request(self.officer, csr_pem=FAKE_CSR, device_name='CSR PC')
        req.status = 'pending'
        req.save()
        count_before = AuthorizedDevice.objects.count()
        # Patch _issue_client_certificate_from_csr so CA files are not needed
        with patch.object(
            type(req),
            '_issue_client_certificate_from_csr',
            return_value=('-----BEGIN CERTIFICATE-----\nFAKE\n-----END CERTIFICATE-----', 1234),
        ):
            req.approve(reviewer=self.admin, device_name='CSR PC', security_level='STANDARD')
        self.assertEqual(
            AuthorizedDevice.objects.count(), count_before + 1,
            'approve() must create one v2 AuthorizedDevice',
        )
        v2 = AuthorizedDevice.objects.order_by('-enrolled_at').first()
        self.assertEqual(v2.status, AuthorizedDevice.Status.ACTIVE)
        self.assertEqual(v2.device_name, 'CSR PC')

    def test_approve_without_csr_still_creates_v2_device(self):
        """approve() without CSR must still create v2 device (CSR optional for access)."""
        req = _make_approved_request(self.officer, csr_pem='', device_name='No CSR PC')
        req.status = 'pending'
        req.save()
        count_before = AuthorizedDevice.objects.count()
        req.approve(reviewer=self.admin, device_name='No CSR PC', security_level='STANDARD')
        self.assertEqual(AuthorizedDevice.objects.count(), count_before + 1)

    def test_csr_still_stored_after_attach(self):
        """After attach_csr_to_device POST, csr_pem persists on refresh_from_db."""
        req = _make_approved_request(self.admin, csr_pem='')
        client = Client()
        client.force_login(self.admin)
        url = reverse('armguard_admin:attach_csr_to_device', args=[req.id])
        client.post(url, {'csr_pem': FAKE_CSR})
        req.refresh_from_db()
        self.assertIn('BEGIN CERTIFICATE REQUEST', req.csr_pem,
                      'CSR must persist in DB after attach')
