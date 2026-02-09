"""
ArmGuard Load Testing Configuration
Locust-based performance and stress testing
"""
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner, WorkerRunner
import random
import json
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ArmGuardUser(HttpUser):
    """
    Simulates a typical ArmGuard user performing various operations.
    Covers authentication, navigation, and transaction workflows.
    """
    
    wait_time = between(1, 5)  # Random wait between requests
    
    def on_start(self):
        """Login when user starts"""
        self.login()
        self.csrf_token = None
        self.logged_in = False
    
    def login(self):
        """Authenticate user"""
        # Get login page and CSRF token
        with self.client.get("/login/", catch_response=True) as response:
            if response.status_code == 200:
                # Extract CSRF token from cookies
                self.csrf_token = response.cookies.get('csrftoken', '')
        
        # Perform login
        with self.client.post(
            "/login/",
            data={
                "username": "testadmin",
                "password": "TestAdmin123!",
                "csrfmiddlewaretoken": self.csrf_token
            },
            headers={"Referer": f"{self.host}/login/"},
            catch_response=True
        ) as response:
            if response.status_code == 200 or response.status_code == 302:
                self.logged_in = True
                logger.info("User logged in successfully")
            else:
                logger.error(f"Login failed: {response.status_code}")
    
    @task(10)
    def view_dashboard(self):
        """View main dashboard - most common action"""
        with self.client.get("/dashboard/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 302:
                response.success()  # Redirect is OK
            else:
                response.failure(f"Dashboard failed: {response.status_code}")
    
    @task(8)
    def view_personnel_list(self):
        """View personnel list"""
        with self.client.get("/personnel/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Personnel list failed: {response.status_code}")
    
    @task(8)
    def view_inventory_list(self):
        """View inventory list"""
        with self.client.get("/inventory/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Inventory failed: {response.status_code}")
    
    @task(6)
    def view_transactions(self):
        """View transaction history"""
        with self.client.get("/transactions/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Transactions failed: {response.status_code}")
    
    @task(4)
    def search_personnel(self):
        """Search for personnel"""
        search_terms = ["Test", "SGT", "Officer", "Admin"]
        term = random.choice(search_terms)
        
        with self.client.get(
            f"/personnel/search/?q={term}",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Personnel search failed: {response.status_code}")
    
    @task(3)
    def view_qr_scanner(self):
        """View QR scanner page"""
        with self.client.get("/transactions/qr-scanner/", catch_response=True) as response:
            if response.status_code in [200, 302, 403]:
                response.success()
            else:
                response.failure(f"QR scanner failed: {response.status_code}")
    
    @task(2)
    def api_get_personnel(self):
        """API call to get personnel"""
        personnel_ids = ["PE-001", "PE-002", "PE-003"]
        pid = random.choice(personnel_ids)
        
        with self.client.get(
            f"/api/personnel/{pid}/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"API personnel failed: {response.status_code}")
    
    @task(2)
    def api_get_item(self):
        """API call to get item"""
        item_ids = ["ITM-001", "ITM-002", "ITM-003"]
        iid = random.choice(item_ids)
        
        with self.client.get(
            f"/api/item/{iid}/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"API item failed: {response.status_code}")
    
    @task(1)
    def view_static_resource(self):
        """Load static resources"""
        static_files = [
            "/static/css/style.css",
            "/static/js/main.js",
        ]
        resource = random.choice(static_files)
        
        with self.client.get(resource, catch_response=True) as response:
            if response.status_code in [200, 304]:
                response.success()
            else:
                response.failure(f"Static resource failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user performing administrative tasks.
    Higher weight on admin-specific operations.
    """
    
    wait_time = between(2, 8)
    weight = 1  # Less common than regular users
    
    def on_start(self):
        """Login as admin"""
        with self.client.get("/login/") as response:
            self.csrf_token = response.cookies.get('csrftoken', '')
        
        self.client.post(
            "/login/",
            data={
                "username": "testadmin",
                "password": "TestAdmin123!",
                "csrfmiddlewaretoken": self.csrf_token
            },
            headers={"Referer": f"{self.host}/login/"}
        )
    
    @task(5)
    def view_user_management(self):
        """View user management page"""
        with self.client.get("/armguard-admin/user-management/", catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"User management failed: {response.status_code}")
    
    @task(3)
    def view_audit_logs(self):
        """View audit logs"""
        with self.client.get("/armguard-admin/audit-logs/", catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Audit logs failed: {response.status_code}")
    
    @task(2)
    def view_registration_page(self):
        """View registration form"""
        with self.client.get("/armguard-admin/registration/", catch_response=True) as response:
            if response.status_code in [200, 302]:
                response.success()
            else:
                response.failure(f"Registration page failed: {response.status_code}")


class AnonymousUser(HttpUser):
    """
    Simulates unauthenticated users hitting public endpoints.
    Tests rate limiting and access control.
    """
    
    wait_time = between(0.5, 2)
    weight = 2
    
    @task(10)
    def view_login_page(self):
        """View login page"""
        with self.client.get("/login/", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Login page failed: {response.status_code}")
    
    @task(5)
    def attempt_access_protected(self):
        """Attempt to access protected resource"""
        protected_urls = ["/dashboard/", "/personnel/", "/inventory/"]
        url = random.choice(protected_urls)
        
        with self.client.get(url, catch_response=True, allow_redirects=False) as response:
            if response.status_code in [302, 401, 403]:
                response.success()  # Expected behavior
            elif response.status_code == 200:
                response.failure("Protected resource accessible without auth")
            else:
                response.failure(f"Unexpected status: {response.status_code}")
    
    @task(2)
    def failed_login_attempt(self):
        """Simulate failed login (test rate limiting)"""
        with self.client.get("/login/") as response:
            csrf_token = response.cookies.get('csrftoken', '')
        
        with self.client.post(
            "/login/",
            data={
                "username": "attacker",
                "password": "wrongpassword",
                "csrfmiddlewaretoken": csrf_token
            },
            headers={"Referer": f"{self.host}/login/"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 302, 429]:
                response.success()  # 429 = rate limited (expected)
            else:
                response.failure(f"Unexpected login response: {response.status_code}")


# Event handlers for test lifecycle
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    logger.info("=" * 60)
    logger.info("ArmGuard Load Test Starting")
    logger.info("=" * 60)
    if isinstance(environment.runner, MasterRunner):
        logger.info("Running as MASTER node")
    elif isinstance(environment.runner, WorkerRunner):
        logger.info("Running as WORKER node")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops"""
    logger.info("=" * 60)
    logger.info("ArmGuard Load Test Complete")
    logger.info("=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track request metrics"""
    if response_time > 2000:  # Log slow requests (>2s)
        logger.warning(f"Slow request: {name} took {response_time}ms")
    
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
