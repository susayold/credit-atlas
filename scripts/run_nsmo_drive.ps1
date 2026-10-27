param([int]$Port = 8770, [string]$Remote = 'creditatlas:')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:RCLONE_CONFIG = 'D:\data\CodexState\config\creditatlas-rclone.conf'
$sourcePaths = @(
    (Join-Path $projectRoot 'src'),
    (Join-Path $projectRoot 'vendor\credit_risk_strategy_lab\src'),
    (Join-Path $projectRoot 'vendor\credit_risk_strategy_lab')
)
$env:PYTHONPATH = ($sourcePaths -join ';')
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw 'Python 3.12+ was not found. Install project dependencies before starting the Drive-backed D02 runtime.' }
    $pythonPath = $pythonCommand.Source
}
if (-not (Test-Path -LiteralPath $env:RCLONE_CONFIG)) {
    throw 'The read-only rclone configuration is missing. Follow docs/DRIVE_RUNTIME.md; credentials stay under D:\data\CodexState.'
}
Set-Location -LiteralPath $projectRoot
& $pythonPath -X utf8 -m credit_atlas.cli --root $projectRoot serve --port $Port --nsmo-drive-remote $Remote
exit $LASTEXITCODE
