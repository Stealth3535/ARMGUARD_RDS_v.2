#!/bin/bash
# Quick fix script for Django environment setup on RPi

echo "🔧 Setting up Django environment variables for ArmGuard A+..."

cd /opt/armguard/armguard
source venv/bin/activate

# Generate Django SECRET_KEY
echo "📝 Generating Django SECRET_KEY..."
SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")

# Create .env file with A+ performance settings
echo "📄 Creating .env file with A+ settings..."
cat > .env << EOF
# Django Core Settings
DJANGO_SECRET_KEY=${SECRET_KEY}
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*

# Database Settings (PostgreSQL with fallback to SQLite)
DATABASE_URL=postgresql://armguard_user:armguard_secure_2024@localhost:5432/armguard_db
SQLITE_FALLBACK=True

# A+ Performance Cache Settings
CACHE_BACKEND=redis
REDIS_URL=redis://127.0.0.1:6379/0
CACHE_TIMEOUT=3600

# Security Settings
SECURE_SSL_REDIRECT=False
SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False

# Static Files
STATIC_ROOT=/opt/armguard/armguard/staticfiles
MEDIA_ROOT=/opt/armguard/armguard/media

# RPi Optimizations
RPi_DEPLOYMENT=True
ARM64_OPTIMIZATIONS=True
EOF

chmod 600 .env

echo "✅ Django environment configured with A+ settings"
echo "🔍 Verifying .env file created:"
ls -la .env
echo "🔐 Environment variables configured:"
head -5 .env

echo ""
echo "🚀 Now you can continue with database setup:"
echo "   cd /opt/armguard/armguard"
echo "   source venv/bin/activate" 
echo "   python manage.py makemigrations"
echo "   python manage.py migrate"
echo "   python manage.py collectstatic --noinput"