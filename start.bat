@echo off
REM hmm-studio launcher (idempotent). Builds the image if needed, starts the
REM container via Rancher Desktop's Docker engine, waits for the API to be
REM healthy, then opens the UI in the default browser.
REM
REM Stale-detection strategy : always run `docker compose build` (Docker layer
REM cache makes it fast if nothing changed), then compare the image SHA before
REM and after. If the SHA changed, the running container is on the old image
REM and gets recreated. If unchanged AND container is up, just open the browser.
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

REM --- 2. Release stale container name from a previous compose project ---
docker rm -f hmm-studio >nul 2>&1

REM --- 3. Capture image SHA before build, refresh, then re-capture ---
echo Checking image freshness...
for /f "delims=" %%i in ('docker images -q hmm-studio:latest 2^>nul') do set "BEFORE_ID=%%i"

docker compose build >nul 2>&1
if errorlevel 1 (
    echo docker compose build failed. Try 'docker compose build' for details.
    pause
    exit /b 1
)

for /f "delims=" %%i in ('docker images -q hmm-studio:latest 2^>nul') do set "AFTER_ID=%%i"

set "IMAGE_CHANGED=0"
if not "%BEFORE_ID%"=="%AFTER_ID%" set "IMAGE_CHANGED=1"

if "%BEFORE_ID%"=="" (
    echo Built image hmm-studio:latest %AFTER_ID% for the first time.
) else if "%IMAGE_CHANGED%"=="1" (
    echo Image rebuilt: was %BEFORE_ID% -^> now %AFTER_ID%.
) else (
    echo Image unchanged: %AFTER_ID%.
)

REM --- 4. Already running with the current image? Just open the browser. ---
set "ALREADY_RUNNING=0"
for /f %%i in ('docker ps -q --filter "name=^hmm-studio$" --filter "status=running" 2^>nul') do set "ALREADY_RUNNING=1"

if "%ALREADY_RUNNING%"=="1" if "%IMAGE_CHANGED%"=="0" (
    echo hmm-studio is already running on the current image. Opening UI...
    start "" "http://localhost:8000"
    exit /b 0
)

if "%ALREADY_RUNNING%"=="1" if "%IMAGE_CHANGED%"=="1" (
    echo Recreating container on the new image...
    docker compose down >nul 2>&1
)

REM --- 5. Start services ---
echo Starting services...
docker compose up -d
if errorlevel 1 (
    echo docker compose up failed. Try 'docker compose logs' in this folder.
    pause
    exit /b 1
)

REM --- 6. Wait for API health (60s max) ---
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

REM Cache-bust query : the server now sends Cache-Control: no-store on
REM index.html (since 2026-05-26) but a pre-fix cached index.html in the
REM browser may persist. A timestamped query makes the URL look "new"
REM so the browser refetches at least on the first visit after upgrading.
for /f %%i in ('powershell -NoProfile -Command "[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()"') do set "CACHEBUST=%%i"
start "" "http://localhost:8000/?_=%CACHEBUST%"
endlocal
