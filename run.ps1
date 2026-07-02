#Requires -Version 5.1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Instagram AI Operator ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    python -m venv .venv
}
. .\.venv\Scripts\Activate.ps1

$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"
pip install -r requirements.txt -q

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env yaratildi - sozlamalarni toldiring!" -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "data" | Out-Null

Write-Host -NoNewline "Migratsiya... "
python manage.py migrate --noinput --verbosity 0
if ($LASTEXITCODE -ne 0) {
    Write-Host "XATO" -ForegroundColor Red
    exit 1
}
Write-Host "OK" -ForegroundColor Green

Write-Host ""
Write-Host "Server:  http://localhost:8000" -ForegroundColor Green
Write-Host "Chat:    http://localhost:8000/api/v1/chat" -ForegroundColor Green
Write-Host "Toxtatish: Ctrl+C" -ForegroundColor DarkGray
Write-Host ""

python manage.py runserver 0.0.0.0:8000 --verbosity 1
