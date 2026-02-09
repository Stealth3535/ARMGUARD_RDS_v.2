#!/bin/bash

# =============================================================================
# DEPRECATED: deploy-master.sh wrapper
# =============================================================================
# ⚠️  WARNING: This script has been DEPRECATED and moved to legacy_archive/
# ✨  NEW: Use the modular deployment system instead!
# =============================================================================

echo ""
echo "🚨========================================================================🚨"
echo "⚠️                           DEPRECATED SCRIPT                           ⚠️"
echo "🚨========================================================================🚨"
echo ""
echo "❌ deploy-master.sh has been replaced by the modular deployment system!"
echo ""
echo "✨ NEW RECOMMENDED APPROACH:"
echo "   🎯 For ALL deployments: Use the 4-script modular sequence"
echo "   📁 Location: Same directory (01_setup.sh → 02_config.sh → 03_services.sh → 04_monitoring.sh)"
echo ""
echo "🔄 QUICK MIGRATION:"
echo "   Instead of: ./deploy-master.sh [method]"
echo "   Use this:   ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
echo ""
echo "🏭 ENTERPRISE METHODS (if needed):"
echo "   • Production:     ./methods/production/master-deploy.sh"
echo "   • Docker Testing: ./methods/docker-testing/ (docker-compose up)"
echo "   • VMware Setup:   ./methods/vmware-setup/vm-deploy.sh"
echo ""
echo "📖 COMPREHENSIVE GUIDE: ./README.md"
echo "🔍 LEGACY SCRIPT: ./legacy_archive/deploy-master.sh (for reference only)"
echo ""
echo "🚨========================================================================🚨"
echo ""

read -p "Do you want to run the NEW modular deployment instead? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting modular deployment sequence..."
    echo ""
    
    if [[ -f "01_setup.sh" && -f "02_config.sh" && -f "03_services.sh" && -f "04_monitoring.sh" ]]; then
        echo "✅ All modular scripts found. Executing sequence..."
        chmod +x 01_setup.sh 02_config.sh 03_services.sh 04_monitoring.sh
        ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh
    else
        echo "❌ Modular scripts not found. Please check the directory."
        echo "📖 See README.md for setup instructions."
        exit 1
    fi
else
    echo "❌ Deployment cancelled."
    echo "📖 Please read README.md for the new deployment approach."
    echo ""
    exit 1
fi