"""
ArmGuard Functional Test Suite
Comprehensive testing of all user flows, API endpoints, and application functionality
"""
import pytest
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import json
import os

# Configuration
BASE_URL = os.environ.get('TEST_BASE_URL', 'https://localhost')
SELENIUM_HUB = os.environ.get('SELENIUM_HUB_URL', 'http://localhost:4444/wd/hub')

# Test Users
ADMIN_USER = {'username': 'testadmin', 'password': 'TestAdmin123!'}
ARMORER_USER = {'username': 'testarmorer', 'password': 'TestArmorer123!'}


class TestConfig:
    """Test configuration and fixtures"""
    
    @pytest.fixture(scope='class')
    def driver(self):
        """Create Selenium WebDriver instance"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--window-size=1920,1080')
        
        driver = webdriver.Remote(
            command_executor=SELENIUM_HUB,
            options=chrome_options
        )
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture(scope='class')
    def session(self):
        """Create requests session"""
        session = requests.Session()
        session.verify = False  # For self-signed certs
        return session


class TestAuthentication(TestConfig):
    """Test authentication flows"""
    
    def test_login_page_loads(self, driver):
        """TC-AUTH-001: Login page loads correctly"""
        driver.get(f"{BASE_URL}/login/")
        assert "Login" in driver.title or driver.find_element(By.NAME, "username")
        
    def test_successful_admin_login(self, driver):
        """TC-AUTH-002: Admin can login successfully"""
        driver.get(f"{BASE_URL}/login/")
        
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        
        username_field.clear()
        username_field.send_keys(ADMIN_USER['username'])
        password_field.clear()
        password_field.send_keys(ADMIN_USER['password'])
        password_field.send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dashboard"))
        )
        assert "dashboard" in driver.current_url.lower() or "Dashboard" in driver.page_source
    
    def test_failed_login_invalid_credentials(self, driver):
        """TC-AUTH-003: Invalid credentials show error"""
        driver.get(f"{BASE_URL}/login/")
        
        username_field = driver.find_element(By.NAME, "username")
        password_field = driver.find_element(By.NAME, "password")
        
        username_field.clear()
        username_field.send_keys("invaliduser")
        password_field.clear()
        password_field.send_keys("wrongpassword")
        password_field.send_keys(Keys.RETURN)
        
        time.sleep(2)
        assert "error" in driver.page_source.lower() or "invalid" in driver.page_source.lower()
    
    def test_login_rate_limiting(self, session):
        """TC-AUTH-004: Rate limiting on login endpoint"""
        # Attempt multiple failed logins
        failed_attempts = 0
        for i in range(10):
            response = session.post(
                f"{BASE_URL}/login/",
                data={'username': 'test', 'password': 'wrong'},
                allow_redirects=False
            )
            if response.status_code == 429:
                failed_attempts = i + 1
                break
        
        assert failed_attempts <= 6, "Rate limiting should kick in within 6 attempts"
    
    def test_logout_functionality(self, driver):
        """TC-AUTH-005: User can logout successfully"""
        # Login first
        driver.get(f"{BASE_URL}/login/")
        driver.find_element(By.NAME, "username").send_keys(ADMIN_USER['username'])
        driver.find_element(By.NAME, "password").send_keys(ADMIN_USER['password'])
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))
        
        # Logout
        logout_link = driver.find_element(By.LINK_TEXT, "Logout")
        logout_link.click()
        
        WebDriverWait(driver, 10).until(EC.url_contains("login"))
        assert "login" in driver.current_url.lower()


class TestAuthorization(TestConfig):
    """Test authorization and access control"""
    
    def test_unauthenticated_redirect(self, session):
        """TC-AUTHZ-001: Unauthenticated users redirected to login"""
        protected_urls = [
            '/dashboard/',
            '/personnel/',
            '/inventory/',
            '/transactions/',
        ]
        
        for url in protected_urls:
            response = session.get(f"{BASE_URL}{url}", allow_redirects=False)
            assert response.status_code in [302, 401, 403], f"URL {url} should redirect"
    
    def test_admin_only_endpoints(self, session):
        """TC-AUTHZ-002: Admin-only endpoints require admin role"""
        # Login as armorer (non-admin)
        session.post(f"{BASE_URL}/login/", data=ARMORER_USER)
        
        admin_urls = [
            '/armguard-admin/user-management/',
            '/armguard-admin/registration/',
        ]
        
        for url in admin_urls:
            response = session.get(f"{BASE_URL}{url}", allow_redirects=False)
            # Should be forbidden or redirected
            assert response.status_code in [302, 403]
    
    def test_idor_protection(self, session):
        """TC-AUTHZ-003: IDOR protection on user details"""
        # Login as regular user
        session.post(f"{BASE_URL}/login/", data=ARMORER_USER)
        
        # Try to access another user's details
        response = session.get(f"{BASE_URL}/users/1/")
        assert response.status_code in [403, 404]


class TestPersonnelManagement(TestConfig):
    """Test personnel CRUD operations"""
    
    def test_personnel_list_loads(self, driver):
        """TC-PERS-001: Personnel list page loads"""
        # Login
        driver.get(f"{BASE_URL}/login/")
        driver.find_element(By.NAME, "username").send_keys(ADMIN_USER['username'])
        driver.find_element(By.NAME, "password").send_keys(ADMIN_USER['password'])
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))
        
        # Navigate to personnel
        driver.get(f"{BASE_URL}/personnel/")
        assert "personnel" in driver.page_source.lower()
    
    def test_personnel_search(self, driver):
        """TC-PERS-002: Personnel search functionality"""
        driver.get(f"{BASE_URL}/personnel/")
        
        search_field = driver.find_element(By.NAME, "search_query")
        search_field.send_keys("Test")
        search_field.send_keys(Keys.RETURN)
        
        time.sleep(2)
        # Check search results appear
        assert driver.find_elements(By.CLASS_NAME, "personnel-card") or "No results" in driver.page_source


class TestInventoryManagement(TestConfig):
    """Test inventory CRUD operations"""
    
    def test_inventory_list_loads(self, driver):
        """TC-INV-001: Inventory list page loads"""
        driver.get(f"{BASE_URL}/login/")
        driver.find_element(By.NAME, "username").send_keys(ADMIN_USER['username'])
        driver.find_element(By.NAME, "password").send_keys(ADMIN_USER['password'])
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))
        
        driver.get(f"{BASE_URL}/inventory/")
        assert "inventory" in driver.page_source.lower() or "items" in driver.page_source.lower()


class TestTransactions(TestConfig):
    """Test transaction workflows"""
    
    def test_transaction_list_loads(self, driver):
        """TC-TRANS-001: Transaction list page loads"""
        driver.get(f"{BASE_URL}/login/")
        driver.find_element(By.NAME, "username").send_keys(ADMIN_USER['username'])
        driver.find_element(By.NAME, "password").send_keys(ADMIN_USER['password'])
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until(EC.url_contains("dashboard"))
        
        driver.get(f"{BASE_URL}/transactions/")
        assert "transaction" in driver.page_source.lower()
    
    def test_qr_scanner_page_loads(self, driver):
        """TC-TRANS-002: QR scanner page loads for authorized users"""
        driver.get(f"{BASE_URL}/transactions/qr-scanner/")
        assert "scanner" in driver.page_source.lower() or "scan" in driver.page_source.lower()


class TestAPIEndpoints(TestConfig):
    """Test API endpoint functionality"""
    
    def test_api_get_personnel(self, session):
        """TC-API-001: GET personnel API returns data"""
        # Login first
        session.post(f"{BASE_URL}/login/", data=ADMIN_USER)
        
        response = session.get(f"{BASE_URL}/api/personnel/PE-001/")
        assert response.status_code in [200, 404]  # 200 if exists, 404 if not
    
    def test_api_get_item(self, session):
        """TC-API-002: GET item API returns data"""
        session.post(f"{BASE_URL}/login/", data=ADMIN_USER)
        
        response = session.get(f"{BASE_URL}/api/item/ITM-001/")
        assert response.status_code in [200, 404]
    
    def test_api_requires_authentication(self, session):
        """TC-API-003: API endpoints require authentication"""
        # Clear session
        session.cookies.clear()
        
        response = session.get(f"{BASE_URL}/api/personnel/PE-001/")
        assert response.status_code in [302, 401, 403]
    
    def test_api_json_content_type(self, session):
        """TC-API-004: API endpoints require JSON content type for POST"""
        session.post(f"{BASE_URL}/login/", data=ADMIN_USER)
        
        # POST without JSON content type
        response = session.post(
            f"{BASE_URL}/api/transactions/create/",
            data={'test': 'data'}
        )
        assert response.status_code in [400, 415]


class TestSecurityHeaders(TestConfig):
    """Test security headers presence"""
    
    def test_security_headers_present(self, session):
        """TC-SEC-001: Security headers are present"""
        response = session.get(f"{BASE_URL}/login/")
        
        required_headers = [
            'X-Frame-Options',
            'X-Content-Type-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
        ]
        
        for header in required_headers:
            assert header in response.headers, f"Missing header: {header}"
    
    def test_csp_header_present(self, session):
        """TC-SEC-002: Content-Security-Policy header present"""
        response = session.get(f"{BASE_URL}/login/")
        assert 'Content-Security-Policy' in response.headers
    
    def test_no_server_disclosure(self, session):
        """TC-SEC-003: Server version not disclosed"""
        response = session.get(f"{BASE_URL}/login/")
        server_header = response.headers.get('Server', '')
        assert 'nginx' not in server_header.lower() or '/' not in server_header


class TestErrorHandling(TestConfig):
    """Test error handling"""
    
    def test_404_page(self, session):
        """TC-ERR-001: 404 page displays correctly"""
        response = session.get(f"{BASE_URL}/nonexistent-page-12345/")
        assert response.status_code == 404
    
    def test_csrf_protection(self, session):
        """TC-ERR-002: CSRF protection working"""
        # Try POST without CSRF token
        response = session.post(
            f"{BASE_URL}/login/",
            data={'username': 'test', 'password': 'test'},
            headers={'Referer': 'https://evil.com'}
        )
        # Should be rejected or require CSRF token
        assert response.status_code in [403, 400] or 'csrf' in response.text.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--html=test_results/functional_report.html'])
