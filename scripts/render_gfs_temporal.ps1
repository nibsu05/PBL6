param([string]$DeckPath = '', [string]$OutputDir = '', [switch]$Preview)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
if (-not $DeckPath) { $DeckPath = Join-Path $repoRoot 'reports/gfs_temporal_2026_11_17/PBL6_CAI_TIEN_DU_BAO_NGAN_HAN.pptx' }
if (-not $OutputDir) { $OutputDir = Join-Path $repoRoot 'data/operational/gfs_temporal_2026_11_17/native_render' }
$DeckPath = (Resolve-Path -LiteralPath $DeckPath).Path
$null = New-Item -ItemType Directory -Force -Path $OutputDir
$hadPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app = $null; $deck = $null; $measurements = 0
$issues = [System.Collections.Generic.List[object]]::new()
function Test-Bounds($frame, $height, $width, $slide, $shape, $cell) {
    if ($frame.HasText -ne -1) { return }
    $script:measurements++
    $availableH = $height - $frame.MarginTop - $frame.MarginBottom
    $availableW = $width - $frame.MarginLeft - $frame.MarginRight
    if (($frame.TextRange.BoundHeight -gt $availableH + 1.5) -or ($frame.TextRange.BoundWidth -gt $availableW + 1.5)) {
        $value = $frame.TextRange.Text
        $script:issues.Add([ordered]@{slide=$slide; shape=$shape; cell=$cell; text=$value.Substring(0,[Math]::Min(160,$value.Length));
            available_h=$availableH; needed_h=$frame.TextRange.BoundHeight; available_w=$availableW; needed_w=$frame.TextRange.BoundWidth})
    }
}
try {
    $app = New-Object -ComObject PowerPoint.Application
    $deck = $app.Presentations.Open($DeckPath, -1, 0, 0)
    foreach ($slide in $deck.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTable -eq -1) {
                for ($r=1; $r -le $shape.Table.Rows.Count; $r++) {
                    for ($c=1; $c -le $shape.Table.Columns.Count; $c++) {
                        $cell = $shape.Table.Cell($r,$c).Shape
                        Test-Bounds $cell.TextFrame2 $cell.Height $cell.Width $slide.SlideIndex $shape.Id "$r,$c"
                    }
                }
            } elseif ($shape.HasTextFrame -eq -1) {
                Test-Bounds $shape.TextFrame2 $shape.Height $shape.Width $slide.SlideIndex $shape.Id ''
            }
        }
        $slide.Export((Join-Path $OutputDir ('slide_{0:D2}.png' -f $slide.SlideIndex)), 'PNG', 1600, 900)
    }
    $deck.SaveAs((Join-Path $OutputDir 'report.pdf'), 32)
    $report = [ordered]@{status=$(if ($issues.Count -eq 0) {'passed'} else {'failed'}); renderer='Microsoft PowerPoint native COM';
        slides=$deck.Slides.Count; text_boxes_checked=$measurements; overflows=@($issues.ToArray()); preview=$Preview.IsPresent;
        pptx_sha256=(Get-FileHash -LiteralPath $DeckPath -Algorithm SHA256).Hash.ToLowerInvariant()}
    $json = $report | ConvertTo-Json -Depth 8
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $OutputDir 'audit.json'), ($json.Replace("`r`n","`n") + "`n"), $encoding)
    if (-not $Preview) {
        [System.IO.File]::WriteAllText((Join-Path $repoRoot 'reports/gfs_temporal_2026_11_17/slide_render_verification.json'), ($json.Replace("`r`n","`n") + "`n"), $encoding)
    }
    [ordered]@{status=$report.status; slides=$deck.Slides.Count; overflows=$issues.Count; measured=$measurements} | ConvertTo-Json -Compress
} finally {
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck) }
    if ($null -ne $app) {
        if ((-not $hadPowerPoint) -and $app.Presentations.Count -eq 0) { $app.Quit() }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)
    }
    [GC]::Collect(); [GC]::WaitForPendingFinalizers()
}
if ($issues.Count -gt 0) { exit 2 }
