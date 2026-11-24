"""Render the written feasibility assessment and aggregate-only chart."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION_START
from docx.shared import Cm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_final_regional_plan import word_copy


def main():
    out = ROOT / 'reports/vrain_data_handoff_2026_11_09'
    zones = pd.read_csv(out / 'zone_thinning_daily.csv')
    region = pd.read_csv(out / 'network_thinning_daily.csv')
    region = region[(region.method == 'thiessen_available_network') & (region.reference == 'dense_thiessen')]
    names = [('coastal', 'Ven biển'), ('interior', 'Nội địa'), ('highland', 'Vùng núi'), ('all', 'Toàn R93')]
    fig, ax = plt.subplots(figsize=(10.8, 6.2))
    colors = ['#2670A8', '#DA8A22', '#38865C']
    positions = np.arange(len(names));width = .23
    for offset, (year, color) in enumerate(zip(['2021', '2022', '2023'], colors)):
        values = [float((region if key == 'all' else zones[zones.zone == key]).loc[
            lambda d: d.scenario.astype(str) == year, 'nrmse_p50'].iloc[0])*100 for key, _ in names]
        bars = ax.bar(positions + (offset-1)*width, values, width, color=color, label='Mẫu thiếu '+year)
        ax.bar_label(bars, labels=[f'{v:.1f}%' for v in values], padding=3, fontsize=9)
    ax.set_xticks(positions, [label for _, label in names], fontsize=12)
    ax.set_ylabel('NRMSE so với mạng đầy đủ (%)', fontsize=12)
    ax.set_ylim(0, 85);ax.grid(axis='y', alpha=.2);ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(frameon=False, loc='upper left')
    fig.suptitle('Mưa trung bình toàn vùng có thể che khuất sai khác ở vùng núi',
                 fontsize=15, fontweight='bold', x=.06, ha='left')
    fig.text(.06, .89, 'Thiessen; trung vị qua mẫu thiếu lịch sử, cùng 67 ngày tham chiếu cuối 2024.', fontsize=10)
    fig.text(.06, .025, 'Tham chiếu nội bộ, không phải chân lý độc lập. Đây là độ nhạy nhãn, không phải sai số mô hình dự báo.\n'
             'Ven biển/nội địa/vùng núi là nhóm ô R93, không phải ranh hành chính. NRMSE = RMSE / mưa tham chiếu trung bình.', fontsize=9)
    fig.subplots_adjust(left=.09, right=.98, bottom=.17, top=.82)
    fig.savefig(out / 'DO_NHAY_NHAN_VUNG.png', dpi=180)
    plt.close(fig)
    source = out / 'DANH_GIA_KHA_THI_VA_HUONG_DI.md'
    target = word_copy(source)
    doc = Document(target)
    for section in doc.sections:
        for paragraph in section.footer.paragraphs:
            for run in paragraph.runs:
                run.text = run.text.replace('20/10/2026', '09/11/2026')
    doc.core_properties.title = 'Đánh giá khả thi nhãn mưa vùng và hướng nghiên cứu'
    doc.core_properties.subject = 'Kiểm định nhãn Vrain trước huấn luyện; không mở 2025'
    section = doc.add_section(WD_SECTION_START.NEW_PAGE)
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = Cm(29.7), Cm(21)
    doc.add_heading('Biểu đồ độ nhạy của nhãn khi mạng trạm thay đổi', level=1)
    doc.add_picture(str(out / 'DO_NHAY_NHAN_VUNG.png'), width=Cm(25.5))
    doc.save(target)
    print('Published assessment Word and aggregate chart:', out)


if __name__ == '__main__':
    main()
