$ErrorActionPreference = 'Stop'

# FINMARKET project is Downloads\Finmarket_Kart_Essentials_Storefront\Finmarket Kart Essentials
# SAMLAPA is a sibling folder directly under Downloads.
$Downloads = Join-Path $env:USERPROFILE 'Downloads'
$Samlapa = Join-Path $Downloads 'samlapa-20261109T063346Z-1-001\samlapa'
$FastAPIPath = Join-Path $Samlapa 'io\finmkt\fastapi'
$FastAPIPyProject = Join-Path $FastAPIPath 'pyproject.toml'

Write-Host "SAMLAPA root : $Samlapa"
Write-Host "FastAPI path : $FastAPIPath"

if (-not (Test-Path $FastAPIPyProject -PathType Leaf)) {
    throw "SAMLAPA FastAPI pyproject.toml not found: $FastAPIPyProject. Verify where the SAMLAPA folder was extracted."
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host 'Refreshing uv.lock against the local SAMLAPA package...'
uv lock

Write-Host 'Synchronizing the FINMARKET environment...'
uv sync

Write-Host 'SAMLAPA FinMkt FastAPI dependency setup completed.'
