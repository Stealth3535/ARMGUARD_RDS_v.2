@echo off
REM =============================================================================
REM 🎯 ARMGUARD ONE SYSTEMATIZED DEPLOYMENT - Windows Launcher
REM =============================================================================
REM Single deployment entry point for Windows environments
REM Version: 4.0.0
REM =============================================================================

echo.
echo ╔═════════════════════════════════════════════════════════════════════════════╗
echo ║                                                                             ║  
echo ║               🎯 ARMGUARD SYSTEMATIZED DEPLOYMENT                           ║
echo ║                                                                             ║
echo ║    One Command • Complete System • All Capabilities Integrated             ║
echo ║                                                                             ║
echo ╚═════════════════════════════════════════════════════════════════════════════╝
echo.

REM Check if WSL is available  
where wsl >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ WSL detected - launching systematized deployment...
    echo.
    wsl bash -c "cd '%CD%' && chmod +x deploy && ./deploy %*"
) else (
    echo ⚠️  WSL not detected
    echo.
    echo This deployment system requires Linux/WSL environment for optimal functionality.
    echo.  
    echo Available options:
    echo   1. Install WSL: https://docs.microsoft.com/windows/wsl/install
    echo   2. Use Docker Desktop with Linux containers  
    echo   3. Deploy to Linux server using deployment bridge
    echo.
    echo For development on Windows, you can run:
    echo   cd armguard
    echo   python manage.py runserver
    echo.
    pause
)