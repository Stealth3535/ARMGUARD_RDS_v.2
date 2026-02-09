# ==============================================================================
# COMPREHENSIVE ENVIRONMENT VALIDATOR - CROSS-PLATFORM  
# ==============================================================================

param(
    [switch]$Detailed = $false,
    [switch]$SkipInteractive = $false
)

$script:VALIDATION_RESULTS = @()

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

function Add-Result {
    param([string]$Category, [string]$Test, [string]$Status, [string]$Message, [string]$Details = "")
    
    $result = @{
        Category = $Category
        Test = $Test
        Status = $Status
        Message = $Message
        Details = $Details
    }
    
    $script:VALIDATION_RESULTS += $result
    
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
}

function Test-HardwareEnvironment {
    Write-Host "`nHardware Environment Analysis..." -ForegroundColor Cyan
    
    # CPU Analysis
    $coreCount = [int]$env:NUMBER_OF_PROCESSORS
    Add-Result "Hardware" "CPU Cores" "INFO" "$coreCount cores detected"
    
    # Memory Analysis
    $totalMemory = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB, 0)
    if ($totalMemory -ge 512) {
        Add-Result "Hardware" "Memory" "PASS" "$totalMemory MB total memory"
    } else {
        Add-Result "Hardware" "Memory" "FAIL" "Insufficient memory: $totalMemory MB"
    }
    
    # Disk Space Analysis
    $systemDrive = Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DeviceID -eq $env:SystemDrive }
    $freeSpaceGB = [math]::Round($systemDrive.FreeSpace / 1GB, 1)
    if ($freeSpaceGB -ge 2) {
        Add-Result "Hardware" "Disk Space" "PASS" "$freeSpaceGB GB available"
    } else {
        Add-Result "Hardware" "Disk Space" "FAIL" "Low disk space: $freeSpaceGB GB"
    }
    
    # Platform Detection
    $computerSystem = Get-CimInstance Win32_ComputerSystem
    $platformType = if ($computerSystem.Model -match "VMware|Virtual|VirtualBox") { "Virtual Machine" }
        elseif ($env:WSL_DISTRO_NAME) { "WSL" }
        else { "Physical Hardware" }
    
    Add-Result "Hardware" "Platform" "INFO" "$platformType detected"
}

function Test-OperatingSystem {
    Write-Host "`nOperating System Analysis..." -ForegroundColor Cyan
    
    # Windows Version
    $os = Get-CimInstance Win32_OperatingSystem
    Add-Result "OS" "Windows Version" "PASS" "$($os.Caption) Build $($os.BuildNumber)"
    
    # PowerShell Version
    $psVersion = $PSVersionTable.PSVersion
    if ($psVersion.Major -ge 5) {
        Add-Result "OS" "PowerShell Version" "PASS" "PowerShell $($psVersion.ToString())"
    } else {
        Add-Result "OS" "PowerShell Version" "FAIL" "PowerShell version too old: $($psVersion.ToString())"
    }
    
    # Administrator Privileges
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if ($isAdmin) {
        Add-Result "OS" "Administrator Rights" "PASS" "Running with administrator privileges"
    } else {
        Add-Result "OS" "Administrator Rights" "WARN" "Not running as administrator"
    }
    
    # Network Adapters
    $networkAdapters = Get-NetAdapter | Where-Object { $_.Status -eq "Up" }
    if ($networkAdapters.Count -gt 0) {
        Add-Result "OS" "Network" "PASS" "$($networkAdapters.Count) active network adapter(s)"
    } else {
        Add-Result "OS" "Network" "FAIL" "No active network adapters"
    }
}

function Test-SoftwareDependencies {
    Write-Host "`nSoftware Dependencies Analysis..." -ForegroundColor Cyan
    
    # Python Detection
    try {
        $pythonVersion = python --version 2>$null
        if ($pythonVersion) {
            Add-Result "Software" "Python" "PASS" "$pythonVersion detected"
        } else {
            Add-Result "Software" "Python" "FAIL" "Python not found"
        }
    } catch {
        Add-Result "Software" "Python" "FAIL" "Python not accessible"
    }
    
    # pip Package Manager
    try {
        $pipVersion = pip --version 2>$null
        if ($pipVersion) {
            Add-Result "Software" "pip" "PASS" "pip package manager available"
        } else {
            Add-Result "Software" "pip" "FAIL" "pip not available"
        }
    } catch {
        Add-Result "Software" "pip" "WARN" "Could not verify pip installation"
    }
    
    # Git Version Control
    try {
        $gitVersion = git --version 2>$null
        if ($gitVersion) {
            Add-Result "Software" "Git" "PASS" "$gitVersion detected"
        } else {
            Add-Result "Software" "Git" "FAIL" "Git not found"
        }
    } catch {
        Add-Result "Software" "Git" "FAIL" "Git not accessible"
    }
    
    # PostgreSQL Detection
    $pgService = Get-Service -Name "*postgresql*" -ErrorAction SilentlyContinue
    if ($pgService) {
        if ($pgService.Status -eq "Running") {
            Add-Result "Software" "PostgreSQL" "PASS" "PostgreSQL service running"
        } else {
            Add-Result "Software" "PostgreSQL" "WARN" "PostgreSQL installed but not running"
        }
    } else {
        Add-Result "Software" "PostgreSQL" "WARN" "PostgreSQL not detected"
    }
    
    # Redis Detection
    $redisService = Get-Service -Name "*redis*" -ErrorAction SilentlyContinue
    if ($redisService) {
        if ($redisService.Status -eq "Running") {
            Add-Result "Software" "Redis" "PASS" "Redis service running"
        } else {
            Add-Result "Software" "Redis" "WARN" "Redis installed but not running"
        }
    } else {
        Add-Result "Software" "Redis" "WARN" "Redis not detected"
    }
    
    # Chocolatey Package Manager
    try {
        $chocoVersion = choco --version 2>$null
        if ($chocoVersion) {
            Add-Result "Software" "Chocolatey" "PASS" "Chocolatey package manager available"
        } else {
            Add-Result "Software" "Chocolatey" "WARN" "Chocolatey not installed"
        }
    } catch {
        Add-Result "Software" "Chocolatey" "WARN" "Chocolatey not available"
    }
    
    # Docker Detection
    try {
        $dockerVersion = docker --version 2>$null
        if ($dockerVersion) {
            Add-Result "Software" "Docker" "INFO" "Docker available"
        }
    } catch {
        # Docker not critical for basic deployment
    }
}

function Test-NetworkEnvironment {
    Write-Host "`nNetwork Environment Analysis..." -ForegroundColor Cyan
    
    # Internet Connectivity
    try {
        $pingResult = Test-NetConnection -ComputerName "8.8.8.8" -Port 53 -InformationLevel Quiet -ErrorAction SilentlyContinue
        if ($pingResult) {
            Add-Result "Network" "Internet" "PASS" "Internet connection available"
        } else {
            Add-Result "Network" "Internet" "FAIL" "No internet connection"
        }
    } catch {
        Add-Result "Network" "Internet" "WARN" "Could not test internet connectivity"
    }
    
    # DNS Resolution
    try {
        $dnsTest = Resolve-DnsName -Name "github.com" -ErrorAction SilentlyContinue
        if ($dnsTest) {
            Add-Result "Network" "DNS" "PASS" "DNS resolution working"
        } else {
            Add-Result "Network" "DNS" "FAIL" "DNS resolution failed"
        }
    } catch {
        Add-Result "Network" "DNS" "WARN" "Could not test DNS resolution"
    }
    
    # Port Availability
    $commonPorts = @(80, 443, 8000, 6379)
    $busyPorts = 0
    
    foreach ($port in $commonPorts) {
        try {
            $portTest = Test-NetConnection -ComputerName "localhost" -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            if ($portTest) {
                $busyPorts++
            }
        } catch {
            # Port appears available
        }
    }
    
    if ($busyPorts -eq 0) {
        Add-Result "Network" "Ports" "PASS" "Common ports available"
    } else {
        Add-Result "Network" "Ports" "WARN" "$busyPorts common ports in use"
    }
}

function Test-ArmGuardEnvironment {
    Write-Host "`nArmGuard-Specific Environment..." -ForegroundColor Cyan
    
    # Project Files
    $projectRoot = Split-Path -Parent $PSScriptRoot
    $requiredFiles = @("manage.py", "requirements.txt", "core\\settings.py")
    
    $missingFiles = 0
    foreach ($file in $requiredFiles) {
        $filePath = Join-Path $projectRoot $file
        if (Test-Path $filePath) {
            Add-Result "ArmGuard" "Project Files" "PASS" "$file exists"
        } else {
            Add-Result "ArmGuard" "Project Files" "FAIL" "$file missing"
            $missingFiles++
        }
    }
    
    # Environment Configuration
    $envFile = Join-Path $projectRoot ".env"
    if (Test-Path $envFile) {
        Add-Result "ArmGuard" "Environment" "PASS" ".env configuration exists"
        
        # Validate critical variables
        $envContent = Get-Content $envFile
        $criticalVars = @("DJANGO_SECRET_KEY", "DB_NAME", "REDIS_PASSWORD")
        
        $missingVars = 0
        foreach ($var in $criticalVars) {
            $varLine = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=" }
            if ($varLine) {
                Add-Result "ArmGuard" "Config Variables" "PASS" "$var configured"
            } else {
                Add-Result "ArmGuard" "Config Variables" "FAIL" "$var not configured"
                $missingVars++
            }
        }
    } else {
        Add-Result "ArmGuard" "Environment" "FAIL" ".env file not found"
    }
    
    # Requirements File Check
    $requirementsFile = Join-Path $projectRoot "requirements.txt"
    if (Test-Path $requirementsFile) {
        Add-Result "ArmGuard" "Requirements" "PASS" "requirements.txt exists"
        
        # Check Django version
        $reqContent = Get-Content $requirementsFile
        $djangoLine = $reqContent | Where-Object { $_ -like "Django==*" }
        if ($djangoLine -like "*5.2.7*") {
            Add-Result "ArmGuard" "Django Version" "PASS" "Django 5.2.7 specified"
        } else {
            Add-Result "ArmGuard" "Django Version" "WARN" "Django version may not be optimal"
        }
    }
}

function Show-ValidationSummary {
    $totalTests = $script:VALIDATION_RESULTS.Count
    $passedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "PASS" }).Count
    $failedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count
    $warnTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }).Count
    $infoTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "INFO" }).Count
    
    Write-Host @"

===============================================================================
COMPREHENSIVE ENVIRONMENT VALIDATION SUMMARY
===============================================================================
Total Tests: $totalTests
[PASS] Passed: $passedTests
[FAIL] Failed: $failedTests
[WARN] Warnings: $warnTests  
[INFO] Information: $infoTests

"@ -ForegroundColor Cyan
    
    # Category breakdown
    $categories = $script:VALIDATION_RESULTS | Group-Object Category | Sort-Object Name
    
    Write-Host "Results by Category:" -ForegroundColor White
    foreach ($category in $categories) {
        $catPassed = ($category.Group | Where-Object { $_.Status -eq "PASS" }).Count
        $catFailed = ($category.Group | Where-Object { $_.Status -eq "FAIL" }).Count
        $catWarns = ($category.Group | Where-Object { $_.Status -eq "WARN" }).Count
        $catTotal = $category.Count
        
        $statusColor = if ($catFailed -eq 0 -and $catWarns -eq 0) { "Green" } 
                      elseif ($catFailed -eq 0) { "Yellow" } 
                      else { "Red" }
        
        Write-Host "  $($category.Name): $catPassed passed, $catFailed failed, $catWarns warnings" -ForegroundColor $statusColor
    }
    
    # Overall Assessment
    Write-Host "`nDeployment Readiness:" -ForegroundColor White
    
    if ($failedTests -eq 0) {
        if ($warnTests -eq 0) {
            Write-Host "[EXCELLENT] Ready for immediate deployment!" -ForegroundColor Green
        } else {
            Write-Host "[GOOD] Ready for deployment with minor optimizations" -ForegroundColor Yellow
        }
    } elseif ($failedTests -le 2) {
        Write-Host "[NEEDS ATTENTION] Fix issues before deployment" -ForegroundColor DarkYellow
    } else {
        Write-Host "[NOT READY] Multiple critical issues require resolution" -ForegroundColor Red
    }
    
    Write-Host "===============================================================================" -ForegroundColor Cyan
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    Write-Host @"

===============================================================================
ARMGUARD COMPREHENSIVE ENVIRONMENT VALIDATOR
===============================================================================
Complete hardware, OS, and software environment testing
===============================================================================

"@ -ForegroundColor Cyan

    $startTime = Get-Date
    
    # Run validation tests
    Test-HardwareEnvironment
    Test-OperatingSystem
    Test-SoftwareDependencies
    Test-NetworkEnvironment
    Test-ArmGuardEnvironment
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-Host "`nValidation completed in $([math]::Round($duration.TotalSeconds, 1)) seconds" -ForegroundColor Gray
    
    # Show summary
    Show-ValidationSummary
    
    # Return exit code
    $criticalFailures = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count
    if ($criticalFailures -eq 0) {
        Write-Host "`nSystem ready for deployment!" -ForegroundColor Green
        return 0
    } elseif ($criticalFailures -le 2) {
        Write-Host "`nMinor issues found - review before deployment." -ForegroundColor Yellow
        return 1
    } else {
        Write-Host "`nCritical issues found - resolve before deployment." -ForegroundColor Red
        return 2
    }
}

# Execute
$exitCode = Main
exit $exitCode