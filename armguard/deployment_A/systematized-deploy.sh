#!/bin/bash

# =============================================================================
# DEPRECATED: systematized-deploy.sh wrapper
# =============================================================================
# ⚠️  WARNING: This script has been DEPRECATED and moved to legacy_archive/
# ✨  NEW: Use the improved modular deployment system!
# =============================================================================

echo ""
echo "🚨========================================================================🚨"
echo "⚠️                           DEPRECATED SCRIPT                           ⚠️" 
echo "🚨========================================================================🚨"
echo ""
echo "❌ systematized-deploy.sh has been REPLACED by the modular system!"
echo ""
echo "✨ IMPROVED SYSTEMATIZED APPROACH:"
echo "   🎯 01_setup.sh     → Environment & Prerequisites"
echo "   🔧 02_config.sh    → SSL & Django Configuration"
echo "   🚀 03_services.sh  → Service Deployment"
echo "   📊 04_monitoring.sh→ Health & Monitoring"
echo ""
echo "🔄 MIGRATION PATH:"
echo "   Old: ./systematized-deploy.sh"
echo "   New: ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh"
echo ""
echo "✨ ADVANTAGES OF NEW SYSTEM:"
echo "   • Better error handling and recovery"
echo "   • Modular - can run individual phases"
echo "   • Enhanced monitoring options"
echo "   • Improved SSL certificate management"
echo ""
echo "📖 COMPREHENSIVE GUIDE: ./README.md"
echo "🔍 LEGACY SCRIPT: ./legacy_archive/systematized-deploy.sh (reference only)"
echo ""
echo "🚨========================================================================🚨"
echo ""

read -p "Do you want to run the NEW modular deployment instead? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting improved modular deployment..."
    echo ""
    
    if [[ -f "01_setup.sh" ]]; then
        echo "✅ Starting modular deployment sequence..."
        chmod +x *.sh 2>/dev/null
        ./01_setup.sh && ./02_config.sh && ./03_services.sh && ./04_monitoring.sh
    else
        echo "❌ Modular scripts not found. Please check the directory."
        exit 1
    fi
else
    echo "❌ Deployment cancelled."
    echo "📖 Please read README.md for migration guidance."
    exit 1
fi