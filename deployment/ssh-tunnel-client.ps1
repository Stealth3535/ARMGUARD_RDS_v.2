# ArmGuard SSH Tunnel Client for Windows PowerShell
# Secure Internet Access via SSH Tunneling

param(
    [string]$ServerIP = "",
    [string]$ServerUser = "rds",
    [int]$LocalPort = 8000,
    [int]$RemotePort = 8000,
    [string]$Action = "menu"
)

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

Write-Host "🚇 ArmGuard SSH Tunnel Client (Windows)" -ForegroundColor $BLUE
Write-Host "========================================"

# Configuration
$SSHKeyPath = "$env:USERPROFILE\.ssh\armguard_access"
$TunnelInfoFile = "$env:USERPROFILE\.armguard_tunnel.json"

# Function to test if SSH is available
function Test-SSHAvailable {
    try {
        $sshVersion = ssh -V 2>&1
        return $true
    }
    catch {
        Write-Host "❌ SSH client not found. Please install OpenSSH:" -ForegroundColor $RED
        Write-Host "   Windows 10/11: Settings > Apps > Optional Features > Add 'OpenSSH Client'" -ForegroundColor $YELLOW
        Write-Host "   Or download from: https://github.com/PowerShell/Win32-OpenSSH/releases" -ForegroundColor $BLUE
        return $false
    }
}

# Function to setup SSH key
function Setup-SSHKey {
    if (!(Test-Path "$SSHKeyPath")) {
        Write-Host "🔑 Generating SSH key pair for secure access..." -ForegroundColor $YELLOW
        
        # Create .ssh directory if it doesn't exist
        $sshDir = Split-Path $SSHKeyPath
        if (!(Test-Path $sshDir)) {
            New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
        }
        
        # Generate SSH key
        $keyComment = "armguard-access-$(Get-Date -Format 'yyyyMMdd')"
        ssh-keygen -t ed25519 -f $SSHKeyPath -N '""' -C $keyComment
        
        if (Test-Path "$SSHKeyPath") {
            Write-Host "✅ SSH key generated: $SSHKeyPath" -ForegroundColor $GREEN
            Write-Host "📋 Copy this public key to your server:" -ForegroundColor $YELLOW
            Write-Host ""
            Get-Content "$SSHKeyPath.pub"
            Write-Host ""
            Write-Host "📝 Run on server: ssh-copy-id -i $SSHKeyPath.pub $ServerUser@$ServerIP" -ForegroundColor $BLUE
            Read-Host "Press Enter after copying the key to the server"
        }
        else {
            Write-Host "❌ Failed to generate SSH key" -ForegroundColor $RED
            return $false
        }
    }
    return $true
}

# Function to test SSH connection
function Test-SSHConnection {
    param([string]$ServerIP)
    
    Write-Host "🔍 Testing SSH connection..." -ForegroundColor $YELLOW
    
    try {
        $result = ssh -i $SSHKeyPath -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$ServerUser@$ServerIP" "echo 'SSH connection successful'" 2>$null
        if ($result -eq "SSH connection successful") {
            Write-Host "✅ SSH connection successful" -ForegroundColor $GREEN
            return $true
        }
    }
    catch {
        Write-Host "❌ SSH connection failed: $($_.Exception.Message)" -ForegroundColor $RED
        return $false
    }
    
    Write-Host "❌ SSH connection failed" -ForegroundColor $RED
    return $false
}

# Function to create tunnel
function New-SSHTunnel {
    param(
        [string]$ServerIP,
        [int]$LocalPort,
        [int]$RemotePort
    )
    
    Write-Host "🚇 Creating SSH tunnel..." -ForegroundColor $YELLOW
    Write-Host "Local port: $LocalPort -> Server: ${ServerIP}:${RemotePort}"
    
    # Stop existing tunnel first
    Stop-SSHTunnel
    
    # Create tunnel
    try {
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = "ssh"
        $processInfo.Arguments = "-i `"$SSHKeyPath`" -N -L ${LocalPort}:localhost:${RemotePort} ${ServerUser}@${ServerIP}"
        $processInfo.UseShellExecute = $false
        $processInfo.CreateNoWindow = $true
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        $process.Start()
        
        # Wait a moment to see if the process starts successfully
        Start-Sleep -Seconds 2
        
        if (!$process.HasExited) {
            Write-Host "✅ SSH tunnel created successfully (PID: $($process.Id))" -ForegroundColor $GREEN
            Write-Host "🌐 Access ArmGuard at: http://localhost:$LocalPort" -ForegroundColor $BLUE
            
            # Save tunnel info
            $tunnelInfo = @{
                PID = $process.Id
                LocalPort = $LocalPort
                Server = $ServerIP
                RemotePort = $RemotePort
                Created = (Get-Date).ToString()
            }
            $tunnelInfo | ConvertTo-Json | Set-Content $TunnelInfoFile
            
            return $true
        }
        else {
            Write-Host "❌ SSH tunnel process exited immediately" -ForegroundColor $RED
            return $false
        }
    }
    catch {
        Write-Host "❌ Failed to create SSH tunnel: $($_.Exception.Message)" -ForegroundColor $RED
        return $false
    }
}

# Function to stop tunnel
function Stop-SSHTunnel {
    if (Test-Path $TunnelInfoFile) {
        $tunnelInfo = Get-Content $TunnelInfoFile | ConvertFrom-Json
        
        try {
            $process = Get-Process -Id $tunnelInfo.PID -ErrorAction Stop
            $process.Kill()
            Write-Host "✅ Tunnel stopped (PID: $($tunnelInfo.PID))" -ForegroundColor $GREEN
        }
        catch {
            Write-Host "🔍 Tunnel process not found (may have already stopped)" -ForegroundColor $YELLOW
        }
        
        Remove-Item $TunnelInfoFile -Force
    }
    
    # Kill any SSH processes that might be tunneling
    Get-Process ssh -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*-L*localhost:*"
    } | ForEach-Object {
        $_.Kill()
        Write-Host "🔍 Cleaned up SSH tunnel process (PID: $($_.Id))" -ForegroundColor $YELLOW
    }
}

# Function to check tunnel status
function Get-TunnelStatus {
    if (Test-Path $TunnelInfoFile) {
        $tunnelInfo = Get-Content $TunnelInfoFile | ConvertFrom-Json
        
        try {
            $process = Get-Process -Id $tunnelInfo.PID -ErrorAction Stop
            Write-Host "✅ Tunnel is active (PID: $($tunnelInfo.PID))" -ForegroundColor $GREEN
            Write-Host "   Local: http://localhost:$($tunnelInfo.LocalPort)"
            Write-Host "   Server: $($tunnelInfo.Server):$($tunnelInfo.RemotePort)"
            Write-Host "   Created: $($tunnelInfo.Created)"
            
            # Test if the service is responding
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$($tunnelInfo.LocalPort)" -TimeoutSec 5 -ErrorAction Stop
                Write-Host "   🌐 ArmGuard is responding" -ForegroundColor $GREEN
            }
            catch {
                Write-Host "   ⚠️ Tunnel active but service not responding" -ForegroundColor $YELLOW
            }
        }
        catch {
            Write-Host "❌ Tunnel process not found" -ForegroundColor $RED
            Remove-Item $TunnelInfoFile -Force
        }
    }
    else {
        Write-Host "🔍 No active tunnel found" -ForegroundColor $YELLOW
    }
}

# Function to open browser
function Open-Browser {
    param([int]$Port = $LocalPort)
    
    $url = "http://localhost:$Port"
    Write-Host "🌐 Opening ArmGuard in browser..." -ForegroundColor $YELLOW
    Start-Process $url
}

# Function to show menu
function Show-Menu {
    Write-Host ""
    Write-Host "📋 SSH Tunnel Menu" -ForegroundColor $BLUE
    Write-Host "1. Connect to ArmGuard server"
    Write-Host "2. Stop tunnel"
    Write-Host "3. Check status"
    Write-Host "4. Setup SSH key"
    Write-Host "5. Open ArmGuard in browser"
    Write-Host "6. Exit"
    Write-Host ""
}

# Main script logic
if (!(Test-SSHAvailable)) {
    exit 1
}

# Handle command line parameters
switch ($Action.ToLower()) {
    "connect" {
        if ([string]::IsNullOrEmpty($ServerIP)) {
            Write-Host "❌ Server IP required for connect action" -ForegroundColor $RED
            Write-Host "Usage: .\ssh-tunnel-client.ps1 -ServerIP <ip> -Action connect" -ForegroundColor $BLUE
            exit 1
        }
        
        if (Setup-SSHKey) {
            if (Test-SSHConnection $ServerIP) {
                New-SSHTunnel $ServerIP $LocalPort $RemotePort
            }
        }
        exit 0
    }
    "stop" {
        Stop-SSHTunnel
        exit 0
    }
    "status" {
        Get-TunnelStatus
        exit 0
    }
    "open" {
        Open-Browser
        exit 0
    }
    "menu" {
        # Continue to interactive menu
    }
    default {
        Write-Host "🚇 ArmGuard SSH Tunnel Client (Windows)" -ForegroundColor $BLUE
        Write-Host ""
        Write-Host "Usage: .\ssh-tunnel-client.ps1 [parameters]" -ForegroundColor $BLUE
        Write-Host ""
        Write-Host "Parameters:"
        Write-Host "  -ServerIP <ip>     Server IP or hostname"
        Write-Host "  -ServerUser <user> SSH username (default: rds)"
        Write-Host "  -LocalPort <port>  Local port (default: 8000)"
        Write-Host "  -RemotePort <port> Remote port (default: 8000)"
        Write-Host "  -Action <action>   Action: connect, stop, status, open, menu"
        Write-Host ""
        Write-Host "Examples:"
        Write-Host "  .\ssh-tunnel-client.ps1 -ServerIP 203.0.113.1 -Action connect"
        Write-Host "  .\ssh-tunnel-client.ps1 -Action status"
        Write-Host "  .\ssh-tunnel-client.ps1 -Action menu"
        exit 0
    }
}

# Interactive menu mode
if ([string]::IsNullOrEmpty($ServerIP)) {
    Write-Host "🌐 Enter your public IP address or server hostname:" -ForegroundColor $YELLOW
    $ServerIP = Read-Host "Server IP/Hostname"
    
    if ([string]::IsNullOrEmpty($ServerIP)) {
        Write-Host "❌ Server IP is required" -ForegroundColor $RED
        exit 1
    }
}

while ($true) {
    Show-Menu
    $choice = Read-Host "Select option (1-6)"
    
    switch ($choice) {
        "1" {
            if (Setup-SSHKey) {
                if (Test-SSHConnection $ServerIP) {
                    New-SSHTunnel $ServerIP $LocalPort $RemotePort
                }
            }
        }
        "2" {
            Stop-SSHTunnel
        }
        "3" {
            Get-TunnelStatus
        }
        "4" {
            Setup-SSHKey
        }
        "5" {
            Open-Browser
        }
        "6" {
            Write-Host "👋 Goodbye!" -ForegroundColor $GREEN
            exit 0
        }
        default {
            Write-Host "❌ Invalid option" -ForegroundColor $RED
        }
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
}