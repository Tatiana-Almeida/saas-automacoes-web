Param(
  [string]$BackendPath = "C:\Users\Tatiana Almeida\Documents\SAAS\SAAS DE AUTOMAÇÕES WEB\backend"
)

Write-Host "Generating migrations for tenants app..."

if (-not (Test-Path $BackendPath)) {
  Write-Error "Backend path not found: $BackendPath"
  exit 1
}

Push-Location $BackendPath

# Try local Python first
if (Get-Command python -ErrorAction SilentlyContinue) {
  Write-Host "Python detected. Using local environment."
  if (-not (Test-Path ".venv")) {
    python -m venv .venv
  }
  if (Test-Path ".venv/Scripts/Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
  }
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  python manage.py makemigrations tenants
  Pop-Location
  exit 0
}

# Fallback to Docker Compose if available
if (Get-Command docker -ErrorAction SilentlyContinue) {
  Write-Host "Python not found. Trying Docker Compose."
  if (Test-Path ".env") {
    docker compose up -d --build
    docker compose exec django python manage.py makemigrations tenants
    Pop-Location
    exit 0
  } else {
    Write-Error "Missing .env in backend. Copy .env.example to .env and configure DATABASE_URL/REDIS_URL."
    Pop-Location
    exit 1
  }
}

Write-Error "Neither local Python nor Docker are available. Install Python or Docker Desktop to proceed."
Pop-Location
exit 1
