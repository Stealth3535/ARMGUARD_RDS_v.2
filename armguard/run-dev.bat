@echo off
REM Quick development server launcher with minimal middleware

echo ========================================
echo ARMGUARD Development Server (Windows)
echo Minimal middleware for fast development
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
)

REM Use development settings
set DJANGO_SETTINGS_MODULE=core.settings_dev

echo Starting Django development server...
echo Access at: http://localhost:8000
echo Press Ctrl+C to stop
echo.

python manage.py runserver 0.0.0.0:8000

pause
