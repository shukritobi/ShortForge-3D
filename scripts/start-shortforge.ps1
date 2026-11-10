# Optional convenience wrapper, runs only explicitly requested allowlisted jobs.
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot ".."))
$py = Join-Path (Get-Location) ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    Write-Error "Set up .venv first using py -m venv .venv and pip install -e .[dev]"
    exit 1
}
& $py "scripts/pc_agent.py" @args
exit $LASTEXITCODE
