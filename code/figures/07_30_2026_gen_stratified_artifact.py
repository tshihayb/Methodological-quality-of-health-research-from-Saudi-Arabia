# -*- coding: utf-8 -*-
# Stratified quality artifact, SPLIT BY TASK (descriptive/causal) with BOTH axes (validity flaws + reporting gaps).
# Run: PYTHONUTF8=1 python code/figures/07_30_2026_gen_stratified_artifact.py
import pandas as pd, html as H
KA=dict(keep_default_na=False, na_values=[''])
summ=pd.read_csv('data/scoring/07_30_2026_stratified_summary.csv', **KA)
doms=pd.read_csv('data/scoring/07_30_2026_stratified_domains.csv', **KA)

STRATS=[('Saudi data used',['Yes','No'],'is the study&rsquo;s data from Saudi Arabia?'),
 ('Number of authors',['1-2','3-10','11+'],'team size (authors with a real surname)'),
 ('% Saudi authors',['>=50%','<50%'],'share of authors with a Saudi affiliation'),
 ('Corresponding author',['Saudi','Non-Saudi'],'corresponding author&rsquo;s affiliation'),
 ('First author',['Saudi','Non-Saudi'],'first author&rsquo;s affiliation'),
 ('Last author',['Saudi','Non-Saudi'],'last author&rsquo;s affiliation'),
 ('Sector composition',['Academic-only','Health-system'],'any Saudi author at a hospital, medical city, MoH, or military-health body vs university/academic only'),
 ('Single vs multi-sector',['Single-sector','Multi-sector'],'do the paper&rsquo;s Saudi authors span more than one institution type?'),
 ('JCR 2022 quartile',['Q1','Q2','Q3','Q4','None'],'Clarivate JCR 2022 impact-factor quartile'),
 ('Funding',['Funded','Declared none','Not stated'],'funding as adjudicated by the authors on 2026-08-25 &mdash; &ldquo;declared none&rdquo; is an explicit statement that the work was unfunded, and &ldquo;not stated&rdquo; is what is left after that declaration is counted, not the transparency figure')]
DDESC=['Random error','Selection bias','Measurement bias','Missing data','Conflating task','Mentioning errors']
DCAUS=['Random error','Selection bias','Measurement bias','Confounding bias','Missing data','Mentioning errors']
# ⚠ 2026-08-26: these were hardcoded at 4.5 / 3.0 and the 2026-08-22 graded re-scoring roughly
# DOUBLED the validity scores - 28 of the 56 rows then sat above 4.5, so every causal bar was
# pinned at 100% width and carried no information at all while its printed number stayed right.
# Derive both ceilings from the data with a little headroom, and assert that nothing clips.
def _ceil_half(x): return max(0.5, __import__("math").ceil(x * 2.0 + 0.4) / 2.0)
VMAX = _ceil_half(summ.mean_val_err.astype(float).max())
RMAX = _ceil_half(summ.mean_rep_gap.astype(float).max())
assert summ.mean_val_err.astype(float).max() <= VMAX, "validity bars clip"
assert summ.mean_rep_gap.astype(float).max() <= RMAX, "reporting bars clip"
LVLAB={'>=50%':'&ge;50%','Q1-Q2':'Q1&ndash;Q2','Q3-Q4':'Q3&ndash;Q4','None':'Not ranked','Academic-only':'Academic only','1-2':'1&ndash;2','3-10':'3&ndash;10'}
def llab(l): return LVLAB.get(l,l)
def srow(nm,lv,tk):
    r=summ[(summ.stratifier==nm)&(summ.level==lv)&(summ.task==tk)]; return r.iloc[0] if len(r) else None
def drow(nm,lv,tk,D):
    r=doms[(doms.stratifier==nm)&(doms.level==lv)&(doms.task==tk)&(doms.domain==D)]; return r.iloc[0] if len(r) else None
def lvls_for(nm,tk,lvs): return [l for l in lvs if srow(nm,l,tk) is not None and int(srow(nm,l,tk).N)>0]

def ebar(v,mx,col):
    return ('<span class="eb"><span class="ebt"><i style="width:%.0f%%;background:%s"></i></span>'
            '<span class="ebv">%.2f</span></span>'%(min(v/mx*100,100),col,v))
def summ_table(nm,tk,lvs):
    rows=''
    for l in lvs:
        r=srow(nm,l,tk)
        rows+=('<tr><th>%s</th><td class="n">%d</td><td>%s</td><td>%s</td></tr>'
               %(llab(l),int(r.N),ebar(float(r.mean_val_err),VMAX,'var(--val)'),ebar(float(r.mean_rep_gap),RMAX,'#e08a12')))
    return ('<table class="ssum"><thead><tr><th>Group</th><th>n</th>'
            '<th>Validity flaws / paper <span class="mut">(0&ndash;%.1f)</span></th>'
            '<th>Reporting gaps / paper <span class="mut">(0&ndash;%.0f)</span></th></tr></thead><tbody>%s</tbody></table>'
            %(VMAX,RMAX,rows))
def tint(pct,axis):
    c=(208,59,59) if axis=='v' else (224,138,18)
    a=0.07+0.80*pct/100; tc='#fff' if a>0.5 else 'var(--ink)'
    return '<td style="background:rgba(%d,%d,%d,%.2f);color:%s">%.0f</td>'%(c[0],c[1],c[2],a,tc,pct)
def matrix(nm,tk,lvs):
    doml=DDESC if tk=='Descriptive' else DCAUS
    top='<th rowspan="2" class="dh">Domain</th>'
    for l in lvs: top+='<th colspan="2" class="lvh">%s<span>n=%d</span></th>'%(llab(l),int(srow(nm,l,tk).N))
    sub=''.join('<th class="hv">flaw</th><th class="hr">gap</th>' for _ in lvs)
    body=''
    for D in doml:
        cells=''
        for l in lvs:
            d=drow(nm,l,tk,D)
            if d is None or int(d.applic)==0: cells+='<td class="z">&mdash;</td><td class="z">&mdash;</td>'; continue
            cells+=tint(float(d.val_pct),'v')+tint(float(d.rep_pct),'r')
        body+='<tr><th class="dn">%s</th>%s</tr>'%(H.escape(D),cells)
    return '<div class="tscroll"><table class="dmatrix"><thead><tr>%s</tr><tr>%s</tr></thead><tbody>%s</tbody></table></div>'%(top,sub,body)
def subpanel(nm,tk,lvs):
    lv=lvls_for(nm,tk,lvs)
    return ('<div class="subp"><div class="subph">%s studies <span class="mut">&mdash; compared across groups</span></div>%s'
            '<div class="mh">Validity-flaw <b style="color:var(--val)">%%</b> and reporting-gap <b style="color:#c9790f">%%</b> by domain '
            '<span class="mut">&mdash; of applicable papers; darker = higher</span></div>%s</div>'
            %(tk,summ_table(nm,tk,lv),matrix(nm,tk,lv)))
def section(nm,lvs,desc):
    return ('<section class="spanel"><div class="sh">%s</div><div class="sdesc">%s</div>%s%s</section>'
            %(H.escape(nm),desc,subpanel(nm,'Descriptive',lvs),subpanel(nm,'Causal',lvs)))
panels=''.join(section(nm,lvs,desc) for nm,lvs,desc in STRATS)

def g(nm,lv,tk,f):
    r=srow(nm,lv,tk); return float(r[f]) if r is not None else 0.0
dfs,dfn=g('First author','Saudi','Descriptive','mean_val_err'),g('First author','Non-Saudi','Descriptive','mean_val_err')
cfs,cfn=g('First author','Saudi','Causal','mean_val_err'),g('First author','Non-Saudi','Causal','mean_val_err')
dq12,dq34,dnone=g('JCR Q1-2 vs Q3-4','Q1-Q2','Descriptive','mean_val_err'),g('JCR Q1-2 vs Q3-4','Q3-Q4','Descriptive','mean_val_err'),g('JCR Q1-2 vs Q3-4','None','Descriptive','mean_val_err')
cq1=g('JCR 2022 quartile','Q1','Causal','mean_val_err')
hsc_r,acc_r=g('Sector composition','Health-system','Causal','mean_rep_gap'),g('Sector composition','Academic-only','Causal','mean_rep_gap')
hsd_v,acd_v=g('Sector composition','Health-system','Descriptive','mean_val_err'),g('Sector composition','Academic-only','Descriptive','mean_val_err')
msc_r,ssc_r=g('Single vs multi-sector','Multi-sector','Causal','mean_rep_gap'),g('Single vs multi-sector','Single-sector','Causal','mean_rep_gap')
t12c,t11c=g('Number of authors','1-2','Causal','mean_val_err'),g('Number of authors','11+','Causal','mean_val_err')

PAGE=r'''<title>Stratified quality by task &mdash; Saudi 2022 health research</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--val:#d03b3b;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,56px) 20px}
.wrap{max-width:1000px;margin:0 auto}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.6vw,34px);line-height:1.14;letter-spacing:-.01em;margin:0 0 14px;text-wrap:balance;max-width:24ch}
.lede{color:var(--muted);font-size:15.5px;max-width:72ch;margin:0 0 22px}
.lede b{color:var(--ink);font-weight:600}
.callout{background:var(--accent-soft);border:1px solid var(--accent-line);border-radius:12px;padding:16px 18px;margin:0 0 34px;font-size:14px;color:var(--ink);line-height:1.65}
.callout b{color:var(--accent)}
.spanel{margin:0 0 30px;border-top:2px solid var(--hair-strong);padding-top:20px}
.sh{font-family:var(--serif);font-size:21px;font-weight:600;margin:0 0 2px}
.sdesc{color:var(--faint);font-size:12.5px;margin:0 0 16px}
.subp{margin:0 0 22px}
.subph{font-size:13.5px;font-weight:600;color:var(--ink);margin:0 0 10px}
.mut{color:var(--faint);font-weight:400;font-size:12px}
.mh{font-size:12px;color:var(--muted);margin:12px 0 8px}
.ssum{border-collapse:collapse;width:100%;font-size:12.5px;max-width:640px;margin:0 0 6px}
.ssum th{font-weight:600;color:var(--muted);text-align:left;padding:5px 10px;border-bottom:1px solid var(--hair);font-size:11.5px}
.ssum td,.ssum tbody th{padding:5px 10px;border-bottom:1px solid var(--hair);font-weight:400;color:var(--ink)}
.ssum td.n{color:var(--muted);font-variant-numeric:tabular-nums}
.eb{display:flex;align-items:center;gap:8px}
.ebt{flex:1;height:12px;max-width:180px;background:var(--row);border-radius:3px;overflow:hidden}
.ebt i{display:block;height:100%}
.ebv{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12px;min-width:30px}
.tscroll{overflow-x:auto;border:1px solid var(--hair);border-radius:11px;background:var(--panel)}
table.dmatrix{border-collapse:collapse;width:100%;font-size:12.5px;min-width:440px}
.dmatrix th{color:var(--muted);font-weight:600;padding:7px 9px;font-size:11px;white-space:nowrap;text-align:center}
.dmatrix .dh{text-align:left;vertical-align:bottom;border-bottom:2px solid var(--hair-strong)}
.dmatrix .lvh{border-bottom:1px solid var(--hair);border-left:2px solid var(--paper)}
.dmatrix .lvh span{display:block;font-size:9.5px;color:var(--faint);font-weight:400}
.dmatrix .hv{color:var(--val);border-bottom:2px solid var(--hair-strong);font-size:10px;font-weight:600;border-left:2px solid var(--paper)}
.dmatrix .hr{color:#c9790f;border-bottom:2px solid var(--hair-strong);font-size:10px;font-weight:600}
.dmatrix tbody th.dn{text-align:left;font-weight:400;color:var(--ink);font-size:12.5px;padding:7px 10px;border-bottom:1px solid var(--hair);white-space:nowrap}
.dmatrix td{padding:7px 9px;text-align:center;font-variant-numeric:tabular-nums;font-weight:500;border-bottom:1px solid var(--hair)}
.dmatrix td.z{color:var(--faint);background:var(--row);font-weight:400}
.dmatrix .hv,.dmatrix td:nth-child(even){border-left:2px solid var(--paper)}
.foot{margin-top:8px;color:var(--faint);font-size:12.5px;line-height:1.6;max-width:92ch}
.foot b{color:var(--muted)} .foot code{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
</style>
<div class="wrap">
<p class="eyebrow">Assessment of Healthcare Research Quality &middot; Saudi Arabia</p>
<h1>Does research quality differ by group?</h1>
<p class="lede">The scoring of the <b>310 papers</b>, stratified by Saudi involvement, <b>team size</b>, <b>institutional sector</b>, and <b>JCR 2022</b> quartile &mdash; and split by study task, so <b>descriptive papers are compared across groups and causal papers across groups</b> (the two carry different numbers of items, so pooling them would confound any comparison). Each domain shows both the <b style="color:var(--val)">validity-flaw</b> rate and the <b style="color:#c9790f">reporting-gap</b> rate.</p>
<div class="callout"><b>Splitting by task corrects the pooled read.</b> The apparent &ldquo;Saudi-led = higher error&rdquo; was mostly a task-mix effect. <b>Within task the gaps are small and mixed:</b> Saudi-first <i>descriptive</i> papers are marginally cleaner (__DFS__ vs __DFN__ flaws), Saudi-first <i>causal</i> marginally worse (__CFS__ vs __CFN__). The clearest real signal is for <b>descriptive</b> studies, where higher-JCR journals carry fewer validity flaws (Q1&ndash;2 __DQ12__ vs Q3&ndash;4 __DQ34__ vs not-ranked __DNONE__); <b>causal</b> studies stay uniformly high-flaw regardless of quartile (Q1 is among the worst at __CQ1__). Reporting gaps track validity but flatter, and not-ranked journals are worst on both. <b>Institutional structure adds a second signal:</b> papers whose Saudi authors include a hospital, medical city, MoH, or military-health body are consistently cleaner &mdash; fewer reporting gaps on both tasks (causal __HSC_R__ vs __ACC_R__) and fewer <i>descriptive</i> validity flaws (__HSD_V__ vs __ACD_V__); cross-sector (multi-sector) collaboration mostly matches single-sector work, edging it only on causal reporting (__MSC_R__ vs __SSC_R__). <b>Team size</b> adds a faint gradient &mdash; smaller teams are marginally more error-prone (causal 1&ndash;2 authors __T12C__ vs 11+ __T11C__). All within-task and associational.</div>
__PANELS__
<p class="foot"><b>Outcomes.</b> <i>Validity flaws / paper</i> and <i>reporting gaps / paper</i> are the additive counts over that paper&rsquo;s scored items (descriptive papers carry fewer items than causal, so the two tasks are shown separately and must not be compared to each other). <i>Domain cells</i> = share of <b>applicable</b> papers with &ge;1 validity flaw (red) or &ge;1 reporting gap (amber) in that domain. Some task&ndash;domain cells have no items on one axis and so read 0 by construction: descriptive <i>selection</i> / <i>measurement</i> carry no reporting items, <i>conflating</i> is validity-only, and <i>mentioning errors</i> is reporting-only. <b>Groups.</b> Saudi first/corresponding/last = that author has any Saudi affiliation (positions are ~redundant, corresponding &asymp; first 91&#37;); JCR is the Clarivate 2022 quartile, 66/310 in journals with no ranking. <i>Number of authors</i> = team size, counting only authors with a real surname, collapsed to 1&ndash;2 / 3&ndash;10 / 11+. <i>Sector composition</i> = <b>Health-system</b> if any Saudi author sits at a hospital / medical city, KFSHRC, Ministry of Health, or military/security-forces health body (99 papers), else <b>Academic only</b> (university, college, or research institute; 211). <i>Single vs multi-sector</i> = whether the paper&rsquo;s Saudi authors span more than one institution type (66 multi-sector). Both come from the paper-level sector map behind the <code>outputs/reports/07_25_2026_saudi_institutions_artifact.html</code>; every one of the 310 scored papers resolved to a sector. The sector cuts are <b>observational and confounded</b> (sector correlates with topic, journal, and team size), so read them as associations within task, not effects. Small task&times;group strata (e.g. Q4, JCR causal n=19) are noisy &mdash; read with the n. <b>Data.</b> Scored 2026-07-23 dataset; <code>code/scoring/07_30_2026_stratified_analysis.R</code> + <code>code/figures/07_30_2026_gen_stratified_artifact.py</code>. Formal group tests not yet applied.</p>
</div>'''
out=(PAGE.replace('__PANELS__',panels)
     .replace('__DFS__','%.2f'%dfs).replace('__DFN__','%.2f'%dfn)
     .replace('__CFS__','%.2f'%cfs).replace('__CFN__','%.2f'%cfn)
     .replace('__DQ12__','%.2f'%dq12).replace('__DQ34__','%.2f'%dq34).replace('__DNONE__','%.2f'%dnone)
     .replace('__CQ1__','%.2f'%cq1)
     .replace('__HSC_R__','%.2f'%hsc_r).replace('__ACC_R__','%.2f'%acc_r)
     .replace('__HSD_V__','%.2f'%hsd_v).replace('__ACD_V__','%.2f'%acd_v)
     .replace('__MSC_R__','%.2f'%msc_r).replace('__SSC_R__','%.2f'%ssc_r)
     .replace('__T12C__','%.2f'%t12c).replace('__T11C__','%.2f'%t11c))
open('outputs/reports/07_30_2026_stratified_results.html','w',encoding='utf-8').write(out)
print('wrote outputs/reports/07_30_2026_stratified_results.html')
print('desc first S/NS %.2f/%.2f | causal first S/NS %.2f/%.2f | desc JCR Q12/Q34/None %.2f/%.2f/%.2f | causal Q1 %.2f'%(dfs,dfn,cfs,cfn,dq12,dq34,dnone,cq1))
