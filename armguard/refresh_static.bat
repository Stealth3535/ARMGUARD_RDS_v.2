@echo off
REM ArmGuard Static Files Refresh Script
REM Run this after making CSS or template changes

echo ========================================
echo ArmGuard Static Files Refresh
echo ========================================
echo.

echo [1/3] Collecting static files...
python manage.py collectstatic --noinput --clear

echo.
echo [2/3] Clearing Django cache...
python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache cleared!')"

echo.
echo [3/3] Done!
echo.
echo ========================================
echo Next Steps:
echo 1. Restart your Django development server (Ctrl+C then run again)
echo 2. Clear your browser cache:
echo    - Chrome: Ctrl+Shift+Delete or Ctrl+F5 (hard refresh)
echo    - Firefox: Ctrl+Shift+Delete or Ctrl+F5
echo    - Edge: Ctrl+Shift+Delete or Ctrl+F5
echo 3. Reload the page
echo ========================================
pause
