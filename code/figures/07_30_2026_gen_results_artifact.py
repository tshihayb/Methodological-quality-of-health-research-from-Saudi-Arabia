# -*- coding: utf-8 -*-
# Builds the HTML results artifact for the reporting-vs-validity 4-state quality scoring.
# Reads the three 07_30 scored CSVs; emits outputs/reports/07_30_2026_quality_scoring_results.html in the house style.
# Run: PYTHONUTF8=1 python code/figures/07_30_2026_gen_results_artifact.py
import pandas as pd, numpy as np, html as H

KA = dict(dtype=str, keep_default_na=False, na_values=[])   # keep the literal state "NA" as a string
dom = pd.read_csv('data/scoring/07_30_2026_scored_domain.csv', **KA)
it  = pd.read_csv('data/scoring/07_30_2026_scored_items_long.csv', **KA)
stu = pd.read_csv('data/scoring/07_30_2026_scored_study.csv')

DOMS  = ['Random error','Selection bias','Measurement bias','Confounding bias','Missing data','Mentioning errors','Conflating task']
DLAB  = {'Mentioning errors':'Mentioning errors in the discussion','Conflating task':'Conflating the task'}
STATES= ['OK','REP','VAL','NA']
SLAB  = {'OK':'No issue','REP':'Reporting gap','VAL':'Validity flaw','NA':'N/A'}
N_C = int((dom[dom.domain=='Random error'].Study_Type=='Causal').sum())
N_D = int((dom[dom.domain=='Random error'].Study_Type=='Descriptive').sum())
N_T = N_C + N_D

def counts(dm, tk):
    s = dom[(dom.domain==dm)&(dom.Study_Type==tk)].state
    N = len(s)
    return N, {k:int((s==k).sum()) for k in STATES}

# ---- study-level ----
stu['transparency']=pd.to_numeric(stu['transparency'],errors='coerce')
stu['validity']=pd.to_numeric(stu['validity'],errors='coerce')
stu['domains_flagged']=pd.to_numeric(stu['domains_flagged'],errors='coerce')
tv = stu.dropna(subset=['transparency','validity'])
mt, mv = tv.transparency.median(), tv.validity.median()
clean = int((stu.domains_flagged==0).sum()); ge3 = int((stu.domains_flagged>=3).sum())
Q = {('hi','hi'):int(((tv.transparency>=mt)&(tv.validity>=mv)).sum()),
     ('hi','lo'):int(((tv.transparency>=mt)&(tv.validity< mv)).sum()),
     ('lo','hi'):int(((tv.transparency< mt)&(tv.validity>=mv)).sum()),
     ('lo','lo'):int(((tv.transparency< mt)&(tv.validity< mv)).sum())}
edges=[0,0.2,0.4,0.6,0.8,1.0001]
tb=np.clip(np.digitize(tv.transparency,edges[1:-1]),0,4)
vb=np.clip(np.digitize(tv.validity,     edges[1:-1]),0,4)
grid=np.zeros((5,5),int)
for a,b in zip(vb,tb): grid[a,b]+=1

# ---- sensitivity ----
sens=[]
for dm in DOMS:
    sub=dom[(dom.domain==dm)&(dom.state!='NA')]; N=len(sub)
    prim=int((sub.state=='VAL').sum()); upp=int(sub.state.isin(['VAL','REP']).sum())
    sens.append((dm,N,100*prim/N if N else 0,100*upp/N if N else 0))

# ---- author insight ----
erd=it[it.item=='err_disc'][['PMID','raw']].set_index('PMID')['raw']
IMAP={'Selection bias':'selection bias','Measurement bias':'measurement bias','Confounding bias':'confounding bias','Missing data':'missing data','Random error':'random error'}
insight=[]
for dm,lab in IMAP.items():
    vpm=dom[(dom.domain==dm)&(dom.state=='VAL')].PMID
    e=erd.reindex(vpm).fillna('').str.lower()
    ack=int(e.str.contains(lab).sum()); n=len(vpm)
    insight.append((dm,n,ack,100*ack/n if n else 0))

# ---- secondary (additive) severity: per-domain mean VAL/REP + study-level score histograms ----
pri = it[it['primary']=='TRUE'].copy()
pri['v']=(pri.state=='VAL').astype(int); pri['r']=(pri.state=='REP').astype(int); pri['a']=(pri.state!='NA').astype(int)
g = pri.groupby(['PMID','domain','Study_Type'])[['v','r','a']].sum().reset_index()
DMEAN={}; SCALE=0.0
for dm in DOMS:
    for tk in ['Descriptive','Causal']:
        s=g[(g.domain==dm)&(g.Study_Type==tk)&(g.a>0)]
        if len(s):
            # ⚠ These were named mv,mr - at MODULE level, so they overwrote the study-level
            # median validity index computed at line 30 and never restored it.  Every
            # published version of this figure printed the LAST domain's mean flag count
            # (0.64, Conflating-task descriptive) where the headline says "median validity
            # index".  Renamed; the assertion before substitution now pins it.
            dv,dr=float(s.v.mean()),float(s.r.mean()); DMEAN[(dm,tk)]=(dv,dr); SCALE=max(SCALE,dv+dr)
        else:
            DMEAN[(dm,tk)]=(None,None)
SCALE = SCALE*1.06 if SCALE>0 else 1.0
stu['nv']=pd.to_numeric(stu['n_val_flags'],errors='coerce'); stu['nr']=pd.to_numeric(stu['n_rep_gaps'],errors='coerce')
maxV=int(stu.nv.max()); maxR=int(stu.nr.max())
def _hist(col,mx):
    return {v:(int(((stu[col]==v)&(stu.Study_Type=='Descriptive')).sum()),
               int(((stu[col]==v)&(stu.Study_Type=='Causal')).sum())) for v in range(mx+1)}
VH=_hist('nv',maxV); RH=_hist('nr',maxR)
mVc=stu[stu.Study_Type=='Causal'].nv.mean(); mVd=stu[stu.Study_Type=='Descriptive'].nv.mean()
mRc=stu[stu.Study_Type=='Causal'].nr.mean(); mRd=stu[stu.Study_Type=='Descriptive'].nr.mean()

# ---- Yasser's checks: confounding-flaw composition + quadrant percentages ----
wq=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv', **KA)
wcau=wq[wq.Study_Type=='Causal']
_cvp=set(dom[(dom.domain=='Confounding bias')&(dom.state=='VAL')].PMID)
_cop=set(dom[(dom.domain=='Confounding bias')&(dom.state=='OK')].PMID)
_sub=wcau[wcau.PMID.isin(_cvp)]
_noadj=_sub['causal_base_conf_meth'].str.lower().str.contains('no adjustment')
_ment =_sub['causal_err_disc'].str.lower().str.contains('confounding bias')
CFN=len(_sub); CF_noadj=int(_noadj.sum()); CF_adj=int((~_noadj).sum())
CF_noadj_ack=int((_noadj&_ment).sum()); CF_adj_ack=int((~_noadj&_ment).sum())
CF_ok_ment=int(wcau[wcau.PMID.isin(_cop)]['causal_err_disc'].str.lower().str.contains('confounding bias').sum())
NTV=Q[('hi','hi')]+Q[('hi','lo')]+Q[('lo','hi')]+Q[('lo','lo')]
def qp(k): return '%.0f'%(100*Q[k]/NTV) if NTV else '0'

# ================= HTML =================
def pct(n,N): return '%.1f'%(100*n/N) if N else '0.0'
def seg(frac,color):  # one stacked-bar segment
    if frac<=0: return ''
    return '<i style="width:%.4f%%;background:%s"></i>'%(frac*100,color)
CVAR={'OK':'var(--ok)','REP':'var(--rep)','VAL':'var(--val)','NA':'var(--na)'}

def bar_row(tk, dm):
    N,c=counts(dm,tk)
    if N==0 or c['NA']==N:
        return ('<div class="brow"><span class="tk">%s</span>'
                '<span class="bar"><i style="width:100%%;background:var(--na)"></i></span>'
                '<span class="bpct na">n/a</span></div>'%tk[0])
    order=['OK','REP','VAL','NA']
    segs=''.join(seg(c[s]/N,CVAR[s]) for s in order)
    # ⚠ DENOMINATOR = APPLICABLE PAPERS, not all papers of the task.  This was pct(...,N),
    # which includes the not-applicable ones and so DILUTED the prevalence.  It only shows
    # in random error, the one domain with N/A papers (whole-population sampling skips it):
    # descriptive read 17.3% (14/81) instead of 25.5% (14/55), causal 26.2% instead of 31.6%.
    # The applicable base is the project's stated convention - it is what the Methods record
    # and the Suppl. Table S1 footnote both quote - so the figure was the odd one out.
    flaw=pct(c['VAL'],N-c['NA'])
    return ('<div class="brow"><span class="tk">%s</span><span class="bar">%s</span>'
            '<span class="bpct">%s%%</span></div>'%(tk[0],segs,flaw))

def domain_block(dm):
    lab=DLAB.get(dm,dm)
    note=''
    if dm=='Confounding bias': note=' <span class="dn">causal only</span>'
    if dm=='Conflating task':  note=' <span class="dn">descriptive only</span>'
    if dm=='Random error':     note=' <span class="dn">precision, not bias</span>'
    if dm=='Mentioning errors':note=' <span class="dn">pure reporting</span>'
    return ('<div class="dblock"><div class="dt">%s%s</div>%s%s</div>'
            %(H.escape(lab),note,bar_row('Descriptive',dm),bar_row('Causal',dm)))

bars=''.join(domain_block(dm) for dm in DOMS)

# sensitivity range bars (red to primary, amber to upper)
def sens_row(dm,N,p,u):
    lab=DLAB.get(dm,dm)
    swing='<span class="sw">+%.0f</span>'%(u-p) if u-p>=1 else '<span class="sw z">flat</span>'
    return ('<div class="srow"><span class="slab">%s</span>'
            '<span class="strack"><i class="sp" style="width:%.3f%%"></i>'
            '<i class="su" style="width:%.3f%%"></i></span>'
            '<span class="sval">%.0f&ndash;%.0f%%</span>%s'
            '<span class="sn">/%d</span></div>'%(H.escape(lab),p,max(u-p,0),p,u,swing,N))
sensbars=''.join(sens_row(*r) for r in sens)

# heatmap 5x5
mx=grid.max()
def cell(cnt):
    if cnt==0: return '<div class="hc" style="background:var(--panel)"></div>'
    a=0.10+0.85*cnt/mx
    tc='#fff' if a>0.5 else 'var(--ink)'
    return '<div class="hc" style="background:rgba(22,105,122,%.2f);color:%s">%d</div>'%(a,tc,cnt)
rowlab=['0&ndash;.2','.2&ndash;.4','.4&ndash;.6','.6&ndash;.8','.8&ndash;1']
hrows=''
for r in range(4,-1,-1):
    hrows+='<div class="hrow"><span class="hrl">%s</span>%s</div>'%(rowlab[r],''.join(cell(grid[r,c]) for c in range(5)))
hcols='<div class="hcl"><span class="hsp"></span>'+''.join('<span>%s</span>'%l for l in rowlab)+'</div>'

# insight bars
def ins_row(dm,n,ack,p):
    lab=DLAB.get(dm,dm)
    return ('<div class="irow"><span class="ilab">%s</span>'
            '<span class="itrack"><i style="width:%.2f%%"></i></span>'
            '<span class="ival">%.0f%%</span><span class="in">%d/%d</span></div>'
            %(H.escape(lab),p,p,ack,n))
insbars=''.join(ins_row(*r) for r in insight)

def sec_row(tk,dm):
    mv,mr=DMEAN[(dm,tk)]
    if mv is None:
        return '<div class="brow"><span class="tk">%s</span><span class="bar"><i style="width:100%%;background:var(--na)"></i></span><span class="bpct na">n/a</span></div>'%tk[0]
    wv=mv/SCALE*100; wr=mr/SCALE*100; segs=''
    if wv>0: segs+='<i style="width:%.3f%%;background:var(--val)"></i>'%wv
    if wr>0: segs+='<i style="width:%.3f%%;background:var(--rep)"></i>'%wr
    return '<div class="brow"><span class="tk">%s</span><span class="bar">%s</span><span class="bpct">%.2f</span></div>'%(tk[0],segs,mv+mr)
secbars=''.join('<div class="dblock"><div class="dt">%s</div>%s%s</div>'
                %(H.escape(DLAB.get(dm,dm)),sec_row('Descriptive',dm),sec_row('Causal',dm)) for dm in DOMS)
def histbars(Hd,mx,cC,cD,nD,nC):
    # grouped: descriptive (light) and causal (dark) side by side; heights = % WITHIN each task so the shapes compare
    maxp=max(max((d/nD*100 if nD else 0),(c/nC*100 if nC else 0)) for d,c in Hd.values()) or 1
    out=''
    for v in range(mx+1):
        d,c=Hd[v]; pdd=(d/nD*100 if nD else 0); pcc=(c/nC*100 if nC else 0)
        out+=('<div class="hbcol"><div class="hbpair">'
              '<i class="hbb" style="height:%.1fpx;background:%s" title="descriptive: %d (%.0f%%)"></i>'
              '<i class="hbb" style="height:%.1fpx;background:%s" title="causal: %d (%.0f%%)"></i>'
              '</div><div class="hbx">%d</div></div>'%(pdd/maxp*92,cD,d,pdd,pcc/maxp*92,cC,c,pcc,v))
    return out
vhist=histbars(VH,maxV,'var(--val)','#eba9a9',N_D,N_C); rhist=histbars(RH,maxR,'var(--rep)','#f0cfa0',N_D,N_C)

PAGE=r'''<title>Reporting vs validity &mdash; quality of Saudi 2022 health research</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;
--ok:#0ca30c;--rep:#e08a12;--val:#d03b3b;--na:#b4b2a9;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--na:#5b636e;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--na:#b4b2a9;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--na:#5b636e;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,56px) 20px}
.wrap{max-width:1000px;margin:0 auto}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.6vw,34px);line-height:1.14;letter-spacing:-.01em;margin:0 0 14px;text-wrap:balance;max-width:22ch}
.lede{color:var(--muted);font-size:15.5px;max-width:70ch;margin:0 0 26px}
.lede b{color:var(--ink);font-weight:600}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:0 0 34px}
.stat{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:14px 16px}
.stat .v{font-family:var(--serif);font-size:27px;font-weight:600;font-variant-numeric:tabular-nums;color:var(--accent)}
.stat .k{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.35}
section{margin:0 0 38px}
.sh{font-family:var(--serif);font-size:20px;font-weight:600;margin:0 0 4px}
.sd{color:var(--muted);font-size:14px;max-width:74ch;margin:0 0 18px}
.key{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;font-size:12.5px;color:var(--muted);margin:0 0 16px}
.key span{display:flex;align-items:center;gap:6px}
.sq{width:11px;height:11px;border-radius:3px}
.panel{background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:18px 20px}
.dblock{margin:0 0 13px}
.dblock:last-child{margin-bottom:0}
.dt{font-size:13.5px;font-weight:600;color:var(--ink);margin:0 0 5px}
.dn{font-weight:400;color:var(--faint);font-size:12px}
.brow{display:flex;align-items:center;gap:10px;margin:3px 0}
.tk{flex:none;width:15px;font-size:11px;color:var(--faint)}
.bar{flex:1;display:flex;height:20px;border-radius:4px;overflow:hidden;background:var(--row)}
.bar i{display:block;height:100%;box-shadow:1px 0 0 var(--panel)}
.bpct{flex:none;width:52px;text-align:right;font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.bpct.na{color:var(--faint);font-style:italic}
.srow{display:flex;align-items:center;gap:10px;margin:8px 0}
.slab{flex:none;width:190px;font-size:13px;color:var(--ink)}
.strack{flex:1;display:flex;height:16px;border-radius:4px;overflow:hidden;background:var(--row)}
.strack .sp{background:var(--val);height:100%}
.strack .su{background:var(--rep);height:100%;opacity:.85}
.sval{flex:none;width:80px;text-align:right;font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.sw{flex:none;width:40px;text-align:right;font-size:11.5px;color:var(--rep);font-weight:600}
.sw.z{color:var(--faint);font-weight:400}
.sn{flex:none;width:36px;text-align:right;font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
.hm{display:flex;gap:22px;flex-wrap:wrap;align-items:flex-start}
.hgrid{flex:none}
.axl{font-size:11.5px;color:var(--muted);margin:0 0 7px}
.hrow{display:flex;gap:3px;margin-bottom:3px}
.hrl{flex:none;width:42px;font-size:10px;color:var(--faint);display:flex;align-items:center;justify-content:flex-end;padding-right:6px}
.hc{width:52px;height:34px;border:1px solid var(--hair);border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:12px;font-variant-numeric:tabular-nums}
.hcl{display:flex;gap:3px;margin-top:5px}
.hcl .hsp{flex:none;width:42px}
.hcl span{width:52px;text-align:center;font-size:10px;color:var(--faint)}
.hx{text-align:center;font-size:11.5px;color:var(--muted);margin-top:8px;padding-left:42px}
.quad{flex:1;min-width:220px;align-self:center}
.q2{display:grid;grid-template-columns:1fr 1fr;gap:8px;max-width:340px}
.qc{border:1px solid var(--hair);border-radius:9px;padding:11px 13px;background:var(--panel)}
.qc .qn{font-family:var(--serif);font-size:22px;font-weight:600;font-variant-numeric:tabular-nums}
.qc .ql{font-size:11.5px;color:var(--muted);margin-top:2px}
.qc.good .qn{color:var(--ok)} .qc.bad .qn{color:var(--val)}
.irow{display:flex;align-items:center;gap:10px;margin:7px 0}
.ilab{flex:none;width:190px;font-size:13px;color:var(--ink)}
.itrack{flex:1;height:16px;border-radius:4px;overflow:hidden;background:var(--row)}
.itrack i{display:block;height:100%;background:var(--accent)}
.ival{flex:none;width:44px;text-align:right;font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.in{flex:none;width:52px;text-align:right;font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
.foot{margin-top:8px;color:var(--faint);font-size:12.5px;line-height:1.6;max-width:92ch}
.foot b{color:var(--muted)} .foot code{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
.foot .pf{display:inline-block;width:9px;height:9px;border-radius:2px;vertical-align:middle;margin-right:3px}
.subh{font-size:13px;font-weight:600;color:var(--muted);margin:0 0 12px;letter-spacing:.02em}
.histwrap{display:flex;gap:26px;flex-wrap:wrap}
.hist{flex:1;min-width:250px}
.histt{font-size:12.5px;color:var(--ink);margin:0 0 12px}
.hbrow{display:flex;gap:5px;align-items:flex-end}
.hbcol{flex:1;display:flex;flex-direction:column;align-items:center;gap:5px;justify-content:flex-end}
.hbstack{width:100%;max-width:26px;display:flex;flex-direction:column;justify-content:flex-end;border-radius:3px 3px 0 0;overflow:hidden}
.hbseg{width:100%}
.hbx{font-size:10px;color:var(--faint);font-variant-numeric:tabular-nums}
.histm{font-size:11.5px;color:var(--muted);margin-top:12px}
.hbpair{display:flex;gap:2px;align-items:flex-end;height:92px}
.hbb{width:10px;border-radius:2px 2px 0 0}
.tvrow{display:flex;gap:10px;align-items:stretch}
.tvy{writing-mode:vertical-rl;transform:rotate(180deg);text-align:center;font-size:11.5px;color:var(--muted);flex:none;padding:2px 0}
.tvq{flex:1;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tvcell{border:1px solid var(--hair);border-radius:10px;padding:13px 15px;min-height:98px;display:flex;flex-direction:column;justify-content:center;background:var(--panel)}
.tvcell .n{font-family:var(--serif);font-size:29px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1;color:var(--ink)}
.tvcell .l{font-size:13.5px;font-weight:600;color:var(--ink);margin-top:6px}
.tvcell .p{font-size:11.5px;color:var(--muted);margin-top:3px}
.tvcell.good{background:rgba(12,163,12,0.06);border-color:rgba(12,163,12,0.28)} .tvcell.good .n{color:var(--ok)}
.tvcell.bad{background:rgba(208,59,59,0.05);border-color:rgba(208,59,59,0.25)} .tvcell.bad .n{color:var(--val)}
.tvx{text-align:center;font-size:11.5px;color:var(--muted);margin-top:12px}
.inote{margin-top:16px;padding-top:13px;border-top:1px solid var(--hair);font-size:12px;color:var(--muted);line-height:1.65}
.inote b{color:var(--ink);font-weight:600}
</style>
<div class="wrap">
<p class="eyebrow">Assessment of Healthcare Research Quality &middot; Saudi Arabia</p>
<h1>Reporting versus validity: how good is the research?</h1>
<p class="lede">Every scored item is judged on two axes &mdash; whether the study <b>reported</b> enough to be judged, and whether, given what it reported, it is <b>valid</b>. Each study &times; domain resolves to one of four states. Across the <b>__NT__ scored papers</b> (__NC__ causal, __ND__ descriptive; predictive studies carry no bias items and are excluded), __CLEANSENT__</p>
<div class="stats">
<div class="stat"><div class="v">__NT__</div><div class="k">papers scored (__NC__ causal &middot; __ND__ descriptive)</div></div>
<div class="stat"><div class="v">__CLEAN__</div><div class="k">clean papers &mdash; zero domains flagged</div></div>
<div class="stat"><div class="v">__GE3__%</div><div class="k">carry a validity flaw in &ge;3 domains</div></div>
<div class="stat"><div class="v">__MT__ / __MV__</div><div class="k">median transparency / validity index</div></div>
</div>

<section>
<div class="sh">Four-state verdict by domain and task</div>
<div class="sd">Each domain is rolled up by the <b>weakest link</b> &mdash; flagged if any constituent item is. The right-hand number is the share of <b>applicable</b> papers carrying a <b>validity flaw</b>; the bar itself is over all papers of that task, so its grey N/A segment is outside that denominator. Amber (reporting gap) marks studies too opaque to judge, not studies shown to be biased.</div>
<div class="key">
<span><span class="sq" style="background:var(--ok)"></span>No issue</span>
<span><span class="sq" style="background:var(--rep)"></span>Reporting gap</span>
<span><span class="sq" style="background:var(--val)"></span>Validity flaw</span>
<span><span class="sq" style="background:var(--na)"></span>N/A (census / not applicable)</span>
<span style="margin-left:auto"><b style="color:var(--muted)">D</b> descriptive &middot; <b style="color:var(--muted)">C</b> causal</span>
</div>
<div class="panel">__BARS__</div>
</section>

<section>
<div class="sh">Secondary scoring &mdash; additive severity</div>
<div class="sd">The weakest-link flag collapses each domain to yes/no; the additive count keeps the gradient. Two scores per paper &mdash; a <b style="color:var(--val)">validity score</b> (demonstrated flaws) and a <b style="color:var(--rep)">transparency score</b> (reporting gaps). It adds the most where a domain has several scored items &mdash; above all measurement &mdash; and at the study level, where the burden spreads across a wide range.</div>
<div class="panel">
<div class="subh">Mean issues per paper, by domain</div>
<div class="key"><span><span class="sq" style="background:var(--val)"></span>validity flaws</span><span><span class="sq" style="background:var(--rep)"></span>reporting gaps</span><span style="margin-left:auto">bars share a 0&ndash;__SCALE__ scale &middot; <b style="color:var(--muted)">D</b> descriptive &middot; <b style="color:var(--muted)">C</b> causal</span></div>
__SECBARS__
</div>
<div class="panel" style="margin-top:14px">
<div class="subh">Study-level score distribution <span style="font-weight:400;color:var(--faint)">&mdash; side-by-side bars, % of each task&rsquo;s papers at each score (light = descriptive, dark = causal)</span></div>
<div class="histwrap">
<div class="hist"><div class="histt">Validity error score &mdash; flaws per paper</div><div class="hbrow">__VHIST__</div><div class="histm">causal mean __MVC__ &middot; descriptive mean __MVD__ &middot; range 0&ndash;__MAXV__</div></div>
<div class="hist"><div class="histt">Transparency score &mdash; reporting gaps per paper</div><div class="hbrow">__RHIST__</div><div class="histm">causal mean __MRC__ &middot; descriptive mean __MRD__ &middot; range 0&ndash;__MAXR__</div></div>
</div>
</div>
</section>

<section>
<div class="sh">How much does the &ldquo;not reported&rdquo; ruling move each domain?</div>
<div class="sd">Red is the share with a demonstrated <b>validity flaw</b>; the amber extension adds every <b>reporting gap</b> (the old &ldquo;not reported = biased&rdquo; convention) &mdash; so the true rate is bracketed by the two. Validity-driven domains barely move; <b>random error</b> and <b>missing data</b> swing widely, because their apparent &ldquo;problem&rdquo; is largely unreported detail, not proven bias.</div>
<div class="panel">__SENS__</div>
</section>

<section>
<div class="sh">Transparency &times; validity</div>
<div class="sd">Every study placed by two scores: <b>transparency</b> &mdash; how completely it reports (left&rarr;right) &mdash; and <b>validity</b> &mdash; how many judgeable checks it passes (bottom&rarr;top). Split at the median of each (transparency __MT__, validity __MV__), the __NT__ studies fall into four groups.</div>
<div class="panel">
<div class="tvrow">
<div style="display:flex;flex-direction:column;justify-content:space-between;text-align:right;font-size:10.5px;color:var(--faint);flex:none;padding:4px 6px 4px 0;line-height:1.3"><span>&#9650; more<br>checks<br>passed</span><span>fewer<br>&#9660;</span></div>
<div class="tvq">
<div class="tvcell"><div class="n">__QLH__</div><div class="l">Sound but under-reported</div><div class="p">passes checks, reports little &middot; __QLHP__%</div></div>
<div class="tvcell good"><div class="n">__QHH__</div><div class="l">Transparent &amp; sound</div><div class="p">high on both &middot; __QHHP__%</div></div>
<div class="tvcell bad"><div class="n">__QLL__</div><div class="l">Opaque &amp; flawed</div><div class="p">low on both &middot; __QLLP__%</div></div>
<div class="tvcell bad"><div class="n">__QHL__</div><div class="l">Transparent but flawed</div><div class="p">reports well, fails checks &middot; __QHLP__%</div></div>
</div>
</div>
<div class="tvx">&larr; reports less &nbsp;&nbsp;&middot;&nbsp;&nbsp; <b>Transparency</b> &mdash; completeness of reporting &nbsp;&nbsp;&middot;&nbsp;&nbsp; reports more &rarr;</div>
</div>
</section>

<section>
<div class="sh">Do authors acknowledge the flaw they carry?</div>
<div class="sd">For each domain we take <b>only the studies we flagged with a validity flaw</b> (studies scored &ldquo;no issue&rdquo; are excluded, even when they mention the error), then ask what share named that error in their own limitations. The bar fills to the acknowledged share; <b>n / N</b> is acknowledged out of flagged.</div>
<div class="panel">__INS__
<div class="inote"><b>Verifying the base (Yasser&rsquo;s check).</b> The denominator is strictly the flagged studies &mdash; e.g. __CFOKMENT__ confounding-<i>sound</i> papers do mention confounding and are correctly excluded. Of the __CFN__ confounding-flagged papers, __CFNOADJ__ made <b>no adjustment at all</b> (__CFNOADJACK__ acknowledged) and __CFADJ__ <b>ran an adjustment but chose confounders by weak / data-driven criteria</b> (__CFADJACK__ acknowledged). So most acknowledging papers did perform some adjustment &mdash; whether that second group should count as a confounding flaw is a scoring choice worth confirming.</div>
</div>
</section>

<p class="foot"><b>Framework.</b> States: <span class="pf" style="background:var(--ok)"></span>no issue &middot; <span class="pf" style="background:var(--rep)"></span>reporting gap (an item answered &ldquo;not reported / unknown&rdquo; &mdash; opaque, not judgeable) &middot; <span class="pf" style="background:var(--val)"></span>validity flaw (reported, and biased) &middot; <span class="pf" style="background:var(--na)"></span>not applicable. A domain is flagged by the <b>weakest link</b> (any constituent item), with an additive per-item count kept as a secondary severity. <b>Not reported</b> is scored as its own reporting-gap state, not folded into validity &mdash; the sensitivity panel brackets the alternative.
<b>Conventions applied.</b> The two measurement-accounting items (<code>*_bias_acc</code>) <b>are scored, and they never pass</b> &mdash; the answer is &ldquo;No&rdquo; on 229 of 229 causal papers and 80 of 81 descriptive. They were held out until 2026-08-22, on the grounds that a constant cannot separate papers; they are now scored because a constant sitting at total failure is a finding rather than a nuisance. Measurement-bias prevalence therefore <b>saturates near 100&#37;</b>, and it is the graded severities, not the flag, that keep the domain discriminating; <code>base_sel</code> = &ldquo;No&rdquo; is a validity flaw (baseline selection bias present and not accounted for); randomization-only trials are exempt from the confounding flag under an intention-to-treat reading (two unadjusted per-protocol trials excepted); differential misclassification and dependent measurement errors count as validity flaws. Not yet applied: exposure-validation N/A for randomized interventions (so causal measurement is a mild upper bound), and the 36 missing-data handling GAPs remain N/A (worst-case they lift missing-data validity toward 23&#37;).
<b>Data.</b> The 2026-08-08 adjudicated dataset (385 papers; 310 with bias items). Generated by <code>code/figures/07_30_2026_gen_results_artifact.py</code> from the scored CSVs. Stratification by Saudi-affiliation variables and a SAS cross-check are pending.</p>
</div>'''

# ⚠ The lede used to END with the hardcoded words "only a handful clear every domain".
# Under the 2026-08-22 graded scoring that count is ZERO, so the sentence had become
# false while the statistic beside it was right - the failure mode where derived numbers
# update and the prose around them does not.  Derive the sentence from the same number.
_cleansent = ('<b>not one</b> clears every domain.' if clean == 0 else
              'exactly <b>one</b> clears every domain.' if clean == 1 else
              'only a handful &mdash; <b>%d</b> &mdash; clear every domain.' % clean if clean <= 15 else
              '<b>%d</b> clear every domain.' % clean)

# the two headline indices must still be what line 30 computed - see the rename above
assert abs(mt - tv.transparency.median()) < 1e-9, ('mt was clobbered', mt)
assert abs(mv - tv.validity.median())     < 1e-9, ('mv was clobbered', mv)

out=(PAGE.replace('__NT__',str(N_T)).replace('__NC__',str(N_C)).replace('__ND__',str(N_D))
     .replace('__CLEANSENT__',_cleansent)
     .replace('__CLEAN__',str(clean)).replace('__GE3__','%.0f'%(100*ge3/len(stu)))
     .replace('__MT__','%.2f'%mt).replace('__MV__','%.2f'%mv)
     .replace('__BARS__',bars).replace('__SENS__',sensbars)
     .replace('__HROWS__',hrows).replace('__HCOLS__',hcols)
     .replace('__QHH__',str(Q[('hi','hi')])).replace('__QHL__',str(Q[('hi','lo')]))
     .replace('__QLH__',str(Q[('lo','hi')])).replace('__QLL__',str(Q[('lo','lo')]))
     .replace('__INS__',insbars)
     .replace('__SCALE__','%.1f'%SCALE).replace('__SECBARS__',secbars)
     .replace('__VHIST__',vhist).replace('__RHIST__',rhist)
     .replace('__MVC__','%.1f'%mVc).replace('__MVD__','%.1f'%mVd)
     .replace('__MRC__','%.1f'%mRc).replace('__MRD__','%.1f'%mRd)
     .replace('__MAXV__',str(maxV)).replace('__MAXR__',str(maxR))
     .replace('__QHHP__',qp(('hi','hi'))).replace('__QHLP__',qp(('hi','lo')))
     .replace('__QLHP__',qp(('lo','hi'))).replace('__QLLP__',qp(('lo','lo')))
     .replace('__CFN__',str(CFN)).replace('__CFNOADJ__',str(CF_noadj)).replace('__CFADJ__',str(CF_adj))
     .replace('__CFNOADJACK__',str(CF_noadj_ack)).replace('__CFADJACK__',str(CF_adj_ack)).replace('__CFOKMENT__',str(CF_ok_ment)))
open('outputs/reports/07_30_2026_quality_scoring_results.html','w',encoding='utf-8').write(out)
print('wrote outputs/reports/07_30_2026_quality_scoring_results.html')
print('scored',N_T,'| clean',clean,'| >=3 flagged %.0f%%'%(100*ge3/len(stu)),'| med T/V %.2f/%.2f'%(mt,mv))
print('quadrants HH/HL/LH/LL',Q[('hi','hi')],Q[('hi','lo')],Q[('lo','hi')],Q[('lo','lo')])
print('sens',[(d,round(p),round(u)) for d,_,p,u in sens])
