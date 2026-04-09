# Load-LevelsEnv.ps1
# Dot-source this script to set Levels Engine env vars in the current session.
#
# Usage:
#   . tools\levels_engine\scripts\Load-LevelsEnv.ps1
#   python tools\levels_engine\doctor.py
#   python tools\levels_engine\run_levels.py SPY

$envFile = Join-Path $PSScriptRoot '..\.env'

if (-not (Test-Path $envFile)) {
    Write-Host "[FAIL] .env file not found at: $envFile" -ForegroundColor Red
    Write-Host "  Copy .env.example first:"
    Write-Host "    copy tools\levels_engine\.env.example tools\levels_engine\.env"
    return
}

Write-Host ""
Write-Host "Loading env from: $envFile" -ForegroundColor Cyan
Write-Host ""

$count = 0
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    # Skip comments and blank lines
    if ($line -match '^\s*#' -or $line -match '^\s*$') { return }
    # Split on first = only
    $parts = $line -split '=', 2
    if ($parts.Count -lt 2) { return }

    $key = $parts[0].Trim()
    $val = $parts[1].Trim()

    # Strip wrapping quotes if present
    if (($val.StartsWith('"') -and $val.EndsWith('"')) -or
        ($val.StartsWith("'") -and $val.EndsWith("'"))) {
        $val = $val.Substring(1, $val.Length - 2)
    }

    # Set in current session
    [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')

    # Print masked
    if ($val.Length -gt 10) {
        $masked = $val.Substring(0,4) + '...' + $val.Substring($val.Length-4) + "  (len=$($val.Length))"
    } elseif ($val.Length -gt 4) {
        $masked = $val.Substring(0,2) + '***' + $val.Substring($val.Length-2)
    } else {
        $masked = $val
    }
    Write-Host "  [OK]  $key = $masked" -ForegroundColor Green
    $count++
}

Write-Host ""
Write-Host "  $count variable(s) loaded into this PowerShell session." -ForegroundColor Cyan
Write-Host ""
