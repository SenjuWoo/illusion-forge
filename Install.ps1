# Build and test Illusion Forge from this directory.
# This script does not copy the plugin into a game unless -Approve is passed
# together with -Game kk or -Game hs2.
# Debug log: $env:ILLUSIONFORGE_DEBUG = "1"

[CmdletBinding()]
param(
    [ValidateSet("kk", "hs2")]
    [string]$Game,
    [switch]$Approve
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root
$env:PYTHONPATH = Join-Path $Root "src"
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

& $Python -m unittest discover -s (Join-Path $Root "tests") -v
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Python -m illusionforge build-bridge
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Approve) {
    if (-not $Game) { throw "-Approve requires -Game kk or -Game hs2" }
    & $Python -m illusionforge install-bridge --game $Game --approve
    exit $LASTEXITCODE
}

Write-Output "Tests and bridge build finished. The plugin was not copied into a game."
