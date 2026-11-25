param([ValidateSet('unit', 'integration', 'all')][string]$Scope = 'all')
# Backend tests (pytest) and frontend tests (Vitest) if present.
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
Push-Location $BackendDir
try {
    switch ($Scope) {
        'unit'        { Invoke-Checked $Py @('-m', 'pytest', '-m', 'unit') }
        'integration' { Invoke-Checked $Py @('-m', 'pytest', '-m', 'integration') }
        'all'         { Invoke-Checked $Py @('-m', 'pytest', '--cov', '--cov-report=term-missing') }
    }
} finally { Pop-Location }
if ((Test-Frontend) -and $Scope -ne 'integration') {
    Push-Location $FrontendDir
    try { npm run test --if-present -- --run; if ($LASTEXITCODE -ne 0) { Stop-Nexzen 'Frontend tests failed' } } finally { Pop-Location }
}
