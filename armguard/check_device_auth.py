#!/usr/bin/env python3
"""
Quick check of device authorization middleware status
"""
import os
import django
import sys
import json
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from core.middleware.device_authorization import DeviceAuthorizationMiddleware

def check_device_authorization_status():
    """Check if device authorization is properly integrated"""
    
    print("🛡️  DEVICE AUTHORIZATION SYSTEM STATUS CHECK")
    print("=" * 50)
    
    # Check if middleware is registered
    middleware_active = 'core.middleware.DeviceAuthorizationMiddleware' in settings.MIDDLEWARE
    print(f"✅ Middleware registered in settings: {middleware_active}")
    
    # Check current mode
    print(f"🔧 Current DEBUG mode: {settings.DEBUG}")
    
    # Check authorized devices file
    auth_file = Path(settings.BASE_DIR) / 'authorized_devices.json'
    file_exists = auth_file.exists()
    print(f"📄 Authorized devices file exists: {file_exists}")
    
    if file_exists:
        with open(auth_file) as f:
            config = json.load(f)
        
        devices_count = len(config.get('devices', []))
        allow_all = config.get('allow_all', 'NOT SET')
        restricted_paths_count = len(config.get('restricted_paths', []))
        
        print(f"👥 Registered devices: {devices_count}")
        print(f"🔓 Allow all mode: {allow_all}")
        print(f"🚫 Restricted paths: {restricted_paths_count}")
        
        # Show device details
        print("\n📋 DEVICE INVENTORY:")
        for i, device in enumerate(config.get('devices', []), 1):
            print(f"  {i}. {device.get('name', 'Unknown')}")
            print(f"     IP: {device.get('ip', 'N/A')}")
            print(f"     Can transact: {device.get('can_transact', False)}")
            print(f"     Description: {device.get('description', 'N/A')}")
    else:
        print("⚠️  Authorized devices file not found")
    
    # Test middleware instantiation
    try:
        middleware = DeviceAuthorizationMiddleware(None)
        print("✅ Middleware instantiation: SUCCESS")
        
        # Check loaded config
        has_devices = hasattr(middleware, 'authorized_devices')
        print(f"✅ Config loaded: {has_devices}")
        
        if has_devices:
            allow_all_setting = middleware.authorized_devices.get('allow_all', False)
            print(f"🔧 Middleware allow_all mode: {allow_all_setting}")
            
    except Exception as e:
        print(f"❌ Middleware instantiation: FAILED - {e}")
    
    print("\n" + "=" * 50)
    print("DEPLOYMENT STATUS:")
    
    if middleware_active and file_exists:
        print("🟢 FULLY INTEGRATED - Device authorization is active")
    elif middleware_active and not file_exists:
        print("🟡 PARTIALLY INTEGRATED - Middleware active but no device file")
    else:
        print("🔴 NOT INTEGRATED - Middleware not registered")
    
    return middleware_active, file_exists

if __name__ == '__main__':
    check_device_authorization_status()