param(
    [int]$Port = 8765
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "windows_bridge_server.py"
if (-not (Test-Path $scriptPath)) {
    throw "windows_bridge_server.py not found: $scriptPath"
}

if ([string]::IsNullOrWhiteSpace($env:WINDOWS_BRIDGE_PORT)) {
    $env:WINDOWS_BRIDGE_PORT = [string]$Port
}

python $scriptPath
