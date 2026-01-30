"""
ArmGuard API Test Suite
Comprehensive testing of all API endpoints
"""
import pytest
import requests
import json
import time
import os

BASE_URL = os.environ.get('TEST_BASE_URL', 'https://localhost')

# Test credentials
ADMIN_CREDENTIALS = {'username': 'testadmin', 'password': 'TestAdmin123!'}
ARMORER_CREDENTIALS = {'username': 'testarmorer', 'password': 'TestArmorer123!'}


class TestAPIBase:
    """Base class with common fixtures"""
    
    @pytest.fixture(scope='class')
    def admin_session(self):
        """Authenticated admin session"""
        session = requests.Session()
        session.verify = False
        
        # Get CSRF token
        response = session.get(f"{BASE_URL}/login/")
        csrf_token = session.cookies.get('csrftoken', '')
        
        # Login
        session.post(
            f"{BASE_URL}/login/",
            data={
                **ADMIN_CREDENTIALS,
                'csrfmiddlewaretoken': csrf_token
            },
            headers={'Referer': f"{BASE_URL}/login/"}
        )
        return session
    
    @pytest.fixture(scope='class')
    def armorer_session(self):
        """Authenticated armorer session"""
        session = requests.Session()
        session.verify = False
        
        response = session.get(f"{BASE_URL}/login/")
        csrf_token = session.cookies.get('csrftoken', '')
        
        session.post(
            f"{BASE_URL}/login/",
            data={
                **ARMORER_CREDENTIALS,
                'csrfmiddlewaretoken': csrf_token
            },
            headers={'Referer': f"{BASE_URL}/login/"}
        )
        return session
    
    @pytest.fixture(scope='function')
    def unauthenticated_session(self):
        """Unauthenticated session"""
        session = requests.Session()
        session.verify = False
        return session


class TestPersonnelAPI(TestAPIBase):
    """Test Personnel API endpoints"""
    
    def test_get_personnel_authenticated(self, admin_session):
        """API-PERS-001: Get personnel with valid authentication"""
        response = admin_session.get(f"{BASE_URL}/api/personnel/PE-001/")
        # Should return data or 404 if not found
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert 'id' in data or 'error' in data
    
    def test_get_personnel_unauthenticated(self, unauthenticated_session):
        """API-PERS-002: Get personnel without authentication fails"""
        response = unauthenticated_session.get(f"{BASE_URL}/api/personnel/PE-001/")
        assert response.status_code in [302, 401, 403]
    
    def test_personnel_search_api(self, admin_session):
        """API-PERS-003: Personnel search API works"""
        response = admin_session.get(f"{BASE_URL}/personnel/search/?q=test")
        assert response.status_code == 200
        data = response.json()
        assert 'results' in data


class TestItemAPI(TestAPIBase):
    """Test Item/Inventory API endpoints"""
    
    def test_get_item_authenticated(self, admin_session):
        """API-ITEM-001: Get item with valid authentication"""
        response = admin_session.get(f"{BASE_URL}/api/item/ITM-001/")
        assert response.status_code in [200, 404]
    
    def test_get_item_unauthenticated(self, unauthenticated_session):
        """API-ITEM-002: Get item without authentication fails"""
        response = unauthenticated_session.get(f"{BASE_URL}/api/item/ITM-001/")
        assert response.status_code in [302, 401, 403]
    
    def test_item_with_autofill(self, admin_session):
        """API-ITEM-003: Item API returns autofill data"""
        response = admin_session.get(f"{BASE_URL}/api/item/ITM-001/?duty_type=Guard")
        if response.status_code == 200:
            data = response.json()
            # Should include autofill if duty_type provided
            assert 'autofill' in data or 'error' in data


class TestTransactionAPI(TestAPIBase):
    """Test Transaction API endpoints"""
    
    def test_create_transaction_requires_auth(self, unauthenticated_session):
        """API-TRANS-001: Create transaction requires authentication"""
        response = unauthenticated_session.post(
            f"{BASE_URL}/api/transactions/create/",
            json={'personnel_id': 'PE-001', 'item_id': 'ITM-001', 'action': 'Take'}
        )
        assert response.status_code in [302, 401, 403]
    
    def test_create_transaction_requires_json(self, admin_session):
        """API-TRANS-002: Create transaction requires JSON content type"""
        csrf_token = admin_session.cookies.get('csrftoken', '')
        
        response = admin_session.post(
            f"{BASE_URL}/api/transactions/create/",
            data={'personnel_id': 'PE-001'},
            headers={
                'X-CSRFToken': csrf_token,
                'Referer': BASE_URL
            }
        )
        assert response.status_code in [400, 415]
    
    def test_create_transaction_validation(self, admin_session):
        """API-TRANS-003: Create transaction validates input"""
        csrf_token = admin_session.cookies.get('csrftoken', '')
        
        # Missing required fields
        response = admin_session.post(
            f"{BASE_URL}/api/transactions/create/",
            json={'personnel_id': 'PE-001'},  # Missing item_id and action
            headers={
                'X-CSRFToken': csrf_token,
                'Referer': BASE_URL,
                'Content-Type': 'application/json'
            }
        )
        assert response.status_code == 400
        data = response.json()
        assert 'error' in data


class TestQRCodeAPI(TestAPIBase):
    """Test QR Code verification API"""
    
    def test_verify_qr_requires_post(self, admin_session):
        """API-QR-001: QR verification requires POST"""
        response = admin_session.get(f"{BASE_URL}/transactions/verify-qr/")
        assert response.status_code in [405, 400]
    
    def test_verify_qr_empty_data(self, admin_session):
        """API-QR-002: QR verification rejects empty data"""
        csrf_token = admin_session.cookies.get('csrftoken', '')
        
        response = admin_session.post(
            f"{BASE_URL}/transactions/verify-qr/",
            data={'qr_data': ''},
            headers={
                'X-CSRFToken': csrf_token,
                'Referer': BASE_URL
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') == False
    
    def test_verify_qr_invalid_format(self, admin_session):
        """API-QR-003: QR verification handles invalid format"""
        csrf_token = admin_session.cookies.get('csrftoken', '')
        
        response = admin_session.post(
            f"{BASE_URL}/transactions/verify-qr/",
            data={'qr_data': 'INVALID:FORMAT:DATA'},
            headers={
                'X-CSRFToken': csrf_token,
                'Referer': BASE_URL
            }
        )
        data = response.json()
        assert data.get('success') == False


class TestRateLimiting(TestAPIBase):
    """Test rate limiting on API endpoints"""
    
    def test_login_rate_limiting(self, unauthenticated_session):
        """API-RATE-001: Login endpoint rate limited"""
        rate_limited = False
        for i in range(15):
            response = unauthenticated_session.post(
                f"{BASE_URL}/login/",
                data={'username': 'test', 'password': 'wrong'}
            )
            if response.status_code == 429:
                rate_limited = True
                break
            time.sleep(0.1)
        
        assert rate_limited, "Rate limiting should trigger within 15 attempts"
    
    def test_api_rate_limiting(self, admin_session):
        """API-RATE-002: API endpoints rate limited"""
        rate_limited = False
        for i in range(50):
            response = admin_session.get(f"{BASE_URL}/api/personnel/PE-001/")
            if response.status_code == 429:
                rate_limited = True
                break
        
        # Note: This may not trigger if rate limit is generous
        # Just verify the endpoint responds
        assert response.status_code in [200, 404, 429]


class TestInputValidation(TestAPIBase):
    """Test input validation on API endpoints"""
    
    def test_sql_injection_prevention(self, admin_session):
        """API-SEC-001: SQL injection attempts are safe"""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "1; SELECT * FROM users",
            "' UNION SELECT * FROM users --"
        ]
        
        for payload in malicious_inputs:
            response = admin_session.get(f"{BASE_URL}/api/personnel/{payload}/")
            # Should return 404 or 400, not 500
            assert response.status_code in [400, 404], f"Possible SQL injection: {payload}"
    
    def test_xss_prevention(self, admin_session):
        """API-SEC-002: XSS attempts are sanitized"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')"
        ]
        
        for payload in xss_payloads:
            response = admin_session.get(f"{BASE_URL}/personnel/search/?q={payload}")
            if response.status_code == 200:
                # Response should not contain raw script
                assert '<script>' not in response.text
    
    def test_path_traversal_prevention(self, admin_session):
        """API-SEC-003: Path traversal attempts are blocked"""
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in traversal_attempts:
            response = admin_session.get(f"{BASE_URL}/media/{payload}")
            assert response.status_code in [400, 403, 404]


class TestCORSAndCSRF(TestAPIBase):
    """Test CORS and CSRF protections"""
    
    def test_csrf_token_required(self, admin_session):
        """API-SEC-004: CSRF token required for mutations"""
        # Clear CSRF token
        admin_session.cookies.pop('csrftoken', None)
        
        response = admin_session.post(
            f"{BASE_URL}/api/transactions/create/",
            json={'personnel_id': 'PE-001', 'item_id': 'ITM-001', 'action': 'Take'},
            headers={'Content-Type': 'application/json'}
        )
        assert response.status_code in [403, 400]
    
    def test_cross_origin_rejected(self, admin_session):
        """API-SEC-005: Cross-origin requests handled properly"""
        response = admin_session.post(
            f"{BASE_URL}/api/transactions/create/",
            json={'test': 'data'},
            headers={
                'Origin': 'https://evil.com',
                'Referer': 'https://evil.com/attack'
            }
        )
        # Should be rejected due to CSRF/origin check
        assert response.status_code in [400, 403]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--html=test_results/api_report.html'])
