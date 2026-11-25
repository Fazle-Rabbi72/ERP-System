# Run the ARQ background worker.
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
Push-Location $BackendDir
try { Invoke-Checked $Py @('-m', 'arq', 'app.workers.settings.WorkerSettings') } finally { Pop-Location }
