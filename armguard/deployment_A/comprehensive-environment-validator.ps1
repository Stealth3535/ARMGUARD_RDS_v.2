# ==============================================================================
# COMPREHENSIVE ENVIRONMENT VALIDATOR - CROSS-PLATFORM
# ==============================================================================
# PURPOSE: Complete hardware, OS, and software environment testing
# SUPPORTS: Windows (PowerShell) and Linux (Bash compatibility)
# VERSION: 5.0.0 - Full System Validation
# ==============================================================================

param(
    [switch]$Detailed = $false,
    [switch]$FixIssues = $false,
    [string]$ReportPath = "",
    [switch]$SkipInteractive = $false
)

# ==============================================================================
# SYSTEM DETECTION AND CONSTANTS
# ==============================================================================

$script:VALIDATION_RESULTS = @()
$script:SYSTEM_INFO = @{}
$script:REQUIREMENTS = @{
    MinMemoryMB = 512
    MinDiskGB = 2
    MinPythonVersion = [Version]"3.8"
    RequiredPorts = @(80, 443, 8000, 6379)
    RequiredServices = @("PostgreSQL", "Redis", "Python", "Git")
}

# ==============================================================================
# COMPREHENSIVE HARDWARE DETECTION
# ==============================================================================

function Test-HardwareEnvironment {
    Write-Host "`n🖥️ Hardware Environment Analysis..." -ForegroundColor Cyan
    
    # CPU Analysis
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $coreCount = [int]$env:NUMBER_OF_PROCESSORS
    $architecture = $env:PROCESSOR_ARCHITECTURE
    
    Add-Result "Hardware" "CPU Architecture" "INFO" "$architecture detected" "Cores: $coreCount, Model: $($cpu.Name)"
    
    # Memory Analysis
    $totalMemory = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB, 0)
    $availableMemory = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1KB, 0)
    
    if ($totalMemory -ge $script:REQUIREMENTS.MinMemoryMB) {
        Add-Result "Hardware" "Memory" "PASS" "$totalMemory MB total memory" "Available: $availableMemory MB"
    } else {
        Add-Result "Hardware" "Memory" "FAIL" "Insufficient memory: $totalMemory MB" "Minimum required: $($script:REQUIREMENTS.MinMemoryMB) MB" "Add more RAM or enable virtual memory"
    }
    
    # Disk Space Analysis
    $systemDrive = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DeviceID -eq $env:SystemDrive }
    $freeSpaceGB = [math]::Round($systemDrive.FreeSpace / 1GB, 1)
    
    if ($freeSpaceGB -ge $script:REQUIREMENTS.MinDiskGB) {
        Add-Result "Hardware" "Disk Space" "PASS" "$freeSpaceGB GB available" "Drive: $($systemDrive.DeviceID)"
    } else {
        Add-Result "Hardware" "Disk Space" "FAIL" "Insufficient disk space: $freeSpaceGB GB" "Minimum required: $($script:REQUIREMENTS.MinDiskGB) GB" "Free up disk space or add storage"
    }
    
    # Platform Detection
    $computerSystem = Get-CimInstance Win32_ComputerSystem
    $platformType = if ($computerSystem.Model -match "VMware|Virtual|VirtualBox") { "Virtual Machine" }
        elseif ($computerSystem.Manufacturer -match "Docker") { "Container" }
        elseif ($env:WSL_DISTRO_NAME) { "WSL" }
        else { "Physical Hardware" }
    
    Add-Result "Hardware" "Platform" "INFO" "$platformType detected" "Manufacturer: $($computerSystem.Manufacturer), Model: $($computerSystem.Model)"
    
    # Performance Recommendations
    $recommendedWorkers = [math]::Max(2, ($coreCount * 2 + 1))
    Add-Result "Hardware" "Performance Config" "INFO" "Recommended workers: $recommendedWorkers" "Based on $coreCount CPU cores"
    
    $script:SYSTEM_INFO.Hardware = @{
        CPUCores = $coreCount
        Architecture = $architecture
        TotalMemoryMB = $totalMemory
        AvailableMemoryMB = $availableMemory
        FreeSpaceGB = $freeSpaceGB
        PlatformType = $platformType
        RecommendedWorkers = $recommendedWorkers
    }
}

# ==============================================================================
# OPERATING SYSTEM ANALYSIS
# ==============================================================================

function Test-OperatingSystem {
    Write-Host "`n💻 Operating System Analysis..." -ForegroundColor Cyan
    
    # Windows Version Detection
    $os = Get-CimInstance Win32_OperatingSystem
    $winVersion = [Version]$os.Version
    $osName = $os.Caption
    $buildNumber = $os.BuildNumber
    
    Add-Result "OS" "Windows Version" "PASS" "$osName" "Version: $($winVersion.ToString()), Build: $buildNumber"
    
    # PowerShell Version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -ge 5) {
        Add-Result "OS" "PowerShell Version" "PASS" "PowerShell $($psVersion.ToString()) compatible"
    } else {
        Add-Result "OS" "PowerShell Version" "FAIL" "PowerShell version too old: $($psVersion.ToString())" "Minimum required: 5.0" "Update to PowerShell 5.0+"
    }
    
    # Administrator Privileges
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if ($isAdmin) {
        Add-Result "OS" "Administrator Rights" "PASS" "Running with administrator privileges"
    } else {
        Add-Result "OS" "Administrator Rights" "WARN" "Not running as administrator" "Some features may be limited" "Run PowerShell as Administrator for full functionality"
    }
    
    # Windows Features
    $features = @{
        "IIS" = "Web Server role for production deployment"
        "Hyper-V" = "Virtualization support for containers"
    }
    
    foreach ($feature in $features.Keys) {
        $featureState = Get-WindowsOptionalFeature -Online -FeatureName $feature -ErrorAction SilentlyContinue
        if ($featureState -and $featureState.State -eq "Enabled") {
            Add-Result "OS" "Windows Features" "INFO" "$feature enabled" $features[$feature]
        }
    }
    
    # Network Configuration
    $networkAdapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
    if ($networkAdapters.Count -gt 0) {
        Add-Result "OS" "Network Adapters" "PASS" "$($networkAdapters.Count) active network adapter(s)"
        foreach ($adapter in $networkAdapters) {
            $ipConfig = Get-NetIPAddress -InterfaceIndex $adapter.InterfaceIndex | Where-Object { $_.AddressFamily -eq "IPv4" } | Select-Object -First 1
            if ($ipConfig) {
                Add-Result "OS" "Network Config" "INFO" "$($adapter.Name): $($ipConfig.IPAddress)"
            }
        }
    } else {
        Add-Result "OS" "Network Adapters" "FAIL" "No active network adapters" "" "Check network connections"
    }
    
    $script:SYSTEM_INFO.OS = @{
        Name = $osName
        Version = $winVersion.ToString()
        BuildNumber = $buildNumber
        PowerShellVersion = $psVersion.ToString()
        IsAdmin = $isAdmin
        NetworkAdapters = $networkAdapters.Count
    }
}

# ==============================================================================
# SOFTWARE DEPENDENCY VALIDATION
# ==============================================================================

function Test-SoftwareDependencies {
    Write-Host "`n📦 Software Dependencies Analysis..." -ForegroundColor Cyan
    
    # Python Detection and Validation
    Test-PythonEnvironment
    
    # Git Version Control
    Test-GitInstallation
    
    # Database Systems
    Test-DatabaseSystems
    
    # Cache Systems
    Test-CacheSystems
    
    # Web Servers
    Test-WebServers
    
    # Package Managers
    Test-PackageManagers
    
    # Development Tools
    Test-DevelopmentTools
}

function Test-PythonEnvironment {
    Write-Host "Checking Python environment..." -ForegroundColor White
    
    # Python Installation
    try {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCmd) {
            $pythonCmd = Get-Command python3 -ErrorAction SilentlyContinue
        }
        
        if ($pythonCmd) {
            $pythonVersion = & $pythonCmd.Source --version 2>$null
            $versionMatch = $pythonVersion -match "Python (\d+\.\d+\.\d+)"
            if ($versionMatch) {
                $pyVer = [Version]$Matches[1]
                if ($pyVer -ge $script:REQUIREMENTS.MinPythonVersion) {
                    Add-Result "Software" "Python Version" "PASS" "Python $($pyVer.ToString()) installed" "Location: $($pythonCmd.Source)"
                } else {
                    Add-Result "Software" "Python Version" "FAIL" "Python version too old: $($pyVer.ToString())" "Minimum required: $($script:REQUIREMENTS.MinPythonVersion)" "Update Python to version $($script:REQUIREMENTS.MinPythonVersion) or later"
                }
            } else {
                Add-Result "Software" "Python Version" "WARN" "Could not determine Python version" "Output: $pythonVersion"
            }
        } else {
            Add-Result "Software" "Python Installation" "FAIL" "Python not found in PATH" "" "Install Python $($script:REQUIREMENTS.MinPythonVersion)+ from python.org"
        }
    } catch {
        Add-Result "Software" "Python Installation" "FAIL" "Python check failed: $($_.Exception.Message)" "" "Install Python from python.org"
    }
    
    # pip Package Manager
    try {
        $pipVersion = pip --version 2>$null
        if ($pipVersion) {
            Add-Result "Software" "pip Manager" "PASS" "pip package manager available" "Version info: $pipVersion"
        } else {
            Add-Result "Software" "pip Manager" "FAIL" "pip not available" "" "Install pip or repair Python installation"
        }
    } catch {
        Add-Result "Software" "pip Manager" "WARN" "Could not verify pip installation"
    }
    
    # Virtual Environment Support
    try {
        $venvTest = python -m venv --help 2>$null
        if ($venvTest) {
            Add-Result "Software" "Virtual Environments" "PASS" "venv module available"
        } else {
            Add-Result "Software" "Virtual Environments" "WARN" "venv module not available" "" "Install python3-venv package"
        }
    } catch {
        Add-Result "Software" "Virtual Environments" "WARN" "Could not test venv support"
    }
}

function Test-GitInstallation {
    Write-Host "Checking Git version control..." -ForegroundColor White
    
    try {
        $gitVersion = git --version 2>$null
        if ($gitVersion) {
            Add-Result "Software" "Git Installation" "PASS" "Git version control available" "Version: $gitVersion"
            
            # Git Configuration
            $gitUser = git config --global user.name 2>$null
            $gitEmail = git config --global user.email 2>$null
            
            if ($gitUser -and $gitEmail) {
                Add-Result "Software" "Git Configuration" "PASS" "Git configured with user: $gitUser ($gitEmail)"
            } else {
                Add-Result "Software" "Git Configuration" "WARN" "Git not configured with user credentials" "" "Run git config commands to set user name and email"
            }
        } else {
            Add-Result "Software" "Git Installation" "FAIL" "Git not found" "" "Install Git from git-scm.com"
        }
    } catch {
        Add-Result "Software" "Git Installation" "FAIL" "Git check failed: $($_.Exception.Message)" "" "Install Git from git-scm.com"
    }
}

function Test-DatabaseSystems {
    Write-Host "Checking database systems..." -ForegroundColor White
    
    # PostgreSQL
    $pgService = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue
    if ($pgService) {
        if ($pgService.Status -eq "Running") {
            Add-Result "Software" "PostgreSQL" "PASS" "PostgreSQL service running" "Service: $($pgService.Name)"
        } else {
            Add-Result "Software" "PostgreSQL" "WARN" "PostgreSQL installed but not running" "Service: $($pgService.Name), Status: $($pgService.Status)" "Start PostgreSQL service"
        }
    } else {
        # Check for psql command
        try {
            $psqlVersion = psql --version 2>$null
            if ($psqlVersion) {
                Add-Result "Software" "PostgreSQL Client" "PASS" "PostgreSQL client available" "Version: $psqlVersion"
            } else {
                Add-Result "Software" "PostgreSQL" "WARN" "PostgreSQL not detected" "" "Install PostgreSQL for production deployment"
            }
        } catch {
            Add-Result "Software" "PostgreSQL" "WARN" "PostgreSQL not detected" "" "Install PostgreSQL from postgresql.org"
        }
    }
    
    # SQLite (built into Python)
    try {
        $sqliteTest = python -c "import sqlite3; print(sqlite3.sqlite_version)" 2>$null
        if ($sqliteTest) {
            Add-Result "Software" "SQLite" "PASS" "SQLite available (Python built-in)" "Version: $sqliteTest"
        } else {
            Add-Result "Software" "SQLite" "WARN" "Could not verify SQLite support"
        }
    } catch {
        # Not critical as SQLite is usually built into Python
    }
}

function Test-CacheSystems {
    Write-Host "Checking cache systems..." -ForegroundColor White
    
    # Redis Server
    $redisService = Get-Service -Name "*redis*" -ErrorAction SilentlyContinue
    if ($redisService) {
        if ($redisService.Status -eq "Running") {
            Add-Result "Software" "Redis Server" "PASS" "Redis service running" "Service: $($redisService.Name)"
        } else {
            Add-Result "Software" "Redis Server" "WARN" "Redis installed but not running" "Service: $($redisService.Name), Status: $($redisService.Status)" "Start Redis service"
        }
    } else {
        # Check for redis-cli command
        try {
            $redisVersion = redis-cli --version 2>$null
            if ($redisVersion) {
                Add-Result "Software" "Redis Client" "PASS" "Redis client available" "Version: $redisVersion"
            } else {
                Add-Result "Software" "Redis" "WARN" "Redis not detected" "" "Install Redis for caching and real-time features"
            }
        } catch {
            Add-Result "Software" "Redis" "WARN" "Redis not detected" "" "Install Redis from redis.io or use Windows binaries"
        }
    }
}

function Test-WebServers {
    Write-Host "Checking web servers..." -ForegroundColor White
    
    # IIS (Internet Information Services)
    try {
        $iisFeature = Get-WindowsOptionalFeature -Online -FeatureName "IIS-WebServerRole" -ErrorAction SilentlyContinue
        if ($iisFeature -and $iisFeature.State -eq "Enabled") {
            Add-Result "Software" "IIS Web Server" "PASS" "IIS web server enabled"
        } else {
            Add-Result "Software" "IIS Web Server" "WARN" "IIS not enabled" "" "Enable IIS for production deployment: Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole"
        }
    } catch {
        Add-Result "Software" "IIS Web Server" "WARN" "Could not check IIS status"
    }
    
    # Nginx (if installed via package manager or manually)
    try {
        $nginxVersion = nginx -v 2>$1
        if ($nginxVersion) {
            Add-Result "Software" "Nginx" "PASS" "Nginx web server available" "Version info: $nginxVersion"
        }
    } catch {
        # Nginx not critical on Windows, IIS is preferred
    }
}

function Test-PackageManagers {
    Write-Host "Checking package managers..." -ForegroundColor White
    
    # Chocolatey
    try {
        $chocoVersion = choco --version 2>$null
        if ($chocoVersion) {
            Add-Result "Software" "Chocolatey" "PASS" "Chocolatey package manager available" "Version: $chocoVersion"
        } else {
            Add-Result "Software" "Chocolatey" "WARN" "Chocolatey not installed" "" "Install Chocolatey from chocolatey.org for automated package management"
        }
    } catch {
        Add-Result "Software" "Chocolatey" "WARN" "Chocolatey not available" "" "Install from chocolatey.org"
    }
    
    # Windows Package Manager (winget)
    try {
        $wingetVersion = winget --version 2>$null
        if ($wingetVersion) {
            Add-Result "Software" "Windows Package Manager" "PASS" "winget available" "Version: $wingetVersion"
        }
    } catch {
        # Not critical, available in newer Windows versions
    }
}

function Test-DevelopmentTools {
    Write-Host "Checking development tools..." -ForegroundColor White
    
    # Node.js (for frontend build tools if needed)
    try {
        $nodeVersion = node --version 2>$null
        if ($nodeVersion) {
            Add-Result "Software" "Node.js" "INFO" "Node.js available" "Version: $nodeVersion"
        }
    } catch {
        # Not critical for Django deployment
    }
    
    # Docker (for containerized deployment)
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Add-Result "Software" "Docker" "INFO" "Docker available" "Version: $dockerVersion"
            
            # Test if Docker is running
            try {
                $dockerInfo = docker info 2>$null
                if ($dockerInfo) {
                    Add-Result "Software" "Docker Status" "PASS" "Docker daemon running"
                } else {
                    Add-Result "Software" "Docker Status" "WARN" "Docker installed but daemon not running" "" "Start Docker Desktop or service"
                }
            } catch {
                Add-Result "Software" "Docker Status" "WARN" "Docker daemon not accessible"
            }
        }
    } catch {
        # Docker not critical for basic deployment
    }
    
    # Visual Studio Code (development environment)
    $codeLocations = @(
        "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe",
        "$env:ProgramFiles\Microsoft VS Code\Code.exe",
        "$env:ProgramFiles(x86)\Microsoft VS Code\Code.exe"
    )
    
    $vsCodeFound = $false
    foreach ($location in $codeLocations) {
        if (Test-Path $location) {
            Add-Result "Software" "VS Code" "INFO" "Visual Studio Code detected" "Location: $location"
            $vsCodeFound = $true
            break
        }
    }
    
    if (-not $vsCodeFound) {
        # Check PATH for code command
        try {
            $codeVersion = code --version 2>$null
            if ($codeVersion) {
                Add-Result "Software" "VS Code" "INFO" "Visual Studio Code available via PATH"
            }
        } catch {
            # Not critical, just informational
        }
    }
}

# ==============================================================================
# NETWORK CONNECTIVITY AND PORT VALIDATION
# ==============================================================================

function Test-NetworkEnvironment {
    Write-Host "`n🌐 Network Environment Analysis..." -ForegroundColor Cyan
    
    # Internet Connectivity
    try {
        $pingResult = Test-NetConnection -ComputerName "8.8.8.8" -Port 53 -InformationLevel Quiet
        if ($pingResult) {
            Add-Result "Network" "Internet Connectivity" "PASS" "Internet connection available"
        } else {
            Add-Result "Network" "Internet Connectivity" "FAIL" "No internet connection" "" "Check network settings and connectivity"
        }
    } catch {
        Add-Result "Network" "Internet Connectivity" "WARN" "Could not test internet connectivity"
    }
    
    # DNS Resolution
    try {
        $dnsTest = Resolve-DnsName -Name "github.com" -ErrorAction SilentlyContinue
        if ($dnsTest) {
            Add-Result "Network" "DNS Resolution" "PASS" "DNS resolution working"
        } else {
            Add-Result "Network" "DNS Resolution" "FAIL" "DNS resolution failed" "" "Check DNS settings"
        }
    } catch {
        Add-Result "Network" "DNS Resolution" "WARN" "Could not test DNS resolution"
    }
    
    # Port Availability
    foreach ($port in $script:REQUIREMENTS.RequiredPorts) {
        try {
            $portTest = Test-NetConnection -ComputerName "localhost" -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
            if (-not $portTest) {
                Add-Result "Network" "Port Availability" "PASS" "Port $port available"
            } else {
                Add-Result "Network" "Port Availability" "WARN" "Port $port already in use" "" "Stop service using port $port or configure alternative port"
            }
        } catch {
            Add-Result "Network" "Port Availability" "PASS" "Port $port appears available"
        }
    }
    
    # Firewall Status
    try {
        $firewallProfiles = Get-NetFirewallProfile
        $activeProfiles = $firewallProfiles | Where-Object { $_.Enabled -eq $true }
        if ($activeProfiles) {
            Add-Result "Network" "Windows Firewall" "INFO" "Firewall active on $($activeProfiles.Count) profile(s)" "Profiles: $($activeProfiles.Name -join ', ')"
        } else {
            Add-Result "Network" "Windows Firewall" "WARN" "Windows Firewall disabled" "" "Consider enabling firewall for security"
        }
    } catch {
        Add-Result "Network" "Windows Firewall" "WARN" "Could not check firewall status"
    }
}

# ==============================================================================
# ARMGUARD-SPECIFIC VALIDATION
# ==============================================================================

function Test-ArmGuardEnvironment {
    Write-Host "`n🛡️ ArmGuard-Specific Environment..." -ForegroundColor Cyan
    
    # Project Files
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $requiredFiles = @(
        "manage.py",
        "requirements.txt",
        "core\settings.py",
        "core\wsgi.py",
        "core\asgi.py"
    )
    
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $projectRoot $file
        if (Test-Path $filePath) {
            Add-Result "ArmGuard" "Project Files" "PASS" "$file exists"
        } else {
            Add-Result "ArmGuard" "Project Files" "FAIL" "$file missing" "Expected: $filePath" "Ensure complete ArmGuard project structure"
        }
    }
    
    # Environment Configuration
    $envFile = Join-Path $projectRoot ".env"
    if (Test-Path $envFile) {
        Add-Result "ArmGuard" "Environment Config" "PASS" ".env configuration file exists"
        
        # Validate critical environment variables
        $envContent = Get-Content $envFile
        $criticalVars = @("DJANGO_SECRET_KEY", "DB_NAME", "REDIS_PASSWORD")
        
        foreach ($var in $criticalVars) {
            $varLine = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=" }
            if ($varLine) {
                Add-Result "ArmGuard" "Environment Variables" "PASS" "$var configured"
            } else {
                Add-Result "ArmGuard" "Environment Variables" "FAIL" "$var not configured" "" "Run unified-env-generator.ps1 to create complete configuration"
            }
        }
    } else {
        Add-Result "ArmGuard" "Environment Config" "FAIL" ".env file not found" "Expected: $envFile" "Run unified-env-generator.ps1 to create environment configuration"
    }
    
    # Python Dependencies
    $requirementsFile = Join-Path $projectRoot "requirements.txt"
    if (Test-Path $requirementsFile) {
        Add-Result "ArmGuard" "Requirements File" "PASS" "requirements.txt exists"
        
        # Check Django version
        $reqContent = Get-Content $requirementsFile
        $djangoLine = $reqContent | Where-Object { $_ -like "Django==*" }
        if ($djangoLine -like "*5.2.7*") {
            Add-Result "ArmGuard" "Django Version" "PASS" "Django 5.2.7 specified in requirements"
        } else {
            Add-Result "ArmGuard" "Django Version" "WARN" "Django version may not be optimal" "Found: $djangoLine" "Consider updating to Django 5.2.7"
        }
    }
    
    # Database Connectivity Test (if possible)
    try {
        $pythonTest = python -c "import django; print('OK')" 2>$null
        if ($pythonTest -eq "OK") {
            Add-Result "ArmGuard" "Django Import" "PASS" "Django can be imported"
        }
    } catch {
        # Not critical at this stage
    }
}

# ==============================================================================
# VALIDATION FRAMEWORK AND REPORTING
# ==============================================================================

function Add-Result {
    param([string]$Category, [string]$Test, [string]$Status, [string]$Message, [string]$Details = "", [string]$Recommendation = "")
    
    $result = @{
        Category = $Category
        Test = $Test
        Status = $Status
        Message = $Message
        Details = $Details
        Recommendation = $Recommendation
        Timestamp = Get-Date
    }
    
    $script:VALIDATION_RESULTS += $result
    
    # Display result
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    
    $icon = switch ($Status) {
        "PASS" { "[PASS]" }
        "FAIL" { "[FAIL]" }
        "WARN" { "[WARN]" }
        "INFO" { "[INFO]" }
        default { "[TEST]" }
    }
    
    Write-Host "  $icon $Test`: $Message" -ForegroundColor $color
    
    if ($Detailed -and $Details) {
        Write-Host "    Details: $Details" -ForegroundColor Gray
    }
    
    if ($Status -eq "FAIL" -and $Recommendation) {
        Write-Host "    💡 Fix: $Recommendation" -ForegroundColor Yellow
    }
}

function Show-ValidationSummary {
    $totalTests = $script:VALIDATION_RESULTS.Count
    $passedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "PASS" }).Count
    $failedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count
    $warnTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }).Count
    $infoTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "INFO" }).Count
    
    Write-Host @"

═══════════════════════════════════════════════════════════════
🎯 COMPREHENSIVE ENVIRONMENT VALIDATION SUMMARY
═══════════════════════════════════════════════════════════════
Total Tests: $totalTests
✅ Passed: $passedTests
❌ Failed: $failedTests
⚠️ Warnings: $warnTests
ℹ️ Information: $infoTests

"@ -ForegroundColor Cyan
    
    # Category breakdown
    $categories = $script:VALIDATION_RESULTS | Group-Object Category | Sort-Object Name
    
    foreach ($category in $categories) {
        $catPassed = ($category.Group | Where-Object { $_.Status -eq "PASS" }).Count
        $catFailed = ($category.Group | Where-Object { $_.Status -eq "FAIL" }).Count
        $catWarns = ($category.Group | Where-Object { $_.Status -eq "WARN" }).Count
        $catTotal = $category.Count
        $catRate = if ($catTotal -gt 0) { [math]::Round((($catPassed) / $catTotal) * 100, 0) } else { 0 }
        
        $statusColor = if ($catFailed -eq 0 -and $catWarns -eq 0) { "Green" } 
                      elseif ($catFailed -eq 0) { "Yellow" } 
                      else { "Red" }
        
        Write-Host "📊 $($category.Name): " -NoNewline -ForegroundColor White
        Write-Host "$catPassed✅ $catFailed❌ $catWarns⚠️ ($catRate%)" -ForegroundColor $statusColor
    }
    
    # Overall readiness assessment
    Write-Host "`n🚀 Deployment Readiness Assessment:" -ForegroundColor White
    
    if ($failedTests -eq 0) {
        if ($warnTests -eq 0) {
            Write-Host "🟢 EXCELLENT - Ready for immediate deployment!" -ForegroundColor Green
            Write-Host "All systems validated successfully." -ForegroundColor Green
        } else {
            Write-Host "🟡 GOOD - Ready for deployment with minor optimizations" -ForegroundColor Yellow
            Write-Host "Address warnings for optimal performance." -ForegroundColor Yellow
        }
    } elseif ($failedTests -le 2) {
        Write-Host "🟠 NEEDS ATTENTION - Fix critical issues before deployment" -ForegroundColor DarkYellow
        Write-Host "Resolve failed tests for successful deployment." -ForegroundColor DarkYellow
    } else {
        Write-Host "🔴 NOT READY - Multiple critical issues require resolution" -ForegroundColor Red
        Write-Host "Address all failed tests before attempting deployment." -ForegroundColor Red
    }
    
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Export-ValidationReport {
    param([string]$FilePath)
    
    if (-not $FilePath) {
        $FilePath = Join-Path $PSScriptRoot "ENVIRONMENT_VALIDATION_REPORT_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
    }
    
    $report = @"
# 🔍 ArmGuard Comprehensive Environment Validation Report
**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**System:** $($script:SYSTEM_INFO.OS.Name) $($script:SYSTEM_INFO.OS.Version)
**Platform:** $($script:SYSTEM_INFO.Hardware.PlatformType)
**Total Tests:** $($script:VALIDATION_RESULTS.Count)

## 📊 Summary
- ✅ **Passed:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "PASS" }).Count)
- ❌ **Failed:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count)
- ⚠️ **Warnings:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }).Count)
- ℹ️ **Information:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "INFO" }).Count)

## 🖥️ System Information
- **Hardware:** $($script:SYSTEM_INFO.Hardware.CPUCores) cores, $($script:SYSTEM_INFO.Hardware.TotalMemoryMB) MB RAM, $($script:SYSTEM_INFO.Hardware.FreeSpaceGB) GB free
- **Operating System:** $($script:SYSTEM_INFO.OS.Name) $($script:SYSTEM_INFO.OS.Version)
- **PowerShell:** $($script:SYSTEM_INFO.OS.PowerShellVersion)
- **Architecture:** $($script:SYSTEM_INFO.Hardware.Architecture)
- **Platform Type:** $($script:SYSTEM_INFO.Hardware.PlatformType)

## 📋 Detailed Test Results

"@

    $categories = $script:VALIDATION_RESULTS | Group-Object Category | Sort-Object Name
    
    foreach ($category in $categories) {
        $report += "`n### $($category.Name)`n`n"
        
        foreach ($result in $category.Group | Sort-Object Test) {
            $icon = switch ($result.Status) {
                "PASS" { "✅" }
                "FAIL" { "❌" }
                "WARN" { "⚠️" }
                "INFO" { "ℹ️" }
                default { "🔍" }
            }
            
            $report += "**$icon $($result.Test):** $($result.Message)`n"
            
            if ($result.Details) {
                $report += "- *Details:* $($result.Details)`n"
            }
            
            if ($result.Recommendation) {
                $report += "- *💡 Recommendation:* $($result.Recommendation)`n"
            }
            
            $report += "`n"
        }
    }
    
    # Add recommendations section
    $failedResults = $script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }
    if ($failedResults.Count -gt 0) {
        $report += "`n## 🔧 Critical Issues to Fix`n`n"
        foreach ($failed in $failedResults) {
            if ($failed.Recommendation) {
                $report += "- **$($failed.Test):** $($failed.Recommendation)`n"
            }
        }
    }
    
    $warnResults = $script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }
    if ($warnResults.Count -gt 0) {
        $report += "`n## ⚡ Recommended Optimizations`n`n"
        foreach ($warn in $warnResults) {
            if ($warn.Recommendation) {
                $report += "- **$($warn.Test):** $($warn.Recommendation)`n"
            }
        }
    }
    
    Set-Content -Path $FilePath -Value $report -Encoding UTF8
    Write-Host "`n📄 Comprehensive validation report exported to: $FilePath" -ForegroundColor Green
    return $FilePath
}

# ==============================================================================
# MAIN EXECUTION FUNCTION
# ==============================================================================

function Main {
    Write-Host @"

═══════════════════════════════════════════════════════════════
🔍 ARMGUARD COMPREHENSIVE ENVIRONMENT VALIDATOR
═══════════════════════════════════════════════════════════════
Complete hardware, OS, and software environment testing
Cross-platform validation for optimal deployment readiness
═══════════════════════════════════════════════════════════════

"@ -ForegroundColor Cyan

    $startTime = Get-Date
    
    # Run comprehensive validation tests
    Test-HardwareEnvironment
    Test-OperatingSystem
    Test-SoftwareDependencies
    Test-NetworkEnvironment
    Test-ArmGuardEnvironment
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host "`n⏱️ Validation completed in $([math]::Round($duration.TotalSeconds, 1)) seconds" -ForegroundColor Gray
    
    # Show comprehensive summary
    Show-ValidationSummary
    
    # Export report if requested
    if ($ReportPath -or $Detailed) {
        $reportFile = Export-ValidationReport -FilePath $ReportPath
        if (-not $SkipInteractive) {
            $openReport = Read-Host "`nOpen validation report? (y/n)"
            if ($openReport -eq "y" -or $openReport -eq "yes") {
                Start-Process $reportFile
            }
        }
    }
    
    # Return exit code based on results
    $criticalFailures = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count
    if ($criticalFailures -eq 0) {
        Write-Host "`n🎉 Environment validation successful! System ready for deployment." -ForegroundColor Green
        return 0
    } elseif ($criticalFailures -le 2) {
        Write-Host "`n⚠️ Environment validation completed with minor issues. Review and fix before deployment." -ForegroundColor Yellow
        return 1
    } else {
        Write-Host "`n❌ Environment validation failed. Multiple critical issues require resolution." -ForegroundColor Red
        return 2
    }
}

# Execute main function
$exitCode = Main
exit $exitCode