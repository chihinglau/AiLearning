#requires -Version 5.1
<#
  AiLearning backend environment setup (local venv, no system-wide installs).
  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\setup-backend.ps1
#>
[CmdletBinding()]
param(
  [string]$Root = '',
  [string]$Python = ''
)
$ErrorActionPreference = 'Stop'

if (-not $Root) { $Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path }
$Backend = Join-Path $Root 'backend'
if (-not (Test-Path (Join-Path $Backend 'requirements.txt'))) { throw "backend not found: $Backend" }

if (-not $Python) {
  $candidate = Join-Path $Root '.tools\Python312\python.exe'
  if (Test-Path $candidate) { $Python = $candidate } else { $Python = 'python' }
}

$venv = Join-Path $Backend '.venv'
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
  Write-Host "Creating venv: $venv ($Python)" -ForegroundColor Cyan
  & $Python -m venv $venv
}
$py = Join-Path $venv 'Scripts\python.exe'

Write-Host 'Installing backend dependencies...' -ForegroundColor Cyan
& $py -m pip install --upgrade pip -q
& $py -m pip install -r (Join-Path $Backend 'requirements-dev.txt')

Write-Host 'Applying migrations + seed data...' -ForegroundColor Cyan
Push-Location $Backend
try {
  & $py -m alembic upgrade head
  & $py -m scripts.seed
} finally { Pop-Location }

Write-Host '[DONE] backend ready. Start with:' -ForegroundColor Green
Write-Host '  cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 18080'
