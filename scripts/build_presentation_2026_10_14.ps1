param(
    [string]$OutputDir = ''
)

$ErrorActionPreference = 'Stop'
if (-not $OutputDir) {
    $OutputDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'data\operational\presentation_build_20261014'
}
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

function Color([int]$r, [int]$g, [int]$b) { return ($r + 256 * $g + 65536 * $b) }
$navy = Color 23 43 65
$teal = Color 0 126 135
$orange = Color 220 119 47
$ink = Color 37 53 67
$muted = Color 93 111 126
$pale = Color 238 246 247
$light = Color 245 247 249
$white = Color 255 255 255
$border = Color 211 223 227

function Box($slide, [double]$x, [double]$y, [double]$w, [double]$h, [int]$fill, [int]$stroke = -1) {
    $shape = $slide.Shapes.AddShape(1, $x, $y, $w, $h)
    $shape.Fill.Solid()
    $shape.Fill.ForeColor.RGB = $fill
    if ($stroke -lt 0) { $shape.Line.Visible = 0 } else { $shape.Line.Visible = -1; $shape.Line.ForeColor.RGB = $stroke }
    return $shape
}
function Txt($slide, [string]$s, [double]$x, [double]$y, [double]$w, [double]$h, [int]$size = 20, [int]$color = 0, [bool]$bold = $false, [int]$align = 1) {
    $shape = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $tf = $shape.TextFrame
    $tf.MarginLeft = 0; $tf.MarginRight = 0; $tf.MarginTop = 0; $tf.MarginBottom = 0
    $tf.WordWrap = -1
    $tf.TextRange.Text = $s
    $tf.TextRange.Font.Name = 'Arial'
    $tf.TextRange.Font.Size = $size
    $tf.TextRange.Font.Color.RGB = $color
    if ($bold) { $tf.TextRange.Font.Bold = -1 }
    $tf.TextRange.ParagraphFormat.Alignment = $align
    return $shape
}
function BaseSlide($p, [string]$title, [string]$kicker, [int]$n) {
    $s = $p.Slides.Add($p.Slides.Count + 1, 12)
    $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB = $white
    Box $s 0 0 960 10 $teal | Out-Null
    Txt $s $kicker 44 24 760 20 11 $teal $true | Out-Null
    Txt $s $title 44 52 870 64 29 $navy $true | Out-Null
    Box $s 44 496 872 1 $border | Out-Null
    Txt $s 'PBL6  |  Đà Nẵng  |  14.10.2026' 44 508 650 17 10 $muted | Out-Null
    Txt $s ([string]$n) 870 508 46 17 10 $muted $false 3 | Out-Null
    return $s
}
function Notes($slide, [string]$content) {
    $slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = $content
}
function TableCell($slide, [string]$value, [double]$x, [double]$y, [double]$w, [double]$h, [int]$fill, [int]$fontColor, [int]$fontSize = 16, [bool]$bold = $false, [int]$align = 1) {
    Box $slide $x $y $w $h $fill $border | Out-Null
    Txt $slide $value ($x+9) ($y+8) ($w-18) ($h-14) $fontSize $fontColor $bold $align | Out-Null
}

$app = New-Object -ComObject PowerPoint.Application
$p = $app.Presentations.Add()
$p.PageSetup.SlideWidth = 960
$p.PageSetup.SlideHeight = 540
try {
    # 1 — cover
    $s = $p.Slides.Add(1,12)
    $s.Background.Fill.Solid(); $s.Background.Fill.ForeColor.RGB = $navy
    Box $s 0 0 960 540 $navy | Out-Null
    Box $s 0 0 16 540 $teal | Out-Null
    Txt $s 'PBL6  /  BÁO CÁO TIẾN ĐỘ' 60 66 700 25 15 (Color 116 216 218) $true | Out-Null
    Txt $s "Dự báo mưa vài giờ tới`ncho Đà Nẵng" 60 130 825 160 40 $white $true | Out-Null
    Txt $s 'Dữ liệu địa phương · so sánh mô hình · khả năng triển khai ứng dụng' 60 338 810 58 20 $white | Out-Null
    Box $s 60 444 84 5 $orange | Out-Null
    Txt $s 'Trao đổi với giảng viên  ·  08:00, 14/10/2026' 60 466 760 24 14 (Color 194 209 219) | Out-Null
    Notes $s 'Đây là tiến độ nghiên cứu và demo hồi cứu, chưa phải dự báo AI trực tiếp hay sản phẩm cảnh báo ngập.'

    # 2 — user needs
    $s = BaseSlide $p 'Nhu cầu: biết mưa sắp tới, không chỉ mưa đang xảy ra' 'BÀI TOÁN & NGƯỜI DÙNG' 2
    Box $s 44 132 275 290 $pale | Out-Null
    Txt $s 'Hiện có ở Đà Nẵng' 62 152 240 28 20 $navy $true | Out-Null
    Txt $s 'Danang Smart City đã có theo dõi mưa, mực nước và điểm ngập thời gian thực.' 62 198 232 111 17 $ink | Out-Null
    Txt $s 'Vì vậy, đề tài không nhận là bản đồ mưa/ngập đầu tiên.' 62 325 232 68 15 $muted | Out-Null
    Box $s 342 132 574 290 $light | Out-Null
    Txt $s 'Lớp thông tin nhóm muốn kiểm chứng' 362 150 528 31 21 $navy $true | Out-Null
    Txt $s '0–6 giờ tới' 362 197 244 46 30 $teal $true | Out-Null
    Txt $s 'Lượng mưa và xác suất vượt ngưỡng theo ô lưới; luôn hiện giờ phát hành, nguồn và độ cũ dữ liệu.' 362 254 514 86 19 $ink | Out-Null
    Txt $s 'Người dùng giả định: người đi lại; cán bộ theo dõi khu vực; người vận hành app.' 362 357 510 50 15 $muted | Out-Null
    Txt $s 'Rà soát tài liệu, chưa phỏng vấn người dùng. Ô ~10–11 km không dự báo ngập cấp đường.' 44 442 872 43 14 $orange $true | Out-Null
    Notes $s 'Nguồn: https://tralien.danang.gov.vn/chuyen-doi-so/cac-tinh-nang-ho-tro-ung-pho-thien-tai-tren-ung-dung-danang-smart-city-324820 ; https://hdnd.danang.gov.vn/chi-tiet-tin/group/157/nid/23678/som-cong-khai-ban-do-ngap-lut-cua-thanh-pho-da-nang ; https://public.wmo.int/resources/wmo-bulletin/wmo-bulletin-vol-71-1-2022/communicating-life-saving-action-enhancing-messaging-early-warnings-systems ; reports/research_rainfall/user_needs_desk_review_2026_10_14.md. Nhu cầu sản phẩm là giả thuyết từ tài liệu, không phải kết quả khảo sát.'

    # 3 — label and experiment
    $s = BaseSlide $p 'Chọn nhãn đúng rồi mới so mô hình' 'DỮ LIỆU & THIẾT KẾ THỬ NGHIỆM' 3
    Txt $s 'CSI bắt ngày mưa ≥50 mm tại 10 trạm GSOD' 44 132 755 30 18 $ink $true | Out-Null
    $heads=@('GSMaP GC v8','IMERG','ERA5')
    $values=@('0,33','0,22','0,17')
    for($i=0;$i -lt 3;$i++) {
        $x=44+$i*292
        Box $s $x 174 272 103 $(if($i -eq 0){$pale}else{$light}) | Out-Null
        Txt $s $heads[$i] ($x+15) 187 240 28 17 $ink $true | Out-Null
        Txt $s $values[$i] ($x+15) 219 240 49 32 $(if($i -eq 0){$teal}else{$navy}) $true | Out-Null
    }
    Txt $s 'ERA5 mưa bỏ sót nhiều ngày cực đoan ở audit cũ; dùng GSMaP GC làm nhãn nghiên cứu.' 44 295 870 56 19 $ink | Out-Null
    Box $s 44 370 872 1 $border | Out-Null
    Txt $s '93 ô Đà Nẵng  →  30 ô cố định để so sánh  →  3 năm validation (2021–23) × 3 seed' 44 388 872 54 18 $navy $true | Out-Null
    Txt $s 'Test 2025 giữ kín. GSMaP GC có hiệu chỉnh trạm: benchmark GSOD chưa hoàn toàn độc lập.' 44 450 872 36 14 $orange | Out-Null
    Notes $s 'Nguồn nội bộ: reports/station_benchmark/README.md ; reports/domain_screen_danang/README.md ; reports/research_rainfall/slide_content_2026_10_14.md. CSI là Critical Success Index. Đối chiếu GC với GSOD có rủi ro trùng nguồn hiệu chỉnh gauge.'

    # 4 — strongest model finding
    $s = BaseSlide $p 'Kết quả rõ nhất: đổi hàm học lượng mưa' 'THỰC NGHIỆM MÔ HÌNH' 4
    Txt $s 'RMSE tổng mưa 0–3 giờ, tháng 5–10 (mm; thấp hơn là tốt hơn)' 44 120 872 28 17 $ink | Out-Null
    TableCell $s 'Năm' 44 166 112 42 $navy $white 15 $true
    TableCell $s 'LightGBM RAW: L1(log) → Tweedie' 156 166 380 42 $navy $white 15 $true
    TableCell $s 'Bi-LSTM RAW: log-Huber → Tweedie' 536 166 380 42 $navy $white 15 $true
    $years=@('2021','2022','2023')
    $lgb=@('4,607  →  3,947','4,841  →  4,534','4,205  →  3,610')
    $lstm=@('4,046  →  3,876','4,661  →  4,581','3,963  →  3,540')
    for($i=0;$i -lt 3;$i++) {
        $y=208+$i*55; $f=if($i%2 -eq 0){$white}else{$light}
        TableCell $s $years[$i] 44 $y 112 55 $f $navy 18 $true
        TableCell $s $lgb[$i] 156 $y 380 55 $f $teal 21 $true
        TableCell $s $lstm[$i] 536 $y 380 55 $f $teal 21 $true
    }
    Txt $s 'LightGBM: CI95% mức giảm RMSE loại 0 cả 3 năm. Bi-LSTM: 2022 chưa chắc; BSS xác suất ≥1 giảm 0,186→0,148.' 44 394 872 72 16 $ink | Out-Null
    Notes $s 'Nguồn: reports/followup_danang/amount/paired_bootstrap.json ; reports/followup_danang/bilstm_tweedie/paired_bootstrap.json ; reports/research_rainfall/slide_content_2026_10_14.md. So cùng sample/fold trong từng họ mô hình. Không suy ra xác suất cải thiện đồng đều.'

    # 5 — domain
    $s = BaseSlide $p 'Hiểu khí tượng địa phương: tín hiệu có, thắng lợi chưa chắc' 'ĐÓNG GÓP THEO VÙNG' 5
    Box $s 44 136 337 280 $pale | Out-Null
    Txt $s 'Gió Đông Bắc' 63 156 288 29 21 $navy $true | Out-Null
    Txt $s '12–18%' 63 210 273 49 32 $teal $true | Out-Null
    Txt $s 'số mẫu trong audit' 63 259 270 24 16 $ink | Out-Null
    Txt $s '46–65%' 63 310 273 49 32 $orange $true | Out-Null
    Txt $s 'sự kiện mưa ≥10 mm/3 giờ' 63 359 276 45 16 $ink | Out-Null
    Txt $s 'Bi-LSTM DOMAIN − RAW: ΔCSI xác suất mưa ≥10 mm/3 giờ' 407 150 500 54 18 $navy $true | Out-Null
    $deltas=@('2021  +0,051','2022  +0,007','2023  +0,031')
    for($i=0;$i -lt 3;$i++) {
        Box $s 408 (222+$i*53) 496 43 $light | Out-Null
        Txt $s $deltas[$i] 426 (229+$i*53) 450 28 20 $teal $true | Out-Null
    }
    Txt $s 'CI95% từng năm đều chứa 0; LightGBM chưa xác nhận lợi ích lặp.' 407 400 507 57 16 $orange $true | Out-Null
    Notes $s 'Nguồn: reports/domain_screen_danang/README.md ; reports/domain_screen_danang/domain_effect_ci.png ; reports/domain_screen_danang/regime_event_rates.png. Tỷ lệ gió chỉ mô tả dữ liệu; không là quan hệ nhân quả. DOMAIN CSI tăng mô tả nhưng CI bootstrap từng năm chứa 0.'

    # 6 — operation
    $s = BaseSlide $p 'App đã có demo hồi cứu; phát hành AI live còn cổng dữ liệu' 'TỪ MÔ HÌNH ĐẾN SẢN PHẨM' 6
    Box $s 44 138 412 287 $pale | Out-Null
    Txt $s 'Đã kiểm tra' 62 156 360 30 21 $navy $true | Out-Null
    Txt $s '24/24' 62 208 357 49 34 $teal $true | Out-Null
    Txt $s 'tệp GSMaP NRT v8 tải, giải mã' 62 258 356 44 17 $ink | Out-Null
    Txt $s '93/93 ô hữu hạn; demo archive dùng checkpoint thật; 36 phép đối chiếu API khớp.' 62 322 358 78 16 $ink | Out-Null
    Box $s 480 138 436 287 $light | Out-Null
    Txt $s 'Cần kiểm định trước AI live' 499 156 396 31 21 $navy $true | Out-Null
    Txt $s 'Một tệp mới được phát hiện khi đã cũ 3,53–3,70 giờ; mới 1 quan sát.' 499 207 393 69 17 $ink | Out-Null
    Txt $s 'Train lại lag 5h: RMSE tăng 0,038–0,053 mm/3h (~1%) so lag 4h trên 3 fold.' 499 292 393 90 17 $ink | Out-Null
    Txt $s 'Cần đo nhiều ngày và xác minh mọi biến đầu vào có sẵn đúng giờ phát hành.' 44 442 872 43 16 $orange $true | Out-Null
    Notes $s 'Nguồn: reports/followup_danang/jaxa_live_first_detection.json ; reports/followup_danang/bilstm_tweedie_lag5/README.md ; reports/research_rainfall/slide_content_2026_10_14.md. Một file watcher không đại diện latency điển hình. Demo archive không đồng nghĩa AI live. Lag5 retrain trên cùng 30 cell/3 fold/3 seed; không phải đánh giá app trực tiếp.'

    # 7 — roadmap
    $s = BaseSlide $p 'Ba bước để chọn mô hình thực sự dùng được' 'KẾ HOẠCH & CÂU HỎI CHO GIẢNG VIÊN' 7
    $steps=@(
        @('01','Đo nguồn','Ghi giờ file mới nhiều ngày; kiểm tra train–NRT và dữ liệu có trước giờ phát hành.'),
        @('02','So công bằng','AI và ECMWF trên cùng ô, giờ, hạn, nhãn; đánh giá mưa mạnh, xác suất, độ trễ.'),
        @('03','Chốt app','Chọn mô hình/fallback theo kết quả; thử với người dùng; rồi mới mở rộng 1–3 ngày.')
    )
    for($i=0;$i -lt 3;$i++) {
        $y=138+$i*94
        Box $s 44 $y 872 80 $(if($i%2 -eq 0){$pale}else{$light}) | Out-Null
        Txt $s $steps[$i][0] 58 ($y+17) 62 48 29 $teal $true | Out-Null
        Txt $s $steps[$i][1] 132 ($y+9) 185 29 19 $navy $true | Out-Null
        Txt $s $steps[$i][2] 320 ($y+10) 572 58 16 $ink | Out-Null
    }
    Txt $s 'Xin góp ý: tập trung 0–6h một vùng? Ưu tiên RMSE hay bắt mưa mạnh? Có trạm giờ độc lập?' 44 440 872 46 16 $orange $true | Out-Null
    Notes $s 'Kế hoạch: reports/research_rainfall/execution_plan.md ; reports/research_rainfall/slide_content_2026_10_14.md. User interviews và T-OPS chưa hoàn tất; đây là bước tiếp theo, không phải kết quả đã có.'

    # 8 — backup ECMWF
    $s = BaseSlide $p 'ECMWF là đối chứng dự báo, không phải nhãn ERA5' 'DỰ PHÒNG NẾU ĐƯỢC HỎI' 8
    Txt $s 'Pilot: 56 run trong 14 ngày (10/2024) × 30 ô = 1.680 cặp dự báo/nhãn.' 44 139 872 60 20 $navy $true | Out-Null
    Box $s 44 222 410 153 $pale | Out-Null
    Txt $s 'ECMWF / Open-Meteo' 62 241 372 29 19 $navy $true | Out-Null
    Txt $s 'RMSE 3,950 mm/3h' 62 290 360 36 24 $teal $true | Out-Null
    Txt $s 'CSI ≥10: 0,089' 62 335 360 25 18 $ink | Out-Null
    Box $s 474 222 442 153 $light | Out-Null
    Txt $s 'Đối chứng luôn 0' 493 241 390 29 19 $navy $true | Out-Null
    Txt $s 'RMSE 3,878 mm/3h' 493 290 398 36 24 $orange $true | Out-Null
    Txt $s 'Chỉ 4/14 ngày có mưa mạnh.' 493 335 390 25 18 $ink | Out-Null
    Txt $s 'CI hiệu RMSE chứa 0; chưa có phép so AI–ECMWF cùng mẫu vận hành. Pilot chỉ thăm dò.' 44 406 872 71 17 $ink | Out-Null
    Notes $s 'Nguồn: reports/research_rainfall/ecmwf_pilot_14d/README.md. ECMWF IFS là forecast trước giờ đích, khác ERA5 reanalysis. Open-Meteo là bước trung gian nội suy/giải tổng, không native GRIB. Historical available_at chưa được xác minh đầy đủ. Không tuyên bố AI vượt ECMWF.'

    $draft = Join-Path $OutputDir 'PBL6_Da_Nang_2026_10_14_draft.pptx'
    $p.SaveAs($draft,24)
    for($i=1;$i -le $p.Slides.Count;$i++) {
        $png = Join-Path $OutputDir ('slide_{0:D2}.png' -f $i)
        $p.Slides.Item($i).Export($png,'PNG',1280,720)
    }
    Write-Output "DRAFT $draft slides=$($p.Slides.Count)"
} finally {
    $p.Close()
    $app.Quit()
}
