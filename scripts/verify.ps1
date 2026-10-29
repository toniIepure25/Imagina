# Thin wrapper around scripts/verify.py for PowerShell users.
$ErrorActionPreference = "Stop"
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) { throw "python not found" }
& $python.Source "$PSScriptRoot/verify.py" @args
exit $LASTEXITCODE
