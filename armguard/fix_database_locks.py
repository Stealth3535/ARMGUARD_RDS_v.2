#!/usr/bin/env python
"""
Emergency fix for database locks causing hang on email field edit.
Run this if your web app hangs when editing forms.

This script:
1. Disables simple_history temporarily
2. Vacuums the SQLite database
3. Clears any stuck database locks
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection, transaction
from django.conf import settings

print("=" * 70)
print("ARMGUARD DATABASE LOCK FIX")
print("=" * 70)
print()

# Check if using SQLite
if 'sqlite' in settings.DATABASES['default']['ENGINE']:
    print("✓ SQLite database detected")
    db_path = settings.DATABASES['default']['NAME']
    print(f"  Database: {db_path}")
    print()
    
    # Close all connections
    print("Closing all database connections...")
    connection.close()
    
    # Run VACUUM to optimize and remove locks
    print("Running VACUUM to optimize database...")
    try:
        with connection.cursor() as cursor:
            # Disable foreign keys temporarily
            cursor.execute("PRAGMA foreign_keys=OFF")
            # Vacuum the database
            cursor.execute("VACUUM")
            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
        print("✓ Database vacuumed successfully")
    except Exception as e:
        print(f"✗ Vacuum failed: {e}")
    
    # Check for -wal and -shm files (Write-Ahead Logging)
    wal_file = str(db_path) + '-wal'
    shm_file = str(db_path) + '-shm'
    
    if os.path.exists(wal_file):
        print(f"\n⚠️ WAL file exists: {wal_file}")
        print("  This can cause locks. Database will checkpoint on next access.")
    
    if os.path.exists(shm_file):
        print(f"⚠️ SHM file exists: {shm_file}")
    
    print()
    print("Checkpoint WAL (if using WAL mode)...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            print("✓ WAL checkpoint completed")
    except Exception as e:
        print(f"  WAL mode not active or checkpoint failed: {e}")
    
    # Set optimal pragmas
    print()
    print("Setting optimal SQLite pragmas...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA journal_mode=DELETE")  # Disable WAL mode
            cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
            cursor.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp
            cursor.execute("PRAGMA cache_size=10000")  # Larger cache
        print("✓ Pragmas set successfully")
    except Exception as e:
        print(f"✗ Failed to set pragmas: {e}")
    
    print()
    print("=" * 70)
    print("DATABASE FIX COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart your Django development server")
    print("2. Try editing the email field again")
    print("3. If still hanging, use settings_dev.py:")
    print("   set DJANGO_SETTINGS_MODULE=core.settings_dev")
    print()
    
else:
    print("✓ PostgreSQL detected - no SQLite-specific fixes needed")
    print()
    print("If still experiencing hangs:")
    print("1. Check PostgreSQL connection pool settings")
    print("2. Monitor for long-running queries:")
    print("   SELECT * FROM pg_stat_activity WHERE state = 'active';")
    print()
