"""Tổng hợp đầy đủ 3fold; không chọn/chấm thêm mẫu hoặc điều chỉnh model."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=ROOT/'reports/domain_screen_danang'
SOURCES=[f'{learner}_{cfg}' for learner in ['BiLSTM','LightGBM'] for cfg in ['BASE','RAW','DOMAIN']]
COLORS=['#94a3b8','#2563eb','#d97706','#64748b','#0d9488','#be123c']
def table(df,cols,labels=None):
    labels=labels or cols
    lines=['| '+' | '.join(labels)+' |','| '+' | '.join(['---']*len(cols))+' |']
    for _,r in df.iterrows():
        values=[f'{r[c]:.3f}' if isinstance(r[c],(float,np.floating)) else str(r[c]) for c in cols]
        lines.append('| '+' | '.join(values)+' |')
    return '\n'.join(lines)

def main():
    scores=pd.read_csv(OUT/'scores.csv')
    main=scores[(scores.season=='may_oct')&(scores.window=='0-3h')&(scores.source.isin(SOURCES))].copy()
    if len(main)!=18 or set(main.year)!={2021,2022,2023}:raise ValueError('Chưa đủ18hàng6cấu hình/3fold')
    run=json.loads((OUT/'run.json').read_text(encoding='utf-8'))
    if len(run['history'])!=36:raise ValueError('Chưa đủ27NN+9LightGBM')
    comparisons=json.loads((OUT/'paired_bootstrap.json').read_text(encoding='utf-8'))
    decisions=[]
    for learner in ['BiLSTM','LightGBM']:
        for year in [2021,2022,2023]:
            raw=main[(main.source==learner+'_RAW')&(main.year==year)].iloc[0]
            dom=main[(main.source==learner+'_DOMAIN')&(main.year==year)].iloc[0]
            boot=next(x for x in comparisons if x['year']==year and x['source_a']==learner+'_DOMAIN' and x['metric'].startswith('CSI'))
            decisions.append(dict(learner=learner,year=year,delta_csi=dom.CSI_prob_10-raw.CSI_prob_10,
                ci_low=boot['ci_low'],ci_high=boot['ci_high'],
                relative_bs1_reduction=(raw.BS_1-dom.BS_1)/raw.BS_1,
                relative_bs10_reduction=(raw.BS_10-dom.BS_10)/raw.BS_10,
                practical_signal=bool(dom.CSI_prob_10-raw.CSI_prob_10>=.03 or (raw.BS_1-dom.BS_1)/raw.BS_1>=.05)))
    decision=pd.DataFrame(decisions)
    decision.to_csv(OUT/'domain_decisions.csv',index=False)
    means=main.groupby('source')[['CSI_prob_10','BSS_1','BSS_10','RMSE','FAR_prob_10']].mean().reindex(SOURCES)
    means.to_csv(OUT/'annual_means.csv')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(13,5))
    for ax,metric,title in [(axes[0],'CSI_prob_10','Quyết định mưa ≥10 mm / 3 h'),(axes[1],'BSS_1','Xác suất mưa ≥1 mm / 3 h')]:
        for i,(source,color) in enumerate(zip(SOURCES,COLORS)):
            sub=main[main.source==source].sort_values('year')
            ax.plot(sub.year,sub[metric],marker='o',color=color,label=source.replace('_',' '))
        ax.set_xticks([2021,2022,2023]);ax.set_xlabel('Năm validation lịch sử');ax.set_ylabel(metric.replace('_prob_10','').replace('_1',''))
        ax.set_title(title);ax.grid(alpha=.15)
    handles,legend_labels=axes[1].get_legend_handles_labels()
    fig.legend(handles,legend_labels,fontsize=8,loc='lower center',bbox_to_anchor=(.5,.005),ncol=3)
    fig.suptitle('Đà Nẵng: cùng mẫu, cùng nguồn — tháng 5–10, 30 ô',fontsize=14)
    fig.tight_layout(rect=[0,.14,1,1])
    fig.savefig(OUT/'model_comparison.png',dpi=170);fig.savefig(OUT/'model_comparison.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),sharey=True)
    for ax,learner in zip(axes,['BiLSTM','LightGBM']):
        sub=decision[decision.learner==learner]
        for _,r in sub.iterrows():
            ax.plot([r.ci_low,r.ci_high],[r.year,r.year],color='#2563eb',lw=3)
            ax.scatter(r.delta_csi,r.year,color='#2563eb',s=55)
        ax.axvline(0,color='#64748b',ls='--');ax.axvline(.03,color='#d97706',ls=':',label='Mốc thực dụng +0,03')
        ax.set_title(learner);ax.set_yticks([2021,2022,2023]);ax.set_xlabel('ΔCSI: DOMAIN − RAW');ax.grid(alpha=.12)
    axes[0].set_ylabel('Năm validation')
    handles,legend_labels=axes[1].get_legend_handles_labels()
    fig.legend(handles,legend_labels,fontsize=8,loc='lower center',bbox_to_anchor=(.5,.005))
    fig.suptitle('Khoảng tin cậy 95% — bootstrap khối 5 ngày, 1.000 lần',fontsize=12)
    fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(OUT/'domain_effect_ci.png',dpi=170);fig.savefig(OUT/'domain_effect_ci.svg');plt.close(fig)
    label=json.loads((OUT/'label_audit.json').read_text(encoding='utf-8'))
    fig,ax=plt.subplots(figsize=(6.5,4))
    correction=label['correction_dependence']
    vals=[100*r['fraction_gc_volume_raw_le_001'] for r in correction]
    bars=ax.bar(['Tháng 5–10','Tháng 11–2','Tháng 3–4'],vals,color=['#2563eb','#d97706','#94a3b8'])
    ax.bar_label(bars,labels=[f'{v:.1f}%' for v in vals],padding=4)
    ax.set_ylim(0,85);ax.set_ylabel('% tổng mưa GC ở giờ raw ≤0,01 mm')
    ax.set_title('Nhãn hiệu chỉnh phụ thuộc nguồn theo mùa\n93 ô Đà Nẵng, 2021–2023')
    fig.tight_layout();fig.savefig(OUT/'label_correction.png',dpi=170);plt.close(fig)
    regimes=pd.read_csv(OUT/'regimes.csv')
    regime_main=regimes[regimes.source=='BiLSTM_RAW'].copy()
    regime_main['event_rate']=regime_main.n_obs_events/regime_main.n
    regime_main['sample_share']=regime_main.n/regime_main.groupby('year').n.transform('sum')
    regime_main['event_share']=regime_main.n_obs_events/regime_main.groupby('year').n_obs_events.transform('sum')
    regime_main[['year','regime','n','n_obs_events','event_rate','sample_share','event_share']].to_csv(OUT/'regime_event_rates.csv',index=False)
    fig,ax=plt.subplots(figsize=(8,4.5))
    for i,(regime,color) in enumerate([('NE','#2563eb'),('W','#d97706'),('other','#94a3b8')]):
        sub=regime_main[regime_main.regime==regime].sort_values('year')
        ax.bar(np.arange(3)+(i-1)*.23,sub.event_rate*100,width=.22,color=color,label=regime)
    ax.set_xticks(np.arange(3),[2021,2022,2023]);ax.set_ylabel('% cửa sổ có mưa ≥10 mm/3h')
    ax.set_title('Tần suất mưa ≥10 mm/3 h theo gió 850 hPa quá khứ')
    ax.legend(title='Proxy hướng gió');fig.tight_layout();fig.savefig(OUT/'regime_event_rates.png',dpi=170);plt.close(fig)
    positive={l:int(decision[decision.learner==l].practical_signal.sum()) for l in ['BiLSTM','LightGBM']}
    summary=dict(completed=True,nn_runs=27,lightgbm_pipelines=9,lightgbm_heads=135,eval_windows=int(sum(f['eval_n'] for f in run['folds'])),
                 practical_domain_years=positive,decisions=decisions,tests_passed=73,test_2025_scored=False)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    brief=ROOT/'reports/research_rainfall/brief_giang_vien_2026_10_14.md'
    text=[
    '# Kết quả thực hiện và đề xuất trao đổi ngày 14/10/2026',
    '',
    '## Kết luận cần trình bày trước',
    '',
    'Đã thực hiện phép so có kiểm soát trên dữ liệu Đà Nẵng, gồm ba năm validation lịch sử, Bi-LSTM ba seed và LightGBM. Phần hiểu biết địa phương được kiểm tra bằng cách thêm biểu diễn gió–ẩm–địa hình vào chính các biến khí tượng thô đó; không quy lợi ích thêm nguồn dữ liệu cho biểu diễn vật lý.',
    '',
    'Đây là kết quả nghiên cứu hồi cứu có code và checkpoint tái lập. Chưa xác nhận vận hành; test 2025 chưa mở. Đầu xác suất và đầu lượng mưa trả lời hai mục tiêu khác nhau, nên giữ riêng hai loại CSI.',
    '',
    '## Những gì đã làm và kiểm tra',
    '',
    '- 27 lượt Bi-LSTM (3 cấu hình × 3 năm × 3 seed), 9 pipeline LightGBM (135 đầu), cố định 30.000 mẫu train mỗi fold; '+str(summary['eval_windows'])+' cửa sổ evaluation, 30 ô chọn theo địa hình/khoảng cách biển.',
    '- Train/cal/eval cuốn chiếu; chuẩn hóa chỉ trên train; RAW/DOMAIN cùng số tham số và cùng cửa sổ. Tương lai chỉ gồm lịch. Loss khác giữa NN/cây nên so learner có giới hạn.',
    '- 73 kiểm tra đạt. Suy luận CPU từ checkpoint/normalizer/Platt đã khớp dự báo CUDA đã lưu trong sai số số học nhỏ; API HTTP đã trả dự báo thật từ checkpoint ở chế độ archive.',
    '- Đã lấy snapshot forecast và kiểm tra hợp đồng khí tượng cho 93/93 ô; bộ ghi theo giờ chạy trong 2,1 giờ. NRT quan trắc và T-OPS chưa hoàn tất.',
    '',
    '## Kết quả chính',
    '',
    'Tháng 5–10, tổng mưa 0–3 giờ; CSI ở đây là quyết định từ xác suất, ngưỡng chọn năm calibration trước evaluation. BSS tham chiếu khí hậu ô/tháng/giờ chỉ học trên train; BSS dương là tốt hơn tham chiếu đó, chưa phải tốt hơn ECMWF.',
    '',
    table(main[['year','source','CSI_prob_10','CSI_amount_10','BSS_1','BSS_10','FAR_prob_10','RMSE']],
          ['year','source','CSI_prob_10','CSI_amount_10','BSS_1','BSS_10','FAR_prob_10','RMSE'],
          ['Năm','Cấu hình','CSI xác suất ≥10','CSI lượng mưa ≥10','BSS ≥1','BSS ≥10','FAR ≥10','RMSE mm/3h']),
    '',
    '![So sánh theo năm](../domain_screen_danang/model_comparison.png)',
    '',
    'Không so trực tiếp mức tăng với pilot cũ: lượt này giữ một tập 30.000 mẫu train cố định qua epoch, còn pilot cũ lấy các tập con khác qua epoch và dùng cấu hình/cửa sổ khác.',
    '',
    '## Biểu diễn vật lý có giúp ổn định không?',
    '',
    table(decision,['learner','year','delta_csi','ci_low','ci_high','relative_bs1_reduction'],
          ['Learner','Năm','ΔCSI DOMAIN−RAW','CI thấp','CI cao','BS ≥1 giảm tương đối']),
    '',
    'Cột giảm BS là tỷ lệ, ví dụ 0,05 nghĩa là giảm 5%; âm nghĩa là xấu hơn. Tiêu chí thực dụng đặt trước: ΔCSI ≥0,03 hoặc BS ≥1 giảm ≥5%, lặp ít nhất 2/3 năm và xét bất định/chỉ số còn lại. Số năm đạt tín hiệu: Bi-LSTM '+str(positive['BiLSTM'])+'/3, LightGBM '+str(positive['LightGBM'])+'/3. Chạm ngưỡng này chỉ là sàng lọc, không thay xác nhận độc lập.',
    '',
    '![Hiệu số và CI](../domain_screen_danang/domain_effect_ci.png)',
    '',
    'Nếu tín hiệu không lặp qua năm/learner, giữ RAW và BASE làm ứng viên nguồn đơn giản hơn; DOMAIN chỉ là giả thuyết đã thử, chưa bắt buộc đưa vào app. Nếu có tín hiệu lặp, vẫn cần tăng dữ liệu và kiểm tra bằng forecast thật trước khi chọn checkpoint.',
    '',
    '## Đóng góp domain ngoài việc thêm cột',
    '',
    'Audit cho thấy cube và Earth Engine tại ô chứa trạm khớp tổng ngày; 1.042 ngày chung 2021–2023 đối chiếu GSOD. GC có CSI ngày ≥50 mm 0,438 tại trạm này, raw 0,246 và ERA5 0,352. Đây là đánh giá nguồn nhãn, không phải điểm mô hình; GSOD có thể tham gia hiệu chỉnh GC nên không bảo đảm độc lập.',
    '',
    '67,6% tổng GC mùa tháng 11–2 nằm ở giờ raw ≤0,01 mm, so với 20,8% mùa tháng 5–10. Vì vậy chấm giờ/3 giờ trong mùa 5–10 và tách 6 giờ mùa đông. Chỉ báo này phản ánh phụ thuộc hiệu chỉnh, không chứng minh thời điểm mưa thật sai; cần nhãn trạm theo giờ để kết luận mạnh hơn.',
    '',
    '![Nhãn theo mùa](../domain_screen_danang/label_correction.png)',
    '',
    'Hiểu domain còn giúp lựa chọn nguồn và kiểm tra tính khả thi: IFS 9 km thiếu trường 850; IFS 0,25° có 850 nhưng thiếu CIN trong probe. Đã làm chuyển mây %→0–1, hướng gió→u/v và q850 từ T/RH; dữ liệu thiếu/đơn vị sai bị từ chối. Chưa coi q suy ra là tương đương q ERA5 hoàn toàn.',
    '',
    '## Ý nghĩa và giới hạn của tài liệu',
    '',
    'Bài [PLOS One 2026](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0342825) tại Trung Bộ là bằng chứng gần nhất: bộ biến theo khí tượng đạt CSI 0,55 so 0,53, nhưng là ước lượng cùng giờ với Himawari/trạm, không dự báo tương lai 6 giờ. Cơ chế địa hình và hoàn lưu trong [nghiên cứu Trung Bộ 2023](https://onlinelibrary.wiley.com/doi/full/10.1155/2023/7256634) hỗ trợ giả thuyết gió–ẩm; không bảo đảm mức tăng mô hình. Chín nguồn và giới hạn chuyển giao nằm trong [literature_domain_review.md](literature_domain_review.md).',
    '',
    'Một phép so có ý nghĩa cho PBL khi câu hỏi, đối chứng, chia thời gian và hệ quả lựa chọn app rõ ràng. Kết quả âm giúp loại một thiết kế và tiết kiệm phạm vi; không thể hứa tạo chênh lệch lớn bằng cách thử nhiều mô hình. Đóng góp hiện có là pipeline đánh giá cùng mẫu, chẩn đoán nhãn theo mùa, phép thử vật lý và đoạn nối từ checkpoint tới API.',
    '',
    '## Hướng thực hiện và nội dung xin góp ý',
    '',
    'Tên đề tài đề xuất: **Dự báo xác suất mưa cực ngắn tại Đà Nẵng: đánh giá đóng góp dữ liệu khí tượng và tương tác gió–ẩm–địa hình, triển khai ứng dụng dự báo**. Trọng tâm trước là một vùng và hạn 6 giờ; sản phẩm TFT 1–3 ngày ở giai đoạn sau.',
    '',
    'Kế hoạch cụ thể, đầu ra và điều kiện chuyển tiếp: [execution_plan.md](execution_plan.md). Xin góp ý về phạm vi một vùng/hạn 6 giờ; ưu tiên xác suất và sự kiện mưa; khả năng tiếp cận nhãn trạm theo giờ; và mức bằng chứng cần có trước mở rộng kiến trúc. Đây là đề nghị trao đổi trực tiếp của nhóm, chưa gửi cho giảng viên.',
    '',
    'Dữ liệu/checkpoint/snapshot ngoài Git. [Thiết kế đầy đủ](../domain_screen_danang/README.md), [scores.csv](../domain_screen_danang/scores.csv), [CI bootstrap](../domain_screen_danang/paired_bootstrap.json), [manifest run](../domain_screen_danang/run.json).'
    ]
    text.insert(6, 'Bi-LSTM thêm biểu diễn vật lý tăng CSI quyết định ≥10 mm/3 h so RAW lần lượt 0,051 / 0,007 / 0,031 ở 2021 / 2022 / 2023. Hai năm đạt mốc thực dụng +0,03, nhưng cả ba CI95% chứa0 và LightGBM chưa cho lợi ích lặp đủ lớn. Giữ DOMAIN cùng RAW làm ứng viên kiểm định tiếp, chưa chọn model cuối cho app. Đầu lượng mưa vẫn thiên thấp; không coi tăng CSI đầu xác suất là cải thiện tương đương của lượng mm.')
    text.insert(7,'')
    # Phân tích cohort đã đặt trước, mô tả; không kiểm định nhân quả.
    loc=text.index('## Ý nghĩa và giới hạn của tài liệu')
    cohort_text=['## Tín hiệu khí tượng địa phương trong dữ liệu','',
        table(regime_main,['year','regime','n','n_obs_events','event_rate','sample_share','event_share'],
              ['Năm','Gió','Số mẫu','Sự kiện ≥10','Tần suất sự kiện','Tỷ lệ mẫu','Tỷ lệ sự kiện']),'',
        'Các tỷ lệ trong bảng ở thang0–1. Nhóm NE chỉ chiếm khoảng12–18% mẫu nhưng46–65% sự kiện mưa mạnh. Đây là bằng chứng mô tả để ưu tiên gió–ẩm tầng thấp; chưa chứng minh nhân quả vì còn khác tháng/đợt mưa/địa hình. NE chỉ là u/v trung bình6h đều<−0,5m/s, không phải xác định đợt không khí lạnh hoặc bão.', '',
        '![Tần suất sự kiện theo hướng gió](../domain_screen_danang/regime_event_rates.png)','',
        'DOMAIN thêm bốn proxy cùng lúc nên chưa biết proxy địa hình đóng góp riêng bao nhiêu. Tiếp theo cần phép bỏ từng thành phần; tương tác gió với gradient địa hình hai chiều là giả thuyết tốt hơn hướng NE cố định, nhưng phải cung cấp cùng gradient cho đối chứng RAW. Không thêm dữ liệu địa hình mới chỉ ở DOMAIN rồi gọi là lợi ích biểu diễn.','']
    text[loc:loc]=cohort_text
    brief.write_text('\n'.join(text)+'\n',encoding='utf-8')
    for artifact in OUT.glob('*.svg'):
        artifact.write_text('\n'.join(line.rstrip() for line in artifact.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
