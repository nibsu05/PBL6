"""Export development-result figures; only aggregate values leave private data."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from src.gfs_daily import PUBLIC


def main():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    point=pd.read_csv(PUBLIC/'point_metrics.csv');point=point[point.fold.eq('dev')]
    models=['ZERO','GFS','MOS','LGB_N3','LGB_N5','GRU_N3','GRU_N5']
    colors=['#999999','#172b4d','#9a6800','#007c91','#57b7b0','#7954a1','#ce5c82']
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for ax,fun,col,title in zip(axes,['mean','median'],['macro_rmse','macro_mae'],
        ['Đầu mean: RMSE theo trạm','Đầu median: MAE theo trạm']):
        for model,color in zip(models,colors):
            s=point[point.model.eq(model)&point.functional.eq(fun)].sort_values('horizon')
            ax.plot(s.horizon,s[col],marker='o',color=color,label=model,linewidth=1.7)
        ax.set(title=title,xlabel='Ngày dự báo',ylabel='mm / 24 giờ (nhỏ hơn tốt hơn)',xticks=[1,2,3]);ax.grid(alpha=.15)
    axes[1].legend(loc='upper left',bbox_to_anchor=(1.02,1),frameon=False)
    fig.suptitle('57 trạm · Lịch hằng ngày · Dev 2024 · Chưa mở test 2025',fontweight='bold')
    fig.tight_layout();fig.savefig(PUBLIC/'luong_mua.png',dpi=180,bbox_inches='tight');plt.close(fig)
    ci=pd.read_csv(PUBLIC/'paired_bootstrap.csv');pairs=[('LGB_N1','LGB_N0'),('LGB_N2','LGB_N1'),('LGB_N3','LGB_N1'),('LGB_N4','LGB_N3'),('LGB_N5','LGB_N4'),('GRU_N5','GRU_N3')]
    fig,axes=plt.subplots(1,3,figsize=(13,5),sharey=True)
    for ax,h in zip(axes,[1,2,3]):
        for j,(a,b) in enumerate(pairs):
            r=ci[ci.model.eq(a)&ci.reference.eq(b)&ci.horizon.eq(h)&ci.functional.eq('mean')&ci.metric.eq('rmse')].iloc[0]
            color='#007c91' if r.ci95_high<0 else '#4d5966'
            ax.plot([r.ci95_low,r.ci95_high],[j,j],color=color,lw=2);ax.plot(r.difference,j,'o',color=color)
        ax.axvline(0,color='#b34d40',ls='--',lw=1);ax.set(title=f'Ngày {h}',xlabel='Δ RMSE mean (mm/24h)');ax.grid(axis='x',alpha=.15)
    axes[0].set_yticks(range(len(pairs)),[a.replace('LGB_','')+' − '+b.replace('LGB_','') for a,b in pairs]);axes[0].invert_yaxis()
    fig.suptitle('Giá trị bổ sung đặc trưng · Điểm và CI95% ghép cặp\nÂm có lợi; CI còn cắt 0: chưa phân biệt rõ',fontweight='bold')
    fig.tight_layout();fig.savefig(PUBLIC/'dan_xuat_ci.png',dpi=180,bbox_inches='tight');plt.close(fig)


if __name__=='__main__':main()
