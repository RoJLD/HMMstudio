# Returns whether the built frontend bundle is stale vs the frontend source.
#
# Exit code :
#   0 -> bundle is UP TO DATE (no rebuild needed)
#   1 -> bundle is STALE (start.ps1 / start.bat will trigger a rebuild)
#
# Detection :
#   Compare the max mtime under src\hmm_studio\frontend\src\** and a handful
#   of frontend config files (package.json, vite.config.ts, tsconfig.json,
#   tailwind.config.js, postcss.config.js) against the mtime of the built
#   src\hmm_studio\server\static\index.html.
#
# Called by both launchers (start.ps1 native, start.bat via
# powershell -ExecutionPolicy Bypass -File). Standalone usage is also fine
# for "should I rebuild before pushing ?" sanity checks.

$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "..")

$staticOutput = "src\hmm_studio\server\static\index.html"
$frontendDir = "src\hmm_studio\frontend"

if (-not (Test-Path $staticOutput)) {
    Write-Host "Frontend stale : no built bundle at $staticOutput." -ForegroundColor Yellow
    exit 1
}

$staticMtime = (Get-Item $staticOutput).LastWriteTime

# Collect watched files.
$watched = New-Object System.Collections.Generic.List[System.IO.FileInfo]
$srcDir = Join-Path $frontendDir "src"
if (Test-Path $srcDir) {
    Get-ChildItem -Path $srcDir -Recurse -File -ErrorAction SilentlyContinue |
        ForEach-Object { $watched.Add($_) }
}
foreach ($cfg in @("package.json", "vite.config.ts", "tsconfig.json", "tailwind.config.js", "postcss.config.js", "index.html")) {
    $cfgPath = Join-Path $frontendDir $cfg
    if (Test-Path $cfgPath) { $watched.Add((Get-Item $cfgPath)) }
}

if ($watched.Count -eq 0) {
    # No watched files — treat as up to date (don't trigger an empty rebuild).
    Write-Host "Frontend up to date (no watched files; static bundle date $($staticMtime.ToString('yyyy-MM-dd HH:mm:ss')))." -ForegroundColor DarkGray
    exit 0
}

$newest = $watched |
    Sort-Object -Property LastWriteTime -Descending |
    Select-Object -First 1

if ($newest.LastWriteTime -gt $staticMtime) {
    $rel = Resolve-Path -Path $newest.FullName -Relative
    Write-Host "Frontend stale : $rel modified $($newest.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss')) > bundle $($staticMtime.ToString('yyyy-MM-dd HH:mm:ss'))." -ForegroundColor Yellow
    exit 1
}

Write-Host "Frontend up to date (bundle $($staticMtime.ToString('yyyy-MM-dd HH:mm:ss')) >= newest source)." -ForegroundColor DarkGray
exit 0
