param([string]$OutputDir = '')

$ErrorActionPreference = 'Stop'
if (-not $OutputDir) {
    $OutputDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'data\operational\presentation_build_20261014'
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

function Color([int]$r,[int]$g,[int]$b) { $r + 256*$g + 65536*$b }
$navy=Color 23 43 65
$teal=Color 0 126 135
$orange=Color 220 119 47
$ink=Color 37 53 67
$muted=Color 93 111 126
$border=Color 211 223 227
$white=Color 255 255 255

function Rect($s,[double]$x,[double]$y,[double]$w,[double]$h,[int]$fill) {
    $o=$s.Shapes.AddShape(1,$x,$y,$w,$h)
    $o.Fill.Solid(); $o.Fill.ForeColor.RGB=$fill; $o.Line.Visible=0
    $o
}
function Label($s,[string]$value,[double]$x,[double]$y,[double]$w,[double]$h,[int]$size,[int]$color,[bool]$bold=$false) {
    $o=$s.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $t=$o.TextFrame
    $t.MarginLeft=0; $t.MarginRight=0; $t.MarginTop=0; $t.MarginBottom=0
    $t.WordWrap=-1; $t.TextRange.Text=$value
    $t.TextRange.Font.Name='Arial'; $t.TextRange.Font.Size=$size
    $t.TextRange.Font.Color.RGB=$color
    if($bold){$t.TextRange.Font.Bold=-1}
    $o
}

$app=New-Object -ComObject PowerPoint.Application
$p=$app.Presentations.Add()
$p.PageSetup.SlideWidth=960; $p.PageSetup.SlideHeight=540
try {
    $s=$p.Slides.Add(1,12)
    Rect $s 0 0 960 540 $white | Out-Null
    Rect $s 0 0 960 10 $teal | Out-Null
    Label $s 'KHẢO SÁT ĐỀ TÀI' 44 25 810 19 11 $teal $true | Out-Null
    Label $s 'Dự báo mưa trước bao lâu là hữu ích?' 44 54 870 52 29 $navy $true | Out-Null
    Label $s 'Tham chiếu hiện có' 44 130 420 31 20 $navy $true | Out-Null
    Label $s 'Định hướng PBL tại Đà Nẵng' 500 130 415 31 20 $navy $true | Out-Null
    Rect $s 480 134 1 246 $border | Out-Null

    Label $s 'Đà Nẵng' 44 170 162 28 17 $teal $true | Out-Null
    Label $s 'Smart City hiển thị mưa và điểm ngập đang ghi nhận.' 200 169 265 54 16 $ink | Out-Null
    Label $s 'Hồng Kông' 44 229 162 28 17 $teal $true | Out-Null
    Label $s 'MyObservatory dự báo mưa theo vị trí trong 1–2 giờ.' 200 228 265 54 16 $ink | Out-Null
    Label $s 'Đài Loan' 44 288 162 28 17 $teal $true | Out-Null
    Label $s 'CWA công bố lượng mưa theo khoảng 3 giờ khi mưa lớn.' 200 287 265 54 16 $ink | Out-Null
    Label $s 'WMO' 44 347 162 28 17 $teal $true | Out-Null
    Label $s 'Nowcasting thuộc khoảng 0–6 giờ tới.' 200 346 265 33 16 $ink | Out-Null

    Label $s '1–6 giờ' 500 172 370 43 29 $teal $true | Out-Null
    Label $s 'Dự báo theo ô lưới, cập nhật mỗi giờ.' 500 220 405 54 17 $ink | Out-Null
    Label $s '3 giờ đầu' 500 280 390 43 26 $navy $true | Out-Null
    Label $s 'Ưu tiên kiểm chứng tổng mưa 3 giờ và xác suất mưa mạnh.' 500 326 406 57 17 $ink | Out-Null

    Rect $s 44 399 872 1 $border | Out-Null
    Label $s 'Mốc 3 giờ là lựa chọn thử nghiệm. Nhóm chưa khảo sát để biết người dùng cần nhất mốc 1, 3 hay 6 giờ.' 44 410 872 43 16 $orange $true | Out-Null
    Rect $s 44 463 872 1 $border | Out-Null
    Label $s 'ĐỀ TÀI GỒM' 44 475 140 20 11 $teal $true | Out-Null
    Label $s 'Dữ liệu GSMaP + ECMWF' 168 474 224 22 15 $ink | Out-Null
    Label $s 'So mô hình, đặc trưng vùng; đánh giá cùng mẫu' 402 474 283 39 14 $ink | Out-Null
    Label $s 'App mưa 3h, xác suất và độ mới dữ liệu' 696 474 220 38 14 $ink | Out-Null
    Label $s 'Nguồn: Danang Smart City, HKO, CWA, WMO (liên kết trong ghi chú).' 44 519 872 16 10 $muted | Out-Null

    $s.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text=@'
Lời trình bày (khoảng 50 giây): Đà Nẵng đã có ứng dụng hiển thị mưa và ngập được ghi nhận. Ở nước ngoài, MyObservatory của cơ quan khí tượng Hồng Kông dự báo mưa theo vị trí 1–2 giờ, còn cơ quan khí tượng Đài Loan phát hành lượng mưa dự báo theo khoảng 3 giờ trong những đợt mưa lớn. WMO gọi khoảng 0–6 giờ là nowcasting. Vì thế nhóm nghiên cứu hạn 1–6 giờ, trước mắt kiểm chứng lượng mưa tích lũy 3 giờ và xác suất mưa mạnh trên Đà Nẵng. Đây là quyết định thiết kế, chưa có phỏng vấn hay khảo sát định lượng chứng minh 3 giờ là nhu cầu cao nhất. Đồ án bao gồm dữ liệu, mô hình, đánh giá cùng mẫu và app; hiện chỉ có demo hồi cứu, chưa có AI live.

Nguồn:
WMO OSCAR, Nowcasting / Very Short-Range Forecasting: https://space.oscar.wmo.int/applicationareas/view/2_3_nowcasting_very_short_range_forecasting
Danang Smart City, chức năng hỗ trợ thiên tai: https://tralien.danang.gov.vn/chuyen-doi-so/cac-tinh-nang-ho-tro-ung-pho-thien-tai-tren-ung-dung-danang-smart-city-324820
Hong Kong Observatory, MyObservatory: https://www.hko.gov.hk/en/myobservatory.htm
Taiwan Central Weather Administration, annual review (tr. 24, QPF 3 giờ cho 12 giờ kế tiếp khi mưa lớn): https://www.cwa.gov.tw/Data/service/notice/download/Publish_20250326113535.pdf
Dự án: CLAUDE.md; KE_HOACH_DU_AN.md; reports/research_rainfall/user_needs_desk_review_2026_10_14.md.

Lưu ý: Ví dụ CWA là lượng mưa theo khoảng 3 giờ, không phải bằng chứng họ chỉ dự báo đến giờ thứ 3. Không có khảo sát trực tiếp người dùng Đà Nẵng, không tuyên bố mốc 3h được ưa thích nhất. Lưới ~10–11 km không suy ra ngập từng tuyến đường.
'@
    $draft=Join-Path $OutputDir 'Khao_sat_de_tai_1_slide_2026_10_14_draft.pptx'
    $preview=Join-Path $OutputDir 'Khao_sat_de_tai_1_slide_2026_10_14_preview.png'
    $p.SaveAs($draft,24)
    $s.Export($preview,'PNG',1280,720)
    Write-Output "DRAFT $draft"
    Write-Output "PREVIEW $preview"
} finally {
    $p.Close(); $app.Quit()
}
