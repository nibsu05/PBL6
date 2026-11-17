# Share DELETE as well as READ/WRITE: monitoring must not block atomic log replacement.
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$taskBase = Join-Path $repoRoot 'data/operational/gfs_temporal_2026_11_17'
$result = [ordered]@{}
foreach ($name in @('collection_progress','pipeline_progress','training_progress','scoring_progress')) {
    $path = Join-Path $taskBase ($name + '.json')
    if (-not (Test-Path -LiteralPath $path)) { continue }
    $stream = $null; $reader = $null
    try {
        $sharing = [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
        $stream = [System.IO.FileStream]::new($path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, $sharing)
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8)
        $value = $reader.ReadToEnd() | ConvertFrom-Json
    } finally {
        if ($null -ne $reader) { $reader.Dispose() }
        if ($null -ne $stream) { $stream.Dispose() }
    }
    $alive = $false
    try { $process = [System.Diagnostics.Process]::GetProcessById($value.pid); $alive = -not $process.HasExited; $process.Dispose() } catch {}
    $result[$name] = [ordered]@{process_alive=$alive; record=$value}
}
$result | ConvertTo-Json -Depth 8 -Compress
