# Create venv, install dependencies, create .env. Safe to re-run.
. (Join-Path $PSScriptRoot '_common.ps1')

$pyCmd = $null
foreach ($candidate in @('python3.12', 'python', 'python3')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        & $candidate -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)'
        if ($LASTEXITCODE -eq 0) { $pyCmd = $candidate; break }
    }
}
if (-not $pyCmd) { Stop-Nexzen 'Python 3.12 required but not found.' }

if (-not (Test-Path $Py)) {
    Write-Info "Creating virtualenv at $VenvDir"
    Invoke-Checked $pyCmd @('-m', 'venv', $VenvDir)
}
Write-Info 'Installing backend dependencies'
Invoke-Checked $Py @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-Checked $Py @('-m', 'pip', 'install', '-r', (Join-Path $BackendDir 'requirements-dev.txt'))

$envFile = Join-Path $RootDir '.env'
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $RootDir '.env.example') $envFile
    Write-Info 'Created .env from .env.example - edit it and replace every CHANGE_ME.'
}

if (Test-Frontend) {
    Assert-Command 'npm' 'Install Node.js 20+.'
    Write-Info 'Installing frontend dependencies'
    Push-Location $FrontendDir
    try { npm install; if ($LASTEXITCODE -ne 0) { Stop-Nexzen 'npm install failed' } } finally { Pop-Location }
} else {
    Write-Info 'frontend/package.json not found yet (added in step F9) - skipping.'
}

if (-not (Get-Command psql -ErrorAction SilentlyContinue)) { Write-Info 'WARNING: psql not found. Install PostgreSQL 16.' }
if (-not (Get-Command redis-cli -ErrorAction SilentlyContinue)) { Write-Info 'WARNING: redis-cli not found. Install Redis 7.' }
Write-Info 'Setup complete.'
