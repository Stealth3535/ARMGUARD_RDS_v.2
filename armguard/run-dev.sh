#!/bin/bash
# Quick development server launcher with minimal middleware

echo "========================================"
echo "ARMGUARD Development Server (Linux)"
echo "Minimal middleware for fast development"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Warning: Virtual environment not found"
fi

# Use development settings
export DJANGO_SETTINGS_MODULE=core.settings_dev

echo "Starting Django development server..."
echo "Access at: http://localhost:8000"
echo "Press Ctrl+C to stop"
echo ""

python manage.py runserver 0.0.0.0:8000
