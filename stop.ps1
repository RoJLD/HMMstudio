# Graceful stop. Containers are stopped but kept (faster restart via start.ps1).
# For full teardown (also remove containers, but the named volume survives),
# run: docker compose down
# To also wipe data: docker compose down -v

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
docker compose stop
Write-Host "hmm-studio stopped. Run .\start.ps1 to bring it back." -ForegroundColor Cyan
