"""Readable aggregate pilot report and standalone figures, without station data."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from docx import Document
from docx.shared import Cm,Pt

OUT=ROOT/'reports/gfs_station_pilot_2026_11_10'


def fmt(x,digits=2):return '—' if not np.isfinite(x) else f'{x:.{digits}f}'


def main():
    point=pd.read_csv(OUT/'point_metrics.csv');prob=pd.read_csv(OUT/'probability_metrics.csv')
    event=pd.read_csv(OUT/'event_metrics.csv');ci=pd.read_csv(OUT/'paired_bootstrap.csv')
    protocol=json.loads((OUT/'protocol.json').read_text());audit=json.loads((OUT/'dataset_audit.json').read_text())
    verify=json.loads((OUT/'verification.json').read_text());run=json.loads((OUT/'run_summary.json').read_text())
    neural=json.loads((OUT/'gru_summary.json').read_text())
    model_verify=json.loads((OUT/'model_verification.json').read_text())
    release=json.loads((OUT/'release_timestamp_audit.json').read_text())
    release_metrics=pd.read_csv(OUT/'release_sensitivity_metrics.csv')
    assert model_verify['status']=='passed'
    models=['CLIM','PERSISTENCE','GFS','A0','A1','A2','A3']+(['GRU_A2'] if neural['status']=='complete' else [])
    labels={'CLIM':'Khí hậu','PERSISTENCE':'Persistence','GFS':'GFS nguyên bản','A0':'LightGBM A0',
        'A1':'LightGBM A1','A2':'LightGBM A2','A3':'LightGBM A3','GRU_A2':'GRU A2'}
    dev=point[point.fold.eq('dev')]
    mae=dev.pivot(index='model',columns='horizon',values='macro_mae').reindex(models)
    figure,ax=plt.subplots(figsize=(11,5.4))
    x=np.arange(len(models));colors=['#255f85','#2a9d8f','#e9a23b']
    for h in [1,2,3]:ax.bar(x+(h-2)*.25,mae[h],width=.24,label=f'Ngày {h}',color=colors[h-1])
    ax.set_xticks(x,[labels[m] for m in models],rotation=18,ha='right');ax.set_ylabel('MAE trung bình giữa trạm (mm / 24h)')
    ax.set_title('Pilot 20 trạm · lịch issue mỗi 7 ngày · đánh giá phát triển 2024')
    ax.legend();ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    figure.tight_layout();figure.savefig(OUT/'mae_comparison.png',dpi=180);plt.close(figure)
    reliability=pd.read_csv(OUT/'reliability.csv')
    figure,axes=plt.subplots(1,2,figsize=(10,4.5))
    for ax,t in zip(axes,[1.,50.]):
        ax.plot([0,1],[0,1],color='gray',linestyle='--',label='Hiệu chuẩn lý tưởng')
        for m in ['A0','A2','A3']+(['GRU_A2'] if neural['status']=='complete' else []):
            s=reliability[reliability.model.eq(m)&reliability.threshold_mm.eq(t)].sort_values('bin')
            ax.plot(s.mean_probability,s.observed_frequency,marker='o',label=labels[m])
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Xác suất dự báo trung bình',ylabel='Tần suất xảy ra thực tế',title=f'Mưa ≥ {t:g} mm / 24h')
        ax.grid(alpha=.2)
    axes[1].legend(fontsize=8);figure.suptitle('Reliability: gộp ba hạn, tập phát triển 2024; các bin có cỡ mẫu khác nhau')
    figure.tight_layout();figure.savefig(OUT/'reliability.png',dpi=180);plt.close(figure)

    lines=['# Kết quả pilot GFS + Vrain tại trạm — 10/11/2026','',
        '**Đã chạy thí nghiệm thực tế**, gồm khí hậu tham chiếu, persistence, GFS nguyên bản và LightGBM A0–A3. '
        +('GRU A2 cũng đã chạy theo gate định trước trên tập hiệu chỉnh.' if neural['status']=='complete' else 'GRU được dừng theo gate định trước trên tập hiệu chỉnh.'),'',
        '**Phạm vi:** 20 trạm; lịch cố định mỗi 7 ngày trong 2021–2024, 208 issue đã trích GFS. Đây là pilot, '
        'chưa phải thí nghiệm dự báo hằng ngày hoặc kết quả cuối cho toàn bộ 79/86 trạm. Năm 2025 vẫn giữ kín.','',
        '## Bài toán và cách tránh lấy nhầm tương lai','',
        'Lúc 19:00 giờ Việt Nam, dự báo ba tổng mưa riêng: 0–24h, 24–48h và 48–72h. Nhãn là Vrain tại chính trạm. '
        'GFS khởi tạo 00UTC, sớm hơn issue 12 giờ; hiệu các tổng mưa tích lũy +12/+36/+60/+84h tạo đúng ba cửa sổ 19–19h. '
        'Các trường khí tượng ở +24/+48/+72h là dự báo từ cùng bản khởi tạo, không phải số đo tương lai hay ERA5 kỳ đích.','',
        'Giả định mưa trạm trễ 1 giờ: summary 1/6/24h kết thúc 18:00; chuỗi bảy ngày đầy đủ kết thúc hôm trước. '
        'GFS giả định sẵn sàng sau 8 giờ từ init, nhưng chưa xác minh thời điểm công bố lịch sử từng file. '
        'Đây là thiết kế hồi cứu có kiểm soát thời gian, chưa chứng nhận hệ thống vận hành.','',
        '## Mẫu, biến và mô hình','',
        f"Chọn 20 trạm từ {protocol['eligible_cohort_candidates']} ứng viên bằng dữ liệu train và địa lý/DEM, không chọn theo điểm cal/dev. "
        'Mỗi trạm pilot có 565–728 ngày train đầy đủ. Không yêu cầu toàn mạng có số đo đồng thời.','',
        '| Phần | Năm | Mẫu trạm–issue | Dòng theo ba hạn | Vai trò |','|---|---|---:|---:|---|']
    for fold,years,role in [('train','2021–2022','Fit mô hình và thống kê'),('cal','2023','Earlystop, Platt, gate GRU'),('dev','2024','Đánh giá phát triển, chưa test cuối')]:
        count=audit['split_rows'][fold]
        lines.append(f'| {fold} | {years} | {count//3:,} | {count:,} | {role} |')
    lines+=['','Hai issue bị loại vì nhãn vượt ranh split; 461 mẫu trạm–issue không đủ lịch sử/nhãn bị loại. '
        'Mọi cấu hình dùng chung phần dữ liệu còn lại. Số mẫu giữa các trạm/đợt mưa không độc lập.','',
        '| Cấu hình | Số biến | Bổ sung |','|---|---:|---|',
        '| A0 | 6 | Mưa GFS + lịch + tọa độ/ID trạm |',
        '| A1 | 16 | A0 + bảy ngày mưa và summary 1/6/24h tại trạm |',
        '| A2 | 25 | A1 + T/RH/gió 850/PWAT, độ ẩm riêng dẫn xuất và proxy vận chuyển ẩm |',
        '| A3 | 32 | A2 + DEM, gradient và tương tác gió–địa hình–ẩm |','',
        'Tất cả LightGBM dùng Tweedie p=1,5 cho lượng mưa, classifier cho ≥1/≥50mm. Mỗi cấu hình có ba seed 17/29/43, '
        'lấy trung bình dự báo; đây không phải ba năm kiểm định độc lập. Cal dùng Platt nên điểm xác suất cal không phải ngoài mẫu. '
        'Ngưỡng 50mm là phân tích thăm dò của pilot, không tự nhận tiêu chuẩn cảnh báo.','',
        '## Kết quả lượng mưa trên phần phát triển 2024','',
        'MAE dưới đây là trung bình MAE giữa các trạm, mỗi trạm có trọng số bằng nhau; nhỏ hơn tốt hơn. '
        '**In đậm là thấp nhất trong từng cột**, không tự đồng nghĩa khác biệt có ý nghĩa thống kê.','',
        '| Phương pháp | MAE ngày 1 (mm) | MAE ngày 2 (mm) | MAE ngày 3 (mm) |','|---|---:|---:|---:|']
    for m in models:
        cells=[f'**{mae.loc[m,h]:.2f}**' if np.isclose(mae.loc[m,h],mae[h].min()) else f'{mae.loc[m,h]:.2f}' for h in [1,2,3]]
        lines.append('| '+labels[m]+' | '+' | '.join(cells)+' |')
    gains=[]
    for h in [1,2,3]:
        raw=mae.loc['GFS',h];value=mae.loc['A2',h]
        gains.append(dict(horizon=h,gfs_mae=float(raw),a2_mae=float(value),relative_mae_reduction_percent=float((raw-value)/raw*100)))
    lines+=['','A2 là cấu hình đặt trước cho đối chứng chuỗi, không chọn theo điểm dev. So với GFS, MAE A2 thay đổi: '
        +'; '.join(f"ngày {g['horizon']}: {g['relative_mae_reduction_percent']:.1f}% giảm" for g in gains)+'.','',
        '## Kiểm tra chênh lệch và tác dụng thêm biến','',
        'Chênh MAE = phương pháp thứ nhất trừ tham chiếu; số âm có lợi cho phương pháp thứ nhất. '
        'CI bootstrap 95% theo khối bốn issue liên tiếp, giữ các trạm trong cùng đợt. CI có cả 0 nghĩa là chưa đủ căn cứ cải thiện ổn định.','',
        '| So sánh | Ngày | Chênh MAE (mm) | CI 95% (mm) |','|---|---:|---:|---|']
    for a,b in [('A2','GFS'),('A1','A0'),('A2','A1'),('A3','A2')]+([('GRU_A2','A2')] if neural['status']=='complete' else []):
        for h in [1,2,3]:
            s=ci[ci.fold.eq('dev')&ci.model.eq(a)&ci.reference.eq(b)&ci.horizon.eq(h)]
            if len(s):
                r=s.iloc[0];lines.append(f"| {a} − {b} | {h} | {r.mae_difference:.2f} | [{r.ci95_low:.2f}; {r.ci95_high:.2f}] |")
    lines+=['','**Kết luận về mức chắc chắn:** CI A2−GFS ở cả ba ngày đều còn chứa 0. '
        'Mức giảm MAE ngày 3 khoảng 24% là dấu hiệu trên mẫu pilot, chưa đủ để khẳng định cải thiện ổn định. '
        'A3 chưa cho thấy lợi ích địa hình chắc chắn so A2. GRU có MAE cao hơn A2 ở cả ba hạn trong cấu hình đã thử, '
        'nhưng RMSE ngày 3 thấp hơn: GRU 18,31mm so A2 20,17mm. Có đánh đổi giữa các chỉ số; '
        'không kết luận GRU kém trên mọi mặt hoặc mọi kiến trúc GRU đều kém.','',
        '## Kiểm tra thời điểm sửa file nguồn','',
        f"Đã kiểm tra Last-Modified của {release['messages']:,} thông điệp thuộc {release['cycles']} chu kỳ. "
        f"Có {release['cycles_with_object_modification_after_issue']} chu kỳ đầu 2021 được sửa/chép trong archive sau issue; "
        'Last-Modified không chứng minh thời điểm phát hành dự báo gốc. Không có trường hợp này ở các năm cal/dev.','',
        'Đã chạy thêm A2 ba seed, bỏ các chu kỳ train có timestamp không rõ; không thay kết quả chính và không chọn theo điểm mưa.','',
        '| Ngày | MAE A2 chính (mm) | MAE A2 bỏ chu kỳ train không rõ (mm) |','|---|---:|---:|']
    for h in [1,2,3]:
        s=release_metrics[release_metrics.fold.eq('dev')&release_metrics.horizon.eq(h)].set_index('model')
        lines.append(f"| {h} | {s.loc['A2_primary','macro_mae']:.2f} | {s.loc['A2_omit_ambiguous_train_cycles','macro_mae']:.2f} |")
    lines+=['','## RMSE, Bias và phát hiện sự kiện','',
        'RMSE nhấn mạnh lỗi lượng mưa lớn; Bias âm là dự báo thiếu mưa. BSS >0 nghĩa là xác suất tốt hơn khí hậu tham chiếu trên cùng mẫu. '
        'POD cần đọc cùng FAR và CSI; không có mức POD tốt chung cho mọi bài toán.','']
    for h in [1,2,3]:
        lines += [f'### Ngày {h}', '', '| Phương pháp | RMSE mm | Bias mm | BSS ≥1 | CSI ≥1 | POD ≥1 | FAR ≥1 |', '|---|---:|---:|---:|---:|---:|---:|']
        for m in models:
            p=dev[dev.model.eq(m)&dev.horizon.eq(h)].iloc[0]
            e=event[event.fold.eq('dev')&event.horizon.eq(h)&event.model.eq(m)&event.threshold_mm.eq(1)].iloc[0]
            s=prob[prob.fold.eq('dev')&prob.horizon.eq(h)&prob.model.eq(m)&prob.threshold_mm.eq(1)]
            bss=fmt(s.iloc[0].macro_bss,3) if len(s) else '—'
            lines.append(f'| {labels[m]} | {p.macro_rmse:.2f} | {p.macro_bias:.2f} | {bss} | {fmt(e.macro_csi,3)} | {fmt(e.macro_pod,3)} | {fmt(e.macro_far,3)} |')
    lines+=['','Xác suất được chuyển thành báo có khi p≥0,5; GFS/persistence dùng lượng dự báo≥ngưỡng. '
        'GFS không có BSS ở đây vì là dự báo đơn trị, không phải xác suất đã hiệu chuẩn. '
        'POD/FAR không xác định được giữ NaN và báo số trạm hỗ trợ trong CSV, không tự đổi thành 0.','',
        'Xác suất không cải thiện đồng đều với lượng mưa. Ví dụ ở ngày 1, cần đối chiếu BSS A0 với A2/A3, '
        'không chọn cấu hình chỉ vì MAE thấp hơn. Ảnh reliability gộp ba hạn chỉ hỗ trợ chẩn đoán; có bin ít mẫu.','',
        '## Giới hạn và bước tiếp theo','',
        '- Pilot mới có lịch issue mỗi 7 ngày, 20 trạm và bốn năm thời tiết; cần chạy lịch hằng ngày để xác nhận. '
        'Không dùng số dòng hoặc nhiều trạm cùng trận để phóng đại cỡ mẫu độc lập.',
        '- Mùa/năm có thể cho kết quả khác nhau. Gate GRU dựa trên cal: A2 chỉ đạt ở ngày 3 với mức cải thiện nhỏ; '
        'không dùng kết quả dev thuận lợi để sửa gate hoặc chọn trạm.',
        '- Địa hình là proxy, không phải cao độ đo tại trạm; chưa có kiểm chứng lịch sử di chuyển/cảm biến. '
        'Một số điểm có cao độ DEM gần hoặc thấp hơn mực biển. Mean/std là chín điểm trong ô ±5km theo hai trục, '
        'không phải trung bình tất cả pixel. ID trạm đã có thể mang một phần khác biệt địa phương; '
        'chưa kiểm chứng tổng quát sang trạm chưa thấy.',
        '- Chưa chứng minh các đặc trưng thêm đều hữu ích. Thứ tự A0→A3 còn phụ thuộc nhóm đã có; '
        'cần thử bỏ nhóm khỏi cấu hình đầy đủ, giữ cùng mẫu, trước kết luận đóng góp.',
        '- Đánh giá ≥50mm có thể ít đợt mưa; xem số sự kiện và số issue có mưa trong CSV. '
        'Chưa có CI cho mọi chênh lệch BSS hoặc bằng chứng cải thiện cực đoan ổn định.',
        '- Trễ mưa trạm 1 giờ và GFS 8 giờ là giả định cần kiểm chứng. GFS là sản phẩm lưới, '
        'không mô tả đầy đủ địa hình/quá trình nhỏ tại từng trạm.',
        '- Năm 2025 chưa mở, 2026 không fit/tuning. Tập 2024 là đánh giá phát triển; kết quả này chưa là test cuối.','',
        '**Bước tiếp theo đề xuất:** hoàn thành thí nghiệm hằng ngày với protocol cố định, kiểm tra độ nhạy trễ dữ liệu, '
        'và ablation bỏ nhóm; tiếp tục đánh giá theo từng trạm/mùa/hạn. Chưa có cơ sở yêu cầu chuyển sang mô hình lớn hơn.','',
        '## Bằng chứng và tái tạo','',
        f"Đã replay {verify['rows_replayed']:,} dòng từ raw Vrain, kiểm tra {verify['forecast_message_headers_checked']:,} header GRIB; "
        f"tải lại {verify['new_raw_grib_range_requests']} thông điệp và đối chiếu {verify['independent_four_corner_samples']} mẫu nội suy độc lập. "
        'Không dùng ERA5 hoặc khí tượng tương lai thực đo trong X.','',
        f"Đã replay {model_verify['replayed_lightgbm_amount_estimators']} estimator lượng mưa, "
        f"{model_verify['replayed_lightgbm_binary_estimators']} classifier và ba checkpoint GRU trên CPU; "
        'đối chiếu dự báo lưu, scaler train-only và metrics tổng hợp đạt.','',
        '[Protocol](protocol.json), [audit dữ liệu](dataset_audit.json), [verification](verification.json), '
        '[kết quả lượng mưa](point_metrics.csv), [xác suất](probability_metrics.csv), [sự kiện](event_metrics.csv), '
        '[bootstrap](paired_bootstrap.csv), [seed](seed_point_metrics.csv), [GRU](gru_summary.json), '
        '[replay mô hình](model_verification.json), [timestamp nguồn](release_timestamp_audit.json), '
        '[kiểm tra độ nhạy](release_sensitivity_metrics.csv).','',
        'Mã chạy: prepare/collect/build/validate/run_gfs_station_pilot.py và run_gfs_station_gru.py. '
        'Dữ liệu, tọa độ, checkpoint và dự đoán từng thời điểm nằm ngoài Git.','',
        'Nguồn: [NOAA GFS](https://registry.opendata.aws/noaa-gfs-bdp-pds/), '
        '[inventory GFS](https://www.nco.ncep.noaa.gov/pmb/products/gfs/), '
        '[Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/), '
        '[attribution DEM](https://github.com/tilezen/joerd/blob/master/docs/attribution.md).','']
    (OUT/'BAO_CAO_PILOT.md').write_text('\n'.join(lines),encoding='utf8')
    result=dict(status='pilot_complete',weekly_cadence_days=7,selected_stations=20,forecast_issues_collected=208,
        models_completed=models,
        training_station_issue_samples=audit['split_rows']['train']//3,
        calibration_station_issue_samples=audit['split_rows']['cal']//3,
        development_station_issue_samples=audit['split_rows']['dev']//3,
        a2_vs_raw_gfs_development=gains,gru_status=neural['status'],
        A2_vs_GFS_all_three_CI_include_zero=bool(((ci.loc[ci.fold.eq('dev')&ci.model.eq('A2')&ci.reference.eq('GFS'),'ci95_low']<=0)
            &(ci.loc[ci.fold.eq('dev')&ci.model.eq('A2')&ci.reference.eq('GFS'),'ci95_high']>=0)).all()),
        full_daily_experiment_complete=False,final_test_performed=False,test2025_read=False,
        conclusion='Preliminary point skill; feature/probability gains not uniform. Daily replication and uncertainty checks required.')
    (OUT/'result_summary.json').write_text(json.dumps(result,indent=2)+'\n')

    doc=Document();section=doc.sections[0]
    section.page_width=Cm(21);section.page_height=Cm(29.7)
    section.top_margin=section.bottom_margin=Cm(1.6)
    section.left_margin=section.right_margin=Cm(1.6)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(5)
    doc.add_heading('PILOT DỰ BÁO MƯA TẠI TRẠM',0)
    doc.add_paragraph('GFS + Vrain · 20 trạm · ba hạn ngày · 10/11/2026')
    doc.add_paragraph('Đã chạy LightGBM A0–A3 và các đối chứng. '+('GRU A2 cũng đã chạy với ba seed.' if neural['status']=='complete' else 'GRU chưa qua điều kiện pilot.'))
    doc.add_paragraph('Quan trọng: lịch issue mỗi 7 ngày trong 2021–2024, chưa phải dự báo hằng ngày đầy đủ. Năm 2025 vẫn giữ kín; 2024 là phần đánh giá phát triển.')
    doc.add_heading('Mục tiêu và đầu vào',1)
    doc.add_paragraph('Lúc 19h Việt Nam, dự báo ba tổng24h riêng tại cùng trạm. GFS00UTC khởi tạo trước issue12h; dữ liệu khí tượng tương lai là dự báo từ bản này, không phải số thực đo. Mưa trạm có cutoff18h theo trễ giả định1h; lịch sử gồm bảy ngày đầy đủ và summary1/6/24h.')
    doc.add_paragraph('A0: mưa GFS, lịch, vị trí/ID. A1: thêm mưa quá khứ trạm. A2: thêm T/RH/gió850/PWAT và proxyẩm. A3: thêm DEM và tương tác gió–địa hình. Tất cả cấu hình cùng mẫu; mỗi mô hình học chung20trạm.')
    doc.add_paragraph(f"Train2021–22: {audit['split_rows']['train']//3:,} mẫu trạm–issue; cal2023: {audit['split_rows']['cal']//3:,}; dev2024: {audit['split_rows']['dev']//3:,}. Mỗi mẫu có ba nhãn ngày riêng. Mọi scaler/reference fittrain; earlystop/calibration dùngcal.")
    doc.add_heading('MAE trên phần phát triển2024',1)
    t=doc.add_table(rows=1,cols=4);t.style='Light Shading Accent 1'
    for c,text in zip(t.rows[0].cells,['Phương pháp','Ngày1 (mm)','Ngày2 (mm)','Ngày3 (mm)']):c.text=text
    for m in models:
        cells=t.add_row().cells;cells[0].text=labels[m]
        for h in [1,2,3]:
            r=cells[h].paragraphs[0].add_run(f'{mae.loc[m,h]:.2f}')
            r.bold=bool(np.isclose(mae.loc[m,h],mae[h].min()))
    doc.add_paragraph('MAE trung bình đồng trọng số giữa trạm; nhỏ hơn tốt hơn. In đậm là thấp nhất từng cột, chưa khẳng định khác biệt có ý nghĩa thống kê.')
    doc.add_picture(str(OUT/'mae_comparison.png'),width=Cm(17.4))
    doc.add_page_break()
    doc.add_heading('Đọc kết quả một cách thận trọng',1)
    for text in [
        'A2 so với GFS: '+ '; '.join(f"ngày{g['horizon']} giảmMAE {g['relative_mae_reduction_percent']:.1f}%" for g in gains)+'.',
        'Đây là thay đổi trên pilot2024. Kết quả2023 có thể khác; A2 chỉ đạt gateGRU ở ngày3 với chênh lệch nhỏ. Không chọn cấu hình theo phần2024 rồi gọi đó là test cuối.',
        'Thêm biến không cải thiện đồng đều mọi chỉ số. MAE, RMSE, Bias và BSS có thể chọn cấu hình khác nhau. Cần giữ mọi kết quả, kể cả không cải thiện.',
        'POD cao phải đọc cùng FAR và CSI. BSS>0 nghĩa là tốt hơn xác suất khí hậu tham chiếu. Cal đã được dùng để hiệu chuẩn nên điểm xác suấtcal không phải ngoài mẫu.',
        'CI bootstrap giữ các trạm của cùng đợt trong một khối. Cả ba CI A2−GFS còn chứa0: mức giảm MAE chưa chứng minh cải thiện ổn định. Xem bảng đầy đủ trong BAO_CAO_PILOT.md và paired_bootstrap.csv.',
        'GRU có MAE cao hơn A2 ở cả ba hạn, nhưng RMSE ngày3 thấp hơn (18,31 so20,17mm). Đây là đánh đổi, không phải GRU kém mọi mặt. A3 chưa cho lợi ích địa hình ổn định.',
        'Có7chu kỳ đầu2021 có timestamp sửa/chép archive sau issue. Đã thử bỏ các chu kỳ đó khỏi train và chạy lại A2; hướng thay đổi điểm số vẫn tương tự. Chưa coi Last-Modified là bằng chứng phát hành gốc.'
    ]:doc.add_paragraph(text)
    doc.add_heading('CI95% cho A2 so với GFS (mm)',1)
    t=doc.add_table(rows=1,cols=3);t.style='Light Shading Accent 1'
    for c,text in zip(t.rows[0].cells,['Ngày','ChênhMAE A2−GFS','CI95%']):c.text=text
    for h in [1,2,3]:
        r=ci[ci.fold.eq('dev')&ci.model.eq('A2')&ci.reference.eq('GFS')&ci.horizon.eq(h)].iloc[0]
        for c,text in zip(t.add_row().cells,[str(h),f'{r.mae_difference:.2f}',f'[{r.ci95_low:.2f}; {r.ci95_high:.2f}]']):c.text=text
    doc.add_heading('Giới hạn và bước tiếp theo',1)
    for text in [
        'Pilot lấy mẫu mỗi7ngày,20trạm,bốn năm thời tiết; nhiều trạm cùng trận không là mẫu độc lập. Chưa kết luận cho toàn mạng hoặc mưa cực đoan.',
        'Trễ trạm1h và GFS8h là giả định chưa xác minh lịch sử từng file. DEM là proxy, không phải cao độ khảo sát; chưa biết lịch sử di chuyển/cảm biến.',
        'Đã kiểm tra nguồn, khoảng tích lũy, đơn vị, thời gian và việc ghép. Kiểm tra cấu trúc không chứng nhận cảm biến hoặc năng lực vận hành.',
        'Bước tiếp: lịch dự báo hằng ngày, độ nhạy trễ dữ liệu và ablation bỏ nhóm. Chưa cần mặc định tăng kích thước mô hình. Giữ2025kín đến khi khóa protocol;2026khôngtuning.'
    ]:doc.add_paragraph(text)
    doc.add_paragraph('Nguồn: NOAA GFS; Mapzen Terrain Tiles (attribution theo tilezen/joerd). Báo cáo và CSV chi tiết ở reports/gfs_station_pilot_2026_11_10/. Dữ liệu/tọa độ/model/dự đoán từng mốc nằm ngoài GitHub công khai.')
    doc.core_properties.title='Pilot GFS + Vrain — dự báo mưa ngày 1–3 tại trạm'
    doc.core_properties.subject='20 trạm, cadence 7 ngày, train 2021–2022 / cal 2023 / dev 2024'
    doc.save(OUT/'BAO_CAO_PILOT.docx')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
