"""Publish three-model comparisons from verified aggregates; no model fitting."""
from pathlib import Path
import copy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from presentation_layout import Deck, TEAL, RED, NAVY, MUTED
from build_final_regional_plan import word_copy

OUT = ROOT / 'reports/short_range_three_models_2026_10_21'
OLD = ROOT / 'reports/short_range_revised_2026_10_21'
MATRIX = ROOT / 'reports/short_range_ablation_2026_10_21'
PILOT = ROOT / 'reports/informer_regional_pilot_2026_10_21'
STEM = 'PBL6_SO_SANH_3_MO_HINH'
MODELS = ['lgbm', 'tft', 'informer']
LABELS = {'lgbm': 'LightGBM', 'tft': 'TFT', 'informer': 'Informer'}
METRICS = ['RMSE', 'MAE', 'bias', 'BS', 'BSS', 'CSI', 'POD', 'FAR']
HEADERS = ['RMSE ↓', 'MAE ↓', 'Bias ≈0', 'BS ↓', 'BSS ↑', 'CSI ↑', 'POD ↑', 'FAR ↓']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, content):
    (OUT / name).write_text(content, encoding='utf8', newline='\n')


def markdown_table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join(['---'] * len(headers)) + ' |',
                      *['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]])


def load_scores():
    a = pd.read_csv(MATRIX / 'scores_ensemble_pooled.csv')
    b = pd.read_csv(PILOT / 'scores_pooled.csv')
    a = a[(a.season == 'all') & (a.threshold_mm == 16) & a.model.isin(['lgbm', 'tft'])]
    b = b[(b.season == 'all') & (b.threshold_mm == 16)]
    # Reused TFT predictions were independently replayed; check their aggregates too.
    for r in b[b.model == 'tft'].itertuples():
        x = a[(a.model == 'tft') & (a.experiment == r.experiment) & (a.lead_day == r.lead_day)].iloc[0]
        assert all(abs(float(x[k]) - float(getattr(r, k))) < 1e-10 for k in METRICS)
    result = pd.concat([a, b[b.model == 'informer']], ignore_index=True)
    assert len(result) == 54 and not result.duplicated(['model', 'experiment', 'lead_day']).any()
    assert set(result.n) == {1075} and set(result.events) == {114}
    assert result.groupby(['experiment', 'lead_day']).obs_mean.nunique().max() == 1
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    original = json.loads((OLD / 'slide_scene.json').read_text(encoding='utf8'))
    scores = load_scores()
    deck = Deck()
    roles = {}
    exports = []
    for e in [f'E{i}' for i in range(8)]:
        for day in [1, 2, 3]:
            for model in MODELS:
                r = scores[(scores.experiment == e) & (scores.lead_day == day) & (scores.model == model)]
                record = dict(experiment=e, lead_day=day, model=model, status='available' if len(r) else 'not_run',
                              season='all', threshold_mm=16, n=1075, events=114)
                record.update({k: float(r.iloc[0][k]) if len(r) else None for k in METRICS})
                exports.append(record)
    pd.DataFrame(exports).to_csv(OUT / 'KET_QUA_3_MO_HINH.csv', index=False, lineterminator='\n')

    def reuse(number):
        slide = copy.deepcopy(original[number - 1])
        deck.slides.append(slide)
        return slide

    def new(title, note, source='', section='SO SÁNH BA MÔ HÌNH'):
        return deck.slide(title, section, source or 'Cùng mẫu 2021–2023 • q=16 mm/24h • Vùng 93 ô xấp xỉ • Chưa chấm 2025', note)

    def role(name, slide):
        roles[name] = slide
        return slide

    def text(slide, y, message, size=22, h=1.0):
        return deck.text(slide, .70, y, 11.95, h, message, size)

    def replace_text(slide, before, after):
        for sh in slide['shapes']:
            if sh['kind'] == 'text':
                sh['text'] = sh['text'].replace(before, after)
        slide['note'] = slide['note'].replace(before, after)

    def find(model, e, day):
        rows = scores[(scores.model == model) & (scores.experiment == e) & (scores.lead_day == day)]
        return None if rows.empty else rows.iloc[0]

    def metric_style(value, key, winner):
        return dict(bold=winner, color=RED if key == 'BSS' and value < 0 else TEAL if winner else NAVY)

    def score_rows(experiments, day):
        rows, styles = [], {}
        for e in experiments:
            complete = all(find(model, e, day) is not None for model in MODELS)
            for model in MODELS:
                r = find(model, e, day)
                row = [e, LABELS[model]]
                if r is None:
                    row += ['—'] * len(METRICS)
                else:
                    row += [f'{r[k]:.3f}' for k in METRICS]
                    for col, key in enumerate(METRICS, 2):
                        values = [float(find(m, e, day)[key]) for m in MODELS] if complete else []
                        values = [abs(v) for v in values] if key == 'bias' else values
                        target = min(values) if key in ['RMSE', 'MAE', 'bias', 'BS', 'FAR'] and complete else max(values) if complete else None
                        v = abs(float(r[key])) if key == 'bias' else float(r[key])
                        winner = complete and round(v, 3) == round(target, 3)
                        styles[f'{len(rows) + 1},{col}'] = metric_style(float(r[key]), key, winner)
                rows.append(row)
        return rows, styles

    s = new('Đặc trưng nào giúp dự đoán mưa vùng?',
            'Nghiên cứu dự đoán ba tổng mưa 24 giờ của vùng. Báo cáo đặt LightGBM, TFT và Informer cạnh nhau. TFT và LightGBM đã đủ E0–E7; Informer mới E0/E7. Tổng 114 lượt đã kiểm chứng không đồng nghĩa hoàn thành toàn ma trận ba mô hình.')
    text(s, 1.65, 'LightGBM · TFT · Informer — ba ngày dự đoán\nCùng điều kiện đánh giá, đọc đủ lượng mm và xác suất', 25)
    deck.card(s, .55, 3.05, 3.95, 2.55, 'Đã chạy', 'TFT: 72 lượt, đủ E0–E7\nLightGBM: 24 pipeline\nInformer: 18 lượt E0/E7', 20)
    deck.card(s, 4.70, 3.05, 3.95, 2.55, 'Phần còn thiếu', 'Informer chưa có E1–E6\nKhông điền số giả hoặc số 0\nChưa mở test 2025', 20)
    deck.card(s, 8.85, 3.05, 3.95, 2.55, 'Cách đọc', 'So ba mô hình cùng E/ngày\nThêm biến: so trong mô hình\nĐậm chưa là ý nghĩa thống kê', 20)
    deck.band(s, 'E7 ngày 1: LightGBM tốt hơn về RMSE/BSS/FAR; Informer về CSI; TFT về POD.', size=18.5)
    reuse(2); reuse(3)
    s = reuse(4)
    s['title'] = 'Đầu vào của ba mô hình được tạo thế nào?'
    replace_text(s, 'Một mẫu TFT được tạo như thế nào?', s['title'])
    for shape in s['shapes']:
        if shape['kind'] == 'table':
            shape['rows'][-1][1] = 'Ba mô hình dự đoán lượng + xác suất'
    s['note'] += '\nTFT và Informer dùng chuỗi 28 bước; LightGBM dùng các thống kê của cùng cửa sổ lịch sử. Cùng nguyên liệu không đồng nghĩa cùng biểu diễn hoặc chỉ khác kiến trúc.'
    role('groups', reuse(5))

    s = role('coverage', new('Đã chạy đến đâu? TFT/LightGBM đủ, Informer còn thiếu',
        'Số trong bảng là lượt huấn luyện hoặc pipeline, không phải số ngày mưa. Mỗi E có 9 lượt mạng = ba fold nhân ba seed, LightGBM có ba pipeline xác định. Informer chỉ E0 và E7, còn thiếu 54 lượt E1–E6. Không chạy thêm mô hình trong bước cập nhật slide này.'))
    combinations = ['B', 'B+A', 'B+M', 'B+C', 'B+A+M', 'B+A+C', 'B+M+C', 'B+A+M+C']
    counts = [11, 23, 31, 12, 43, 24, 32, 44]
    rows = [[f'E{i}', combinations[i], counts[i], '3', '9', '9' if i in [0, 7] else 'Chưa chạy'] for i in range(8)]
    deck.table(s, ['E', 'Nhóm biến', 'Biến', 'LightGBM', 'TFT', 'Informer'], rows, y=1.58, row_h=.48,
               widths=[.7, 2.1, .8, 3.0, 2.6, 3.05], size=18, tag='coverage_three_models')
    deck.band(s, 'Đã có: 72 TFT + 24 pipeline LightGBM + 18 Informer = 114 lượt.', size=19)
    s = role('seeds', reuse(7))
    replace_text(s, 'Kết quả TFT đang báo', 'Kết quả TFT/Informer đang báo')
    s['note'] += '\nCả TFT và Informer đều dùng seed 42/43/44. LightGBM hiện không bagging/feature sampling nên không nhân ba lượt xác định giống nhau.'
    s = reuse(8)
    replace_text(s, 'Tám E: 8 × 9 = **72 lượt TFT**; LightGBM có **24 pipeline**.',
                 'TFT đủ tám E: **72 lượt**; LightGBM: **24 pipeline**.\nInformer mới hai E: 2 × 9 = **18 lượt**.')
    for shape in s['shapes']:
        if shape['kind'] == 'text' and shape['y'] > 5.0 and shape['y'] < 6.0:
            shape['h'] = 1.25

    s = new('Vì sao cùng thử LightGBM, TFT và Informer?',
            'LightGBM là đối chứng cây mạnh, TFT học trọng số biến và chuỗi, Informer là đối chứng attention. Đây là lý do chọn thử; kết quả thực nghiệm mới cho biết mô hình nào phù hợp. Không gọi TFT thắng hoặc Informer không khả thi chỉ từ tên kiến trúc.')
    deck.card(s, .55, 1.75, 3.95, 3.95, 'LightGBM', 'Cây tăng cường\nHọc từ bảng thống kê quá khứ\nĐối chứng cần vượt\nĐã đủ E0–E7', 22)
    deck.card(s, 4.70, 1.75, 3.95, 3.95, 'TFT', 'Chọn biến, gating, LSTM\nKết hợp attention\nNhiều hạn đầu ra\nĐã đủ E0–E7', 22)
    deck.card(s, 8.85, 1.75, 3.95, 3.95, 'Informer', 'Attention, ProbSparse\nCó thông tin thời gian\nĐã chạy được cùng dữ liệu\nMới E0/E7', 22)
    deck.band(s, 'TFT và Informer hiện đều là bản điều chỉnh cho bài toán vùng, chưa tuning.', size=19)
    s = new('Cùng thông tin đầu vào, khác cách biểu diễn và học',
            'Ba mô hình cùng nguồn khí tượng quá khứ, lịch, vùng, nhãn, mẫu và chia thời gian. TFT/Informer dùng chuỗi, LightGBM tóm tắt lịch sử thành bảng. Loss và cách học không hoàn toàn giống nhau; vì vậy đây là so ba pipeline, không cô lập riêng kiến trúc.')
    deck.table(s, ['Nội dung', 'LightGBM', 'TFT', 'Informer'], [
        ['Nguyên liệu', 'Quá khứ + lịch', 'Quá khứ + lịch', 'Quá khứ + lịch'],
        ['Biểu diễn', 'Thống kê lịch sử', 'Chuỗi 28 bước', 'Chuỗi 28 bước'],
        ['Cách học', 'Cây tăng cường', 'VSN/LSTM/attention', 'ProbSparse/decoder'],
        ['Lặp huấn luyện', 'Xác định', 'Ba seed', 'Ba seed'],
        ['Đầu ra chấm', 'mm và xác suất', 'mm và xác suất', 'mm và xác suất']],
        row_h=.72, widths=[2.35, 3.3, 3.3, 3.3], size=20, tag='design_three_models')
    deck.band(s, 'Cùng mẫu/nhãn/hạn; không quy mọi khác biệt điểm số riêng cho kiến trúc.', size=18.5)
    for number in range(11, 19):
        s = reuse(number)
        if number == 13: role('metrics', s)

    s = role('counts', new('POD cao hơn: ba mô hình đánh đổi ra sao?',
        'E7 ngày 1 có 114 sự kiện và 961 ngày không có sự kiện. Cả ba dùng quyết định xác suất với ngưỡng chọn riêng trên calibration. TFT bắt nhiều nhất, LightGBM báo nhầm ít nhất, Informer nằm giữa về POD/FAR và có CSI cao nhất. Không phải so ở cùng mức FAR.'))
    count_rows = []
    for model in MODELS:
        r = find(model, 'E7', 1)
        hits = round(r.POD * r.events); miss = int(r.events) - hits
        false = round(hits / (1 - r.FAR) - hits)
        assert abs(hits / (hits + miss + false) - r.CSI) < 1e-10
        count_rows.append([LABELS[model], str(hits), str(miss), str(false), f'{r.POD:.3f}', f'{r.FAR:.3f}', f'{r.CSI:.3f}'])
    deck.table(s, ['Mô hình', 'Trúng H', 'Bỏ sót M', 'Báo nhầm F', 'POD ↑', 'FAR ↓', 'CSI ↑'], count_rows,
               row_h=.82, widths=[2.1, 1.5, 1.5, 1.65, 1.85, 1.85, 1.8], size=21, tag='counts_three_models')
    text(s, 5.15, 'TFT bắt được nhiều sự kiện hơn; LightGBM ít báo nhầm hơn.\nInformer có CSI cao nhất: phải đọc đủ cả ba mô hình.', 23)
    pd.DataFrame(count_rows, columns=['model', 'hits', 'miss', 'false_alarm', 'POD', 'FAR', 'CSI']).to_csv(
        OUT / 'SO_DEM_E7_NGAY1.csv', index=False, lineterminator='\n')
    reuse(20); reuse(21)
    s = reuse(22)
    replace_text(s, 'POD/FAR giữa hai mô hình hiện', 'POD/FAR giữa ba mô hình hiện')
    s = reuse(23)
    replace_text(s, 'Vì sao POD trên slide lên 0,640? Hai cách báo khác nhau', 'Ví dụ TFT: hai quy tắc báo mưa cho POD khác nhau')
    s['title'] = 'Ví dụ TFT: hai quy tắc báo mưa cho POD khác nhau'
    s['note'] += '\nSlide này minh họa hai quy tắc của cùng TFT, không xếp hạng mô hình. Phép so mô hình đặt đủ ba ở bảng E7 tiếp theo.'

    for day in [1, 2, 3]:
        s = role(f'bss_day{day}', new(f'Ngày {day}: BSS của ba mô hình trên E0–E7',
            'Mỗi hàng cùng một cấu hình nhóm biến. Chỉ E0/E7 hiện có đủ ba mô hình. Các ô thiếu Informer là chưa chạy, không phải số 0. Chỉ in đậm giá trị tốt nhất trong hàng đủ ba. Điểm tốt hơn chưa là ý nghĩa thống kê.'))
        rows, styles = [], {}
        for i in range(8):
            e = f'E{i}'; values = [find(model, e, day) for model in MODELS]
            rows.append([e, *[f'{r.BSS:.3f}' if r is not None else 'Chưa chạy' for r in values]])
            complete = all(r is not None for r in values)
            goal = max(float(r.BSS) for r in values) if complete else None
            for col, r in enumerate(values, 1):
                if r is not None:
                    styles[f'{i+1},{col}'] = metric_style(float(r.BSS), 'BSS', complete and round(float(r.BSS), 3) == round(goal, 3))
        deck.table(s, ['E', 'LightGBM', 'TFT', 'Informer'], rows, y=1.55, row_h=.49,
                   widths=[1.15, 3.7, 3.7, 3.7], size=21, styles=styles, tag=f'bss_3models_{day}')
        deck.band(s, 'Đậm: tốt nhất trong hàng đủ ba mô hình · Đỏ: BSS âm · Informer E1–E6 chưa chạy.', size=18)

    comments = {
        1: 'LightGBM tốt hơn về RMSE, MAE, BSS và FAR.\nInformer có CSI cao nhất; TFT có POD cao nhất.',
        2: 'LightGBM tốt hơn ở nhiều chỉ số; TFT có POD cao nhất.\nMọi BSS đều dương nhưng chỉ còn khoảng 0,025–0,043.',
        3: 'Cả ba BSS đều âm: chưa vượt khí hậu về xác suất.\nMột chỉ số tốt hơn không đủ để kết luận dự báo ngày 3 đã tốt.'}
    for day in [1, 2, 3]:
        s = role(f'e7_day{day}', new(f'E7 · ngày {day}: so đồng thời đủ ba mô hình',
            'Cùng 44 biến gốc, 1075 mẫu, ba năm đánh giá và nhãn mưa vùng; sự kiện từ 16 mm/24h. TFT/Informer trung bình ba seed; LightGBM xác định. Ngưỡng xác suất chọn trên calibration. Đậm là điểm tốt nhất ở độ chính xác hiển thị, không phải kết quả kiểm định.\n' + comments[day].replace('\n', ' ')))
        rows, styles = score_rows(['E7'], day)
        rows = [r[1:] for r in rows]
        styles = {f'{key.split(",")[0]},{int(key.split(",")[1])-1}': value for key, value in styles.items()}
        deck.table(s, ['Mô hình', *HEADERS], rows, y=1.80, row_h=.78,
                   widths=[1.85, 1.45, 1.3, 1.3, 1.15, 1.3, 1.3, 1.3, 1.3],
                   size=17.8, styles=styles, tag=f'e7_3models_{day}')
        text(s, 5.15, comments[day], 23)
        s['source'] = 'E7 • q=16 mm/24h • 1.075 mẫu/hạn • Đậm: tốt nhất trong ba, chưa là ý nghĩa thống kê • RMSE/MAE/Bias: mm/24h'
        s['shapes'][3]['text'] = s['source']

    s = reuse(28)
    replace_text(s, 'Nhóm nào cải thiện? Đọc điểm cùng khoảng tin cậy', 'Trong TFT: nhóm nào có bằng chứng cải thiện?')
    s['title'] = 'Trong TFT: nhóm nào có bằng chứng cải thiện?'
    s['note'] += '\nĐây là ablation trong TFT, không xếp hạng ba kiến trúc. Informer chưa E1–E6 nên chưa kiểm tra riêng A/M/C trên Informer.'
    s = new('Khả thi tính toán; chưa hoàn thành nghiên cứu cuối',
            'Có 72 TFT, 24 pipeline LightGBM và 18 Informer được kiểm chứng. Ma trận ba mô hình chưa đủ E1–E6 của Informer. Không cần chạy lại kết quả cũ chỉ để trình bày ba mô hình cùng bảng. Vẫn cần chốt ranh, QC nhãn, kiểm định chênh lệch và khóa thiết kế trước test 2025.')
    deck.card(s, .55, 1.75, 5.95, 3.95, 'Đã có', 'TFT/LightGBM: đủ E0–E7\nInformer: E0/E7, khoảng 5,3 phút\n114 lượt đã được kiểm chứng\nCó cả kết quả cải thiện và kết quả âm', 22)
    deck.card(s, 6.85, 1.75, 5.95, 3.95, 'Còn thiếu', 'Informer E1–E6: 54 lượt\nKiểm định chênh lệch ba pipeline\nRanh vùng và kiểm chứng nhãn\nChốt thiết kế rồi mới chấm 2025', 22)
    deck.band(s, 'Lượt này cập nhật cách trình bày từ kết quả có sẵn; không huấn luyện mới.', size=19)
    s = new('Kết luận phải đặt trong bức tranh đủ ba mô hình',
            'Không nói TFT tốt nhất chỉ vì POD cao hoặc Informer thắng chỉ vì hơn TFT ở một số chỉ số. LightGBM là đối chứng mạnh ngày 1–2 ở E7. Informer khả thi, có CSI tốt hơn ngày 1; TFT bắt nhiều sự kiện hơn nhưng báo nhầm nhiều hơn. Cả ba ngày 3 BSS âm. Informer E1–E6 chưa chạy, test cuối chưa mở.')
    text(s, 1.75, '1. LightGBM là đối chứng mạnh, không được bỏ khỏi bảng so.\n\n2. Ngày 1: LightGBM hơn ở RMSE/BSS/FAR; Informer ở CSI; TFT ở POD.\n\n3. Ngày 3: cả ba chưa vượt khí hậu về dự báo xác suất.\n\n4. Informer mới E0/E7; chưa có ma trận ba mô hình hoàn chỉnh.', 24, h=3.9)
    deck.band(s, 'Phụ lục: đủ ba mô hình trong mỗi E/ngày; ô thiếu ghi rõ chưa chạy.', size=19)
    main_count = len(deck.slides)

    reuse(31)
    for day in [1, 2, 3]:
        for block, experiments in enumerate([['E0', 'E1', 'E2'], ['E3', 'E4', 'E5'], ['E6', 'E7']], 1):
            s = new(f'Ngày {day} · {experiments[0]}–{experiments[-1]} · ba mô hình cùng bảng',
                    'Mỗi E có ba dòng LightGBM, TFT, Informer. Dấu gạch là Informer chưa chạy, không phải metric bằng 0. Chỉ tô đậm tốt nhất trong cùng E khi đủ ba mô hình. Bias xét khoảng cách tới 0; các metric khác theo mũi tên. Số liệu gộp toàn năm; bảng mùa nằm trong CSV nguồn.',
                    section='PHỤ LỤC · ĐỦ E0–E7, BA MÔ HÌNH')
            rows, styles = score_rows(experiments, day)
            deck.table(s, ['E', 'Mô hình', *HEADERS], rows, y=1.60, row_h=.44,
                       widths=[.5, 1.65, *[1.2625] * 8], size=17.2, styles=styles, tag=f'full_3models_{day}_{block}')
            deck.band(s, '— = Informer chưa chạy E1–E6 · Đậm chỉ khi đủ ba mô hình cùng E/ngày.', size=18)
    for number in range(38, 43): reuse(number)

    for number, slide in enumerate(deck.slides, 1):
        slide['number'] = number
        for shape in slide['shapes']:
            if shape['kind'] == 'text' and abs(shape['x'] - 12.05) < .01 and abs(shape['y'] - .18) < .01:
                shape['text'] = f'{number:02d}'
    deck.save(OUT / (STEM + '.pptx'), OUT / (STEM + '.html'), OUT / 'slide_scene.json')
    role_numbers = {key: value['number'] for key, value in roles.items()}
    write('LOI_DAN.md', '# Lời dẫn: đặt đủ ba mô hình cạnh nhau\n\n' + '\n\n'.join(
        f"## Slide {s['number']}: {s['title']}\n\n{s['note']}" for s in deck.slides))
    overview = '''# So sánh LightGBM, TFT và Informer trên cùng điều kiện

Informer hiện **chưa chạy E1–E6**. TFT đã có 72 lượt E0–E7; LightGBM 24 pipeline E0–E7; Informer 18 lượt E0/E7. Còn 54 lượt Informer để đủ toàn ma trận. Lượt cập nhật này chỉ tổng hợp aggregate đã kiểm chứng, không huấn luyện mới hoặc mở test 2025.

So mô hình cần đặt đủ ba trong cùng E, cùng ngày, cùng mẫu, nhãn, mùa, ngưỡng mưa và quy trình chọn ngưỡng xác suất trên calibration. Không cần huấn luyện cùng lúc hoặc chạy lại LightGBM/TFT. TFT và Informer là trung bình dự đoán ba seed; LightGBM hiện chạy xác định. Cùng nguyên liệu nhưng LightGBM dùng thống kê lịch sử, mạng dùng chuỗi, nên đây là so pipeline chứ chưa cô lập riêng kiến trúc.

Mỗi hạn có 1.075 mốc đánh giá gộp 2021–2023; 114 sự kiện vùng từ 16 mm/24 giờ. Các bảng dưới gộp toàn năm. Tách mùa vẫn có ở báo cáo nguồn; không đổi phạm vi thành chỉ mùa mưa.

'''
    for day in [1, 2, 3]:
        rows, _ = score_rows(['E7'], day)
        overview += f'## E7, ngày {day}\n\n' + markdown_table(['Mô hình', *HEADERS], [r[1:] for r in rows]) + '\n\n' + comments[day] + '\n\n'
    overview += '''## Kết luận và phần còn thiếu

LightGBM E7 ngày 1–2 có nhiều điểm tốt hơn TFT/Informer; không được bỏ đối chứng này khỏi kết luận. Informer ngày 1 có CSI cao nhất, TFT có POD cao nhất; ưu thế POD phải đọc cùng FAR. Ngày 3 cả ba BSS âm, chưa vượt khí hậu tham chiếu. Chữ đậm chỉ là điểm tốt nhất trong phép so đủ ba, chưa chứng minh chênh lệch có ý nghĩa thống kê.

Chưa có kết quả riêng nhóm A/M/C của Informer vì thiếu E1–E6; không lấy kết quả TFT để khẳng định các nhóm có ích với mọi kiến trúc. Chưa tuning hoặc kiểm định chênh lệch ba pipeline, chưa chốt ranh/QC nhãn và chưa mở holdout 2025. Ma trận CSV có 72 vị trí dự kiến, 54 có kết quả và 18 vị trí Informer chưa chạy; số vị trí bảng không phải số lượt huấn luyện.

## Giải thích dữ liệu, nhóm biến, seed và metrics

Phần dưới giữ giải thích đầy đủ từ báo cáo trước. Các bảng so sánh ba mô hình ở đầu tài liệu này và slide mới là bản cập nhật; các ví dụ một mô hình minh họa công thức không phải xếp hạng mô hình.

'''
    previous = (OLD / 'GIAI_THICH_THEO_CAU_HOI.md').read_text(encoding='utf8')
    # Avoid appending the obsolete two-model result table from the older companion.
    previous = previous.split('## 6.')[0]
    overview += previous
    write('GIAI_THICH_SO_SANH_3_MO_HINH.md', overview.rstrip() + '\n')
    word_copy(OUT / 'GIAI_THICH_SO_SANH_3_MO_HINH.md')
    write('README.md', f'''# Báo cáo so sánh đồng thời ba mô hình

- [PowerPoint {len(deck.slides)} slide]({STEM}.pptx), [HTML trình chiếu]({STEM}.html).
- [Giải thích Word](GIAI_THICH_SO_SANH_3_MO_HINH.docx), [Markdown](GIAI_THICH_SO_SANH_3_MO_HINH.md), [lời dẫn](LOI_DAN.md).
- [Bảng 72 vị trí E × mô hình × ngày](KET_QUA_3_MO_HINH.csv): 54 đã có kết quả, 18 vị trí Informer chưa chạy; không điền 0.
- [Số đếm E7 ngày 1](SO_DEM_E7_NGAY1.csv); [ma trận TFT/LightGBM và bảng mùa](../short_range_ablation_2026_10_21/README.md), [pilot Informer và bảng mùa](../informer_regional_pilot_2026_10_21/README.md).
- [Giải thích nguồn POD và hai quy tắc báo mưa](../short_range_revised_2026_10_21/README.md).

Có {main_count} slide chính, {len(deck.slides)-main_count} slide tra cứu. Bảng trạng thái ở slide {role_numbers['coverage']}; ba bảng E7 đầy đủ tám metrics ở slide {role_numbers['e7_day1']}–{role_numbers['e7_day3']}. Mỗi bảng xếp hạng mô hình đặt đủ LightGBM, TFT, Informer trong cùng E/ngày; khi thiếu Informer thì không đánh dấu mô hình thắng. Ví dụ công thức hoặc ablation trong một mô hình được ghi rõ mục đích.

Informer mới chạy E0/E7, chưa E1–E6; đây là bản cập nhật trình bày, không huấn luyện mới. Đậm theo số hiển thị chỉ là điểm tốt hơn, chưa có kiểm định chênh lệch ba pipeline. Cùng dữ liệu/nhãn/mẫu nhưng khác biểu diễn giữa cây và mạng. Vùng 93 ô còn xấp xỉ, nhãn cần QC; không đọc test 2025.

Tái lập: `python scripts/build_short_range_three_models.py`, rồi `python scripts/render_short_range_three_models.py` và `python scripts/validate_short_range_three_models.py`. Các báo cáo cũ giữ nguyên.
''')
    sources = [OLD / 'slide_scene.json', OLD / 'GIAI_THICH_THEO_CAU_HOI.md',
               MATRIX / 'scores_ensemble_pooled.csv', PILOT / 'scores_pooled.csv',
               MATRIX / 'run.json', MATRIX / 'checkpoint_audit.json', PILOT / 'run.json', PILOT / 'validation.json']
    assert all(p.exists() for p in sources)
    files = {p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in sorted(OUT.iterdir())
             if p.is_file() and p.name not in ['build_manifest.json', 'render_manifest.json', 'validation.json', 'XEM_TRUOC.png']}
    write('build_manifest.json', json.dumps(dict(status='complete', slides=len(deck.slides), main_slides=main_count,
        roles=role_numbers, models=MODELS, comparison_metrics=METRICS, completed_fits=dict(tft=72, lgbm=24, informer=18),
        planned_score_rows=72, available_score_rows=54, missing_informer_score_rows=18, new_training_runs=0,
        test2025_read=False, code_sha256=sha(__file__),
        sources={str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in sources}, files=files), ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(slides=len(deck.slides), main_slides=main_count, roles=role_numbers, new_training_runs=0), indent=2))


if __name__ == '__main__':
    main()
