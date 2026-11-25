# Shared helpers. Dot-sourced by the other scripts.
$ErrorActionPreference = 'Stop'

$script:RootDir     = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$script:BackendDir  = Join-Path $RootDir 'backend'
$script:FrontendDir = Join-Path $RootDir 'frontend'
$script:VenvDir     = Join-Path $BackendDir '.venv'
if ($IsLinux -or $IsMacOS) { $script:Py = Join-Path $VenvDir 'bin/python' }
else { $script:Py = Join-Path $VenvDir 'Scripts\python.exe' }

function Write-Info([string]$Message) { Write-Host "[nexzen] $Message" -ForegroundColor Cyan }
function Stop-Nexzen([string]$Message) { Write-Host "[nexzen] ERROR: $Message" -ForegroundColor Red; exit 1 }

function Assert-Command([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { Stop-Nexzen "'$Name' not found. $Hint" }
}
function Assert-Venv { if (-not (Test-Path $Py)) { Stop-Nexzen 'Virtualenv missing. Run: make setup' } }
function Test-Frontend { Test-Path (Join-Path $FrontendDir 'package.json') }

# Run a native command and fail the script on non-zero exit code.
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { Stop-Nexzen "Command failed: $Exe $($Arguments -join ' ')" }
}
