"""
Migration: authorized_device_system
=====================================
Auto-generated skeleton. Run:
    python manage.py makemigrations core
    python manage.py migrate

This script also provides a DATA MIGRATION helper that reads
authorized_devices.json and seeds the new AuthorizedDevice table.

Usage:
    python manage.py shell < armguard/core/device/migration_seed.py
"""

from django.utils import timezone
import json
import uuid
import os
from pathlib import Path


def seed_from_json(dry_run: bool = False):
    """
    Read the legacy authorized_devices.json and create AuthorizedDevice rows.

    Run inside a Django shell: exec(open('core/device/migration_seed.py').read()); seed_from_json()
    """
    # Import here so this file is safe to import outside of Django context
    from django.contrib.auth.models import User
    from core.device.models import AuthorizedDevice, DeviceAuditEvent

    json_path = Path(__file__).resolve().parent.parent.parent / 'authorized_devices.json'
    if not json_path.exists():
        print(f'[SKIP] {json_path} not found')
        return

    with open(json_path) as f:
        data = json.load(f)

    devices = data.get('devices', [])
    print(f'[INFO] Found {len(devices)} device(s) in authorized_devices.json')

    # Use "system" superuser as the approval actor, or first superuser found
    try:
        actor = User.objects.filter(is_superuser=True).order_by('id').first()
    except Exception:
        actor = None

    created = 0
    skipped = 0

    for entry in devices:
        fingerprint = entry.get('fingerprint', '')
        name        = entry.get('name', 'Migrated Device')
        ip          = entry.get('ip') or entry.get('address')
        active      = entry.get('active', True)
        sec_level   = entry.get('security_level', 'HIGH_SECURITY')
        created_raw = entry.get('created_at')
        can_transact       = entry.get('can_transact', False)
        max_daily          = entry.get('max_daily_transactions', 50)
        active_hours_raw   = entry.get('active_hours')

        # Map old security_level → new SecurityTier
        tier_map = {
            'DEVELOPMENT':   AuthorizedDevice.SecurityTier.STANDARD,
            'STANDARD':      AuthorizedDevice.SecurityTier.STANDARD,
            'HIGH':          AuthorizedDevice.SecurityTier.HIGH_SECURITY,
            'HIGH_SECURITY': AuthorizedDevice.SecurityTier.HIGH_SECURITY,
            'MILITARY':      AuthorizedDevice.SecurityTier.MILITARY,
        }
        tier = tier_map.get(sec_level.upper(), AuthorizedDevice.SecurityTier.HIGH_SECURITY)

        # Parse active hours
        hours_start = hours_end = None
        if active_hours_raw:
            if isinstance(active_hours_raw, dict):
                from datetime import time as dtime
                try:
                    hours_start = dtime.fromisoformat(active_hours_raw.get('start', '') + ':00' if len(active_hours_raw.get('start','')) == 5 else active_hours_raw.get('start',''))
                    hours_end   = dtime.fromisoformat(active_hours_raw.get('end', '') + ':00' if len(active_hours_raw.get('end','')) == 5 else active_hours_raw.get('end',''))
                except ValueError:
                    pass
            elif isinstance(active_hours_raw, str) and '-' in active_hours_raw:
                from datetime import time as dtime
                parts = active_hours_raw.split('-')
                try:
                    s = parts[0].strip()
                    e = parts[1].strip()
                    hours_start = dtime.fromisoformat(s + ':00' if len(s) == 5 else s)
                    hours_end   = dtime.fromisoformat(e + ':00' if len(e) == 5 else e)
                except ValueError:
                    pass

        if dry_run:
            print(f'  [DRY RUN] Would create: {name} | tier={tier} | ip={ip} | active={active}')
            skipped += 1
            continue

        # Generate a new stable device_token for each migrated entry.
        # Derive deterministically from the legacy fingerprint so the seed
        # is idempotent (re-running it won't create duplicates).
        if fingerprint and len(fingerprint) == 64:
            stable_token = fingerprint
        elif fingerprint:
            import hashlib
            stable_token = hashlib.sha256(fingerprint.encode()).hexdigest()  # 64 hex chars
        else:
            import secrets as _sec
            stable_token = _sec.token_hex(32)

        device, was_created = AuthorizedDevice.objects.get_or_create(
            device_token=stable_token,
            defaults={
                'user': actor,
                'device_name': name,
                'ip_first_seen': ip,
                'ip_last_seen': ip,
                'ip_binding': ip if entry.get('ip_binding_strict', False) else None,
                'status': AuthorizedDevice.Status.ACTIVE if active else AuthorizedDevice.Status.REVOKED,
                'security_tier': tier,
                'can_transact': can_transact,
                'max_daily_transactions': max_daily,
                'active_hours_start': hours_start,
                'active_hours_end': hours_end,
                'authorized_at': timezone.now(),
                'enrollment_reason': f'Migrated from authorized_devices.json. Legacy fingerprint: {fingerprint[:16]}...',
                'reviewed_by': actor,
                'reviewed_at': timezone.now(),
                'review_notes': 'Automatically migrated from v1 JSON store',
            }
        )

        if was_created:
            DeviceAuditEvent.log(
                device, 'ACTIVATED', actor,
                notes='Migrated from authorized_devices.json'
            )
            created += 1
            print(f'  [CREATED] {name} (status={device.status})')
        else:
            skipped += 1
            print(f'  [EXISTS]  {name} — skipped')

    print(f'\n[DONE] Created: {created}, Skipped: {skipped}')
    if not dry_run:
        print('[NOTE] Review created devices at /admin/ before disabling the old JSON middleware.')


if __name__ == '__main__':
    # Allow running as: python core/device/migration_seed.py --dry-run
    import sys
    dry = '--dry-run' in sys.argv
    seed_from_json(dry_run=dry)
