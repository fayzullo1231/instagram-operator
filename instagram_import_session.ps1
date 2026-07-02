#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$SessionFile
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Avval .\run.ps1 ni bir marta ishga tushiring" -ForegroundColor Yellow
    exit 1
}

.\.venv\Scripts\python.exe manage.py instagram_import_session $SessionFile
