param([int]$Port = 8770)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
Set-Location -LiteralPath $projectRoot
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -X utf8 -m credit_atlas.cli serve --port $Port
exit $LASTEXITCODE
