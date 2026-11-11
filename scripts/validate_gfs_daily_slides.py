"""Replay aggregate values and audit native/HTML daily-v2 slides without raw data."""
from pathlib import Path
import hashlib
import html
import json
import math
import re
import subprocess

import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/gfs_daily_slides_2026_11_11'
DATA=ROOT/'reports/gfs_station_daily_v2_2026_11_10'
PRIVATE=ROOT/'data/operational/gfs_daily_slides_2026_11_11'
STEM='PBL6_MUA_TRAM_HANG_NGAY_V2'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def fmt(v,d=3):return '\u2014' if pd.isna(v) else f'{float(v):.{d}f}'.replace('.',',')


def main():
    manifest=read(OUT/'build_manifest.json');scene=read(OUT/'slide_content.json')
    prs=Presentation(OUT/(STEM+'.pptx'));tables={}
    assert len(scene)==len(prs.slides)==manifest['slides']
    assert not manifest['training_run'] and not manifest['test2025_read']
    for path,digest in manifest['sources'].items():assert sha(ROOT/path)==digest,path
    for path,digest in manifest['code_sha256'].items():assert sha(ROOT/path)==digest,path
    for name,digest in manifest['files_sha256'].items():assert sha(OUT/name)==digest,name
    snapshot=PRIVATE/'source_snapshot.json'
    if snapshot.exists():
        for path,digest in read(snapshot).items():assert sha(ROOT/path)==digest,('pre-task source changed',path)
    for native,slide in zip(prs.slides,scene):
        assert native.notes_slide.notes_text_frame.text==slide['note']
        assert len(slide['note'].split())>=60
        assert '\ufffd' not in slide['note']
        assert len(native.shapes)==len(slide['shapes'])
        for shape,spec in zip(native.shapes,slide['shapes']):
            assert spec['x']>=0 and spec['y']>=0
            assert spec['x']+spec['w']<=13.334 and spec['y']+spec['h']<=7.5
            if spec['kind']=='table':
                assert spec['tag'] not in tables
                tables[spec['tag']]=spec
                for ri,row in enumerate([spec['headers']]+spec['rows']):
                    for ci,text in enumerate(row):
                        cell=shape.table.cell(ri,ci);assert cell.text==str(text)
                        style=spec['styles'].get(f'{ri},{ci}',{})
                        for p in cell.text_frame.paragraphs:
                            for run in p.runs:
                                assert run.font.size.pt==spec['size']
                                assert run.font.bold==(ri==0 or style.get('bold',False))
                                assert str(run.font.color.rgb)==('FFFFFF' if ri==0 else style.get('color','123047'))
            elif spec['kind']=='text':assert shape.text==spec['text'].replace('**','')
        foreground=[s for s in slide['shapes'] if s['kind']!='rect']
        for i,a in enumerate(foreground):
            for b in foreground[:i]:
                dx=min(a['x']+a['w'],b['x']+b['w'])-max(a['x'],b['x'])
                dy=min(a['y']+a['h'],b['y']+b['h'])-max(a['y'],b['y'])
                assert dx<=.03 or dy<=.03,('foreground overlap',slide['number'],a,b)
    data={};numeric=0;matrix_values={}
    matrix_tags={'rmse','mae','bss50','latency','full_rmse','full_mae','full_bias','full_bs1','full_bss1','full_bs50','full_bss50'}
    for c in manifest['numeric_checks']:
        if c['file'] not in data:data[c['file']]=pd.read_csv(DATA/c['file'])
        f=data[c['file']]
        for key,v in c['filters'].items():f=f[f[key].eq(v)]
        assert len(f)==1,c
        r=f.iloc[0];table=tables[c['tag']];actual=table['rows'][c['row']][c['col']]
        if c['kind']=='scalar':
            expected=fmt(r[c['key']],c['digits']);numeric+=1
            if c['tag'] in matrix_tags:
                matrix_values.setdefault((c['tag'],c['col'],c['key']),[]).append((c['row'],float(r[c['key']])))
        else:
            expected=f"{fmt(r.difference)} [{fmt(r.ci95_low)}; {fmt(r.ci95_high)}]";numeric+=3
            style=table['styles'].get(f"{c['row']+1},{c['col']}",{})
            assert bool(style.get('bold',False))==bool(r.ci95_high<0),('CI highlight',c)
        assert actual==expected,(c,actual,expected)
    for (tag,col,key),values in matrix_values.items():
        transformed=[abs(v) if key=='macro_bias' else v for _,v in values]
        best=(max if key=='macro_bss' else min)(transformed)
        for (row,_),v in zip(values,transformed):
            bold=tables[tag]['styles'].get(f'{row+1},{col}',{}).get('bold',False)
            assert bold==math.isclose(v,best,rel_tol=1e-9,abs_tol=1e-12),(tag,row,col)
    audit=read(DATA/'dataset_audit.json')
    for i,part in enumerate(('train','cal','dev')):
        assert int(tables['split_counts']['rows'][i][1].replace('.',''))==audit['counts'][part]['station_issues']
    for group,count,_ in tables['features']['rows']:assert int(count)==audit['feature_counts'][group]
    selection=read(DATA/'tree_selection.json')['selected']
    for row,key in zip(tables['tree_config']['rows'],('mean','median','wet','conditional')):
        c=selection[key]['candidate']
        assert row[1:4]==[str(c[x]) for x in ('num_leaves','max_depth','min_child_samples')]
        assert row[4]=='/'.join(str(selection[key]['trees'][str(h)]) for h in (1,2,3))
    protected=read(ROOT/'data/operational/workspace_cleanup_2026_11_09/user_files.json')
    for item in protected:assert sha(ROOT/item['path'])==item['sha256'],'Protected user file changed'
    assert not (ROOT/'reports/short_range_three_models_2026_10_21/PBL6_SO_SANH_3_MO_HINH.pptx').exists()
    assert not list(OUT.glob('*.pdf'))
    render=read(OUT/'native_render_audit.json')
    assert render['pptx_sha256']==sha(OUT/(STEM+'.pptx'))
    assert render['slide_count']==len(scene) and render['pdf_exported']
    assert not render['overflows'],render['overflows']
    pdf=PRIVATE/(STEM+'.pdf')
    assert pdf.read_bytes().startswith(b'%PDF-') and pdf.stat().st_size>100_000
    chrome=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    cmd=[str(chrome),'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
         '--allow-file-access-from-files','--user-data-dir='+str(PRIVATE/'chrome_layout_profile'),
         '--virtual-time-budget=3000','--dump-dom',(OUT/(STEM+'.html')).as_uri()+'?all=1']
    result=subprocess.run(cmd,capture_output=True,timeout=60,creationflags=0x08000000)
    assert result.returncode==0
    dom=result.stdout.decode('utf8');(PRIVATE/'rendered_dom.html').write_text(dom,encoding='utf8')
    match=re.search(r'<pre id="layout-status">(.*?)</pre>',dom,re.S);assert match
    browser=json.loads(html.unescape(match.group(1)))
    assert browser['checked'] and not browser['overflows'],browser
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);previews=[]
    for sheet_no,start in enumerate(range(1,len(scene)+1,16),1):
        numbers=list(range(start,min(start+16,len(scene)+1)))
        canvas=Image.new('RGB',(1680,math.ceil(len(numbers)/4)*257),'#DFE7EF');draw=ImageDraw.Draw(canvas)
        for i,n in enumerate(numbers):
            image=Image.open(PRIVATE/'native_png'/f'slide_{n:02d}.png').convert('RGB')
            assert image.size==(1600,900)
            x=i%4*420+10;y=i//4*257+25
            canvas.paste(image.resize((400,225),Image.Resampling.LANCZOS),(x,y))
            draw.text((x,y-22),f'Slide {n:02d}',font=font,fill='#123047')
        name=f'XEM_TRUOC_{sheet_no:02d}.png';canvas.save(OUT/name);previews.append(name)
    report=dict(status='passed',slides=len(scene),main_slides=manifest['main_slides'],
                appendix_slides=len(scene)-manifest['main_slides'],numeric_cells_checked=len(manifest['numeric_checks']),
                numeric_values_checked=numeric,source_hashes_checked=len(manifest['sources']),
                editable_pptx_and_notes_checked=True,geometry_checked=True,
                native_text_boxes_checked=render['text_boxes_checked'],native_overflows=[],browser_layout=browser,
                protected_user_files_unchanged=True,training_performed=False,test2025_read=False,
                pdf_private_sha256=sha(pdf),previews=previews)
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
