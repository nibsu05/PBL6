"""Editable research slides and notes from frozen aggregate evidence; no training."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from datetime import datetime,timezone
import html,json,re,zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from docx import Document
from docx.shared import Inches as DI,Pt as DP
from scripts.short_range_overview_data import PUBLIC,PRIVATE,STUDIES,REFERENCES,Evidence,fmt,sha,write_json
from scripts.short_range_overview_content import make_slides
from scripts.short_range_overview_notes import NOTES

NAVY='17364D';TEAL='087D89';GRAY='546A79';BG='F6F9FC';PALE='E8F2F5';AMBER='9A632B'


def readable(text):
    text=str(text);tokens=r'N[0-5]|T[0-3]|P[1-6]|D[1-3]|L2|p50|p1|log1p|LINEAR23|LINEAR6|ERA5'
    text=re.sub(r'('+tokens+r')(?=[a-zà-ỹ])',r'\1 ',text);protected={}
    def hold(match):
        key='ZZHOLD'+chr(65+len(protected))+'ZZ';protected[key]=match.group();return key
    text=re.sub(r'\b(?:'+tokens+r')\b|\b[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+\b',hold,text)
    text=re.sub(r'(?<=[A-Za-zÀ-ỹ])(?=\d)|(?<=\d)(?=[A-Za-zÀ-ỹ])',' ',text)
    for key,value in protected.items():text=text.replace(key,value)
    text=text.replace('mẫu/trạm–issue','mẫu trạm–issue')
    for a,b in [('GRUN3','GRU N3'),('GRUN5','GRU N5')]:text=text.replace(a,b)
    return text


def rich_parts(value):
    return [(x[2:-2],True) if x.startswith('**') and x.endswith('**') else (x,False)
        for x in re.split(r'(\*\*.*?\*\*)',readable(value)) if x]


class Deck:
    def __init__(self):
        self.p=Presentation();self.p.slide_width=Inches(13.333);self.p.slide_height=Inches(7.5)
    def rect(self,s,x,y,w,h,color=PALE):
        z=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
        z.fill.solid();z.fill.fore_color.rgb=RGBColor.from_string(color);z.line.fill.background();return z
    def text(self,s,x,y,w,h,value,size=22,color=NAVY,bold=False,url=None):
        box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w+.07),Inches(h));frame=box.text_frame
        frame.word_wrap=True;frame.margin_left=frame.margin_right=frame.margin_top=frame.margin_bottom=0
        for i,line in enumerate(str(value).split('\n')):
            p=frame.paragraphs[0] if i==0 else frame.add_paragraph();p.space_before=Pt(0);p.space_after=Pt(0)
            for text,isbold in rich_parts(line):
                r=p.add_run();r.text=text;r.font.name='Aptos';r.font.size=Pt(size);r.font.bold=bold or isbold;r.font.color.rgb=RGBColor.from_string(color)
                if url:r.hyperlink.address=url
        return box
    def table(self,s,headers,rows,widths=None,row_h=.65,size=20,y=1.82,x=.65,w=12.1):
        widths=widths or [w/len(headers)]*len(headers)
        if abs(sum(widths)-w)>.02:raise ValueError('Column widths do not sum to table width')
        z=s.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(w),Inches(row_h*(len(rows)+1)))
        table=z.table
        for j,width in enumerate(widths):table.columns[j].width=Inches(width)
        for i,row in enumerate([headers]+rows):
            table.rows[i].height=Inches(row_h)
            for j,v in enumerate(row):
                cell=table.cell(i,j);cell.margin_top=Inches(.06);cell.margin_bottom=Inches(.03);cell.margin_left=Inches(.075);cell.margin_right=Inches(.035)
                cell.fill.solid();cell.fill.fore_color.rgb=RGBColor.from_string(NAVY if i==0 else ('EAF2F5' if i%2 else 'FFFFFF'))
                tf=cell.text_frame;tf.word_wrap=True;p=tf.paragraphs[0];p.space_after=Pt(0)
                for text,bold in rich_parts(v):
                    r=p.add_run();r.text=text;r.font.name='Aptos';r.font.size=Pt(size);r.font.bold=bold or i==0;r.font.color.rgb=RGBColor.from_string('FFFFFF' if i==0 else NAVY)
        return z
    def cards(self,s,cards,y=2.1,h=3.35):
        gap=.27;w=(12.1-gap*(len(cards)-1))/len(cards)
        for i,(title,body) in enumerate(cards):
            x=.65+i*(w+gap);self.rect(s,x,y,w,h)
            self.text(s,x+.17,y+.2,w-.34,.88,title,21,TEAL,True)
            self.text(s,x+.17,y+1.22,w-.34,h-1.4,body,21)
    def flow(self,s,steps,y=2.25):
        w=2.73;gap=.39
        for i,(title,body) in enumerate(steps):
            x=.65+i*(w+gap);self.rect(s,x,y,w,2.95)
            self.text(s,x+.15,y+.22,w-.30,.95,title,21,TEAL,True)
            self.text(s,x+.15,y+1.42,w-.30,1.2,body,21)
            if i<3:self.text(s,x+w+.04,y+1.13,.31,.56,'›',32,TEAL,True)
    def new(self,item):
        s=self.p.slides.add_slide(self.p.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=RGBColor.from_string(BG)
        self.text(s,.55,.20,10.8,.24,item['section'],11,TEAL,True)
        page=f"{item['number']:02d} / {item['main_count']}" if item['main'] else f"PL {item['number']-item['main_count']:02d}"
        self.text(s,11.95,.20,.9,.24,page,11,GRAY)
        self.text(s,.55,.65,12.2,.9,item['title'],29,bold=True)
        if item.get('scope'):self.text(s,.65,1.51,12.05,.24,item['scope'],12,TEAL)
        refs=item.get('refs',[])
        if refs:
            for j,key in enumerate(refs[:3]):self.text(s,.65+4.08*j,7.21,3.95,.23,f'[{key}] '+REFERENCES[key]['short'],10.2,GRAY,url=REFERENCES[key]['url'])
        else:self.text(s,.65,7.21,12.0,.23,'18/11/2026  •  Nguồn số: CSV/protocol đã khóa; xem ghi chú và danh mục bằng chứng.',10.5,GRAY)
        if item.get('takeaway'):
            self.rect(s,.55,6.48,12.25,.69,'E3EEF2')
            self.text(s,.72,6.54,11.90,.58,item['takeaway'],17.3,TEAL,True)
        s.notes_slide.notes_text_frame.text=item['notes']+'\n\n'+self.source_note(item)
        return s
    @staticmethod
    def source_note(item):
        text='Nguồn số: evidence_inputs.json và các bảng CSV được liên kết. '+item.get('scope','')
        for key in item.get('refs',[]):text+='\n['+key+'] '+REFERENCES[key]['short']+' — '+REFERENCES[key]['url']
        return text
    def render(self,item):
        s=self.new(item);kind=item['kind']
        if kind=='cover':
            for z in list(s.shapes):
                if z.top==Inches(.65):z._element.getparent().remove(z._element)
            self.text(s,.75,1.62,11.9,1.6,item['title'],35,bold=True)
            self.text(s,.78,3.53,11.8,.6,item['subtitle'],25,TEAL)
            for i,value in enumerate(item['badges']):
                self.rect(s,.75+4.15*i,4.65,3.87,.85);self.text(s,.91+4.15*i,4.87,3.56,.4,value,20,bold=True)
        elif kind=='table':self.table(s,item['headers'],item['rows'],item.get('widths'),item.get('row_h',.65),item.get('size',20))
        elif kind=='cards':self.cards(s,item['cards'])
        elif kind in ('inventory','tuning'):
            for i,(number,label) in enumerate(item['stats']):
                x=.65+4.14*i;self.rect(s,x,2.0,3.84,2.13);self.text(s,x+.18,2.35,3.48,.7,number,40,TEAL,True);self.text(s,x+.18,3.27,3.48,.55,label,20)
            self.text(s,.75,4.65,11.8,1.25,item['bottom'],24)
        elif kind=='before_after':
            for x,title,lines in [(.65,item['left_title'],item['left']),(6.87,item['right_title'],item['right'])]:
                self.rect(s,x,1.95,5.88,3.92);self.text(s,x+.20,2.20,5.45,.72,title,23,TEAL,True)
                for i,line in enumerate(lines):self.text(s,x+.20,3.15+.83*i,5.45,.70,line,21)
        elif kind=='quality':
            for i,(title,body,status) in enumerate(item['levels']):
                y=1.93+i*1.38;self.rect(s,.65,y,12.1,1.16,PALE if status=='good' else 'F3EDE2')
                self.text(s,.86,y+.2,3.12,.73,title,22,TEAL if status=='good' else AMBER,True);self.text(s,4.25,y+.2,8.18,.73,body,21)
        elif kind=='flow':self.flow(s,item['steps'])
        elif kind=='roadmap':self.flow(s,item['steps'],2.15)
        elif kind=='models':
            for i,(model,inputs,why) in enumerate(item['models']):
                y=1.95+1.40*i;self.rect(s,.65,y,12.1,1.18);self.text(s,.85,y+.16,2.3,.85,model,22,TEAL,True)
                self.text(s,3.32,y+.16,3.70,.85,inputs,21);self.text(s,7.3,y+.16,5.15,.85,why,20)
        elif kind=='inputs':
            for i,(title,body) in enumerate(item['panels']):
                x=.65+6.24*i;self.rect(s,x,1.95,5.86,3.90);self.text(s,x+.2,2.16,5.45,.55,title,24,TEAL,True);self.text(s,x+.2,3.15,5.45,2.0,body,23)
        elif kind=='split':
            for i,row in enumerate(item['rows']):
                y=2.04+i*2.0
                for j,value in enumerate(row):
                    x=.65+2.43*j;self.rect(s,x,y,2.32,1.48,NAVY if j==0 else PALE);self.text(s,x+.12,y+.20,2.08,1.10,value,20,'FFFFFF' if j==0 else NAVY,j==0)
        elif kind=='heads':
            for i,(title,body) in enumerate(item['outputs']):
                x=.65+6.24*(i%2);y=1.95+2.08*(i//2);self.rect(s,x,y,5.86,1.78)
                self.text(s,x+.2,y+.18,5.45,.42,title,23,TEAL,True);self.text(s,x+.2,y+.92,5.45,.63,body,21)
        elif kind=='target_timeline':self.target(s)
        elif kind=='events':self.events(s)
        elif kind=='factorial':self.factorial(s)
        elif kind=='gru':self.gru(s)
        elif kind=='calibration':self.calibration(s)
        elif kind=='image':self.picture(s,PUBLIC/item['image'])
        elif kind=='references':
            for i,key in enumerate(item['keys']):
                r=REFERENCES[key];y=1.83+1.46*i
                self.text(s,.7,y,11.9,.35,f'[{key}] '+r['short'],19,TEAL,True,url=r['url']);self.text(s,.7,y+.43,11.9,.68,r['title'],18.5);self.text(s,.7,y+1.11,11.9,.26,r['status'],13.5,GRAY)
        else:raise ValueError('Unknown slide kind: '+kind)
    def picture(self,s,path):
        with Image.open(path) as im:w,h=im.size
        scale=min(12.0/w,4.52/h);width=w*scale;height=h*scale
        s.shapes.add_picture(str(path),Inches((13.333-width)/2),Inches(1.80),width=Inches(width),height=Inches(height))
    def target(self,s):
        self.text(s,.7,1.87,11.8,.48,'Ví dụ lịch phát: 19h ngày 18/11/2026 (UTC+7)',23,TEAL,True)
        self.rect(s,.7,2.65,3.05,2.65);self.text(s,.9,2.92,2.65,.6,'Quá khứ đã có',23,TEAL,True);self.text(s,.9,3.82,2.65,1.1,'7 ngày mưa\n+ tổng gần nhất\nCutoff: 18h',21)
        for i in range(3):
            x=4.14+2.86*i;self.rect(s,x,2.65,2.63,2.65,NAVY if i==0 else PALE);col='FFFFFF' if i==0 else NAVY
            self.text(s,x+.15,2.94,2.33,.55,f'Ngày {i+1}',25,col,True);self.text(s,x+.15,3.76,2.33,1.15,f'{24*i}–{24*(i+1)}h\nTổng 24 giờ\nKết thúc {19+i}/11',21,col)
        self.text(s,.75,5.7,11.8,.47,'Không phải mưa trung bình vùng; không phải tổng cộng dồn 48h hoặc 72h.',21)
    def events(self,s):
        self.table(s,['Minh họa','Thực có','Thực không'],[['Báo có','40 · H','20 · F'],['Báo không','60 · M','80']],[2.40,1.84,1.84],.78,20,2.12,.65,6.08)
        for i,(name,formula) in enumerate([('POD','40/(40+60) = 0,400'),('FAR','20/(40+20) = 0,333'),('CSI','40/(40+60+20) = 0,333')]):
            y=2.12+1.05*i;self.text(s,7.15,y,1.12,.5,name,23,TEAL,True);self.text(s,8.42,y,4.25,.6,formula,20)
        self.text(s,.75,5.68,11.8,.55,'Ví dụ công thức, không phải số liệu mô hình. H: trúng; M: bỏ sót; F: báo nhầm.',19,GRAY)
    def factorial(self,s):
        self.table(s,['Loss đầu mean','Train 2021–2022','Train 2021–2024'],[['Tweedie · p=1,5','A\n35.116 mẫu trạm–issue','B\n72.886 mẫu trạm–issue'],['L2 · bình phương sai số','C\n35.116 mẫu trạm–issue','D\n72.886 mẫu trạm–issue']],[3.1,4.5,4.5],1.05,22,2.00)
        self.text(s,.75,5.51,11.8,.62,'Cùng 57 trạm, 26 biến, ngân sách và ba seed; 2025 chỉ hiệu chỉnh xác suất/ngưỡng.',20)
    def gru(self,s):
        self.flow(s,[('Mưa 7 ngày','[batch, 7, 1]'),('GRU encoder','Hidden 16'),('Ghép context + ID','N3: context 3 × 18'),('Ba MLP head','Mean/median/p1/q')],2.05)
        self.text(s,.75,5.65,11.8,.56,'N3: 4.364 tham số • N5: 4.796 • 17 epoch • batch 256 • chuẩn hóa chỉ trên train',19)
    def calibration(self,s):
        self.flow(s,[('Xác suất raw','p1 và q từ mô hình'),('Platt trên cal','Giữ riêng từng quý'),('Chọn cutoff','CSI trên xác suất OOF'),('Khóa trước đánh giá','p50 = p1 × q')],2.05)
        self.text(s,.75,5.65,11.8,.56,'Protocol cũ: cal 2023 • A–D mới: cal 2025 • Không hiệu chỉnh bằng 2026',19)


def figures(e):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':16})
    fig,axes=plt.subplots(1,2,figsize=(12.0,4.45))
    for ax,group,title in zip(axes,['under1','ge50'],['Ngày khô: quan trắc <1 mm','Mưa lớn: quan trắc ≥50 mm']):
        values=[]
        for model in ('B','D'):
            value,_=e.value('window','dry_heavy_metrics',dict(evaluation_set='retrospective2026_modern',horizon=1,model=model,observed_bin=group),'micro_bias')
            values.append(value)
        ax.bar(['B · Tweedie','D · L2'],values,color=['#087D89','#607BA6'],width=.6)
        ax.axhline(0,color='#17364D',lw=1);ax.set_title(title,fontsize=17);ax.set_ylabel('Bias, mm/24h',fontsize=16)
        for i,value in enumerate(values):ax.text(i,value+(1.1 if value<0 else .11),fmt(value),ha='center',va='bottom',fontsize=17,fontweight='bold')
        ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
        if group=='under1':ax.set_ylim(0,3.6)
        else:ax.set_ylim(-56,0)
    fig.suptitle('Cùng train2021–2024 • Ngày1 • Modern2026 • Hậu kiểm theo mưa thực tế',fontsize=16)
    fig.tight_layout();fig.savefig(PUBLIC/'loss_tradeoff.png',dpi=190);plt.close(fig)
    p=e.csv('window','paired_comparisons');p=p[p.evaluation_set.eq('retrospective2026_modern')&p.family.eq('factorial')]
    fig,axes=plt.subplots(2,2,figsize=(12.0,4.50))
    for ax,(a,b,title) in zip(axes.ravel(),[('B','A','Thêm năm · Tweedie'),('D','C','Thêm năm · L2'),('C','A','Đổi loss · hai năm'),('D','B','Đổi loss · bốn năm')]):
        q=p[p['first'].eq(a)&p.reference.eq(b)].sort_values('horizon')
        y=np.arange(3);delta=q.difference.to_numpy();lo=q.simultaneous_ci_low.to_numpy();hi=q.simultaneous_ci_high.to_numpy()
        ax.errorbar(delta,y,xerr=np.array([delta-lo,hi-delta]),fmt='o',capsize=3,color='#087D89')
        ax.axvline(0,color='#A54437',ls='--');ax.set_yticks(y,[f'Ngày {h}' for h in q.horizon],fontsize=14)
        ax.set_title(f'{a}−{b}: {title}',fontsize=15);ax.tick_params(axis='x',labelsize=13);ax.invert_yaxis();ax.grid(axis='x',alpha=.2)
    fig.supxlabel('ΔRMSE, mm/24h • Âm có lợi cho cấu hình đứng trước • CI đồng thời theo họ12',fontsize=14)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(PUBLIC/'factorial_ci.png',dpi=200);plt.close(fig)


def item_lines(item):
    lines=[]
    for name in ['cards','steps','panels','models','outputs','stats','levels']:
        for values in item.get(name,[]):lines.append(' — '.join(str(x) for x in values[:3] if x not in ('good','warn')))
    if item.get('bottom'):lines.append(item['bottom'])
    if item.get('left_title'):
        lines.append(item['left_title']+': '+'; '.join(item['left']))
        lines.append(item['right_title']+': '+'; '.join(item['right']))
    return [readable(v).replace('**','') for v in lines]


def rich_doc(paragraph,value):
    for text,bold in rich_parts(value):paragraph.add_run(text).bold=bold


def handouts(items):
    doc=Document();doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=DP(11)
    for section in doc.sections:section.left_margin=DI(.8);section.right_margin=DI(.8)
    doc.add_heading('Thuyết minh báo cáo dự báo mưa ngắn hạn',0)
    doc.add_paragraph('Luồng chính 31 slide cho 25–30 phút; 31 slide phụ lục. Cập nhật 18/11/2026. Nội dung này giải thích slide bằng lời, không phải hướng dẫn train một mô hình mới.')
    markdown=['# Ghi chú thuyết trình: dự báo mưa ngắn hạn tại trạm','',
        'Dùng slide1–31 cho25–30phút. Slide32–62 là phụ lục để tra cứu, không cần đọc hết trong buổi báo cáo.','']
    for item in items:
        heading=f"{item['number']:02d}. {item['title'].replace(chr(10),' ')}"
        doc.add_heading(heading,1);markdown+=['## '+heading,'']
        role='Luồng chính' if item['main'] else 'Phụ lục'
        if item.get('scope'):role+=' · '+item['scope']
        doc.add_paragraph(readable(role));markdown+=[readable(role),'']
        if item.get('headers'):
            table=doc.add_table(rows=1,cols=len(item['headers']));table.style='Light Shading Accent 1'
            for j,value in enumerate(item['headers']):rich_doc(table.rows[0].cells[j].paragraphs[0],value)
            for row in item['rows']:
                cells=table.add_row().cells
                for j,value in enumerate(row):rich_doc(cells[j].paragraphs[0],value)
            escape=lambda v:readable(v).replace('|','\\|').replace('\n','; ')
            markdown+=['| '+' | '.join(escape(v) for v in item['headers'])+' |','| '+' | '.join(['---']*len(item['headers']))+' |']
            markdown+=['| '+' | '.join(escape(v) for v in row)+' |' for row in item['rows']]+['']
        for line in item_lines(item):doc.add_paragraph(line);markdown+=[line,'']
        if item.get('image'):
            doc.add_picture(str(PUBLIC/item['image']),width=DI(6.6))
            markdown+=['![Hình kết quả]('+item['image']+')','']
        doc.add_paragraph(item['notes']);markdown+=[item['notes'],'']
        if item.get('takeaway'):
            p=doc.add_paragraph();rich_doc(p,'**Ý chính: '+item['takeaway']+'**');markdown+=['**Ý chính: '+item['takeaway']+'**','']
        for key in item.get('refs',[]):
            source='['+key+'] '+REFERENCES[key]['short']+' — '+REFERENCES[key]['url']
            doc.add_paragraph(source);markdown+=[source,'']
    doc.save(PUBLIC/'THUYET_MINH_SLIDE.docx')
    (PUBLIC/'GHI_CHU_THUYET_TRINH.md').write_text(readable('\n'.join(markdown)).rstrip()+'\n',encoding='utf-8',newline='\n')
    guide='''# Cách dùng bộ báo cáo

Mở `PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx` để trình chiếu. Luồng chính là slide1–31, tổng khoảng25–30phút. Slide32–62 là phụ lục; dùng khi được hỏi hoặc gửi người đọc sau buổi báo cáo. Word và Markdown chứa lời giải thích cho từng slide; phần Notes trong PowerPoint cũng có nội dung này.

Các bảng in đậm số nhỏ nhất trong chính bảng đó. In đậm không tự có ý nghĩa thống kê. Kết quả 2025 thuộc protocol cũ; 2026 thuộc nghiên cứu hồi cứu mới. Đọc dòng phạm vi ngay trên bảng và ghi chú để không trộn điều kiện. A/C train 2021–22, B/D train 2021–24; A/B dùng Tweedie, C/D dùng L2. Năm 2025 dùng hiệu chỉnh trong protocol mới, không còn là test mới của phiên bản này.

Nên dành khoảng5phút cho bài toán/nguồn dữ liệu,5phút cho nhóm biến/mô hình,7phút cho huấn luyện/metrics,7–8phút cho kết quả,3–4phút cho giới hạn/hướng tiếp. Không đọc mọi tên biến trong phần chính; phụ lục và catalogue có đầy đủ.

Train và đánh giá hiện giữ cùng 57 trạm. Chưa có kiểm định giữ riêng trạm hoặc khu vực để chứng minh khả năng tổng quát hóa không gian; đây là một hướng tiếp theo, không phải kết quả đã có. Mọi kết quả 2026 trong báo cáo mới là hồi cứu đã xem, không phải test mới chưa dùng.

`NGUON_TAI_LIEU.md` phân biệt paper bình duyệt, preprint, tài liệu kỹ thuật và nguồn số nội bộ. Một số trang nhà xuất bản chặn mở toàn văn; tài liệu ghi rõ chỉ kiểm tra được phần công khai/tóm tắt/phương pháp được lập chỉ mục. Không có tuyên bố đã đọc toàn bộ mọi paper.

`BAN_DOC_OFFLINE.html` đọc được không cần cài PowerPoint, có nút điều hướng và ghi chú. PDF được xuất bằng PowerPoint trong thư mục private để gửi đọc; không commit PDF hoặc dữ liệu nguồn lên repo công khai. Gói báo cáo không chứa dữ liệu trạm, checkpoint hoặc thông tin đăng nhập.
'''
    (PUBLIC/'README.md').write_text(readable(guide),encoding='utf-8',newline='\n')
    refs=['# Nguồn tài liệu và giới hạn đối chiếu','','Ngày kiểm tra:18/11/2026. Chỉ dùng nguồn gốc hoặc tài liệu của cơ quan phát hành; không xếp hạng dự án bằng điểm ở bài toán khác.','']
    for key,r in REFERENCES.items():
        refs+=['## ['+key+'] '+r['short'],'','['+r['title']+']('+r['url']+')','',
            '**Trạng thái:** '+r['status']+'.','', '**Đã kiểm tra:** '+r['verified'],'','**Cách sử dụng:** '+r['use'],'']
    refs+=['## Nguồn số của dự án','',
        'Các bảng lấy từ CSV đã khóa trong ba thư mục: gfs_station_final_2026_11_17, gfs_temporal_2026_11_17 và gfs_training_window_2026_11_18. evidence_inputs.json lưu checksum; numeric_bindings.json lưu bộ lọc và cột cho từng số được trích. Các hình minh họa công thức được ghi rõ, không phải dự báo thực tế.','',
        'Thí nghiệm cũ được giữ nguyên. Bản slide chỉ đọc các kết quả, không fit lại mô hình hoặc đổi vai trò các số đã công bố. Đây là báo cáo mới bao quát nhiều nghiên cứu có phạm vi khác nhau, không gộp chúng thành một bảng test chung.','']
    (PUBLIC/'NGUON_TAI_LIEU.md').write_text(readable('\n'.join(refs)),encoding='utf-8',newline='\n')
    write_json(PUBLIC/'references.json',REFERENCES)


def rich_html(value):
    return ''.join('<strong>'+html.escape(t)+'</strong>' if bold else html.escape(t) for t,bold in rich_parts(value)).replace('\n','<br>')


def offline(items):
    import base64
    articles=[]
    for item in items:
        parts=[f'<article data-main="{int(item["main"])}" id="slide{item["number"]}">',f'<small>{html.escape(item["section"])}</small>',
            f'<h1>{rich_html(item["title"])}</h1>']
        if item.get('scope'):parts.append('<p class="scope">'+html.escape(item['scope'])+'</p>')
        if item.get('subtitle'):parts.append('<p>'+rich_html(item['subtitle'])+'</p>')
        if item.get('headers'):
            parts.append('<table><thead><tr>'+''.join('<th>'+rich_html(x)+'</th>' for x in item['headers'])+'</tr></thead><tbody>')
            for row in item['rows']:parts.append('<tr>'+''.join('<td>'+rich_html(x)+'</td>' for x in row)+'</tr>')
            parts.append('</tbody></table>')
        lines=item_lines(item)
        if lines:parts.append('<ul>'+''.join('<li>'+rich_html(x)+'</li>' for x in lines)+'</ul>')
        if item.get('image'):
            data=base64.b64encode((PUBLIC/item['image']).read_bytes()).decode()
            parts.append('<img alt="Hình kết quả" src="data:image/png;base64,'+data+'">')
        if item['kind']=='target_timeline':parts.append('<p>19h ngày18/11 → ngày1 kết thúc19h ngày19/11 → ngày2 kết thúc19h ngày20/11 → ngày3 kết thúc19h ngày21/11.</p>')
        if item['kind']=='events':parts.append('<p>Minh họa H=40,M=60,F=20: POD=0,400; FAR=0,333; CSI=0,333. Không phải kết quả mô hình.</p>')
        if item['kind']=='factorial':parts.append('<p>A/C: 2021–22; B/D: 2021–24. A/B dùng Tweedie, C/D dùng L2. Cùng57trạm,26biến và ngân sách.</p>')
        if item.get('takeaway'):parts.append('<p class="takeaway">'+rich_html(item['takeaway'])+'</p>')
        parts.append('<details><summary>Giải thích để trình bày</summary><p>'+html.escape(item['notes'])+'</p></details>')
        if item.get('keys'):
            for key in item['keys']:
                r=REFERENCES[key];parts.append('<p>['+key+'] <a href="'+r['url']+'">'+html.escape(r['title'])+'</a><br>'+html.escape(r['status'])+'</p>')
        parts.append('<footer>')
        for key in item.get('refs',[]):parts.append('<a href="'+REFERENCES[key]['url']+'">['+key+'] '+html.escape(REFERENCES[key]['short'])+'</a> · ')
        parts.append(f'18/11/2026 · Slide {item["number"]}/62</footer></article>');articles.append(''.join(parts))
    css='''body{margin:0;background:#edf3f7;font:21px/1.5 system-ui,sans-serif;color:#17364d}nav{position:sticky;top:0;background:#17364d;color:white;padding:12px;display:flex;gap:14px;align-items:center;z-index:2}button{font:inherit;padding:6px 15px;border:0;border-radius:5px}article{display:none;max-width:1150px;margin:20px auto;padding:35px;background:#fff;min-height:650px}h1{font-size:36px;line-height:1.25}small,.scope{color:#087d89}.takeaway{padding:15px;background:#e8f2f5;font-weight:600}table{border-collapse:collapse;width:100%;font-size:19px}th,td{padding:10px;border:1px solid #dce5eb;text-align:left}th{background:#17364d;color:white}tr:nth-child(even){background:#edf4f7}details{padding:12px;background:#f4f7fa}footer{font-size:13px;margin-top:25px}img{max-width:100%;max-height:500px}a{color:#087d89}@media print{nav{display:none}article{display:block!important;page-break-after:always;margin:0}details{display:block}}'''
    js='''const all=[...document.querySelectorAll('article')];let list=all,i=0;function show(){all.forEach(x=>x.style.display='none');list[i].style.display='block';document.querySelector('#page').textContent=(i+1)+' / '+list.length;window.scrollTo(0,0)}function step(n){i=Math.max(0,Math.min(list.length-1,i+n));show()}document.querySelector('#next').onclick=()=>step(1);document.querySelector('#prev').onclick=()=>step(-1);document.querySelector('#main').onchange=e=>{list=e.target.checked?all.filter(x=>x.dataset.main==='1'):all;i=0;show()};document.onkeydown=e=>{if(e.key==='ArrowRight')step(1);if(e.key==='ArrowLeft')step(-1)};show();'''
    page='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PBL6 · Báo cáo dự báo mưa ngắn hạn</title><style>'+css+'</style><nav><button id="prev">← Trước</button><span id="page"></span><button id="next">Tiếp →</button><label><input id="main" type="checkbox"> Chỉ31slide chính</label></nav>'+''.join(articles)+'<script>'+js+'</script></html>'
    (PUBLIC/'BAN_DOC_OFFLINE.html').write_text(page,encoding='utf-8',newline='\n')


def main():
    PUBLIC.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    before={}
    for name in STUDIES.values():
        for p in (ROOT/'reports'/name).rglob('*'):
            if p.is_file() and not p.name.startswith('~$'):before[str(p.relative_to(ROOT)).replace('\\','/')]=sha(p)
    for relative in ['reports/daily_gauge_slides_2026_11_04/PBL6_DU_LIEU_NGAY_3_MO_HINH.pptx',
        'reports/short_range_three_models_2026_10_21/Dự đoán ngắn hạn 21_10.pptx']:
        before[relative]=sha(ROOT/relative)
    if not (PRIVATE/'protected_before.json').exists():write_json(PRIVATE/'protected_before.json',before)
    else:
        for relative,digest in json.loads((PRIVATE/'protected_before.json').read_text()).items():
            if sha(ROOT/relative)!=digest:raise ValueError('Old report/user slide changed: '+relative)
    e=Evidence();items=make_slides(e)
    e.csv('temporal','paired_comparisons')
    e.js('reports/station_update_2026_11_16/dataset_summary.json')
    for rel in ['reports/gfs_temporal_2026_11_17/model_verification.json',
                'reports/gfs_training_window_2026_11_18/tests_verification.json']:
        if e.js(rel)['status']!='passed':raise ValueError('Source evidence is not verified: '+rel)
    if len(items)!=len(NOTES):raise ValueError('Every slide needs an authored explanation')
    for i,item in enumerate(items):item['notes']=readable(NOTES[i])
    figures(e);deck=Deck()
    for item in items:deck.render(item)
    deck.p.save(PUBLIC/'PBL6_BAO_CAO_DAY_DU_DU_BAO_MUA_NGAN_HAN.pptx')
    handouts(items);offline(items)
    write_json(PUBLIC/'slide_manifest.json',items)
    write_json(PUBLIC/'numeric_bindings.json',e.bindings)
    source=e.csv('window','feature_catalog');source.to_csv(PUBLIC/'feature_catalog.csv',index=False,lineterminator='\n')
    write_json(PUBLIC/'evidence_inputs.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),files=e.inputs,
        source_read_only=True,model_training=False,model_rescoring=False))
    # Capture runtime status as a dated snapshot, not a source pretending to stay current.
    tracker=ROOT/'data/operational/gfs_training_window_2026_11_18/live/tracker.json'
    runtime=json.loads(tracker.read_text()) if tracker.exists() else {}
    write_json(PUBLIC/'prospective_snapshot.json',dict(snapshot_utc=datetime.now(timezone.utc).isoformat(),
        stage=runtime.get('stage','unknown'),heartbeat_utc=runtime.get('updated_utc'),issue_utc=runtime.get('issue_utc'),
        forecast_issued=False,truth_verified=False,note='Publication snapshot; inspect private tracker for actual later status.'))
    print(dict(slides=len(items),main_slides=sum(i['main'] for i in items),minutes=round(sum(i['minutes'] for i in items),1),numeric_bindings=len(e.bindings)),flush=True)


if __name__=='__main__':main()
