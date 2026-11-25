# Bootstrap PostgreSQL roles and least-privilege grants (idempotent).
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
Push-Location $BackendDir
try { Invoke-Checked $Py @('-m', 'app.core.db_bootstrap') } finally { Pop-Location }
