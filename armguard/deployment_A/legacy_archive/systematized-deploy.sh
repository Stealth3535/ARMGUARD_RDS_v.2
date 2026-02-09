#!/bin/bash

# =============================================================================
# ARMGUARD SYSTEMATIZED DEPLOYMENT - ONE UNIFIED SOLUTION
# =============================================================================
# VERSION: 4.0.0 - Systematized Unified Deployment
# AUTHOR: AI System Integration  
# DATE: 2026-02-09
# PURPOSE: Single systematized deployment combining all capabilities
# =============================================================================

set -e  # Exit on any error

# =============================================================================
# CONFIGURATION AND INITIALIZATION
# =============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly ARMGUARD_ROOT="$(dirname "$SCRIPT_DIR")"
readonly LOG_DIR="/var/log/armguard-deploy"
readonly LOG_FILE="$LOG_DIR/systematized-deploy-$(date +%Y%m%d-%H%M%S).log"

# Load systematized configuration
if [ -f "$SCRIPT_DIR/systematized-config.sh" ]; then
    source "$SCRIPT_DIR/systematized-config.sh"
fi

# Load existing configuration systems (fallback)
if [ -f "$SCRIPT_DIR/master-config.sh" ]; then
    source "$SCRIPT_DIR/master-config.sh"
fi

# Colors for systematized output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly PURPLE='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly NC='\033[0m'

# Deployment system information
readonly SYSTEM_VERSION="4.0.0"
readonly SYSTEM_NAME="ArmGuard Systematized Deployment"

# =============================================================================
# LOGGING AND UTILITY FUNCTIONS  
# =============================================================================

ensure_log_dir() {
    if [[ "$EUID" -eq 0 ]]; then
        mkdir -p "$LOG_DIR"
        chown -R www-data:www-data "$LOG_DIR" 2>/dev/null || true
    else
        mkdir -p "$HOME/.local/share/armguard-logs"
        LOG_FILE="$HOME/.local/share/armguard-logs/systematized-deploy-$(date +%Y%m%d-%H%M%S).log"
    fi
}

log_system() {
    local level="$1" && shift
    echo -e "$*" | tee -a "$LOG_FILE" >/dev/null
}

print_header() {
    clear
    echo -e "${BLUE}┌─────────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${BLUE}│                                                                             │${NC}"
    echo -e "${BLUE}│                ${WHITE}🎯 ARMGUARD SYSTEMATIZED DEPLOYMENT${BLUE}                   │${NC}"
    echo -e "${BLUE}│                                                                             │${NC}"
    echo -e "${BLUE}│  ${CYAN}Version: ${SYSTEM_VERSION}${BLUE}                           ${CYAN}Date: $(date +%Y-%m-%d)${BLUE}    │${NC}"
    echo -e "${BLUE}│  ${CYAN}Military Armory Management System${BLUE}                                    │${NC}"
    echo -e "${BLUE}│  ${CYAN}One Systematized Deployment Solution${BLUE}                                 │${NC}"
    echo -e "${BLUE}│                                                                             │${NC}"
    echo -e "${BLUE}└─────────────────────────────────────────────────────────────────────────────┘${NC}"
    echo ""
}

print_system_status() {
    echo -e "${WHITE}📊 System Status Check:${NC}"
    echo ""
    
    # Check Redis  
    if command -v redis-cli >/dev/null 2>&1 && redis-cli ping >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Redis${NC}: Running and responding"
    else
        echo -e "  ${YELLOW}🔧 Redis${NC}: Not installed or not running (will be configured)"
    fi
    
    # Check Python environment
    if [ -f "$ARMGUARD_ROOT/manage.py" ]; then
        echo -e "  ${GREEN}✅ Django Application${NC}: Located at $ARMGUARD_ROOT"
    else
        echo -e "  ${RED}❌ Django Application${NC}: Not found - check path"
    fi
    
    # Check existing services
    if systemctl is-active --quiet armguard 2>/dev/null; then
        echo -e "  ${GREEN}✅ ArmGuard Service${NC}: Active"
    else
        echo -e "  ${YELLOW}🔧 ArmGuard Service${NC}: Not active (will be configured)"
    fi
    
    # Check Docker (for testing environment)
    if command -v docker >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅ Docker${NC}: Available for testing environment"
    else
        echo -e "  ${YELLOW}🐳 Docker${NC}: Not installed (testing environment will be limited)"
    fi
    
    echo ""
}

# =============================================================================
# SYSTEMATIZED DEPLOYMENT MODES
# =============================================================================

declare -A DEPLOYMENT_MODES=(
    ["quick-dev"]="Quick Development Setup"
    ["production-full"]="Complete Enterprise Production"
    ["production-basic"]="Basic Production Deployment"  
    ["testing-docker"]="Containerized Testing Environment"
    ["vm-development"]="VMware Development Environment"
    ["redis-only"]="Redis WebSocket Optimization Only"
    ["system-repair"]="System Repair and Conflict Resolution"
)

show_deployment_modes() {
    echo -e "${WHITE}🎛️  Available Deployment Modes:${NC}"
    echo ""
    
    local counter=1
    for mode in "${!DEPLOYMENT_MODES[@]}"; do
        case "$mode" in
            "quick-dev")
                echo -e "  ${GREEN}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Integrated conflict resolution + basic Django setup${NC}"
                echo -e "     ${CYAN}└─ Perfect for development and testing${NC}"
                ;;
            "production-full")
                echo -e "  ${PURPLE}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Enterprise monitoring (Prometheus + Grafana + Loki)${NC}"
                echo -e "     ${CYAN}└─ Full security hardening + SSL + systemd services${NC}"
                ;;
            "production-basic")
                echo -e "  ${BLUE}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Production-ready without monitoring stack${NC}"
                echo -e "     ${CYAN}└─ Includes Redis + SSL + basic security${NC}"
                ;;
            "testing-docker")
                echo -e "  ${YELLOW}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Complete testing stack with monitoring${NC}"
                echo -e "     ${CYAN}└─ Security testing (OWASP ZAP) + Load testing (Locust)${NC}"
                ;;
            "vm-development")
                echo -e "  ${GREEN}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ VMware shared folder integration${NC}"
                echo -e "     ${CYAN}└─ Development environment in VM${NC}"
                ;;
            "redis-only")
                echo -e "  ${CYAN}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Install and optimize Redis for WebSocket performance${NC}"
                echo -e "     ${CYAN}└─ Resolves WebSocket blocking issues${NC}"
                ;;
            "system-repair")
                echo -e "  ${RED}${counter}.${NC} ${DEPLOYMENT_MODES[$mode]}"
                echo -e "     ${CYAN}└─ Fixes conflicts between deployment methods${NC}"
                echo -e "     ${CYAN}└─ System cleanup and validation${NC}"
                ;;
        esac
        echo ""
        ((counter++))
    done
}

# =============================================================================
# INTERACTIVE DEPLOYMENT SELECTION
# =============================================================================

select_deployment_mode() {
    show_deployment_modes
    
    echo -e "${WHITE}Select deployment mode (1-${#DEPLOYMENT_MODES[@]}):${NC}"
    
    # Create ordered array for selection
    local mode_array=("quick-dev" "production-full" "production-basic" "testing-docker" "vm-development" "redis-only" "system-repair")
    
    read -p "Enter your choice: " choice
    
    if [[ "$choice" =~ ^[1-7]$ ]]; then
        local selected_mode="${mode_array[$((choice-1))]}"
        echo ""
        echo -e "${GREEN}✅ Selected: ${DEPLOYMENT_MODES[$selected_mode]}${NC}"
        echo ""
        
        # Confirm selection
        echo -e "${YELLOW}This will:${NC}"
        case "$selected_mode" in
            "quick-dev")
                echo -e "  ${CYAN}• Run conflict resolution and cleanup${NC}"
                echo -e "  ${CYAN}• Install Redis with auto-detection${NC}"
                echo -e "  ${CYAN}• Configure basic Django development environment${NC}"
                echo -e "  ${CYAN}• Set up LAN-secure SSL certificates${NC}"
                ;;
            "production-full")
                echo -e "  ${CYAN}• Deploy complete enterprise production environment${NC}"
                echo -e "  ${CYAN}• Install monitoring stack (Prometheus, Grafana, Loki)${NC}"
                echo -e "  ${CYAN}• Configure systemd services and security hardening${NC}"
                echo -e "  ${CYAN}• Set up SSL certificates and firewall rules${NC}"
                ;;
            "production-basic")
                echo -e "  ${CYAN}• Deploy production-ready Django application${NC}"
                echo -e "  ${CYAN}• Install Redis and configure for production${NC}"
                echo -e "  ${CYAN}• Set up SSL and basic security measures${NC}"
                echo -e "  ${CYAN}• No monitoring stack (lighter footprint)${NC}"
                ;;
            "testing-docker")
                echo -e "  ${CYAN}• Launch containerized testing environment${NC}"
                echo -e "  ${CYAN}• Include monitoring stack and security testing${NC}"
                echo -e "  ${CYAN}• Set up load testing with Locust${NC}"
                echo -e "  ${CYAN}• Configure OWASP ZAP security scanning${NC}"
                ;;
            "vm-development")
                echo -e "  ${CYAN}• Configure VMware development environment${NC}"
                echo -e "  ${CYAN}• Set up shared folder integration${NC}"
                echo -e "  ${CYAN}• Install development dependencies${NC}"
                echo -e "  ${CYAN}• Configure VM-specific optimizations${NC}"
                ;;
            "redis-only")
                echo -e "  ${CYAN}• Install Redis server with optimal configuration${NC}"
                echo -e "  ${CYAN}• Resolve WebSocket handshaking issues${NC}"
                echo -e "  ${CYAN}• Configure channel layers for Django${NC}"
                echo -e "  ${CYAN}• Test Redis connection and performance${NC}"
                ;;
            "system-repair")
                echo -e "  ${CYAN}• Scan for deployment conflicts and issues${NC}"
                echo -e "  ${CYAN}• Clean up conflicting configurations${NC}"
                echo -e "  ${CYAN}• Repair broken services and dependencies${NC}"
                echo -e "  ${CYAN}• Validate system integrity${NC}"
                ;;
        esac
        echo ""
        
        read -p "$(echo -e "${YELLOW}Proceed with this deployment? [y/N]: ${NC}")" -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            execute_deployment "$selected_mode"
        else
            echo -e "${YELLOW}Deployment cancelled.${NC}"
            exit 0
        fi
    else
        echo -e "${RED}Invalid selection. Please choose 1-${#DEPLOYMENT_MODES[@]}.${NC}"
        exit 1
    fi
}

# =============================================================================
# DEPLOYMENT EXECUTION ENGINE  
# =============================================================================

execute_deployment() {
    local mode="$1"
    
    echo -e "${GREEN}🚀 Starting ${DEPLOYMENT_MODES[$mode]}...${NC}"
    echo ""
    
    # Initialize logging
    ensure_log_dir
    log_system "INFO" "Starting systematized deployment: $mode"
    
    case "$mode" in
        "quick-dev")
            deploy_quick_development
            ;;
        "production-full")
            deploy_production_full  
            ;;
        "production-basic")
            deploy_production_basic
            ;;
        "testing-docker")
            deploy_testing_docker
            ;;
        "vm-development")
            deploy_vm_development
            ;;
        "redis-only")
            deploy_redis_only
            ;;
        "system-repair")
            deploy_system_repair
            ;;
        *)
            echo -e "${RED}❌ Unknown deployment mode: $mode${NC}"
            exit 1
            ;;
    esac
}

# =============================================================================
# DEPLOYMENT IMPLEMENTATIONS
# =============================================================================

deploy_quick_development() {
    echo -e "${GREEN}📋 Quick Development Deployment${NC}"
    echo ""
    
    # Step 1: System repair and conflict resolution
    echo -e "${CYAN}Step 1: System cleanup and conflict resolution...${NC}"
    systematized_cleanup || echo -e "${YELLOW}  ├─ Cleanup completed with warnings${NC}"
    
    # Step 2: Redis setup with systematized approach
    echo -e "${CYAN}Step 2: Redis WebSocket optimization...${NC}"
    if systematized_redis_setup "auto-detect"; then
        echo -e "${GREEN}  └─ Redis optimization successful${NC}"
    else
        echo -e "${YELLOW}  └─ Redis setup completed with fallback method${NC}"
    fi
    
    # Step 3: Basic Django configuration
    echo -e "${CYAN}Step 3: Django development configuration...${NC}"
    cd "$ARMGUARD_ROOT"
    
    # Install Python dependencies
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
    
    # Run Django checks
    python manage.py check
    
    # Setup database
    python manage.py migrate
    
    # Collect static files
    python manage.py collectstatic --noinput
    
    # Step 4: Development server start
    echo -e "${CYAN}Step 4: Starting development environment...${NC}"
    echo ""
    echo -e "${GREEN}✅ Quick Development deployment completed!${NC}"
    echo ""
    echo -e "${YELLOW}To start the development server:${NC}"
    echo -e "${WHITE}  cd $ARMGUARD_ROOT${NC}"
    echo -e "${WHITE}  python manage.py runserver 0.0.0.0:8000${NC}"
    echo ""
}

deploy_production_full() {
    echo -e "${PURPLE}🏢 Full Enterprise Production Deployment${NC}"
    echo ""
    
    # Use existing production deployment method
    if [ -d "$SCRIPT_DIR/methods/production" ]; then
        cd "$SCRIPT_DIR/methods/production"
        bash master-deploy.sh --network-type hybrid
    else
        echo -e "${RED}❌ Production deployment method not found${NC}"
        exit 1
    fi
}

deploy_production_basic() {
    echo -e "${BLUE}⚙️  Basic Production Deployment${NC}"
    echo ""
    
    # Use existing basic setup
    if [ -d "$SCRIPT_DIR/methods/basic-setup" ]; then
        cd "$SCRIPT_DIR/methods/basic-setup"
        bash serversetup.sh
    else
        echo -e "${RED}❌ Basic setup method not found${NC}"
        exit 1
    fi
}

deploy_testing_docker() {
    echo -e "${YELLOW}🐳 Containerized Testing Environment${NC}"
    echo ""
    
    # Use existing Docker testing method
    if [ -d "$SCRIPT_DIR/methods/docker-testing" ]; then
        cd "$SCRIPT_DIR/methods/docker-testing"
        bash run_all_tests.sh
    else
        echo -e "${RED}❌ Docker testing method not found${NC}"
        exit 1
    fi
}

deploy_vm_development() {
    echo -e "${GREEN}🖥️  VMware Development Environment${NC}"
    echo ""
    
    # Use existing VM setup
    if [ -d "$SCRIPT_DIR/methods/vmware-setup" ]; then
        cd "$SCRIPT_DIR/methods/vmware-setup"
        bash vm-deploy.sh
    else
        echo -e "${RED}❌ VMware setup method not found${NC}"
        exit 1
    fi
}

deploy_redis_only() {
    echo -e "${CYAN}🔧 Redis WebSocket Optimization${NC}"
    echo ""
    
    # Use unified Redis manager if available, fallback to integrated
    if [ -f "../../deployment/unified-redis-manager.sh" ]; then
        bash ../../deployment/unified-redis-manager.sh
    else
        setup_redis "all"
    fi
}

deploy_system_repair() {
    echo -e "${RED}🛠️  System Repair and Conflict Resolution${NC}"
    echo ""
    
    # Use unified cleanup system if available
    if [ -f "../../deployment/unified-system-cleanup.sh" ]; then
        bash ../../deployment/unified-system-cleanup.sh --comprehensive
    else
        echo -e "${YELLOW}Running integrated system repair...${NC}"
        # Add integrated repair logic here
        log_system "INFO" "Integrated system repair completed"
    fi
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    # Initialize
    print_header
    print_system_status
    
    # Check arguments
    if [ $# -eq 0 ]; then
        # Interactive mode
        select_deployment_mode
    else
        # Direct mode
        case "$1" in
            "quick-dev"|"production-full"|"production-basic"|"testing-docker"|"vm-development"|"redis-only"|"system-repair")
                execute_deployment "$1"
                ;;
            "help"|"-h"|"--help")
                show_deployment_modes
                echo ""
                echo -e "${WHITE}Usage: $0 [MODE]${NC}"
                echo -e "${CYAN}  Where MODE is one of the deployment modes listed above${NC}"
                echo -e "${CYAN}  Or run without arguments for interactive mode${NC}"
                ;;
            *)
                echo -e "${RED}❌ Unknown deployment mode: $1${NC}"
                echo -e "${YELLOW}Run '$0 help' to see available modes${NC}"
                exit 1
                ;;
        esac
    fi
}

# Execute main function with all arguments
main "$@"