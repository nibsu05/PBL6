param([string]$OutputDir = '')

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
if (-not $OutputDir) { $OutputDir = Join-Path $repo 'data\operational\presentation_build_20261014' }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$source = Join-Path $repo 'reports\presentation_2026_10_14\PBL6_Da_Nang_2026_10_14.pptx'

function Color([int]$r,[int]$g,[int]$b) { $r + 256*$g + 65536*$b }
$navy=Color 23 43 65
$teal=Color 0 126 135
$orange=Color 220 119 47
$ink=Color 37 53 67
$muted=Color 93 111 126
$pale=Color 238 246 247
$light=Color 245 247 249
$white=Color 255 255 255
$border=Color 211 223 227

function Rect($slide,[double]$x,[double]$y,[double]$w,[double]$h,[int]$fill) {
    $shape=$slide.Shapes.AddShape(1,$x,$y,$w,$h)
    $shape.Fill.Solid(); $shape.Fill.ForeColor.RGB=$fill; $shape.Line.Visible=0
    $shape
}
function Txt($slide,[string]$value,[double]$x,[double]$y,[double]$w,[double]$h,[int]$size,[int]$color,[bool]$bold=$false) {
    $shape=$slide.Shapes.AddTextbox(1,$x,$y,$w,$h)
    $tf=$shape.TextFrame
    $tf.MarginLeft=0; $tf.MarginRight=0; $tf.MarginTop=0; $tf.MarginBottom=0
    $tf.WordWrap=-1; $tf.TextRange.Text=$value
    $tf.TextRange.Font.Name='Arial'; $tf.TextRange.Font.Size=$size
    $tf.TextRange.Font.Color.RGB=$color
    if($bold){$tf.TextRange.Font.Bold=-1}
    $shape
}
function Base($p,[int]$index,[string]$kicker,[string]$title) {
    $s=$p.Slides.Add($index,12)
    Rect $s 0 0 960 540 $white | Out-Null
    Rect $s 0 0 960 10 $teal | Out-Null
    Txt $s $kicker 44 24 850 19 11 $teal $true | Out-Null
    Txt $s $title 44 52 872 64 29 $navy $true | Out-Null
    Rect $s 44 496 872 1 $border | Out-Null
    Txt $s 'PBL6  |  Đà Nẵng  |  14.10.2026' 44 508 660 17 10 $muted | Out-Null
    $s
}
function Note($slide,[string]$value) { $slide.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text=$value }
function Row($slide,[int]$y,[string]$name,[string]$role,[int]$fill) {
    Rect $slide 44 $y 872 57 $fill | Out-Null
    Txt $slide $name 60 ($y+12) 220 40 17 $navy $true | Out-Null
    Txt $slide $role 292 ($y+10) 605 42 16 $ink | Out-Null
}

$app=New-Object -ComObject PowerPoint.Application
$p=$app.Presentations.Open($source,$true,$false,$false)
try {
    if($p.Slides.Count -ne 8){throw 'Expected source deck with 8 slides'}

    # 3. Define the product and research question in plain language.
    $s=Base $p 3 'CÂU HỎI NGHIÊN CỨU' 'Nhóm dự báo điều gì cho người dùng?'
    Txt $s 'Sản phẩm đang làm sâu' 44 135 416 31 20 $navy $true | Out-Null
    Txt $s '1–6 giờ tới' 44 179 420 50 31 $teal $true | Out-Null
    Txt $s 'Mỗi giờ phát hành một bản mới cho 93 ô Đà Nẵng, mỗi ô rộng khoảng 10–11 km.' 44 239 415 95 18 $ink | Out-Null
    Txt $s 'App ưu tiên tổng mưa 3 giờ và xác suất mưa mạnh, kèm thời điểm dữ liệu.' 44 343 416 89 18 $ink | Out-Null
    Rect $s 480 139 1 295 $border | Out-Null
    Txt $s 'Ba câu hỏi phải trả lời' 508 135 408 31 20 $navy $true | Out-Null
    Txt $s '1. Dữ liệu mưa nào đủ tin để học?' 508 188 400 49 18 $ink | Out-Null
    Txt $s '2. Đổi mô hình hoặc đặc trưng địa phương có giúp trên cùng mẫu?' 508 249 400 77 18 $ink | Out-Null
    Txt $s '3. Dữ liệu có đến kịp để app dự báo thật và vượt đối chứng ECMWF?' 508 344 400 88 18 $ink | Out-Null
    Txt $s 'Dự báo 1–3 ngày bằng TFT là giai đoạn sau. App hiện chưa dự báo ngập từng đường.' 44 450 872 38 15 $orange $true | Out-Null
    Note $s 'Nói: Bài toán không chỉ là tăng điểm mô hình. Nhóm dự kiến phát hành dự báo mưa mỗi giờ trong 1–6 giờ tới theo 93 ô lưới Đà Nẵng. Người dùng thấy tổng mưa 3 giờ và xác suất, nhưng lưới khoảng 10–11 km không cho biết một con đường sẽ ngập. Ba câu hỏi nghiên cứu là nhãn, lợi ích của thiết kế mô hình/đặc trưng, và khả năng chạy đúng giờ. Sản phẩm TFT 1–3 ngày làm sau. Nguồn nội bộ: CLAUDE.md, KE_HOACH_DU_AN.md mục 2, project_plan_v2.md.'

    # 4. Source roles and data timing.
    $s=Base $p 4 'DỮ LIỆU' 'Mỗi nguồn có một vai trò khác nhau'
    Row $s 139 'GSMaP GC v8' 'Mưa lịch sử hiệu chỉnh trạm: nhãn để mô hình học và chấm.' $pale
    Row $s 203 'GSMaP raw / NRT' 'Mưa vệ tinh gần hiện tại: đầu vào, phải kiểm tra giờ tệp đến.' $light
    Row $s 267 'ERA5' 'Khí tượng đã xảy ra: nghiên cứu hồi cứu và huấn luyện thử.' $pale
    Row $s 331 'ECMWF IFS' 'Bản dự báo đã phát hành: đầu vào vận hành và đối chứng app.' $light
    Row $s 395 'Trạm GSOD' 'Đối chiếu độc lập một phần cho mưa ngày; chưa có trạm giờ rộng.' $pale
    Txt $s 'Giờ dự báo thật chỉ được dùng dữ liệu đã tồn tại trước giờ phát hành.' 44 463 872 28 16 $orange $true | Out-Null
    Note $s 'Nói: Cần phân biệt nhãn, đầu vào và đối chứng. GSMaP GC là mưa lịch sử làm đích học, còn GSMaP raw/NRT là quan trắc gần thời gian thực dùng lúc phát hành. ERA5 là dữ liệu hồi cứu, không thể giả vờ đã có tại thời điểm dự báo. ECMWF IFS là bản dự báo từ trước giờ đích, dùng cả đầu vào và đối chứng. Trạm GSOD giúp audit nhãn nhưng không phải tập trạm giờ độc lập. Nguồn: CLAUDE.md, project_plan_v2.md mục 0/1/4, reports/station_benchmark/README.md. Chưa hoàn tất T-OPS thay ERA5 bằng đầu vào phát hành thật.'

    # 6. Design and model comparisons.
    $s=Base $p 6 'PHƯƠNG PHÁP' 'So cùng dữ liệu để biết thay đổi nào thật sự giúp'
    Txt $s 'Thiết kế phép so' 44 137 420 28 20 $navy $true | Out-Null
    Txt $s '30 ô cố định theo địa hình và khoảng cách biển' 44 185 416 56 18 $ink | Out-Null
    Txt $s '3 năm kiểm chứng: 2021, 2022, 2023' 44 248 416 51 18 $ink | Out-Null
    Txt $s '3 lần khởi tạo; test 2025 giữ kín' 44 308 416 53 18 $ink | Out-Null
    Txt $s 'Cùng ô, cùng giờ, cùng nhãn; báo khoảng tin cậy.' 44 371 416 68 18 $teal $true | Out-Null
    Rect $s 480 137 1 307 $border | Out-Null
    Txt $s 'Các phép thử' 508 137 408 29 20 $navy $true | Out-Null
    Txt $s 'LightGBM: mức sàn học máy dễ kiểm tra.' 508 185 399 54 17 $ink | Out-Null
    Txt $s 'Bi-LSTM: mô hình chuỗi đang thử cho 1–6 giờ.' 508 246 399 54 17 $ink | Out-Null
    Txt $s 'RAW so DOMAIN: dữ liệu thô hay thêm biểu diễn gió, ẩm, địa hình?' 508 308 399 72 17 $ink | Out-Null
    Txt $s 'Tweedie: đổi cách học lượng mưa lệch về số 0 và mưa lớn.' 508 393 399 52 17 $ink | Out-Null
    Txt $s 'Chấm riêng sai số mm, bắt mưa mạnh và chất lượng xác suất.' 44 463 872 28 16 $orange $true | Out-Null
    Note $s 'Nói: Để không nhầm hiệu quả mô hình với khác biệt dữ liệu, nhóm giữ 30 ô, cùng thời điểm, cùng nhãn, ba năm validation, ba seed; chọn tham số ở năm calibration trước khi chấm. LightGBM là mức sàn mạnh, Bi-LSTM đọc chuỗi; RAW so DOMAIN hỏi giá trị biểu diễn vật lý địa phương. Tweedie là hàm mất mát phù hợp hơn với mưa có nhiều số 0 và đuôi lớn. RMSE là sai số lượng mưa, CSI đo khả năng phát hiện mưa vượt ngưỡng, BSS đo xác suất so khí hậu. Test 2025 chưa mở. Nguồn: reports/domain_screen_danang/README.md, reports/followup_danang/amount/README.md, reports/followup_danang/bilstm_tweedie/README.md.'

    # 10. Deployment path.
    $s=Base $p 10 'TRIỂN KHAI ỨNG DỤNG' 'Một dự báo chỉ hiển thị khi dữ liệu đầu vào hợp lệ'
    Row $s 142 '1. Thu nguồn' 'Lấy NRT và forecast; lưu giờ phát hành, giờ nhận, phiên bản.' $pale
    Row $s 209 '2. Chặn lỗi' 'Kiểm tra đủ cửa sổ 24 giờ, dữ liệu không cũ hoặc thiếu.' $light
    Row $s 276 '3. Suy luận' 'Chạy checkpoint được chọn và hiệu chỉnh xác suất.' $pale
    Row $s 343 '4. Hiển thị' 'Bản đồ 93 ô: mm/3 giờ, xác suất, thời điểm cập nhật.' $light
    Txt $s 'Hiện có demo từ checkpoint trên dữ liệu lịch sử; AI live chưa bật.' 44 435 872 39 19 $orange $true | Out-Null
    Note $s 'Nói: Demo hôm nay chạy từ checkpoint thật và đã đối chiếu 36 trường hợp suy luận qua API, nhưng là dữ liệu archive. Để chạy live phải ghi giờ file JAXA đến liên tục, kiểm tra NRT có đủ cửa sổ và forecast ECMWF sẵn trước issue, chấm T-OPS cùng mẫu, rồi mới chọn checkpoint. Nếu thiếu nguồn, app cần thông báo trạng thái và dùng forecast nguồn đã kiểm chứ không bịa dự báo AI. Nguồn: reports/followup_danang/nrt_latency_sensitivity.json; reports/followup_danang/jaxa_live_first_detection.json; demo/domain_api.py; CLAUDE.md.'

    # Update static footer page numbers on all non-cover slides.
    for($i=2;$i -le $p.Slides.Count;$i++) {
        $slide=$p.Slides.Item($i)
        $updated=$false
        foreach($shape in $slide.Shapes) {
            try {
                if($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) {
                    $old=$shape.TextFrame.TextRange.Text.Trim()
                    if($shape.Top -ge 495 -and $old -match '^\d{1,2}$') {
                        $shape.TextFrame.TextRange.Text=[string]$i
                        $updated=$true
                    }
                }
            } catch { }
        }
        if(-not $updated){ Txt $slide ([string]$i) 873 508 43 17 10 $muted | Out-Null }
    }

    $draft=Join-Path $OutputDir 'PBL6_Da_Nang_full_brief_2026_10_14_draft.pptx'
    $p.SaveAs($draft,24)
    for($i=1;$i -le $p.Slides.Count;$i++) {
        $png=Join-Path $OutputDir ('full_slide_{0:D2}.png' -f $i)
        $p.Slides.Item($i).Export($png,'PNG',1280,720)
    }
    Write-Output "DRAFT $draft slides=$($p.Slides.Count)"
} finally {
    $p.Close(); $app.Quit()
}
