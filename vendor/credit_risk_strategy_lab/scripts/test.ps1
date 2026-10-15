$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$testParent = Join-Path $projectRoot 'artifacts/private/test-runs'
New-Item -ItemType Directory -Path $testParent -Force | Out-Null
$testBase = [IO.Path]::GetFullPath((Join-Path $testParent ([guid]::NewGuid().ToString('N'))))
if (-not $testBase.StartsWith([IO.Path]::GetFullPath($testParent) + [IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe test path' }
if (Test-Path -LiteralPath $testBase) { throw 'Refusing to reuse a pytest base directory' }
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
Push-Location $projectRoot
try {
    & $pythonPath -m pytest -q --tb=short --basetemp $testBase
    $resultCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $resultCode
