# hmm-studio launcher (idempotent). Builds the image if needed, starts the
# container via Rancher Desktop's Docker engine, waits for the API to be
# healthy, then opens the UI in the default browser.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# --- 1. Docker daemon reachable? Try to auto-start Rancher / Docker Desktop. ---
function Test-Docker {
    $null = docker info 2>&1
    return ($LASTEXITCODE -eq 0)
}

if (-not (Test-Docker)) {
    $candidates = @(
        "$env:ProgramFiles\Rancher Desktop\Rancher Desktop.exe",
        "$env:LOCALAPPDATA\Programs\Rancher Desktop\Rancher Desktop.exe",
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    )
    $dockerApp = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $dockerApp) {
        Write-Host ""
        Write-Host "  Docker is not reachable and no Rancher / Docker Desktop install was found." -ForegroundColor Red
        Write-Host "  Start it manually then relaunch." -ForegroundColor Red
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }

    Write-Host "Docker daemon not reachable. Starting `"$dockerApp`" ..." -ForegroundColor Yellow
    Start-Process -FilePath $dockerApp

    $timeoutSec = 180
    $start = Get-Date
    $ready = $false
    while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
        Start-Sleep -Seconds 2
        if (Test-Docker) { $ready = $true; break }
    }

    if (-not $ready) {
        Write-Host "  Docker did not become reachable within ${timeoutSec}s. Open Rancher / Docker Desktop and retry." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Docker is up." -ForegroundColor Green
}

# --- 2. Already running? Just open the browser. ---
$running = docker ps -q --filter "name=^hmm-studio$" --filter "status=running" 2>$null
if ($running) {
    Write-Host "hmm-studio is already running. Opening UI..." -ForegroundColor Green
    Start-Process "http://localhost:8000"
    exit 0
}

# --- 3. Release stale container from a previous compose project, if any ---
$exists = docker ps -aq --filter "name=^hmm-studio$" 2>$null
if ($exists) {
    $project = docker inspect hmm-studio --format '{{ index .Config.Labels "com.docker.compose.project" }}' 2>$null
    if ($project -and $project -ne "hmm-studio") {
        Write-Host "Releasing hmm-studio from previous compose project ($project)..." -ForegroundColor Yellow
        docker rm -f hmm-studio 2>&1 | Out-Null
    }
}

# --- 4. Build (no-op if cached) and start ---
Write-Host "Building image (first run takes ~2-3 min)..." -ForegroundColor Cyan
docker compose build 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  docker compose build failed. Check 'docker compose build' output." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting services..." -ForegroundColor Cyan
docker compose up -d 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  docker compose up failed. Check 'docker compose logs' for details." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- 5. Wait for API health ---
Write-Host "Waiting for hmm-studio on http://localhost:8000 ..." -ForegroundColor Cyan
$timeoutSec = 60
$start = Get-Date
$ready = $false
while (((Get-Date) - $start).TotalSeconds -lt $timeoutSec) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $ready) {
    Write-Host "  API did not respond within ${timeoutSec}s. Check 'docker compose logs hmm-studio'." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- 6. Open the UI ---
Write-Host ""
Write-Host "  hmm-studio is up." -ForegroundColor Green
Write-Host "  UI:   http://localhost:8000" -ForegroundColor Green
Write-Host "  API:  http://localhost:8000/docs (Swagger)" -ForegroundColor Green
Write-Host ""
Start-Process "http://localhost:8000"
