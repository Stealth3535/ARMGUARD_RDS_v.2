# ==============================================================================
# SYNC VALIDATION SYSTEM - DEPLOYMENT VERIFICATION
# ==============================================================================

# Simple validation functions
function Test-PowerShellScripts {
    Write-Host "Testing PowerShell Scripts..." -ForegroundColor Cyan
    
    $scripts = @("deployment-helper.ps1", "01_setup.ps1", "02_config.ps1", "unified-env-generator.ps1")
    $passed = 0
    
    foreach ($script in $scripts) {
        if (Test-Path $script) {
            Write-Host "[PASS] $script exists" -ForegroundColor Green
            $passed++
        } else {
            Write-Host "[FAIL] $script not found" -ForegroundColor Red
        }
    }
    
    return @{ Passed = $passed; Total = $scripts.Count }
}

function Test-EnvironmentFile {
    Write-Host "Testing Environment Configuration..." -ForegroundColor Cyan
    
    $envFile = ".\.env"
    if (Test-Path $envFile) {
        Write-Host "[PASS] .env file exists" -ForegroundColor Green
        
        $envContent = Get-Content $envFile -ErrorAction SilentlyContinue
        $requiredVars = @("DJANGO_SECRET_KEY", "DB_NAME", "REDIS_PASSWORD")
        
        $found = 0
        foreach ($var in $requiredVars) {
            $varLine = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=" }
            if ($varLine) {
                Write-Host "[PASS] $var configured" -ForegroundColor Green
                $found++
            } else {
                Write-Host "[FAIL] $var missing" -ForegroundColor Red
            }
        }
        
        return @{ Passed = $found + 1; Total = $requiredVars.Count + 1 }
    } else {
        Write-Host "[FAIL] .env file not found" -ForegroundColor Red
        return @{ Passed = 0; Total = 4 }
    }
}

function Test-Requirements {
    Write-Host "Testing Requirements..." -ForegroundColor Cyan
    
    $reqFile = "..\requirements.txt"
    if (Test-Path $reqFile) {
        $content = Get-Content $reqFile
        $djangoLine = $content | Where-Object { $_ -like "Django==*" }
        
        if ($djangoLine -like "*5.2.7*") {
            Write-Host "[PASS] Django version aligned (5.2.7)" -ForegroundColor Green
            return @{ Passed = 2; Total = 2 }
        } else {
            Write-Host "[FAIL] Django version mismatch: $djangoLine" -ForegroundColor Red
            return @{ Passed = 1; Total = 2 }
        }
    } else {
        Write-Host "[FAIL] requirements.txt not found" -ForegroundColor Red
        return @{ Passed = 0; Total = 2 }
    }
}

function Test-DatabaseSettings {
    Write-Host "Testing Database Settings..." -ForegroundColor Cyan
    
    $settingsFile = "..\core\settings_production.py"
    if (Test-Path $settingsFile) {
        Write-Host "[PASS] Production settings file exists" -ForegroundColor Green
        
        $content = Get-Content $settingsFile -Raw
        if ($content -match "config\('DB_") {
            Write-Host "[PASS] Database uses environment variables" -ForegroundColor Green
            return @{ Passed = 2; Total = 2 }
        } else {
            Write-Host "[FAIL] Database settings not environment-based" -ForegroundColor Red
            return @{ Passed = 1; Total = 2 }
        }
    } else {
        Write-Host "[FAIL] Production settings not found" -ForegroundColor Red
        return @{ Passed = 0; Total = 2 }
    }
}

function Test-RedisSettings {
    Write-Host "Testing Redis Settings..." -ForegroundColor Cyan
    
    $redisFile = "..\core\redis_settings.py"
    if (Test-Path $redisFile) {
        Write-Host "[PASS] Redis settings file exists" -ForegroundColor Green
        
        $content = Get-Content $redisFile -Raw
        if ($content -match "REDIS_PASSWORD") {
            Write-Host "[PASS] Redis password authentication configured" -ForegroundColor Green
            return @{ Passed = 2; Total = 2 }
        } else {
            Write-Host "[FAIL] Redis password not configured" -ForegroundColor Red
            return @{ Passed = 1; Total = 2 }
        }
    } else {
        Write-Host "[FAIL] Redis settings not found" -ForegroundColor Red
        return @{ Passed = 0; Total = 2 }
    }
}

# Main validation
function Main {
    Write-Host @"

===============================================================================
ARMGUARD SYNCHRONIZATION VALIDATOR
===============================================================================
Basic validation of deployment synchronization fixes
===============================================================================

"@ -ForegroundColor Cyan

    $allResults = @()
    
    # Run tests
    Write-Host "`n--- PowerShell Scripts ---" -ForegroundColor White
    $allResults += Test-PowerShellScripts
    
    Write-Host "`n--- Environment File ---" -ForegroundColor White
    $allResults += Test-EnvironmentFile
    
    Write-Host "`n--- Requirements ---" -ForegroundColor White
    $allResults += Test-Requirements
    
    Write-Host "`n--- Database Settings ---" -ForegroundColor White
    $allResults += Test-DatabaseSettings
    
    Write-Host "`n--- Redis Settings ---" -ForegroundColor White
    $allResults += Test-RedisSettings
    
    # Calculate totals
    $totalPassed = ($allResults | Measure-Object -Property Passed -Sum).Sum
    $totalTests = ($allResults | Measure-Object -Property Total -Sum).Sum
    $successRate = [math]::Round(($totalPassed / $totalTests) * 100, 1)
    
    # Summary
    Write-Host @"

===============================================================================
VALIDATION SUMMARY
===============================================================================
Total Tests: $totalTests
Passed: $totalPassed
Failed: $($totalTests - $totalPassed)
Success Rate: $successRate%

"@ -ForegroundColor Cyan

    if ($successRate -ge 80) {
        Write-Host "DEPLOYMENT READY: Good synchronization status!" -ForegroundColor Green
        return 0
    } elseif ($successRate -ge 60) {
        Write-Host "NEEDS ATTENTION: Some issues need fixing" -ForegroundColor Yellow
        return 1
    } else {
        Write-Host "CRITICAL ISSUES: Major synchronization problems" -ForegroundColor Red
        return 2
    }
}

# Execute
$exitCode = Main
exit $exitCode