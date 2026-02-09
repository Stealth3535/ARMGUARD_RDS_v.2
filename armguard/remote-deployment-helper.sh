#!/bin/bash

################################################################################
# SSH Connection and Remote Deployment Helper
# Helps diagnose SSH issues and deploy ArmGuard to remote systems
################################################################################

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

TARGET_HOST="192.168.0.1"
SSH_USER="rds"
SSH_PORTS=(22 2022 2222 22000 22222)

print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║          SSH Connection & Remote Deployment Helper          ║"  
    echo "║                                                              ║"
    echo "║  This script will:                                          ║"
    echo "║  • Diagnose SSH connection issues                           ║"
    echo "║  • Help enable SSH on the target system                    ║"
    echo "║  • Deploy ArmGuard with Redis WebSocket optimization       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo
}

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test network connectivity
test_connectivity() {
    log_info "Testing network connectivity to $TARGET_HOST..."
    
    if ping -c 3 $TARGET_HOST >/dev/null 2>&1; then
        log_info "✅ Network connectivity: GOOD"
        return 0
    else
        log_error "❌ Network connectivity: FAILED"
        echo "   The host $TARGET_HOST is not reachable"
        return 1
    fi
}

# Scan for open SSH ports
scan_ssh_ports() {
    log_info "Scanning for SSH services on common ports..."
    
    local found_ssh=false
    
    for port in "${SSH_PORTS[@]}"; do
        echo -n "  Checking port $port... "
        
        if timeout 5 bash -c "</dev/tcp/$TARGET_HOST/$port" 2>/dev/null; then
            echo -e "${GREEN}OPEN${NC}"
            log_info "✅ Found potential SSH service on port $port"
            
            # Try SSH connection
            if timeout 10 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -p $port $SSH_USER@$TARGET_HOST exit 2>/dev/null; then
                log_info "✅ SSH authentication successful on port $port"
                export SSH_PORT=$port
                found_ssh=true
                break
            else
                log_warn "⚠️  Port $port is open but SSH authentication failed"
            fi
        else
            echo -e "${RED}CLOSED${NC}"
        fi
    done
    
    if [ "$found_ssh" = false ]; then
        log_error "❌ No accessible SSH service found on any common port"
        return 1
    fi
    
    return 0
}

# Identify target system type
identify_system() {
    log_info "Attempting to identify target system type..."
    
    # Try HTTP to see if it's a web device
    if curl -s --connect-timeout 5 http://$TARGET_HOST >/dev/null 2>&1; then
        log_info "✅ HTTP service detected - might be a router, IoT device, or web server"
        
        # Check common router/device interfaces
        local response=$(curl -s --connect-timeout 3 http://$TARGET_HOST 2>/dev/null | head -100)
        if echo "$response" | grep -qi "router\|login\|admin\|management"; then
            log_warn "⚠️  Appears to be a router or management interface"
            log_info "   Try accessing http://$TARGET_HOST in a web browser"
        fi
    fi
    
    # Try HTTPS
    if curl -s -k --connect-timeout 5 https://$TARGET_HOST >/dev/null 2>&1; then
        log_info "✅ HTTPS service detected"
    fi
    
    # Check for common service ports
    local common_ports=(80 443 8080 8443 23 21 25 53 110 143 993 995)
    local found_services=()
    
    for port in "${common_ports[@]}"; do
        if timeout 2 bash -c "</dev/tcp/$TARGET_HOST/$port" 2>/dev/null; then
            found_services+=($port)
        fi
    done
    
    if [ ${#found_services[@]} -gt 0 ]; then
        log_info "Found services on ports: ${found_services[*]}"
    fi
}

# Generate SSH enablement instructions
show_ssh_enablement_guide() {
    cat << EOF

${YELLOW}═══════════════════════════════════════════════════════════════${NC}
${YELLOW}SSH Service Not Found - How to Enable SSH${NC}
${YELLOW}═══════════════════════════════════════════════════════════════${NC}

If $TARGET_HOST is a Linux system, you can enable SSH by:

${BLUE}Option 1: Physical Access${NC}
1. Connect keyboard/monitor to the system
2. Login locally and run these commands:

   ${GREEN}# Ubuntu/Debian:${NC}
   sudo apt update
   sudo apt install openssh-server -y
   sudo systemctl enable ssh
   sudo systemctl start ssh
   
   ${GREEN}# RHEL/CentOS/Fedora:${NC}
   sudo dnf install openssh-server -y  # or: yum install openssh-server -y
   sudo systemctl enable sshd
   sudo systemctl start sshd
   
   ${GREEN}# Allow SSH through firewall:${NC}
   sudo ufw allow ssh  # Ubuntu/Debian
   sudo firewall-cmd --permanent --add-service=ssh  # RHEL/CentOS/Fedora
   sudo firewall-cmd --reload

${BLUE}Option 2: Router/Network Admin Interface${NC}
1. Access your router admin panel (usually http://192.168.1.1 or 192.168.0.1)
2. Look for port forwarding or SSH settings
3. Enable SSH access if the router supports it

${BLUE}Option 3: Remote Desktop/VNC${NC}
If the system has VNC or remote desktop enabled:
1. Connect via VNC viewer
2. Enable SSH using the commands above

${BLUE}Option 4: Raspberry Pi HDMI Method${NC}
If this is a Raspberry Pi:
1. Connect HDMI cable and keyboard
2. Enable SSH via: sudo systemctl enable ssh && sudo systemctl start ssh
3. Or via desktop: Raspberry Pi Configuration → Interfaces → SSH: Enable

EOF
}

# Deploy ArmGuard with Redis to remote system
deploy_to_remote() {
    local ssh_port=${SSH_PORT:-22}
    
    log_info "Deploying ArmGuard with Redis WebSocket optimization to remote system..."
    
    # Copy deployment scripts
    log_info "Uploading deployment scripts..."
    scp -P $ssh_port -r deployment/ $SSH_USER@$TARGET_HOST:~/armguard-deployment/
    
    # Copy application files
    log_info "Uploading ArmGuard application..."
    rsync -avz -e "ssh -p $ssh_port" --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
        ./ $SSH_USER@$TARGET_HOST:~/armguard/
    
    # Execute remote deployment
    log_info "Executing remote deployment with Redis setup..."
    ssh -p $ssh_port $SSH_USER@$TARGET_HOST << 'EOF'
        # Make scripts executable
        chmod +x ~/armguard-deployment/install-redis-websocket.sh
        chmod +x ~/armguard-deployment/deploy-master.sh
        
        # Install Redis first
        echo "Installing Redis for WebSocket optimization..."
        sudo ~/armguard-deployment/install-redis-websocket.sh --verbose
        
        # Deploy ArmGuard
        echo "Deploying ArmGuard..."
        cd ~/armguard
        sudo ~/armguard-deployment/deploy-master.sh production
        
        echo "✅ ArmGuard deployment with Redis completed!"
EOF
    
    if [ $? -eq 0 ]; then
        log_info "✅ Remote deployment completed successfully!"
        echo
        echo -e "${GREEN}🎉 ArmGuard with Redis WebSocket optimization deployed to $TARGET_HOST${NC}"
        echo -e "${BLUE}   Access your application at: http://$TARGET_HOST${NC}"
        echo -e "${BLUE}   SSH access: ssh -p $ssh_port $SSH_USER@$TARGET_HOST${NC}"
    else
        log_error "❌ Remote deployment failed"
        return 1
    fi
}

# Main execution
main() {
    print_banner
    
    log_info "Target: $SSH_USER@$TARGET_HOST"
    echo
    
    # Step 1: Test basic connectivity
    if ! test_connectivity; then
        log_error "Cannot proceed - target host is not reachable"
        exit 1
    fi
    
    # Step 2: Scan for SSH services
    if scan_ssh_ports; then
        log_info "✅ SSH service found and accessible!"
        echo
        read -p "Deploy ArmGuard with Redis to $TARGET_HOST? (y/N): " confirm
        if [[ $confirm =~ ^[Yy] ]]; then
            deploy_to_remote
        else
            echo "Deployment cancelled"
        fi
    else
        # Step 3: System identification and troubleshooting
        identify_system
        show_ssh_enablement_guide
        
        echo
        echo -e "${CYAN}Next Steps:${NC}"
        echo "1. Enable SSH on $TARGET_HOST using the methods above"
        echo "2. Run this script again: ./remote-deployment-helper.sh"
        echo "3. Or manually copy and run deployment scripts"
    fi
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo "Diagnoses SSH connectivity and deploys ArmGuard with Redis optimization"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac