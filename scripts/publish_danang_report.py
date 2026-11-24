"""Add verified Da Nang architecture diagrams and model comparisons to the final report."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.draw_danang_system import write_figures
from scripts.publish_unified_station_report import (
    DOCUMENTS, OUTPUT as DETAILED_REPORT, append_markdown, layout_figures_and_captions,
    layout_tables, next_heading, paragraph, replace_section, rewrite,
)

PUBLIC = ROOT / "reports/danang_system_2026_11_24"
OUTPUT = DOCUMENTS / "PBL6_BAO_CAO_CUOI_KY_DA_NANG.docx"


def design_sections(path):
    sections = {}
    for block in path.read_text(encoding="utf-8").split("\n## ")[1:]:
        title, _, content = block.partition("\n")
        lines = []
        for line in content.splitlines():
            match = re.fullmatch(r"!\[[^]]+\]\(figures/(design_[a-z]+)\.png\)", line)
            lines.append(f"<!-- figure:{match.group(1)} -->" if match else line)
        sections[title] = lines
    return sections


def insert_before(doc, following_title, title, lines, artwork):
    following = next_heading(doc, following_title)
    anchor = paragraph(doc, following._p.getprevious(), title, "Heading 2")._p
    append_markdown(doc, anchor, lines, artwork)


def ensure_bullet_style(doc):
    """Word can omit unused built-in styles when it saves the base report."""
    if "List Bullet" in doc.styles:
        return
    numbering = doc.part.numbering_part.element
    abstract_id = 1 + max((int(n.get(qn("w:abstractNumId"))) for n in numbering.findall(qn("w:abstractNum"))),
                          default=-1)
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    level = OxmlElement("w:lvl")
    level.set(qn("w:ilvl"), "0")
    for tag, value in (("start", "1"), ("numFmt", "bullet"), ("lvlText", "•"), ("lvlJc", "left")):
        child = OxmlElement("w:" + tag)
        child.set(qn("w:val"), value)
        level.append(child)
    abstract.append(level)
    numbering.insert_element_before(abstract, "w:num", "w:numIdMac")
    num_id = numbering.add_num(abstract_id).numId
    style = doc.styles.add_style("List Bullet", WD_STYLE_TYPE.PARAGRAPH, builtin=True)
    style.base_style = doc.styles["Normal"]
    style.paragraph_format.left_indent = Pt(21)
    style.paragraph_format.first_line_indent = Pt(-11)
    style._element.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = num_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=DETAILED_REPORT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    doc = Document(args.base)
    if len(doc.sections) != 4:
        raise ValueError("Use the reviewed four-section Word report")
    ensure_bullet_style(doc)
    artwork = write_figures(PUBLIC / "figures")
    design = design_sections(PUBLIC / "THIET_KE_HE_THONG.md")
    for following, title in (
        ("CHƯƠNG TRÌNH VÀ KẾT QUẢ", "Dựng mẫu và cấu trúc mô hình"),
        ("Tổ chức chương trình", "Kiến trúc hệ thống và vận hành"),
    ):
        insert_before(doc, following, title, design[title], artwork)
    comparisons = (PUBLIC / "SO_SANH_MO_HINH.md").read_text(encoding="utf-8").splitlines()
    insert_before(doc, "KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN",
                  "So sánh LightGBM, GRU và Bi-LSTM theo từng hạn", comparisons, artwork)

    rewrite(doc, "Báo cáo trình bày hai bài toán tại trạm",
            "Báo cáo trình bày hai bài toán tại trạm Đà Nẵng, các bước kiểm tra và ghép dữ liệu, "
            "huấn luyện, kết quả từng nhánh và phép thử đổi kiến trúc. Bản đồ dùng chung chín kỳ "
            "cho 57 trạm lõi. Sơ đồ đi từ nguồn, mẫu và cấu trúc mô hình đến nhật ký phát dự báo, "
            "hiển thị, phân quyền và đối chiếu.")
    anchor = replace_section(doc, "Nghiên cứu mở rộng sang Huế", "TÀI LIỆU THAM KHẢO")
    heading = Paragraph(anchor, doc)
    heading.clear().add_run("Ưu tiên triển khai tại Đà Nẵng")
    anchor = paragraph(doc, anchor, "Mục tiêu tiếp theo là kiểm tra đường thu mưa giờ tại Đà Nẵng, "
                       "ghi đủ dữ liệu và thời gian thực nhận trước giờ phát, rồi chấm qua nhiều đợt mưa. "
                       "Giữ các đối chứng, báo riêng mưa mạnh và đo độ trễ từng nguồn.")._p
    paragraph(doc, anchor, "Các phép thử kiến trúc mới dùng những đợt 2025 đã được chấm, "
              "có giá trị so sánh trên cùng dữ liệu. Mô hình vận hành chỉ được xem xét đổi sau khi "
              "có thêm dữ liệu phù hợp điều kiện phát thật và các đợt giữ riêng đã định trước.")
    layout_tables(doc)
    layout_figures_and_captions(doc)
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(13)
    doc.styles["Normal"].paragraph_format.line_spacing = 1.3

    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output)
    print(f"{len(doc.sections)} sections, {len(doc.tables)} tables, {len(doc.inline_shapes)} figures: {args.output}")


if __name__ == "__main__":
    main()
