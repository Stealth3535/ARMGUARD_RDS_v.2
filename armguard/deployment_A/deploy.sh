#!/bin/bash

################################################################################
# ARMGUARD SIMPLE DEPLOYMENT
# 
# This is the ONLY script you need to run for production deployment.
# It automatically detects your environment and deploys everything.
#
# Usage: sudo bash deploy.sh
################################################################################

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear

echo -e "${CYAN}"
cat << "EOF"
    ___    ____  __  __________  _____    ____  ____ 
   /   |  / __ \/  |/  / ____/ / / / /   / __ \/ __ \
  / /| | / /_/ / /|_/ / / __/ / / / /   / /_/ / / / /
 / ___ |/ _, _/ /  / / /_/ / /_/ / /___/ _, _/ /_/ / 
/_/  |_/_/ |_/_/  /_/\____/\____/_____/_/ |_/_____/  
                                                      
EOF
echo -e "${NC}"

echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}║              ${WHITE}ARMGUARD DEPLOYMENT SYSTEM${CYAN}                      ║${NC}"
echo -e "${BOLD}${CYAN}║                                                              ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    echo -e "${YELLOW}Usage: sudo bash deploy.sh${NC}"
    exit 1
fi

# Detect script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo -e "${BLUE}📍 Detected Configuration:${NC}"
echo -e "   Project: ${GREEN}$PROJECT_ROOT${NC}"
echo -e "   User: ${GREEN}$(who am i | awk '{print $1}')${NC}"
echo -e "   OS: ${GREEN}$(lsb_release -d 2>/dev/null | cut -f2 || echo "Linux")${NC}"
echo ""

# Check if project structure is valid
if [ ! -f "$PROJECT_ROOT/manage.py" ]; then
    echo -e "${RED}ERROR: Invalid project structure${NC}"
    echo -e "${YELLOW}Cannot find manage.py in $PROJECT_ROOT${NC}"
    exit 1
fi

echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}What do you want to do?${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${GREEN}1)${NC} ${BOLD}Fresh Deployment${NC}"
echo -e "     Choose: Production, Basic Setup, Docker, or VMware"
echo -e "     ${YELLOW}Time: Varies by method${NC}"
echo ""
echo -e "  ${GREEN}2)${NC} ${BOLD}Cleanup & Re-deploy${NC}"
echo -e "     Fix failed deployment and start over"
echo -e "     ${YELLOW}Time: 5-10 minutes${NC}"
echo ""
echo -e "  ${GREEN}3)${NC} ${BOLD}Quick Fix${NC}"
echo -e "     Update existing deployment with latest code"
echo -e "     ${YELLOW}Time: 2-3 minutes${NC}"
echo ""
echo -e "  ${GREEN}4)${NC} ${BOLD}Development Mode${NC}"
echo -e "     Run Django development server (no nginx/systemd)"
echo -e "     ${YELLOW}Time: Instant${NC}"
echo ""
echo -e "  ${GREEN}5)${NC} Exit"
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
read -p "Enter your choice [1-5]: " CHOICE

case $CHOICE in
    1)
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${BOLD}Select Deployment Method:${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "  ${GREEN}1)${NC} ${BOLD}Production Deployment${NC}"
        echo -e "     Full production setup with Nginx, Gunicorn, SSL"
        echo -e "     ${YELLOW}Recommended for: Raspberry Pi, Ubuntu Server${NC}"
        echo ""
        echo -e "  ${GREEN}2)${NC} ${BOLD}Basic Setup${NC}"
        echo -e "     Manual VM or server setup"
        echo -e "     ${YELLOW}Recommended for: Custom configurations${NC}"
        echo ""
        echo -e "  ${GREEN}3)${NC} ${BOLD}Docker Testing${NC}"
        echo -e "     Containerized deployment with Docker Compose"
        echo -e "     ${YELLOW}Recommended for: Testing, development${NC}"
        echo ""
        echo -e "  ${GREEN}4)${NC} ${BOLD}VMware Setup${NC}"
        echo -e "     VMware-specific configuration"
        echo -e "     ${YELLOW}Recommended for: VMware environments${NC}"
        echo ""
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        read -p "Enter your choice [1-4]: " DEPLOY_METHOD
        
        # Pull latest code
        echo ""
        echo -e "${YELLOW}Pulling latest code from Git...${NC}"
        cd "$PROJECT_ROOT"
        ORIGINAL_USER=$(who am i | awk '{print $1}')
        sudo -u $ORIGINAL_USER git pull origin main 2>/dev/null || true
        echo ""
        
        case $DEPLOY_METHOD in
            1)
                echo -e "${BLUE}🚀 Starting Production Deployment...${NC}"
                echo ""
                DEPLOY_SCRIPT="$PROJECT_ROOT/deployment_A/methods/production/deploy-armguard.sh"
                if [ ! -f "$DEPLOY_SCRIPT" ]; then
                    echo -e "${RED}ERROR: Production deployment script not found${NC}"
                    exit 1
                fi
                chmod +x "$DEPLOY_SCRIPT"
                bash "$DEPLOY_SCRIPT"
                ;;
                
            2)
                echo -e "${BLUE}🔧 Starting Basic Setup...${NC}"
                echo ""
                BASIC_DIR="$PROJECT_ROOT/deployment_A/methods/basic-setup"
                if [ ! -d "$BASIC_DIR" ]; then
                    echo -e "${RED}ERROR: Basic setup directory not found${NC}"
                    exit 1
                fi
                
                echo -e "${CYAN}Available setup scripts:${NC}"
                echo -e "  1) Server Setup (serversetup.sh)"
                echo -e "  2) VM Setup (vmsetup.sh)"
                echo ""
                read -p "Select setup type [1-2]: " BASIC_TYPE
                
                if [ "$BASIC_TYPE" = "1" ]; then
                    SETUP_SCRIPT="$BASIC_DIR/serversetup.sh"
                elif [ "$BASIC_TYPE" = "2" ]; then
                    SETUP_SCRIPT="$BASIC_DIR/vmsetup.sh"
                else
                    echo -e "${RED}Invalid choice${NC}"
                    exit 1
                fi
                
                if [ ! -f "$SETUP_SCRIPT" ]; then
                    echo -e "${RED}ERROR: Setup script not found${NC}"
                    exit 1
                fi
                
                chmod +x "$SETUP_SCRIPT"
                bash "$SETUP_SCRIPT"
                ;;
                
            3)
                echo -e "${BLUE}🐳 Starting Docker Testing Environment...${NC}"
                echo ""
                DOCKER_DIR="$PROJECT_ROOT/deployment_A/methods/docker-testing"
                if [ ! -d "$DOCKER_DIR" ]; then
                    echo -e "${RED}ERROR: Docker testing directory not found${NC}"
                    exit 1
                fi
                
                cd "$DOCKER_DIR"
                
                # Check if Docker is installed
                if ! command -v docker &> /dev/null; then
                    echo -e "${YELLOW}Docker not found. Installing Docker...${NC}"
                    curl -fsSL https://get.docker.com -o get-docker.sh
                    sh get-docker.sh
                    usermod -aG docker $ORIGINAL_USER
                fi
                
                # Check if Docker Compose is installed
                if ! command -v docker-compose &> /dev/null; then
                    echo -e "${YELLOW}Docker Compose not found. Installing...${NC}"
                    apt-get update
                    apt-get install -y docker-compose
                fi
                
                echo -e "${GREEN}Starting Docker containers...${NC}"
                docker-compose up -d
                
                echo ""
                echo -e "${GREEN}✓ Docker containers started${NC}"
                echo -e "${CYAN}View logs: docker-compose logs -f${NC}"
                echo -e "${CYAN}Stop containers: docker-compose down${NC}"
                ;;
                
            4)
                echo -e "${BLUE}🖥️  Starting VMware Setup...${NC}"
                echo ""
                VMWARE_DIR="$PROJECT_ROOT/deployment_A/methods/vmware-setup"
                if [ ! -d "$VMWARE_DIR" ]; then
                    echo -e "${RED}ERROR: VMware setup directory not found${NC}"
                    exit 1
                fi
                
                echo -e "${CYAN}Please refer to the VMware setup documentation:${NC}"
                echo -e "${YELLOW}$VMWARE_DIR/README.md${NC}"
                echo ""
                echo -e "${YELLOW}VMware setup requires manual configuration.${NC}"
                echo -e "${YELLOW}Follow the README for detailed instructions.${NC}"
                
                if [ -f "$VMWARE_DIR/README.md" ]; then
                    read -p "View README now? (y/n): " VIEW_README
                    if [[ "$VIEW_README" =~ ^[Yy] ]]; then
                        less "$VMWARE_DIR/README.md"
                    fi
                fi
                ;;
                
            *)
                echo ""
                echo -e "${RED}Invalid choice. Please run again and select 1-4.${NC}"
                exit 1
                ;;
        esac
        ;;
        
    2)
        echo ""
        echo -e "${BLUE}🧹 Starting Cleanup & Re-deployment...${NC}"
        echo ""
        
        # Pull latest code
        echo -e "${YELLOW}Pulling latest code from Git...${NC}"
        cd "$PROJECT_ROOT"
        ORIGINAL_USER=$(who am i | awk '{print $1}')
        sudo chown -R $ORIGINAL_USER:$ORIGINAL_USER "$PROJECT_ROOT"
        sudo -u $ORIGINAL_USER git pull origin main 2>/dev/null || true
        
        # Run cleanup and redeploy
        CLEANUP_SCRIPT="$PROJECT_ROOT/deployment_A/methods/production/cleanup-and-redeploy.sh"
        if [ ! -f "$CLEANUP_SCRIPT" ]; then
            echo -e "${RED}ERROR: Cleanup script not found${NC}"
            echo -e "${YELLOW}Falling back to direct deployment...${NC}"
            DEPLOY_SCRIPT="$PROJECT_ROOT/deployment_A/methods/production/deploy-armguard.sh"
            chmod +x "$DEPLOY_SCRIPT"
            bash "$DEPLOY_SCRIPT"
        else
            chmod +x "$CLEANUP_SCRIPT"
            bash "$CLEANUP_SCRIPT"
        fi
        ;;
        
    3)
        echo ""
        echo -e "${BLUE}⚡ Running Quick Fix...${NC}"
        echo ""
        
        # Pull latest code
        echo -e "${YELLOW}Pulling latest code from Git...${NC}"
        cd "$PROJECT_ROOT"
        ORIGINAL_USER=$(who am i | awk '{print $1}')
        sudo chown -R $ORIGINAL_USER:$ORIGINAL_USER "$PROJECT_ROOT"
        sudo -u $ORIGINAL_USER git pull origin main
        
        # Run quick fix
        QUICK_FIX="$PROJECT_ROOT/deployment_A/methods/production/quick-fix-use-cloned-repo.sh"
        if [ ! -f "$QUICK_FIX" ]; then
            echo -e "${RED}ERROR: Quick fix script not found${NC}"
            exit 1
        fi
        
        chmod +x "$QUICK_FIX"
        bash "$QUICK_FIX"
        ;;
        
    4)
        echo ""
        echo -e "${BLUE}💻 Starting Development Server...${NC}"
        echo ""
        
        cd "$PROJECT_ROOT"
        
        # Check for virtual environment
        if [ -d "$PROJECT_ROOT/.venv" ]; then
            source "$PROJECT_ROOT/.venv/bin/activate"
        elif [ -d "$PROJECT_ROOT/venv" ]; then
            source "$PROJECT_ROOT/venv/bin/activate"
        fi
        
        # Set development settings
        export DJANGO_SETTINGS_MODULE=core.settings
        
        echo -e "${GREEN}Starting Django development server...${NC}"
        echo -e "${YELLOW}Access at: http://localhost:8000${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        
        python manage.py runserver 0.0.0.0:8000
        ;;
        
    5)
        echo ""
        echo -e "${CYAN}Goodbye!${NC}"
        exit 0
        ;;
        
    *)
        echo ""
        echo -e "${RED}Invalid choice. Please run again and select 1-5.${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
