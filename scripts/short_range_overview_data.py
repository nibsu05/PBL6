"""Read frozen aggregate evidence; this presentation never trains or rescores models."""
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
NAME='short_range_comprehensive_2026_11_18'
PUBLIC=ROOT/'reports'/NAME
PRIVATE=ROOT/'data/operational'/NAME
STUDIES=dict(final='gfs_station_final_2026_11_17',temporal='gfs_temporal_2026_11_17',window='gfs_training_window_2026_11_18')

REFERENCES={
 'P1':dict(short='Zhang & Ye · 2021 · JHM',title='Machine Learning for Precipitation Forecasts Postprocessing: Multimodel Comparison and Experimental Investigation',
    url='https://journals.ametsoc.org/view/journals/hydr/22/11/JHM-D-21-0096.1.xml',doi='10.1175/JHM-D-21-0096.1',status='Bài tạp chí bình duyệt',
    verified='Mục tóm tắt và các đoạn phương pháp/kết quả được lập chỉ mục trên trang nhà xuất bản; mở trực tiếp toàn văn trả HTTP403.',
    use='Cơ sở dùng LightGBM để hậu xử lý dự báo mưa; không dùng điểm số bài báo để xếp hạng dự án.'),
 'P2':dict(short='Salehi & Salehi Neyshabouri · 2025',title='A hybrid deep learning framework for improving short-term precipitation forecasts',
    url='https://doi.org/10.1016/j.envsoft.2025.106635',doi='10.1016/j.envsoft.2025.106635',status='Environmental Modelling & Software, bài bình duyệt',
    verified='Đã kiểm tra nội dung tóm tắt/phương pháp công khai được lập chỉ mục ở ScienceDirect và kho mã của tác giả; trang toàn văn trả HTTP403.',
    use='GRU mã hóa mưa quá khứ, ghép dự báo nền CNRFC và lịch để dự báo mưa ngày; nguồn nhãn PRISM khác Vrain.'),
 'P3':dict(short='Iwase & Takenawa · 2026 · preprint',title='Improvements to the post-processing of weather forecasts using machine learning and feature selection',
    url='https://arxiv.org/html/2604.19340v1',doi='10.48550/arXiv.2604.19340',status='Bản thảo arXiv v1, chưa coi là bằng chứng bình duyệt',
    verified='Đã đọc bản HTML phương pháp và tóm tắt: LightGBM, MSM/JMA, 18 vị trí, nhãn mưa3h, đầu vào lân cận và Tweedie.',
    use='Tham khảo lựa chọn biến/loss; khác kỳ đo và nguồn dự báo nên không so RMSE hoặc POD trực tiếp.'),
 'P4':dict(short='Gneiting · 2011 · JASA',title='Making and Evaluating Point Forecasts',
    url='https://arxiv.org/abs/0912.0902',doi='10.1198/jasa.2011.r10138',status='Bài phương pháp, bản thảo tác giả công khai',
    verified='Đã kiểm tra tóm tắt tác giả trên arXiv; nội dung nhấn mạnh phải khớp scoring function với đại lượng cần dự báo.',
    use='Cơ sở phân biệt mean/RMSE với median/MAE; lựa chọn metric trước khi xem kết quả.'),
 'D1':dict(short='NOAA/NCEI · GFS',title='Global Forecast System (GFS)',
    url='https://www.ncei.noaa.gov/products/weather-climate-models/global-forecast',status='Tài liệu cơ quan cung cấp',
    verified='Đã kiểm tra trang sản phẩm chính thức: GFS cung cấp dự báo nhiều trường khí tượng và sản phẩm0,25°.',
    use='Giải thích vai trò nguồn GFS; không dùng mô tả sản phẩm để khẳng định thời điểm phát hành lịch sử từng file đã được chứng minh.'),
 'D2':dict(short='ECMWF/Copernicus · reanalysis',title='Climate reanalysis',
    url='https://climate.copernicus.eu/climate-reanalysis',status='Tài liệu cơ quan cung cấp',
    verified='Đã kiểm tra mô tả ERA5 tái phân tích, dữ liệu giờ trên lưới0,25° trong CDS.',
    use='Phân biệt tái phân tích với số đo trạm và bản dự báo được phát trước issue.'),
 'D3':dict(short='NOAA/MDL · MOS',title='Model Output Statistics',
    url='https://vlab.noaa.gov/web/mdl/mos',status='Tài liệu cơ quan dự báo',
    verified='Đã kiểm tra định nghĩa MOS là quan hệ thống kê giữa đầu ra mô hình và quan trắc.',
    use='Cơ sở đối chứng hậu xử lý đơn giản; MOS của dự án không phải tái hiện đầy đủ hệ thống MOS vận hành của NOAA.'),
 'P5':dict(short='Lim và cộng sự · 2021 · TFT',title='Temporal Fusion Transformers for interpretable multi-horizon time series forecasting',
    url='https://doi.org/10.1016/j.ijforecast.2021.03.012',status='International Journal of Forecasting, bình duyệt',
    verified='Đã kiểm tra tóm tắt gốc và định danh bài tạp chí; kiến trúc kết hợp đầu vào tĩnh, quá khứ và biết trước.',
    use='Giải thích TFT là ứng viên hợp lệ, chưa có đối chứng TFT trên bộ GFS–Vrain hiện tại để kết luận nó kém.'),
 'P6':dict(short='Zhou và cộng sự · 2021 · Informer',title='Informer: Beyond Efficient Transformer for Long Sequence Time-Series Forecasting',
    url='https://arxiv.org/abs/2012.07436',status='AAAI2021; bản thảo tác giả công khai',
    verified='Đã kiểm tra tóm tắt gốc về dự báo chuỗi dài và cơ chế ProbSparse.',
    use='Không mặc định kiến trúc chuỗi dài cần thiết cho7ngày lịch sử/3đầu ra; cũng không tuyên bố không khả thi khi chưa thử đúng dữ liệu.'),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def fmt(value,digits=3):
    return '—' if pd.isna(value) else f'{float(value):.{digits}f}'.replace('.',',')


class Evidence:
    def __init__(self):
        self.frames={};self.bindings=[];self.inputs={}
    def csv(self,study,name):
        rel=f'reports/{STUDIES[study]}/{name}.csv'
        if rel not in self.frames:
            self.frames[rel]=pd.read_csv(ROOT/rel);self.inputs[rel]=sha(ROOT/rel)
        return self.frames[rel]
    def js(self,relative):
        self.inputs[relative]=sha(ROOT/relative)
        return json.loads((ROOT/relative).read_text(encoding='utf-8'))
    def value(self,study,name,filters,column,digits=3):
        frame=self.csv(study,name);mask=pd.Series(True,index=frame.index)
        for key,value in filters.items():mask &= frame[key].eq(value)
        found=frame.loc[mask,column]
        if len(found)!=1:raise ValueError(f'Nonunique evidence {study}/{name}: {filters}/{column}: {len(found)}')
        number=found.iloc[0]
        if hasattr(number,'item'):number=number.item()
        shown=fmt(number,digits) if isinstance(number,(int,float)) and not isinstance(number,bool) else str(number)
        self.bindings.append(dict(file=f'reports/{STUDIES[study]}/{name}.csv',filters=filters,column=column,
            numeric_value=number,display=shown,digits=digits))
        return number,shown
    def point(self,study,scope,models,functional='mean',metric='macro_rmse'):
        rows=[];raw=[]
        for model,label in models:
            values=[];numbers=[]
            for h in (1,2,3):
                n,v=self.value(study,'point_metrics',dict(evaluation_set=scope,horizon=h,model=model,functional=functional),metric)
                values.append(v);numbers.append(n)
            rows.append([label]+values);raw.append(numbers)
        for j in range(3):
            best=min(r[j] for r in raw)
            for i,row in enumerate(raw):
                if abs(row[j]-best)<1e-10:rows[i][j+1]='**'+rows[i][j+1]+'**'
        return rows
    def probability(self,study,scope,models,threshold=50):
        rows=[]
        for model,label in models:
            row=[label]
            for h in (1,2,3):
                _,v=self.value(study,'probability_metrics',dict(evaluation_set=scope,horizon=h,model=model,threshold_mm=threshold),'macro_bss')
                row.append(v)
            rows.append(row)
        return rows
    def event_rows(self,study,scope,model):
        rows=[]
        for h in (1,2,3):
            filters=dict(evaluation_set=scope,horizon=h,model=model,threshold_mm=50,decision_rule='calibration_selected')
            vals=[]
            for col in ['cutoff','macro_pod','macro_far','macro_csi']:
                _,v=self.value(study,'event_metrics',filters,col,2 if col=='cutoff' else 3);vals.append(v)
            _,bss=self.value(study,'probability_metrics',dict(evaluation_set=scope,horizon=h,model=model,threshold_mm=50),'macro_bss')
            rows.append([f'Ngày {h}']+vals+[bss])
        return rows
