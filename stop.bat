@echo off
REM Graceful stop. Containers are stopped but kept (faster restart via start.bat).
REM For full teardown (also remove containers, but the named volume survives),
REM run: docker compose down
REM To also wipe data: docker compose down -v

setlocal
cd /d "%~dp0"
docker compose stop
echo.
echo hmm-studio stopped. Run start.bat to bring it back.
endlocal
