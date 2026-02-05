# Install mkcert on Windows to trust HTTPS certificates

Write-Host "🔒 Installing mkcert on Windows for trusted HTTPS" -ForegroundColor Cyan
Write-Host ""

Write-Host "📋 Option 1: Using Chocolatey (Recommended)" -ForegroundColor Yellow
Write-Host "If you have Chocolatey installed:" -ForegroundColor White
Write-Host "  choco install mkcert" -ForegroundColor Green
Write-Host "  mkcert -install" -ForegroundColor Green
Write-Host ""

Write-Host "📋 Option 2: Manual Download" -ForegroundColor Yellow
Write-Host "1. Download mkcert for Windows from:" -ForegroundColor White
Write-Host "   https://github.com/FiloSottile/mkcert/releases" -ForegroundColor Cyan
Write-Host "2. Download: mkcert-v1.4.4-windows-amd64.exe" -ForegroundColor White
Write-Host "3. Rename to: mkcert.exe" -ForegroundColor White
Write-Host "4. Run in PowerShell (as Administrator):" -ForegroundColor White
Write-Host "   .\mkcert.exe -install" -ForegroundColor Green
Write-Host ""

Write-Host "📋 Option 3: Using Scoop" -ForegroundColor Yellow
Write-Host "If you have Scoop installed:" -ForegroundColor White  
Write-Host "  scoop install mkcert" -ForegroundColor Green
Write-Host "  mkcert -install" -ForegroundColor Green
Write-Host ""

Write-Host "🎯 After installing mkcert on Windows:" -ForegroundColor Green
Write-Host "1. The CA certificate will be added to Windows certificate store" -ForegroundColor White
Write-Host "2. Restart your browser" -ForegroundColor White  
Write-Host "3. Visit https://192.168.0.177 - no more warnings!" -ForegroundColor White
Write-Host ""

Write-Host "🚀 Alternative: Quick Manual Trust" -ForegroundColor Yellow
Write-Host "If you don't want to install mkcert:" -ForegroundColor White
Write-Host "1. Click 'Advanced' on the warning page" -ForegroundColor White
Write-Host "2. Click 'Proceed to 192.168.0.177'" -ForegroundColor White
Write-Host "3. In Chrome, click the padlock icon → Certificate → Details → Copy to File" -ForegroundColor White
Write-Host "4. Install the certificate in Windows Trusted Root Certification Authorities" -ForegroundColor White