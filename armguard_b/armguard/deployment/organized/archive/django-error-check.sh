#!/bin/bash

echo "🔍 Django Error Diagnosis"
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📋 Running Django checks to see the actual error..."
echo ""

# Run Django check with verbose output
python manage.py check --verbosity=2

echo ""
echo "🧪 Testing database connection..."
python manage.py migrate --dry-run

echo ""
echo "📝 Testing Django settings import..."
python -c "
import os
import sys
sys.path.append('/opt/armguard')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

try:
    import django
    print('✅ Django import: OK')
    
    django.setup()
    print('✅ Django setup: OK')
    
    from django.conf import settings
    print('✅ Settings import: OK')
    
    print(f'   DEBUG: {settings.DEBUG}')
    print(f'   DATABASE ENGINE: {settings.DATABASES[\"default\"][\"ENGINE\"]}')
    print(f'   DATABASE NAME: {settings.DATABASES[\"default\"][\"NAME\"]}')
    
    # Test middleware imports
    print('')
    print('🔧 Testing middleware imports...')
    for middleware in settings.MIDDLEWARE:
        try:
            from django.utils.module_loading import import_string
            import_string(middleware)
            print(f'✅ {middleware}')
        except Exception as e:
            print(f'❌ {middleware}: {e}')
            
except Exception as e:
    print(f'❌ Django error: {e}')
    import traceback
    traceback.print_exc()
"

echo ""
echo "🚀 Attempting manual server startup with error details..."
echo "   (Press Ctrl+C after seeing startup messages or errors)"
echo ""

# Try to start the development server
python manage.py runserver 0.0.0.0:8000 --verbosity=2