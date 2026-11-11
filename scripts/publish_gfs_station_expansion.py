"""Publish a 57-station report, separating cohort coverage from model skill."""
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Cm,Pt

from src.gfs_experiment import SOURCE_NAME,experiment_paths
from src.gfs_cohort_comparison import match_original_examples
from src.gfs_station_dataset import macro_metrics
from scripts.run_gfs_station_pilot import block_difference

NAME='gfs_station_57_2026_11_10'


def readable(text):
    text=re.sub(r'(\d)(trạm|ngày|giờ|năm|mẫu|hàng|cửa|hạn|nhãn|đầu|có|và|chưa|thì|còn)',r'\1 \2',text,flags=re.I)
    text=re.sub(r'(sung|lên|từ|cùng|đúng|có|nhóm|bản|giữ|số|với|và|dưới|trong|ngày|trạm|hạn|train/cal)(\d)',r'\1 \2',text)
    text=re.sub(r'(\d)(mm|h)\b',r'\1 \2',text)
    return text


def main():
    new=experiment_paths(ROOT,NAME);old=experiment_paths(ROOT,SOURCE_NAME)
    out=new.public
    expanded=pd.read_parquet(new.base/'predictions_private.parquet')
    previous=pd.read_parquet(old.base/'predictions_private.parquet')
    old_ids=pd.read_csv(old.base/'pilot_stations_private.csv').canonical_id.tolist()
    matched=match_original_examples(previous,expanded,old_ids)
    audit=json.loads((out/'dataset_audit.json').read_text());cohort=json.loads((out/'cohort_expansion_audit.json').read_text())
    verification=json.loads((out/'verification.json').read_text());models_verified=json.loads((out/'model_verification.json').read_text())
    assert verification['status']==models_verified['status']=='passed'
    points=pd.read_csv(out/'point_metrics.csv');neural=json.loads((out/'gru_summary.json').read_text())
    methods=['CLIM','PERSISTENCE','GFS','A0','A1','A2','A3']+(['GRU_A2'] if neural['status']=='complete' else [])
    scopes=[('all57',57,expanded),('original20',57,expanded[expanded.station_id.isin(old_ids)]),
            ('added37',57,expanded[~expanded.station_id.isin(old_ids)]),('original20',20,previous)]
    rows=[]
    for scope,trained,frame in scopes:
        for fold in ['cal','dev']:
            for h in [1,2,3]:
                part=frame[frame.split.eq(fold)&frame.horizon.eq(h)]
                for method in methods:
                    if method not in part:continue
                    metric,_=macro_metrics(pd.DataFrame(dict(station_id=part.station_id,y=part.y_mm,pred=part[method])))
                    rows.append(dict(evaluation_cohort=scope,trained_stations=trained,fold=fold,horizon=h,model=method,**metric))
    scoped=pd.DataFrame(rows);scoped.to_csv(out/'cohort_scope_metrics.csv',index=False)
    comparisons=[]
    for fold in ['cal','dev']:
        for h in [1,2,3]:
            part=matched[matched.split_20.eq(fold)&matched.horizon.eq(h)]
            for method in ['A0','A1','A2','A3','GRU_A2']:
                if method+'_20' not in part or method+'_expanded' not in part:continue
                f=part[['station_id','issue_utc']].copy()
                f['y_mm']=part.y_mm_20;f['model20']=part[method+'_20'];f['model57']=part[method+'_expanded']
                comparisons.append(dict(fold=fold,horizon=h,model=method,matched_stations=f.station_id.nunique(),
                    matched_rows=len(f),**block_difference(f,'model57','model20')))
    comparison=pd.DataFrame(comparisons);comparison.to_csv(out/'matched_original20_bootstrap.csv',index=False)
    common_a2=comparison[comparison.fold.eq('dev')&comparison.model.eq('A2')]
    scope_dev=scoped[scoped.fold.eq('dev')&scoped.model.eq('A2')]
    mae=points[points.fold.eq('dev')].pivot(index='model',columns='horizon',values='macro_mae').reindex(methods)
    labels={'CLIM':'Khí hậu','PERSISTENCE':'Persistence','GFS':'GFS nguyên bản','A0':'LightGBM A0',
            'A1':'LightGBM A1','A2':'LightGBM A2','A3':'LightGBM A3','GRU_A2':'GRU A2'}
    fig,ax=plt.subplots(figsize=(10.5,5))
    for offset,(trained,color) in enumerate([(20,'#3f7397'),(57,'#2a9d8f')]):
        p=scoped[(scoped.fold=='dev')&(scoped.model=='A2')&(scoped.evaluation_cohort=='original20')&(scoped.trained_stations==trained)].sort_values('horizon')
        bars=ax.bar(np.arange(3)+(offset-.5)*.3,p.macro_mae,width=.29,color=color,label=f'Train/cal {trained} trạm')
        ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=9)
    ax.set_xticks(np.arange(3),['Ngày 1','Ngày 2','Ngày 3']);ax.set_ylabel('Macro-MAE (mm cho tổng 24h)')
    ax.set_title('Đánh giá trên cùng 20 trạm và cùng thời điểm của năm 2024')
    ax.legend();ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout();fig.savefig(out/'matched_original20.png',dpi=180);plt.close(fig)
    lines=['# Mở rộng dự báo ngắn hạn từ 20 lên 57 trạm','',
        '**Đã mở rộng tập huấn luyện chính lên 57 trạm**, bổ sung 37 trạm đã có trong nguồn. Không phải lắp thêm trạm '
        'hay lấy dữ liệu toàn Việt Nam. Tất cả thuộc danh mục Vrain nhóm Đà Nẵng đang dùng.','',
        '## Vì sao 57, chưa phải 86?','',
        '| Nhóm | Số trạm | Trạng thái |','|---|---:|---|',
        '| Giữ tiêu chuẩn train của pilot | 57 | ≥365 ngày đầy đủ và ≥30 ngày ≥1mm trong2021–2022; đưa vào bản mở rộng |',
        '| Có mẫu train nhưng lịch sử ngắn hơn | 22 | Có thể làm phân tích mở rộng riêng; chưa gộp vào nhóm chính |',
        '| Có lịch sử nhưng chưa có cửa sổ train hợp lệ | 3 | Chưa đưa vào đánh giá các trạm đã biết |',
        '| Chỉ có trong danh mục hiện hành | 4 | Chưa có lịch sử từ nguồn2021–2024 đang dùng |','',
        f"Nhóm57có {cohort['selected_train_day_range'][0]}–{cohort['selected_train_day_range'][1]} ngày train đầy đủ. "
        f"Tuy nhiên, {cohort['stations_below_30_train_weekly_windows']} trạm có dưới30cửa sổ train theo lịch7ngày "
        f"(ít nhất{cohort['min_train_weekly_windows']}). Đủ tổng số ngày không đồng nghĩa chuỗi liên tục hoặc chất lượng cảm biến đã được chứng nhận.",'',
        '## Đã thực hiện','',
        '- Dùng lại GFS đã trích cho82vịtrí; không tải lại toàn bộ dữ liệu GFS. Có tải kiểm tra một số thông điệp để replay độc lập.',
        '- Giữ lịch208issue mỗi7ngày, cùng đặc trưng A0–A3, hyperparameter, seed17/29/43 và split; không mở2025.',
        '- Huấn luyện LightGBM A0–A3 trên57trạm; chạy GRU theo gatecal đã định trước. Khí hậu, persistence và GFS là các đối chứng.',
        '- Giữ nguyên pilot20trạm. Mở rộng là phiên bản riêng, có protocol, dataset, model, kết quả và checksum riêng.','',
        '| Phần | Mẫu trạm–issue | Dòng ba hạn |','|---|---:|---:|']
    for fold in ['train','cal','dev']:
        n=audit['split_rows'][fold];lines.append(f'| {fold} | {n//3:,} | {n:,} |')
    lines+=['','Mỗi mẫu dự báo ba lượng24hriêng tại cùng trạm; cutoffmưa18h choissue19h. '
        'GFS00UTC cung cấp ba cửa sổ19–19h. MọiA dùng cùng mẫu. Dữ liệu trạm thiếu chỉ loại mẫu của chính trạm đó.','',
        '## Kết quả trên toàn57trạm, phần phát triển2024','',
        'Macro-MAE đồng trọng số giữa trạm, nhỏ hơn tốt hơn. In đậm là thấp nhất trong cột; không tự khẳng định khác biệt có ý nghĩa thống kê.','',
        '| Phương pháp | Ngày1 mm | Ngày2 mm | Ngày3 mm |','|---|---:|---:|---:|']
    for method in methods:
        cells=[f'**{mae.loc[method,h]:.2f}**' if np.isclose(mae.loc[method,h],mae[h].min()) else f'{mae.loc[method,h]:.2f}' for h in [1,2,3]]
        lines.append('| '+labels[method]+' | '+' | '.join(cells)+' |')
    lines+=['','**Không so trực tiếp bảng57trạm với điểm trung bình20trạm cũ để kết luận mô hình tốt lên hoặc kém đi.** '
        'Các trạm mới có độ khó và lịch sử khác nhau. Phải giữ cùng đối tượng đánh giá.','',
        '## So sánh công bằng trên đúng20trạm ban đầu','',
        'Đã xác minh nhãn, toàn bộ32đầu vào A3, split và khóa(trạm,issue,hạn) giống nhau. '
        'So sánh dưới đây mở rộng cả dữ liệu train và cal, giữ thiết lập mô hình; không phải chỉ tăng dữ liệu train đơn độc.','',
        '| Mô hình A2 | Ngày1 mm | Ngày2 mm | Ngày3 mm |','|---|---:|---:|---:|']
    for trained in [20,57]:
        p=scoped[(scoped.fold=='dev')&(scoped.model=='A2')&(scoped.evaluation_cohort=='original20')&(scoped.trained_stations==trained)].set_index('horizon')
        lines.append(f'| Train/cal{trained}trạm; đánh giá cùng20trạm | '+' | '.join(f'{p.loc[h,"macro_mae"]:.2f}' for h in [1,2,3])+' |')
    lines+=['','| Ngày | MAE57−MAE20 mm | CI95% mm |','|---|---:|---|']
    for r in common_a2.sort_values('horizon').itertuples():
        lines.append(f'| {r.horizon} | {r.mae_difference:.3f} | [{r.ci95_low:.3f}; {r.ci95_high:.3f}] |')
    lines+=['','Số âm có lợi cho bản mở rộng. CI bao gồm0 thì chưa đủ bằng chứng cải thiện ổn định. '
        'Bootstrap theo khối4issue liên tiếp, giữ các trạm trong cùng đợt. Không dùng20và57như hai mẫu độc lập.','',
        '**Diễn giải kết quả:** trên cùng20trạm, điểm MAE A2 ngày1 giảm, ngày2 gần như ngang và ngày3 tăng '
        'ở bản train/cal57trạm. Các CI chênh lệch vẫn chứa0. Vì vậy, mở rộng phạm vi thành công chưa đồng nghĩa '
        'tăng độ chính xác ổn định; cũng chưa đủ để kết luận mô hình mở rộng chắc chắn kém hơn.','',
        '## Đọc giới hạn đúng phạm vi','',
        '- Tăng số trạm giúp mở rộng phạm vi, chưa bảo đảm mọi trạm hoặc mọi chỉ số tốt hơn. Đọc cảRMSE/Bias/BS/BSS/CSI/POD/FAR trong CSV.',
        '- Lịch vẫn mỗi7ngày, chưa phải dự báo hằng ngày đầy đủ. Số năm và các đợt thời tiết không tăng; nhiều trạm cùng trận mưa không là nhiều mùa độc lập.',
        '- 79trạm có cửa sổtrain là giới hạn rộng hơn của nguồn hiện có, nhưng22trạm bổ sung có lịch sử ngắn. Có thể thử mô hình chung ở nhóm này với protocol riêng, không tự gọi tất cả86trạm đã sẵn sàng.',
        '- Chưa đánh giá tổng quát sang trạm chưa thấy. Các37trạm bổ sung đã có dữ liệu train trong bản57; đây là kiểm định tương lai ở trạm đã biết.',
        '- Trễtrạm1h/GFS8h vẫn là giả định. Có7chu kỳ đầu2021có timestamp sửa/chép archive sauissue; không suy ra đó là thờiđiểmpháthànhgốc.',
        '- Dữ liệu qua kiểm tra ghép/cấu trúc, chưa chứng nhận cảm biến, vị trí lịch sử hoặc độtrễ vận hành. DEM là proxy, không phải cao độ khảo sát.',
        '- 2024 là phần đánh giá phát triển;2025vẫn giữ kín,2026khôngfit/tuning.','',
        '## File và tái tạo','',
        f'Dataset private: `data/processed/{NAME}/gfs_vrain_pilot.parquet`. Mô hình và per-timepredictions ở `data/operational/{NAME}/`.','',
        'Chạy `scripts/prepare_gfs_station_expansion.py`; đặt `PBL6_GFS_EXPERIMENT=gfs_station_57_2026_11_10` '
        'trước các script build/validate/run/GRU/verify. Nguồn GFS dùng chung chỉ đọc. Publisher của bản mở rộng là `scripts/publish_gfs_station_expansion.py`.','',
        '[Protocol](protocol.json), [QC/cohort](cohort_expansion_audit.json), [ghép mẫu](dataset_audit.json), '
        '[kiểm tra nguồn](verification.json), [replay mô hình](model_verification.json), '
        '[toàn bộ nhóm đánh giá](cohort_scope_metrics.csv), [so sánh ghép cặp20trạm](matched_original20_bootstrap.csv), '
        '[lượng mưa](point_metrics.csv), [xác suất](probability_metrics.csv), [sự kiện](event_metrics.csv).','']
    markdown='\n'.join(lines)
    markdown=''.join(part if i%2 else readable(part) for i,part in enumerate(re.split(r'(`[^`]*`)',markdown)))
    (out/'BAO_CAO_MO_RONG.md').write_text(markdown,encoding='utf8')
    result=dict(status='57_station_expansion_complete',stations=57,added_stations=37,
        wider_candidate_stations_with_train_windows=79,not_in_main_due_short_history=22,
        cadence_days=7,original_experiment_unchanged=True,
        complete_station_issue_counts={fold:audit['split_rows'][fold]//3 for fold in ['train','cal','dev']},
        models_completed=methods,matched_original20_rows=len(matched),same_labels_and_all_inputs_verified=True,
        matched_A2_development=common_a2.to_dict('records'),
        test2025_read=False,full_daily_experiment_complete=False)
    (out/'result_summary.json').write_text(json.dumps(result,indent=2)+'\n')
    doc=Document();s=doc.sections[0];s.page_width=Cm(21);s.page_height=Cm(29.7)
    s.top_margin=s.bottom_margin=Cm(1.6);s.left_margin=s.right_margin=Cm(1.6)
    normal=doc.styles['Normal'];normal.font.name='Calibri';normal.font.size=Pt(10)
    normal.paragraph_format.space_after=Pt(5)
    doc.add_heading('MỞ RỘNG DỰ BÁO NGẮN HẠN: 57 TRẠM',0)
    doc.add_paragraph('Đã bổ sung37trạm có sẵn trong nguồn; không phải lắp thêm trạm hoặc dữ liệu toàn Việt Nam. Giữ nguyên pilot20trạm, tạo thí nghiệm mở rộng riêng.')
    doc.add_heading('Vì sao dùng57trạm?',1)
    doc.add_paragraph('57trạm đạt cùng tiêu chuẩn train: ít nhất365ngày đầy đủ và30ngày≥1mm trong2021–2022. Dữ liệu thực tế479–728ngày. Có22trạm khác có mẫutrain nhưng lịch sử ngắn;3trạm chưa cótrain và4vịtrí chỉ có ở danh mục mới. Vì vậy không coi đủ86trạm đã sẵn sàng.')
    doc.add_paragraph('Bản57có5.032/2.582/2.782mẫu train/cal/dev, mỗi mẫu ba nhãn ngày. Lịch vẫn208issue mỗi7ngày trong2021–2024, chưa là thí nghiệm hằng ngày. NguồnGFS82vịtrí đã có, không cần tải lại toàn bộ.')
    doc.add_heading('Macro-MAE trên toàn57trạm, năm2024',1)
    table=doc.add_table(rows=1,cols=4);table.style='Light Shading Accent 1'
    for c,t in zip(table.rows[0].cells,['Phương pháp','Ngày1mm','Ngày2mm','Ngày3mm']):c.text=t
    for method in methods:
        cells=table.add_row().cells;cells[0].text=labels[method]
        for h in [1,2,3]:
            r=cells[h].paragraphs[0].add_run(f'{mae.loc[method,h]:.2f}');r.bold=bool(np.isclose(mae.loc[method,h],mae[h].min()))
    doc.add_paragraph('MAE trung bình giữa trạm; nhỏ hơn tốt hơn. In đậm là thấp nhất trong cột. Không so trực tiếp điểm trung bình57trạm với20trạm vì đối tượng đánh giá khác nhau.')
    doc.add_heading('So trên cùng20trạm ban đầu',1)
    doc.add_picture(str(out/'matched_original20.png'),width=Cm(17.4))
    doc.add_paragraph('Nhãn,32đầu vào,split và các thời điểm đã được kiểm tra trùng khớp. So sánh mở rộng cả train và cal; các thiết lập mô hình giữ nguyên. CI95% ghép cặp có trong bảngMarkdown/CSV; CI chứa0 chưa chứng minh cải thiện ổn định.')
    doc.add_paragraph('Trên cùng20trạm cũ, MAE A2 ngày1 giảm, ngày2 gần như ngang, ngày3 tăng. Cả ba CI chênh lệch còn chứa0. Mở rộng số trạm chưa bảo đảm tăng độ chính xác ổn định; đây không phải kết luận bản mở rộng chắc chắn kém hơn.')
    doc.add_heading('Giới hạn',1)
    doc.add_paragraph('Hai trạm có dưới30cửa sổ train theo lịch7ngày dù đủ tổng số ngày; mô hình học chung nhưng không coi mọi trạm ngang nhau về lịch sử. Đọc thêmRMSE/Bias/BSS/POD/FAR. Thêm trạm không tạo thêm năm/mùa khí hậu hoặc bảo đảm điểm tốt hơn.')
    doc.add_paragraph('2025giữkín;2024chưa là testcuối;2026khôngtuning. Trễmưa1h vàGFS8h là giả định chưa xác minh đầy đủ. Dữ liệu/tọađộ/model/per-timeprediction không đưa lênGitHub công khai.')
    doc.core_properties.title='Mở rộng dự báo mưa ngắn hạn lên57trạm'
    paragraphs=list(doc.paragraphs)+[p for t in doc.tables for row in t.rows for cell in row.cells for p in cell.paragraphs]
    for p in paragraphs:
        for run in p.runs:run.text=readable(run.text)
    doc.save(out/'BAO_CAO_MO_RONG.docx')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
