# Local hosting launcher: starts the FastAPI backend and the Vite frontend
# bound to all interfaces (LAN-accessible), detached with log files.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\serve_local.ps1
#        (or double-click start_local.bat at the project root)

$root = (Resolve-Path "$PSScriptRoot\..").Path
$logs = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$pythonExe = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    $pythonExe = "python"
}

function Stop-Matching([string]$pattern) {
    try {
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -match $pattern } | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Output "stopped: $($_.ProcessName) (PID $($_.ProcessId))"
        }
    } catch {}
}

Write-Output "=== stopping previous instances ==="
Stop-Matching "uvicorn backend.app.main"
Stop-Matching "vite"

Write-Output "=== starting backend  : http://localhost:8000 (docs: /docs) ==="
Start-Process -FilePath $pythonExe `
    -ArgumentList "-m","uvicorn","backend.app.main:app","--host","0.0.0.0","--port","8000" `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs "backend.log") `
    -RedirectStandardError  (Join-Path $logs "backend.err.log")

Write-Output "=== starting frontend : http://localhost:5173 ==="
Start-Process -FilePath "cmd" `
    -ArgumentList "/c","npx vite --host 0.0.0.0 --port 5173 > ..\logs\frontend.log 2>&1" `
    -WorkingDirectory (Join-Path $root "frontend") -WindowStyle Hidden

Start-Sleep -Seconds 2

$lan = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" } |
        Select-Object -First 1).IPAddress

Write-Output ""
Write-Output "==============================================================="
Write-Output "  AURA is hosted locally"
Write-Output "  This PC : http://localhost:5173"
if ($lan) { Write-Output "  LAN     : http://$lan`:5173   (same Wi-Fi devices)" }
Write-Output "  API     : http://localhost:8000  | docs: /docs"
Write-Output "  Logs    : logs\backend.log, logs\frontend.log"
Write-Output "==============================================================="

Start-Process "http://localhost:5173/"
