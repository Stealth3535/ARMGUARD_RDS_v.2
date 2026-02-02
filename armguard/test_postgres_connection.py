#!/usr/bin/env python
"""
PostgreSQL Connection Test for ArmGuard
Tests database connection and basic operations
"""
import os
import sys
import django
from pathlib import Path

# Add the project directory to the Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def test_postgres_connection():
    """Test PostgreSQL database connection"""
    print("🔍 Testing PostgreSQL Connection...")
    print("-" * 50)
    
    try:
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            print(f"✅ PostgreSQL Connection: SUCCESS")
            print(f"📊 Database Version: {version}")
            
            # Test basic operations
            cursor.execute("SELECT current_database(), current_user;")
            db_info = cursor.fetchone()
            print(f"📁 Database Name: {db_info[0]}")
            print(f"👤 Database User: {db_info[1]}")
            
            # Check if tables exist (after migrations)
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
            """)
            table_count = cursor.fetchone()[0]
            print(f"📋 Tables in Database: {table_count}")
            
        print("-" * 50)
        print("🎉 PostgreSQL is ready for ArmGuard!")
        return True
        
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        print("-" * 50)
        print("💡 Make sure PostgreSQL is installed and running:")
        print("   1. Install PostgreSQL")
        print("   2. Create database: CREATE DATABASE armguard;")
        print("   3. Create user: CREATE USER armguard_user WITH PASSWORD 'your_password';")
        print("   4. Grant privileges: GRANT ALL PRIVILEGES ON DATABASE armguard TO armguard_user;")
        print("   5. Update your .env file with correct DB_PASSWORD")
        return False

if __name__ == "__main__":
    success = test_postgres_connection()
    if success:
        print("\n🚀 Ready to run migrations:")
        print("   python manage.py makemigrations")
        print("   python manage.py migrate")
        sys.exit(0)
    else:
        sys.exit(1)