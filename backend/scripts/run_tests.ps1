param(
    [string]$Py = "python"
)

# Try local Python venv or system, else fallback to Docker Compose
Write-Host "Running backend tests..."

function Run-LocalTests {
    Write-Host "Attempting local pytest..."
    $venvActivate = Join-Path $PWD ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        & $venvActivate
    }
    & $Py -m pip --version | Out-Null
    & $Py -m pip install -r requirements.txt
    if (Test-Path "requirements-dev.txt") {
        & $Py -m pip install -r requirements-dev.txt
    }
    & $Py -m pytest -q
}

function Run-DockerTests {
    Write-Host "Falling back to Docker Compose pytest..."
    docker compose exec django python -m pytest -q
}

try {
    Run-LocalTests
}
catch {
    Write-Warning "Local run failed: $($_.Exception.Message)"
    try { Run-DockerTests } catch { Write-Error "Docker run failed: $($_.Exception.Message)" }
}
