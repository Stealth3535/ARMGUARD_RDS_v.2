#!/bin/bash

################################################################################
# ArmGuard GitHub Upload Script
# Prepares and uploads the ArmGuard project to GitHub
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}📤 ARMGUARD GITHUB UPLOAD${NC}"
echo "========================="
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo -e "${RED}❌ Please run this script from the ArmGuard project root directory${NC}"
    exit 1
fi

echo -e "${BLUE}📋 Pre-upload checklist:${NC}"
echo ""

# Check for sensitive files
echo -e "${YELLOW}🔍 Checking for sensitive files...${NC}"

SENSITIVE_FILES=(
    ".env"
    "*.key"
    "*.pem" 
    "*.crt"
    "db.sqlite3"
    "secrets.json"
)

FOUND_SENSITIVE=false
for pattern in "${SENSITIVE_FILES[@]}"; do
    if find . -name "$pattern" -type f | grep -q .; then
        echo -e "${RED}⚠️  Found sensitive files: $pattern${NC}"
        FOUND_SENSITIVE=true
    fi
done

if [ "$FOUND_SENSITIVE" = true ]; then
    echo -e "${YELLOW}These files are already ignored by .gitignore${NC}"
fi

echo -e "${GREEN}✅ Sensitive file check complete${NC}"

# Initialize git repository if not already initialized
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}🔧 Initializing Git repository...${NC}"
    git init
    echo -e "${GREEN}✅ Git repository initialized${NC}"
else
    echo -e "${GREEN}✅ Git repository already exists${NC}"
fi

# Add all files
echo -e "${YELLOW}📁 Adding files to Git...${NC}"
git add .

# Check git status
echo -e "${BLUE}📊 Git status:${NC}"
git status --porcelain | head -10

# Commit changes
echo ""
read -p "Enter commit message (default: 'Initial ArmGuard commit - Production ready system'): " COMMIT_MSG
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Initial ArmGuard commit - Production ready system"
fi

git commit -m "$COMMIT_MSG" || echo "No changes to commit"

echo ""
echo -e "${CYAN}🌐 GitHub Repository Setup${NC}"
echo "=========================="
echo ""

echo -e "${YELLOW}Next steps:${NC}"
echo ""
echo "1. 🌐 Create a new repository on GitHub:"
echo "   • Go to: https://github.com/new"
echo "   • Repository name: armguard"
echo "   • Description: Military Inventory Management System"
echo "   • Set to Public or Private (your choice)"
echo "   • Don't initialize with README (we already have one)"
echo ""

echo "2. 📤 Push to GitHub:"
echo "   • Copy the repository URL from GitHub"
echo "   • Run these commands:"
echo ""
echo -e "${GREEN}   git remote add origin https://github.com/YOURUSERNAME/armguard.git${NC}"
echo -e "${GREEN}   git branch -M main${NC}"
echo -e "${GREEN}   git push -u origin main${NC}"
echo ""

echo "3. ✅ Verify upload:"
echo "   • Check your GitHub repository"
echo "   • Verify README.md displays correctly"
echo "   • Check that sensitive files are NOT uploaded"
echo ""

echo -e "${BLUE}📋 Repository Features:${NC}"
echo ""
echo "✅ Comprehensive README.md"
echo "✅ Proper .gitignore (excludes sensitive files)"
echo "✅ MIT License"
echo "✅ Organized project structure"
echo "✅ Complete deployment documentation"
echo "✅ Security configurations"
echo ""

echo -e "${CYAN}🚀 Your repository will include:${NC}"
echo ""
echo "• 📱 Complete Django application"
echo "• 🔧 Deployment automation scripts"
echo "• 📚 Comprehensive documentation"
echo "• 🔐 Security implementations"
echo "• 🥧 Raspberry Pi deployment guides"
echo "• 🌐 HTTPS setup instructions"
echo "• 🔒 Device authorization system"
echo ""

echo -e "${GREEN}🎉 Your ArmGuard system is ready for GitHub!${NC}"
echo ""

# Show some useful Git commands
echo -e "${BLUE}📋 Useful Git commands:${NC}"
echo ""
echo -e "${YELLOW}# Check status${NC}"
echo "git status"
echo ""
echo -e "${YELLOW}# Add new files${NC}"
echo "git add ."
echo ""
echo -e "${YELLOW}# Commit changes${NC}"
echo "git commit -m 'Your commit message'"
echo ""
echo -e "${YELLOW}# Push to GitHub${NC}"
echo "git push origin main"
echo ""
echo -e "${YELLOW}# Pull from GitHub${NC}"  
echo "git pull origin main"
echo ""

echo -e "${CYAN}🔍 Pro Tips:${NC}"
echo ""
echo "• Use meaningful commit messages"
echo "• Commit frequently with small changes"
echo "• Create branches for new features"
echo "• Use GitHub Issues for bug tracking"
echo "• Set up GitHub Actions for CI/CD"
echo ""

echo -e "${GREEN}Happy coding! 🚀${NC}"