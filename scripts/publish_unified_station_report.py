"""Merge the detailed PBL6 report, shared-forecast results, and expansion study."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
import re
import sys
from urllib.parse import urljoin

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.publish_station_nowcast import insert_caption, insert_table


DOCUMENTS = ROOT / "data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24"
TEMPLATE = DOCUMENTS / "PBL6_BAO_CAO_CUOI_KY_HAI_NHANH.docx"
OUTPUT = DOCUMENTS / "PBL6_BAO_CAO_CUOI_KY_RA_SOAT.docx"
PUBLIC = ROOT / "reports/station_forecast_unified_2026_11_24"
REVIEW = ROOT / "reports/station_forecast_reviewed_2026_11_24"
FIGURES = ROOT / "data/operational/station_map_unified_2026_11_24/qa"
REPO_REPORT = "https://github.com/nibsu05/PBL6/blob/research/tft-regional/reports/"
INLINE = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^\s)]+\))")


def plot_timeline(path):
    from matplotlib import pyplot as plt
    from matplotlib.ticker import FixedLocator

    fig, axes = plt.subplots(2, 1, figsize=(8, 2.65), layout="constrained")
    navy, cyan, light = "#183d50", "#4399a7", "#d6ecee"
    for i in range(6):
        axes[0].barh(0, 1, left=i, height=.50, color=cyan, edgecolor="white")
        axes[0].text(i + .5, 0, str(i + 1), color="white", ha="center", va="center", weight="bold")
    axes[0].set(xlim=(0, 6), ylim=(-.4, .4), title="Cực ngắn · từng giờ trong 6 giờ đầu")
    axes[0].xaxis.set_major_locator(FixedLocator(range(7)))
    for day in range(3):
        axes[1].barh(0, 24, left=day * 24, height=.50, color=light, edgecolor="white")
        axes[1].text(day * 24 + 13, 0, f"Ngày {day + 1}", color=navy, ha="center", va="center", weight="bold")
    axes[1].barh(0, 6, left=0, height=.50, color=cyan, edgecolor="white")
    axes[1].set(xlim=(0, 72), ylim=(-.4, .4), title="Ngắn hạn · ba tổng 24 giờ từ cùng mốc phát",
                xlabel="Số giờ tính từ mốc phát dự báo")
    axes[1].xaxis.set_major_locator(FixedLocator([0, 6, 24, 48, 72]))
    for axis in axes:
        axis.set_yticks([])
        axis.spines[["right", "top", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#90a8af")
        axis.title.set_color(navy)
    fig.savefig(path, dpi=210, facecolor="white")
    plt.close(fig)


def hyperlink(p, label, url):
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), p.part.relate_to(url, RT.HYPERLINK, is_external=True))
    run = OxmlElement("w:r")
    properties = OxmlElement("w:rPr")
    style = OxmlElement("w:rStyle")
    style.set(qn("w:val"), "Hyperlink")
    properties.append(style)
    run.append(properties)
    node = OxmlElement("w:t")
    node.text = label
    run.append(node)
    link.append(run)
    p._p.append(link)


def insert_run(p, line):
    for portion in INLINE.split(line):
        if portion.startswith("**"):
            p.add_run(portion[2:-2]).bold = True
        elif portion.startswith("`"):
            p.add_run(portion[1:-1])
        elif portion.startswith("[") and "](" in portion:
            label, url = portion[1:-1].split("](", 1)
            hyperlink(p, label, urljoin(REPO_REPORT + "station_forecast_reviewed_2026_11_24/", url))
        else:
            p.add_run(portion)


def paragraph(doc, anchor, text="", style=None):
    p = doc.add_paragraph(style=style)
    insert_run(p, text)
    anchor.addnext(p._p)
    return p


def caption(doc, anchor, kind, title):
    node = insert_caption(doc, anchor, kind, 1, title)
    p = Paragraph(node, doc)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = kind == "Table"
    p.paragraph_format.keep_together = True
    return node


def next_heading(doc, title):
    matches = [p for p in doc.paragraphs if p.text == title]
    if len(matches) != 1:
        raise ValueError(f"Expected one report heading: {title}")
    return matches[0]


def replace_section(doc, first, last):
    anchor = next_heading(doc, first)._p
    end = next_heading(doc, last)._p
    following = anchor.getnext()
    while following is not end:
        if following is None or following.tag == qn("w:sectPr"):
            raise ValueError(f"Invalid position of section {last}")
        node, following = following, following.getnext()
        node.getparent().remove(node)
    return anchor


def md_section(lines, heading):
    i = lines.index("### " + heading) + 1
    result = []
    for line in lines[i:]:
        if line.startswith(("## ", "### ")):
            break
        result.append(line)
    return result


def image(doc, anchor, path, text):
    if not path.is_file():
        return anchor
    p = paragraph(doc, anchor)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Cm(15.4))
    return caption(doc, p._p, "Figure", text)


def append_markdown(doc, anchor, lines, artwork):
    title = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("# "):
            continue
        match = re.fullmatch(r"#{2,4} (.+)", line)
        if match:
            anchor = paragraph(doc, anchor, match.group(1), "Heading 3")._p
            continue
        picture = re.fullmatch(r"<!-- figure:(\w+) -->", line)
        if picture:
            path, text = artwork[picture.group(1)]
            anchor = image(doc, anchor, path, text)
            continue
        if re.fullmatch(r"\*\*[^*]+\*\*", line):
            title = line[2:-2]
            continue
        if line.startswith("|"):
            rows = []
            while line.startswith("|"):
                cells = [c.strip() for c in line.strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append([(cell.strip("*"), cell.startswith("**") and cell.endswith("**")) for cell in cells])
                if i == len(lines) or not lines[i].strip().startswith("|"):
                    break
                line = lines[i].strip()
                i += 1
            anchor = caption(doc, anchor, "Table", title)
            anchor = insert_table(doc, anchor, rows)
            title = ""
            continue
        style = "List Bullet" if line.startswith("- ") else None
        anchor = paragraph(doc, anchor, line[2:] if style else line, style)._p
    return anchor


def rewrite(doc, prefix, text):
    candidates = [p for p in doc.paragraphs if p.text.startswith(prefix)]
    if len(candidates) != 1:
        raise ValueError(f"Expected one paragraph beginning with {prefix}")
    p = candidates[0]
    p.clear()
    insert_run(p, text)


def restore_section_break(doc):
    """Restore separate cover, indices, introduction, and Arabic body sections."""
    opening = next_heading(doc, "MỞ ĐẦU")
    chapter = next_heading(doc, "TỔNG QUAN ĐỀ TÀI")
    old_intro_end = chapter._p.getprevious()
    intro_end = old_intro_end.find("./w:pPr/w:sectPr", namespaces=old_intro_end.nsmap)
    if len(doc.sections) != 3 or intro_end is None:
        raise ValueError("Use the full two-branch report with its original pagination")
    front = deepcopy(intro_end)
    marker = doc.add_paragraph()
    opening._p.addprevious(marker._p)
    marker._p.get_or_add_pPr().append(front)
    marker.paragraph_format.space_before = Pt(0)
    marker.paragraph_format.space_after = Pt(0)
    marker.paragraph_format.line_spacing = Pt(1)
    roman = intro_end.find(qn("w:pgNumType"))
    roman.attrib.pop(qn("w:start"), None)
    for attr in ("footerReference", "headerReference"):
        for element in intro_end.findall(qn("w:" + attr)):
            intro_end.remove(element)
    for p in doc.paragraphs:
        if p.style.name == "Heading 1" and p._p is not chapter._p:
            p.paragraph_format.page_break_before = True


def layout_tables(doc):
    for t in doc.tables:
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = False
        n = len(t.columns)
        width = 15.6
        preferred = t._tbl.tblPr.find(qn("w:tblW"))
        preferred.set(qn("w:type"), "dxa")
        preferred.set(qn("w:w"), str(Cm(width).twips))
        sizes = []
        for column in t.columns:
            samples = [len(cell.text) for cell in column.cells]
            sizes.append(min(85, max(17, max(samples))))
        if n >= 6:
            widths = [3.55] + [(width - 3.55) / (n - 1)] * (n - 1)
        else:
            minimum = 1.65
            widths = [minimum + (width - n * minimum) * length / sum(sizes) for length in sizes]
        for col, cm in zip(t.columns, widths):
            col.width = Cm(cm)
            for cell in col.cells:
                cell.width = Cm(cm)
        for i, row in enumerate(t.rows):
            props = row._tr.get_or_add_trPr()
            if props.find(qn("w:cantSplit")) is None:
                props.append(OxmlElement("w:cantSplit"))
            if i == 0 and props.find(qn("w:tblHeader")) is None:
                props.append(OxmlElement("w:tblHeader"))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_before = Pt(2)
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.line_spacing = 1.12
                    p.paragraph_format.first_line_indent = Pt(0)
                    p.paragraph_format.keep_with_next = i == 0
                    p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if re.fullmatch(r"[\d., %−+–>-]+", p.text)
                                   else WD_ALIGN_PARAGRAPH.LEFT)
                    for run in p.runs:
                        run.font.name = "Times New Roman"
                        run.font.size = Pt(11)
                        if i == 0:
                            run.bold = True


def layout_figures_and_captions(doc):
    limit = Cm(15.6)
    for shape in doc.inline_shapes:
        if shape.width > limit:
            shape.height = int(shape.height * limit / shape.width)
            shape.width = limit
    for p in doc.paragraphs:
        if p.style.name != "Caption":
            continue
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_together = True
        p.paragraph_format.keep_with_next = p.text.startswith("Bảng ")
        previous = p._p.getprevious()
        if p.text.startswith("Hình ") and previous is not None and previous.xpath(".//w:drawing"):
            figure = Paragraph(previous, doc)
            figure.alignment = WD_ALIGN_PARAGRAPH.CENTER
            figure.paragraph_format.keep_with_next = True


def bibliography(doc):
    for p in doc.paragraphs:
        if re.match(r"^\[\d+\]", p.text) and "https://" in p.text:
            name, url = p.text.split("https://", 1)
            p.clear()
            p.add_run(name.rstrip() + " ")
            hyperlink(p, "Nguồn tham khảo", "https://" + url.strip())


def report(template, markdown, expansion, output, figures):
    doc = Document(template)
    restore_section_break(doc)
    full = markdown.read_text(encoding="utf-8").splitlines()
    figures.mkdir(parents=True, exist_ok=True)
    plot_timeline(figures / "forecast-periods.png")
    artwork = {
        "timeline": (figures / "forecast-periods.png", "Sáu giờ đầu nằm trong Ngày 1"),
        "map_hour": (figures / "unified-hour.png", "Bản đồ xã, phường tại Giờ 1"),
        "map_day": (figures / "unified-day.png", "Cùng bản đồ khi chuyển đến Ngày 1"),
    }
    rewrite(doc, "Báo cáo trình bày hai bài toán tại trạm", "Báo cáo trình bày hai bài toán tại trạm, các bước kiểm tra "
            "dữ liệu, chọn và khóa mô hình, kết quả từng nhánh và phép đối chiếu trên phần giao. "
            "Bản đồ dùng chung chín kỳ cho 57 trạm lõi. Phần cuối phân tích tính khả thi khi mở rộng từ Đà Nẵng sang Huế.")
    rewrite(doc, "Kho quan trắc có 86 vị trí", "Danh mục Vrain có 86 vị trí. Nhánh giờ đã kiểm định trên 79 trạm. "
            "Nhánh ngày đã kiểm định trên 57 trạm, đều thuộc tập giờ. Bản đồ mặc định dùng 57 trạm chung và "
            "báo số trạm có số riêng cho từng kỳ dự báo.")
    rewrite(doc, "Sản phẩm của nhánh gồm bộ dữ liệu", "Sản phẩm gồm hai bộ dữ liệu đã ghép theo trạm và thời gian, "
            "mô hình và đối chứng đã khóa, bảng kết quả và một bản đồ có thể chuyển giữa chín kỳ. Màu khu vực "
            "lấy lượng cao nhất tại trạm thuộc xã, phường. Sau đăng nhập có số đo, sai lệch và CSV.")
    rewrite(doc, "Chương trình ngắn hạn chạy bằng Python", "Hai nhánh dùng Python để tạo đầu ra theo trạm, "
            "thời điểm phát và khoảng hiệu lực. Backend ghép hai sản phẩm theo cùng thời điểm phát. "
            "Trình duyệt chọn kỳ, nguồn dự báo và phạm vi trạm từ đầu ra đã tính.")
    rewrite(doc, "Đầu lượng mưa của bản đồ dùng trung bình", "Nhánh giờ của bản đồ dùng LightGBM R, có lớp "
            "Bi-LSTM R và mốc giữ mưa để đối chiếu. Nhánh ngày dùng LightGBM B, GFS và xác suất đạt 50 mm "
            "trong 24 giờ. Mỗi kỳ có đơn vị và số trạm có số riêng.")
    rewrite(doc, "Mô hình và dữ liệu thí nghiệm nằm ở phía xử lý", "Mô hình nằm ở phía xử lý. "
            "Giao diện đọc các dự báo đã lưu. Các thử nghiệm điều chỉnh lượng và tính nhất quán được đánh giá "
            "riêng trước khi cân nhắc áp dụng.")
    rewrite(doc, "Sau khi đăng ký lịch, nhóm khởi chạy thử", "Tác vụ thử nhận diện tình huống nguồn hoặc nhãn "
            "chưa đủ. Bản đồ có chín lượt lịch sử ghép được cả hai nhánh. Xác nhận vận hành cần một bản dự báo "
            "ghi trước giờ phát với dữ liệu thực, rồi đối chiếu sau kỳ.")

    theory = next_heading(doc, "Ý tưởng")._p
    append_markdown(doc, theory, md_section(full, "Giờ phát và độ dài kỳ đo"), artwork)
    hour = replace_section(doc, "Dự báo cực ngắn", "CHƯƠNG TRÌNH VÀ KẾT QUẢ")
    hour = paragraph(doc, hour, "Mỗi mẫu là một trạm và một giờ phát. Đầu vào gồm 24 khoảng giờ đã qua, "
                     "đầu ra là sáu lượng mưa tương lai tại chính trạm. Việc tạo đầu vào kiểm tra cửa sổ quá khứ. "
                     "Điều kiện đủ sáu nhãn được áp dụng khi học hoặc chấm.")._p
    append_markdown(doc, hour, md_section(full, "Huấn luyện nhánh cực ngắn"), artwork)

    ui = replace_section(doc, "Giao diện chính của chương trình", "Kết quả thực thi của chương trình")
    ui = append_markdown(doc, ui, md_section(full, "Bản đồ thống nhất theo chín kỳ"), artwork)
    image(doc, ui, DOCUMENTS / "web_v2/theo_doi_nguon.png",
          "Trang Theo dõi nguồn và nhật ký của lần thử ghi dự báo")
    old_ui = next(p for p in doc.paragraphs if p.text.startswith("Web có chế độ phát lại cực ngắn bằng"))
    old_figure = old_ui._p.getnext()
    old_caption = old_figure.getnext()
    if not old_figure.xpath(".//w:drawing") or Paragraph(old_caption, doc).style.name != "Caption":
        raise ValueError("Unexpected placement of the old hourly screenshot")
    anchor = old_ui._p.getprevious()
    for node in (old_ui._p, old_figure, old_caption):
        node.getparent().remove(node)
    for title in ("So sánh trên đúng 57 trạm và mốc 19h", "Đối chiếu tổng sáu giờ với Ngày 1",
                  "Nguồn dữ liệu và vận hành kiểm tra"):
        anchor = paragraph(doc, anchor, title, "Heading 3")._p
        anchor = append_markdown(doc, anchor, md_section(full, title), artwork)

    refs = next_heading(doc, "TÀI LIỆU THAM KHẢO")
    anchor = paragraph(doc, refs._p.getprevious(), "Nghiên cứu mở rộng sang Huế", "Heading 2")._p
    append_markdown(doc, anchor, expansion.read_text(encoding="utf-8").splitlines(), artwork)
    bibliography(doc)
    layout_tables(doc)
    layout_figures_and_captions(doc)
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(13)
    normal.paragraph_format.line_spacing = 1.3
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    normal.paragraph_format.widow_control = True

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(f"Saved {len(doc.tables)} tables, {len(doc.inline_shapes)} figures and {len(doc.sections)} sections to {output}",
          flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--markdown", type=Path, default=PUBLIC / "BAO_CAO_CHI_TIET.md")
    parser.add_argument("--expansion", type=Path, default=REVIEW / "DE_XUAT_MO_RONG.md")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures-dir", type=Path, default=FIGURES)
    args = parser.parse_args()
    report(args.template, args.markdown, args.expansion, args.output, args.figures_dir)


if __name__ == "__main__":
    main()
