#!/bin/bash

# =============================================================================
# ArmGuard Master Deployment Script
# Unified deployment orchestrator for all environments
# =============================================================================

set -e

# Load master configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/master-config.sh"

# =============================================================================
# Usage and Help
# =============================================================================

show_usage() {
    cat << EOF
ArmGuard Master Deployment Script

USAGE:
    $0 [METHOD] [OPTIONS]

METHODS:
    vm-test        Deploy to VMware test environment (shared folder)
    basic-setup    Basic server setup (simple installation)
    production     Full production deployment (enterprise features)
    docker-test    Docker testing environment (containers + monitoring)
    
    list           List all available deployment methods
    status         Show current deployment status
    help           Show this help message

OPTIONS:
    --dry-run      Show what would be done without executing
    --verbose      Enable verbose output
    --force        Force deployment even if already deployed
    --config       Show current configuration
    
EXAMPLES:
    $0 vm-test                    # Deploy to VM test environment
    $0 production --verbose       # Production deployment with verbose output
    $0 docker-test --dry-run      # Preview Docker testing setup
    $0 status                     # Check current deployment status

ENVIRONMENTS:
    • vm-test: VMware VM with shared folders (for development/testing)
    • basic-setup: Simple server deployment (minimal features)
    • production: Full production server (all enterprise features)
    • docker-test: Containerized testing with monitoring stack

For detailed documentation, see README.md in each method directory.
EOF
}

# =============================================================================
# Environment Detection and Validation
# =============================================================================

detect_current_environment() {
    if [ -d "/mnt/hgfs" ] && [ -d "/mnt/hgfs/Armguard" ]; then
        echo "vm-test"
    elif [ -f "/.dockerenv" ]; then
        echo "docker-test"
    elif [ -f "/etc/systemd/system/armguard.service" ]; then
        echo "production"
    elif [ -f "/var/www/armguard/manage.py" ]; then
        echo "basic-setup"
    else
        echo "unknown"
    fi
}

validate_method() {
    local method=$1
    local valid_methods=("vm-test" "basic-setup" "production" "docker-test")
    
    for valid_method in "${valid_methods[@]}"; do
        if [ "$method" = "$valid_method" ]; then
            return 0
        fi
    done
    
    return 1
}

# =============================================================================
# Deployment Methods
# =============================================================================

deploy_vm_test() {
    log "INFO" "Starting VMware VM test deployment..."
    
    if [ ! -d "/mnt/hgfs" ]; then
        log "ERROR" "VMware shared folder not detected. Is this running in a VM?"
        log "INFO" "Make sure VMware Tools are installed and shared folder is configured."
        exit 1
    fi
    
    cd "$SCRIPT_DIR/methods/vmware-setup"
    chmod +x vm-deploy.sh
    ./vm-deploy.sh "$@"
}

deploy_basic_setup() {
    log "INFO" "Starting basic server setup deployment..."
    
    if [ ! -f "$SCRIPT_DIR/methods/basic-setup/serversetup.sh" ]; then
        log "ERROR" "Basic setup script not found"
        exit 1
    fi
    
    cd "$SCRIPT_DIR/methods/basic-setup"
    chmod +x serversetup.sh
    ./serversetup.sh "$@"
}

deploy_production() {
    log "INFO" "Starting production deployment..."
    
    if [ "$EUID" -eq 0 ]; then
        log "ERROR" "Production deployment should not be run as root"
        log "INFO" "Run as regular user - sudo will be used when needed"
        exit 1
    fi
    
    cd "$SCRIPT_DIR/methods/production"
    chmod +x master-deploy.sh
    ./master-deploy.sh "$@"
}

deploy_docker_test() {
    log "INFO" "Starting Docker testing environment deployment..."
    
    if ! command_exists docker; then
        log "ERROR" "Docker is required for testing environment"
        log "INFO" "Please install Docker first: https://docs.docker.com/install/"
        exit 1
    fi
    
    if ! command_exists docker-compose && ! docker compose version &>/dev/null; then
        log "ERROR" "Docker Compose is required for testing environment"
        log "INFO" "Please install Docker Compose first"
        exit 1
    fi
    
    cd "$SCRIPT_DIR/methods/docker-testing"
    chmod +x run_all_tests.sh
    ./run_all_tests.sh "$@"
}

# =============================================================================
# Status and Information Commands
# =============================================================================

show_status() {
    local current_env=$(detect_current_environment)
    
    cat << EOF
ArmGuard Deployment Status
========================

Current Environment: $current_env
Detection Time: $(date)
Host: $HOSTNAME ($HOST_IP)

Configuration Summary:
• Project Directory: $PROJECT_DIR
• Database: $DB_ENGINE ($DB_NAME)
• Web Server: $WEB_SERVER
• Debug Mode: $DEBUG
• SSL Enabled: $SSL_ENABLED

Services Status:
EOF

    # Check common services
    local services=("nginx" "postgresql" "redis-server")
    
    for service in "${services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            echo -e "• $service: ${GREEN}running${NC}"
        elif command_exists "$service"; then
            echo -e "• $service: ${YELLOW}installed but not running${NC}"
        else
            echo -e "• $service: ${RED}not installed${NC}"
        fi
    done
    
    # Check Docker services if in container environment
    if [ "$current_env" = "docker-test" ]; then
        echo
        echo "Docker Services:"
        docker-compose ps 2>/dev/null || echo "Docker Compose not running"
    fi
    
    # Check application status
    echo
    echo "Application Status:"
    if [ -f "$PROJECT_DIR/manage.py" ]; then
        echo -e "• Django Application: ${GREEN}found${NC}"
        
        if [ -f "$PROJECT_DIR/.env" ]; then
            echo -e "• Environment Configuration: ${GREEN}configured${NC}"
        else
            echo -e "• Environment Configuration: ${YELLOW}missing${NC}"
        fi
        
        if [ -d "$PROJECT_DIR/venv" ]; then
            echo -e "• Virtual Environment: ${GREEN}found${NC}"
        else
            echo -e "• Virtual Environment: ${YELLOW}missing${NC}"
        fi
    else
        echo -e "• Django Application: ${RED}not found${NC}"
    fi
}

show_config() {
    cat << EOF
ArmGuard Configuration
====================

Environment: $ENVIRONMENT
Version: $ARMGUARD_VERSION
Deployment Date: $DEPLOYMENT_DATE

Paths:
• Base Directory: $BASE_DIR
• Project Directory: $PROJECT_DIR
• Static Files: $STATIC_DIR
• Media Files: $MEDIA_DIR
• Log Directory: $LOG_DIR
• Backup Directory: $BACKUP_DIR

Database:
• Engine: $DB_ENGINE
• Name: $DB_NAME
• User: $DB_USER
• Host: $DB_HOST:$DB_PORT

Web Server:
• Server: $WEB_SERVER
• Domain: $DOMAIN
• HTTP Port: $HTTP_PORT
• HTTPS Port: $HTTPS_PORT
• SSL Enabled: $SSL_ENABLED

Security:
• Debug Mode: $DEBUG
• Allowed Hosts: $ALLOWED_HOSTS

Features:
• API Enabled: $ENABLE_API
• Admin Enabled: $ENABLE_ADMIN
• Monitoring: $ENABLE_MONITORING
• Backup: $BACKUP_ENABLED

Network:
• Host IP: $HOST_IP
• Bind IP: $BIND_IP
• Public IP: $PUBLIC_IP
EOF
}

list_methods() {
    cat << EOF
Available Deployment Methods
===========================

1. vm-test (VMware Test Environment)
   • Target: VMware VM with shared folders
   • Use case: Development and testing
   • Features: Basic setup, test database, development tools
   • Path: $SCRIPT_DIR/methods/vmware-setup/
   
2. basic-setup (Simple Server Setup)
   • Target: Basic Linux server
   • Use case: Simple production deployment
   • Features: Essential services only
   • Path: $SCRIPT_DIR/methods/basic-setup/
   
3. production (Enterprise Production)
   • Target: Production server
   • Use case: Full production deployment
   • Features: All enterprise features, monitoring, backups
   • Path: $SCRIPT_DIR/methods/production/
   
4. docker-test (Container Testing)
   • Target: Docker environment
   • Use case: Comprehensive testing and CI/CD
   • Features: Full testing suite, monitoring stack
   • Path: $SCRIPT_DIR/methods/docker-testing/

Current environment detected: $(detect_current_environment)

Use '$0 [method]' to deploy, or '$0 [method] --help' for method-specific options.
EOF
}

# =============================================================================
# Main Script Logic
# =============================================================================

main() {
    local method=""
    local dry_run=false
    local verbose=false
    local force=false
    local show_config_flag=false
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            vm-test|basic-setup|production|docker-test)
                method="$1"
                shift
                ;;
            list|status|help)
                method="$1"
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --verbose)
                verbose=true
                export LOG_LEVEL="DEBUG"
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --config)
                show_config_flag=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log "ERROR" "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Handle special commands
    if [ "$show_config_flag" = true ]; then
        show_config
        exit 0
    fi
    
    case $method in
        "list")
            list_methods
            exit 0
            ;;
        "status")
            show_status
            exit 0
            ;;
        "help"|"")
            show_usage
            exit 0
            ;;
    esac
    
    # Validate deployment method
    if ! validate_method "$method"; then
        log "ERROR" "Invalid deployment method: $method"
        echo
        list_methods
        exit 1
    fi
    
    # Show configuration if verbose
    if [ "$verbose" = true ]; then
        show_config
        echo
    fi
    
    # Dry run mode
    if [ "$dry_run" = true ]; then
        log "INFO" "DRY RUN: Would execute $method deployment"
        log "INFO" "Method directory: $SCRIPT_DIR/methods/${method/-/\-}"
        log "INFO" "Target environment: $ENVIRONMENT"
        exit 0
    fi
    
    # Check for existing deployment (unless forced)
    if [ "$force" = false ]; then
        local current_env=$(detect_current_environment)
        if [ "$current_env" != "unknown" ] && [ "$current_env" != "$method" ]; then
            log "WARN" "Detected existing deployment: $current_env"
            log "WARN" "Attempting to deploy: $method"
            echo
            read -p "Continue with deployment? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log "INFO" "Deployment cancelled"
                exit 0
            fi
        fi
    fi
    
    # Execute deployment method
    log "INFO" "Starting ArmGuard deployment: $method"
    log "INFO" "Target environment: $ENVIRONMENT"
    echo
    
    case $method in
        "vm-test")
            deploy_vm_test "$@"
            ;;
        "basic-setup")
            deploy_basic_setup "$@"
            ;;
        "production")
            deploy_production "$@"
            ;;
        "docker-test")
            deploy_docker_test "$@"
            ;;
    esac
    
    log "INFO" "Deployment completed: $method"
}

# Check if script is being sourced or executed
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi