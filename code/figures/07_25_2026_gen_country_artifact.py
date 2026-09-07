# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Generate the theme-aware 'Author countries' HTML artifact from the mapping CSVs + map PNGs.
Honors the project design system (petrol-teal #16697a, serif headings, tabular-nums)."""
import pandas as pd, json, html, os, sys
# Run from the repository root; the GEO table lives beside the enrichment scripts.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'enrichment'))

C = pd.read_csv('data/authors/07_25_2026_country_counts.csv')
P = pd.read_csv('data/authors/07_25_2026_paper_country_summary.csv')
L = pd.read_csv('data/authors/07_25_2026_author_country_long.csv')
b64 = json.load(open('data/authors/07_25_2026_map_b64.json'))
mapmod = __import__('07_25_2026_author_country_map')
GEO = mapmod.GEO
REGC = {'Gulf':'#0f5c6b','Other Arab':'#5aa9bd','Europe':'#6a4c93','Asia':'#e07a5f',
        'Sub-Saharan Africa':'#b8860b','Americas':'#2a9d8f','Oceania':'#c05299','Other':'#888'}

# ⚠ TWO DIFFERENT TOTALS -- do not conflate them (2026-08-24).
# NPOS   = author POSITIONS: one author x one paper. This is the population.
# TOTAL  = country PLACEMENTS: the counts column sums to more than NPOS because, under the
#          any-affiliation convention, a dual-affiliated author is counted once in EACH of
#          their countries. Before the convention changed these were equal, so the artifact
#          used one variable for both; afterwards that made it print "3,829 author positions"
#          while the provenance line beneath it (3,443 + 51 + 14) still summed to 3,508.
# Rule: describe the POPULATION with NPOS; describe bubble/bar magnitudes with TOTAL.
NPOS  = int(len(L))
TOTAL = int(C['author_appearances'].sum())
C['region'] = C['country'].map(lambda c: GEO[c][2] if c in GEO else 'Other')
C = C.sort_values(['author_appearances','papers_with_>=1_author'], ascending=False).reset_index(drop=True)
maxapp = C['author_appearances'].max()

# ---- derived headline numbers (data-driven) ----
NPAPERS   = int(P['PMID'].nunique())
NCOUNTRY  = int((C['author_appearances']>0).sum())          # countries that are some author's primary
PCT_INTL  = P['international'].mean()*100
SAUDI_APP = int(C.loc[C.country=='Saudi Arabia','author_appearances'].iloc[0])
SAUDI_PCT = SAUDI_APP/NPOS*100
SRC = L['source'].value_counts().to_dict()
N_PUBMED = int(SRC.get('pubmed-affil',0)); N_GOLD=int(SRC.get('pdf-gold-note',0)); N_MAN=int(SRC.get('manual-context',0))
def _c(n): return f'{n:,}'
# consortium skew facts
BIG = P[P['n_distinct_countries']>=20]
N_BIG=int(len(BIG)); MAX_C=int(P['n_distinct_countries'].max())
MAX_A=int(P['n_authors'].max()); MAX_A_C=int(P.loc[P['n_authors'].idxmax(),'n_distinct_countries'])
DUAL_PCT=(L['n_countries_author']>1).mean()*100
_Lf=L[L['is_first']]
FIRST_PRIMARY=int((_Lf['primary_country']=='Saudi Arabia').sum())
FIRST_ANY=int(_Lf['all_countries'].fillna('').str.contains('Saudi Arabia').sum())
FIRST_GAP=FIRST_ANY-FIRST_PRIMARY
N_VALID=NPAPERS-3   # the 3 newly-added papers post-date the legacy gold file

roll = (C.groupby('region')
          .agg(countries=('country','nunique'), authors=('author_appearances','sum'),
               papers=('papers_with_>=1_author','max'))
          .reset_index())
roll['pct'] = (roll.authors/TOTAL*100).round(1)
roll = roll.sort_values('authors', ascending=False)
region_order = list(roll.region)
GULF_PCT = float(roll.loc[roll.region=='Gulf','pct'].iloc[0])

# ---- table rows ----
def chip(reg):
    return f'<span class="chip" style="--rc:{REGC.get(reg,"#888")}">{html.escape(reg)}</span>'

rows_html = []
for i, r in C.iterrows():
    app = int(r['author_appearances']); pct = app/TOTAL*100
    barw = max(app/maxapp*100, 0.6)
    rows_html.append(
        f'<tr data-app="{app}" data-first="{int(r.first_author)}" data-last="{int(r.last_author)}" '
        f'data-corr="{int(r.corresponding_author)}" data-pap="{int(r["papers_with_>=1_author"])}" '
        f'data-region="{html.escape(r.region)}" data-name="{html.escape(r.country)}">'
        f'<td class="num rank">{i+1}</td>'
        f'<td class="country">{html.escape(r.country)}</td>'
        f'<td>{chip(r.region)}</td>'
        f'<td class="num strong">{app}</td>'
        f'<td class="barcell"><span class="bar" style="width:{barw:.2f}%"></span>'
        f'<span class="pct">{pct:.1f}%</span></td>'
        f'<td class="num">{int(r.first_author) or "&middot;"}</td>'
        f'<td class="num">{int(r.last_author) or "&middot;"}</td>'
        f'<td class="num">{int(r.corresponding_author) or "&middot;"}</td>'
        f'<td class="num">{int(r["papers_with_>=1_author"])}</td>'
        f'</tr>')
rows_html = '\n'.join(rows_html)

# ---- region rollup bars ----
rollmax = roll.authors.max()
roll_html = []
for _, r in roll.iterrows():
    roll_html.append(
        f'<div class="rollrow">'
        f'<div class="rolllab">{chip(r.region)}<span class="rollmeta">{int(r.countries)} countries</span></div>'
        f'<div class="rollbarwrap"><span class="rollbar" style="width:{r.authors/rollmax*100:.1f}%;'
        f'background:{REGC.get(r.region,"#888")}"></span></div>'
        f'<div class="rollnum">{int(r.authors)}<span class="rollpct">{r.pct:.1f}%</span></div>'
        f'</div>')
roll_html = '\n'.join(roll_html)

STAT = [
    (str(NCOUNTRY), 'countries represented'),
    (_c(NPOS), 'author positions'),
    (str(NPAPERS), 'papers'),
    (f'{PCT_INTL:.0f}%', 'papers are international'),
    (f'{SAUDI_PCT:.0f}%', 'of authors are Saudi'),
]
stat_html = '\n'.join(
    f'<div class="stat"><div class="statv">{v}</div><div class="statl">{l}</div></div>' for v,l in STAT)

HTML = f"""<title>Author countries &mdash; Saudi healthcare research quality</title>
<style>
:root{{
  --accent:#16697a; --accent2:#489fb5;
  --bg:#fbfcfc; --panel:#ffffff; --ink:#1b2b2f; --muted:#5c7075; --line:#dbe6e8;
  --barbg:#e8f0f1; --shadow:0 1px 3px rgba(20,50,60,.06),0 8px 30px rgba(20,50,60,.05);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --body:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
}}
@media (prefers-color-scheme:dark){{:root{{
  --bg:#0e1a1d; --panel:#132427; --ink:#e8eef0; --muted:#93a9ad; --line:#26383d;
  --barbg:#1b3238; --accent:#4db5c9; --accent2:#6fc6d6;
  --shadow:0 1px 3px rgba(0,0,0,.3),0 10px 34px rgba(0,0,0,.28);
}}}}
:root[data-theme="light"]{{
  --bg:#fbfcfc; --panel:#ffffff; --ink:#1b2b2f; --muted:#5c7075; --line:#dbe6e8;
  --barbg:#e8f0f1; --accent:#16697a; --accent2:#489fb5;
  --shadow:0 1px 3px rgba(20,50,60,.06),0 8px 30px rgba(20,50,60,.05);
}}
:root[data-theme="dark"]{{
  --bg:#0e1a1d; --panel:#132427; --ink:#e8eef0; --muted:#93a9ad; --line:#26383d;
  --barbg:#1b3238; --accent:#4db5c9; --accent2:#6fc6d6;
  --shadow:0 1px 3px rgba(0,0,0,.3),0 10px 34px rgba(0,0,0,.28);
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);
  line-height:1.55;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1080px;margin:0 auto;padding:44px 24px 80px}}
.eyebrow{{font-family:var(--body);text-transform:uppercase;letter-spacing:.14em;font-size:12px;
  font-weight:600;color:var(--accent)}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(30px,4.6vw,46px);line-height:1.08;
  margin:.28em 0 .18em;text-wrap:balance;letter-spacing:-.01em}}
.lede{{font-size:18px;color:var(--muted);max-width:64ch;margin:0 0 30px}}
.lede b{{color:var(--ink);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:26px 0 34px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 16px 14px;
  box-shadow:var(--shadow)}}
.statv{{font-family:var(--serif);font-size:clamp(22px,2.6vw,30px);font-weight:600;color:var(--accent);
  font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.statl{{font-size:12.5px;color:var(--muted);margin-top:3px;line-height:1.35}}
section{{margin-top:46px}}
h2{{font-family:var(--serif);font-weight:600;font-size:24px;margin:0 0 4px;letter-spacing:-.01em}}
.sub{{color:var(--muted);font-size:14.5px;margin:0 0 18px;max-width:70ch}}
.mapcard{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:12px;
  box-shadow:var(--shadow);overflow-x:auto}}
.mapcard img{{width:100%;min-width:720px;height:auto;display:block}}
.map-dark{{display:none}} .map-light{{display:block}}
@media (prefers-color-scheme:dark){{.map-dark{{display:block}}.map-light{{display:none}}}}
:root[data-theme="dark"] .map-dark{{display:block}} :root[data-theme="dark"] .map-light{{display:none}}
:root[data-theme="light"] .map-light{{display:block}} :root[data-theme="light"] .map-dark{{display:none}}
.cap{{font-size:12.5px;color:var(--muted);margin:10px 4px 0;line-height:1.45}}
.roll{{display:flex;flex-direction:column;gap:10px;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;padding:20px 22px;box-shadow:var(--shadow)}}
.rollrow{{display:grid;grid-template-columns:210px 1fr 118px;align-items:center;gap:14px}}
.rolllab{{display:flex;align-items:center;gap:9px}}
.rollmeta{{font-size:12px;color:var(--muted)}}
.rollbarwrap{{background:var(--barbg);border-radius:6px;height:15px;overflow:hidden}}
.rollbar{{display:block;height:100%;border-radius:6px}}
.rollnum{{text-align:right;font-variant-numeric:tabular-nums;font-weight:600;font-size:15px}}
.rollpct{{color:var(--muted);font-weight:400;font-size:12.5px;margin-left:8px}}
.chip{{display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;color:var(--ink);
  white-space:nowrap}}
.chip::before{{content:"";width:9px;height:9px;border-radius:50%;background:var(--rc);flex:none}}
.tablecard{{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  box-shadow:var(--shadow);overflow:hidden}}
.tscroll{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:720px;font-size:14px}}
thead th{{position:sticky;top:0;background:var(--panel);text-align:right;font-family:var(--body);
  font-weight:600;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;
  padding:13px 12px;border-bottom:2px solid var(--line);cursor:pointer;user-select:none;white-space:nowrap}}
thead th.l{{text-align:left}}
thead th:hover{{color:var(--accent)}}
th .ar{{opacity:.4;font-size:10px}} th.sorted .ar{{opacity:1;color:var(--accent)}}
tbody td{{padding:9px 12px;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums}}
tbody tr:last-child td{{border-bottom:none}}
tbody tr:hover{{background:color-mix(in srgb,var(--accent) 6%,transparent)}}
td.num{{text-align:right}} td.rank{{color:var(--muted);font-size:12.5px}}
td.country{{font-weight:600;white-space:nowrap}} td.strong{{font-weight:700;color:var(--accent)}}
.barcell{{min-width:150px;white-space:nowrap}}
.bar{{display:inline-block;height:8px;border-radius:4px;background:linear-gradient(90deg,var(--accent),var(--accent2));
  vertical-align:middle}}
.pct{{font-size:12px;color:var(--muted);margin-left:8px;vertical-align:middle}}
.notes{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px 26px;
  box-shadow:var(--shadow);font-size:13.5px;color:var(--muted);line-height:1.62}}
.notes h3{{font-family:var(--serif);color:var(--ink);font-size:16px;margin:0 0 8px}}
.notes b{{color:var(--ink)}} .notes ul{{margin:0;padding-left:20px}} .notes li{{margin:5px 0}}
.foot{{margin-top:30px;font-size:12px;color:var(--muted);text-align:center}}
@media(max-width:820px){{.stats{{grid-template-columns:repeat(2,1fr)}}
  .rollrow{{grid-template-columns:150px 1fr 96px}}}}
</style>

<div class="wrap">
  <div class="eyebrow">Assessment of healthcare research quality in Saudi Arabia</div>
  <h1>The countries behind the authors</h1>
  <p class="lede">Every author on the <b>{NPAPERS} included papers</b> (the 377 adjudicated papers plus 8
  added Saudi-authored papers, from PubMed 2022), placed by the country of their affiliation.
  <b>{_c(NPOS)} author positions</b> resolve to <b>{NCOUNTRY} countries</b> &mdash; the map of an intensely
  international literature anchored in the Gulf.</p>

  <div class="stats">{stat_html}</div>

  <section>
    <h2>Where the authors are based</h2>
    <p class="sub">Proportional-symbol map: each bubble is a country, its area proportional to the number of
    author positions there, coloured by world region. Saudi Arabia (the home base, {_c(SAUDI_APP)} positions) is shown
    as a star rather than a disk so it does not swallow its smaller neighbours.</p>
    <div class="mapcard">
      <img class="map-light" alt="World map of author countries (light)" src="data:image/png;base64,{b64['light']}">
      <img class="map-dark"  alt="World map of author countries (dark)"  src="data:image/png;base64,{b64['dark']}">
    </div>
    <p class="cap">Author positions = one author &times; one paper ({_c(NPOS)} across {NPAPERS} papers). Counted once per country, so dual-affiliated authors contribute to each of their countries and the country totals sum to {_c(TOTAL)}, not {_c(NPOS)}. Bubbles for
    every country except Saudi Arabia; a country&rsquo;s bubble sits at its centroid. {N_BIG} global-consortium
    papers (each &ge;20 countries; the largest lists {MAX_A} authors from {MAX_A_C} countries) inflate the appearance
    counts for Italy, Greece and Nigeria in particular &mdash; see the papers-participated column for a skew-resistant view.</p>
  </section>

  <section>
    <h2>By world region</h2>
    <p class="sub">Author positions grouped into seven regions. Saudi Arabia alone is {SAUDI_PCT:.1f}% of all positions;
    the Gulf as a whole is {GULF_PCT:.1f}%.</p>
    <div class="roll">{roll_html}</div>
  </section>

  <section>
    <h2>All {NCOUNTRY} countries</h2>
    <p class="sub">Click any column heading to re-sort. <b>Authors</b> counts author positions (skewed by large
    consortia); <b>Papers</b> counts distinct papers with at least one author from that country (skew-resistant).
    <b>First</b>, <b>Last</b> and <b>Corr.</b> count papers whose first-listed, last-listed, or corresponding
    author is based there. Corresponding authors are resolved by name (339 papers) or by e-mail (3); for the
    remaining 43 the source file records no usable name — it identified the author from the paper's affiliation
    marker and address — so Saudi status comes from the hand-coded, PDF-confirmed flag, which also carries the
    convention that a paper counts as Saudi-corresponding if <i>any</i> of its corresponding authors is Saudi.
    A flag cannot name a foreign country, so for <b>9 papers, all of them non-Saudi, no country is counted</b>
    and the non-Saudi corresponding totals are lower bounds. Saudi = 246, matching Table 1.</p>
    <div class="tablecard"><div class="tscroll">
      <table id="t">
        <thead><tr>
          <th class="num" data-k="rank">#</th>
          <th class="l" data-k="name">Country</th>
          <th class="l" data-k="region">Region</th>
          <th class="num sorted" data-k="app">Authors <span class="ar">&#9660;</span></th>
          <th class="num" data-k="app">Share</th>
          <th class="num" data-k="first">First</th>
          <th class="num" data-k="last">Last</th>
          <th class="num" data-k="corr">Corr.</th>
          <th class="num" data-k="pap">Papers</th>
        </tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div></div>
  </section>

  <section>
    <h2>How this was built</h2>
    <div class="notes">
      <h3>Source &amp; method</h3>
      <p>The population is the <b>{NPAPERS} papers</b> = the 377 adjudicated papers + 8 added Saudi-authored papers
      (5 that had only one reviewer, plus 3 new); it excludes two papers with no Saudi author and one co-authored by
      a study PI. Author lists and affiliation strings come from <b>PubMed E-utilities</b>. A country classifier reads
      each affiliation block &mdash; splitting on <code>|</code> and <code>;</code>, taking the rightmost country per
      institution, so &ldquo;China Medical University, Taichung, <b>Taiwan</b>&rdquo; resolves to Taiwan, not China. An
      author&rsquo;s <b>primary country</b> is that of their first-listed affiliation; dual-affiliation authors
      ({DUAL_PCT:.1f}% of positions) keep every country they list.</p>
      <h3>Coverage &amp; validation</h3>
      <ul>
        <li><b>100% of {_c(NPOS)} author positions</b> are placed: {_c(N_PUBMED)} from PubMed affiliations,
        {N_GOLD} recovered from the project&rsquo;s PDF-verified affiliation notes, and {N_MAN} from within-paper
        institutional context (truncated PubMed records).</li>
        <li>The classifier reproduces the study&rsquo;s hand-verified &ldquo;any Saudi author&rdquo; flag on all
        <b>{N_VALID} papers it covers</b> ({N_VALID}/{N_VALID}; the 3 newly-added papers post-date that file) &mdash;
        an independent check that Saudi affiliations are caught wherever they appear.</li>
        <li>One correction to the legacy file: PMID STUDY-0531 lists first and last authors (Abusrair, Bohlega) with a
        truncated &ldquo;Divisions of Neurology and.&rdquo; string; the raw PubMed record and co-author context place
        both at King Faisal Specialist Hospital, Riyadh &mdash; <b>Saudi Arabia</b>.</li>
      </ul>
      <h3>Reading the numbers</h3>
      <ul>
        <li><b>Author positions vs. people:</b> an author on two papers is counted twice; this is an author-position
        map, not a de-duplicated headcount.</li>
        <li><b>Primary vs. any affiliation:</b> {FIRST_PRIMARY} papers have a Saudi <i>first-listed</i> first author;
        {FIRST_ANY} have a first author with <i>any</i> Saudi affiliation &mdash; the {FIRST_GAP}-paper gap is
        dual-affiliated first authors.</li>
        <li>Counts are over the <b>{NPAPERS} included papers</b> (the 377 analysis subset gives a near-identical
        distribution).</li>
      </ul>
    </div>
  </section>

  <p class="foot">Generated 2026-07-25 &middot; data: <code>data/authors/07_25_2026_country_counts.csv</code>,
  <code>data/authors/07_25_2026_author_country_long.csv</code>, <code>data/authors/07_25_2026_paper_country_summary.csv</code></p>
</div>

<script>
(function(){{
  // Theme-aware map swap: inline styles win over any cascade quirk; handles initial
  // prefers-color-scheme AND the viewer's data-theme toggle.
  var ml=document.querySelector('.map-light'), md=document.querySelector('.map-dark');
  function setMap(){{
    var t=document.documentElement.getAttribute('data-theme');
    var dark = t==='dark' || (!t && matchMedia('(prefers-color-scheme:dark)').matches);
    md.style.display=dark?'block':'none'; ml.style.display=dark?'none':'block';
  }}
  setMap();
  try{{matchMedia('(prefers-color-scheme:dark)').addEventListener('change',setMap);}}catch(e){{}}
  new MutationObserver(setMap).observe(document.documentElement,{{attributes:true,attributeFilter:['data-theme']}});
}})();
(function(){{
  var tb=document.querySelector('#t tbody'), ths=document.querySelectorAll('#t thead th');
  var cur='app', asc=false;
  function sort(k,th){{
    asc = (k===cur)? !asc : (k==='name'||k==='region');
    cur=k;
    ths.forEach(function(h){{h.classList.remove('sorted');var a=h.querySelector('.ar');if(a)a.remove();}});
    th.classList.add('sorted');
    var s=document.createElement('span');s.className='ar';s.innerHTML=asc?' &#9650;':' &#9660;';th.appendChild(s);
    var rows=[].slice.call(tb.querySelectorAll('tr'));
    rows.sort(function(a,b){{
      var x,y;
      if(k==='name'||k==='region'){{x=a.dataset[k];y=b.dataset[k];return asc?x.localeCompare(y):y.localeCompare(x);}}
      if(k==='rank'){{x=+a.querySelector('.rank').textContent;y=+b.querySelector('.rank').textContent;}}
      else{{x=+a.dataset[k];y=+b.dataset[k];}}
      return asc?x-y:y-x;
    }});
    rows.forEach(function(r){{tb.appendChild(r);}});
  }}
  ths.forEach(function(th){{th.addEventListener('click',function(){{sort(th.dataset.k,th);}});}});
}})();
</script>
"""

with open('outputs/reports/07_25_2026_author_countries_artifact.html','w',encoding='utf-8') as f:
    f.write(HTML)
print('wrote outputs/reports/07_25_2026_author_countries_artifact.html', len(HTML)//1024, 'KB')
