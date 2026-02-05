#!/usr/bin/env python
"""
PostgreSQL Connection Test for ArmGuard - DISABLED FOR SECURITY
This file contains raw SQL queries and should not be used in production.
Use Django management commands instead: python manage.py dbshell
"""

# SECURITY WARNING: This file has been disabled to prevent SQL injection risks.
# Raw cursor.execute() calls can be dangerous if user input reaches them.
# Use Django ORM or management commands for database operations.

print("❌ This test script has been disabled for security reasons.")
print("💡 Use 'python manage.py dbshell' to test database connectivity.")
print("💡 Use 'python manage.py check --database default' to verify database setup.")
sys.exit(1)

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