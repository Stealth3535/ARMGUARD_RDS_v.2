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
        """DeviceAuthorizationRequest created via POST stores csr_pem, mac, pc_user, specs."""
        client = Client()
        client.force_login(self.officer)
        url = reverse('armguard_admin:request_device_authorization')
        client.post(url, {
            'device_name':  'Flow Test PC',
            'reason':       'Integration test',
            'csr_pem':      FAKE_CSR,
            'mac_address':  'AA:BB:CC:DD:EE:FF',
            'pc_username':  'test.officer',
            'system_specs': '{"os":"Win32","cpu_cores":8,"ram_gb":16}',
        }, follow=True)
        req = DeviceAuthorizationRequest.objects.filter(
            requested_by=self.officer,
            device_name='Flow Test PC',
        ).first()
        self.assertIsNotNone(req, 'DeviceAuthorizationRequest must be created')
        self.assertIn('BEGIN CERTIFICATE REQUEST', req.csr_pem)
        self.assertEqual(req.mac_address, 'AA:BB:CC:DD:EE:FF')
        self.assertEqual(req.pc_username, 'test.officer')
        self.assertEqual(req.system_specs.get('cpu_cores'), 8)

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

    def test_new_fields_saved_on_request_creation(self):
        """mac_address, pc_username, and system_specs are saved to the DB on creation."""
        req = DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.0.0.5',
            user_agent='TestBrowser/1.0',
            requested_by=self.officer,
            reason='Testing PC fields',
            device_name='Field Test PC',
            mac_address='11:22:33:44:55:66',
            pc_username='field.user',
            system_specs={'os': 'Linux x86_64', 'cpu_cores': 4, 'ram_gb': 8},
        )
        req.refresh_from_db()
        self.assertEqual(req.mac_address, '11:22:33:44:55:66')
        self.assertEqual(req.pc_username, 'field.user')
        self.assertEqual(req.system_specs['cpu_cores'], 4)

    def test_view_page_shows_mac_and_pc_username(self):
        """view_device_request template renders MAC address and PC username."""
        req = _make_approved_request(
            self.admin,
            csr_pem='',
            device_name='MAC Test PC',
        )
        req.mac_address = 'AA:BB:CC:DD:EE:FF'
        req.pc_username = 'mac.test.user'
        req.system_specs = {'os': 'Win32', 'cpu_cores': 8}
        req.save()

        client = Client()
        client.force_login(self.admin)
        url = reverse('armguard_admin:view_device_request', args=[req.id])
        resp = client.get(url)
        html = _decode(resp)
        self.assertIn('AA:BB:CC:DD:EE:FF', html, 'MAC address must appear in View page')
        self.assertIn('mac.test.user', html, 'PC username must appear in View page')
        self.assertIn('Win32', html, 'OS from system_specs must appear in View page')


# ── ManageDeviceRequestsTests ─────────────────────────────────────────────────

@NO_DEVICE_MIDDLEWARE
class ManageDeviceRequestsTests(TestCase):
    """Rigorous tests for /admin/device/requests/ (manage_device_requests view)."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='mgr_admin', password='pass', email='mgr@a.com'
        )
        self.officer = User.objects.create_user(
            username='mgr_officer', password='pass'
        )
        self.client = Client()
        self.client.force_login(self.admin)
        self.url = reverse('armguard_admin:manage_device_requests')

    # ── Access control ──────────────────────────────────────────────────────

    def test_redirects_anonymous(self):
        """Unauthenticated request is redirected to login."""
        c = Client()
        resp = c.get(self.url)
        self.assertIn(resp.status_code, (302, 403))

    def test_non_superuser_denied(self):
        """Regular (non-superuser) user cannot access the manage page."""
        c = Client()
        c.force_login(self.officer)
        resp = c.get(self.url)
        self.assertIn(resp.status_code, (302, 403))

    def test_superuser_gets_200(self):
        """Superuser can access the manage page."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    # ── Rendering with no records ───────────────────────────────────────────

    def test_empty_state_renders(self):
        """Page renders OK with zero requests."""
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        html = _decode(resp)
        self.assertIn('Device Authorization Requests', html)

    # ── Rendering with new fields ───────────────────────────────────────────

    def test_mac_and_pc_username_shown_in_list(self):
        """MAC address and PC username appear in the manage list for matching records."""
        req = _make_approved_request(self.admin, device_name='MAC List PC')
        req.mac_address = 'DE:AD:BE:EF:00:01'
        req.pc_username = 'list.user'
        req.save()

        resp = self.client.get(self.url + '?status=approved')
        html = _decode(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('DE:AD:BE:EF:00:01', html, 'MAC must appear in list')
        self.assertIn('list.user', html, 'PC username must appear in list')

    def test_system_specs_pills_shown_in_list(self):
        """OS / CPU / RAM spec pills render correctly in the list."""
        req = _make_approved_request(self.admin, device_name='Spec Pill PC')
        req.system_specs = {'os': 'Win64', 'cpu_cores': 16, 'ram_gb': 32}
        req.save()

        resp = self.client.get(self.url + '?status=approved')
        html = _decode(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Win64', html, 'OS pill must appear in list')
        self.assertIn('16 cores', html, 'CPU pill must appear in list')
        self.assertIn('32 GB RAM', html, 'RAM pill must appear in list')

    def test_old_record_empty_system_specs_does_not_crash(self):
        """Records with empty system_specs ({}) render without raising a 500."""
        req = _make_approved_request(self.admin, device_name='Old Record PC')
        # system_specs defaults to {} — simulate a legacy record
        req.system_specs = {}
        req.mac_address = ''
        req.pc_username = ''
        req.save()

        resp = self.client.get(self.url + '?status=approved')
        self.assertEqual(resp.status_code, 200,
            'Empty system_specs must not cause 500 — migration may not be applied on server')

    def test_csr_badge_shown_when_csr_present(self):
        """CSR on file badge appears when csr_pem is set."""
        req = _make_approved_request(self.admin, csr_pem=FAKE_CSR, device_name='CSR Badge PC')

        resp = self.client.get(self.url + '?status=approved')
        html = _decode(resp)
        self.assertIn('CSR on file', html, 'CSR badge must show when csr_pem exists')

    def test_no_csr_badge_shown_when_no_csr(self):
        """No CSR badge appears when csr_pem is empty."""
        req = _make_approved_request(self.admin, csr_pem='', device_name='No CSR Badge PC')

        resp = self.client.get(self.url + '?status=approved')
        html = _decode(resp)
        self.assertIn('No CSR', html, 'No-CSR badge must show when csr_pem is empty')

    # ── Status filter ───────────────────────────────────────────────────────

    def test_filter_approved_only_shows_approved(self):
        """?status=approved returns only approved records without crashing."""
        approved_fp = secrets.token_hex(16)
        DeviceAuthorizationRequest.objects.create(
            device_fingerprint=approved_fp,
            ip_address='10.10.10.10',
            user_agent='Browser/1',
            requested_by=self.admin,
            reason='Approved req',
            device_name='Approved One',
            status='approved',
        )
        pending_fp = secrets.token_hex(16)
        DeviceAuthorizationRequest.objects.create(
            device_fingerprint=pending_fp,
            ip_address='10.20.20.20',
            user_agent='Browser/1',
            requested_by=self.officer,
            reason='Pending req',
            device_name='Pending One',
            status='pending',
        )

        resp = self.client.get(self.url + '?status=approved')
        html = _decode(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('10.10.10.10', html, 'Approved IP must appear')
        self.assertNotIn('10.20.20.20', html, 'Pending IP must NOT appear in approved filter')

    def test_filter_pending_returns_200(self):
        resp = self.client.get(self.url + '?status=pending')
        self.assertEqual(resp.status_code, 200)

    def test_filter_rejected_returns_200(self):
        resp = self.client.get(self.url + '?status=rejected')
        self.assertEqual(resp.status_code, 200)

    def test_all_filter_returns_all_statuses(self):
        DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.30.30.30',
            user_agent='Browser/1',
            requested_by=self.admin,
            reason='All filter approved',
            device_name='AllFilter Approved',
            status='approved',
        )
        DeviceAuthorizationRequest.objects.create(
            device_fingerprint=secrets.token_hex(16),
            ip_address='10.40.40.40',
            user_agent='Browser/1',
            requested_by=self.officer,
            reason='All filter pending',
            device_name='AllFilter Pending',
            status='pending',
        )
        resp = self.client.get(self.url + '?status=all')
        html = _decode(resp)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('10.30.30.30', html, 'Approved IP must appear in all-filter')
        self.assertIn('10.40.40.40', html, 'Pending IP must appear in all-filter')

    # ── Context variables ───────────────────────────────────────────────────

    def test_stat_counts_in_context(self):
        """pending_count, approved_count, rejected_count are passed to context."""
        _make_approved_request(self.admin, device_name='Count Test')
        resp = self.client.get(self.url)
        self.assertIn('pending_count', resp.context)
        self.assertIn('approved_count', resp.context)
        self.assertIn('rejected_count', resp.context)
        self.assertGreaterEqual(resp.context['approved_count'], 1)

    def test_select_related_does_not_raise(self):
        """Queryset uses select_related so accessing requested_by doesn't trigger extra queries."""
        req = _make_approved_request(self.admin, device_name='SR Test')
        resp = self.client.get(self.url + '?status=approved')
        self.assertEqual(resp.status_code, 200)
        html = _decode(resp)
        # requested_by.username must be visible
        self.assertIn(self.admin.username, html)
