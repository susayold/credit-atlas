$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = Join-Path $projectRoot '.tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
# Upstream tests exercise non-Git directories. Place fixtures outside this
# checkout so Git does not discover the CreditAtlas parent repository.
$fixtureRoot = Join-Path (Split-Path -Parent $projectRoot) 'credit-atlas-tests'
New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null
$testTemp = Join-Path $fixtureRoot ([guid]::NewGuid().ToString('N'))
Set-Location -LiteralPath $projectRoot
& node --check apps/web/app.js
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& (Join-Path $projectRoot '.venv\Scripts\python.exe') -m pytest -c pyproject.toml tests --basetemp $testTemp -q
exit $LASTEXITCODE
