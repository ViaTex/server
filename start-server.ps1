$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$server = $root
$venv = Join-Path $server "venv"
$env:SSL_CERT_FILE = ""

Push-Location $server
Write-Host "Starting FastAPI server..." -ForegroundColor Cyan
Write-Host "  API (Swagger): http://localhost:8000/docs" -ForegroundColor Green
& "$venv\Scripts\uvicorn.exe" app.main:app --reload --host 0.0.0.0 --port 8000
Pop-Location
