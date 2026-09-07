# NOTE (public repository): 7 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""ITT vs per-protocol estimands for every RCT-related paper whose adjudicated exposure IS the randomised treatment."""
import pandas as pd, html as H

df = pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv', dtype=str)
p = df[df.Study_Type == 'Causal'].pivot_table(index='PMID', columns='variable', values='final', aggfunc='first')
bcm = p.causal_base_conf_meth.fillna('')
p['is_rct'] = p.causal_design.astype(str).str.startswith('Randomized clinical trial')
# NB: match Randomization as a whole selected option, NOT a substring -- the IV option label
# ('Instrumental variable analysis besides randomization (...)') also contains the word.
p['rand']   = bcm.map(lambda v: any(x.strip().lower()=='randomization' for x in str(v).split(';')))
p['randonly'] = bcm.str.strip().str.lower() == 'randomization'
sel = sorted(p[p.is_rct | p.rand].index)

s = pd.read_csv('data/adjudication/07_22_2026_rct_analysis_pop_screen.csv'); s['pmid'] = s.pmid.astype(str); s = s.set_index('pmid')
a = pd.concat([pd.read_excel('private/reviewers/papers_assignment_strat.xlsx'), pd.read_excel('private/reviewers/papers_assignment_strat_2.xlsx')])
a['PMID'] = a.PMID.astype(str); a = a.set_index('PMID')

def grp(i, r):
    if r.is_rct and r.randonly: return 'A'
    if r.is_rct and r.rand:     return 'D'
    if r.is_rct:                return 'B'
    return 'C'

rows = []
for i in sel:
    r = p.loc[i]
    g = grp(i, r)
    title = str(a.loc[i, 'Title'])[:70] if i in a.index else ''
    base_m = r.causal_base_conf_meth if pd.notna(r.causal_base_conf_meth) else '—'
    tv_m   = r.causal_tv_conf_meth if pd.notna(r.causal_tv_conf_meth) else 'skipped (no time-varying effect estimated)'
    if i not in s.index:
        rows.append(dict(pmid=i, g=g, title=title, temporal='—', b_itt='not screened', b_pp='not screened',
                         tv_itt='not screened', tv_pp='not screened', base_m=base_m, tv_m=tv_m, cls='unscreened', ord=3))
        continue
    sc = s.loc[i]
    pop = str(sc.primary_analysis_population); pp = str(sc.reports_any_pp_or_astreated).lower() == 'yes'
    temporal = str(sc.treatment_temporal); adj = str(sc.pp_adjustment)
    kind = 'naive — no adjustment' if adj.lower().startswith('none') else ('baseline-covariate adjustment only' if adj != 'nan' else '')
    b_itt = ('Yes' if pop == 'ITT' else
             'Yes <span class="sub">(implied — zero attrition)</span>' if pop == 'Not-reported' else
             '<span class="no">No</span> <span class="sub">— %s</span>' % pop)
    b_pp  = ('<b>Yes</b> — %s<br><span class="sub">%s</span>' % (pop, kind)) if (pp and temporal == 'point') else '—'
    tv_itt = 'No'
    tv_pp = ('<b>Yes</b> — %s<br><span class="sub">%s · <b class="no">no g-method</b></span>' % (pop, kind)) if (pp and temporal == 'sustained') else '—'
    cls = 'tvpp' if (pp and temporal == 'sustained') else ('bpp' if pp else 'itt')
    order = 0 if cls == 'tvpp' else (1 if cls == 'bpp' else 2)
    rows.append(dict(pmid=i, g=g, title=title, temporal=temporal, b_itt=b_itt, b_pp=b_pp, tv_itt=tv_itt,
                     tv_pp=tv_pp, base_m=base_m, tv_m=tv_m, cls=cls, ord=order))

rows.sort(key=lambda r: (r['ord'], r['pmid']))
n_itt = sum(1 for r in rows if r['cls'] == 'itt'); n_bpp = sum(1 for r in rows if r['cls'] == 'bpp')
n_tv = sum(1 for r in rows if r['cls'] == 'tvpp'); n_un = sum(1 for r in rows if r['cls'] == 'unscreened')

body = ''
for r in rows:
    body += ('<tr class="%s"><th scope="row"><span class="pm">%s</span><span class="tags">'
             '<span class="gg g%s">%s</span>%s</span><span class="ti">%s</span></th>'
             '<td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class="mth">%s</td><td class="mth">%s</td></tr>') % (
        r['cls'], r['pmid'], r['g'], r['g'],
        ('<span class="tmp">%s</span>' % r['temporal']) if r['temporal'] != '—' else '',
        H.escape(r['title']), r['b_itt'], r['b_pp'], r['tv_itt'], r['tv_pp'],
        H.escape(str(r['base_m'])), H.escape(str(r['tv_m'])))

PAGE = '''<title>ITT versus per-protocol estimands in the randomised trials</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--prob:#a6432a;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--prob:#a6432a;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,60px) 20px}
.wrap{max-width:1180px;margin:0 auto}
.tabtag{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line);padding:3px 9px;border-radius:5px;margin:0 0 12px}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.4vw,32px);line-height:1.14;margin:0 0 14px;max-width:28ch}
.lede{color:var(--muted);font-size:15px;max-width:76ch;margin:0 0 18px}
.lede b{color:var(--ink);font-weight:600}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 22px}
.card{border:1px solid var(--hair);border-radius:9px;padding:9px 14px;background:var(--panel);min-width:150px}
.card .n{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums}
.card .l{font-size:11.5px;color:var(--muted)}
.card.hot{border-color:var(--prob)} .card.hot .n{color:var(--prob)}
.tscroll{overflow-x:auto;border:1px solid var(--hair);border-radius:11px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:1080px}
thead th{position:sticky;top:0;background:var(--panel);text-align:left;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);font-weight:600;padding:11px 13px 9px;border-bottom:2px solid var(--ink);vertical-align:bottom}
thead th.grp{background:var(--totbg);color:var(--accent)}
tbody th[scope="row"]{text-align:left;font-weight:400;padding:9px 13px;vertical-align:top;border-top:1px solid var(--hair);position:sticky;left:0;background:var(--panel);min-width:250px}
tbody td{padding:9px 13px;vertical-align:top;border-top:1px solid var(--hair)}
tbody td.mth{background:var(--totbg);font-size:12px;color:var(--muted)}
.pm{font-weight:700;font-variant-numeric:tabular-nums;margin-right:7px}
.ti{display:block;color:var(--faint);font-size:11.5px;margin-top:2px;line-height:1.35}
.tags{display:inline-flex;gap:5px;vertical-align:middle}
.gg,.tmp{font-size:9.5px;letter-spacing:.04em;text-transform:uppercase;font-weight:700;padding:1px 5px;border-radius:4px;border:1px solid var(--hair-strong);color:var(--muted)}
.gA{color:var(--accent);border-color:var(--accent-line);background:var(--accent-soft)}
.tmp{font-weight:600;border-style:dotted;color:var(--faint)}
.sub{color:var(--faint);font-size:11.5px}
.no{color:var(--prob);font-weight:700}
tr.tvpp th[scope="row"],tr.tvpp td{background:rgba(166,67,42,.05)}
tr.bpp th[scope="row"],tr.bpp td{background:rgba(166,67,42,.03)}
tr.unscreened th[scope="row"],tr.unscreened td{color:var(--faint);font-style:italic}
tbody tr:hover th[scope="row"],tbody tr:hover td{background:var(--row)}
.foot{margin-top:20px;color:var(--faint);font-size:12.5px;max-width:96ch;line-height:1.6}
.foot b{color:var(--muted)}
.foot code{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
</style>
<div class="wrap">
<span class="tabtag">RCT estimands</span>
<p class="eyebrow">Assessment of Healthcare Research Quality &middot; Saudi Arabia</p>
<h1>ITT versus per-protocol estimands in the randomised trials</h1>
<p class="lede">All <b>__N__ papers</b> that are randomised by design or record <i>Randomization</i> as an adjustment method, and whose <b>adjudicated exposure is the randomised treatment</b> (verified for the 27 previously screened). Whether a per-protocol effect is a <b>baseline</b> or a <b>time-varying</b> estimand depends on the treatment: for a <b>point</b> intervention adherence is settled at baseline, whereas for a <b>sustained</b> strategy the per-protocol effect is inherently time-varying and requires g-methods.</p>
<div class="cards">
<div class="card"><div class="n">__NITT__</div><div class="l">ITT only &mdash; no per-protocol effect</div></div>
<div class="card hot"><div class="n">__NBPP__</div><div class="l">Baseline per-protocol (point treatment)</div></div>
<div class="card hot"><div class="n">__NTV__</div><div class="l">Time-varying per-protocol (sustained)</div></div>
<div class="card"><div class="n">0</div><div class="l">Time-varying ITT estimated</div></div>
<div class="card"><div class="n">__NUN__</div><div class="l">Not yet screened</div></div>
</div>
<div class="tscroll"><table>
<thead><tr><th>Paper</th><th>Baseline ITT</th><th>Baseline per-protocol<br>(which type)</th><th>Time-varying ITT</th><th>Time-varying per-protocol<br>(which type)</th><th class="grp">Baseline adjustment method<br>(as recorded)</th><th class="grp">Time-varying adjustment method<br>(as recorded)</th></tr></thead>
<tbody>__BODY__</tbody></table></div>
<p class="foot"><b>Groups.</b> <code>A</code> = design RCT with Randomization as the only adjustment method (24) &middot; <code>D</code> = RCT with Randomization plus another method (2) &middot; <code>B</code> = design RCT but Randomization not recorded (1, PMID STUDY-0499) &middot; <code>C</code> = Randomization recorded but design labelled Cohort (2, PMIDs STUDY-0431 &amp; STUDY-0385 &mdash; confirmed randomised by full text, so their design label is what is wrong).
<b>Why time-varying ITT is empty here &mdash; and what it would take to fill it.</b> A time-varying ITT effect is perfectly possible, in two senses. <b>(1) A time-varying <i>effect</i> of a point exposure:</b> assignment happens once, but the outcome is measured repeatedly, so the assignment effect is indexed by time and may grow, wane or reverse (survival-curve contrasts, non-proportional hazards, an arm&times;time interaction in MMRM/GEE). This needs <b>no</b> time-varying confounding control &mdash; randomisation keeps assignment independent of the potential outcomes at every time, and conditioning on post-baseline variables would <i>introduce</i> bias; the live threat is informative censoring, handled by IPCW or imputation. Four of these trials did fit such models (STUDY-0669 GEE, STUDY-0764 repeated-measures ANOVA, STUDY-0567 mixed models, STUDY-0783 MMRM) and still correctly recorded <code>time_verying</code>=&#8220;No&#8221;. <b>(2) Sequentially randomised (SMART) designs,</b> where assignment itself repeats: the exposure genuinely is time-varying, and comparing sustained regimes still requires g-methods even though everything is randomised (Hern&aacute;n &amp; Robins, Table 20.1) &mdash; though the weights are known by design. <b>No trial in this sample is a SMART</b>, which is why the column is empty. Read <code>time_verying</code> as &#8220;time-varying <i>exposure</i> requiring time-varying confounding control&#8221;, not &#8220;effect estimated at several timepoints&#8221;.
<b>Time-varying ITT versus time-varying per-protocol.</b> The phrase attaches to different objects: under ITT the <i>effect</i> varies over time while the exposure (assignment) stays a baseline point exposure; under per-protocol the <i>exposure itself</i> varies over time. Hence the opposite handling of post-baseline variables &mdash; under ITT you must <b>not</b> adjust for them, whereas under per-protocol you <b>must</b>, but only via g-methods, because adherence is driven by time-varying confounders that prior treatment itself affects.
<b>Why the per-protocol column splits.</b> Under Hern&aacute;n &amp; Robins (Ch. 22), the per-protocol effect of a <b>sustained</b> strategy demands g-methods (IPW with marginal structural models, the parametric g-formula, doubly-robust estimation, or g-estimation), because adherence over time is affected by prior treatment and by time-varying confounders. <b>None of the four sustained-treatment trials used any g-method</b> &mdash; two adjusted only for baseline covariates and two were fully naive &mdash; so none of them validly estimated the per-protocol effect they reported. The two <b>point</b>-treatment per-protocol analyses are baseline/attrition-driven selection instead, and both are naive; note this overlaps the loss-to-follow-up domain, so it should not be double-counted as confounding.
<b>Reading the last two columns.</b> These are what the review tool recorded, not what the paper did &mdash; the contrast with the estimand columns is the point. A trial that reports a per-protocol effect while recording &#8220;Randomization&#8221; as its only adjustment method has, in substance, an unadjusted analysis of a non-randomised comparison.</p>
</div>'''
PAGE = (PAGE.replace('__BODY__', body).replace('__N__', str(len(rows))).replace('__NITT__', str(n_itt)).replace('__NBPP__', str(n_bpp))
            .replace('__NTV__', str(n_tv)).replace('__NUN__', str(n_un)))
open('outputs/reports/07_23_2026_rct_itt_vs_perprotocol.html', 'w', encoding='utf-8').write(PAGE)
print('rows=%d | ITT-only=%d  baselinePP=%d  time-varyingPP=%d  unscreened=%d' % (len(rows), n_itt, n_bpp, n_tv, n_un))
print('wrote outputs/reports/07_23_2026_rct_itt_vs_perprotocol.html')
