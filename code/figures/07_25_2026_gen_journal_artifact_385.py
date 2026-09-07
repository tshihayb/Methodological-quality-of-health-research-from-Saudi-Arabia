# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Journal-landscape artifact on the canonical 385 papers (design system: petrol-teal, serif, tabular-nums)."""
import pandas as pd, html
BJ='data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv'
BP='data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv'
bj=pd.read_csv(BJ,dtype=str).fillna(''); bp=pd.read_csv(BP,dtype=str).fillna('')
NJ=len(bj); NP=len(bp)
def I(s): return pd.to_numeric(s,errors='coerce').fillna(0).astype(int)
bj['n_papers_i']=I(bj.n_papers)

QC={'Q1':'#16697a','Q2':'#489fb5','Q3':'#c99a2e','Q4':'#c05046','pending':'#9aa7ab','None':'#9aa7ab'}
def qdist(s):
    v=s.value_counts(); return [(q,int(v.get(q,0))) for q in ['Q1','Q2','Q3','Q4']]
def bars(pairs,total,cmap=QC,pend=0,pendlab='JCR pending',mx=None):
    # ⚠ SHARED SCALE. Each card used to normalise to its own maximum, so JCR Q2 (103 papers)
    # was drawn exactly as wide as SJR Q1 (184) - in a section whose own subhead asserts
    # "JCR ranks lower than SJR", the geometry said the opposite of the numbers.
    mx=mx or max([n for _,n in pairs]+[pend,1]); out=[]
    for k,n in pairs:
        out.append(f'<div class="brow"><div class="blab"><span class="chip" style="--rc:{cmap.get(k,"#888")}">{k}</span></div>'
          f'<div class="bwrap"><span class="bbar" style="width:{n/mx*100:.1f}%;background:{cmap.get(k,"#888")}"></span></div>'
          f'<div class="bnum">{n}<span class="bpct">{n/total*100:.0f}%</span></div></div>')
    if pend:
        out.append(f'<div class="brow"><div class="blab"><span class="chip" style="--rc:#9aa7ab">{pendlab}</span></div>'
          f'<div class="bwrap"><span class="bbar" style="width:{pend/mx*100:.1f}%;background:#9aa7ab"></span></div>'
          f'<div class="bnum">{pend}<span class="bpct">{pend/total*100:.0f}%</span></div></div>')
    return '\n'.join(out)

# SJR
# ⚠ '-' is SJR's not-ranked value. It used to be dropped, so the SJR card summed to 374
# papers while the JCR card beside it summed to 385 - two different completeness
# conventions side by side, in the very comparison the section invites, flattering SJR.
sjr_j=qdist(bj.sjr_best_quartile); sjr_p=qdist(bp.sjr_best_quartile)
sjr_j_pend=int((bj.sjr_best_quartile=='-').sum()); sjr_p_pend=int((bp.sjr_best_quartile=='-').sum())
SJR_Q12_P=sum(n for q,n in sjr_p if q in('Q1','Q2'))
assert sum(n for _,n in sjr_p)+sjr_p_pend==NP, 'the SJR card must account for every paper'
# JCR (pending = blank)
jcr_j=qdist(bj.jcr_2022_quartile); jcr_p=qdist(bp.jcr_2022_quartile)
jcr_j_pend=int(bj.jcr_2022_quartile.isin(['None','']).sum()); jcr_p_pend=int(bp.jcr_2022_quartile.isin(['None','']).sum())
JCR_Q12_P=sum(n for q,n in jcr_p if q in('Q1','Q2'))
# the two by-paper cards are read against each other, so they share one bar scale
QMAX=max([n for _,n in sjr_p]+[n for _,n in jcr_p]+[sjr_p_pend,jcr_p_pend])
# access
oa_yes=int((bj.scimago_open_access=='Yes').sum()); oa_no=int((bj.scimago_open_access=='No').sum())
oa_p=int((bp.scimago_open_access=='Yes').sum()); doaj_j=int((bj.is_in_doaj=='True').sum())
doaj_p=int((bp.is_in_doaj=='True').sum())
# indexing
med=int((bj.in_medline=='Yes').sum()); scop=int((bj.in_scopus_2022=='Yes').sum())
pmc_p=int((bp.in_pmc=='Yes').sum()) if 'in_pmc' in bp else 0
# fields
# ⚠ PER PAPER. bp.field is the paper's own OpenAlex primary topic. The by-JOURNAL file also
# has a 'field' column, but it is one arbitrary paper's topic pinned to the whole journal -
# it equals the FIRST paper's field for all 48 multi-paper journals - so IJERPH is filed
# there as Dentistry although 16 of its 29 papers are Medicine and 1 is Dentistry. Never
# read subject from the journal file.
# ⚠ one paper (PMID STUDY-0429) carries no OpenAlex topic at all. It is not a tenth field;
# counting it as one both overstates the field count and hides the only coverage gap in
# the topic data, so it is reported separately.
NOFIELD=int((bp.field=='').sum())
_fld=bp.field[bp.field!=''].value_counts()
fields=_fld.head(9); FIELD_REST=int(_fld[9:].sum()); FIELD_REST_N=int(len(_fld)-9)
assert int(fields.sum())+FIELD_REST+NOFIELD==NP

def statcards():
    S=[(str(NP),'papers'),(str(NJ),'journals'),
       (f'{SJR_Q12_P/NP*100:.0f}%','papers in SJR Q1&ndash;Q2'),
       (f'{oa_p/NP*100:.0f}%','papers in open-access journals'),
       (f'{fields.iloc[0]}','papers on Medicine topics')]
    return '\n'.join(f'<div class="stat"><div class="statv">{v}</div><div class="statl">{l}</div></div>' for v,l in S)

def fieldbars():
    mx=int(fields.iloc[0]); out=[]
    for f,n in fields.items():
        out.append(f'<div class="brow"><div class="clab">{html.escape(str(f))}</div>'
          f'<div class="bwrap"><span class="bbar" style="width:{n/mx*100:.1f}%;background:#489fb5"></span></div>'
          f'<div class="bnum">{int(n)}<span class="bpct">{int(n)/NP*100:.0f}%</span></div></div>')
    # ⚠ a truncated chart must say what it truncated: the nine bars leave out 19 papers
    # across nine further fields, which used to vanish with no "other" row and no denominator
    out.append(f'<div class="brow"><div class="clab">{FIELD_REST_N} further fields</div>'
      f'<div class="bwrap"><span class="bbar" style="width:{FIELD_REST/mx*100:.1f}%;background:#9aa7ab"></span></div>'
      f'<div class="bnum">{FIELD_REST}<span class="bpct">{FIELD_REST/NP*100:.0f}%</span></div></div>')
    if NOFIELD:
        out.append(f'<div class="brow"><div class="clab">no topic assigned</div>'
          f'<div class="bwrap"><span class="bbar" style="width:{NOFIELD/mx*100:.1f}%;background:#c8ced2"></span></div>'
          f'<div class="bnum">{NOFIELD}<span class="bpct">&lt;1%</span></div></div>')
    return '\n'.join(out)

# full journal table
bj2=bj.sort_values('n_papers_i',ascending=False)
trows=[]
# ⚠ the Field column used to print bj.field - the first-paper artefact described above -
# so the table asserted, 229 times, a subject for the JOURNAL that was really one of its
# papers' topics. scimago_areas is a real journal property: the Scopus areas SCImago
# assigns the journal.
for i,r in enumerate(bj2.itertuples()):
    # ⚠ one state, one symbol: the SJR column printed a raw hyphen from the CSV while the
    # JCR column printed an em-dash for the same thing.
    sjrq=('&mdash;' if r.sjr_best_quartile in ('-','') else r.sjr_best_quartile); jcrq=r.jcr_2022_quartile or ('<span class="pend">pending</span>' if 'not yet extracted' in r.jcr_note else ('&mdash;' if r.jcr_note else '&middot;'))
    acc='Open' if r.scimago_open_access=='Yes' else ('Closed' if r.scimago_open_access=='No' else '&middot;')
    # ⚠ the sort keys must not be blank. pandas turns the literal "None" in the CSV into
    # NaN on read, so the 33 not-ranked journals used to sort under the empty string
    # instead of as a group; "ZZ" keeps them together and last.
    trows.append(f'<tr data-p="{int(r.n_papers_i)}" data-j="{html.escape(r.journal)}" data-sjr="{r.sjr_best_quartile or "ZZ"}" data-jcr="{r.jcr_2022_quartile or "ZZ"}">'
      f'<td class="num rank">{i+1}</td><td class="jn">{html.escape(r.journal)}</td>'
      f'<td class="num strong">{int(r.n_papers_i)}</td>'
      f'<td class="num">{sjrq}</td><td class="num">{jcrq}</td>'
      f'<td>{acc}</td><td class="fd">{html.escape(r.scimago_areas or "&middot;")}</td></tr>')
trows='\n'.join(trows)

def qchip(k): return f'<span class="chip" style="--rc:{QC.get(k,"#888")}">{k}</span>'

HTML=f"""<title>Journal landscape &mdash; Saudi healthcare research quality</title>
<style>
:root{{--accent:#16697a;--accent2:#489fb5;--bg:#fbfcfc;--panel:#fff;--ink:#1b2b2f;--muted:#5c7075;
 --line:#dbe6e8;--barbg:#eaf1f2;--shadow:0 1px 3px rgba(20,50,60,.06),0 8px 30px rgba(20,50,60,.05);
 --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;--body:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0e1a1d;--panel:#132427;--ink:#e8eef0;--muted:#93a9ad;--line:#26383d;--barbg:#1b3238;--accent:#4db5c9;--accent2:#6fc6d6;--shadow:0 1px 3px rgba(0,0,0,.3),0 10px 34px rgba(0,0,0,.28);}}}}
:root[data-theme="light"]{{--bg:#fbfcfc;--panel:#fff;--ink:#1b2b2f;--muted:#5c7075;--line:#dbe6e8;--barbg:#eaf1f2;--accent:#16697a;--accent2:#489fb5;}}
:root[data-theme="dark"]{{--bg:#0e1a1d;--panel:#132427;--ink:#e8eef0;--muted:#93a9ad;--line:#26383d;--barbg:#1b3238;--accent:#4db5c9;--accent2:#6fc6d6;}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);line-height:1.55}}
.wrap{{max-width:1040px;margin:0 auto;padding:44px 24px 80px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:12px;font-weight:600;color:var(--accent)}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(30px,4.6vw,46px);line-height:1.08;margin:.28em 0 .18em;text-wrap:balance}}
.lede{{font-size:18px;color:var(--muted);max-width:66ch;margin:0 0 30px}}.lede b{{color:var(--ink);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:13px;margin:26px 0 20px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:15px;box-shadow:var(--shadow)}}
.statv{{font-family:var(--serif);font-size:clamp(20px,2.4vw,28px);font-weight:600;color:var(--accent);font-variant-numeric:tabular-nums}}
.statl{{font-size:12px;color:var(--muted);margin-top:3px;line-height:1.35}}
section{{margin-top:44px}}h2{{font-family:var(--serif);font-weight:600;font-size:24px;margin:0 0 4px}}
.sub{{color:var(--muted);font-size:14.5px;margin:0 0 18px;max-width:72ch}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px 22px;box-shadow:var(--shadow)}}
.card h3{{font-family:var(--serif);font-size:16px;margin:0 0 12px}}
.brow{{display:grid;grid-template-columns:88px 1fr auto;align-items:center;gap:12px;margin:9px 0}}
.bwrap{{background:var(--barbg);border-radius:6px;height:14px;overflow:hidden}}.bbar{{display:block;height:100%;border-radius:6px}}
.bnum{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;font-size:14px;white-space:nowrap}}
.bpct{{color:var(--muted);font-weight:400;font-size:12px;margin-left:7px}}
.clab{{font-size:13px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.chip{{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;color:var(--ink)}}
.chip::before{{content:"";width:9px;height:9px;border-radius:50%;background:var(--rc);flex:none}}
.tablecard{{background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}}
.tscroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:620px;font-size:13.5px}}
thead th{{position:sticky;top:0;background:var(--panel);text-align:right;font-size:11.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;padding:11px 12px;border-bottom:2px solid var(--line);cursor:pointer;white-space:nowrap}}
thead th.l{{text-align:left}}thead th:hover{{color:var(--accent)}}th.sorted{{color:var(--accent)}}
tbody td{{padding:8px 12px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}}
tbody tr:hover{{background:color-mix(in srgb,var(--accent) 6%,transparent)}}
td.num{{text-align:right}}td.rank{{color:var(--muted);font-size:12px}}td.jn{{font-weight:600}}td.strong{{color:var(--accent);font-weight:700}}
td.fd{{color:var(--muted);font-size:12.5px;white-space:nowrap}}.pend{{color:#9aa7ab;font-style:italic;font-size:12px}}
.notes{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px 26px;box-shadow:var(--shadow);font-size:13.5px;color:var(--muted);line-height:1.62}}
.notes h3{{font-family:var(--serif);color:var(--ink);font-size:16px;margin:14px 0 8px}}.notes h3:first-child{{margin-top:0}}
.notes b{{color:var(--ink)}}.notes ul{{margin:0;padding-left:20px}}.notes li{{margin:5px 0}}
.foot{{margin-top:28px;font-size:12px;color:var(--muted);text-align:center}}
@media(max-width:860px){{.stats{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}}}
</style>
<div class="wrap">
 <div class="eyebrow">Assessment of healthcare research quality in Saudi Arabia</div>
 <h1>Where the research was published</h1>
 <p class="lede">The <b>{NP} included papers</b> (377 adjudicated + 8 added Saudi-authored) appeared in
 <b>{NJ} journals</b>. Most sit in the upper SJR quartiles &mdash; <b>{SJR_Q12_P/NP*100:.0f}% of papers</b> in a
 Q1 or Q2 journal &mdash; and the corpus is predominantly clinical Medicine, which is the primary topic of {fields.iloc[0]/NP*100:.0f}% of papers.</p>
 <div class="stats">{statcards()}</div>

 <section><h2>Journal quartile</h2>
  <p class="sub">Two rankings: SCImago <b>SJR</b> (Scopus, 2022) and Clarivate <b>JCR</b> JIF (2022). JCR ranks lower than SJR.</p>
  <div class="two">
   <div class="card"><h3>SCImago SJR &mdash; by paper</h3>{bars(sjr_p,NP,pend=sjr_p_pend,pendlab='Not ranked',mx=QMAX)}</div>
   <div class="card"><h3>Clarivate JCR &mdash; by paper</h3>{bars(jcr_p,NP,pend=jcr_p_pend,pendlab='Not ranked',mx=QMAX)}</div>
  </div>
 </section>

 <section><h2>Open versus closed access</h2>
  <p class="sub">SCImago open-access flag and DOAJ membership, <b>by journal</b> (of {NJ}). Per <b>paper</b> the
  same measures give <b>{oa_p} open ({oa_p/NP*100:.1f}%)</b> and <b>{doaj_p} in a DOAJ journal ({doaj_p/NP*100:.1f}%)</b>
  &mdash; the headline tile above is the paper-level figure, and the two differ because the open-access journals in this
  sample carry more papers each. <b>Open and Closed partition the {NJ}; DOAJ is a subset of Open</b> (all {doaj_j} DOAJ
  journals are flagged open access), so the three bars do not add up.</p>
  <div class="card">
   <div class="brow"><div class="blab"><span class="chip" style="--rc:#2a9d8f">Open</span></div><div class="bwrap"><span class="bbar" style="width:{oa_yes/max(oa_yes,oa_no)*100:.0f}%;background:#2a9d8f"></span></div><div class="bnum">{oa_yes}<span class="bpct">{oa_yes/NJ*100:.0f}%</span></div></div>
   <div class="brow"><div class="blab"><span class="chip" style="--rc:#6a6f8e">Closed</span></div><div class="bwrap"><span class="bbar" style="width:{oa_no/max(oa_yes,oa_no)*100:.0f}%;background:#6a6f8e"></span></div><div class="bnum">{oa_no}<span class="bpct">{oa_no/NJ*100:.0f}%</span></div></div>
   <div class="brow"><div class="blab"><span class="chip" style="--rc:#489fb5">DOAJ</span></div><div class="bwrap"><span class="bbar" style="width:{doaj_j/max(oa_yes,oa_no)*100:.0f}%;background:#489fb5"></span></div><div class="bnum">{doaj_j}<span class="bpct">{doaj_j/NJ*100:.0f}%</span></div></div>
  </div>
 </section>

 <section><h2>Subject area</h2>
  <p class="sub">Each paper by <b>its own</b> OpenAlex primary topic &mdash; a property of the paper, not of the journal it appeared in. All {NP} papers are counted. A clinical-Medicine corpus with dental, psychology and public-health tails.</p>
  <div class="card">{fieldbars()}</div>
 </section>

 <section><h2>Every journal</h2>
  <p class="sub">All {NJ} journals, most-published first. Click a heading to sort. SJR = SCImago quartile; JCR = Clarivate JIF quartile (2022); <b>&mdash;</b> = that ranking does not place the journal.</p>
  <div class="tablecard"><div class="tscroll"><table id="t"><thead><tr>
   <th class="num" data-k="rank">#</th><th class="l" data-k="j">Journal</th>
   <th class="num sorted" data-k="p">Papers</th><th class="num" data-k="sjr">SJR</th>
   <th class="num" data-k="jcr">JCR</th><th class="l" data-k="acc">Access</th><th class="l" data-k="fd">Scopus subject area</th>
  </tr></thead><tbody>{trows}</tbody></table></div></div>
 </section>

 <section><h2>How this was built</h2>
  <div class="notes">
   <h3>Population</h3>
   <p>The <b>{NP} papers</b> = the 377 adjudicated papers + 8 added Saudi-authored papers (5 previously single-reviewed
   + 3 new), matching the author-landscape population exactly. Two papers with no Saudi author and one co-authored by a
   study PI are excluded.</p>
   <h3>Sources (nothing invented)</h3>
   <ul>
    <li><b>Identity &amp; indexing:</b> PubMed / NLM Catalog. <b>SJR quartile, categories, open-access:</b> SCImago 2022
    (full 32,162-journal list). <b>Topic &amp; DOAJ:</b> OpenAlex. <b>JCR JIF quartile:</b> Clarivate JCR 2022.</li>
    <li><b>SJR</b> places {NJ-sjr_j_pend} of the {NJ} journals ({NP-sjr_p_pend} of {NP} papers); <b>Computational
    intelligence and neuroscience</b> ({sjr_p_pend} papers) is Scopus-covered but was assigned no 2022 SJR quartile,
    so it is reported as not ranked rather than guessed. <b>JCR</b> for the original 226 journals was extracted from
    Clarivate. The <b>3 journals new to the 385</b> were filled from web-secondary sources (flagged for confirmation
    against a Clarivate pass): <b>[NAME-REDACTED] Q2</b>, <b>[NAME-REDACTED] Q3</b>, and
    <b>Journal of Diabetes Science &amp; Technology</b> &mdash; an ESCI journal that received a JIF but no quartile in
    JCR 2022, so it counts as <b>None</b>. {jcr_j_pend} journals in total have no 2022 JCR quartile (delisted /
    not-ranked / ESCI).</li>
   </ul>
  </div>
 </section>
 <p class="foot">Generated 2026-07-25 &middot; <code>data/journals/07_25_2026_journal_landscape_by_journal_385_JCR.csv</code> &middot; <code>_by_paper_385_JCR.csv</code></p>
</div>
<script>
(function(){{var tb=document.querySelector('#t tbody'),ths=document.querySelectorAll('#t thead th');var cur='p',asc=false;
function sort(k,th){{asc=(k===cur)?!asc:(k==='j'||k==='fd'||k==='acc'||k==='sjr'||k==='jcr');cur=k;
 ths.forEach(h=>h.classList.remove('sorted'));th.classList.add('sorted');
 var rows=[].slice.call(tb.querySelectorAll('tr'));
 rows.sort(function(a,b){{var x,y;
  if(k==='rank'){{x=+a.querySelector('.rank').textContent;y=+b.querySelector('.rank').textContent;}}
  else if(k==='p'){{x=+a.dataset.p;y=+b.dataset.p;}}
  else{{x=a.dataset[k]||'';y=b.dataset[k]||'';return asc?x.localeCompare(y):y.localeCompare(x);}}
  return asc?x-y:y-x;}});
 rows.forEach(r=>tb.appendChild(r));}}
ths.forEach(th=>th.addEventListener('click',()=>sort(th.dataset.k,th)));}})();
</script>
"""
open('outputs/reports/07_25_2026_journal_landscape_385_artifact.html','w',encoding='utf-8').write(HTML)
print('wrote outputs/reports/07_25_2026_journal_landscape_385_artifact.html',len(HTML)//1024,'KB · journals',NJ,'papers',NP)
