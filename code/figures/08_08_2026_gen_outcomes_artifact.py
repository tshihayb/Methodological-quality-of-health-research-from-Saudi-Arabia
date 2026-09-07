# -*- coding: utf-8 -*-
# Build the determined-outcomes artifact (combined + stratified by task) for the 385.
# NOTE: 'adjudicated' is a PROVENANCE BADGE here, true of the 310 descriptive+causal outcomes
# only. Never apply it to all 385 -- the 75 predictive outcomes are machine-determined and
# unverified. Use 'determined outcome' when speaking of the whole sample.
# Run: PYTHONUTF8=1 python code/figures/08_08_2026_gen_outcomes_artifact.py
import csv, json, html as H
S=json.load(open("data/outcomes/08_08_2026_outcomes_summary.json",encoding="utf-8"))
rowsall=list(csv.DictReader(open("data/outcomes/08_08_2026_all_outcomes_classified.csv",encoding="utf-8-sig")))
TASKS=["Descriptive","Causal","Predictive"]
TT=S["task_totals"]; N=sum(TT.values())
CATORDER=["1.1","1.2","1.3","1.4","1.5","2.1","2.2","2.3","3.1","3.2","3.3","4.1","OTHER"]
DOMS=["1","2","3","4","9"]
DCOL={"1":"#16697a","2":"#d98324","3":"#7a6ca8","4":"#3f8f7a","9":"#9aa3a7"}
DOMLAB={"1":"Clinical / biomedical","2":"Patient-reported & functional","3":"Knowledge, attitudes & behaviors","4":"Health-system & process","9":"Other"}
def cat(c): return S["cat"][c]
def dom(d): return S["dom"][d]
def pct(a,b): return (100.0*a/b) if b else 0.0

# ---------- combined distribution (domain-grouped bars) ----------
maxcat=max(cat(c)["total"] for c in CATORDER)
comb=""
for d in DOMS:
    cats=[c for c in CATORDER if cat(c)["domain"]==d and cat(c)["total"]>0]
    if not cats: continue
    comb+='<div class="domgrp"><div class="domhd"><span class="dot" style="background:%s"></span>%s <span class="dn">%d papers · %.0f%%</span></div>'%(
        DCOL[d],H.escape(DOMLAB[d]),dom(d)["total"],pct(dom(d)["total"],N))
    for c in cats:
        t=cat(c)["total"]
        comb+=('<div class="brow"><div class="blab">%s</div>'
               '<div class="bwrap"><span class="bbar" style="width:%.1f%%;background:%s"></span></div>'
               '<div class="bnum">%d<span class="bpct">%.1f%%</span></div></div>')%(
               H.escape(cat(c)["label"]),100.0*t/maxcat,DCOL[d],t,pct(t,N))
    comb+='</div>'

# ---------- domain x task 100% stacked ----------
def stacked(task):
    seg=""
    tot=TT[task]
    for d in DOMS:
        v=dom(d)["counts"][task]
        if v==0: continue
        seg+='<span class="seg" style="width:%.2f%%;background:%s" title="%s: %d (%.0f%%)"></span>'%(
            pct(v,tot),DCOL[d],DOMLAB[d],v,pct(v,tot))
    return seg
stackblock=""
for task in TASKS:
    stackblock+=('<div class="strow"><div class="stlab">%s <span class="stn">n=%d</span></div>'
                 '<div class="stbar">%s</div></div>')%(task,TT[task],stacked(task))
legend="".join('<span class="lg"><span class="dot" style="background:%s"></span>%s</span>'%(DCOL[d],H.escape(DOMLAB[d])) for d in DOMS if any(dom(d)["counts"][t] for t in TASKS))

# ---------- category x task matrix (count + within-task %) ----------
def tint(p):
    a=0.07+0.85*(p/100.0); tc="#fff" if a>0.55 else "var(--ink)"
    return "background:rgba(22,105,122,%.2f);color:%s"%(a,tc)
mrows=""
for c in CATORDER:
    if cat(c)["total"]==0: continue
    tds=""
    for task in TASKS:
        v=cat(c)["counts"][task]; p=pct(v,TT[task])
        tds+='<td style="%s">%d<span class="cp">%.0f%%</span></td>'%(tint(p) if v else "color:var(--faint);background:var(--row)",v,p)
    mrows+=('<tr><th class="cn"><span class="dot" style="background:%s"></span>%s</th>%s'
            '<td class="tot">%d</td></tr>')%(DCOL[cat(c)["domain"]],H.escape(cat(c)["label"]),tds,cat(c)["total"])

# ---------- browse-all table ----------
def srctag(s):
    return '<span class="tag ai">AI · unverified</span>' if s.startswith("machine") else '<span class="tag adj">adjudicated</span>'
brows=""
order={c:i for i,c in enumerate(CATORDER)}
for r in sorted(rowsall,key=lambda r:(TASKS.index(r["Study_Type"]),order.get(r["category"],99))):
    conf=r["confidence"]
    confbadge=('<span class="cf cf%s">%s</span>'%(conf[:1].upper(),conf)) if conf else ""
    brows+=('<tr data-task="%s" data-cat="%s" data-src="%s">'
            '<td class="pmid">%s</td><td><span class="tk tk%s">%s</span></td>'
            '<td class="oc">%s</td><td class="ct"><span class="dot" style="background:%s"></span>%s</td>'
            '<td>%s%s</td></tr>')%(
            r["Study_Type"],r["category"],("m" if r["source"].startswith("machine") else "a"),
            r["PMID"],r["Study_Type"][:1],r["Study_Type"],
            H.escape(r["outcome"]),DCOL.get(r["domain"],"#9aa3a7"),H.escape(r["cat_label"]),
            srctag(r["source"]),(" "+confbadge if confbadge else ""))

# headline numbers
nmach=sum(1 for r in rowsall if r["source"].startswith("machine"))
nadj=len(rowsall)-nmach
assert nmach+nadj==N, (nmach,nadj,N)
assert all(r["Study_Type"]=="Predictive" for r in rowsall if r["source"].startswith("machine")), \
    "a non-predictive row is machine-sourced -- the provisional-share wording assumes otherwise"
clin=dom("1")["total"]; kap=dom("3")["total"]
d_kap=sum(cat(c)["counts"]["Descriptive"] for c in ("3.1","3.2","3.3")); d_tot=TT["Descriptive"]
p_clin=sum(cat(c)["counts"]["Predictive"] for c in ("1.1","1.2","1.3","1.4","1.5")); p_tot=TT["Predictive"]
p_dx=cat("1.2")["counts"]["Predictive"]
c_ment=cat("2.2")["counts"]["Causal"]

PAGE=f'''<title>What Saudi health research measures &mdash; study outcomes</title>
<style>
:root{{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#5c6673;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e6eef0;--accent-line:#bcd6db;--hair:#e7e4dd;--hair-strong:#d5d1c7;--row:#f5f3ee;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}}
@media (prefers-color-scheme:dark){{:root{{--paper:#0f1418;--panel:#161b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#6f7987;--accent:#5bb5c6;--accent-soft:#15303a;--accent-line:#2b4a54;--hair:#242a32;--hair-strong:#333a44;--row:#1a1f26;}}}}
:root[data-theme="light"]{{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#5c6673;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e6eef0;--accent-line:#bcd6db;--hair:#e7e4dd;--hair-strong:#d5d1c7;--row:#f5f3ee;}}
:root[data-theme="dark"]{{--paper:#0f1418;--panel:#161b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#6f7987;--accent:#5bb5c6;--accent-soft:#15303a;--accent-line:#2b4a54;--hair:#242a32;--hair-strong:#333a44;--row:#1a1f26;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.55;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,56px) 20px}}
.wrap{{max-width:1020px;margin:0 auto}}
.eyebrow{{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(25px,3.7vw,36px);line-height:1.12;letter-spacing:-.01em;margin:0 0 14px;text-wrap:balance;max-width:26ch}}
.lede{{color:var(--muted);font-size:15.5px;max-width:74ch;margin:0 0 22px}}
.lede b{{color:var(--ink);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:22px 0 26px}}
.stat{{background:var(--panel);border:1px solid var(--hair);border-radius:12px;padding:14px 14px 12px}}
.statv{{font-family:var(--serif);font-size:clamp(20px,2.4vw,27px);font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}}
.statl{{font-size:11.5px;color:var(--muted);margin-top:3px;line-height:1.35}}
.callout{{background:var(--accent-soft);border:1px solid var(--accent-line);border-radius:12px;padding:16px 18px;margin:0 0 34px;font-size:14px;line-height:1.65}}
.callout b{{color:var(--accent)}}
section{{margin:0 0 30px;border-top:2px solid var(--hair-strong);padding-top:20px}}
h2{{font-family:var(--serif);font-size:22px;font-weight:600;margin:0 0 3px;letter-spacing:-.01em}}
.sub{{color:var(--faint);font-size:13px;margin:0 0 18px;max-width:80ch}}
.card{{background:var(--panel);border:1px solid var(--hair);border-radius:14px;padding:18px 20px}}
.domgrp{{margin:0 0 15px}}
.domhd{{display:flex;align-items:center;gap:8px;font-weight:600;font-size:13.5px;margin:2px 0 8px}}
.domhd .dn{{color:var(--faint);font-weight:400;font-size:12px}}
.dot{{width:10px;height:10px;border-radius:50%;flex:none;display:inline-block}}
.brow{{display:grid;grid-template-columns:275px 1fr auto;align-items:center;gap:12px;margin:5px 0 5px 18px}}
.blab{{font-size:13px;min-width:0}}
.bwrap{{background:var(--row);border-radius:5px;height:13px;overflow:hidden}}
.bbar{{display:block;height:100%;border-radius:5px}}
.bnum{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;font-size:13.5px;white-space:nowrap}}
.bpct{{color:var(--faint);font-weight:400;font-size:11.5px;margin-left:6px}}
.strow{{display:grid;grid-template-columns:120px 1fr;align-items:center;gap:14px;margin:10px 0}}
.stlab{{font-size:13.5px;font-weight:600}} .stn{{color:var(--faint);font-weight:400;font-size:12px}}
.stbar{{display:flex;height:26px;border-radius:6px;overflow:hidden;background:var(--row)}}
.seg{{height:100%}}
.legend{{display:flex;flex-wrap:wrap;gap:14px;margin:14px 0 2px 134px}}
.lg{{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--muted)}}
.tscroll{{overflow-x:auto;border:1px solid var(--hair);border-radius:12px;background:var(--panel)}}
table{{border-collapse:collapse;width:100%;font-size:13px;min-width:520px}}
.mtx th.cn{{text-align:left;font-weight:500;color:var(--ink);padding:8px 10px;border-bottom:1px solid var(--hair);white-space:nowrap;display:flex;align-items:center;gap:8px}}
.mtx thead th{{color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;padding:9px 10px;border-bottom:2px solid var(--hair-strong);text-align:center}}
.mtx thead th.l{{text-align:left}}
.mtx td{{padding:7px 10px;text-align:center;font-variant-numeric:tabular-nums;border-bottom:1px solid var(--hair);font-weight:600}}
.mtx td.tot{{color:var(--accent)}} .cp{{display:block;font-size:10px;font-weight:400;opacity:.75}}
#bt thead th{{position:sticky;top:0;background:var(--panel);text-align:left;font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;padding:10px;border-bottom:2px solid var(--hair-strong);cursor:pointer;white-space:nowrap;user-select:none}}
#bt tbody td{{padding:7px 10px;border-bottom:1px solid var(--hair);vertical-align:top}}
#bt tbody tr:hover{{background:var(--accent-soft)}}
.pmid{{font-variant-numeric:tabular-nums;color:var(--muted);font-size:12.5px}}
.oc{{max-width:420px}}
.tk{{font-size:11px;font-weight:600;padding:1px 7px;border-radius:20px;border:1px solid var(--hair-strong);white-space:nowrap}}
.tkD{{color:#8a6d1f;border-color:#d9b25e}} .tkC{{color:#166a5a;border-color:#59b39b}} .tkP{{color:#5a4a8c;border-color:#9a86c8}}
.ct{{white-space:nowrap}} .ct .dot{{margin-right:6px}}
.tag{{font-size:10.5px;font-weight:600;padding:1px 6px;border-radius:5px;white-space:nowrap}}
.tag.adj{{background:var(--accent-soft);color:var(--accent)}} .tag.ai{{background:rgba(217,131,36,.14);color:#c9790f}}
.cf{{font-size:10px;color:var(--faint);margin-left:2px}}
.filt{{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 12px}}
.filt button{{font:inherit;font-size:12.5px;padding:5px 12px;border:1px solid var(--hair-strong);background:var(--panel);color:var(--muted);border-radius:20px;cursor:pointer}}
.filt button.on{{background:var(--accent);color:#fff;border-color:var(--accent)}}
.notes{{background:var(--panel);border:1px solid var(--hair);border-radius:14px;padding:20px 24px;font-size:13px;color:var(--muted);line-height:1.6}}
.notes h3{{font-family:var(--serif);color:var(--ink);font-size:15.5px;margin:14px 0 7px}} .notes h3:first-child{{margin-top:0}}
.notes b{{color:var(--ink)}} .notes code{{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px;font-size:12px}}
.foot{{margin-top:24px;font-size:12px;color:var(--faint);text-align:center}}
@media(max-width:820px){{.stats{{grid-template-columns:repeat(2,1fr)}}.brow{{grid-template-columns:150px 1fr auto;margin-left:6px}}.strow{{grid-template-columns:1fr}}.legend{{margin-left:0}}.oc{{max-width:none}}}}
</style>
<div class="wrap">
<p class="eyebrow">Assessment of Healthcare Research Quality &middot; Saudi Arabia</p>
<h1>What Saudi health research measures</h1>
<p class="lede">The single determined <b>outcome</b> (dependent variable) of every one of the <b>{N} included papers</b>, sorted into <b>12 categories across 4 domains plus a residual <i>Other</i></b> &mdash; shown <b>combined</b> and <b>split by study task</b>. Outcomes for the {TT['Descriptive']} descriptive and {TT['Causal']} causal studies were <b>adjudicated by the two reviewers</b>; the {TT['Predictive']} predictive studies&rsquo; outcomes were <b>determined here by a large language model under the same rule and are provisional</b>, pending reviewer sign-off. Every count below mixes the two &mdash; the source of each is given in the table.</p>
<div class="stats">
<div class="stat"><div class="statv">{N}</div><div class="statl">papers, one outcome each</div></div>
<div class="stat"><div class="statv">{clin}</div><div class="statl">clinical / biomedical outcomes ({pct(clin,N):.0f}%)</div></div>
<div class="stat"><div class="statv">{cat('1.2')['total']}</div><div class="statl">disease occurrence / diagnosis &mdash; the largest category</div></div>
<div class="stat"><div class="statv">{kap}</div><div class="statl">knowledge / attitudes / behaviors ({pct(kap,N):.0f}%)</div></div>
<div class="stat"><div class="statv">{p_dx}/{p_tot}</div><div class="statl">predictive studies targeting disease detection</div></div>
</div>
<div class="callout"><b>What a study measures depends on what kind of study it is.</b> Descriptive research is the survey arm &mdash; <b>{pct(d_kap,d_tot):.0f}% of descriptive outcomes</b> are knowledge, attitudes or behaviors (vs {pct(sum(cat(c)['counts']['Causal'] for c in ('3.1','3.2','3.3')),TT['Causal']):.0f}% of causal). Causal research is the most clinical-and-patient-centred, and holds <b>almost every mental-health outcome</b> ({c_ment} of {cat('2.2')['total']}). Predictive research is overwhelmingly diagnostic &mdash; <b>{pct(p_clin,p_tot):.0f}% clinical/biomedical</b>, most of it disease-detection models. Satisfaction is the rarest outcome anywhere ({cat('2.3')['total']} of {N}), and health-system and process outcomes reach only {cat('4.1')['total']} ({pct(cat('4.1')['total'],N):.0f}%).</div>

<section>
<h2>The outcomes overall</h2>
<p class="sub">All {N} determined outcomes by category, grouped into the four domains plus <i>Other</i>. Percentages are of the {N} papers; bar length is relative to the largest category. <b>{nmach} of these {N} ({pct(nmach,N):.0f}%) are provisional machine determinations</b>, all of them predictive studies.</p>
<div class="card">{comb}</div>
</section>

<section>
<h2>By study task</h2>
<p class="sub">The same outcomes, split by the study&rsquo;s task. Each bar is one task&rsquo;s outcomes, segmented by domain &mdash; so the bars show <b>how the mix shifts</b>, not raw counts.</p>
<div class="card">{stackblock}<div class="legend">{legend}</div></div>
<p class="sub" style="margin-top:20px">Category detail &mdash; count and, below it, the share <i>within that task</i> (column %). Cell shading tracks the within-task share.</p>
<div class="tscroll"><table class="mtx"><thead><tr><th class="l">Outcome category</th><th>Descriptive<br><span style="font-weight:400;text-transform:none">n={TT['Descriptive']}</span></th><th>Causal<br><span style="font-weight:400;text-transform:none">n={TT['Causal']}</span></th><th>Predictive<br><span style="font-weight:400;text-transform:none">n={TT['Predictive']}</span></th><th>All</th></tr></thead><tbody>{mrows}</tbody></table></div>
</section>

<section>
<h2>Every outcome</h2>
<p class="sub">All {N} papers &mdash; click a heading to sort, or filter by task. Predictive outcomes are tagged <span class="tag ai">AI · unverified</span> (machine-determined, pending reviewer sign-off); the rest are <span class="tag adj">adjudicated</span> by the two reviewers.</p>
<div class="filt"><button data-f="all" class="on">All {N}</button><button data-f="Descriptive">Descriptive {TT['Descriptive']}</button><button data-f="Causal">Causal {TT['Causal']}</button><button data-f="Predictive">Predictive {TT['Predictive']}</button></div>
<div class="tscroll" style="max-height:620px;overflow-y:auto"><table id="bt"><thead><tr><th data-k="pmid">PMID</th><th data-k="task">Task</th><th data-k="oc">Determined outcome</th><th data-k="cat">Category</th><th data-k="src">Source</th></tr></thead><tbody>{brows}</tbody></table></div>
</section>

<section>
<h2>How the outcomes were determined</h2>
<div class="notes">
<h3>The rule (identical for all tasks)</h3>
<p>The outcome is the study&rsquo;s <b>dependent variable</b>. It was read from the <b>title first, then abstract, then methods</b>. With more than one outcome, the <b>first one named in the methods that actually has results</b> in the main text or tables was taken; with multiple time points, the <b>main time point</b> in the methods (else the last). One outcome per paper, so the counts above are also paper counts.</p>
<h3>Who determined each</h3>
<ul>
<li><b>Descriptive &amp; causal ({TT['Descriptive']+TT['Causal']} papers)</b> &mdash; the <b>adjudicated</b> outcomes from the two reviewers (TSA &amp; YA), assembled from the adjudication files (full coverage, no text disagreements).</li>
<li><b>Predictive ({TT['Predictive']} papers)</b> &mdash; not previously extracted, so determined <b>here from the full-text PDFs by the same rule</b> and tagged <b>AI&nbsp;·&nbsp;unverified</b>. Each carries a confidence flag and a one-line rationale in <code>data/outcomes/08_08_2026_all_outcomes_classified.csv</code> for reviewer verification. All {TT['Predictive']} were determined the same way, so the predictive arm is uniform.</li>
</ul>
<h3>Categorising</h3>
<p>Each outcome was placed in exactly one of <b>12 categories across 4 domains</b>, or in the residual <i>Other</i>, using a written codebook (<code>docs/methods/08_08_2026_outcome_categorization_codebook.md</code>) with a fixed decision order &mdash; e.g. &ldquo;knowledge score&rdquo; routes to <i>Knowledge</i>, &ldquo;anxiety scale&rdquo; to <i>Mental health</i>, before the generic <i>scales</i> rule. <i>Other</i> is drawn above as a fifth group so that nothing is hidden. Re-categorising any outcome is a one-line change. <b>{cat('OTHER')['total']}</b> outcomes are not health outcomes at all and sit in <i>Other</i>: six studies whose result is a questionnaire&rsquo;s reliability rather than a health state, three image-processing papers reporting only image-quality metrics, two education results, a web-page credibility rating and a court verdict. <b>{sum(1 for r in rowsall if r['category']=='OTHER' and r['Study_Type']=='Predictive')}</b> of them are predictive studies.</p>
<p>The categories for the {TT['Descriptive']+TT['Causal']} adjudicated outcomes were assigned by the rule-based classifier and then reviewed by hand; the {TT['Predictive']} predictive categories were assigned by the same model that determined those outcomes, working from the same codebook, and <b>have not been through the classifier or a manual review</b>.</p>
<p><b>Read the differences as descriptive, not evaluative</b> &mdash; a KAP-heavy descriptive literature and a diagnosis-heavy predictive literature reflect what those designs are for, not their quality.</p>
</div>
</section>
<p class="foot">Generated 2026-08-08 &middot; {N} papers (same set as the institutions / author-countries / journal-landscape artifacts) &middot; data <code>data/outcomes/08_08_2026_all_outcomes_classified.csv</code></p>
</div>
<script>
(function(){{
 var tb=document.querySelector('#bt tbody'),ths=document.querySelectorAll('#bt thead th'),cur='',asc=true;
 function val(tr,k){{if(k==='pmid')return +tr.querySelector('.pmid').textContent;if(k==='task')return tr.dataset.task;if(k==='cat')return tr.dataset.cat;if(k==='src')return tr.dataset.src;return tr.querySelector('.oc').textContent.toLowerCase();}}
 ths.forEach(function(th){{th.addEventListener('click',function(){{var k=th.dataset.k;asc=(k===cur)?!asc:true;cur=k;var rs=[].slice.call(tb.querySelectorAll('tr'));rs.sort(function(a,b){{var x=val(a,k),y=val(b,k);return (x<y?-1:x>y?1:0)*(asc?1:-1);}});rs.forEach(function(r){{tb.appendChild(r);}});}});}});
 var btns=document.querySelectorAll('.filt button');
 btns.forEach(function(b){{b.addEventListener('click',function(){{btns.forEach(function(x){{x.classList.remove('on');}});b.classList.add('on');var f=b.dataset.f;tb.querySelectorAll('tr').forEach(function(tr){{tr.style.display=(f==='all'||tr.dataset.task===f)?'':'none';}});}});}});
}})();
</script>'''
open("outputs/reports/08_08_2026_outcomes_artifact.html","w",encoding="utf-8").write(PAGE)
print("wrote outputs/reports/08_08_2026_outcomes_artifact.html (%d chars)"%len(PAGE))
print("domain totals:",{d:dom(d)["total"] for d in DOMS})
print("desc KAP%%=%.0f  causal clinical rows, pred clinical%%=%.0f"%(pct(d_kap,d_tot),pct(p_clin,p_tot)))
