# Run API (hot reload) and, if present, the frontend dev server.
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
if (-not (Test-Path (Join-Path $BackendDir 'app\main.py'))) { Stop-Nexzen 'app/main.py not found yet (added in step F2).' }

$procs = @()
try {
    $procs += Start-Process -FilePath $Py -WorkingDirectory $BackendDir -NoNewWindow -PassThru `
        -ArgumentList @('-m', 'uvicorn', 'app.main:create_app', '--factory', '--reload', '--host', '127.0.0.1', '--port', '8000')
    if (Test-Frontend) {
        $npm = (Get-Command npm).Source
        $procs += Start-Process -FilePath $npm -WorkingDirectory $FrontendDir -NoNewWindow -PassThru -ArgumentList @('run', 'dev')
    }
    Write-Info 'Running. Press Ctrl+C to stop.'
    Wait-Process -Id ($procs | ForEach-Object { $_.Id })
} finally {
    foreach ($p in $procs) { if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
}
