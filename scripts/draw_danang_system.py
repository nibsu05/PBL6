"""Draw the Da Nang report diagrams at a resolution suitable for Word."""

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

INK = "#153047"
TEAL = "#187c81"
PALE = "#e8f3f3"
BLUE = "#eaf0f6"
GRAY = "#f0f2f4"
WARN = "#fff1dc"


class Diagram:
    def __init__(self, height, extent=(12, 7)):
        self.figure = Figure(figsize=(8.2, height), facecolor="white")
        FigureCanvasAgg(self.figure)
        self.axes = self.figure.add_axes([.008, .014, .984, .972])
        self.axes.set(xlim=(0, extent[0]), ylim=(0, extent[1]))
        self.axes.axis("off")

    def label(self, x, y, text, size=14, weight="normal", color=INK, align="center"):
        self.axes.text(x, y, text, ha=align, va="center", size=size, weight=weight,
                       family="DejaVu Sans", color=color, linespacing=1.25)

    def box(self, x, y, w, h, text, fill=PALE, size=14):
        self.axes.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.024,rounding_size=0.12",
                                          edgecolor="#9eb4bf", facecolor=fill, linewidth=1.2))
        self.label(x + w / 2, y + h / 2, text, size)

    def arrow(self, start, end):
        self.axes.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", color=TEAL,
                                           linewidth=1.5, shrinkA=2, shrinkB=2, mutation_scale=14))

    def line(self, x, y):
        self.axes.plot(x, y, color=TEAL, lw=1.5)

    def save(self, path):
        self.figure.savefig(path, dpi=230, facecolor="white")


def system_layers():
    d = Diagram(4.65)
    d.label(.16, 6.66, "NGHIÊN CỨU VÀ KIỂM ĐỊNH", 13, "bold", TEAL, "left")
    d.box(.16, 5.17, 2.56, 1.16, "Vrain lưu trữ\nERA5 và GFS", BLUE)
    d.box(3.03, 5.17, 2.64, 1.16, "Kiểm tra giờ\nGhép, chia mẫu", BLUE, 13)
    d.box(6.0, 5.17, 2.64, 1.16, "Huấn luyện\nChấm đối chứng", BLUE)
    d.box(9.00, 5.17, 2.84, 1.16, "Mô hình khóa\nvà bản phát lại", BLUE)
    for x, end in [(2.72, 3.03), (5.67, 6.0), (8.64, 9.00)]:
        d.arrow((x, 5.75), (end, 5.75))
    d.label(.16, 4.52, "VẬN HÀNH HẰNG NGÀY", 13, "bold", TEAL, "left")
    d.box(.16, 2.93, 2.56, 1.16, "Vrain theo giờ\nGFS theo chu kỳ")
    d.box(3.03, 2.93, 2.64, 1.16, "Tác vụ 18h40\nKiểm tra nguồn")
    d.box(6.0, 2.93, 2.64, 1.16, "Dự báo ba kỳ\nSổ lần phát")
    d.box(9.00, 2.93, 2.84, 1.16, "API bản đồ\nChín kỳ tại trạm")
    for x, end in [(2.72, 3.03), (5.67, 6.0), (8.64, 9.00)]:
        d.arrow((x, 3.51), (end, 3.51))
    d.arrow((10.42, 5.17), (10.42, 4.09))
    d.line([9.0, 7.33], [4.86, 4.86])
    d.line([9.0, 9.0], [5.17, 4.86])
    d.arrow((7.33, 4.86), (7.33, 4.09))
    d.box(.29, .73, 3.18, 1.03, "Khách\nBản đồ dự báo", GRAY, 13)
    d.box(4.11, .73, 3.48, 1.03, "Sau đăng nhập\nThực đo, sai lệch, CSV", GRAY, 13)
    d.box(8.22, .73, 3.62, 1.03, "Quản trị sau đăng nhập\nNhật ký và lỗi nguồn", GRAY, 13)
    d.line([1.88, 10.42], [2.33, 2.33])
    d.line([10.42, 10.42], [2.33, 2.93])
    for x in (1.88, 5.85, 10.03):
        d.arrow((x, 2.33), (x, 1.76))
    return d


def rainfall_inputs():
    d = Diagram(3.7, (12, 6))
    d.label(.18, 5.66, "CỰC NGẮN · TẠI MỘT TRẠM", 13, "bold", TEAL, "left")
    d.box(.18, 3.74, 3.42, 1.50, "24 giờ đã qua\nMưa trạm và tháng\nERA5 khi thử hồi cứu", BLUE)
    d.box(4.29, 3.74, 3.43, 1.50, "Ghép theo giờ kết thúc\nĐủ lịch sử để dự báo\nĐủ nhãn để chấm", BLUE, 13)
    d.box(8.40, 3.74, 3.42, 1.50, "6 lượng mưa\nMỗi lượng trong 1 giờ\nTừ +1h đến +6h", BLUE)
    d.label(.18, 3.13, "NGẮN HẠN · CÙNG TRẠM, PHÁT LÚC 19H", 13, "bold", TEAL, "left")
    d.box(.18, 1.01, 3.42, 1.66, "Vrain đến 18h\nGFS 00 UTC\nTọa độ và địa hình")
    d.box(4.29, 1.01, 3.43, 1.66, "Ghép đúng trạm\nGFS theo từng kỳ đích\nCùng mốc phát 19h", PALE, 13)
    d.box(8.40, 1.01, 3.42, 1.66, "3 tổng mưa 24h\n0–24h, 24–48h, 48–72h\nvà xác suất theo ngưỡng", PALE, 13)
    for y in (4.49, 1.84):
        d.arrow((3.60, y), (4.29, y))
        d.arrow((7.72, y), (8.40, y))
    return d


def hourly_models():
    d = Diagram(4.45)
    d.box(.16, 2.96, 2.70, 1.40, "R · 24 giờ đã qua\nMưa, chênh, tháng", GRAY, 13)
    d.box(3.38, 5.02, 4.38, 1.45, "Bi-LSTM\n64 nút mỗi chiều\nĐọc cùng lịch sử theo 2 chiều", BLUE, 13)
    d.box(3.38, 2.94, 4.38, 1.45, "GRU trong phép thử bổ sung\nMột chiều, 110 nút\nCùng mã trạm và đầu ra", BLUE, 13)
    d.box(3.38, .86, 4.38, 1.45, "LightGBM R\n24 độ trễ + tổng và cực đại\n6 bộ cây, mỗi hạn một bộ", PALE, 13)
    d.box(8.38, 2.96, 3.46, 1.40, "6 lượng mưa\nTừng giờ tại trạm", GRAY)
    for y in (5.75, 3.66, 1.58):
        d.arrow((2.86, 3.66), (3.38, y))
        d.arrow((7.76, y), (8.38, 3.66))
    d.label(6, .30, "Chọn epoch mạng theo RMSE 2023 · Chấm cả sáu giờ trên cùng mẫu 2025", 11.5)
    return d


def daily_models():
    d = Diagram(4.8)
    d.box(.17, 4.91, 2.46, 1.43, "Mưa trạm\n7 kỳ đã qua\n× 1 giá trị", GRAY, 13)
    d.box(3.05, 4.91, 4.26, 1.43, "GRU 16 nút\nhoặc Bi-LSTM 9 nút mỗi chiều\nMã trạm 4 chiều", BLUE, 13)
    d.box(.17, 2.78, 2.46, 1.43, "Bối cảnh N3\n18 biến\ncho từng kỳ", GRAY, 13)
    d.box(3.05, 2.78, 4.26, 1.43, "Ghép bối cảnh với tóm tắt\nchuỗi mưa và mã trạm\n3 đầu dự báo, mỗi đầu 24 nút", BLUE, 13)
    d.box(7.79, 2.66, 4.03, 1.67, "Trung bình và trung vị\nP(mưa ≥1 mm)\nP(≥50 mm | ≥1 mm)", PALE, 13)
    d.arrow((2.63, 5.63), (3.05, 5.63))
    d.arrow((2.63, 3.50), (3.05, 3.50))
    d.arrow((5.18, 4.91), (5.18, 4.21))
    d.arrow((7.31, 3.50), (7.79, 3.50))
    d.box(.17, .68, 7.14, 1.26, "Nhánh cây LightGBM\nMột hàng 26 biến cho mỗi trạm, giờ phát và kỳ", PALE, 13)
    d.box(7.79, .68, 4.03, 1.26, "Các đầu riêng dùng bộ cây\nvà hiệu chỉnh xác suất", PALE, 13)
    d.arrow((7.31, 1.31), (7.79, 1.31))
    return d


def operations():
    d = Diagram(5.05)
    d.box(.15, 5.30, 2.85, 1.28, "18h40\nTác vụ Windows")
    d.box(3.38, 5.30, 4.80, 1.28, "Mưa đủ tới 18h? GFS đủ trường?\nKiểm giờ, giá trị và đơn vị", BLUE, 13)
    d.box(8.57, 5.30, 3.28, 1.28, "Thiếu hoặc trễ\nGhi lý do và báo admin", WARN, 13)
    d.arrow((3.00, 5.94), (3.38, 5.94))
    d.arrow((8.18, 5.94), (8.57, 5.94))
    d.box(3.38, 3.47, 4.80, 1.12, "Đủ nguồn · chạy LightGBM B\nGhi đầu vào và dự báo trước 19h", PALE, 13)
    d.arrow((5.78, 5.30), (5.78, 4.59))
    d.box(8.57, 3.31, 3.28, 1.45, "Web ghi đúng chế độ\nPhát lại khi chưa có\nlần phát trực tiếp", GRAY, 13)
    d.arrow((8.18, 4.03), (8.57, 4.03))
    d.arrow((10.21, 5.30), (10.21, 4.76))
    d.box(.15, 1.22, 2.85, 1.34, "20h05\nTác vụ đối chiếu", BLUE, 13)
    d.box(3.38, 1.22, 4.80, 1.34, "Đến hạn + đủ Vrain thực đo\nChấm đúng các cửa sổ 24h", BLUE, 13)
    d.box(8.57, 1.22, 3.28, 1.34, "Chờ bổ sung khi thiếu\nCập nhật nhật ký\nvà trang theo dõi", GRAY, 13)
    d.arrow((3.00, 1.89), (3.38, 1.89))
    d.arrow((8.18, 1.89), (8.57, 1.89))
    d.line([5.78, 5.78], [2.93, 3.47])
    d.arrow((5.78, 2.93), (5.78, 2.56))
    d.label(6, .45, "Luồng hiện hành cho nhánh ngày · Nhánh giờ đang có các bản phát lại", 11.5)
    return d


def storage_relations():
    d = Diagram(4.4)
    d.box(.36, 4.67, 4.64, 1.67, "TRẠM VÀ BÍ DANH\nMã chuẩn, ghép mã từng kênh\nTọa độ, cao độ, ranh giới", BLUE, 13)
    d.box(7.02, 4.67, 4.63, 1.67, "QUAN TRẮC MƯA\nMã trạm + giờ kết thúc + kênh\nLượng mm và cờ chất lượng", BLUE, 13)
    d.box(.36, 1.70, 4.64, 1.67, "LẦN PHÁT DỰ BÁO\nMốc phát + phiên bản\nChế độ, giờ ghi nhận, dấu tệp", PALE, 13)
    d.box(7.02, 1.70, 4.63, 1.67, "DỰ BÁO TẠI TRẠM\nTrạm + lần phát + kỳ + mô hình\nKhoảng hiệu lực, lượng, xác suất", PALE, 13)
    d.arrow((5.00, 5.50), (7.02, 5.50))
    d.label(6.01, 5.85, "Mã trạm", 11)
    d.arrow((5.00, 2.53), (7.02, 2.53))
    d.label(6.01, 2.88, "Giờ phát", 11)
    d.line([2.68, 2.68, 6.55], [4.67, 4.03, 4.03])
    d.line([6.55, 6.55], [4.03, 3.10])
    d.arrow((6.55, 3.10), (7.02, 3.10))
    d.arrow((8.15, 4.67), (8.15, 3.37))
    d.label(9.99, 4.01, "Cùng trạm, cùng kỳ", 11)
    d.label(6, .76, "Dữ liệu nghiệp vụ dạng Parquet/JSON · Tài khoản và thông báo dùng SQLite", 11.5)
    return d


def write_figures(folder):
    definitions = {
        "design_layers": (system_layers, "Kiến trúc hệ thống PBL6 tại Đà Nẵng và quyền xem"),
        "design_inputs": (rainfall_inputs, "Ghép dữ liệu và dựng nhãn cho hai nhánh tại trạm"),
        "design_hour": (hourly_models, "Cấu trúc Bi-LSTM, GRU và LightGBM trong dự báo 1–6 giờ"),
        "design_day": (daily_models, "Cấu trúc các mô hình cho ba tổng mưa 24 giờ"),
        "design_operations": (operations, "Luồng kiểm tra nguồn, phát dự báo và đối chiếu hằng ngày"),
        "design_storage": (storage_relations, "Khóa dữ liệu và quan hệ dùng khi ghép, phát và đối chiếu"),
    }
    folder.mkdir(parents=True, exist_ok=True)
    artwork = {}
    for key, (draw, title) in definitions.items():
        path = folder / f"{key}.png"
        draw().save(path)
        artwork[key] = path, title
    return artwork
