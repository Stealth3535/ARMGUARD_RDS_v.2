#!/bin/bash
# ArmGuard Docker Entrypoint Script
# Handles database migrations, static files, and application startup

set -e

echo "=============================================="
echo "ArmGuard Application Container Starting..."
echo "=============================================="

# Wait for database
echo "[1/5] Waiting for PostgreSQL database..."
while ! nc -z ${DB_HOST:-armguard-db} ${DB_PORT:-5432}; do
    echo "  PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "  ✓ PostgreSQL is available"

# Wait for Redis
echo "[2/5] Waiting for Redis..."
while ! nc -z ${REDIS_HOST:-armguard-redis} 6379; do
    echo "  Redis is unavailable - sleeping"
    sleep 2
done
echo "  ✓ Redis is available"

# Run database migrations
echo "[3/5] Running database migrations..."
python manage.py migrate --noinput
echo "  ✓ Migrations complete"

# Collect static files
echo "[4/5] Collecting static files..."
python manage.py collectstatic --noinput --clear
echo "  ✓ Static files collected"

# Create superuser if not exists (for testing)
echo "[5/5] Setting up test admin user..."
python manage.py shell << EOF
from django.contrib.auth.models import User, Group
from django.db import IntegrityError

# Create groups if they don't exist
for group_name in ['Admin', 'Armorer']:
    Group.objects.get_or_create(name=group_name)
    print(f"  ✓ Group '{group_name}' ready")

# Create test admin user
try:
    if not User.objects.filter(username='testadmin').exists():
        admin = User.objects.create_superuser(
            username='testadmin',
            email='testadmin@armguard.local',
            password='TestAdmin123!'
        )
        admin.groups.add(Group.objects.get(name='Admin'))
        print("  ✓ Test admin user created")
    else:
        print("  ✓ Test admin user exists")
except IntegrityError:
    print("  ✓ Test admin user exists")

# Create test armorer user
try:
    if not User.objects.filter(username='testarmorer').exists():
        armorer = User.objects.create_user(
            username='testarmorer',
            email='testarmorer@armguard.local',
            password='TestArmorer123!',
            is_staff=True
        )
        armorer.groups.add(Group.objects.get(name='Armorer'))
        print("  ✓ Test armorer user created")
    else:
        print("  ✓ Test armorer user exists")
except IntegrityError:
    print("  ✓ Test armorer user exists")
EOF

echo ""
echo "=============================================="
echo "Application initialization complete!"
echo "=============================================="
echo ""

# Execute the main command
exec "$@"
