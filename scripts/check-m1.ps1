param(
    [ValidateSet('synthetic', 'ulog')]
    [string]$Profile = 'synthetic',
    [string]$CacheDirectory = '.uv-cache',
    [switch]$Offline
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$checkArgs = @((Join-Path $PSScriptRoot 'check-m1.py'), '--profile', $Profile,
    '--cache-directory', $CacheDirectory)
if ($Offline) { $checkArgs += '--offline' }
& python @checkArgs
if ($LASTEXITCODE -ne 0) { throw "M1 $Profile checks failed (exit $LASTEXITCODE)." }
