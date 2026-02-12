#!/usr/bin/env python
"""
Clear device lockout from cache
Run this when a device is locked out and you need to reset it
"""
import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.cache import cache

# Device fingerprint to unlock
DEVICE_FINGERPRINT = "444be32e095db424f8b4ae5b1e5cf8bb"

# Clear lockout
lockout_key = f"device_lockout_{DEVICE_FINGERPRINT}"
attempts_key = f"device_attempts_{DEVICE_FINGERPRINT}"

cache.delete(lockout_key)
cache.delete(attempts_key)

print(f"✅ Device lockout cleared for: {DEVICE_FINGERPRINT[:16]}...")
print(f"   - Lockout key: {lockout_key}")
print(f"   - Attempts key: {attempts_key}")
print("\nYou can now access the admin dashboard.")
