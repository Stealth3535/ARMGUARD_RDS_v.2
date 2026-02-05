# ArmGuard GitHub Upload Script (Windows PowerShell)

Write-Host "📤 ARMGUARD GITHUB UPLOAD" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (!(Test-Path "manage.py")) {
    Write-Host "❌ Please run this script from the ArmGuard project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Preparing ArmGuard for GitHub upload..." -ForegroundColor Blue

# Check for Git
try {
    git --version | Out-Null
    Write-Host "✅ Git is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Git is not installed. Please install Git for Windows:" -ForegroundColor Red
    Write-Host "   https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

# Initialize git repository if not exists
if (!(Test-Path ".git")) {
    Write-Host "🔧 Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
} else {
    Write-Host "✅ Git repository already exists" -ForegroundColor Green
}

# Add files
Write-Host "📁 Adding files to Git..." -ForegroundColor Yellow
git add .

# Commit
Write-Host "💾 Committing changes..." -ForegroundColor Yellow
$commitMsg = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrEmpty($commitMsg)) {
    $commitMsg = "Initial ArmGuard commit - Production ready military inventory system"
}

git commit -m $commitMsg

Write-Host ""
Write-Host "🌐 GITHUB SETUP INSTRUCTIONS" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

Write-Host ""
Write-Host "📋 Step 1: Create GitHub Repository" -ForegroundColor Yellow
Write-Host "1. Go to: https://github.com/new" -ForegroundColor White
Write-Host "2. Repository name: armguard" -ForegroundColor Green
Write-Host "3. Description: Military Inventory Management System" -ForegroundColor Green
Write-Host "4. Choose Public or Private" -ForegroundColor White
Write-Host "5. DO NOT initialize with README" -ForegroundColor Red
Write-Host ""

Write-Host "📋 Step 2: Connect to GitHub" -ForegroundColor Yellow
Write-Host "Run these commands after creating the repository:" -ForegroundColor White
Write-Host ""
Write-Host "git remote add origin https://github.com/YOURUSERNAME/armguard.git" -ForegroundColor Green
Write-Host "git branch -M main" -ForegroundColor Green  
Write-Host "git push -u origin main" -ForegroundColor Green
Write-Host ""

Write-Host "✅ WHAT'S INCLUDED:" -ForegroundColor Green
Write-Host "• Complete Django military inventory system" -ForegroundColor White
Write-Host "• 55+ deployment tools and guides" -ForegroundColor White
Write-Host "• Raspberry Pi deployment ready" -ForegroundColor White
Write-Host "• HTTPS/SSL security" -ForegroundColor White
Write-Host "• Device authorization" -ForegroundColor White
Write-Host "• Professional documentation" -ForegroundColor White
Write-Host ""

Write-Host "🎉 Ready to upload to GitHub! 🚀" -ForegroundColor Green