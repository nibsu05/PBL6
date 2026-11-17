$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$path = Join-Path $repoRoot 'data/operational/gfs_training_window_2026_11_18/progress.json'
$sharing = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
$stream = [System.IO.File]::Open($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, $sharing)
try {
    $reader = New-Object System.IO.StreamReader($stream)
    try { $state = $reader.ReadToEnd() | ConvertFrom-Json } finally { $reader.Dispose() }
} finally { $stream.Dispose() }
$state | Format-List
if ($state.pid) {
    $process = Get-Process -Id $state.pid -ErrorAction SilentlyContinue
    [ordered]@{process_alive=($null -ne $process); updated_utc=$state.updated_utc} | ConvertTo-Json -Compress
}
