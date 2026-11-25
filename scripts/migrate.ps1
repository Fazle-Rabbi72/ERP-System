param([string]$Revision = 'head')
# Apply database migrations (Alembic arrives in step F3).
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
if (-not (Test-Path (Join-Path $BackendDir 'alembic.ini'))) { Stop-Nexzen 'Alembic not configured yet (added in step F3).' }
Push-Location $BackendDir
try { Invoke-Checked $Py @('-m', 'alembic', 'upgrade', $Revision) } finally { Pop-Location }
