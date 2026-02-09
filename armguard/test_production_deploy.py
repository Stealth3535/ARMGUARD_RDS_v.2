#!/usr/bin/env python3
"""
Production deployment test for device authorization system
"""
import os
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings

def test_production_deployment():
    """Test production deployment configuration"""
    
    print("🚀 PRODUCTION DEPLOYMENT TEST")
    print("=" * 50)
    
    # Check Django settings
    print("🔧 DJANGO CONFIGURATION:")
    print(f"  DEBUG: {settings.DEBUG}")
    print(f"  MIDDLEWARE registered: {'core.middleware.DeviceAuthorizationMiddleware' in settings.MIDDLEWARE}")
    
    # Load and check authorized devices configuration
    auth_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
    
    if not auth_file.exists():
        print("❌ ERROR: authorized_devices.json not found")
        return False
        
    with open(auth_file) as f:
        config = json.load(f)
    
    print("\\n📋 DEVICE AUTHORIZATION CONFIGURATION:")
    print(f"  Security Mode: {config.get('security_mode', 'NOT SET')}")
    print(f"  Allow All: {config.get('allow_all', 'NOT SET')}")
    print(f"  Require Registration: {config.get('require_device_registration', 'NOT SET')}")
    print(f"  Registered Devices: {len(config.get('devices', []))}")
    print(f"  Restricted Paths: {len(config.get('restricted_paths', []))}")
    print(f"  High Security Paths: {len(config.get('high_security_paths', []))}")
    
    # Check device configurations
    print("\\n👥 DEVICE INVENTORY:")
    
    production_ready = True
    
    for i, device in enumerate(config.get('devices', []), 1):
        name = device.get('name', 'Unknown')
        can_transact = device.get('can_transact', False)
        active = device.get('active', True)
        security_level = device.get('security_level', 'STANDARD')
        
        status = "✅" if (active and can_transact) else "⚠️"
        print(f"  {i}. {status} {name}")
        print(f"     Security: {security_level}")
        print(f"     Can transact: {'Yes' if can_transact else 'No'}")
        print(f"     Active: {'Yes' if active else 'No'}")
        
        # Check for production readiness issues
        if 'Armory' in name and not can_transact:
            print(f"     🚨 ISSUE: Armory device should have can_transact=true")
            production_ready = False
    
    # Security compliance check
    print("\\n🛡️ SECURITY COMPLIANCE:")
    
    compliance_checks = []
    
    # Check allow_all setting
    allow_all = config.get('allow_all')
    if allow_all is False:
        compliance_checks.append("✅ Device restrictions enabled (allow_all=false)")
    elif allow_all is True:
        compliance_checks.append("❌ Device restrictions disabled (allow_all=true)")
        production_ready = False
    else:
        compliance_checks.append("⚠️ Device access policy not explicitly set")
        production_ready = False
    
    # Check security mode  
    security_mode = config.get('security_mode')
    if security_mode == 'PRODUCTION':
        compliance_checks.append("✅ Production security mode active")
    elif security_mode == 'DEVELOPMENT':
        compliance_checks.append("⚠️ Development security mode active")
        if not settings.DEBUG:
            production_ready = False
    else:
        compliance_checks.append("❌ Security mode not set")
        production_ready = False
        
    # Check path protection
    restricted_paths = len(config.get('restricted_paths', []))
    high_security_paths = len(config.get('high_security_paths', []))
    
    if restricted_paths >= 5:
        compliance_checks.append(f"✅ {restricted_paths} restricted paths protected")
    else:
        compliance_checks.append(f"⚠️ Only {restricted_paths} restricted paths protected")
        
    if high_security_paths >= 3:
        compliance_checks.append(f"✅ {high_security_paths} high-security paths protected")
    else:
        compliance_checks.append(f"⚠️ Only {high_security_paths} high-security paths protected")
    
    # Check audit settings
    audit_settings = config.get('audit_settings', {})
    if audit_settings.get('log_all_attempts'):
        compliance_checks.append("✅ Comprehensive audit logging enabled")
    else:
        compliance_checks.append("⚠️ Audit logging not configured")
        
    for check in compliance_checks:
        print(f"  {check}")
    
    # Final assessment
    print("\\n" + "=" * 50)
    
    if production_ready and not settings.DEBUG:
        print("🟢 PRODUCTION READY")
        print("✅ System is properly configured for military deployment")
        return True
    elif production_ready and settings.DEBUG:
        print("🟡 CONFIGURATION READY (Development Mode)")
        print("⚠️ Set DEBUG=False for production deployment")
        return True
    else:
        print("🔴 NOT PRODUCTION READY")
        print("❌ Configuration issues must be resolved before deployment")
        return False

if __name__ == '__main__':
    test_production_deployment()