# SHADOWLINK Demo Dashboard Launcher
param(
    [string]$HostAddress = "127.0.0.1",
    [int]$Port = 8000
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  SHADOWLINK: Defensive Privacy Re-identification Platform" -ForegroundColor Cyan
Write-Host "  Interactive University Demo Dashboard" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard URL : http://$HostAddress`:$Port/demo" -ForegroundColor Green
Write-Host "  API Docs URL  : http://$HostAddress`:$Port/docs" -ForegroundColor Yellow
Write-Host "  Health Status : http://$HostAddress`:$Port/health" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Ctrl+C to terminate the server." -ForegroundColor Gray
Write-Host ""

$pythonCmd = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $pythonCmd -m uvicorn shadowlink.api.app:app --host $HostAddress --port $Port

