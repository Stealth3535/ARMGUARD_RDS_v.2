#!/bin/bash
# ===========================================
# ArmGuard SSH Tunnel Client Script
# Secure Internet Access via SSH Tunneling
# ===========================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default configuration
DEFAULT_SERVER_IP=""
DEFAULT_SERVER_USER="rds"
DEFAULT_LOCAL_PORT="8000"
DEFAULT_REMOTE_PORT="8000"
SSH_KEY_PATH="$HOME/.ssh/armguard_access"

echo -e "${BLUE}🚇 ArmGuard SSH Tunnel Client${NC}"
echo "================================"

# Function to create SSH key if it doesn't exist
setup_ssh_key() {
    if [ ! -f "$SSH_KEY_PATH" ]; then
        echo -e "${YELLOW}🔑 Generating SSH key pair for secure access...${NC}"
        ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "armguard-access-$(date +%Y%m%d)"
        echo -e "${GREEN}✅ SSH key generated: $SSH_KEY_PATH${NC}"
        echo -e "${YELLOW}📋 Copy this public key to your server:${NC}"
        echo ""
        cat "$SSH_KEY_PATH.pub"
        echo ""
        echo -e "${BLUE}📝 Run on server: ssh-copy-id -i $SSH_KEY_PATH.pub $DEFAULT_SERVER_USER@$DEFAULT_SERVER_IP${NC}"
        read -p "Press Enter after copying the key to the server..."
    fi
}

# Function to test SSH connection
test_ssh_connection() {
    echo -e "${YELLOW}🔍 Testing SSH connection...${NC}"
    if ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=10 "$DEFAULT_SERVER_USER@$1" "echo 'SSH connection successful'" 2>/dev/null; then
        echo -e "${GREEN}✅ SSH connection successful${NC}"
        return 0
    else
        echo -e "${RED}❌ SSH connection failed${NC}"
        return 1
    fi
}

# Function to create tunnel
create_tunnel() {
    local server_ip="$1"
    local local_port="$2"
    local remote_port="$3"
    
    echo -e "${YELLOW}🚇 Creating SSH tunnel...${NC}"
    echo "Local port: $local_port -> Server: $server_ip:$remote_port"
    
    # Kill existing tunnels on the same port
    pkill -f "ssh.*-L $local_port:localhost:$remote_port" 2>/dev/null || true
    
    # Create tunnel in background
    ssh -i "$SSH_KEY_PATH" -N -L "$local_port:localhost:$remote_port" "$DEFAULT_SERVER_USER@$server_ip" &
    TUNNEL_PID=$!
    
    # Wait a moment and test if tunnel is active
    sleep 2
    if kill -0 $TUNNEL_PID 2>/dev/null; then
        echo -e "${GREEN}✅ SSH tunnel created successfully (PID: $TUNNEL_PID)${NC}"
        echo -e "${BLUE}🌐 Access ArmGuard at: http://localhost:$local_port${NC}"
        
        # Create tunnel info file
        cat > "$HOME/.armguard_tunnel" << EOF
PID=$TUNNEL_PID
LOCAL_PORT=$local_port
SERVER=$server_ip
REMOTE_PORT=$remote_port
CREATED=$(date)
EOF
        
        return 0
    else
        echo -e "${RED}❌ Failed to create SSH tunnel${NC}"
        return 1
    fi
}

# Function to stop tunnel
stop_tunnel() {
    if [ -f "$HOME/.armguard_tunnel" ]; then
        source "$HOME/.armguard_tunnel"
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo -e "${GREEN}✅ Tunnel stopped (PID: $PID)${NC}"
        fi
        rm -f "$HOME/.armguard_tunnel"
    else
        # Kill any SSH tunnels that might be running
        pkill -f "ssh.*-L.*localhost:" 2>/dev/null || true
        echo -e "${YELLOW}🔍 Cleaned up any existing tunnels${NC}"
    fi
}

# Function to check tunnel status
check_status() {
    if [ -f "$HOME/.armguard_tunnel" ]; then
        source "$HOME/.armguard_tunnel"
        if kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}✅ Tunnel is active (PID: $PID)${NC}"
            echo "   Local: http://localhost:$LOCAL_PORT"
            echo "   Server: $SERVER:$REMOTE_PORT"
            echo "   Created: $CREATED"
            
            # Test if the service is responding
            if curl -s --connect-timeout 5 "http://localhost:$LOCAL_PORT" > /dev/null; then
                echo -e "${GREEN}   🌐 ArmGuard is responding${NC}"
            else
                echo -e "${YELLOW}   ⚠️ Tunnel active but service not responding${NC}"
            fi
        else
            echo -e "${RED}❌ Tunnel process not found${NC}"
            rm -f "$HOME/.armguard_tunnel"
        fi
    else
        echo -e "${YELLOW}🔍 No active tunnel found${NC}"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo -e "${BLUE}📋 SSH Tunnel Menu${NC}"
    echo "1. Connect to ArmGuard server"
    echo "2. Stop tunnel"
    echo "3. Check status"
    echo "4. Setup SSH key"
    echo "5. Open ArmGuard in browser"
    echo "6. Exit"
    echo ""
}

# Browser opener
open_browser() {
    local url="http://localhost:$DEFAULT_LOCAL_PORT"
    echo -e "${YELLOW}🌐 Opening ArmGuard in browser...${NC}"
    
    if command -v xdg-open > /dev/null; then
        xdg-open "$url"
    elif command -v open > /dev/null; then
        open "$url"
    elif command -v start > /dev/null; then
        start "$url"
    else
        echo -e "${BLUE}📋 Open this URL in your browser: $url${NC}"
    fi
}

# Interactive mode if no arguments
if [ $# -eq 0 ]; then
    # Get server IP if not set
    if [ -z "$DEFAULT_SERVER_IP" ]; then
        echo -e "${YELLOW}🌐 Enter your public IP address or server hostname:${NC}"
        read -p "Server IP/Hostname: " DEFAULT_SERVER_IP
        
        if [ -z "$DEFAULT_SERVER_IP" ]; then
            echo -e "${RED}❌ Server IP is required${NC}"
            exit 1
        fi
    fi
    
    while true; do
        show_menu
        read -p "Select option (1-6): " choice
        
        case $choice in
            1)
                setup_ssh_key
                if test_ssh_connection "$DEFAULT_SERVER_IP"; then
                    create_tunnel "$DEFAULT_SERVER_IP" "$DEFAULT_LOCAL_PORT" "$DEFAULT_REMOTE_PORT"
                fi
                ;;
            2)
                stop_tunnel
                ;;
            3)
                check_status
                ;;
            4)
                setup_ssh_key
                ;;
            5)
                open_browser
                ;;
            6)
                echo -e "${GREEN}👋 Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Invalid option${NC}"
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
fi

# Command line mode
case "$1" in
    "connect")
        SERVER_IP="${2:-$DEFAULT_SERVER_IP}"
        if [ -z "$SERVER_IP" ]; then
            echo -e "${RED}❌ Server IP required${NC}"
            echo "Usage: $0 connect <server_ip>"
            exit 1
        fi
        setup_ssh_key
        test_ssh_connection "$SERVER_IP" && create_tunnel "$SERVER_IP" "$DEFAULT_LOCAL_PORT" "$DEFAULT_REMOTE_PORT"
        ;;
    "stop")
        stop_tunnel
        ;;
    "status")
        check_status
        ;;
    "open")
        open_browser
        ;;
    *)
        echo -e "${BLUE}🚇 ArmGuard SSH Tunnel Client${NC}"
        echo ""
        echo "Usage: $0 [command] [options]"
        echo ""
        echo "Commands:"
        echo "  connect <server_ip>  - Create SSH tunnel to server"
        echo "  stop                 - Stop active tunnel"
        echo "  status              - Check tunnel status"
        echo "  open                - Open ArmGuard in browser"
        echo ""
        echo "Interactive mode: $0 (no arguments)"
        exit 1
        ;;
esac