# -*- coding: utf-8 -*-
"""Generate the 'Saudi institutions' classification artifact (theme-aware, project design system)."""
import pandas as pd, html

A  = pd.read_csv('data/authors/07_25_2026_saudi_affiliation_long.csv')
T  = pd.read_csv('data/authors/07_25_2026_saudi_institution_type_counts.csv')
IC = pd.read_csv('data/authors/07_25_2026_saudi_institution_counts.csv')
P  = pd.read_csv('data/authors/07_25_2026_saudi_paper_level.csv')
CY = pd.read_csv('data/authors/07_25_2026_saudi_city_counts.csv')

N = len(A); NP = A.PMID.nunique()
named = IC[~IC.institution.str.startswith('(')]
N_INST = named.institution.nunique()
N_PLACE = int(IC.institution.str.startswith('(').sum())
multi = int(P.multisector.sum()); multipct = multi/NP*100
# UPPER BOUND on the sector figures (TSA ruling 2026-08-24: report bounds, don't choose).
# Every author here is credited to ONE institution -- the top-level employer named in their
# first Saudi affiliation block -- so where an affiliation names several (176 of 1,520 author
# positions, 11.6%) the others are dropped BEFORE the paper-level union, and a paper can lose
# a sector but never gain one. `sectors_present_union` credits every institution each author
# is on record for. Table 1's footnote carries the same pair; both are computed, never typed,
# so the table and this figure cannot drift apart.
_HEALTH = {'Hospital / medical city', 'Hospital & research centre', 'Ministry of Health',
           'Military & security-forces medical'}
multi_hi = int(P.multisector_union.sum())
hs_lo = int(P.sectors_present.map(lambda s: any(x.strip() in _HEALTH for x in str(s).split(';'))).sum())
hs_hi = int(P.sectors_present_union.map(lambda s: any(x.strip() in _HEALTH for x in str(s).split(';'))).sum())
UNIV_PCT = float(T.loc[T.inst_type=='University','pct_authors'].iloc[0])
def _c(n): return f'{n:,}'
_pt = A[A.source=='pubmed-affil']
N_PT = len(_pt); N_T1 = int((_pt.tier==1).sum()); PCT_NAMED = N_T1/N_PT*100
N_NOAFF = int((A.source!='pubmed-affil').sum())
NCITY_RES = int((A['city']!='Unspecified').sum()) if 'city' in A.columns else N

TYPEC = {
 'University':'#16697a','Hospital / medical city':'#e07a5f','Hospital & research centre':'#d97b46',
 'Military & security-forces medical':'#6a6f8e','Ministry of Health':'#2a9d8f',
 'Other government / ministry':'#5a8fbf','Government authority / agency':'#b8860b',
 'Council / commission':'#8e6bb0','Research centre / institute':'#489fb5',
 'Company / industry':'#c05299','Society / association / NGO':'#d08c60','Other / unspecified':'#8a9499'}
def chip(t):
    return f'<span class="chip" style="--rc:{TYPEC.get(t,"#888")}">{html.escape(t)}</span>'

# ---- by-type rows (author level) ----
maxa=T.author_appearances.max()
tbars=[]
for _,r in T.sort_values('author_appearances',ascending=False).iterrows():
    t=r.inst_type
    tbars.append(
      f'<div class="brow"><div class="blab">{chip(t)}</div>'
      f'<div class="bwrap"><span class="bbar" style="width:{r.author_appearances/maxa*100:.1f}%;background:{TYPEC.get(t,"#888")}"></span></div>'
      f'<div class="bnum">{int(r.author_appearances)}<span class="bpct">{r.pct_authors:.1f}%</span></div>'
      f'<div class="bmeta">{int(r.distinct_institutions)} inst · {int(r.papers_involving)} papers</div></div>')
tbars='\n'.join(tbars)

# ---- paper-level sector involvement ----
pbars=[]
for _,r in T.sort_values('papers_involving',ascending=False).iterrows():
    t=r.inst_type
    pbars.append(
      f'<div class="brow"><div class="blab">{chip(t)}</div>'
      f'<div class="bwrap"><span class="bbar" style="width:{r.pct_papers:.1f}%;background:{TYPEC.get(t,"#888")}"></span></div>'
      f'<div class="bnum">{int(r.papers_involving)}<span class="bpct">{r.pct_papers:.1f}%</span></div></div>')
pbars='\n'.join(pbars)

# ---- lead institution type (paper level) ----
lead=P['lead_saudi_type'].value_counts()
leadbars=[]
for t,n in lead.items():
    leadbars.append(
      f'<div class="brow"><div class="blab">{chip(t)}</div>'
      f'<div class="bwrap"><span class="bbar" style="width:{n/lead.max()*100:.1f}%;background:{TYPEC.get(t,"#888")}"></span></div>'
      f'<div class="bnum">{int(n)}<span class="bpct">{n/NP*100:.1f}%</span></div></div>')
leadbars='\n'.join(leadbars)

# ---- top institutions ----
top=named.sort_values('author_appearances',ascending=False).head(22)
maxi=top.author_appearances.max()
ibars=[]
for _,r in top.iterrows():
    col=TYPEC.get(r.inst_type,'#888')
    ibars.append(
      f'<div class="irow"><div class="itop">'
      f'<span class="iname"><span class="ichip" style="--rc:{col}"></span>{html.escape(r.institution)}</span>'
      f'<span class="ival">{int(r.author_appearances)}<span class="bpct">{int(r.papers)} papers</span></span></div>'
      f'<div class="bwrap"><span class="bbar" style="width:{r.author_appearances/maxi*100:.1f}%;background:{col}"></span></div></div>')
ibars='\n'.join(ibars)

# ---- cities ----
CY.columns=['city','n'] if len(CY.columns)==2 else CY.columns
cy=CY[CY.city!='Unspecified'].sort_values('n',ascending=False).head(14)
maxc=cy.n.max()
cbars=[]
for _,r in cy.iterrows():
    cbars.append(
      f'<div class="brow"><div class="clab">{html.escape(str(r.city))}</div>'
      f'<div class="bwrap"><span class="bbar" style="width:{r.n/maxc*100:.1f}%;background:#489fb5"></span></div>'
      f'<div class="bnum">{int(r.n)}</div></div>')
cbars='\n'.join(cbars)

# ---- full institution table ----
rows=[]
disp=IC.copy()
disp['nm']=~disp.institution.str.startswith('(')
disp=disp.sort_values(['nm','author_appearances'],ascending=[False,False])
for i,r in enumerate(disp.itertuples()):
    nm = not r.institution.startswith('(')
    rows.append(
      f'<tr data-auth="{int(r.author_appearances)}" data-pap="{int(r.papers)}" data-name="{html.escape(r.institution)}" data-type="{html.escape(r.inst_type)}">'
      f'<td class="num rank">{i+1}</td>'
      f'<td class="inst{"" if nm else " ph"}">{html.escape(r.institution)}</td>'
      f'<td>{chip(r.inst_type)}</td>'
      f'<td class="num strong">{int(r.author_appearances)}</td>'
      f'<td class="num">{int(r.papers)}</td></tr>')
rows='\n'.join(rows)

STAT=[(_c(N),'Saudi author positions'),(str(NP),'papers with a Saudi author'),
      (str(N_INST),'named institutions'),(f'{UNIV_PCT:.0f}%','from universities'),
      (f'{multipct:.0f}–{multi_hi/NP*100:.0f}%','papers span >1 sector')]
stat='\n'.join(f'<div class="stat"><div class="statv">{v}</div><div class="statl">{l}</div></div>' for v,l in STAT)

HTML=f"""<title>Saudi institutions &mdash; healthcare research quality</title>
<style>
:root{{--accent:#16697a;--accent2:#489fb5;--bg:#fbfcfc;--panel:#fff;--ink:#1b2b2f;--muted:#5c7075;
 --line:#dbe6e8;--barbg:#eaf1f2;--shadow:0 1px 3px rgba(20,50,60,.06),0 8px 30px rgba(20,50,60,.05);
 --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
 --body:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0e1a1d;--panel:#132427;--ink:#e8eef0;--muted:#93a9ad;
 --line:#26383d;--barbg:#1b3238;--accent:#4db5c9;--accent2:#6fc6d6;
 --shadow:0 1px 3px rgba(0,0,0,.3),0 10px 34px rgba(0,0,0,.28);}}}}
:root[data-theme="light"]{{--bg:#fbfcfc;--panel:#fff;--ink:#1b2b2f;--muted:#5c7075;--line:#dbe6e8;
 --barbg:#eaf1f2;--accent:#16697a;--accent2:#489fb5;--shadow:0 1px 3px rgba(20,50,60,.06),0 8px 30px rgba(20,50,60,.05);}}
:root[data-theme="dark"]{{--bg:#0e1a1d;--panel:#132427;--ink:#e8eef0;--muted:#93a9ad;--line:#26383d;
 --barbg:#1b3238;--accent:#4db5c9;--accent2:#6fc6d6;--shadow:0 1px 3px rgba(0,0,0,.3),0 10px 34px rgba(0,0,0,.28);}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1040px;margin:0 auto;padding:44px 24px 80px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:600;color:var(--accent)}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(30px,4.6vw,46px);line-height:1.08;margin:.28em 0 .18em;text-wrap:balance;letter-spacing:-.01em}}
.lede{{font-size:18px;color:var(--muted);max-width:66ch;margin:0 0 30px}}
.lede b{{color:var(--ink);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:13px;margin:26px 0 20px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px 15px 13px;box-shadow:var(--shadow)}}
.statv{{font-family:var(--serif);font-size:clamp(21px,2.5vw,29px);font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}}
.statl{{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.35}}
section{{margin-top:44px}}
h2{{font-family:var(--serif);font-weight:600;font-size:24px;margin:0 0 4px;letter-spacing:-.01em}}
.sub{{color:var(--muted);font-size:14.5px;margin:0 0 18px;max-width:72ch}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.two h3,.solo h3{{font-family:var(--serif);font-size:16.5px;margin:0 0 3px}}
.two .sub{{font-size:13px;margin-bottom:14px}}
.brow{{display:grid;grid-template-columns:200px 1fr auto;align-items:center;gap:12px;margin:9px 0}}
.brow.wmeta{{grid-template-columns:200px 1fr auto auto}}
.blab{{min-width:0}} .bwrap{{background:var(--barbg);border-radius:6px;height:14px;overflow:hidden}}
.bbar{{display:block;height:100%;border-radius:6px}}
.bnum{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;font-size:14px;white-space:nowrap}}
.bpct{{color:var(--muted);font-weight:400;font-size:12px;margin-left:7px}}
.bmeta{{color:var(--muted);font-size:12px;white-space:nowrap;text-align:right}}
.chip{{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:var(--ink);line-height:1.25}}
.chip::before{{content:"";width:9px;height:9px;border-radius:50%;background:var(--rc);flex:none}}
.clab{{font-size:13px;font-weight:600;display:flex;align-items:center;gap:7px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.irow{{margin:11px 0}}
.itop{{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:5px}}
.iname{{font-size:13.5px;font-weight:600;display:flex;align-items:center;gap:8px}}
.ival{{font-variant-numeric:tabular-nums;font-weight:700;font-size:14px;white-space:nowrap;color:var(--accent)}}
.ichip{{width:9px;height:9px;border-radius:50%;background:var(--rc);flex:none}}
.callout{{display:flex;gap:18px;align-items:center;background:color-mix(in srgb,var(--accent) 8%,transparent);
 border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin-top:16px}}
.callout .big{{font-family:var(--serif);font-size:34px;font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums;line-height:1}}
.callout .txt{{font-size:13.5px;color:var(--muted)}} .callout .txt b{{color:var(--ink)}}
.tablecard{{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}}
.tscroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:560px;font-size:14px}}
thead th{{position:sticky;top:0;background:var(--panel);text-align:right;font-size:12px;color:var(--muted);
 text-transform:uppercase;letter-spacing:.05em;padding:12px;border-bottom:2px solid var(--line);cursor:pointer;user-select:none;white-space:nowrap}}
thead th.l{{text-align:left}} thead th:hover{{color:var(--accent)}}
th .ar{{opacity:.4;font-size:10px}} th.sorted .ar{{opacity:1;color:var(--accent)}}
tbody td{{padding:8px 12px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}}
tbody tr:last-child td{{border-bottom:none}} tbody tr:hover{{background:color-mix(in srgb,var(--accent) 6%,transparent)}}
td.num{{text-align:right}} td.rank{{color:var(--muted);font-size:12.5px}}
td.inst{{font-weight:600}} td.inst.ph{{font-weight:400;font-style:italic;color:var(--muted)}} td.strong{{font-weight:700;color:var(--accent)}}
.notes{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px 26px;box-shadow:var(--shadow);font-size:13.5px;color:var(--muted);line-height:1.62}}
.notes h3{{font-family:var(--serif);color:var(--ink);font-size:16px;margin:14px 0 8px}} .notes h3:first-child{{margin-top:0}}
.notes b{{color:var(--ink)}} .notes ul{{margin:0;padding-left:20px}} .notes li{{margin:5px 0}}
.foot{{margin-top:28px;font-size:12px;color:var(--muted);text-align:center}}
@media(max-width:860px){{.stats{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}
 .brow{{grid-template-columns:150px 1fr auto}}.bmeta{{display:none}}}}
</style>
<div class="wrap">
 <div class="eyebrow">Assessment of healthcare research quality in Saudi Arabia</div>
 <h1>The Saudi institutions behind the research</h1>
 <p class="lede">Every Saudi affiliation on the {NP} included papers (the 377 adjudicated papers plus 8 added
 Saudi-authored papers), classified by institution type. <b>{_c(N)} Saudi author positions</b> resolve to
 <b>{N_INST} named institutions</b> — a research base built overwhelmingly in the <b>universities</b>, with
 hospitals, the military health system, and the Ministry of Health next.
 Every count on this page credits each author position to <b>one institution</b> &mdash; the top-level employer
 named in that author&rsquo;s first Saudi affiliation block. Where an affiliation names more than one Saudi
 institution the others go unrecorded, so the institution count and the university share are
 <b>lower bounds</b>, and the sector figures below are reported as bounds.</p>
 <div class="stats">{stat}</div>

 <section>
  <h2>By institution type</h2>
  <p class="sub">Share of the {_c(N)} Saudi author positions by the type of their (top-level) institution.
  &ldquo;inst&rdquo; = number of distinct institutions of that type; &ldquo;papers&rdquo; = papers with at least one such author.</p>
  <div class="card">{tbars}</div>
 </section>

 <section>
  <h2>At the paper level</h2>
  <p class="sub">How the sectors show up across the {NP} Saudi-authored papers.</p>
  <div class="two">
   <div class="card solo"><h3>Papers involving each sector</h3>
    <p class="sub">A paper counts once per sector if any of its Saudi authors is based there (so rows sum to &gt;100%).</p>
    {pbars}</div>
   <div class="card solo"><h3>Lead Saudi institution</h3>
    <p class="sub">Type of the first-listed Saudi author&rsquo;s institution &mdash; the paper&rsquo;s anchor.</p>
    {leadbars}</div>
  </div>
  <div class="callout"><div class="big">{multipct:.0f}&ndash;{multi_hi/NP*100:.0f}%</div>
   <div class="txt"><b>{multi}&ndash;{multi_hi} of {NP} papers are multi-sector</b> &mdash; their Saudi authors span
   more than one institution type (most often a university together with a hospital or the military health
   system). The figure is a <b>bound, not a point</b>: each author is credited to the single institution their
   affiliation names as top-level employer, so where an affiliation names more than one the others go
   unrecorded and a paper can lose a sector but never gain one. <b>{multi}</b> counts only the credited
   institution; <b>{multi_hi}</b> credits every institution each author is on record for. On the same pair of
   rules at least one Saudi author sits in a hospital, medical city, Ministry of Health or military-health body
   in <b>{hs_lo}&ndash;{hs_hi}</b> papers. Table 1 carries the same bounds.</div></div>
 </section>

 <section>
  <h2>Leading institutions</h2>
  <p class="sub">Top {len(top)} Saudi institutions by author positions (dot colour = sector; &ldquo;p&rdquo; = papers).</p>
  <div class="card">{ibars}</div>
 </section>

 <section>
  <h2>Across the Kingdom</h2>
  <p class="sub">Saudi author positions by city of affiliation (top {len(cy)} shown; city resolved for
  {_c(NCITY_RES)} of {_c(N)}). Riyadh dominates, followed by Jeddah and the Eastern Province.</p>
  <div class="card">{cbars}</div>
 </section>

 <section>
  <h2>Every institution</h2>
  <p class="sub">All {len(IC)} institution labels ({N_INST} named + {N_PLACE} grouped buckets). Click a heading to sort.</p>
  <div class="tablecard"><div class="tscroll"><table id="t">
   <thead><tr>
     <th class="num" data-k="rank">#</th><th class="l" data-k="name">Institution</th>
     <th class="l" data-k="type">Type</th>
     <th class="num sorted" data-k="auth">Authors <span class="ar">&#9660;</span></th>
     <th class="num" data-k="pap">Papers</th>
   </tr></thead><tbody>{rows}</tbody></table></div></div>
 </section>

 <section>
  <h2>How this was built</h2>
  <div class="notes">
   <h3>What is classified</h3>
   <p>A <b>Saudi author position</b> is one author on one paper with at least one Saudi affiliation ({_c(N)} across
   {NP} papers, anchored to the validated author-country map). Each author&rsquo;s Saudi institution is taken from
   their first Saudi affiliation block and matched to its <b>top-level</b> institution — not the nested
   department or college — so &ldquo;Department of Surgery, College of Medicine, King Saud University&rdquo; is a University.</p>
   <h3>Method &amp; coverage</h3>
   <ul>
    <li><b>Tiered matching:</b> a curated list of ~90 Saudi institutions is tried first, then umbrella ministries,
    then keyword fallback. <b>{PCT_NAMED:.0f}% of PubMed-text authors ({_c(N_T1)} of {_c(N_PT)}) matched a specific
    named institution</b>; the rest resolve to the right sector by keyword.</li>
    <li>The {N_NOAFF} authors PubMed left without affiliation text were filled by reading the
    affiliation off the paper itself and classifying it the same way as every other block
    (<code>data/authors/08_23_2026_pdf_affiliations_gold.csv</code>). Most are universities, but not
    all &mdash; two are Ha&rsquo;il hospitals and one is a Ministry of Health post.</li>
   </ul>
   <h3>Rulings (adjustable)</h3>
   <ul>
    <li><b>KFSHRC &rarr; its own &ldquo;Hospital &amp; research centre&rdquo; type</b> &mdash; King Faisal Specialist
    Hospital &amp; Research Centre is both a tertiary hospital and one of the Kingdom&rsquo;s largest research
    centres, so it is counted as its own category rather than folded into either.</li>
    <li><b>University teaching hospitals / medical cities &rarr; University</b> (King Khalid University Hospital,
    King Saud University Medical City, [NAME-REDACTED] of the University …).</li>
    <li><b>National Guard health facilities by function:</b> King Abdulaziz Medical City &rarr; Hospital,
    KAIMRC &rarr; Research centre, KSAU-HS &rarr; University; only the bare ministry umbrella &rarr; Military &amp; security-forces.</li>
    <li><b>[NAME-REDACTED] / Interior / National Guard &rarr; Military &amp; security-forces</b> (not &ldquo;other government&rdquo;).</li>
   </ul>
   <p>The taxonomy has 11 categories; &ldquo;authority&rdquo; and &ldquo;council&rdquo; are genuinely rare in this corpus
   (SFDA, CBAHI; Saudi Health Council / SCFHS). Re-bucketing any institution is a one-line change in
   <code>code/lib/saudi_institution_classifier.py</code>.</p>
  </div>
 </section>
 <p class="foot">Generated 2026-07-25 &middot; data: <code>data/authors/07_25_2026_saudi_affiliation_long.csv</code>,
 <code>data/authors/07_25_2026_saudi_institution_type_counts.csv</code>, <code>data/authors/07_25_2026_saudi_institution_counts.csv</code>,
 <code>data/authors/07_25_2026_saudi_paper_level.csv</code></p>
</div>
<script>
(function(){{
 var tb=document.querySelector('#t tbody'),ths=document.querySelectorAll('#t thead th');
 var cur='auth',asc=false;
 function sort(k,th){{
  asc=(k===cur)?!asc:(k==='name'||k==='type');cur=k;
  ths.forEach(function(h){{h.classList.remove('sorted');var a=h.querySelector('.ar');if(a)a.remove();}});
  th.classList.add('sorted');var s=document.createElement('span');s.className='ar';s.innerHTML=asc?' &#9650;':' &#9660;';th.appendChild(s);
  var rows=[].slice.call(tb.querySelectorAll('tr'));
  rows.sort(function(a,b){{var x,y;
   if(k==='name'||k==='type'){{x=a.dataset[k];y=b.dataset[k];return asc?x.localeCompare(y):y.localeCompare(x);}}
   if(k==='rank'){{x=+a.querySelector('.rank').textContent;y=+b.querySelector('.rank').textContent;}}
   else{{x=+a.dataset[k];y=+b.dataset[k];}} return asc?x-y:y-x;}});
  rows.forEach(function(r){{tb.appendChild(r);}});
 }}
 ths.forEach(function(th){{th.addEventListener('click',function(){{sort(th.dataset.k,th);}});}});
}})();
</script>
"""
open('outputs/reports/07_25_2026_saudi_institutions_artifact.html','w',encoding='utf-8').write(HTML)
print('wrote outputs/reports/07_25_2026_saudi_institutions_artifact.html', len(HTML)//1024,'KB')
