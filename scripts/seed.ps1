# Seed baseline data: permissions, roles, first admin (added in steps F5-F6).
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
if (-not (Test-Path (Join-Path $BackendDir 'app\seed.py'))) { Stop-Nexzen 'Seed module not available yet (added in steps F5-F6).' }
Push-Location $BackendDir
try { Invoke-Checked $Py @('-m', 'app.seed') } finally { Pop-Location }
