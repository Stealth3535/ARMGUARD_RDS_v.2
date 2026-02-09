# ArmGuard Remote SSH Connection & Deployment Helper
# PowerShell version for Windows hosts

param(
    [string]$TargetHost = "192.168.0.1",
    [string]$SSHUser = "rds",
    [switch]$Help
)

if ($Help) {
    Write-Host @"
ArmGuard SSH Connection & Remote Deployment Helper

USAGE:
    .\ssh-helper.ps1 [-TargetHost <IP>] [-SSHUser <username>]
    
PARAMETERS:
    -TargetHost    Target IP address (default: 192.168.0.1)
    -SSHUser       SSH username (default: rds)
    -Help          Show this help message

EXAMPLES:
    .\ssh-helper.ps1                               # Use defaults
    .\ssh-helper.ps1 -TargetHost 192.168.1.100    # Different IP
    .\ssh-helper.ps1 -SSHUser admin                # Different user
"@
    exit 0
}

# Colors for Windows PowerShell
$Red = [System.ConsoleColor]::Red
$Green = [System.ConsoleColor]::Green
$Yellow = [System.ConsoleColor]::Yellow
$Blue = [System.ConsoleColor]::Blue
$Cyan = [System.ConsoleColor]::Cyan

function Write-ColorOutput {
    param([System.ConsoleColor]$ForegroundColor, [string]$Message)
    $originalColor = $Host.UI.RawUI.ForegroundColor
    $Host.UI.RawUI.ForegroundColor = $ForegroundColor
    Write-Output $Message
    $Host.UI.RawUI.ForegroundColor = $originalColor
}

function Write-Banner {
    Write-Output ""
    Write-ColorOutput $Blue "╔══════════════════════════════════════════════════════════════╗"
    Write-ColorOutput $Blue "║          SSH Connection & Remote Deployment Helper          ║"
    Write-ColorOutput $Blue "║                                                              ║"
    Write-ColorOutput $Blue "║  This script will:                                          ║"
    Write-ColorOutput $Blue "║  • Diagnose SSH connection issues                           ║"
    Write-ColorOutput $Blue "║  • Help enable SSH on the target system                    ║"
    Write-ColorOutput $Blue "║  • Deploy ArmGuard with Redis WebSocket optimization       ║"
    Write-ColorOutput $Blue "╚══════════════════════════════════════════════════════════════╝"
    Write-Output ""
}

function Test-NetworkConnectivity {
    Write-ColorOutput $Green "[INFO] Testing network connectivity to $TargetHost..."
    
    try {
        $pingResult = Test-Connection -ComputerName $TargetHost -Count 3 -Quiet -ErrorAction Stop
        if ($pingResult) {
            Write-ColorOutput $Green "✅ Network connectivity: GOOD"
            return $true
        }
    } catch {
        Write-ColorOutput $Red "❌ Network connectivity: FAILED"
        Write-Output "   The host $TargetHost is not reachable"
        return $false
    }
}

function Test-SSHPorts {
    Write-ColorOutput $Green "[INFO] Scanning for SSH services on common ports..."
    
    $SSHPorts = @(22, 2022, 2222, 22000, 22222)
    $foundSSH = $false
    
    foreach ($port in $SSHPorts) {
        Write-Host "  Checking port $port... " -NoNewline
        
        try {
            $connection = Test-NetConnection -ComputerName $TargetHost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
            if ($connection.TcpTestSucceeded) {
                Write-ColorOutput $Green "OPEN"
                Write-ColorOutput $Green "✅ Found potential SSH service on port $port"
                
                # Try SSH connection (if ssh command is available)
                if (Get-Command ssh -ErrorAction SilentlyContinue) {
                    Write-Output "  Testing SSH authentication..."
                    $sshTest = & ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $port "$SSHUser@$TargetHost" exit 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-ColorOutput $Green "✅ SSH authentication successful on port $port"
                        $script:SSHPort = $port
                        $foundSSH = $true
                        break
                    } else {
                        Write-ColorOutput $Yellow "⚠️  Port $port is open but SSH authentication failed"
                    }
                } else {
                    Write-ColorOutput $Yellow "⚠️  Port $port is open (SSH client not available to test auth)"
                    $script:SSHPort = $port
                    $foundSSH = $true
                    break
                }
            } else {
                Write-ColorOutput $Red "CLOSED"
            }
        } catch {
            Write-ColorOutput $Red "CLOSED"
        }
    }
    
    if (-not $foundSSH) {
        Write-ColorOutput $Red "❌ No accessible SSH service found on any common port"
        return $false
    }
    
    return $true
}

function Test-WebServices {
    Write-ColorOutput $Green "[INFO] Checking for HTTP/Web services..."
    
    # Test HTTP
    try {
        $httpResponse = Invoke-WebRequest -Uri "http://$TargetHost" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        Write-ColorOutput $Green "✅ HTTP service detected - might be a router, IoT device, or web server"
        
        if ($httpResponse.Content -match "router|login|admin|management") {
            Write-ColorOutput $Yellow "⚠️  Appears to be a router or management interface"
            Write-Output "   Try accessing http://$TargetHost in a web browser"
        }
    } catch {
        Write-Output "  HTTP service: Not accessible"
    }
    
    # Test HTTPS
    try {
        $httpsResponse = Invoke-WebRequest -Uri "https://$TargetHost" -TimeoutSec 5 -UseBasicParsing -SkipCertificateCheck -ErrorAction Stop 2>$null
        Write-ColorOutput $Green "✅ HTTPS service detected"
    } catch {
        Write-Output "  HTTPS service: Not accessible"
    }
}

function Show-SSHEnablementGuide {
    Write-Output ""
    Write-ColorOutput $Yellow "═══════════════════════════════════════════════════════════════"
    Write-ColorOutput $Yellow "SSH Service Not Found - How to Enable SSH"
    Write-ColorOutput $Yellow "═══════════════════════════════════════════════════════════════"
    Write-Output ""
    Write-Output "If $TargetHost is a Linux system, you can enable SSH by:"
    Write-Output ""
    
    Write-ColorOutput $Blue "Option 1: Physical Access"
    Write-Output "1. Connect keyboard/monitor to the system"
    Write-Output "2. Login locally and run these commands:"
    Write-Output ""
    Write-ColorOutput $Green "   # Ubuntu/Debian:"
    Write-Output "   sudo apt update"
    Write-Output "   sudo apt install openssh-server -y"
    Write-Output "   sudo systemctl enable ssh"
    Write-Output "   sudo systemctl start ssh"
    Write-Output ""
    Write-ColorOutput $Green "   # RHEL/CentOS/Fedora:"
    Write-Output "   sudo dnf install openssh-server -y"
    Write-Output "   sudo systemctl enable sshd"
    Write-Output "   sudo systemctl start sshd"
    Write-Output ""
    Write-ColorOutput $Green "   # Allow SSH through firewall:"
    Write-Output "   sudo ufw allow ssh                          # Ubuntu/Debian"
    Write-Output "   sudo firewall-cmd --permanent --add-service=ssh  # RHEL/CentOS"
    Write-Output "   sudo firewall-cmd --reload"
    Write-Output ""
    
    Write-ColorOutput $Blue "Option 2: Router/Network Admin Interface"
    Write-Output "1. Access your router admin panel (usually http://192.168.1.1 or 192.168.0.1)"
    Write-Output "2. Look for port forwarding or SSH settings"
    Write-Output "3. Enable SSH access if the router supports it"
    Write-Output ""
    
    Write-ColorOutput $Blue "Option 3: Raspberry Pi HDMI Method"
    Write-Output "If this is a Raspberry Pi:"
    Write-Output "1. Connect HDMI cable and keyboard"
    Write-Output "2. Enable SSH via: sudo systemctl enable ssh && sudo systemctl start ssh"
    Write-Output "3. Or via desktop: Raspberry Pi Configuration → Interfaces → SSH: Enable"
    Write-Output ""
    
    Write-ColorOutput $Blue "Option 4: Alternative Connection Methods"
    Write-Output "• VNC (if enabled): Use VNC Viewer to connect remotely"
    Write-Output "• Remote Desktop: If Windows/Linux desktop sharing is enabled"
    Write-Output "• Serial Console: If you have a USB serial adapter"
    Write-Output ""
}

function Deploy-ToRemote {
    if (-not $script:SSHPort) {
        Write-ColorOutput $Red "❌ No SSH port available for deployment"
        return
    }
    
    Write-ColorOutput $Green "[INFO] Preparing to deploy ArmGuard with Redis WebSocket optimization..."
    
    if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
        Write-ColorOutput $Red "❌ SSH client not found on this system"
        Write-Output "   Please install OpenSSH client or use WSL"
        return
    }
    
    if (-not (Get-Command scp -ErrorAction SilentlyContinue)) {
        Write-ColorOutput $Red "❌ SCP client not found on this system"
        Write-Output "   Please install OpenSSH client or use WSL"
        return
    }
    
    Write-Output "Deployment would run these commands:"
    Write-Output "1. scp -P $($script:SSHPort) -r deployment/ ${SSHUser}@${TargetHost}:~/armguard-deployment/"
    Write-Output "2. rsync or scp application files"
    Write-Output "3. ssh -p $($script:SSHPort) ${SSHUser}@${TargetHost} 'sudo ~/armguard-deployment/install-redis-websocket.sh --verbose'"
    Write-Output "4. ssh -p $($script:SSHPort) ${SSHUser}@${TargetHost} 'sudo ~/armguard-deployment/deploy-master.sh production'"
    Write-Output ""
    Write-ColorOutput $Yellow "⚠️  For actual deployment, use WSL with the bash script: ./remote-deployment-helper.sh"
}

# Main execution
function Main {
    Write-Banner
    
    Write-ColorOutput $Green "[INFO] Target: $SSHUser@$TargetHost"
    Write-Output ""
    
    # Step 1: Test basic connectivity
    if (-not (Test-NetworkConnectivity)) {
        Write-ColorOutput $Red "❌ Cannot proceed - target host is not reachable"
        exit 1
    }
    
    # Step 2: Scan for SSH services
    if (Test-SSHPorts) {
        Write-ColorOutput $Green "✅ SSH service found and accessible!"
        Write-Output ""
        
        $confirm = Read-Host "Deploy ArmGuard with Redis to $TargetHost? (y/N)"
        if ($confirm -match '^[Yy]') {
            Deploy-ToRemote
        } else {
            Write-Output "Deployment cancelled"
        }
    } else {
        # Step 3: System identification and troubleshooting
        Test-WebServices
        Show-SSHEnablementGuide
        
        Write-Output ""
        Write-ColorOutput $Cyan "Next Steps:"
        Write-Output "1. Enable SSH on $TargetHost using the methods above"
        Write-Output "2. Run this script again: .\ssh-helper.ps1"
        Write-Output "3. Or use WSL: ./remote-deployment-helper.sh"
        Write-Output "4. Or manually copy and run deployment scripts"
    }
}

# Run main function
Main