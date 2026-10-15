$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
if ((Split-Path -Qualifier $projectRoot) -ne 'D:') { throw 'Project storage must remain on D:' }
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $projectRoot '.cache\pip'
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
Set-Location -LiteralPath $projectRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 is required to create the project environment' }
}
& $python -m pip install -r requirements-lock.txt
if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed' }
& $python -m pip install --no-deps -e . -e vendor/credit_risk_strategy_lab
if ($LASTEXITCODE -ne 0) { throw 'Editable application/engine installation failed' }
& $python -m credit_atlas.cli inventory
exit $LASTEXITCODE
