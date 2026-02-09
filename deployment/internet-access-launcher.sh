#!/bin/bash
# ===========================================
# ArmGuard Internet Access Setup Launcher
# Choose the right security approach
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌐 ArmGuard Internet Access Setup${NC}"
echo -e "${CYAN}Choose Your Security Approach${NC}"
echo "=========================================="

# Function to show security comparison
show_security_comparison() {
    echo ""
    echo -e "${BLUE}🛡️ Security Comparison${NC}"
    echo "┌─────────────────┬─────────────┬─────────────────┬──────────────────┐"
    echo "│ Approach        │ Security    │ Complexity      │ Best For         │"
    echo "├─────────────────┼─────────────┼─────────────────┼──────────────────┤"
    echo -e "│ VPN Server      │ ${GREEN}Excellent${NC}   │ ${YELLOW}Medium${NC}          │ Multiple users   │"
    echo -e "│ SSH Tunnel      │ ${GREEN}Excellent${NC}   │ ${GREEN}Low${NC}             │ Single user      │"
    echo -e "│ HTTPS Direct    │ ${RED}Moderate${NC}    │ ${RED}High${NC}            │ Public access    │"
    echo "└─────────────────┴─────────────┴─────────────────┴──────────────────┘"
    echo ""
}

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"
    
    # Check if running on Ubuntu server
    if ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
        echo -e "${YELLOW}⚠️ This script is optimized for Ubuntu Server${NC}"
    fi
    
    # Check if running as root for some operations
    if [ "$EUID" -ne 0 ] && [ "$1" != "ssh-client" ]; then
        echo -e "${RED}❌ Some operations require root privileges${NC}"
        echo "Please run with: sudo $0"
        exit 1
    fi
    
    # Check internet connection
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        echo -e "${RED}❌ No internet connection detected${NC}"
        exit 1
    fi
    
    # Check if ArmGuard is installed
    if [ ! -d "/home/rds/ARMGUARD_RDS_v.2" ]; then
        echo -e "${YELLOW}⚠️ ArmGuard not found in expected location${NC}"
        echo "Expected: /home/rds/ARMGUARD_RDS_v.2"
        read -p "Continue anyway? (y/N): " continue_anyway
        if [ "$continue_anyway" != "y" ] && [ "$continue_anyway" != "Y" ]; then
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Function to get public IP
get_public_ip() {
    echo -e "${YELLOW}🌐 Detecting public IP address...${NC}"
    PUBLIC_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "")
    
    if [ -n "$PUBLIC_IP" ]; then
        echo -e "${GREEN}✅ Public IP detected: $PUBLIC_IP${NC}"
        echo -e "${BLUE}💡 You'll need to forward ports to: 192.168.0.10${NC}"
    else
        echo -e "${YELLOW}⚠️ Could not detect public IP automatically${NC}"
        read -p "Enter your public IP address: " PUBLIC_IP
    fi
}

# Function to show router configuration
show_router_config() {
    local service="$1"
    local port="$2"
    local protocol="$3"
    
    echo ""
    echo -e "${BLUE}🌐 Router Configuration Required${NC}"
    echo "=================================="
    echo "Service: $service"
    echo "External Port: $port"
    echo "Internal IP: 192.168.0.10"
    echo "Internal Port: $port"
    echo "Protocol: $protocol"
    echo ""
    echo -e "${YELLOW}📋 Router Setup Steps:${NC}"
    echo "1. Open router admin panel (usually 192.168.1.1 or 192.168.0.1)"
    echo "2. Find 'Port Forwarding' or 'NAT' settings"
    echo "3. Add the above port forwarding rule"
    echo "4. Save and reboot router if needed"
    echo ""
}

# Main menu
show_main_menu() {
    echo ""
    echo -e "${CYAN}📋 Choose Your Approach${NC}"
    echo "1. 🔐 VPN Server Setup (Most Secure - Recommended)"
    echo "2. 🚇 SSH Tunnel Client (Simple & Secure)"
    echo "3. 🌐 HTTPS Direct Access (⚠️ Security Risk)"
    echo "4. 📊 Show Security Comparison"
    echo "5. 🔧 System Information"
    echo "6. ❓ Help & Documentation"
    echo "7. 🚪 Exit"
    echo ""
}

# VPN setup function
setup_vpn_server() {
    echo -e "${GREEN}🔐 Setting Up VPN Server${NC}"
    echo "=========================="
    
    get_public_ip
    show_router_config "VPN (WireGuard)" "51820" "UDP"
    
    read -p "Continue with VPN server setup? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        if [ -f "./deployment/setup-vpn-server.sh" ]; then
            chmod +x ./deployment/setup-vpn-server.sh
            ./deployment/setup-vpn-server.sh
        else
            echo -e "${RED}❌ VPN setup script not found${NC}"
            echo "Please ensure you're running from the ARMGUARD_RDS_v.2 directory"
        fi
    fi
}

# SSH tunnel setup function
setup_ssh_tunnel() {
    echo -e "${CYAN}🚇 SSH Tunnel Client Setup${NC}"
    echo "==========================="
    
    get_public_ip
    show_router_config "SSH" "22" "TCP"
    
    echo -e "${BLUE}💡 SSH Tunnel Benefits:${NC}"
    echo "• No direct internet exposure"
    echo "• Uses existing SSH infrastructure"
    echo "• Works from anywhere"
    echo "• Simple one-command setup"
    echo ""
    
    echo -e "${YELLOW}📋 Next Steps:${NC}"
    echo "1. Forward SSH port 22 to your server"
    echo "2. Use the SSH tunnel client:"
    echo ""
    echo -e "${GREEN}Linux/macOS:${NC}"
    echo "./deployment/ssh-tunnel-client.sh connect $PUBLIC_IP"
    echo ""
    echo -e "${GREEN}Windows PowerShell:${NC}"
    echo ".\\deployment\\ssh-tunnel-client.ps1 -ServerIP $PUBLIC_IP -Action connect"
    echo ""
    
    # Make script executable
    if [ -f "./deployment/ssh-tunnel-client.sh" ]; then
        chmod +x ./deployment/ssh-tunnel-client.sh
        echo -e "${GREEN}✅ SSH tunnel client is ready${NC}"
    fi
}

# HTTPS direct setup function
setup_https_direct() {
    echo -e "${RED}⚠️ HTTPS Direct Access Setup${NC}"
    echo "=============================="
    
    echo -e "${RED}WARNING: This exposes ArmGuard directly to the internet!${NC}"
    echo -e "${YELLOW}Recommended: Use VPN or SSH tunnel instead.${NC}"
    echo ""
    echo -e "${BLUE}🛡️ Security measures included:${NC}"
    echo "• SSL/HTTPS encryption"
    echo "• Fail2ban attack protection"
    echo "• Nginx rate limiting"
    echo "• Firewall configuration"
    echo "• Security headers"
    echo ""
    
    get_public_ip
    show_router_config "HTTPS & HTTP" "8443, 80" "TCP"
    
    echo -e "${RED}⚠️ Security Acknowledgment Required${NC}"
    echo "By proceeding, you acknowledge:"
    echo "1. This increases security risks"
    echo "2. Regular monitoring is required"
    echo "3. Strong passwords are essential"
    echo "4. VPN/SSH tunnel is preferred"
    echo ""
    
    read -p "Type 'I UNDERSTAND THE RISKS' to continue: " risk_acknowledgment
    if [ "$risk_acknowledgment" = "I UNDERSTAND THE RISKS" ]; then
        if [ -f "./deployment/setup-https-direct.sh" ]; then
            chmod +x ./deployment/setup-https-direct.sh
            ./deployment/setup-https-direct.sh
        else
            echo -e "${RED}❌ HTTPS setup script not found${NC}"
        fi
    else
        echo -e "${YELLOW}❌ Setup cancelled - Risk acknowledgment required${NC}"
    fi
}

# System information function
show_system_info() {
    echo -e "${BLUE}🔧 System Information${NC}"
    echo "===================="
    echo ""
    echo -e "${CYAN}Server Details:${NC}"
    echo "OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
    echo "Kernel: $(uname -r)"
    echo "Architecture: $(uname -m)"
    echo ""
    
    echo -e "${CYAN}Network Configuration:${NC}"
    echo "Local IP: $(hostname -I | awk '{print $1}')"
    echo "Public IP: $(curl -s ifconfig.me || echo 'Unable to detect')"
    echo ""
    
    echo -e "${CYAN}Service Status:${NC}"
    systemctl is-active --quiet ssh && echo -e "SSH: ${GREEN}Running${NC}" || echo -e "SSH: ${RED}Stopped${NC}"
    
    if systemctl is-active --quiet armguard; then
        echo -e "ArmGuard: ${GREEN}Running${NC}"
    else
        echo -e "ArmGuard: ${YELLOW}Not installed/stopped${NC}"
    fi
    
    if command -v wg &> /dev/null; then
        if systemctl is-active --quiet wg-quick@wg0; then
            echo -e "VPN Server: ${GREEN}Running${NC}"
        else
            echo -e "VPN Server: ${YELLOW}Installed but stopped${NC}"
        fi
    else
        echo -e "VPN Server: ${YELLOW}Not installed${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Disk Usage:${NC}"
    df -h / | tail -n 1 | awk '{print "Root: " $5 " used (" $3 "/" $2 ")"}'
    
    echo ""
    echo -e "${CYAN}Memory Usage:${NC}"
    free -h | grep Mem | awk '{print "RAM: " $3 "/" $2 " (" int($3/$2 * 100) "% used)"}'
}

# Help and documentation function
show_help() {
    echo -e "${BLUE}❓ Help & Documentation${NC}"
    echo "======================="
    echo ""
    echo -e "${CYAN}📚 Available Documentation:${NC}"
    echo "• Complete Internet Access Guide: deployment/COMPLETE_INTERNET_ACCESS_GUIDE.md"
    echo "• Quick Start Guide: deployment/INTERNET_ACCESS_GUIDE.md"
    echo "• GitHub Repository: https://github.com/Stealth3535/ARMGUARD_RDS_v.2"
    echo ""
    
    echo -e "${CYAN}🛠️ Available Scripts:${NC}"
    echo "• VPN Server: deployment/setup-vpn-server.sh"
    echo "• SSH Tunnel (Linux): deployment/ssh-tunnel-client.sh"  
    echo "• SSH Tunnel (Windows): deployment/ssh-tunnel-client.ps1"
    echo "• HTTPS Direct: deployment/setup-https-direct.sh"
    echo ""
    
    echo -e "${CYAN}📞 Support:${NC}"
    echo "• Create issues on GitHub for bugs or questions"
    echo "• Check existing documentation for common solutions"
    echo "• Review logs for troubleshooting information"
    echo ""
    
    echo -e "${CYAN}🔍 Troubleshooting Commands:${NC}"
    echo "• Check services: systemctl status [service-name]"
    echo "• View logs: journalctl -f -u [service-name]"
    echo "• Network test: ping 8.8.8.8"
    echo "• Port check: netstat -tulpn | grep [port]"
}

# Main script execution
main() {
    # Handle command line arguments
    case "$1" in
        "vpn")
            check_prerequisites
            setup_vpn_server
            exit 0
            ;;
        "ssh")
            check_prerequisites ssh-client
            setup_ssh_tunnel
            exit 0
            ;;
        "https")
            check_prerequisites
            setup_https_direct
            exit 0
            ;;
        "info")
            show_system_info
            exit 0
            ;;
        "help")
            show_help
            exit 0
            ;;
    esac
    
    # Interactive mode
    while true; do
        show_main_menu
        read -p "Select option (1-7): " choice
        
        case $choice in
            1)
                check_prerequisites
                setup_vpn_server
                ;;
            2)
                check_prerequisites ssh-client
                setup_ssh_tunnel
                ;;
            3)
                check_prerequisites
                setup_https_direct
                ;;
            4)
                show_security_comparison
                ;;
            5)
                show_system_info
                ;;
            6)
                show_help
                ;;
            7)
                echo -e "${GREEN}👋 Setup complete! Check the documentation for next steps.${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Invalid option${NC}"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Command line usage
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo -e "${BLUE}🌐 ArmGuard Internet Access Setup Launcher${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  vpn     - Setup VPN server (requires root)"
    echo "  ssh     - Setup SSH tunnel client"
    echo "  https   - Setup HTTPS direct access (requires root)"
    echo "  info    - Show system information"
    echo "  help    - Show help and documentation"
    echo ""
    echo "Interactive mode: $0 (no arguments)"
    exit 0
fi

# Run main function
main "$@"