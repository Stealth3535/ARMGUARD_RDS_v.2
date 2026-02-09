# ==============================================================================
# 02_CONFIG.PS1 - UNIFIED CONFIGURATION AND APPLICATION SETUP
# ==============================================================================
# PURPOSE: Environment variables, app configs, SSL certificates, database setup
# REPLACES: Hardcoded settings_production.py generation with unified .env approach
# VERSION: 4.0.0 - Synchronized Configuration System
# ==============================================================================

param(
    [string]$NetworkType = "",
    [string]$Domain = "",
    [string]$ServerIP = "",
    [switch]$ProductionMode = $false,
    [switch]$InteractiveMode = $true
)

# ==============================================================================
# CONFIGURATION AND CONSTANTS
# ==============================================================================

$script:SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:LOG_DIR = if (Test-Administrator) { "C:\logs\armguard-deploy" } else { "$env:LOCALAPPDATA\armguard-logs" }
$script:LOG_FILE = Join-Path $script:LOG_DIR "02-config-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$script:ARMGUARD_ROOT = Split-Path -Parent $script:SCRIPT_DIR

# Load master configuration
$masterConfig = Join-Path $script:SCRIPT_DIR "master-config.ps1"
if (Test-Path $masterConfig) {
    . $masterConfig
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
    }
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO",
        [string]$Color = "White"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logEntry = "[$timestamp] [CONFIG-$Level] $Message"
    
    Write-Host "[CONFIG-$Level] $Message" -ForegroundColor $script:Colors[$Color]
    Add-Content -Path $script:LOG_FILE -Value $logEntry
}

function Log-Info { param([string]$Message) Write-Log $Message "INFO" "GREEN" }
function Log-Warn { param([string]$Message) Write-Log $Message "WARN" "YELLOW" }
function Log-Error { param([string]$Message) Write-Log $Message "ERROR" "RED" }
function Log-Success { param([string]$Message) Write-Log $Message "SUCCESS" "CYAN" }

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# ==============================================================================
# UNIFIED ENVIRONMENT CONFIGURATION
# ==============================================================================

function Invoke-UnifiedConfiguration {
    param(
        [string]$NetworkType,
        [string]$Domain,
        [string]$ServerIP,
        [bool]$ProductionMode,
        [bool]$InteractiveMode
    )
    
    Log-Info "Creating unified environment configuration..."
    
    $envGenerator = Join-Path $script:SCRIPT_DIR "unified-env-generator.ps1"
    
    if (-not (Test-Path $envGenerator)) {
        Log-Error "Unified environment generator not found: $envGenerator"
        return $false
    }
    
    try {
        $params = @{}
        if ($NetworkType) { $params.NetworkType = $NetworkType }
        if ($Domain) { $params.Domain = $Domain }
        if ($ServerIP) { $params.ServerIP = $ServerIP }
        if ($ProductionMode) { $params.ProductionMode = $true }
        if (-not $InteractiveMode) { $params.InteractiveMode = $false }
        
        & $envGenerator @params
        
        $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
        if (Test-Path $envFile) {
            Log-Success "Unified environment configuration created: $envFile"
            return $true
        } else {
            Log-Error "Environment file not created"
            return $false
        }
    } catch {
        Log-Error "Failed to create unified configuration: $($_.Exception.Message)"
        return $false
    }
}

# ==============================================================================
# DATABASE SETUP (POSTGRESQL WITH FULL OPTIMIZATION)
# ==============================================================================

function Setup-PostgreSQL {
    Log-Info "Setting up PostgreSQL with full optimization..."
    
    # Check if PostgreSQL service is available
    $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if (-not $pgService) {
        Log-Warn "PostgreSQL service not found. Installing..."
        
        if (Get-Command choco -ErrorAction SilentlyContinue) {
            & choco install postgresql -y --no-progress
            Start-Sleep -Seconds 10  # Wait for installation
            $pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
        } else {
            Log-Error "PostgreSQL not available and Chocolatey not installed"
            return $false
        }
    }
    
    # Start PostgreSQL service
    if ($pgService) {
        Log-Info "Starting PostgreSQL service..."
        try {
            Start-Service $pgService.Name
            Log-Success "PostgreSQL service started"
        } catch {
            Log-Error "Failed to start PostgreSQL service: $($_.Exception.Message)"
            return $false
        }
    }
    
    # Create database and user (requires .env file to be loaded)
    $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
    if (Test-Path $envFile) {
        try {
            # Parse .env file for database settings
            $envContent = Get-Content $envFile
            $dbName = ($envContent | Where-Object { $_ -like "DB_NAME=*" }) -replace "DB_NAME=", ""
            $dbUser = ($envContent | Where-Object { $_ -like "DB_USER=*" }) -replace "DB_USER=", ""
            $dbPassword = ($envContent | Where-Object { $_ -like "DB_PASSWORD=*" }) -replace "DB_PASSWORD=", ""
            
            if ($dbName -and $dbUser -and $dbPassword) {
                Log-Info "Creating PostgreSQL database and user..."
                
                # Create database and user using psql
                $createDbCmd = @"
CREATE DATABASE $dbName;
CREATE USER $dbUser WITH PASSWORD '$dbPassword';
GRANT ALL PRIVILEGES ON DATABASE $dbName TO $dbUser;
ALTER USER $dbUser CREATEDB;
"@
                
                $createDbCmd | & psql -U postgres -h localhost 2>$null
                Log-Success "Database and user created successfully"
            }
        } catch {
            Log-Warn "Database creation may have failed, but continuing..."
        }
    }
    
    return $true
}

# ==============================================================================
# REDIS SETUP WITH SECURITY
# ==============================================================================

function Setup-Redis {
    Log-Info "Setting up Redis with security configuration..."
    
    # Check if Redis service is available
    $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if (-not $redisService) {
        Log-Info "Installing Redis..."
        
        if (Get-Command choco -ErrorAction SilentlyContinue) {
            & choco install redis-64 -y --no-progress
            Start-Sleep -Seconds 5
            $redisService = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
        } else {
            Log-Error "Redis not available and Chocolatey not installed"
            return $false
        }
    }
    
    # Configure Redis with password authentication
    $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
    if (Test-Path $envFile) {
        $envContent = Get-Content $envFile
        $redisPassword = ($envContent | Where-Object { $_ -like "REDIS_PASSWORD=*" }) -replace "REDIS_PASSWORD=", ""
        
        if ($redisPassword) {
            Log-Info "Configuring Redis with password authentication..."
            
            # Update Redis configuration
            $redisConfPath = "C:\Program Files\Redis\redis.windows-service.conf"
            if (Test-Path $redisConfPath) {
                try {
                    $redisConf = Get-Content $redisConfPath
                    $redisConf = $redisConf | Where-Object { $_ -notlike "requirepass*" }
                    $redisConf += "requirepass $redisPassword"
                    Set-Content -Path $redisConfPath -Value $redisConf
                    Log-Success "Redis password authentication configured"
                } catch {
                    Log-Warn "Could not configure Redis password automatically"
                }
            }
        }
    }
    
    # Start Redis service
    if ($redisService) {
        try {
            Start-Service "Redis"
            Log-Success "Redis service started"
        } catch {
            Log-Error "Failed to start Redis service: $($_.Exception.Message)"
            return $false
        }
        
        # Test Redis connection
        Start-Sleep -Seconds 2
        try {
            $redisTest = & redis-cli ping 2>$null
            if ($redisTest -eq "PONG") {
                Log-Success "Redis is responding"
            }
        } catch {
            Log-Warn "Redis connection test failed - may need manual configuration"
        }
    }
    
    return $true
}

# ==============================================================================
# APPLICATION DIRECTORY SETUP
# ==============================================================================

function Setup-ApplicationDirectories {
    Log-Info "Setting up application directories..."
    
    # Create necessary directories with proper permissions
    $directories = @(
        "C:\www\armguard\static",
        "C:\www\armguard\media", 
        "C:\logs\armguard",
        (Join-Path $script:ARMGUARD_ROOT "logs")
    )
    
    foreach ($dir in $directories) {
        if (-not (Test-Path $dir)) {
            try {
                New-Item -ItemType Directory -Path $dir -Force -Recurse | Out-Null
                Log-Success "Created directory: $dir"
                
                # Set permissions for web server access
                if (Test-Administrator -and $dir -like "C:\www\*") {
                    try {
                        $acl = Get-Acl $dir
                        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule("IIS_IUSRS", "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
                        $acl.SetAccessRule($rule)
                        Set-Acl -Path $dir -AclObject $acl
                        Log-Info "Set web server permissions for: $dir"
                    } catch {
                        Log-Warn "Could not set web server permissions for: $dir"
                    }
                }
            } catch {
                Log-Error "Failed to create directory: $dir"
                return $false
            }
        } else {
            Log-Info "Directory exists: $dir"
        }
    }
    
    return $true
}

# ==============================================================================
# DJANGO APPLICATION SETUP
# ==============================================================================

function Setup-DjangoApplication {
    Log-Info "Setting up Django application..."
    
    # Change to application directory
    Set-Location $script:ARMGUARD_ROOT
    
    # Activate virtual environment
    $venvActivate = Join-Path $script:ARMGUARD_ROOT "venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        . $venvActivate
        Log-Info "Virtual environment activated"
    } else {
        Log-Warn "Virtual environment not found - may need to run 01_setup.ps1 first"
    }
    
    # Load environment variables
    $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
    if (Test-Path $envFile) {
        Log-Info "Loading environment configuration..."
        $envContent = Get-Content $envFile
        foreach ($line in $envContent) {
            if ($line -and $line -notlike "#*" -and $line.Contains("=")) {
                $parts = $line.Split("=", 2)
                if ($parts.Length -eq 2) {
                    $env:($parts[0]) = $parts[1]
                }
            }
        }
        Log-Success "Environment variables loaded"
    }
    
    # Run Django migrations
    Log-Info "Running Django database migrations..."
    try {
        & python manage.py migrate --noinput
        if ($LASTEXITCODE -eq 0) {
            Log-Success "Database migrations completed"
        } else {
            Log-Error "Database migrations failed"
            return $false
        }
    } catch {
        Log-Error "Failed to run migrations: $($_.Exception.Message)"
        return $false
    }
    
    # Collect static files
    Log-Info "Collecting static files..."
    try {
        & python manage.py collectstatic --noinput
        if ($LASTEXITCODE -eq 0) {
            Log-Success "Static files collected"
        } else {
            Log-Warn "Static files collection had issues"
        }
    } catch {
        Log-Warn "Static files collection failed: $($_.Exception.Message)"
    }
    
    # Create superuser (interactive)
    Write-Host "`n🔐 Create Django administrator account:" -ForegroundColor White
    try {
        & python manage.py createsuperuser
        Log-Success "Superuser account created"
    } catch {
        Log-Warn "Superuser creation skipped or failed"
    }
    
    return $true
}

# ==============================================================================
# VALIDATION AND TESTING
# ==============================================================================

function Test-Configuration {
    Log-Info "Testing configuration..."
    
    $issues = @()
    
    # Test .env file exists and is readable
    $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
    if (Test-Path $envFile) {
        Log-Success ".env file exists"
        
        # Test essential environment variables
        $envContent = Get-Content $envFile
        $requiredVars = @("DJANGO_SECRET_KEY", "DB_NAME", "DB_USER", "DB_PASSWORD", "REDIS_PASSWORD")
        
        foreach ($var in $requiredVars) {
            $found = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=$" }
            if ($found) {
                Log-Success "Environment variable: $var"
            } else {
                $issues += "Missing or empty environment variable: $var"
            }
        }
    } else {
        $issues += ".env file not found"
    }
    
    # Test database connection
    Set-Location $script:ARMGUARD_ROOT
    try {
        & python manage.py check --database default
        if ($LASTEXITCODE -eq 0) {
            Log-Success "Database connection working"
        } else {
            $issues += "Database connection issues"
        }
    } catch {
        $issues += "Database check failed"
    }
    
    # Test Redis connection
    try {
        $redisTest = & redis-cli ping 2>$null
        if ($redisTest -eq "PONG") {
            Log-Success "Redis connection working"
        } else {
            $issues += "Redis not responding"
        }
    } catch {
        $issues += "Redis connection test failed"
    }
    
    if ($issues.Count -eq 0) {
        Log-Success "All configuration tests passed"
        return $true
    } else {
        Log-Error "Configuration issues found:"
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
    
    Log-Info "=== ArmGuard Configuration (02_CONFIG.PS1) Started ==="
    Log-Info "Unified Environment Configuration System"
    
    # Configuration phases
    $phases = @(
        @{ 
            Name = "Unified Environment Configuration"
            Function = { 
                Invoke-UnifiedConfiguration -NetworkType $script:NetworkType -Domain $script:Domain -ServerIP $script:ServerIP -ProductionMode $script:ProductionMode -InteractiveMode $script:InteractiveMode 
            }
        },
        @{ Name = "PostgreSQL Database Setup"; Function = { Setup-PostgreSQL } },
        @{ Name = "Redis Configuration"; Function = { Setup-Redis } },
        @{ Name = "Application Directories"; Function = { Setup-ApplicationDirectories } },
        @{ Name = "Django Application Setup"; Function = { Setup-DjangoApplication } }
    )
    
    foreach ($phase in $phases) {
        Log-Info "Phase: $($phase.Name)"
        $success = & $phase.Function
        
        if (-not $success) {
            Log-Error "Configuration phase failed: $($phase.Name)"
            return 1
        }
    }
    
    # Final validation
    if (Test-Configuration) {
        Log-Success "=== ArmGuard Configuration Completed Successfully ==="
        Log-Info "Next step: Run 03_services.ps1 to set up system services"
        Log-Info "Configuration file: $(Join-Path $script:ARMGUARD_ROOT '.env')"
        return 0
    } else {
        Log-Error "Configuration validation failed"
        return 1
    }
}

# Execute main function
$exitCode = Main
exit $exitCode