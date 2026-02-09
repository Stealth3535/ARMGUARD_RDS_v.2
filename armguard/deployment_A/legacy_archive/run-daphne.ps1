# Daphne ASGI Server Runner for Windows
# Runs Daphne for WebSocket support in development

param(
    [string]$Host = "127.0.0.1",
    [int]$Port = 8000,
    [int]$Workers = 2,
    [switch]$Help
)

# Colors for output
$ColorInfo = "Cyan"
$ColorSuccess = "Green"
$ColorWarning = "Yellow"
$ColorError = "Red"

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $ColorSuccess
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $ColorWarning
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $ColorError
}

function Show-Usage {
    Write-Host @"

ArmGuard Daphne ASGI Server Runner (Windows)
Runs Daphne development server with WebSocket support

USAGE:
    .\run-daphne.ps1 [-Host <address>] [-Port <port>] [-Workers <num>] [-Help]

PARAMETERS:
    -Host      Bind address (default: 127.0.0.1)
    -Port      Port number (default: 8000)
    -Workers   Number of workers (default: 2)
    -Help      Show this help message

EXAMPLES:
    .\run-daphne.ps1                           # Run with defaults
    .\run-daphne.ps1 -Port 8080                # Run on different port
    .\run-daphne.ps1 -Host 0.0.0.0 -Workers 4  # Listen on all interfaces with 4 workers

NOTES:
    - Make sure virtual environment is activated first
    - Press Ctrl+C to stop the server
    - For production, use Linux with systemd service

"@
}

# Show help if requested
if ($Help) {
    Show-Usage
    exit 0
}

Write-Host ""
Write-Host "========================================" -ForegroundColor $ColorSuccess
Write-Host "ArmGuard Daphne ASGI Server" -ForegroundColor $ColorSuccess
Write-Host "========================================" -ForegroundColor $ColorSuccess
Write-Host ""

# Configuration
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ArmguardDir = Join-Path $ProjectRoot "armguard"
$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"
$AsgiModule = "core.asgi:application"

Write-Info "Configuration:"
Write-Host "  Project Root: $ProjectRoot"
Write-Host "  Armguard Dir: $ArmguardDir"
Write-Host "  Virtual Env:  $VenvDir"
Write-Host "  Bind Address: $Host`:$Port"
Write-Host "  Workers:      $Workers"
Write-Host ""

# Validation
Write-Info "Validating environment..."

if (-not (Test-Path $ArmguardDir)) {
    Write-Error-Custom "Armguard directory not found: $ArmguardDir"
    Write-Info "Make sure you're running this from the deployment directory"
    exit 1
}
Write-Success "Armguard directory found"

if (-not (Test-Path $VenvDir)) {
    Write-Error-Custom "Virtual environment not found: $VenvDir"
    Write-Info "Create it with: python -m venv .venv"
    exit 1
}
Write-Success "Virtual environment found"

if (-not (Test-Path $PythonExe)) {
    Write-Error-Custom "Python executable not found: $PythonExe"
    exit 1
}
Write-Success "Python executable found"

# Check if Daphne is installed
Write-Info "Checking for Daphne..."
$DaphneCheck = & $PythonExe -m pip show daphne 2>$null
if (-not $DaphneCheck) {
    Write-Error-Custom "Daphne is not installed in the virtual environment"
    Write-Info "Install with: pip install daphne channels channels-redis"
    exit 1
}
Write-Success "Daphne is installed"

# Check if port is already in use
Write-Info "Checking if port $Port is available..."
$Connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Connection) {
    Write-Error-Custom "Port $Port is already in use by process $($Connection.OwningProcess)"
    Write-Info "Stop the process or use a different port with -Port parameter"
    exit 1
}
Write-Success "Port $Port is available"

# Optional: Check if Redis is running (for production channel layer)
Write-Info "Checking for Redis (optional)..."
try {
    $RedisTest = Test-Connection -ComputerName localhost -Port 6379 -Count 1 -ErrorAction Stop
    Write-Success "Redis is running (production channel layer available)"
} catch {
    Write-Warning "Redis is not running (using InMemoryChannelLayer)"
    Write-Info "For production, install Redis or use WSL2/Docker"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor $ColorSuccess
Write-Host "Starting Daphne Server..." -ForegroundColor $ColorSuccess
Write-Host "========================================" -ForegroundColor $ColorSuccess
Write-Host ""
Write-Info "Server URL: http://$Host`:$Port/"
Write-Info "Press Ctrl+C to stop"
Write-Host ""

# Change to armguard directory
Set-Location $ArmguardDir

# Run Daphne
try {
    & $PythonExe -m daphne `
        --bind $Host `
        --port $Port `
        --workers $Workers `
        --proxy-headers `
        --verbosity 2 `
        $AsgiModule
} catch {
    Write-Error-Custom "Failed to start Daphne: $_"
    exit 1
} finally {
    Write-Host ""
    Write-Info "Server stopped"
}
