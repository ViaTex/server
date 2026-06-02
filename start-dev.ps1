# DishaSetu - One-command dev start
# Run from project root: .\start-dev.ps1 (or double-click start-dev.bat)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$server = $root
$venv = Join-Path $server "venv"

# Fix SSL cert issue on this machine
$env:SSL_CERT_FILE = ""

# --- Prerequisite checks --------------------------

Write-Host "`n=== Checking prerequisites ===" -ForegroundColor Cyan

# Docker
$dockerOk = $true
try { $null = docker compose version 2>&1 } catch { $dockerOk = $false }
if (-not $dockerOk) {
  Write-Host "  Warning: Docker Compose not found" -ForegroundColor Yellow
  Write-Host "     Install Docker Desktop from: https://docs.docker.com/desktop/setup/install/windows-install/" -ForegroundColor Yellow
  Write-Host "     Or run PostgreSQL 16 + Redis 7 manually and skip docker compose up" -ForegroundColor Yellow
  Write-Host "     Continuing with Docker step skipped..." -ForegroundColor Yellow
}

# Python
try {
  $pyVer = & "$venv\Scripts\python.exe" --version 2>&1
  if ($pyVer -match "Python 3\.11") {
    Write-Host "  OK  $pyVer (venv)" -ForegroundColor Green
  } else {
    Write-Host "  Warning: $pyVer (venv) - expected Python 3.11.x" -ForegroundColor Yellow
  }
} catch {
  try {
    $pyVer = & "python" --version 2>&1
    if ($pyVer -match "Python 3\.11") {
      Write-Host "  OK  $pyVer (system)" -ForegroundColor Green
    } else {
      Write-Host "  FAIL $pyVer - expected Python 3.11.x" -ForegroundColor Red
      Write-Host "  Install from: https://www.python.org/downloads/release/python-3110/" -ForegroundColor Yellow
    }
  } catch {
    Write-Host "  FAIL Python not found" -ForegroundColor Red
    Write-Host "  Install from: https://www.python.org/downloads/release/python-3110/" -ForegroundColor Yellow
  }
}

# Node.js
try {
  $nodeVer = & "node" --version 2>&1
  Write-Host "  OK  Node.js $nodeVer" -ForegroundColor Green
} catch {
  Write-Host "  FAIL Node.js not found - install from https://nodejs.org/" -ForegroundColor Yellow
}

Write-Host ""

# --- Start infrastructure -------------------------

if ($dockerOk) {
  Write-Host "=== 1/4 Starting Docker (PostgreSQL + Redis) ===" -ForegroundColor Cyan
  docker compose up -d
} else {
  Write-Host "=== 1/4 Skipping Docker (PostgreSQL + Redis assumed running manually) ===" -ForegroundColor Cyan
}

# --- Install deps ---------------------------------

Write-Host "=== 2/4 Installing backend dependencies ===" -ForegroundColor Cyan
& "$venv\Scripts\python.exe" -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r (Join-Path $server "requirements.txt") --quiet

# --- Smart DB check: migrate ---

Write-Host "=== 3/4 Running database migrations ===" -ForegroundColor Cyan
Push-Location $server
& "$venv\Scripts\alembic.exe" upgrade head

# --- Start server ---------------------------------

Write-Host "=== 4/4 Starting FastAPI backend ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "  API (Swagger):  http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
& "$venv\Scripts\uvicorn.exe" app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
