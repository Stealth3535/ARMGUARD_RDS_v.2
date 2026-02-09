# ==============================================================================
# 🎯 ARMGUARD DEPLOYMENT HELPER - POWERSHELL VERSION
# ==============================================================================
# Cross-platform deployment assistant for Windows PowerShell
# Provides interactive guidance for all deployment types
# Version: 4.0.0 - Windows Compatible
# ==============================================================================

param(
    [string]$Mode = "interactive",
    [string]$DeploymentType = "",
    [switch]$Quiet = $false,
    [switch]$Help = $false
)

# ==============================================================================
# CONFIGURATION AND CONSTANTS
# ==============================================================================

$script:SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:LOG_DIR = if ($env:EUID -eq 0) { "C:\logs\armguard-deploy" } else { "$env:LOCALAPPDATA\armguard-logs" }
$script:LOG_FILE = Join-Path $script:LOG_DIR "deployment-helper-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
$script:ARMGUARD_ROOT = Split-Path -Parent $script:SCRIPT_DIR

# Colors for PowerShell output
$script:Colors = @{
    RED = "Red"
    GREEN = "Green" 
    YELLOW = "Yellow"
    BLUE = "Blue"
    PURPLE = "Magenta"
    CYAN = "Cyan"
    WHITE = "White"
}

# Deployment configurations
$script:DEPLOYMENT_CONFIGS = @{
    "main" = @{
        name = "🚀 Main Deployment Scripts (95% of users)"
        description = "Systematic 4-script deployment with integrated network features"
        scripts = @("01_setup.ps1", "02_config.ps1", "03_services.ps1", "04_monitoring.ps1")
        use_case = "Production deployments, development setups, comprehensive installations"
        complexity = "Moderate - Guided configuration"
    }
    "production" = @{
        name = "🏢 Production Enterprise Deployment"  
        description = "Advanced production-ready deployment with enterprise features"
        scripts = @("methods\production\master-deploy.ps1")
        use_case = "Enterprise production environments requiring maximum security"
        complexity = "Advanced - Enterprise features"
    }
    "docker" = @{
        name = "🐳 Docker Testing Environment"
        description = "Complete containerized testing environment with monitoring"
        scripts = @("methods\docker-testing\run_all_tests.ps1") 
        use_case = "Development testing, CI/CD pipelines, containerized deployments"
        complexity = "Medium - Docker knowledge helpful"
    }
    "vmware" = @{
        name = "💻 VMware Deployment"
        description = "Optimized deployment for VMware virtual machines"
        scripts = @("methods\vmware-setup\vm-deploy.ps1")
        use_case = "VMware ESXi, VMware Workstation, virtual testing environments" 
        complexity = "Low - VM-specific optimizations"
    }
    "basic" = @{
        name = "⚡ Quick Basic Setup"
        description = "Minimal setup for development and testing"
        scripts = @("methods\basic-setup\serversetup.ps1")
        use_case = "Quick development setup, basic testing, learning the system"
        complexity = "Low - Minimal configuration"
    }
    "network" = @{
        name = "Network Security Setup"
        description = "Advanced network security with LAN/WAN isolation"
        scripts = @("02_config.ps1")
        use_case = "High-security environments requiring network isolation"
        complexity = "Advanced - Network administration knowledge required"
    }
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
    $logEntry = "[$timestamp] [$Level] $Message"
    
    # Write to console with color
    Write-Host "[$Level] $Message" -ForegroundColor $script:Colors[$Color]
    
    # Write to log file
    Add-Content -Path $script:LOG_FILE -Value $logEntry
}

function Log-Info { param([string]$Message) Write-Log $Message "INFO" "GREEN" }
function Log-Warn { param([string]$Message) Write-Log $Message "WARN" "YELLOW" }  
function Log-Error { param([string]$Message) Write-Log $Message "ERROR" "RED" }
function Log-Success { param([string]$Message) Write-Log $Message "SUCCESS" "CYAN" }

# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================

function Show-Help {
    Write-Host @"

🎯 ArmGuard Deployment Helper - Windows PowerShell Version

USAGE:
    .\deployment-helper.ps1 [OPTIONS]

OPTIONS:
    -Mode <interactive|quick|advanced>  Deployment mode (default: interactive)
    -DeploymentType <type>              Specify deployment type directly
    -Quiet                              Minimize output
    -Help                               Show this help

DEPLOYMENT TYPES:
    main        Main deployment scripts (recommended for most users)
    production  Enterprise production deployment
    docker      Docker containerized testing environment
    vmware      VMware virtual machine deployment
    basic       Quick basic setup for development
    network     Network isolation security setup

EXAMPLES:
    .\deployment-helper.ps1                                    # Interactive mode
    .\deployment-helper.ps1 -DeploymentType main              # Direct main deployment
    .\deployment-helper.ps1 -Mode quick -DeploymentType basic # Quick basic setup

For detailed documentation, see: deployment_A/README.md

"@
}

function Test-Prerequisites {
    Log-Info "Checking deployment prerequisites..."
    
    $issues = @()
    
    # Check PowerShell version
    if ($PSVersionTable.PSVersion.Major -lt 5) {
        $issues += "PowerShell 5.0+ required (current: $($PSVersionTable.PSVersion))"
    }
    
    # Check if running as administrator (for system-level changes)
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Log-Warn "Not running as Administrator - some features may be limited"
    }
    
    # Check Python availability
    try {
        $pythonVersion = python --version 2>$null
        if (-not $pythonVersion) {
            $issues += "Python not found - required for Django application"
        } else {
            Log-Info "Python detected: $pythonVersion"
        }
    } catch {
        $issues += "Python not accessible from PATH"
    }
    
    # Check Git availability
    try {
        $gitVersion = git --version 2>$null
        if ($gitVersion) {
            Log-Info "Git detected: $gitVersion"
        }
    } catch {
        Log-Warn "Git not found - may limit some deployment features"
    }
    
    if ($issues.Count -gt 0) {
        Log-Error "Prerequisites issues found:"
        foreach ($issue in $issues) {
            Log-Error "  • $issue"
        }
        return $false
    }
    
    Log-Success "All prerequisites satisfied"
    return $true
}

function Show-DeploymentOptions {
    Write-Host @"

═══════════════════════════════════════════════════════════════
🎯 ARMGUARD DEPLOYMENT OPTIONS
═══════════════════════════════════════════════════════════════

"@ -ForegroundColor Cyan

    $i = 1
    foreach ($key in $script:DEPLOYMENT_CONFIGS.Keys) {
        $config = $script:DEPLOYMENT_CONFIGS[$key]
        Write-Host "[$i] $($config.name)" -ForegroundColor White
        Write-Host "    $($config.description)" -ForegroundColor Gray
        Write-Host "    Use case: $($config.use_case)" -ForegroundColor DarkGray
        Write-Host "    Complexity: $($config.complexity)" -ForegroundColor DarkGray
        Write-Host ""
        $i++
    }
    
    Write-Host "═══════════════════════════════════════════════════════════════" -ForegroundColor Cyan
}

function Get-UserChoice {
    param(
        [string]$Prompt,
        [string[]]$ValidOptions,
        [string]$Default = ""
    )
    
    do {
        if ($Default) {
            $userInput = Read-Host "$Prompt [$Default]"
            if (-not $userInput) { $userInput = $Default }
        } else {
            $userInput = Read-Host $Prompt
        }
        
        if ($ValidOptions -contains $userInput) {
            return $userInput
        }
        
        Write-Host "Invalid option. Please choose from: $($ValidOptions -join ', ')" -ForegroundColor Red
    } while ($true)
}

function Invoke-DeploymentScript {
    param(
        [string]$ScriptPath,
        [hashtable]$Parameters = @{}
    )
    
    $fullPath = Join-Path $script:SCRIPT_DIR $ScriptPath
    
    if (-not (Test-Path $fullPath)) {
        Log-Error "Deployment script not found: $fullPath"
        return $false
    }
    
    Log-Info "Executing deployment script: $ScriptPath"
    
    try {
        if ($ScriptPath.EndsWith('.ps1')) {
            # PowerShell script
            & $fullPath @Parameters
        } else {
            # Try to run as PowerShell anyway (converted script)
            & $fullPath @Parameters
        }
        
        Log-Success "Deployment script completed successfully"
        return $true
    } catch {
        Log-Error "Deployment script failed: $($_.Exception.Message)"
        return $false
    }
}

function Start-InteractiveDeployment {
    Log-Info "Starting interactive deployment assistant..."
    
    Show-DeploymentOptions
    
    # Get user choice
    $choice = Get-UserChoice -Prompt "Select deployment option (1-6)" -ValidOptions @("1", "2", "3", "4", "5", "6")
    
    # Map choice to deployment type
    $deploymentTypes = @($script:DEPLOYMENT_CONFIGS.Keys)
    $selectedType = $deploymentTypes[$choice - 1]
    $config = $script:DEPLOYMENT_CONFIGS[$selectedType]
    
    Write-Host "`n🎯 Selected: $($config.name)" -ForegroundColor Cyan
    Write-Host "$($config.description)" -ForegroundColor Gray
    
    # Confirm selection
    $confirm = Get-UserChoice -Prompt "`nProceed with this deployment? (y/n)" -ValidOptions @("y", "n", "yes", "no") -Default "y"
    
    if ($confirm -in @("n", "no")) {
        Log-Info "Deployment cancelled by user"
        return
    }
    
    # Execute deployment
    Execute-Deployment -DeploymentType $selectedType
}

function Execute-Deployment {
    param([string]$DeploymentType)
    
    $config = $script:DEPLOYMENT_CONFIGS[$DeploymentType]
    if (-not $config) {
        Log-Error "Unknown deployment type: $DeploymentType"
        return
    }
    
    Log-Info "Starting $($config.name)..."
    
    # Execute deployment scripts
    foreach ($script in $config.scripts) {
        $success = Invoke-DeploymentScript -ScriptPath $script
        if (-not $success) {
            Log-Error "Deployment failed at script: $script"
            return
        }
    }
    
    Show-CompletionSummary -DeploymentType $DeploymentType
}

function Show-CompletionSummary {
    param([string]$DeploymentType)
    
    $config = $script:DEPLOYMENT_CONFIGS[$DeploymentType]
    
    Write-Host @"

═══════════════════════════════════════════════════════════════
🎉 DEPLOYMENT COMPLETED SUCCESSFULLY!
═══════════════════════════════════════════════════════════════

Deployment Type: $($config.name)
Completion Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')

Next Steps:
1. 📋 Review deployment logs: $script:LOG_FILE
2. 🔧 Test application functionality
3. 🔐 Verify security configurations
4. 📖 Check documentation for post-deployment steps

Support:
- Documentation: deployment_A/README.md
- Troubleshooting: deployment_A/docs_archive/
- Log Files: $script:LOG_DIR

═══════════════════════════════════════════════════════════════

"@ -ForegroundColor Green
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    # Initialize logging
    Ensure-LogDir
    
    if ($Help) {
        Show-Help
        return
    }
    
    Log-Info "ArmGuard Deployment Helper started - PowerShell Version"
    
    # Check prerequisites
    if (-not (Test-Prerequisites)) {
        Log-Error "Prerequisites check failed. Please resolve issues before continuing."
        return
    }
    
    # Execute based on mode
    if ($DeploymentType) {
        # Direct deployment
        Execute-Deployment -DeploymentType $DeploymentType
    } elseif ($Mode -eq "interactive" -or -not $Mode) {
        # Interactive mode (default)
        Start-InteractiveDeployment
    } else {
        Log-Error "Unknown mode: $Mode"
        Show-Help
    }
}

# Execute main function
Main