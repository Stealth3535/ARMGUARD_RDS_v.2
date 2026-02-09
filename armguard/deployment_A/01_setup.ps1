# ==============================================================================
# 01_SETUP.PS1 - ENVIRONMENT SETUP AND PREREQUISITES
# ==============================================================================
# PURPOSE: System updates, package installs, environment preparation
# INTEGRATED: Best practices from deployment_A + deployment folders
# VERSION: 4.0.0 - Windows PowerShell Compatible
# ==============================================================================

param(
    [switch]$Quiet = $false,
    [switch]$SkipPackages = $false,
    [switch]$DevMode = $false
)

# ==============================================================================
# CONFIGURATION AND CONSTANTS
# ==============================================================================

$script:SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:LOG_DIR = if (Test-Administrator) { "C:\logs\armguard-deploy" } else { "$env:LOCALAPPDATA\armguard-logs" }
$script:LOG_FILE = Join-Path $script:LOG_DIR "01-setup-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$script:ARMGUARD_ROOT = Split-Path -Parent $script:SCRIPT_DIR

# Load configuration if available
$configFile = Join-Path $script:SCRIPT_DIR "master-config.ps1"
if (Test-Path $configFile) {
    . $configFile
}

# Colors for output
$script:Colors = @{
    RED = "Red"
    GREEN = "Green"
    YELLOW = "Yellow"
    BLUE = "Blue"
    PURPLE = "Magenta"
    CYAN = "Cyan"
    WHITE = "White"
}

# ==============================================================================
# LOGGING SYSTEM
# ==============================================================================

function Ensure-LogDir {
    if (-not (Test-Path $script:LOG_DIR)) {
        New-Item -ItemType Directory -Path $script:LOG_DIR -Force | Out-Null
        if (Test-Administrator) {
            # Set permissions for www-data equivalent (IIS_IUSRS on Windows)
            try {
                $acl = Get-Acl $script:LOG_DIR
                $accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule("IIS_IUSRS", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
                $acl.SetAccessRule($accessRule)
                Set-Acl -Path $script:LOG_DIR -AclObject $acl
            } catch {
                # Permissions setting failed, continue anyway
            }
        }
    }
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [SETUP-$Level] $Message"
    
    if (-not $script:Quiet) {
        Write-Host "[SETUP-$Level] $Message" -ForegroundColor $script:Colors[$Color]
    }
    
    Add-Content -Path $script:LOG_FILE -Value $logEntry
}

function Log-Info { param([string]$Message) Write-Log $Message "INFO" "GREEN" }
function Log-Warn { param([string]$Message) Write-Log $Message "WARN" "YELLOW" }
function Log-Error { param([string]$Message) Write-Log $Message "ERROR" "RED" }
function Log-Success { param([string]$Message) Write-Log $Message "SUCCESS" "CYAN" }

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-SystemInfo {
    Log-Info "Detecting system information..."
    
    $sysInfo = @{
        OS_NAME = (Get-CimInstance Win32_OperatingSystem).Caption
        OS_VERSION = (Get-CimInstance Win32_OperatingSystem).Version
        ARCH = $env:PROCESSOR_ARCHITECTURE
        HOSTNAME = $env:COMPUTERNAME
        USER = $env:USERNAME
    }
    
    # Environment Detection
    if (Test-Path "\\vmware-host\Shared Folders") {
        $sysInfo.ENV_TYPE = "vmware"
        Log-Info "VMware environment detected"
    } elseif (Get-Process "docker" -ErrorAction SilentlyContinue) {
        $sysInfo.ENV_TYPE = "docker"
        Log-Info "Docker environment detected"
    } elseif ((Get-CimInstance Win32_ComputerSystem).Model -match "Virtual") {
        $sysInfo.ENV_TYPE = "virtual"
        Log-Info "Virtual machine environment detected"
    } else {
        $sysInfo.ENV_TYPE = "physical"
        Log-Info "Physical machine environment detected"
    }
    
    Log-Info "System: $($sysInfo.OS_NAME) $($sysInfo.OS_VERSION)"
    Log-Info "Architecture: $($sysInfo.ARCH)"
    Log-Info "Environment: $($sysInfo.ENV_TYPE)"
    
    return $sysInfo
}

# ==============================================================================
# PACKAGE MANAGEMENT
# ==============================================================================

function Install-Chocolatey {
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Log-Info "Chocolatey already installed"
        return $true
    }
    
    Log-Info "Installing Chocolatey package manager..."
    
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        
        Log-Success "Chocolatey installed successfully"
        return $true
    } catch {
        Log-Error "Failed to install Chocolatey: $($_.Exception.Message)"
        return $false
    }
}

function Install-SystemPackages {
    if ($script:SkipPackages) {
        Log-Info "Skipping system package installation"
        return $true
    }
    
    Log-Info "Installing system packages..."
    
    # Install Chocolatey first
    if (-not (Install-Chocolatey)) {
        return $false
    }
    
    $packages = @(
        "python",
        "nodejs",
        "git",
        "postgresql",
        "redis-64",
        "nginx",
        "openssl.light"
    )
    
    foreach ($package in $packages) {
        Log-Info "Installing $package..."
        try {
            & choco install $package -y --no-progress
            Log-Success "$package installed successfully"
        } catch {
            Log-Warn "Failed to install $package, may need manual installation"
        }
    }
    
    return $true
}

# ==============================================================================
# PYTHON ENVIRONMENT SETUP
# ==============================================================================

function Setup-PythonEnvironment {
    Log-Info "Setting up Python environment..."
    
    # Check Python availability
    try {
        $pythonVersion = & python --version 2>$null
        Log-Info "Python detected: $pythonVersion"
    } catch {
        Log-Error "Python not found. Please install Python first."
        return $false
    }
    
    # Create virtual environment
    $venvPath = Join-Path $script:ARMGUARD_ROOT "venv"
    
    if (Test-Path $venvPath) {
        Log-Info "Virtual environment already exists"
    } else {
        Log-Info "Creating Python virtual environment..."
        & python -m venv $venvPath
        
        if (Test-Path $venvPath) {
            Log-Success "Virtual environment created"
        } else {
            Log-Error "Failed to create virtual environment"
            return $false
        }
    }
    
    # Activate virtual environment  
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Log-Info "Activating virtual environment..."
        . $activateScript
        Log-Success "Virtual environment activated"
    }
    
    # Upgrade pip
    Log-Info "Upgrading pip..."
    & python -m pip install --upgrade pip
    
    return $true
}

function Install-PythonRequirements {
    Log-Info "Installing Python requirements..."
    
    $requirementsFile = Join-Path $script:ARMGUARD_ROOT "requirements.txt"
    
    if (Test-Path $requirementsFile) {
        Log-Info "Installing from requirements.txt..."
        & python -m pip install -r $requirementsFile
        Log-Success "Python requirements installed"
    } else {
        Log-Info "Installing essential Python packages..."
        $packages = @(
            "django==5.2.7",
            "djangorestframework",
            "django-cors-headers", 
            "channels",
            "channels-redis",
            "daphne",
            "gunicorn",
            "psycopg2-binary",
            "redis",
            "python-decouple",
            "pillow",
            "qrcode[pil]",
            "reportlab"
        )
        
        foreach ($package in $packages) {
            & python -m pip install $package
        }
        
        Log-Success "Essential Python packages installed"
    }
    
    return $true
}

# ==============================================================================
# DATABASE SETUP
# ==============================================================================

function Setup-Database {
    Log-Info "Setting up database..."
    
    # Start PostgreSQL service if available
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if ($pgService) {
        Log-Info "Starting PostgreSQL service..."
        Start-Service $pgService.Name
        Log-Success "PostgreSQL service started"
    } else {
        Log-Warn "PostgreSQL service not found - may need manual configuration"
    }
    
    # Create database directories
    $dbDir = Join-Path $script:ARMGUARD_ROOT "db"
    if (-not (Test-Path $dbDir)) {
        New-Item -ItemType Directory -Path $dbDir -Force | Out-Null
    }
    
    return $true
}

# ==============================================================================
# REDIS SETUP
# ==============================================================================

function Setup-Redis {
    Log-Info "Setting up Redis..."
    
    # Start Redis service if available
    $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if ($redisService) {
        Log-Info "Starting Redis service..."
        Start-Service "Redis"
        Log-Success "Redis service started"
    } else {
        Log-Warn "Redis service not found - may need manual configuration"
    }
    
    # Test Redis connection
    try {
        $redisTest = & redis-cli ping 2>$null
        if ($redisTest -eq "PONG") {
            Log-Success "Redis is responding"
        }
    } catch {
        Log-Warn "Redis connection test failed"
    }
    
    return $true
}

# ==============================================================================
# SECURITY SETUP
# ==============================================================================

function Setup-Security {
    Log-Info "Configuring security settings..."
    
    # Create secure directories
    $secureDir = Join-Path $script:ARMGUARD_ROOT "secure"
    if (-not (Test-Path $secureDir)) {
        New-Item -ItemType Directory -Path $secureDir -Force | Out-Null
        
        # Set restrictive permissions
        if (Test-Administrator) {
            try {
                $acl = Get-Acl $secureDir
                $acl.SetAccessRuleProtection($true, $false)  # Disable inheritance
                $ownerRule = New-Object System.Security.AccessControl.FileSystemAccessRule($env:USERNAME, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
                $acl.SetAccessRule($ownerRule)
                Set-Acl -Path $secureDir -AclObject $acl
                Log-Success "Secure directory created with restricted permissions"
            } catch {
                Log-Warn "Could not set secure directory permissions"
            }
        }
    }
    
    return $true
}

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

function Test-Setup {
    Log-Info "Validating setup..."
    
    $issues = @()
    
    # Check Python
    try {
        $pythonVersion = & python --version 2>$null
        Log-Success "Python: $pythonVersion"
    } catch {
        $issues += "Python not accessible"
    }
    
    # Check virtual environment
    $venvPath = Join-Path $script:ARMGUARD_ROOT "venv"
    if (Test-Path $venvPath) {
        Log-Success "Virtual environment: Found"
    } else {
        $issues += "Virtual environment not found"
    }
    
    # Check essential packages
    $essentialPackages = @("django", "channels", "redis")
    foreach ($package in $essentialPackages) {
        try {
            & python -c "import $package" 2>$null
            Log-Success "Python package: $package"
        } catch {
            $issues += "Missing Python package: $package"
        }
    }
    
    if ($issues.Count -eq 0) {
        Log-Success "All setup validation checks passed"
        return $true
    } else {
        Log-Error "Setup validation issues found:"
        foreach ($issue in $issues) {
            Log-Error "  • $issue"
        }
        return $false
    }
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    Ensure-LogDir
    
    Log-Info "=== ArmGuard Setup (01_SETUP.PS1) Started ==="
    Log-Info "PowerShell Version: $($PSVersionTable.PSVersion)"
    
    # System detection
    $systemInfo = Get-SystemInfo
    
    # Check administrator privileges
    if (-not (Test-Administrator)) {
        Log-Warn "Not running as Administrator - some features may be limited"
        Log-Warn "For full functionality, run PowerShell as Administrator"
    }
    
    # Setup phases
    $phases = @(
        @{ Name = "System Packages"; Function = { Install-SystemPackages } },
        @{ Name = "Python Environment"; Function = { Setup-PythonEnvironment } },
        @{ Name = "Python Requirements"; Function = { Install-PythonRequirements } },
        @{ Name = "Database Setup"; Function = { Setup-Database } },
        @{ Name = "Redis Setup"; Function = { Setup-Redis } },
        @{ Name = "Security Configuration"; Function = { Setup-Security } }
    )
    
    foreach ($phase in $phases) {
        Log-Info "Phase: $($phase.Name)"
        $success = & $phase.Function
        
        if (-not $success) {
            Log-Error "Setup phase failed: $($phase.Name)"
            Log-Error "Check logs for details: $script:LOG_FILE"
            return 1
        }
    }
    
    # Final validation
    if (Test-Setup) {
        Log-Success "=== ArmGuard Setup Completed Successfully ==="
        Log-Info "Next step: Run 02_config.ps1 for application configuration"
        Log-Info "Log file: $script:LOG_FILE"
        return 0
    } else {
        Log-Error "Setup validation failed"
        return 1
    }
}

# Execute main function
$exitCode = Main
exit $exitCode