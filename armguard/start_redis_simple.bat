@echo off
echo ========================================
echo ArmGuard Redis Server Quick Setup
echo ========================================
echo.
echo This script will check for Redis server options.
echo.

:: Option 1: Check for Docker
echo [1] Checking for Docker...
docker version >nul 2>&1
if errorlevel 1 (
    echo    ❌ Docker not found
) else (
    echo    ✅ Docker found - starting Redis container...
    docker stop armguard-redis >nul 2>&1
    docker rm armguard-redis >nul 2>&1
    docker run -d --name armguard-redis -p 6379:6379 redis:alpine
    if errorlevel 0 (
        echo    ✅ Redis started successfully!
        echo    Run: python manage.py runserver
        pause
        exit /b 0
    )
)

echo.
echo [2] Checking for WSL (Windows Subsystem for Linux)...
wsl --version >nul 2>&1
if errorlevel 1 (
    echo    ❌ WSL not found
) else (
    echo    ✅ WSL found - attempting Redis installation...
    echo    Installing Redis in WSL...
    wsl sudo apt update
    wsl sudo apt install -y redis-server
    echo    Starting Redis server...
    wsl sudo service redis-server start
    if errorlevel 0 (
        echo    ✅ Redis started in WSL!
        echo    Run: python manage.py runserver  
        pause
        exit /b 0
    )
)

echo.
echo ========================================
echo Manual Installation Options:
echo ========================================
echo.
echo Since Docker and WSL are not available, here are your options:
echo.
echo Option A - Download Redis for Windows:
echo 1. Go to: https://github.com/microsoftarchive/redis/releases
echo 2. Download: Redis-x64-3.0.504.msi
echo 3. Install and run Redis server
echo.
echo Option B - Install Docker Desktop:  
echo 1. Download: https://www.docker.com/products/docker-desktop
echo 2. Install Docker Desktop
echo 3. Run this script again
echo.
echo Option C - Enable WSL:
echo 1. Open PowerShell as Administrator
echo 2. Run: wsl --install
echo 3. Restart computer
echo 4. Run this script again
echo.
echo Option D - Continue without Redis:
echo Your WebSockets will work with InMemory fallback
echo (Limited performance but functional)
echo.
echo ========================================
pause