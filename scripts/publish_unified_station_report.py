"""Render the detailed station report using the existing PBL6 Word template."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.publish_station_nowcast import insert_caption, insert_table


DOCUMENTS = ROOT / "data/operational/pbl6_bao_cao_cuoi_ky_2026_11_24"
TEMPLATE = DOCUMENTS / "PBL6_BAO_CAO_CUOI_KY_HAI_NHANH.docx"
OUTPUT = DOCUMENTS / "PBL6_BAO_CAO_CUOI_KY_HAI_NHANH_CHI_TIET.docx"
PUBLIC = ROOT / "reports/station_forecast_unified_2026_11_24"
FIGURES = ROOT / "data/operational/station_map_unified_2026_11_24/qa"
FRONT_AND_BACK = {"MỞ ĐẦU", "TÀI LIỆU THAM KHẢO", "PHỤ LỤC"}


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


def insert_run(paragraph, line):
    line = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", line)
    for portion in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", line):
        if portion.startswith("**"):
            paragraph.add_run(portion[2:-2]).bold = True
        elif portion.startswith("`"):
            paragraph.add_run(portion[1:-1])
        else:
            paragraph.add_run(portion)


def caption(doc, group, number, title):
    node = insert_caption(doc, doc.element.body[-2], group, number, title)
    from docx.text.paragraph import Paragraph

    Paragraph(node, doc).paragraph_format.keep_with_next = group == "Table"


def apply_table_style(table):
    for row in table.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.space_before = Pt(2)
                for run in p.runs:
                    run.font.size = Pt(11)


def report(template, markdown, output, figures):
    doc = Document(template)
    body = doc.element.body
    start = next(p._p for p in doc.paragraphs if p.text == "MỞ ĐẦU")
    # Keep the cover, front matter, index fields, headers and page settings.
    while start is not None and start.tag != qn("w:sectPr"):
        following = start.getnext()
        body.remove(start)
        start = following

    figures.mkdir(parents=True, exist_ok=True)
    plot_timeline(figures / "forecast-periods.png")
    artwork = {
        "timeline": ("forecast-periods.png", "Các kỳ tính từ cùng thời điểm phát"),
        "map_hour": ("unified-hour.png", "Bản đồ xã, phường ở Giờ 1 và thanh chín kỳ"),
        "map_day": ("unified-day.png", "Cùng bản đồ và tập trạm khi chọn Ngày 1"),
    }
    table_number = figure_number = 0
    lines = markdown.read_text(encoding="utf-8").splitlines()
    title = ""
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("# "):
            continue
        match = re.fullmatch(r"(#{2,4}) (.+)", line)
        if match:
            digits, text = match.groups()
            style = "MucLonBaoCao" if text in FRONT_AND_BACK else f"Heading {len(digits) - 1}"
            doc.add_paragraph(text, style=style)
            continue
        picture = re.fullmatch(r"<!-- figure:(\w+) -->", line)
        if picture:
            filename, text = artwork[picture.group(1)]
            image = figures / filename
            if image.is_file():
                p = doc.add_paragraph()
                p.paragraph_format.keep_with_next = True
                p.add_run().add_picture(str(image), width=Cm(15))
                figure_number += 1
                caption(doc, "Figure", figure_number, text)
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
            table_number += 1
            caption(doc, "Table", table_number, title)
            insert_table(doc, body[-2], rows)
            apply_table_style(doc.tables[-1])
            title = ""
            continue
        if line.startswith("- "):
            line = "• " + line[2:]
        insert_run(doc.add_paragraph(), line)

    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    print(f"Saved {table_number} tables and {figure_number} figures to {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=TEMPLATE)
    parser.add_argument("--markdown", type=Path, default=PUBLIC / "BAO_CAO_CHI_TIET.md")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--figures-dir", type=Path, default=FIGURES)
    args = parser.parse_args()
    report(args.template, args.markdown, args.output, args.figures_dir)


if __name__ == "__main__":
    main()
