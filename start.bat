@echo off
REM hmm-studio launcher (idempotent). Builds the image if needed, starts the
REM container via Rancher Desktop's Docker engine, waits for the API to be
REM healthy, then opens the UI in the default browser.
REM
REM To create a desktop shortcut: right-click this file, "Send to" -> "Desktop
REM (create shortcut)". Rename to "hmm-studio" if you like.

setlocal
cd /d "%~dp0"

echo.
echo === hmm-studio launcher ===
echo.

REM --- 1. Docker daemon reachable? Try to auto-start Rancher / Docker Desktop. ---
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok

set "DOCKER_APP="
if exist "%ProgramFiles%\Rancher Desktop\Rancher Desktop.exe" set "DOCKER_APP=%ProgramFiles%\Rancher Desktop\Rancher Desktop.exe"
if not defined DOCKER_APP if exist "%LOCALAPPDATA%\Programs\Rancher Desktop\Rancher Desktop.exe" set "DOCKER_APP=%LOCALAPPDATA%\Programs\Rancher Desktop\Rancher Desktop.exe"
if not defined DOCKER_APP if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" set "DOCKER_APP=%ProgramFiles%\Docker\Docker\Docker Desktop.exe"

if not defined DOCKER_APP (
    echo Docker is not reachable and no Rancher / Docker Desktop install was found.
    echo Start it manually then relaunch.
    echo.
    pause
    exit /b 1
)

echo Docker daemon not reachable. Starting "%DOCKER_APP%" ...
start "" "%DOCKER_APP%"

set /a dcount=0
:waitdocker
timeout /t 2 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto dockerready
set /a dcount+=1
if %dcount% geq 90 (
    echo Docker did not become reachable within 180s. Open Rancher / Docker Desktop and retry.
    pause
    exit /b 1
)
goto waitdocker
:dockerready
echo Docker is up.
:docker_ok

REM --- 2. Frontend stale-check (React tweak triggers a rebuild even if ---
REM --- the container is already up). Exit 1 from the helper = needs rebuild. ---
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_frontend_stale.ps1"
set "FRONTEND_STALE=%errorlevel%"

REM --- 3. Already up? Open the browser unless the frontend is stale. ---
set "ALREADY_RUNNING="
for /f %%i in ('docker ps -q --filter "name=^hmm-studio$" --filter "status=running" 2^>nul') do set "ALREADY_RUNNING=1"

if defined ALREADY_RUNNING (
    if "%FRONTEND_STALE%"=="0" (
        echo hmm-studio is already running. Opening UI...
        start "" "http://localhost:8000"
        exit /b 0
    ) else (
        echo Stopping running container to apply frontend rebuild...
        docker compose down >nul 2>&1
    )
)

REM --- 4. Release stale container name from a previous compose project ---
docker rm -f hmm-studio >nul 2>&1

REM --- 5. Build (no-op if cached) and start ---
echo Starting (first run takes ~2-3 min on a cold image)...
docker compose up -d --build
if errorlevel 1 (
    echo.
    echo docker compose up failed. Try 'docker compose logs' in this folder.
    pause
    exit /b 1
)

REM --- 5. Wait for API health (60s max) ---
echo Waiting for API on :8000 ...
set /a count=0
:wait
curl -sf -o nul http://localhost:8000/health 2>nul
if not errorlevel 1 goto ready
set /a count+=1
if %count% geq 60 (
    echo API did not respond within 60s. Check 'docker compose logs hmm-studio'.
    pause
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait
:ready

echo.
echo === hmm-studio is up ===
echo   UI:   http://localhost:8000
echo   API:  http://localhost:8000/docs (Swagger)
echo.

start "" "http://localhost:8000"
endlocal
