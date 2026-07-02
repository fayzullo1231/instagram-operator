#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Instagram endi Zernio.com orqali ulanadi." -ForegroundColor Cyan
Write-Host ""
Write-Host "1. https://zernio.com/dashboard — Instagram ni ulang"
Write-Host "2. .env ga ZERNIO_API_KEY=sk_... qo'shing"
Write-Host "3. python manage.py instagram_check"
Write-Host "4. .\run.ps1"
Write-Host ""
Write-Host "Eski instagram_login (parol/hotspot) endi kerak emas." -ForegroundColor Yellow
