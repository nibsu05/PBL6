"""Beginner presentation from frozen evidence. No model fit or rescore."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import copy
import json
from pptx.util import Inches
from docx import Document
from docx.shared import Pt
from scripts.build_short_range_overview import Deck, readable
from scripts.short_range_overview_data import Evidence, REFERENCES, sha, write_json, fmt

NAME = 'short_range_explained_v2_2026_11_18'
PUBLIC = ROOT / 'reports' / NAME
PRIVATE = ROOT / 'data/operational' / NAME
OLD = ROOT / 'reports/short_range_comprehensive_2026_11_18'
PPTX = 'PBL6_NGAN_HAN_GIAI_THICH_DE_HIEU.pptx'
REFS = copy.deepcopy(REFERENCES)
REFS.update({
 'E1': dict(short='LightGBM · objective', title='L2 và Tweedie với log-link; p = 1,5 là cấu hình của dự án',
  url='https://lightgbm.readthedocs.io/en/stable/Parameters.html', status='Tài liệu chính thức; không chứng minh Tweedie luôn tốt hơn'),
 'E2': dict(short='scikit-learn · Tweedie', title='Với 1 < p < 2: hỗ trợ giá trị 0 và giá trị dương liên tục',
  url='https://scikit-learn.org/stable/modules/linear_model.html#tweedie-regression', status='Cơ sở thử một loss phù hợp dữ liệu không âm, lệch'),
 'E3': dict(short='ECMWF · Brier score', title='Brier score và Brier skill score so với tham chiếu',
  url='https://confluence.ecmwf.int/pages/viewpage.action?pageId=240849421', status='Dùng để giải thích ý nghĩa BSS, không đặt ngưỡng đạt cho dự án'),
 'E4': dict(short='ECMWF · quyết định', title='Understanding how forecast users make decisions',
  url='https://www.ecmwf.int/en/newsletter/165/news/understanding-how-forecast-users-make-decisions', status='Mức chấp nhận phụ thuộc mục đích và chi phí quyết định'),
 'E5': dict(short='PyTorch · GRU', title='GRU: mạng hồi quy có cổng ghi nhớ thông tin trong chuỗi',
  url='https://docs.pytorch.org/docs/2.15/generated/torch.nn.GRU.html', status='Tài liệu chính thức; cấu hình nhỏ của dự án không phải thuật ngữ kiến trúc riêng'),
})


class BeginnerDeck(Deck):
    @staticmethod
    def source_note(item):
        text = 'Phạm vi: ' + item.get('scope', 'Giải thích phương pháp; ví dụ giả định được đánh dấu riêng.')
        for key in item.get('refs', []):
            r = REFS[key]
            text += '\n[' + key + '] ' + r['short'] + ' — ' + r['url']
        return text

    def new(self, item):
        base = dict(item, refs=[k for k in item.get('refs', []) if k in REFERENCES])
        s = super().new(base)
        for shape in list(s.shapes):
            if shape.top == Inches(7.21):
                shape._element.getparent().remove(shape._element)
        refs = item.get('refs', [])[:3]
        if refs:
            for j, key in enumerate(refs):
                r = REFS[key]
                self.text(s, .65 + 4.08*j, 7.21, 3.95, .23, '['+key+'] '+r['short'], 10.2, '546A79', url=r['url'])
        else:
            self.text(s, .65, 7.21, 12, .23, '18/11/2026 • Nguồn và phép tính: ghi chú / numeric_bindings.json. Không huấn luyện mới.', 10.2, '546A79')
        s.notes_slide.notes_text_frame.text = readable(item['notes']) + '\n\n' + self.source_note(item)
        return s

    def render(self, item):
        if item['kind'] == 'image':
            s = self.new(item)
            path = PUBLIC / item['image']
            self.picture(s, path if path.exists() else OLD / item['image'])
        else:
            super().render(item)


def build_items(e):
    items = []
    derived = []
    scope = 'Hồi cứu 2026 modern • 57 trạm • 14.488 mẫu trạm–issue • chưa đủ cả năm'

    def add(kind, title, notes, takeaway, **kwargs):
        items.append(dict(kind=kind, title=title, notes=notes, takeaway=takeaway,
                          section='PBL6 · GIẢI THÍCH TỪ ĐẦU', main=True, **kwargs))

    def value(name, model, h, col, **extra):
        filters = dict(evaluation_set='retrospective2026_modern', model=model, horizon=h, **extra)
        return e.value('window', name, filters, col, 2)

    def point(model, h, metric='macro_rmse'):
        return value('point_metrics', model, h, metric, functional='mean')

    def percent(name, numerator, denominator, digits=1):
        number = 100*numerator/denominator
        shown = fmt(number, digits)+'%'
        derived.append(dict(name=name, operation='100*numerator/denominator', numerator=numerator,
                            denominator=denominator, value=number, display=shown, digits=digits))
        return shown

    selection = e.js('reports/gfs_training_window_2026_11_18/selection.json')
    old_manifest = e.js('reports/short_range_comprehensive_2026_11_18/slide_manifest.json')
    add('cover', 'Dự báo mưa tại trạm:\nmô hình học gì, kết quả tốt đến đâu?',
        'Bản này dành cho người chưa biết dự án. Đi từ một mẫu dữ liệu đến cách mô hình học, rồi mới đọc kết quả. Mỗi kết quả được gắn với câu hỏi cụ thể và một đối chứng. Luồng chính dài khoảng 28 phút; phụ lục giữ các bảng chi tiết, paper và cấu hình để trả lời giảng viên. Không có lần huấn luyện mới trong bản trình bày này. Mục tiêu là giải thích đúng bằng chứng đã có, không làm điểm số đẹp hơn.',
        'Đọc theo ba câu hỏi: dự báo gì → học như thế nào → có hơn cách đơn giản không?',
        subtitle='Vrain đo mưa tại điểm + GFS dự báo thời tiết + học máy',
        badges=['57 trạm nghiên cứu', 'Ba tổng 24 giờ riêng', 'Luồng chính ~28 phút'])
    add('target_timeline', 'Đầu ra: lượng mưa ngày 1, ngày 2 và ngày 3',
        'Giả sử phát dự báo lúc 19 giờ ngày 18/11. Ngày 1 là lượng mưa từ 19 giờ hôm đó đến 19 giờ hôm sau. Ngày 2 là cửa sổ 24 giờ kế tiếp, và ngày 3 cũng vậy. Có ba con số riêng cho từng trạm, không phải một tổng tích lũy 72 giờ. Lịch trên hình là ví dụ giải thích cửa sổ thời gian, không phải một bản dự báo đã được phát. Đơn vị của mỗi đầu ra là mm trong 24 giờ tại điểm đặt trạm.',
        'Một trạm nhận ba số mm; dự án hiện không dự báo mưa trung bình toàn Đà Nẵng.')
    add('inputs', 'Một mẫu học là một trạm tại một lần phát dự báo',
        'Ví dụ trên slide chỉ minh họa, không phải số đo hoặc dự báo thật. Ở thời điểm phát, ta đã có mưa quá khứ tại trạm và một bản GFS dự báo 12 mm cho ngày mai. Sau khi ngày mai kết thúc, Vrain ghi nhận 20 mm. Khi huấn luyện từ các ngày lịch sử, 20 mm là đáp án để tính lỗi. Khi dự báo một ngày chưa xảy ra, đáp án này chưa có và tuyệt đối không được đưa vào đầu vào. Mẫu của trạm khác giữ lịch sử và đáp án riêng.',
        'MINH HỌA: đầu vào đã biết trước giờ phát; đáp án là số đo xuất hiện sau đó.',
        panels=[('Thông tin đầu vào', 'Mưa quá khứ tại trạm\nGFS dự báo ngày mai: 12 mm\nKhí tượng, vị trí, địa hình'),
                ('Đáp án để học', 'Vrain ngày mai đo: 20 mm\nChỉ có sau khi hết ngày\nMỗi trạm có đáp án riêng')])
    add('table', 'Nguồn nào làm đầu vào, nguồn nào làm đáp án?',
        'Vrain cung cấp mưa đo tại trạm, dùng cho lịch sử và nhãn cần dự đoán. GFS cung cấp bản dự báo khí tượng đã khởi tạo trước thời điểm phát, giúp mô hình có thông tin về thời tiết sắp tới. ERA5 là tái phân tích và vẫn có vai trò ở bộ dữ liệu giờ riêng, nhưng không được dùng trường ERA5 của ngày tương lai làm đầu vào cho thí nghiệm dự báo GFS–Vrain này. GFS được nội suy từ bốn nút lưới 0,25 độ về tọa độ trạm; nội suy không biến nó thành số đo tại điểm.',
        'Nhãn là mưa Vrain; GFS là thông tin dự báo đầu vào, không thay thế số đo.',
        headers=['Nguồn', 'Thông tin gì?', 'Vai trò ở nhánh ngắn hạn'],
        rows=[['Vrain', 'Mưa đo tại từng trạm', 'Lịch sử và nhãn mưa tương lai'],
              ['GFS', 'Mưa, nhiệt, ẩm, gió dự báo', 'Đầu vào cho ba ngày sắp tới'],
              ['DEM', 'Địa hình quanh tọa độ', 'Đặc trưng vị trí, không phải nhãn'],
              ['ERA5', 'Khí tượng tái phân tích', 'Bộ giờ riêng; không lấy tương lai']],
        widths=[1.5,4.5,6.1], row_h=.79, size=20, refs=['D1','D2'])
    add('cards', 'Mô hình chung vẫn dự báo riêng cho từng trạm',
        'Chung có nghĩa là dùng chung bộ quy tắc hoặc trọng số đã học. Mỗi mẫu vẫn mang mã trạm, tọa độ, địa hình, lịch sử mưa và GFS tại vị trí của chính trạm đó, nên đầu ra có thể khác nhau giữa các trạm. Cách này có thể chia sẻ kinh nghiệm giữa trạm nhiều và ít lịch sử. Tuy nhiên, dự án chưa so công bằng với 57 mô hình riêng nên không khẳng định mô hình chung tốt hơn. Dữ liệu các trạm trong cùng đợt mưa cũng có tương quan, không tạo ra 57 năm lịch sử độc lập.',
        'Đây là lựa chọn thiết kế; chưa có thí nghiệm chứng minh hơn 57 mô hình riêng.',
        cards=[('Trạm A', 'Lịch sử của A\nGFS tại A\n→ dự báo cho A'),
               ('Trạm B', 'Lịch sử của B\nGFS tại B\n→ dự báo cho B'),
               ('Cùng cách học', 'Chia sẻ quy tắc\nKhông gộp nhãn\nCần đối chứng riêng')])
    add('table', 'Vì sao chọn phát lúc 19 giờ?',
        '19 giờ là mốc cố định của thí nghiệm để thống nhất cửa sổ mưa 19–19 và phép so các mô hình. Nó không phải giờ tối ưu đã được khảo sát người dùng hoặc chứng minh bằng paper cho dự án. GFS 00 UTC tương ứng 07 giờ Việt Nam, cách giờ phát 12 tiếng. Thí nghiệm giả định nguồn GFS trễ 8 tiếng và trạm trễ 1 tiếng, nên chỉ dùng tổng gần nhất kết thúc lúc 18 giờ. Khả dụng thực tế từng ngày vẫn cần ghi nhận trước giờ phát. Có thể đổi giờ hoặc cycle, nhưng phải định nghĩa và kiểm tra lại protocol.',
        '19 giờ là quy ước nghiên cứu hiện tại; chưa có bằng chứng đây là giờ tốt nhất.',
        headers=['Mốc', 'Ý nghĩa'], rows=[['07h Việt Nam', 'GFS khởi tạo 00 UTC được sử dụng'],
          ['18h', 'Kết thúc dữ liệu mưa gần nhất được phép dùng'],
          ['19h', 'Giờ phát cố định; bắt đầu cửa sổ nhãn'],
          ['Chưa chứng minh', 'Độ trễ nguồn thực tế và ưu thế so với giờ khác']],
        widths=[3.1,9.0], row_h=.78, size=21, refs=['D1'])
    add('quality', 'Dữ liệu dùng được không có nghĩa là mọi trạm đều đủ',
        'Danh mục có 86 vị trí nhưng chỉ 57 trạm vào thí nghiệm cố định theo điều kiện lịch sử huấn luyện. Một trạm thiếu giờ không làm mất mẫu hợp lệ của trạm khác. Nhãn ngày chỉ được tính khi đủ 24 số giờ sau kiểm tra; không điền thiếu thành 0 và không lấy mưa vệ tinh để lấp đáp án. Nguồn mưa đã thu tới ngày 15/11/2026 và issue đủ ba nhãn tới 12/11. Hai kênh Vrain được báo riêng vì chưa chứng minh liên tục. Kiểm tra cấu trúc và ghép dữ liệu không chứng nhận độ chính xác vật lý của cảm biến.',
        'Đã kiểm tra cách ghép và tính nhãn; chất lượng cảm biến và nguồn vẫn có giới hạn.',
        levels=[('86 vị trí danh mục', '57 trạm đủ điều kiện trong thí nghiệm đang báo cáo.', 'good'),
                ('Thiếu giờ → thiếu nhãn', 'Không đổi thành 0 mm; chỉ dùng cửa sổ đủ 24 giờ.', 'good'),
                ('Giới hạn nguồn', 'Tách hai kênh; chưa chứng nhận cảm biến hoặc liên tục.', 'pending')])
    add('table', 'Đâu là mô hình nhóm học, đâu là mốc để so sánh?',
        'LightGBM và GRU là hai họ mô hình học máy nhóm đã huấn luyện. GFS cũng là mô hình, nhưng là hệ thống dự báo khí tượng bằng mô phỏng vật lý của NOAA; nhóm lấy bản dự báo đã có, không huấn luyện lại GFS. MOS là hậu xử lý thống kê, ở dự án được fit bằng hồi quy đơn giản từ mưa GFS và mùa trong năm để dự đoán mưa trạm. Quy tắc luôn 0 mm không cần học. Cả năm cách có thể cho lượng mưa để chấm trên cùng ngày và trạm. Mốc đơn giản là vai trò trong thí nghiệm, không phải tên một mô hình. Nếu mô hình phức tạp chưa hơn cách đơn giản, chưa có lý do nói độ phức tạp tạo thêm giá trị.',
        'Đều có thể tạo dự báo để chấm; khác nhau ở cách tạo và mức độ học của nhóm.',
        headers=['Tên','Bản chất','Tự huấn luyện?','Mục đích'],
        rows=[['LightGBM','Học từ bảng đặc trưng','Có','Mô hình chính để thử biến'],
              ['GRU','Mạng đọc chuỗi quá khứ','Có','Mô hình học chuỗi để so'],
              ['GFS','Vật lý khí tượng (NOAA)','Không','Dự báo nền trước hậu xử lý'],
              ['MOS','Hồi quy hiệu chỉnh GFS','Có','Mốc hậu xử lý đơn giản'],
              ['Luôn 0 mm','Quy tắc cố định','Không','Kiểm tra việc chỉ đoán khô']],
        widths=[1.7,4.2,2.3,3.9],row_h=.73,size=18.5,refs=['D1','D3','E5'])
    add('flow', '“Huấn luyện” là sửa cách dự đoán từ các ngày đã biết',
        'Huấn luyện không phải chỉ nạp file rồi tạo ra một con số chính xác. Với nhiều ngày lịch sử, mô hình dùng đầu vào được phép biết trước giờ phát để dự đoán lượng mưa. Ta so dự đoán với mưa trạm đã xảy ra, tính lỗi theo quy tắc đã chọn, rồi cập nhật mô hình. Quy trình lặp nhiều lần trên tập học. Các ví dụ đánh giá phải ở thời gian riêng để kiểm tra khả năng dùng quy tắc đã học cho dữ liệu khác. Dữ liệu tương lai không được tham gia cập nhật trọng số.',
        'Mô hình học quan hệ từ đầu vào đến số đo trạm, không học bằng năm đánh giá.',
        steps=[('Nhìn đầu vào', 'Thông tin trước\ngiờ phát'), ('Dự đoán', 'Một lượng mưa\ncho mỗi hạn'),
               ('Đối chiếu', 'So với mưa trạm\nđã xảy ra'), ('Sửa quy tắc', 'Giảm lỗi trên\ntập huấn luyện')])
    add('cards', 'LightGBM học từ bảng đặc trưng như thế nào?',
        'Với mỗi hạn dự báo, LightGBM nhận một bảng: mỗi hàng là một trạm tại một thời điểm, các cột là đặc trưng. Mưa của bảy ngày trước cũng là bảy cột trong bảng, nên LightGBM có lịch sử mưa chứ không phải chỉ GRU mới có. Các cây được thêm dần để giảm hàm mất mát trên tập học. Đầu lượng mưa là dự đoán trực tiếp mưa trạm, trong đó GFS là một cột đầu vào. Vì vậy, gọi đây là hậu xử lý GFS về mặt bài toán là đúng, nhưng không nên nói thuật toán luôn bắt đầu từ GFS rồi cộng một residual đã định trước. Dự án có mô hình riêng theo hạn và loại đầu ra, cùng chia sẻ dữ liệu nhiều trạm.',
        'GFS là một đầu vào; mô hình học lượng mưa tại trạm từ toàn bộ bảng.',
        cards=[('Bảng đầu vào', 'Có 7 cột mưa quá khứ\nMỗi hàng: trạm × giờ phát\n26 biến ở cấu hình N3'),
               ('Nhiều cây nhỏ', 'Thêm cây lần lượt\nGiảm lỗi trên tập học\nGiới hạn độ phức tạp'),
               ('Đầu ra lượng', 'Một số mm\nKhông phải vùng trung bình\nSo với nhãn Vrain')], refs=['P1'])
    add('cards', 'GRU là mạng học diễn biến của chuỗi mưa',
        'GRU viết tắt của Gated Recurrent Unit, một dạng mạng nơ-ron đọc dữ liệu theo thứ tự và học giữ hoặc bỏ thông tin quá khứ. Có thể hình dung đọc bảy ngày mưa từ cũ đến mới thay vì chỉ nhìn một dòng rời rạc. Ở dự án, mỗi ngày có một lượng mưa trạm; phần ghi nhớ sau đó được ghép với GFS ba hạn và thông tin trạm. Nhỏ chỉ cấu hình ít tham số để hạn chế chi phí và nguy cơ học thuộc, không phải tên mô hình khác. N3 có 4.364 tham số, hidden 16; 17 epoch là 17 lượt học, không phải 17 ngày. GRU mới chạy protocol cũ; chưa chạy cửa sổ bốn năm A–D. Thắng điểm số chưa tự chứng minh cơ chế ghi nhớ là nguyên nhân duy nhất.',
        'GRU đọc chuỗi theo thứ tự; “nhỏ” chỉ kích thước cấu hình, không phải một mô hình thứ ba.',
        cards=[('Đọc 7 ngày', 'Từ ngày cũ đến mới\nMưa của chính trạm\nHọc diễn biến quá khứ'),
               ('Ghi nhớ', 'Học giữ thông tin\nTóm tắt chuỗi đã đọc\nGhép thông tin trạm'),
               ('Ghép dự báo GFS', 'Thời tiết ba ngày tới\nKết hợp với quá khứ\n→ Ba lượng mưa ngày')], refs=['P2','E5'])
    add('table', 'Mỗi nhóm năm làm một việc khác nhau',
        'Bảng này nói về protocol mới A–D. Hai cửa sổ học là 2021–2022 và 2021–2024 để kiểm tra tác động số năm. Các quý năm 2022 dùng kiểm tra có thứ tự thời gian bên trong phần học, giúp chọn tham số. Năm 2025 được phép hiệu chỉnh xác suất và ngưỡng cảnh báo, không fit cây dự báo lượng mưa. Năm 2026 được đánh giá hồi cứu và đã được xem, nên không gọi là test kín cho các chỉnh sửa tiếp theo. Nghiên cứu cũ có cách chia năm riêng và giữ nguyên kết quả.',
        'Không trộn vai trò các năm giữa protocol cũ và mới; 2026 hiện là hồi cứu.',
        headers=['Giai đoạn', 'Vai trò trong vòng A–D mới'],
        rows=[['2021–2022 / 2021–2024', 'Học trọng số: cửa sổ ngắn / dài'],
              ['Các quý 2022', 'Chọn cấu hình chỉ bằng quá khứ của tập học'],
              ['2025', 'Hiệu chỉnh xác suất và ngưỡng cảnh báo'],
              ['2026 đã xem', 'Đánh giá hồi cứu; không chọn lại mô hình theo điểm']],
        widths=[4.2,7.9], row_h=.78, size=20.5)
    add('flow', 'Chọn tham số bằng cách giả lập dự báo trong quá khứ',
        'Thay vì xáo trộn các ngày, mỗi lượt kiểm tra giữ lại một quý năm 2022 và chỉ học từ thời gian sớm hơn quý đó. Có khoảng cách bảy ngày và loại các nhãn 72 giờ băng ranh để giảm chồng lấn. Ba cấu hình cây, hai loss, bốn quý và ba hạn tạo thành 72 lượt CV. Điểm dùng để lựa chọn là RMSE trung bình theo trạm, sau chặn dự đoán âm về 0. Số cây và cấu hình cuối được dùng chung giữa bốn phương án để so sánh không bị lệch ngân sách.',
        'CV là kiểm tra trong tập học, không phải xem năm 2026 để tìm cấu hình đẹp.',
        steps=[('Học từ quá khứ', 'Chỉ ngày trước\nquý giữ lại'), ('Giữ khoảng cách', 'Gap 7 ngày\nPurge nhãn 72h'),
               ('Chấm quý giữ lại', 'Lặp bốn quý\nnăm 2022'), ('Chọn cấu hình', '72 lượt CV\nNgân sách chung')])
    add('inventory', 'Ba con số về huấn luyện nên hiểu thế nào?',
        'Cấu hình được chọn có tối đa bảy lá mỗi cây, tức mỗi cây chỉ tạo ra một số ít vùng điều kiện. Ngày 1 dùng 171 cây, ngày 2 dùng 109 và ngày 3 dùng 76. Đây là số cây cộng dần, không phải số tầng mạng hoặc số ngày đầu vào. Ba seed 17, 29, 43 thay đổi một số bước lấy mẫu ngẫu nhiên; các dự đoán cuối được tổng hợp theo protocol. Dao động giữa seed giúp thấy nhạy với lần chạy nhưng không phải khoảng tin cậy thống kê theo thời tiết.',
        '7 lá = độ phức tạp mỗi cây; 171 cây = số bước thêm cây; 3 seed = ba lần chạy.',
        stats=[('7 lá', 'Tối đa mỗi cây'), ('171 cây', 'Đầu lượng mưa ngày 1'), ('3 seed', '17, 29, 43')],
        bottom='Ngày 2: 109 cây • Ngày 3: 76 cây\nGiữ ngân sách giống nhau khi so bốn cấu hình A–D.')
    add('table', 'L2: sai càng nhiều, điểm phạt càng tăng nhanh',
        'L2 ở đây là hàm mất mát bình phương sai số dự đoán, không phải thuật ngữ regularization L2 dù tên giống nhau. Lấy dự đoán trừ lượng mưa thực tế rồi bình phương. Trong ví dụ giả định, thực tế 50 mm: dự đoán 40 mm sai 10 mm và nhận phạt 100; dự đoán 20 mm sai 30 mm và nhận phạt 900. Vì vậy lỗi lớn ảnh hưởng mạnh đến việc học. L2 gắn với mục tiêu dự báo trung bình và giảm RMSE, nhưng chỉ tối ưu trên tập học không bảo đảm tốt nhất trên năm khác hoặc ở từng trạm.',
        'L2 là cách chấm lỗi để học; phạt mạnh dự đoán lệch nhiều, không chỉ ngày mưa lớn.',
        headers=['Thực tế (minh họa)', 'Dự đoán', 'Sai số', 'Điểm phạt L2'],
        rows=[['50 mm', '40 mm', '−10 mm', '**100**'], ['50 mm', '20 mm', '−30 mm', '**900**'],
              ['0 mm', '30 mm', '+30 mm', '**900**']], widths=[3.5,2.7,2.7,3.2], row_h=.9, size=22, refs=['E1','P4'])
    add('cards', 'Tweedie: một cách học phù hợp để thử với mưa',
        'Tweedie là một họ phân phối dùng để xây dựng hàm mất mát. Với tham số p bằng 1,5 đang dùng, họ này có thể mô tả giá trị bằng 0 cùng với các giá trị dương liên tục và lệch phải. Điều đó phù hợp về mặt giả thuyết với mưa: nhiều ngày khô, nhiều ngày mưa ít, ít ngày rất lớn. LightGBM dùng log-link cho dự báo trung bình dương; không có nghĩa nhóm đổi nhãn thành log1p hay chia lại lượng mưa. p không phải xác suất mưa và 1,5 không phải ngưỡng mm. Chưa có kiểm định phân phối khẳng định dữ liệu Vrain đúng Tweedie; vẫn phải kiểm tra bằng kết quả ngoài tập học.',
        'Có lý do để thử Tweedie; tên loss không chứng minh mô hình dự báo tốt hơn.',
        cards=[('Đặc điểm mưa', 'Có ngày 0 mm\nGiá trị không âm\nÍt ngày mưa rất lớn'),
               ('Cấu hình đã dùng', 'Tweedie với p = 1,5\nHọc lượng trung bình\nKhông phải xác suất'),
               ('Phải kiểm tra', 'So cùng đầu vào\nCùng ngân sách cây\nChấm cùng ngày, trạm')], refs=['E1','E2'])
    add('factorial', 'Vì sao báo cáo cả Tweedie lẫn L2?',
        'Bốn phương án tách hai câu hỏi: thêm hai năm dữ liệu có ích không, và đổi cách tính lỗi có ích không. A và B cùng Tweedie, khác cửa sổ học; C và D cùng L2, cũng khác cửa sổ. So A với C hoặc B với D giữ số năm để xét loss. Cả bốn giữ 57 trạm, 26 biến, số cây và seed. Chỉ thay loss đầu dự báo trung bình; đầu median và xác suất được dùng chung theo cửa sổ. Do đó không dùng B so D để khẳng định thay đổi POD hay FAR. Tweedie được chọn cho bước tiếp từ CV trong phần học, không chọn bằng điểm 2026.',
        'Đổi loss chỉ là một thay đổi trong cách học; không phải bốn kiến trúc khác nhau.', refs=['E1'])
    add('inputs', 'Một số mm và một xác suất trả lời hai câu hỏi',
        'Đầu lượng mưa trả lời dự báo bao nhiêu mm trong từng ngày. Đầu xác suất trả lời khả năng lượng mưa vượt một ngưỡng định trước, ví dụ 50 mm trong 24 giờ tại trạm. Dự báo 30% không có nghĩa sẽ mưa 30 mm và cũng không phải độ chính xác của mô hình. Đầu median tối ưu cho sai lệch tuyệt đối; đầu mean tối ưu cho bình phương sai số. Minh họa năm kết quả có thể xảy ra 0, 0, 0, 0, 50 mm cho trung bình 10 mm nhưng trung vị 0 mm. Hai số khác nhau vì trả lời hai đại lượng khác nhau.',
        'Không dùng % xác suất thay mm; không lấy MAE median để gọi đó là RMSE mean.',
        panels=[('Lượng mưa: mm', 'Mean: trung bình có điều kiện\nMedian: trung vị có điều kiện\nĐánh giá RMSE / MAE phù hợp'),
                ('Sự kiện: % xác suất', 'Ví dụ: nguy cơ ≥50 mm/24h\nCần chọn ngưỡng để báo có\nChấm BSS và POD/FAR/CSI')], refs=['P4'])
    add('flow', 'Hiệu chỉnh xác suất không phải sửa số đo mưa',
        'Mô hình có thể nói xác suất 70% nhưng tần suất quan sát ở những trường hợp tương tự không gần 70%. Hiệu chỉnh dùng tập riêng năm 2025 để điều chỉnh đầu ra xác suất. Sau đó chọn ngưỡng báo có theo CSI bằng xác suất dự đoán ngoài fold thời gian, rồi khóa trước đánh giá. Ở ngày 1, cutoff đã chọn là 0,35: xác suất từ 35% trở lên được chuyển thành một lần báo có mưa từ 50 mm. Đây là hai ngưỡng khác nhau, một ngưỡng xác suất và một ngưỡng lượng mưa. Quy trình không chỉnh các nhãn Vrain.',
        '50 mm xác định sự kiện; 35% là ngưỡng quyết định báo có ở ngày 1.',
        steps=[('Mô hình học', 'Dùng năm học\nđể fit trọng số'), ('Hiệu chỉnh', 'Dùng riêng 2025\nđể chỉnh xác suất'),
               ('Chọn ngưỡng báo', 'CSI trên xác suất\nngoài fold'), ('Khóa rồi chấm', 'Hồi cứu 2026\nKhông đổi nhãn')])
    add('table', 'Minh họa: sai số được tính từ đâu?',
        'Đây là ba ví dụ giả định để tính tay, không phải ba ngày trong bộ dữ liệu thật. Lấy dự đoán trừ thực tế được +2, −3, −10 mm. MAE là trung bình độ lớn các sai số: 15 chia 3 bằng 5 mm. RMSE là căn của trung bình bình phương: căn của 113 chia 3, bằng khoảng 6,14 mm. Bias là trung bình sai số có dấu, bằng −3,67 mm, nghĩa là có xu hướng dự báo thiếu. RMSE lớn hơn MAE vì lần sai 10 mm được nhấn mạnh hơn. Chưa thể đánh giá tốt hay xấu nếu chưa biết đối chứng trên cùng các ngày này.',
        'MINH HỌA: MAE = 5 mm; RMSE ≈ 6,14 mm; Bias ≈ −3,67 mm.',
        headers=['Ví dụ giả định', 'Thực tế', 'Dự đoán', 'Dự đoán − thực tế'],
        rows=[['Ngày A', '0 mm', '2 mm', '+2 mm'], ['Ngày B', '10 mm', '7 mm', '−3 mm'],
              ['Ngày C', '30 mm', '20 mm', '−10 mm']], widths=[3,2.5,2.5,4.1], row_h=.87, size=23)
    rmse = point('B',1)[1]; mae = point('B',1,'macro_mae')[1]; bias = point('B',1,'macro_bias')[1]
    add('inventory', 'Kết quả thật: “RMSE 15,68 mm” nghĩa là gì?',
        f'Ba số trên slide đều thuộc cùng đầu mean của B và ngày 1 trong hồi cứu 2026 modern. RMSE {rmse} mm là chỉ số nhấn mạnh sai lệch lớn, không phải dự báo rằng ngày mai mưa {rmse} mm, cũng không phải sai lệch tuyệt đối trung bình. Nếu muốn diễn đạt trung bình lệch bao nhiêu mm, xem MAE {mae} mm. Bias {bias} mm cho thấy xu hướng dự báo thiếu trên toàn bộ tập, nhưng mức thiếu ở riêng ngày mưa lớn có thể nặng hơn. Các chỉ số này tính từng trạm rồi trung bình đều 57 trạm, gọi là macro; không phải tính lỗi của lượng mưa trung bình toàn vùng.',
        'RMSE là chỉ số lỗi; MAE dễ đọc hơn về số mm lệch trung bình. Cần xem cả hai.',
        stats=[(rmse+' mm','RMSE: nhấn mạnh lỗi lớn'), (mae+' mm','MAE: lệch tuyệt đối'), (bias+' mm','Bias: xu hướng thiếu/thừa')],
        bottom='Cùng mô hình B, cùng ngày 1, cùng đầu mean.\nTính từng trạm rồi trung bình đều; chưa nói “đủ tốt”.', scope=scope)
    add('table', '“Tốt” trước hết phải tốt hơn cách dự báo nào?',
        'Dữ liệu mưa thường có nhiều ngày khô nên luôn nói 0 mm có thể đạt MAE nhỏ mà bỏ sót toàn bộ mưa lớn. Vì thế cần ZERO. Khí hậu theo mùa dùng thống kê mưa các năm học. GFS là mô hình dự báo vật lý có sẵn của NOAA: trước hết kiểm tra học máy có hơn dùng trực tiếp bản đó không. MOS viết tắt Model Output Statistics, nghĩa là hậu xử lý thống kê đầu ra mô hình. MOS đơn giản của dự án chỉ nhận ba biến mưa GFS, sin và cos ngày trong năm; đầu mean dùng hồi quy Ridge, các đầu median và xác suất có mô hình riêng. Đây là mô hình nhóm có fit, không phải sản phẩm MOS chính thức của NOAA. MOS kiểm tra mức cải thiện có cần đến LightGBM hoặc GRU không. Mọi cách đều chấm cùng trạm, ngày, nhãn và metric.',
        'Đối chứng là mốc so thực nghiệm; không có ngưỡng RMSE chung áp dụng mọi nơi.',
        headers=['Đối chứng', 'Câu hỏi kiểm tra'], rows=[['0 mm mọi ngày', 'Mô hình có chỉ học đoán khô để giảm lỗi?'],
         ['Khí hậu theo mùa', 'Có hơn quy luật mưa thường gặp?'], ['GFS nguyên bản', 'Học máy tạo thêm giá trị gì so dự báo nền?'],
         ['MOS: hồi quy từ GFS', 'Có hơn một cách hậu xử lý ít phức tạp?']], widths=[3.6,8.5], row_h=.79, size=21, refs=['D1','D3'])
    comparison=[]
    for h in (1,2,3):
        g,gs=point('GFS',h); b,bs=point('B',h); m,ms=point('MOS_LONG',h)
        gain=percent('B_RMSE_reduction_vs_GFS_day'+str(h),g-b,g)
        comparison.append([f'Ngày {h}',gs,ms,'**'+bs+'**','**'+gain+'**'])
    add('table', 'Cùng ngày và trạm: B giảm lỗi so với GFS',
        'Bảng dùng đầu mean và cùng mẫu trong hồi cứu 2026 modern. Ngày 1 RMSE GFS khoảng 20,45 mm, MOS dài 18,93 mm và B 15,68 mm. Tỷ lệ giảm là lấy chênh lệch RMSE chia RMSE GFS, khoảng 23,3%. Đây là mức giảm một chỉ số lỗi, không phải độ chính xác 76,7% hoặc 23,3% số ngày đúng thêm. Cả ba hạn có điểm B thấp hơn GFS và MOS dài. Tuy nhiên, phép so B với các đối chứng ở protocol mới chưa có suy luận khoảng tin cậy được xác nhận riêng; bảng hiện là so sánh điểm trên giai đoạn đã xem.',
        'Đã có giá trị ở mức điểm số; chưa đủ để chứng nhận cải thiện ổn định hoặc vận hành.',
        headers=['Hạn', 'GFS', 'MOS dài', 'LightGBM B', 'Giảm so GFS'], rows=comparison,
        widths=[1.7,2,2.3,3.0,3.1], row_h=.9, size=22, scope=scope+' • RMSE mm, thấp hơn tốt hơn')
    a,as_=point('A',2); b,bs=point('B',2); delta=fmt(a-b,2); rel=percent('A_to_B_day2_RMSE_reduction',a-b,a)
    add('inputs', 'Thêm hai năm học: điểm tốt hơn đã đủ chắc chưa?',
        f'A và B cùng Tweedie và đầu vào N3, chỉ khác cửa sổ học. Ngày 2, A học 2021–2022 đạt RMSE {as_} mm, B học 2021–2024 đạt {bs} mm. Mức giảm {delta} mm, khoảng {rel}. Cả ba hạn B đều giảm điểm so A nhưng chưa đạt đủ tiêu chí suy luận đã định trước. Điều đó không chứng minh thêm dữ liệu vô ích; nó nói rằng thí nghiệm chưa có bằng chứng đủ mạnh để tách mức cải thiện khỏi biến động của thời tiết và mẫu. Không chọn lại mô hình theo năm 2026 sau khi thấy các điểm này.',
        'Điểm tốt hơn là tín hiệu; muốn khẳng định cải thiện phải kiểm tra độ chắc chắn.',
        panels=[('A: học hai năm', '2021–2022\nNgày 2: '+as_+' mm RMSE\nCùng đặc trưng, ngân sách'),
                ('B: học bốn năm', '2021–2024\nNgày 2: '+bs+' mm RMSE\nGiảm '+delta+' mm ≈ '+rel)], scope=scope)

    event={}
    for h in (1,2,3):
        filters=dict(threshold_mm=50,decision_rule='calibration_selected')
        event[h]={col:value('event_metrics','B',h,col,**filters)[0] for col in ['hits','misses','false_alarms','micro_pod','micro_far','macro_pod','macro_far','cutoff']}
    d=event[1]; H,M,F=[int(d[k]) for k in ('hits','misses','false_alarms')]
    pod=percent('B_day1_micro_POD',H,H+M); far=percent('B_day1_micro_FAR',F,H+F)
    add('inventory', 'Mưa ≥50 mm: ngày 1 bắt đúng và bỏ sót bao nhiêu?',
        f'Từ bảng đếm thật, có {H+M} trường hợp ngày–trạm mưa ít nhất 50 mm trong 24 giờ. Mô hình báo đúng {H} và bỏ sót {M}, nên POD gộp là {pod}. Trong {H+F} trường hợp đã phát báo có, {F} là báo nhầm, nên FAR gộp là {far}. Một đợt mưa có thể xuất hiện ở nhiều trạm và nhiều cửa sổ; không gọi đây là {H+M} cơn bão độc lập. Các tỷ lệ này tính từ tổng đếm, gọi là micro; có thể khác bảng macro tính tỷ lệ từng trạm rồi trung bình. Chưa có ngưỡng POD 0,4 chung để nói đạt.',
        f'POD gộp = {pod}; FAR gộp = {far}. Có tín hiệu nhưng vẫn bỏ sót nhiều.',
        stats=[(str(H),'Bắt đúng mưa lớn'),(str(M),'Bỏ sót mưa lớn'),(str(F),'Báo nhầm mưa lớn')],
        bottom=f'{H+M} ngày–trạm thực sự mưa lớn; {H+F} lần báo có.\nĐếm gộp micro, không phải trung bình tỷ lệ giữa trạm.', scope=scope+' • B • ngày 1 • cutoff 35%')
    bss=value('probability_metrics','B',1,'macro_bss',threshold_mm=50)[1]
    add('cards', 'BSS dương: xác suất có hơn khí hậu tham chiếu không?',
        'Brier score chấm khoảng cách giữa xác suất dự báo và sự kiện thực tế 0 hoặc 1. BSS so lỗi xác suất đó với khí hậu tham chiếu: BSS bằng 0 nghĩa là ngang tham chiếu, âm là kém hơn, 1 là hoàn hảo. Với một phép tính BSS, 0,36 tương ứng giảm khoảng 36% lỗi Brier so tham chiếu, không phải 36% dự báo đúng. Điểm thực trên slide là trung bình BSS từng trạm so CLIM_LONG được fit 2021–2024, nên không được lấy tỷ số của hai macro BS để tính ngược. BSS dương chưa bảo đảm ngưỡng báo có đang đáp ứng nhu cầu sử dụng.',
        'BSS > 0 là hơn khí hậu theo lỗi xác suất; không phải chứng nhận cảnh báo đủ tốt.',
        cards=[('Mốc 0', 'Ngang khí hậu\nBSS < 0: kém hơn\nBSS = 1: hoàn hảo'),
               ('B ngày 1: '+bss, 'Ngưỡng 50 mm/24h\nMacro giữa trạm\nTham chiếu CLIM_LONG'),
               ('Cần đọc cùng', 'POD: có bỏ sót?\nFAR: có báo nhầm?\nNhu cầu người dùng')], refs=['E3'], scope=scope)
    d=event[3]; H,M,F=[int(d[k]) for k in ('hits','misses','false_alarms')]; far3=percent('B_day3_micro_FAR',F,H+F)
    add('inventory', 'Ngày 3: hơn nửa số lần báo có là báo nhầm',
        f'Ở ngày 3, B có {H} lần bắt đúng, {M} lần bỏ sót và {F} lần báo nhầm mưa từ 50 mm. Có {H+F} lần báo có, trong đó {F} sai, tức FAR gộp {far3}. Cutoff ngày 3 là 20%, khác ngày 1 là 35%, nên thay đổi POD và FAR không chỉ do hạn dự báo mà còn do ngưỡng quyết định. Nếu hạ ngưỡng, thường bắt thêm sự kiện nhưng có thể tăng báo nhầm. Không được chỉ chọn POD cao để nói mô hình tốt. Chấp nhận tỷ lệ báo nhầm này hay không cần xét mục đích và chi phí hành động.',
        f'FAR gộp ngày 3 = {far3}; chưa đủ cơ sở gọi mô hình sẵn sàng cảnh báo.',
        stats=[(str(H),'Bắt đúng'),(str(M),'Bỏ sót'),(str(F),'Báo nhầm')],
        bottom=f'{F} / {H+F} lần báo có là nhầm.\nCần đánh giá đánh đổi, không đọc riêng POD.', scope=scope+' • B • ngày 3 • cutoff 20%')
    add('table', 'Có ba mốc để kết luận “đủ tốt”, không chỉ một số',
        'Mức thứ nhất là có hơn các đối chứng hợp lý trên cùng mẫu hay không. Hiện B tốt hơn GFS và MOS dài về điểm RMSE ở ba hạn trong giai đoạn đã xem; BSS50 cũng dương. Mức thứ hai là cải thiện có ổn định qua năm, mùa, trạm và mưa lớn hay không, với khoảng tin cậy phù hợp các đợt thời tiết phụ thuộc. Phần này chưa được hoàn tất cho B so các đối chứng ở protocol mới. Mức thứ ba là đủ cho một quyết định thực tế: cần biết chấp nhận bỏ sót, báo nhầm và độ trễ thế nào. Chưa có ngưỡng người sử dụng và kiểm chứng tương lai đủ dài nên chưa được tuyên bố đạt mức ba.',
        'Hiện có kết quả nghiên cứu đáng theo dõi; chưa có bằng chứng để chứng nhận vận hành.',
        headers=['Mốc so sánh', 'Hiện có bằng chứng gì?', 'Đánh giá hiện tại'],
        rows=[['1. Hơn đối chứng', 'RMSE B < GFS/MOS dài; BSS50 > 0', '**Đạt ở mức điểm số**'],
              ['2. Cải thiện ổn định', 'Cần kiểm tra nhiều giai đoạn và độ chắc chắn', '**Chưa đủ**'],
              ['3. Đủ dùng thực tế', 'Cần yêu cầu bỏ sót/báo nhầm và độ trễ thật', '**Chưa chứng minh**']],
        widths=[2.9,5.8,3.4], row_h=1.05, size=19.5, refs=['E4'])
    add('image', 'Đổi sang L2: bớt thiếu mưa lớn nhưng thừa ngày khô',
        'Hình là số liệu thật của đầu mean ngày 1 trong hồi cứu modern, so B và D cùng cửa sổ bốn năm. Bias ở các trường hợp thực tế từ 50 mm trở lên chuyển từ khoảng −46,41 lên −34,43 mm: vẫn thiếu nhưng bớt thiếu. Ở các trường hợp thực tế dưới 1 mm, bias tăng từ khoảng +1,88 lên +2,63 mm: báo thừa nhiều hơn. RMSE chung ngày 1 của D cũng cao hơn B. Đây là phân tích có điều kiện theo nhãn quan sát sau sự kiện, không phải quy tắc chọn mô hình trước khi biết trời mưa. Không có khoảng tin cậy cho từng bias có điều kiện trong hình.',
        'Không có loss tốt nhất mọi mặt; cần giữ mục tiêu chính và kiểm tra đánh đổi.', image='loss_tradeoff.png', scope=scope)
    old_rows=[]
    for model,label in [('GFS','GFS'),('LGB_N3','LightGBM N3'),('GRU_N3','GRU N3')]:
        _,shown=e.value('final','point_metrics',dict(evaluation_set='test2025_legacy',horizon=1,model=model,functional='mean'),'macro_rmse',2)
        old_rows.append([label,shown])
    add('table', 'GRU có hữu ích không? Chỉ so khi cùng protocol',
        'Ba số trong bảng đều thuộc kiểm định 2025 của protocol cũ, cùng trạm, mẫu, đầu mean và hạn ngày 1. GRU N3 có RMSE thấp hơn LightGBM N3 và GFS về điểm số, cho thấy đây là một ứng viên đáng kiểm tra. Tuy nhiên, không lấy 24,67 mm của GRU năm 2025 so 15,68 mm của B năm 2026 để kết luận B hơn GRU: thời tiết, nguồn và cách chia năm đã khác. Bảng cũng không tự chứng minh chênh lệch có ý nghĩa thống kê. Nếu cần xếp hạng theo protocol mới, phải huấn luyện GRU với cùng cửa sổ và ngân sách rồi kiểm tra cùng mẫu.',
        'Chưa có so sánh GRU bốn năm với LightGBM B. Không xếp hạng bằng hai năm khác nhau.',
        headers=['Mô hình', 'RMSE ngày 1 (mm)'], rows=old_rows, widths=[6.1,6.0], row_h=.9, size=23,
        scope='Kiểm định 2025 legacy • protocol cũ • 57 trạm • thấp hơn tốt hơn')
    feature=copy.deepcopy(old_manifest[20]); feature.pop('number');feature.pop('main_count');feature['minutes']=0
    feature['title']='Bổ sung đặc trưng: đã có cải thiện nào đáng tin?'
    items.append(feature)
    add('quality', 'Cần làm gì để tiến từ kết quả nghiên cứu đến tin cậy?',
        'Giữ mô hình đã chọn bằng phần học, không tiếp tục lựa chọn bằng năm 2026 đã xem rồi gọi lại là test kín. Thu và lưu đầu vào, dự báo trước giờ phát để kiểm tra có thực sự dùng được GFS và mưa trạm đúng hạn. Tích lũy nhiều đợt mưa chưa xảy ra rồi đánh giá cả lượng và xác suất, theo mùa và từng trạm. Nếu muốn nói mô hình chung tốt hơn mô hình riêng hoặc giờ 19 tốt hơn giờ khác, cần thí nghiệm riêng có kiểm soát. Nếu muốn dùng cảnh báo, phải thống nhất chi phí bỏ sót và báo nhầm với người dùng trước khi chọn điểm vận hành.',
        'Bước quan trọng kế tiếp là kiểm chứng đúng điều kiện sử dụng, không thêm mô hình cho đủ tên.',
        levels=[('Thực tế trước giờ phát', 'Ghi thời điểm nhận nguồn và dự báo; không chỉ hồi phát.', 'pending'),
                ('Tương lai chưa xem', 'Nhiều mùa/đợt mưa; lượng, xác suất, từng trạm.', 'pending'),
                ('Đối chứng cần thêm', 'Chung/riêng, giờ phát và nhu cầu sử dụng nếu cần.', 'pending')])
    add('cards', 'Có thể báo cáo điều gì một cách trung thực?',
        'Nhóm đã chuyển sang nhãn mưa đo tại trạm, ghép bản dự báo khí tượng trước kỳ đích, xây dựng kiểm tra dữ liệu và thí nghiệm có đối chứng. Học máy tạo thêm giá trị ở mức điểm RMSE trên giai đoạn hồi cứu mới, và một số lợi ích của khí tượng thô có bằng chứng trong kiểm định cũ. Những phần chưa chắc cũng là kết quả nghiên cứu: thêm biến không tự động tốt hơn, thêm năm chưa đủ bằng chứng, đổi loss tạo đánh đổi. Vẫn phải cải thiện bỏ sót mưa lớn, báo nhầm, kiểm chứng nguồn và kiểm định tương lai. Không tuyên bố vượt các paper khác chỉ từ RMSE hay POD khác điều kiện.',
        'Có đóng góp nghiên cứu và tín hiệu cải thiện; chưa phải hệ thống cảnh báo đã được chứng nhận.',
        cards=[('Đã làm được', 'Nhãn Vrain tại trạm\nĐầu vào GFS phù hợp kỳ\nĐối chứng và kiểm tra'),
               ('Đã học được', 'Điểm lỗi có giảm\nThêm biến có giới hạn\nLoss tạo đánh đổi'),
               ('Còn phải chứng minh', 'Mưa lớn và báo nhầm\nCải thiện ổn định\nKhả dụng trước giờ phát')])

    main_count=len(items)
    appendices=copy.deepcopy(old_manifest[31:])
    # Avoid copying an outdated navigation-only appendix.
    appendices[0]['cards']=[('Tra theo câu hỏi','Thuật ngữ, biến\nKiến trúc và tuning\nBảng số đầy đủ'),
                            ('Tra theo thời kỳ','2025: protocol cũ\n2026: A–D mới\nKhông trộn điểm'),
                            ('Tra theo độ tin cậy','CI và kiểm tra\nNguồn tài liệu\nGiới hạn kết luận')]
    appendices[0]['notes']='Phụ lục giữ các bảng và mô tả kỹ thuật từ bản tổng hợp trước. Chỉ mở khi người nghe cần kiểm tra một biến, một cấu hình hoặc một số cụ thể. Các bảng luôn giữ nhãn thời kỳ và protocol riêng; không dùng để so trực tiếp các năm khác nhau. Các slide cuối bổ sung bảng A–D, bảng metric và nguồn chính thức cho loss, BSS và tiêu chí sử dụng.'
    appendices.append(copy.deepcopy(old_manifest[22]))
    appendices.append(dict(kind='table',title='Bảng tra tám chỉ số và mốc đọc kết quả',section='PHỤ LỤC · CHỈ SỐ',
      headers=['Chỉ số','Câu hỏi dễ hiểu','Chiều tốt / mốc đọc'],
      rows=[['RMSE','Có nhiều lần sai rất xa không?','Thấp hơn đối chứng'],
            ['MAE','Trung bình lệch tuyệt đối bao nhiêu mm?','Thấp hơn đối chứng'],
            ['Bias','Thường dự báo thừa hay thiếu?','Gần 0; xem riêng mưa lớn'],
            ['BS','Xác suất lệch so sự kiện 0/1 ra sao?','Nhỏ hơn'],
            ['BSS','Có hơn xác suất khí hậu tham chiếu?','>0 là hơn tham chiếu'],
            ['POD','Bắt được bao nhiêu sự kiện thật?','Cao hơn; đọc cùng FAR'],
            ['FAR','Trong lần báo có, bao nhiêu là nhầm?','Thấp hơn; đọc cùng POD'],
            ['CSI','Cân bằng trúng, bỏ sót và báo nhầm?','Cao hơn; cùng ngưỡng']],
      widths=[1.5,6.5,4.1],row_h=.46,size=17,
      takeaway='Không có ngưỡng POD 0,4 hoặc RMSE cố định để tự chứng nhận đạt.',refs=['E3','E4'],
      notes='Các chỉ số lượng mưa đánh giá bằng mm; các chỉ số sự kiện phụ thuộc ngưỡng mm, kỳ tích lũy, cutoff và tỷ lệ xuất hiện. FAR ở dự án là false alarm ratio F chia H cộng F, không phải false alarm rate F chia F cộng TN. BSS so với tham chiếu xác định rõ, không phải phần trăm dự đoán đúng. Khi so kết quả giữa paper, phải khớp đối tượng, kỳ đo, ngưỡng và cách tổng hợp; nếu không thì chỉ so phương pháp và giới hạn, không xếp hạng.'))
    appendices.append(dict(kind='table', title='Nguồn bổ sung cho mô hình, loss và mốc đánh giá',section='PHỤ LỤC · NGUỒN',
      headers=['Nguồn','Dùng để giải thích'],rows=[[REFS[k]['short'],REFS[k]['title']] for k in ('E1','E2','E3','E4','E5')],
      widths=[4,8.1],row_h=.65,size=18.5,refs=['E1','E2','E3','E4','E5'],
      takeaway='Đường dẫn đầy đủ có trong Notes và NGUON_TAI_LIEU.md.',
      notes='Đã đối chiếu tài liệu chính thức LightGBM về objective L2, Tweedie log-link và tweedie_variance_power. Tài liệu scikit-learn giải thích miền của Tweedie với 1 nhỏ hơn p nhỏ hơn 2. Tài liệu ECMWF giải thích Brier score và skill score, cùng vai trò chi phí và lợi ích trong quyết định dùng dự báo. Các nguồn này hỗ trợ cách diễn giải, không thay cho thí nghiệm tại Đà Nẵng và không đặt một ngưỡng đủ tốt chung cho dự án.'))
    items.extend(appendices)
    for i,item in enumerate(items):
        item.update(number=i+1,main_count=main_count,main=i<main_count,minutes=28/main_count if i<main_count else 0)
        item['notes']=readable(item['notes'])
        if not item['main']:item['section']='PHỤ LỤC · '+str(i+1-main_count)
    return items,derived


def handout(items):
    doc=Document()
    normal=doc.styles['Normal'];normal.font.name='Aptos';normal.font.size=Pt(11)
    doc.add_heading('Dự báo mưa ngắn hạn — giải thích từ đầu',0)
    doc.add_paragraph('Dành cho người mới • 18/11/2026 • khoảng 28 phút + phụ lục')
    intro='Đọc các slide chính theo thứ tự. Con số màu đậm là điểm cần giải thích, không phải chứng nhận đạt. Ví dụ giả định được ghi riêng; các kết quả thật giữ đúng năm, nguồn và protocol.'
    doc.add_paragraph(intro)
    md=['# Dự báo mưa ngắn hạn — giải thích từ đầu','',intro,'']
    for item in items:
        title=f"{item['number']:02d}. {readable(item['title']).replace(chr(10),' ')}"
        doc.add_heading(title,1);md.extend(['## '+title,''])
        if item.get('scope'):doc.add_paragraph(item['scope']);md.extend([item['scope'],''])
        if item['kind']=='table':
            table=doc.add_table(rows=1,cols=len(item['headers']));table.style='Light Shading Accent 1'
            for c,v in zip(table.rows[0].cells,item['headers']):c.text=readable(v)
            for row in item['rows']:
                for c,v in zip(table.add_row().cells,row):
                    c.text=readable(v).replace('**','')
                    if '**' in str(v):
                        for r in c.paragraphs[0].runs:r.bold=True
            md.extend(['| '+' | '.join(item['headers'])+' |','| '+' | '.join(['---']*len(item['headers']))+' |'])
            md.extend('| '+' | '.join(str(x).replace('\n',' / ') for x in row)+' |' for row in item['rows']);md.append('')
        doc.add_paragraph(item['notes']);doc.add_paragraph('Ý cần nhớ: '+item['takeaway'])
        md.extend([item['notes'],'','**Ý cần nhớ:** '+item['takeaway'],''])
        if item.get('refs'):
            links='; '.join('['+REFS[k]['short']+']('+REFS[k]['url']+')' for k in item['refs'])
            md.extend(['Nguồn: '+links,''])
            for k in item['refs']:doc.add_paragraph('['+k+'] '+REFS[k]['short']+' — '+REFS[k]['url'])
    doc.save(PUBLIC/'GIAI_THICH_TU_DAU.docx')
    (PUBLIC/'GIAI_THICH_TU_DAU.md').write_text('\n'.join(md).rstrip()+'\n',encoding='utf-8',newline='\n')
    sources=['# Nguồn phương pháp và cách sử dụng','','Các bảng số lấy từ CSV/protocol đã khóa trong evidence_inputs.json. Bản này chỉ trình bày, không huấn luyện hoặc chấm lại.','']
    for k,r in REFS.items():
        sources.extend(['## ['+k+'] '+r['short'],'','['+r['title']+']('+r['url']+')','',r['status'],'',r.get('verified','Đã đối chiếu tài liệu chính thức công khai.'),'',r.get('use','Chỉ hỗ trợ giải thích phương pháp; không chứng nhận kết quả dự án.'),''])
    (PUBLIC/'NGUON_TAI_LIEU.md').write_text('\n'.join(sources),encoding='utf-8',newline='\n')


def main():
    PUBLIC.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    # All old public report files and the user's edited slides are immutable inputs.
    protected_path=PRIVATE/'protected_before.json'
    if not protected_path.exists():
        paths=list(OLD.rglob('*'))
        prior=ROOT/'data/operational/short_range_comprehensive_2026_11_18/protected_before.json'
        protected=json.loads(prior.read_text(encoding='utf-8'))
        protected.update({p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_file() and not p.name.startswith('~$')})
        write_json(protected_path,protected)
    e=Evidence();items,derived=build_items(e)
    deck=BeginnerDeck()
    for item in items:deck.render(item)
    deck.p.save(PUBLIC/PPTX)
    handout(items)
    # Inherited appendix data bindings remain auditable and source hashes stay fixed.
    inherited=json.loads((OLD/'numeric_bindings.json').read_text(encoding='utf-8'))
    inputs=json.loads((OLD/'evidence_inputs.json').read_text(encoding='utf-8'))['files']
    inputs.update(e.inputs)
    write_json(PUBLIC/'slide_manifest.json',items)
    write_json(PUBLIC/'numeric_bindings.json',inherited+e.bindings)
    write_json(PUBLIC/'derived_bindings.json',derived)
    write_json(PUBLIC/'evidence_inputs.json',dict(files=inputs,models_refit=False,metrics_rescored=False))
    main_count=sum(x['main'] for x in items)
    readme=f'''# Báo cáo ngắn hạn — bản giải thích từ đầu

Mở **[{PPTX}]({PPTX})** để trình bày. Có **{main_count} slide chính (~28 phút)** và **{len(items)-main_count} phụ lục**. Mỗi slide có Notes; [Word](GIAI_THICH_TU_DAU.docx) và [bản đọc](GIAI_THICH_TU_DAU.md) diễn giải bằng lời.

Bản này làm rõ một mẫu dữ liệu, cách LightGBM/GRU học, chia năm, chọn tham số, Tweedie/L2, rồi mới đọc từng kết quả. Ví dụ giả định luôn được đánh dấu. Đếm mưa lớn ở luồng chính là **micro**, các bảng chi tiết có **macro**; hai cách không trộn.

## Mốc đánh giá đủ tốt

- **Hơn đối chứng:** B giảm điểm RMSE so GFS và MOS dài trên ba hạn của hồi cứu2026 modern. Ngày1 giảm khoảng23,3% so GFS; không phải độ chính xác76,7%.
- **Cải thiện ổn định:** chưa đủ bằng chứng trong protocol mới để khẳng định B hơn đối chứng ổn định qua các thời kỳ; các phép suy luận A–D không thay cho B–GFS/MOS.
- **Đủ dùng thực tế:** chưa chứng minh. Còn bỏ sót và báo nhầm mưa lớn; cần yêu cầu sử dụng, nguồn đúng hạn và kiểm định tương lai đủ dài. Không có mốc POD0,4 hoặc RMSE cố định để tự gọi đạt.

Mô hình chung và giờ phát19h là lựa chọn thiết kế chưa được so với mô hình riêng hoặc giờ khác. Tweedie/L2 là loss đầu mean; thay loss không thay các đầu xác suất dùng chung theo cửa sổ.

Giữ riêng kiểm định2025 protocol cũ và hồi cứu2026 protocol mới; không xếp hạng bằng hai năm khác nhau. Bản cũ tại ../short_range_comprehensive_2026_11_18/ giữ nguyên. Không có huấn luyện hoặc chấm mô hình mới.

## Gửi thành viên

Gửi PPTX và Word; gói nội bộ gồm PDF có tại `data/operational/{NAME}/PBL6_BAO_CAO_DE_HIEU.zip`. Gói báo cáo này không chứa dữ liệu train. Nguồn và giới hạn truy cập: [NGUON_TAI_LIEU.md](NGUON_TAI_LIEU.md). Bằng chứng số và kiểm tra nằm trong JSON cùng thư mục.
'''
    (PUBLIC/'README.md').write_text(readme,encoding='utf-8',newline='\n')
    print(json.dumps(dict(slides=len(items),main_slides=main_count,talk_minutes=28,bindings=len(inherited+e.bindings),derived=len(derived)),ensure_ascii=False))


if __name__=='__main__':main()
