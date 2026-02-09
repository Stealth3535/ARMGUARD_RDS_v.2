# ==============================================================================
# SYNC VALIDATION SYSTEM - COMPREHENSIVE DEPLOYMENT VERIFICATION
# ==============================================================================
# PURPOSE: Validates all synchronization fixes and deployment readiness  
# CHECKS: App-deployment alignment, configuration integrity, security compliance
# VERSION: 4.0.0 - Complete Synchronization Validation
# ==============================================================================

param(
    [switch]$Detailed = $false,
    [switch]$FixIssues = $false,
    [string]$ReportPath = ""
)

# ==============================================================================
# CONFIGURATION AND CONSTANTS  
# ==============================================================================

$script:SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:ARMGUARD_ROOT = Split-Path -Parent $script:SCRIPT_DIR
$script:VALIDATION_RESULTS = @()

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
# VALIDATION FRAMEWORK
# ==============================================================================

class ValidationResult {
    [string]$Category
    [string]$Test
    [string]$Status  # PASS, FAIL, WARN
    [string]$Message
    [string]$Details
    [string]$Recommendation
    
    ValidationResult([string]$category, [string]$test, [string]$status, [string]$message, [string]$details = "", [string]$recommendation = "") {
        $this.Category = $category
        $this.Test = $test
        $this.Status = $status
        $this.Message = $message
        $this.Details = $details
        $this.Recommendation = $recommendation
    }
}

function Add-ValidationResult {
    param(
        [string]$Category,
        [string]$Test,
        [string]$Status,
        [string]$Message,
        [string]$Details = "",
        [string]$Recommendation = ""
    )
    
    $result = [ValidationResult]::new($Category, $Test, $Status, $Message, $Details, $Recommendation)
    $script:VALIDATION_RESULTS += $result
    
    # Display result
    $color = switch ($Status) {
        "PASS" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    
    $icon = switch ($Status) {
        "PASS" { "[PASS]" }
        "FAIL" { "[FAIL]" }
        "WARN" { "[WARN]" }
        default { "[INFO]" }
    }
    
    Write-Host "$icon [$Category] $Test`: $Message" -ForegroundColor $color
    
    if ($script:Detailed -and $Details) {
        Write-Host "    Details: $Details" -ForegroundColor Gray
    }
    
    if ($Status -eq "FAIL" -and $Recommendation) {
        Write-Host "    💡 Recommendation: $Recommendation" -ForegroundColor Cyan
    }
}

# ==============================================================================
# CROSS-PLATFORM COMPATIBILITY VALIDATION
# ==============================================================================

function Test-CrossPlatformCompatibility {
    Write-Host "`n🔄 Testing Cross-Platform Compatibility..." -ForegroundColor Cyan
    
    # Check PowerShell scripts exist
    $psScripts = @("deployment-helper.ps1", "01_setup.ps1", "02_config.ps1", "unified-env-generator.ps1")
    
    foreach ($script in $psScripts) {
        $scriptPath = Join-Path $script:SCRIPT_DIR $script
        if (Test-Path $scriptPath) {
            Add-ValidationResult "Cross-Platform" "PowerShell Script" "PASS" "$script exists" 
        } else {
            Add-ValidationResult "Cross-Platform" "PowerShell Script" "FAIL" "$script not found" "" "Create PowerShell equivalent of bash script"
        }
    }
    
    # Check PowerShell version compatibility
    if ($PSVersionTable.PSVersion.Major -ge 5) {
        Add-ValidationResult "Cross-Platform" "PowerShell Version" "PASS" "PowerShell $($PSVersionTable.PSVersion.Major).x compatible"
    } else {
        Add-ValidationResult "Cross-Platform" "PowerShell Version" "FAIL" "PowerShell version too old" "Current: $($PSVersionTable.PSVersion)" "Upgrade to PowerShell 5.0 or newer"
    }
    
    # Check Windows compatibility features
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Add-ValidationResult "Cross-Platform" "Package Manager" "PASS" "Chocolatey package manager available"
    } else {
        Add-ValidationResult "Cross-Platform" "Package Manager" "WARN" "Chocolatey not installed" "" "Install Chocolatey for automated package management"
    }
}

# ==============================================================================
# ENVIRONMENT CONFIGURATION VALIDATION
# ==============================================================================

function Test-EnvironmentConfiguration {
    Write-Host "`n🔧 Testing Environment Configuration..." -ForegroundColor Cyan
    
    # Check unified environment generator exists
    $envGenerator = Join-Path $script:SCRIPT_DIR "unified-env-generator.ps1"
    if (Test-Path $envGenerator) {
        Add-ValidationResult "Environment" "Unified Generator" "PASS" "Unified environment generator available"
    } else {
        Add-ValidationResult "Environment" "Unified Generator" "FAIL" "Unified environment generator missing" "" "Create unified-env-generator.ps1"
    }
    
    # Check .env file exists and is complete
    $envFile = Join-Path $script:ARMGUARD_ROOT ".env"
    if (Test-Path $envFile) {
        Add-ValidationResult "Environment" ".env File" "PASS" ".env file exists"
        
        # Validate essential environment variables
        $envContent = Get-Content $envFile -ErrorAction SilentlyContinue
        $requiredVars = @(
            "DJANGO_SECRET_KEY", "DJANGO_DEBUG", "DJANGO_ALLOWED_HOSTS", 
            "DB_ENGINE", "DB_NAME", "DB_USER", "DB_PASSWORD",
            "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
            "SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE"
        )
        
        $missingVars = @()
        foreach ($var in $requiredVars) {
            $found = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=$" -and $_ -notlike "$var= " }
            if (-not $found) {
                $missingVars += $var
            }
        }
        
        if ($missingVars.Count -eq 0) {
            Add-ValidationResult "Environment" "Required Variables" "PASS" "All required environment variables present"
        } else {
            Add-ValidationResult "Environment" "Required Variables" "FAIL" "Missing environment variables" "Missing: $($missingVars -join ', ')" "Run unified-env-generator.ps1 to create complete configuration"
        }
    } else {
        Add-ValidationResult "Environment" ".env File" "FAIL" ".env file not found" "" "Run unified-env-generator.ps1 to create environment file"
    }
    
    # Check .env.example is up to date (template comparison)
    $envExample = Join-Path $script:ARMGUARD_ROOT ".env.example"
    if (Test-Path $envExample) {
        Add-ValidationResult "Environment" ".env.example" "PASS" ".env.example template exists"
        
        # Check if example file has all the new variables we expect
        $exampleContent = Get-Content $envExample
        $newVars = @("DB_SSL_MODE", "DB_CONN_MAX_AGE", "REDIS_PASSWORD", "NETWORK_TYPE")
        $hasNewVars = $true
        
        foreach ($var in $newVars) {
            $found = $exampleContent | Where-Object { $_ -like "*$var*" }
            if (-not $found) {
                $hasNewVars = $false
                break
            }
        }
        
        if ($hasNewVars) {
            Add-ValidationResult "Environment" ".env.example Content" "PASS" ".env.example includes new configuration options"
        } else {
            Add-ValidationResult "Environment" ".env.example Content" "WARN" ".env.example may be outdated" "" "Update .env.example with latest configuration options"
        }
    } else {
        Add-ValidationResult "Environment" ".env.example" "WARN" ".env.example template not found"
    }
}

# ==============================================================================
# DATABASE CONFIGURATION VALIDATION
# ==============================================================================

function Test-DatabaseConfiguration {
    Write-Host "`n🗄️ Testing Database Configuration..." -ForegroundColor Cyan
    
    # Check app settings include advanced PostgreSQL options
    $settingsFile = Join-Path $script:ARMGUARD_ROOT "core\settings.py"
    if (Test-Path $settingsFile) {
        $settingsContent = Get-Content $settingsFile -Raw
        
        # Check for advanced database features
        $advancedFeatures = @(
            "connect_timeout", "sslmode", "MAX_CONNS", 
            "cursor_factory", "CONN_MAX_AGE", "CONN_HEALTH_CHECKS"
        )
        
        $missingFeatures = @()
        foreach ($feature in $advancedFeatures) {
            if ($settingsContent -notlike "*$feature*") {
                $missingFeatures += $feature
            }
        }
        
        if ($missingFeatures.Count -eq 0) {
            Add-ValidationResult "Database" "Advanced Features" "PASS" "App includes advanced PostgreSQL configurations"
        } else {
            Add-ValidationResult "Database" "Advanced Features" "WARN" "Some advanced database features missing" "Missing: $($missingFeatures -join ', ')" "Update core/settings.py with complete PostgreSQL optimization"
        }
    }
    
    # Check production settings alignment
    $prodSettingsFile = Join-Path $script:ARMGUARD_ROOT "core\settings_production.py" 
    if (Test-Path $prodSettingsFile) {
        $prodContent = Get-Content $prodSettingsFile -Raw
        
        if ($prodContent -like "*USE_POSTGRESQL*default=True*") {
            Add-ValidationResult "Database" "Production Default" "PASS" "Production settings default to PostgreSQL"
        } else {
            Add-ValidationResult "Database" "Production Default" "FAIL" "Production settings don't default to PostgreSQL" "" "Update settings_production.py to use PostgreSQL by default"
        }
        
        # Check for environment variable support
        if ($prodContent -like "*config('DB_*") {
            Add-ValidationResult "Database" "Environment Integration" "PASS" "Production settings use environment variables"
        } else {
            Add-ValidationResult "Database" "Environment Integration" "FAIL" "Production settings use hardcoded values" "" "Update production settings to use environment variables"
        }
    } else {
        Add-ValidationResult "Database" "Production Settings" "WARN" "settings_production.py not found"
    }
}

# ==============================================================================
# REDIS SECURITY VALIDATION
# ==============================================================================

function Test-RedisConfiguration {
    Write-Host "`nTesting Redis Configuration..." -ForegroundColor Cyan
    
    # Check redis_settings.py uses environment variables
    $redisSettingsFile = Join-Path $script:ARMGUARD_ROOT "core\redis_settings.py"
    if (Test-Path $redisSettingsFile) {
        $redisContent = Get-Content $redisSettingsFile -Raw
        
        if ($redisContent -like "*config(*REDIS_*") {
            Add-ValidationResult "Redis" "Environment Integration" "PASS" "Redis settings use environment variables"
        } else {
            Add-ValidationResult "Redis" "Environment Integration" "FAIL" "Redis settings use hardcoded values" "" "Update redis_settings.py to use environment variables"
        }
        
        # Check for password authentication support
        if ($redisContent -like "*password*REDIS_CONFIG*") {
            Add-ValidationResult "Redis" "Password Authentication" "PASS" "Redis configured for password authentication"
        } else {
            Add-ValidationResult "Redis" "Password Authentication" "FAIL" "Redis not configured for password authentication" "" "Add password authentication to Redis configuration"
        }
        
        # Check for decouple import
        if ($redisContent -like "*from decouple import config*") {
            Add-ValidationResult "Redis" "Configuration Import" "PASS" "Redis settings import decouple for env vars"
        } else {
            Add-ValidationResult "Redis" "Configuration Import" "FAIL" "Missing decouple import" "" "Add 'from decouple import config' to redis_settings.py"
        }
    } else {
        Add-ValidationResult "Redis" "Settings File" "FAIL" "redis_settings.py not found" "" "Create redis_settings.py with environment variable support"
    }
}

# ==============================================================================
# REQUIREMENTS VALIDATION
# ==============================================================================

function Test-RequirementsSync {
    Write-Host "`n📦 Testing Requirements Synchronization..." -ForegroundColor Cyan
    
    # Check main requirements.txt
    $reqFile = Join-Path $script:ARMGUARD_ROOT "requirements.txt"
    if (Test-Path $reqFile) {
        $reqContent = Get-Content $reqFile
        
        # Check Django version alignment
        $djangoLine = $reqContent | Where-Object { $_ -like "Django==*" }
        if ($djangoLine -like "*Django==5.2.7*") {
            Add-ValidationResult "Requirements" "Django Version" "PASS" "Django version aligned (5.2.7)"
        } else {
            Add-ValidationResult "Requirements" "Django Version" "FAIL" "Django version misaligned" "Found: $djangoLine" "Update Django version to 5.2.7"
        }
        
        # Check Redis version
        $redisLine = $reqContent | Where-Object { $_ -like "redis==*" }
        if ($redisLine -like "*redis==5.0.1*") {
            Add-ValidationResult "Requirements" "Redis Version" "PASS" "Redis version aligned (5.0.1)"
        } else {
            Add-ValidationResult "Requirements" "Redis Version" "WARN" "Redis version inconsistent" "Found: $redisLine" "Standardize Redis version to 5.0.1"
        }
    } else {
        Add-ValidationResult "Requirements" "Main File" "FAIL" "requirements.txt not found"
    }
    
    # Check RPi requirements consistency
    $rpiReqFile = Join-Path $script:ARMGUARD_ROOT "requirements-rpi.txt"
    if (Test-Path $rpiReqFile) {
        $rpiContent = Get-Content $rpiReqFile
        $rpiRedisLine = $rpiContent | Where-Object { $_ -like "redis==*" }
        
        if ($rpiRedisLine -like "*redis==5.0.1*") {
            Add-ValidationResult "Requirements" "RPi Redis Sync" "PASS" "RPi requirements Redis version aligned"
        } else {
            Add-ValidationResult "Requirements" "RPi Redis Sync" "FAIL" "RPi Redis version misaligned" "Found: $rpiRedisLine" "Update RPi requirements to match main requirements"
        }
    }
}

# ==============================================================================
# STATIC/MEDIA PATH VALIDATION
# ==============================================================================

function Test-StaticMediaPaths {
    Write-Host "`n📁 Testing Static/Media Path Alignment..." -ForegroundColor Cyan
    
    # Check production settings paths
    $prodSettingsFile = Join-Path $script:ARMGUARD_ROOT "core\settings_production.py"
    if (Test-Path $prodSettingsFile) {
        $prodContent = Get-Content $prodSettingsFile -Raw
        
        if ($prodContent -like "*STATIC_ROOT = config('STATIC_ROOT'*") {
            Add-ValidationResult "Paths" "Static Root Config" "PASS" "Production settings use configurable static root"
        } else {
            Add-ValidationResult "Paths" "Static Root Config" "FAIL" "Static root path hardcoded in production" "" "Update to use environment variable for static root"
        }
        
        if ($prodContent -like "*MEDIA_ROOT = config('MEDIA_ROOT'*") {
            Add-ValidationResult "Paths" "Media Root Config" "PASS" "Production settings use configurable media root"
        } else {
            Add-ValidationResult "Paths" "Media Root Config" "FAIL" "Media root path hardcoded in production" "" "Update to use environment variable for media root"
        }
        
        # Check for production-appropriate default paths
        if ($prodContent -like "*'/var/www/armguard*" -or $prodContent -like "*'/www/armguard*") {
            Add-ValidationResult "Paths" "Production Paths" "PASS" "Production settings include system-level default paths"
        } else {
            Add-ValidationResult "Paths" "Production Paths" "WARN" "Production paths may not be system-level" "" "Consider using system paths like /var/www/armguard for production"
        }
    }
}

# ==============================================================================
# SERVICE DEPENDENCIES VALIDATION
# ==============================================================================

function Test-ServiceDependencies {
    Write-Host "`n🔧 Testing Service Dependencies..." -ForegroundColor Cyan
    
    # Check ASGI configuration
    $asgiFile = Join-Path $script:ARMGUARD_ROOT "core\asgi.py"
    if (Test-Path $asgiFile) {
        $asgiContent = Get-Content $asgiFile -Raw
        
        if ($asgiContent -like "*django.setup()*") {
            Add-ValidationResult "Services" "ASGI Setup" "PASS" "ASGI properly initializes Django"
        } else {
            Add-ValidationResult "Services" "ASGI Setup" "WARN" "ASGI may not properly initialize Django" "" "Ensure django.setup() is called in asgi.py"
        }
        
        if ($asgiContent -like "*AllowedHostsOriginValidator*") {
            Add-ValidationResult "Services" "WebSocket Security" "PASS" "WebSocket connections have host validation"
        } else {
            Add-ValidationResult "Services" "WebSocket Security" "WARN" "WebSocket host validation missing" "" "Add AllowedHostsOriginValidator to WebSocket routing"
        }
    }
    
    # Check if deployment scripts exist for service management
    $serviceScripts = @("03_services.ps1", "04_monitoring.ps1")
    $serviceScriptsExist = 0
    
    foreach ($script in $serviceScripts) {
        $scriptPath = Join-Path $script:SCRIPT_DIR $script
        if (Test-Path $scriptPath) {
            $serviceScriptsExist++
        }
    }
    
    if ($serviceScriptsExist -eq $serviceScripts.Count) {
        Add-ValidationResult "Services" "Deployment Scripts" "PASS" "Service management scripts available"
    } else {
        Add-ValidationResult "Services" "Deployment Scripts" "WARN" "Missing service management scripts" "Found: $serviceScriptsExist/$($serviceScripts.Count)" "Create PowerShell scripts for service management"
    }
}

# ==============================================================================
# COMPREHENSIVE VALIDATION REPORT
# ==============================================================================

function Show-ValidationSummary {
    Write-Host "`n═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "📊 SYNCHRONIZATION VALIDATION SUMMARY" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
    
    $totalTests = $script:VALIDATION_RESULTS.Count
    $passedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "PASS" }).Count
    $failedTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count  
    $warnTests = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }).Count
    
    Write-Host "Total Tests: $totalTests" -ForegroundColor White
    Write-Host "✅ Passed: $passedTests" -ForegroundColor Green
    Write-Host "❌ Failed: $failedTests" -ForegroundColor Red
    Write-Host "⚠️ Warnings: $warnTests" -ForegroundColor Yellow
    
    $successRate = if ($totalTests -gt 0) { [math]::Round(($passedTests / $totalTests) * 100, 1) } else { 0 }
    Write-Host "📈 Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } elseif ($successRate -ge 60) { "Yellow" } else { "Red" })
    
    # Category breakdown
    Write-Host "`n📋 Results by Category:" -ForegroundColor White
    $categories = $script:VALIDATION_RESULTS | Group-Object Category | Sort-Object Name
    
    foreach ($category in $categories) {
        $catPassed = ($category.Group | Where-Object { $_.Status -eq "PASS" }).Count
        $catTotal = $category.Count
        $catRate = [math]::Round(($catPassed / $catTotal) * 100, 0)
        
        $statusColor = if ($catRate -eq 100) { "Green" } elseif ($catRate -ge 75) { "Yellow" } else { "Red" }
        Write-Host "  $($category.Name): $catPassed/$catTotal ($catRate%)" -ForegroundColor $statusColor
    }
    
    # Deployment readiness assessment
    Write-Host "`n🚀 Deployment Readiness:" -ForegroundColor White
    if ($failedTests -eq 0) {
        Write-Host "✅ READY FOR DEPLOYMENT" -ForegroundColor Green
        Write-Host "All critical synchronization issues resolved." -ForegroundColor Green
    } elseif ($failedTests -le 3) {
        Write-Host "⚠️ DEPLOYMENT POSSIBLE WITH FIXES" -ForegroundColor Yellow
        Write-Host "Minor issues need resolution before production deployment." -ForegroundColor Yellow
    } else {
        Write-Host "❌ DEPLOYMENT NOT RECOMMENDED" -ForegroundColor Red
        Write-Host "Critical synchronization issues need resolution." -ForegroundColor Red
    }
    
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Export-ValidationReport {
    param([string]$FilePath)
    
    if (-not $FilePath) {
        $FilePath = Join-Path $script:SCRIPT_DIR "SYNC_VALIDATION_REPORT_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"
    }
    
    $report = @"
# 🔄 ArmGuard Synchronization Validation Report
**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  
**Total Tests:** $($script:VALIDATION_RESULTS.Count)

## 📊 Summary
- ✅ **Passed:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "PASS" }).Count)
- ❌ **Failed:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count)  
- ⚠️ **Warnings:** $(($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "WARN" }).Count)

## 📋 Detailed Results

"@

    $categories = $script:VALIDATION_RESULTS | Group-Object Category | Sort-Object Name
    
    foreach ($category in $categories) {
        $report += "`n### $($category.Name)`n`n"
        
        foreach ($result in $category.Group) {
            $icon = switch ($result.Status) {
                "PASS" { "✅" }
                "FAIL" { "❌" }
                "WARN" { "⚠️" }
                default { "ℹ️" }
            }
            
            $report += "**$icon $($result.Test):** $($result.Message)`n"
            
            if ($result.Details) {
                $report += "- *Details:* $($result.Details)`n"
            }
            
            if ($result.Recommendation) {
                $report += "- *Recommendation:* $($result.Recommendation)`n"
            }
            
            $report += "`n"
        }
    }
    
    Set-Content -Path $FilePath -Value $report -Encoding UTF8
    Write-Host "📄 Validation report exported to: $FilePath" -ForegroundColor Green
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    Write-Host @"

═══════════════════════════════════════════════════════════════
🔄 ARMGUARD SYNCHRONIZATION VALIDATOR
═══════════════════════════════════════════════════════════════
Comprehensive validation of app-deployment synchronization fixes
═══════════════════════════════════════════════════════════════

"@ -ForegroundColor Cyan

    # Run all validation tests
    Test-CrossPlatformCompatibility
    Test-EnvironmentConfiguration  
    Test-DatabaseConfiguration
    Test-RedisConfiguration
    Test-RequirementsSync
    Test-StaticMediaPaths
    Test-ServiceDependencies
    
    # Show summary
    Show-ValidationSummary
    
    # Export report if requested
    if ($script:ReportPath) {
        Export-ValidationReport -FilePath $script:ReportPath
    }
    
    # Return exit code based on results
    $criticalFailures = ($script:VALIDATION_RESULTS | Where-Object { $_.Status -eq "FAIL" }).Count
    if ($criticalFailures -eq 0) {
        return 0  # Success
    } else {
        return 1  # Issues found
    }
}

# Execute main function
$exitCode = Main
exit $exitCode