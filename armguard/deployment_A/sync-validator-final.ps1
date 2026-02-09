# ==============================================================================
# SYNC VALIDATION SYSTEM - DEPLOYMENT VERIFICATION
# ==============================================================================

Write-Host @"

===============================================================================
ARMGUARD SYNCHRONIZATION VALIDATOR
===============================================================================
Basic validation of deployment synchronization fixes
===============================================================================

"@ -ForegroundColor Cyan

$totalPassed = 0
$totalTests = 0

# Test 1: PowerShell Scripts
Write-Host "--- PowerShell Scripts ---" -ForegroundColor White
$scripts = @("deployment-helper.ps1", "01_setup.ps1", "02_config.ps1", "unified-env-generator.ps1")

foreach ($script in $scripts) {
    $totalTests++
    if (Test-Path $script) {
        Write-Host "[PASS] $script exists" -ForegroundColor Green
        $totalPassed++
    } else {
        Write-Host "[FAIL] $script not found" -ForegroundColor Red
    }
}

# Test 2: Environment File
Write-Host "`n--- Environment File ---" -ForegroundColor White
$envFile = "..\\.env"
$totalTests++
if (Test-Path $envFile) {
    Write-Host "[PASS] .env file exists" -ForegroundColor Green
    $totalPassed++
    
    # Check environment variables
    $envContent = Get-Content $envFile -ErrorAction SilentlyContinue
    $requiredVars = @("DJANGO_SECRET_KEY", "DB_NAME", "REDIS_PASSWORD")
    
    foreach ($var in $requiredVars) {
        $totalTests++
        $varLine = $envContent | Where-Object { $_ -like "$var=*" -and $_ -notlike "$var=" }
        if ($varLine) {
            Write-Host "[PASS] $var configured" -ForegroundColor Green
            $totalPassed++
        } else {
            Write-Host "[FAIL] $var missing or empty" -ForegroundColor Red
        }
    }
} else {
    Write-Host "[FAIL] .env file not found (run unified-env-generator.ps1)" -ForegroundColor Red
}

# Test 3: Requirements
Write-Host "`n--- Requirements ---" -ForegroundColor White
$reqFile = "..\requirements.txt"
$totalTests++
if (Test-Path $reqFile) {
    Write-Host "[PASS] requirements.txt exists" -ForegroundColor Green
    $totalPassed++
    
    $content = Get-Content $reqFile
    $djangoLine = $content | Where-Object { $_ -like "Django==*" }
    
    $totalTests++
    if ($djangoLine -like "*5.2.7*") {
        Write-Host "[PASS] Django version aligned (5.2.7)" -ForegroundColor Green
        $totalPassed++
    } else {
        Write-Host "[FAIL] Django version mismatch: $djangoLine" -ForegroundColor Red
    }
} else {
    Write-Host "[FAIL] requirements.txt not found" -ForegroundColor Red
}

# Test 4: Database Settings
Write-Host "`n--- Database Settings ---" -ForegroundColor White
$settingsFile = "..\core\settings_production.py"
$totalTests++
if (Test-Path $settingsFile) {
    Write-Host "[PASS] Production settings file exists" -ForegroundColor Green
    $totalPassed++
    
    $content = Get-Content $settingsFile -Raw
    $totalTests++
    if ($content -match "config\('DB_") {
        Write-Host "[PASS] Database uses environment variables" -ForegroundColor Green
        $totalPassed++
    } else {
        Write-Host "[FAIL] Database settings not environment-based" -ForegroundColor Red
    }
} else {
    Write-Host "[FAIL] Production settings not found" -ForegroundColor Red
}

# Test 5: Redis Settings
Write-Host "`n--- Redis Settings ---" -ForegroundColor White
$redisFile = "..\core\redis_settings.py"
$totalTests++
if (Test-Path $redisFile) {
    Write-Host "[PASS] Redis settings file exists" -ForegroundColor Green
    $totalPassed++
    
    $content = Get-Content $redisFile -Raw
    $totalTests++
    if ($content -match "REDIS_PASSWORD") {
        Write-Host "[PASS] Redis password authentication configured" -ForegroundColor Green
        $totalPassed++
    } else {
        Write-Host "[FAIL] Redis password not configured" -ForegroundColor Red
    }
} else {
    Write-Host "[FAIL] Redis settings not found" -ForegroundColor Red
}

# Summary
$failed = $totalTests - $totalPassed
$successRate = if ($totalTests -gt 0) { [math]::Round(($totalPassed / $totalTests) * 100, 1) } else { 0 }

Write-Host @"

===============================================================================
VALIDATION SUMMARY
===============================================================================
Total Tests: $totalTests
Passed: $totalPassed
Failed: $failed
Success Rate: $successRate%

"@ -ForegroundColor Cyan

if ($successRate -ge 80) {
    Write-Host "DEPLOYMENT READY: Good synchronization status!" -ForegroundColor Green
    $exitCode = 0
} elseif ($successRate -ge 60) {
    Write-Host "NEEDS ATTENTION: Some issues need fixing" -ForegroundColor Yellow
    $exitCode = 1
} else {
    Write-Host "CRITICAL ISSUES: Major synchronization problems" -ForegroundColor Red
    $exitCode = 2
}

Write-Host "`nNext Steps:" -ForegroundColor White
if (-not (Test-Path "..\\.env")) {
    Write-Host "1. Run: .\unified-env-generator.ps1 to create .env file" -ForegroundColor Yellow
}
if ($failed -gt 0) {
    Write-Host "2. Review failed tests and fix configuration issues" -ForegroundColor Yellow
}
if ($successRate -ge 80) {
    Write-Host "3. Ready to deploy! Run: .\deployment-helper.ps1" -ForegroundColor Green
}

exit $exitCode