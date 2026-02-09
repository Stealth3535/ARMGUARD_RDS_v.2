#!/usr/bin/env python3
"""
Test device authorization behavior in different modes
"""
import os
import django
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from core.middleware.device_authorization import DeviceAuthorizationMiddleware
from django.http import HttpRequest
from django.contrib.auth import get_user_model

User = get_user_model()

def test_device_authorization():
    """Test device authorization with different configurations"""
    
    print("🧪 DEVICE AUTHORIZATION BEHAVIOR TEST")
    print("=" * 50)
    
    # Load current config
    auth_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
    with open(auth_file) as f:
        config = json.load(f)
    
    # Test 1: Check what happens when allow_all is not set
    print("\n🔍 TEST 1: Current Configuration Behavior")
    
    # Since middleware constructor requires get_response, let's check the config directly
    print(f"Config has 'allow_all' key: {'allow_all' in config}")
    
    # Test 2: Show what would happen in production
    print("\n🔍 TEST 2: Production Mode Simulation")
    
    # Create production-like config
    prod_config = config.copy()
    prod_config['allow_all'] = False
    prod_config['restricted_paths'] = [
        "/transactions/create/",
        "/transactions/api/",
        "/inventory/api/",
        "/admin/transactions/",
        "/admin/inventory/"
    ]
    
    print("Production config would be:")
    print(f"  Allow all: {prod_config.get('allow_all')}")
    print(f"  Registered devices: {len(prod_config.get('devices', []))}")
    print(f"  Restricted paths: {len(prod_config.get('restricted_paths', []))}")
    
    # Test 3: Show which paths would be protected
    print("\n🔍 TEST 3: Protected Paths Analysis")
    
    if 'restricted_paths' not in config:
        # Show default paths from middleware code
        default_paths = [
            "/transactions/create/",
            "/transactions/api/",
            "/inventory/api/", 
            "/admin/transactions/",
            "/admin/inventory/"
        ]
        print("Default protected paths (from middleware):")
        for path in default_paths:
            print(f"  🚫 {path}")
    else:
        print("Current protected paths:")
        for path in config.get('restricted_paths', []):
            print(f"  🚫 {path}")
    
    # Test 4: Device authorization status
    print("\n🔍 TEST 4: Device Authorization Status")
    
    for i, device in enumerate(config.get('devices', []), 1):
        name = device.get('name', 'Unknown')
        can_transact = device.get('can_transact', False)
        ip = device.get('ip', 'N/A')
        
        print(f"  Device {i}: {name}")
        print(f"    🌐 IP: {ip}")
        print(f"    💳 Can perform transactions: {'✅' if can_transact else '❌'}")
        
        if name == "Armory PC" and not can_transact:
            print("    ⚠️  DEPLOYMENT ISSUE: Armory PC should have can_transact=true")
    
    print("\n" + "=" * 50)
    print("🚀 DEPLOYMENT READINESS ASSESSMENT:")
    
    issues = []
    
    # Check for production readiness
    if 'allow_all' not in config:
        issues.append("❌ 'allow_all' flag not set - middleware will default to True (development mode)")
    elif config.get('allow_all') == True:
        issues.append("⚠️  'allow_all' is True - should be False for production")
    
    if 'restricted_paths' not in config or len(config.get('restricted_paths', [])) == 0:
        issues.append("⚠️  No restricted paths configured - middleware will use defaults")
    
    armory_pc = next((d for d in config.get('devices', []) if 'Armory' in d.get('name', '')), None)
    if armory_pc and not armory_pc.get('can_transact', False):
        issues.append("⚠️  Armory PC cannot perform transactions")
    
    if not issues:
        print("🟢 PRODUCTION READY - All configurations correct")
    else:
        print("🟡 NEEDS CONFIGURATION - Issues found:")
        for issue in issues:
            print(f"  {issue}")
    
    return len(issues) == 0

if __name__ == '__main__':
    test_device_authorization()