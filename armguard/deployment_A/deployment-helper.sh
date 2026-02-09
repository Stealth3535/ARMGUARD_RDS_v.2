#!/bin/bash

# =============================================================================
# ARMGUARD DEPLOYMENT DECISION HELPER
# Eliminates confusion - guides users to the correct deployment path
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

clear
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                                                                                  ║${NC}"
echo -e "${BLUE}║                    ${WHITE}🛡️  ARMGUARD DEPLOYMENT DECISION HELPER${BLUE}                     ║${NC}"
echo -e "${BLUE}║                          ${CYAN}Find Your Perfect Deployment Path${BLUE}                        ║${NC}"
echo -e "${BLUE}║                                                                                  ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${WHITE}🎯 This helper will guide you to the right deployment approach!${NC}"
echo ""

# Function to execute deployment
execute_deployment() {
    local deployment_type="$1"
    local commands="$2"
    local description="$3"
    
    echo -e "${GREEN}✅ Perfect! You selected: ${WHITE}$deployment_type${NC}"
    echo -e "${CYAN}Description: $description${NC}"
    echo ""
    echo -e "${YELLOW}Commands to execute:${NC}"
    echo -e "${WHITE}$commands${NC}"
    echo ""
    
    read -p "🚀 Execute this deployment now? (y/N): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}🚀 Starting deployment...${NC}"
        echo ""
        eval "$commands"
    else
        echo -e "${YELLOW}ℹ️  Deployment cancelled. You can run these commands manually later.${NC}"
        echo -e "${WHITE}Saved to: deployment-commands.txt${NC}"
        echo "$commands" > deployment-commands.txt
    fi
}

# Main decision logic
echo -e "${BLUE}📋 Let's determine your deployment needs...${NC}"
echo ""

# Question 1: Purpose
echo -e "${WHITE}Question 1: What's your primary goal?${NC}"
echo "1. 🚀 Deploy ArmGuard quickly for development/testing"
echo "2. 🏭 Deploy for production use (standard enterprise features)"
echo "3. 🏢 Deploy for large enterprise (advanced features, compliance)"
echo "4. 🧪 Set up comprehensive testing environment"
echo "5. 🌐 Deploy with network separation (LAN/WAN isolation)"
echo "6. 💻 Deploy on VMware virtual machine"
echo ""

while true; do
    read -p "Your choice (1-6): " purpose
    case $purpose in
        1)
            # Quick deployment for development
            deployment_cmd="chmod +x *.sh && ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
            execution_desc="Standard modular deployment with minimal monitoring"
            execute_deployment "🚀 Quick Development Deployment" "$deployment_cmd" "$execution_desc"
            break
            ;;
        2)
            # Standard production
            echo ""
            echo -e "${BLUE}Question 2: What monitoring level do you need?${NC}"
            echo "1. 📊 Basic health checks (minimal)"
            echo "2. 📈 System metrics + health checks (operational)" 
            echo "3. 🎯 Full monitoring stack with Prometheus + Grafana"
            echo ""
            
            read -p "Monitoring choice (1-3): " monitoring
            case $monitoring in
                1|2|3)
                    deployment_cmd="chmod +x *.sh && ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
                    execution_desc="Standard production deployment with level $monitoring monitoring"
                    execute_deployment "🏭 Standard Production Deployment" "$deployment_cmd" "$execution_desc"
                    ;;
                *)
                    echo -e "${RED}Invalid choice. Using operational monitoring (level 2).${NC}"
                    deployment_cmd="chmod +x *.sh && ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
                    execution_desc="Standard production deployment with operational monitoring"
                    execute_deployment "🏭 Standard Production Deployment" "$deployment_cmd" "$execution_desc"
                    ;;
            esac
            break
            ;;
        3)
            # Enterprise production
            deployment_cmd="./methods/production/master-deploy.sh && ./04_monitoring.sh"
            execution_desc="Full enterprise production with advanced features and comprehensive monitoring"
            execute_deployment "🏢 Enterprise Production Deployment" "$deployment_cmd" "$execution_desc"
            break
            ;;
        4)
            # Testing environment
            deployment_cmd="cd methods/docker-testing && docker-compose up -d"
            execution_desc="Complete testing stack with Prometheus, Grafana, performance tests, and security scanning"
            execute_deployment "🧪 Comprehensive Testing Environment" "$deployment_cmd" "$execution_desc"
            break
            ;;
        5)
            # Network isolation - Now fully integrated
            echo ""
            echo -e "${BLUE}🌐 Advanced Network Setup (Military-Grade Isolation):${NC}"
            echo ""
            echo -e "${WHITE}Network types available:${NC}"
            echo "• ${GREEN}LAN-only${NC}: Secure internal network (192.168.10.x) - Armory PC access"
            echo "• ${CYAN}WAN-only${NC}: Public personnel portal with ACME SSL"  
            echo "• ${PURPLE}Hybrid${NC}: Complete LAN/WAN isolation with dual SSL"
            echo ""
            echo -e "${YELLOW}✨ NEW: Network setup is now fully integrated into modular scripts!${NC}"
            echo -e "${CYAN}All advanced features available during configuration phase.${NC}"
            echo ""
            
            deployment_cmd="chmod +x *.sh && ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
            execution_desc="Integrated network deployment with LAN/WAN/Hybrid options and advanced security"
            execute_deployment "🌐 Network Isolation Deployment (Integrated)" "$deployment_cmd" "$execution_desc"
            break
            ;;
        6)
            # VMware deployment
            deployment_cmd="./methods/vmware-setup/vm-deploy.sh && chmod +x *.sh && ./04_monitoring.sh"
            execution_desc="VMware-optimized deployment with shared folder support"
            execute_deployment "💻 VMware Virtual Machine Deployment" "$deployment_cmd" "$execution_desc"
            break
            ;;
        *)
            echo -e "${RED}Invalid choice. Please select 1-6.${NC}"
            ;;
    esac
done

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                ${WHITE}DEPLOYMENT GUIDANCE COMPLETE${GREEN}                           ║${NC}"
echo -e "${GREEN}║                                                                                  ║${NC}"
echo -e "${GREEN}║  📋 Summary of your deployment approach:                                        ║${NC}"
echo -e "${GREEN}║                                                                                  ║${NC}"
echo -e "${GREEN}║  ✅ No more confusion about which scripts to use                               ║${NC}"  
echo -e "${GREEN}║  ✅ Clear commands provided for your specific needs                            ║${NC}"
echo -e "${GREEN}║  ✅ All legacy scripts archived with systematic approach                       ║${NC}"
echo -e "${GREEN}║  ✨ Advanced network features now integrated in main scripts                   ║${NC}"
echo -e "${GREEN}║                                                                                  ║${NC}"
echo -e "${GREEN}║  📖 For more details: README.md (updated with decision tree)                   ║${NC}"
echo -e "${GREEN}║  🔄 For migration help: MIGRATION_GUIDE.md                                     ║${NC}"
echo -e "${GREEN}║  🌐 Network integration: NETWORK_INTEGRATION_COMPLETE.md                       ║${NC}"
echo -e "${GREEN}║  🏥 Health checks: /usr/local/bin/armguard-health-check                        ║${NC}"
echo -e "${GREEN}║                                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""

exit 0