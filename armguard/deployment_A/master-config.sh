#!/bin/bash

# =============================================================================
# DEPRECATED: master-config.sh wrapper  
# =============================================================================
# ⚠️  WARNING: This script has been DEPRECATED and moved to legacy_archive/
# ✨  NEW: Configuration is now handled by the modular system!
# =============================================================================

echo ""
echo "🚨========================================================================🚨"
echo "⚠️                           DEPRECATED SCRIPT                           ⚠️"
echo "🚨========================================================================🚨"
echo ""
echo "❌ master-config.sh has been replaced by the modular configuration system!"
echo ""
echo "✨ NEW CONFIGURATION APPROACH:"
echo "   🎯 Configuration: Use ./02_config.sh (interactive setup)"
echo "   🔧 Environment:   Use ./01_setup.sh (system setup)"
echo "   📊 Monitoring:    Use ./04_monitoring.sh (health checks)"
echo ""
echo "🔄 QUICK MIGRATION:"
echo "   Instead of: source master-config.sh"
echo "   Use this:   ./02_config.sh (handles all configuration interactively)"
echo ""
echo "📖 COMPREHENSIVE GUIDE: ./README.md"
echo "🔍 LEGACY SCRIPT: ./legacy_archive/master-config.sh (for reference only)"
echo ""
echo "🚨========================================================================🚨"
echo ""

read -p "Do you want to run the NEW configuration system instead? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🚀 Starting configuration setup..."
    echo ""
    
    if [[ -f "02_config.sh" ]]; then
        echo "✅ Configuration script found. Executing..."
        chmod +x 02_config.sh
        ./02_config.sh
    else
        echo "❌ 02_config.sh not found. Please check the directory."
        echo "📖 See README.md for setup instructions."
        exit 1
    fi
else
    echo "❌ Configuration cancelled." 
    echo "📖 Please read README.md for the new configuration approach."
    echo ""
    exit 1
fi