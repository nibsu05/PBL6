param([switch]$AuditOnly)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$publicDir = Join-Path $repoRoot 'reports/gfs_daily_slides_2026_11_11'
$privateDir = Join-Path $repoRoot 'data/operational/gfs_daily_slides_2026_11_11'
$deckPath = Join-Path $publicDir 'PBL6_MUA_TRAM_HANG_NGAY_V2.pptx'
$null = New-Item -ItemType Directory -Force -Path $privateDir
$imageDir = Join-Path $privateDir 'native_png'
$null = New-Item -ItemType Directory -Force -Path $imageDir
$hadPowerPoint = @(Get-Process POWERPNT -ErrorAction SilentlyContinue).Count -gt 0
$app = $null
$deck = $null
$issues = [System.Collections.Generic.List[object]]::new()
$measurements = 0
function Test-TextBounds($frame, $height, $width, $slideNumber, $shapeNumber, $cell) {
    if ($frame.HasText -ne -1) { return }
    $script:measurements++
    $availableH = $height - $frame.MarginTop - $frame.MarginBottom
    $availableW = $width - $frame.MarginLeft - $frame.MarginRight
    $neededH = $frame.TextRange.BoundHeight
    $neededW = $frame.TextRange.BoundWidth
    if (($neededH -gt $availableH + 1.5) -or ($neededW -gt $availableW + 1.5)) {
        $textValue = $frame.TextRange.Text
        $script:issues.Add([ordered]@{
            slide=$slideNumber; shape=$shapeNumber; cell=$cell
            text=$textValue.Substring(0,[Math]::Min(160,$textValue.Length))
            available_h=$availableH; needed_h=$neededH
            available_w=$availableW; needed_w=$neededW
        })
    }
}
try {
    $app = New-Object -ComObject PowerPoint.Application
    # Only our presentation is opened, read-only and without a window.
    $deck = $app.Presentations.Open($deckPath, -1, 0, 0)
    foreach ($slide in $deck.Slides) {
        foreach ($shape in $slide.Shapes) {
            if ($shape.HasTable -eq -1) {
                for ($row=1; $row -le $shape.Table.Rows.Count; $row++) {
                    for ($col=1; $col -le $shape.Table.Columns.Count; $col++) {
                        $cellShape = $shape.Table.Cell($row,$col).Shape
                        Test-TextBounds $cellShape.TextFrame2 $cellShape.Height $cellShape.Width $slide.SlideIndex $shape.Id "$row,$col"
                    }
                }
            } elseif ($shape.HasTextFrame -eq -1) {
                Test-TextBounds $shape.TextFrame2 $shape.Height $shape.Width $slide.SlideIndex $shape.Id ''
            }
        }
        if (-not $AuditOnly) {
            $imagePath = Join-Path $imageDir ('slide_{0:D2}.png' -f $slide.SlideIndex)
            $slide.Export($imagePath, 'PNG', 1600, 900)
        }
    }
    if (-not $AuditOnly) {
        $pdfPath = Join-Path $privateDir 'PBL6_MUA_TRAM_HANG_NGAY_V2.pdf'
        $deck.SaveAs($pdfPath, 32)
    }
    $report = [ordered]@{
        renderer='Microsoft PowerPoint native COM'; version=$app.Version
        slide_count=$deck.Slides.Count; text_boxes_checked=$measurements
        overflow_tolerance_pt=1.5; overflows=@($issues.ToArray())
        pdf_exported=(-not $AuditOnly); read_only_source=$true
        pptx_sha256=(Get-FileHash -LiteralPath $deckPath -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    $report | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 (Join-Path $publicDir 'native_render_audit.json')
    [ordered]@{slides=$deck.Slides.Count; measured=$measurements; overflows=$issues.Count; pdf=(-not $AuditOnly)} | ConvertTo-Json -Compress
} finally {
    if ($null -ne $deck) {
        $deck.Close()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($deck)
    }
    # Do not quit an existing session or close someone else's presentation.
    if ($null -ne $app) {
        if ((-not $hadPowerPoint) -and $app.Presentations.Count -eq 0) { $app.Quit() }
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($app)
    }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
