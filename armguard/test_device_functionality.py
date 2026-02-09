#!/usr/bin/env python3
"""
Complete device authorization functionality test
Tests actual middleware behavior and security enforcement
"""
import os
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.conf import settings
from django.contrib.auth import get_user_model
from core.middleware.device_authorization import DeviceAuthorizationMiddleware

User = get_user_model()

def test_device_authorization_functionality():
    """Test device authorization middleware functionality"""
    
    print("🧪 DEVICE AUTHORIZATION FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Create a mock request factory
    factory = RequestFactory()
    
    # Load middleware with dummy get_response
    def dummy_get_response(request):
        return None
        
    try:
        middleware = DeviceAuthorizationMiddleware(dummy_get_response)
        print("✅ Middleware instantiation: SUCCESS")
    except Exception as e:
        print(f"❌ Middleware instantiation: FAILED - {e}")
        return False
    
    # Test 1: Basic configuration loading
    print("\\n🔍 TEST 1: Configuration Loading")
    config = middleware.authorized_devices
    
    print(f"  Security Mode: {config.get('security_mode')}")
    print(f"  Allow All: {config.get('allow_all')}")
    print(f"  Devices Loaded: {len(config.get('devices', []))}")
    
    # Test 2: Device fingerprinting
    print("\\n🔍 TEST 2: Device Fingerprinting")
    
    # Create mock request
    request = factory.get('/transactions/create/')
    request.META.update({
        'HTTP_USER_AGENT': 'Mozilla/5.0 Test Browser',
        'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.9',
        'HTTP_ACCEPT_ENCODING': 'gzip, deflate',
        'REMOTE_ADDR': '192.168.0.82'  # Developer PC IP
    })
    
    fingerprint = middleware.get_device_fingerprint(request)
    print(f"  Generated Fingerprint: {fingerprint[:16]}...")
    print(f"  Client IP: {middleware.get_client_ip(request)}")
    
    # Test 3: Path restriction detection
    print("\\n🔍 TEST 3: Path Restriction Detection")
    
    test_paths = [
        '/transactions/create/',      # Should be restricted
        '/transactions/api/',         # Should be restricted
        '/admin/',                   # Should be high security
        '/inventory/view/',          # Should be unrestricted
        '/users/profile/'            # Should be unrestricted
    ]
    
    for path in test_paths:
        restriction_level = middleware.is_restricted_path(path)
        status = "🚫" if restriction_level else "✅"
        level_text = restriction_level if restriction_level else "UNRESTRICTED"
        print(f"  {status} {path} -> {level_text}")
    
    # Test 4: Device authorization (simulate registered device)
    print("\\n🔍 TEST 4: Device Authorization")
    
    # Test with Developer PC IP (should be authorized)
    dev_pc_ip = "192.168.0.82"
    request.META['REMOTE_ADDR'] = dev_pc_ip
    
    # Create a mock user
    request.user = type('MockUser', (), {
        'username': 'admin',
        'is_authenticated': True,
        'groups': type('MockGroups', (), {'all': lambda: []})()
    })
    
    is_authorized = middleware.is_device_authorized(
        fingerprint, dev_pc_ip, '/transactions/create/', request.user
    )
    
    result = "✅ AUTHORIZED" if is_authorized else "❌ DENIED"
    print(f"  Developer PC (192.168.0.82): {result}")
    
    # Test with unknown device
    unknown_ip = "192.168.0.999"
    request.META['REMOTE_ADDR'] = unknown_ip
    unknown_fingerprint = middleware.get_device_fingerprint(request)
    
    is_authorized_unknown = middleware.is_device_authorized(
        unknown_fingerprint, unknown_ip, '/transactions/create/', request.user
    )
    
    result_unknown = "✅ AUTHORIZED" if is_authorized_unknown else "❌ DENIED"
    print(f"  Unknown Device (192.168.0.999): {result_unknown}")
    
    # Test 5: Middleware request processing
    print("\\n🔍 TEST 5: Request Processing")
    
    # Test authorized request
    auth_request = factory.get('/transactions/create/')
    auth_request.META.update({
        'HTTP_USER_AGENT': 'Mozilla/5.0 Test Browser',
        'REMOTE_ADDR': '192.168.0.82'
    })
    auth_request.user = request.user
    
    try:
        response = middleware.process_request(auth_request)
        if response is None:
            print("  ✅ Authorized request: ALLOWED")
        else:
            print(f"  ❌ Authorized request: BLOCKED ({response.status_code})")
    except Exception as e:
        print(f"  ⚠️ Authorized request: ERROR - {e}")
    
    # Test unauthorized request
    unauth_request = factory.get('/transactions/create/')
    unauth_request.META.update({
        'HTTP_USER_AGENT': 'Unauthorized Browser',
        'REMOTE_ADDR': '10.0.0.1'  # Different IP
    })
    unauth_request.user = request.user
    
    try:
        response = middleware.process_request(unauth_request)
        if response is None:
            print("  ⚠️ Unauthorized request: ALLOWED (unexpected)")
        else:
            print(f"  ✅ Unauthorized request: BLOCKED ({response.status_code})")
    except Exception as e:
        print(f"  ⚠️ Unauthorized request: ERROR - {e}")
    
    # Test 6: Production readiness summary
    print("\\n🔍 TEST 6: Production Readiness Summary")
    
    readiness_checks = []
    
    # Check critical settings
    if config.get('allow_all') is False:
        readiness_checks.append("✅ Device restrictions enforced")
    else:
        readiness_checks.append("❌ Device restrictions NOT enforced")
    
    if config.get('security_mode') == 'PRODUCTION':
        readiness_checks.append("✅ Production security mode active")
    else:
        readiness_checks.append("❌ Non-production security mode")
    
    if len(config.get('devices', [])) >= 2:
        readiness_checks.append("✅ Multiple devices configured")
    else:
        readiness_checks.append("⚠️ Limited device configuration")
        
    armory_pc = next((d for d in config.get('devices', []) if 'Armory' in d.get('name', '')), None)
    if armory_pc and armory_pc.get('can_transact'):
        readiness_checks.append("✅ Armory PC transaction-enabled")
    else:
        readiness_checks.append("❌ Armory PC transaction-disabled")
    
    for check in readiness_checks:
        print(f"  {check}")
    
    # Final assessment
    print("\\n" + "=" * 60)
    
    all_tests_passed = all([
        is_authorized,  # Dev PC should be authorized
        not is_authorized_unknown,  # Unknown device should be denied
        config.get('allow_all') is False,  # Security enforced
        config.get('security_mode') == 'PRODUCTION'  # Production mode
    ])
    
    if all_tests_passed:
        print("🟢 ALL TESTS PASSED - PRODUCTION READY")
        print("✅ Device authorization system is fully operational")
    else:
        print("🟡 SOME TESTS FAILED - NEEDS ATTENTION")
        print("⚠️ Review configuration and test results")
    
    return all_tests_passed

if __name__ == '__main__':
    test_device_authorization_functionality()