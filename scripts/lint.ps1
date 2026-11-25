param([switch]$Fix)
# Lint + type check + security scan. Use -Fix to auto-fix formatting.
. (Join-Path $PSScriptRoot '_common.ps1')
Assert-Venv
Push-Location $BackendDir
try {
    if ($Fix) {
        Invoke-Checked $Py @('-m', 'ruff', 'check', '--fix', '.')
        Invoke-Checked $Py @('-m', 'ruff', 'format', '.')
    } else {
        Invoke-Checked $Py @('-m', 'ruff', 'check', '.')
        Invoke-Checked $Py @('-m', 'ruff', 'format', '--check', '.')
    }
    if (Test-Path 'app') {
        Invoke-Checked $Py @('-m', 'mypy')
        Invoke-Checked $Py @('-m', 'bandit', '-q', '-r', 'app')
    }
} finally { Pop-Location }
if (Test-Frontend) {
    Push-Location $FrontendDir
    try {
        npm run lint --if-present; if ($LASTEXITCODE -ne 0) { Stop-Nexzen 'Frontend lint failed' }
        npm run typecheck --if-present; if ($LASTEXITCODE -ne 0) { Stop-Nexzen 'Frontend typecheck failed' }
    } finally { Pop-Location }
}
Write-Info 'Lint OK.'
