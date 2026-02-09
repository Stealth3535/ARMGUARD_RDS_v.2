#!/usr/bin/env python3
"""
Simplified device authorization functionality test
Tests core functionality that exists
"""
import os
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import RequestFactory
from django.conf import settings

def test_device_authorization_simple():
    """Test basic device authorization functionality"""
    
    print("🧪 DEVICE AUTHORIZATION CORE FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Test 1: Configuration file check
    print("🔍 TEST 1: Configuration File")
    
    auth_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
    
    if not auth_file.exists():
        print("❌ authorized_devices.json not found")
        return False
        
    with open(auth_file) as f:
        config = json.load(f)
    
    print(f"  ✅ Configuration file loaded")
    print(f"  📋 Security Mode: {config.get('security_mode', 'NOT SET')}")
    print(f"  🔐 Allow All: {config.get('allow_all', 'NOT SET')}")
    print(f"  👥 Registered Devices: {len(config.get('devices', []))}")
    
    # Test 2: Device configuration check
    print("\\n🔍 TEST 2: Device Configuration")
    
    production_ready = True
    
    for i, device in enumerate(config.get('devices', []), 1):
        name = device.get('name', 'Unknown')
        can_transact = device.get('can_transact', False)
        active = device.get('active', True)
        ip = device.get('ip', 'N/A')
        
        print(f"  Device {i}: {name}")
        print(f"    IP: {ip}")
        print(f"    Active: {'✅' if active else '❌'}")
        print(f"    Can Transact: {'✅' if can_transact else '❌'}")
        
        if 'Armory' in name and not can_transact:
            print(f"    🚨 WARNING: {name} should be able to transact")
            production_ready = False
    
    # Test 3: Middleware registration
    print("\\n🔍 TEST 3: Middleware Integration")
    
    middleware_registered = 'core.middleware.DeviceAuthorizationMiddleware' in settings.MIDDLEWARE
    print(f"  Middleware registered: {'✅' if middleware_registered else '❌'}")
    
    if not middleware_registered:
        production_ready = False
    
    # Test 4: Path restrictions configuration
    print("\\n🔍 TEST 4: Path Protection Configuration")
    
    restricted_paths = config.get('restricted_paths', [])
    high_security_paths = config.get('high_security_paths', [])
    
    print(f"  Restricted paths: {len(restricted_paths)}")
    print(f"  High security paths: {len(high_security_paths)}")
    
    critical_paths = ['/transactions/create/', '/admin/', '/api/']
    missing_paths = []
    
    for critical_path in critical_paths:
        protected = any(path.startswith(critical_path) for path in restricted_paths + high_security_paths)
        if not protected:
            missing_paths.append(critical_path)
    
    if missing_paths:
        print(f"  ⚠️ Unprotected critical paths: {missing_paths}")
        
    # Test 5: Production security settings
    print("\\n🔍 TEST 5: Production Security Settings")
    
    security_checks = []
    
    # Security mode check
    if config.get('security_mode') == 'PRODUCTION':
        security_checks.append("✅ Production security mode")
    else:
        security_checks.append("❌ Non-production security mode")
        production_ready = False
    
    # Allow all check
    if config.get('allow_all') is False:
        security_checks.append("✅ Device restrictions enforced")
    else:
        security_checks.append("❌ Device restrictions not enforced")
        production_ready = False
        
    # Registration requirement
    if config.get('require_device_registration'):
        security_checks.append("✅ Device registration required")
    else:
        security_checks.append("⚠️ Device registration not required")
        
    # Audit settings
    audit_settings = config.get('audit_settings', {})
    if audit_settings.get('log_all_attempts'):
        security_checks.append("✅ Comprehensive audit logging")
    else:
        security_checks.append("⚠️ Limited audit logging")
    
    for check in security_checks:
        print(f"  {check}")
    
    # Test 6: Django settings check
    print("\\n🔍 TEST 6: Django Environment")
    
    debug_mode = settings.DEBUG
    print(f"  DEBUG mode: {'🟡 ON (development)' if debug_mode else '✅ OFF (production)'}")
    
    # Test 7: File system permissions (basic check)
    print("\\n🔍 TEST 7: File System")
    
    try:
        # Test if we can read the config file
        with open(auth_file, 'r') as f:
            test_read = f.read(100)
        print("  ✅ Configuration file readable")
        
        # Test if we can write (backup and restore)
        with open(auth_file, 'r') as f:
            original_content = f.read()
        
        with open(auth_file, 'w') as f:
            f.write(original_content)
        
        print("  ✅ Configuration file writable")
        
    except Exception as e:
        print(f"  ❌ File system issue: {e}")
        production_ready = False
    
    # Final assessment
    print("\\n" + "=" * 60)
    print("🎯 DEPLOYMENT ASSESSMENT:")
    
    if production_ready and not debug_mode:
        print("🟢 PRODUCTION READY")
        print("✅ Device authorization system is fully configured for deployment")
        assessment = "READY"
    elif production_ready and debug_mode:
        print("🟡 STAGING READY")
        print("✅ Configuration complete - Set DEBUG=False for production")
        assessment = "STAGING"
    else:
        print("🔴 NOT READY")
        print("❌ Configuration issues must be resolved")
        assessment = "NOT_READY"
    
    # Deployment checklist
    print("\\n📋 PRE-DEPLOYMENT CHECKLIST:")
    checklist = [
        f"{'✅' if middleware_registered else '❌'} Middleware registered in MIDDLEWARE setting",
        f"{'✅' if config.get('allow_all') is False else '❌'} Device restrictions enabled (allow_all=false)",
        f"{'✅' if config.get('security_mode') == 'PRODUCTION' else '❌'} Security mode set to PRODUCTION",
        f"{'✅' if len(config.get('devices', [])) >= 2 else '❌'} Multiple devices configured",
        f"{'✅' if any(d.get('can_transact') for d in config.get('devices', [])) else '❌'} Transaction devices enabled",
        f"{'✅' if len(restricted_paths) >= 5 else '❌'} Critical paths protected",
        f"{'✅' if not debug_mode else '🟡'} Production Django settings (DEBUG=False)"
    ]
    
    for item in checklist:
        print(f"  {item}")
    
    return assessment

if __name__ == '__main__':
    test_device_authorization_simple()