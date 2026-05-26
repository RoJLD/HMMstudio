# hmm-studio launcher (idempotent). Builds the image if needed, starts the
# container via Rancher Desktop's Docker engine, waits for the API to be
# healthy, then opens the UI in the default browser.
#
# Stale-detection strategy : always run `docker compose build` (Docker layer
# cache makes it fast if nothing changed), then compare the image SHA before
# and after. If the SHA changed, the running container is on the old image
# and gets recreated. If unchanged AND container is up, just open the browser.
#
# This is Docker-aware : the comparison is on the image, not on the host's
# server/static/ directory (which is NOT mounted into the container — the
# Dockerfile copies the built bundle in at image-build time).

# NOTE : we do NOT set $ErrorActionPreference = "Stop" globally because under
# Windows PowerShell that turns every native-command stderr write into a
# NativeCommandError (e.g. `docker info` emits "WARNING: No swap limit
# support" on Linux daemons → script aborts). Each step below checks
# $LASTEXITCODE explicitly instead.
Set-Location -Path $PSScriptRoot

# --- 1. Docker daemon reachable? Try to auto-start Rancher / Docker Desktop. ---
function Test-Docker {
    docker info *>$null
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

# --- 2. Release stale container from a previous compose project, if any ---
$exists = docker ps -aq --filter "name=^hmm-studio$" 2>$null
if ($exists) {
    $project = docker inspect hmm-studio --format '{{ index .Config.Labels "com.docker.compose.project" }}' 2>$null
    if ($project -and $project -ne "hmm-studio") {
        Write-Host "Releasing hmm-studio from previous compose project ($project)..." -ForegroundColor Yellow
        docker rm -f hmm-studio *>$null
    }
}

# --- 3. Refresh image. Layer cache makes this fast when nothing changed. ---
Write-Host "Checking image freshness..." -ForegroundColor Cyan
$beforeId = (docker images -q hmm-studio:latest 2>$null | Select-Object -First 1)

docker compose build *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  docker compose build failed. Check 'docker compose build' output." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$afterId = (docker images -q hmm-studio:latest 2>$null | Select-Object -First 1)
$imageChanged = ($beforeId -ne $afterId)

if (-not $beforeId) {
    Write-Host "Built image hmm-studio:latest ($afterId) for the first time." -ForegroundColor Yellow
} elseif ($imageChanged) {
    Write-Host "Image rebuilt (was $beforeId -> now $afterId)." -ForegroundColor Yellow
} else {
    Write-Host "Image unchanged ($afterId)." -ForegroundColor DarkGray
}

# --- 4. Already running with the current image? Just open the browser. ---
$running = docker ps -q --filter "name=^hmm-studio$" --filter "status=running" 2>$null
if ($running -and -not $imageChanged) {
    Write-Host "hmm-studio is already running on the current image. Opening UI..." -ForegroundColor Green
    Start-Process "http://localhost:8000"
    exit 0
}

if ($running -and $imageChanged) {
    Write-Host "Recreating container on the new image..." -ForegroundColor Yellow
    docker compose down *>$null
}

# --- 5. Start services ---
Write-Host "Starting services..." -ForegroundColor Cyan
docker compose up -d *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  docker compose up failed. Check 'docker compose logs' for details." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# --- 6. Wait for API health ---
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

# --- 7. Open the UI ---
# The server now sends Cache-Control: no-store on index.html (since
# 2026-05-26) so future reloads always pick up the latest asset hashes.
# We also append a launch-time cachebust query so browsers carrying a
# pre-fix cached index.html see a "new URL" and refetch on the very
# first visit after upgrading.
$cachebust = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$urlClean = "http://localhost:8000"
$urlBusted = "${urlClean}/?_=$cachebust"

Write-Host ""
Write-Host "  hmm-studio is up." -ForegroundColor Green
Write-Host "  UI:   $urlClean" -ForegroundColor Green
Write-Host "  API:  $urlClean/docs (Swagger)" -ForegroundColor Green
Write-Host ""
Start-Process $urlBusted
