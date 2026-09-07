"""Build the manual-verification worksheet for the 14 disputed stratifier papers.

TSA asked to check these by hand before anything is written to the analysis dataset, so the
page has to carry the EVIDENCE, not the conclusion: every author, the affiliation string each
source saw, and what each source concluded. The counts are then something the reader can
re-derive rather than take on trust.

Honors the project design system used by the other artifacts (petrol-teal #16697a, serif
headings, tabular-nums) rather than inventing a new identity.

Run from the repository root.
"""
import html
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

D = json.load(open('data/quality-control/_strat14.json', encoding='utf-8'))
OUT = 'outputs/reports/08_24_2026_stratifier_worksheet.html'

TOT_A = sum(len(p['authors']) for p in D)
N_CAT = sum(1 for p in D if p['ge50_wide'] != p['ge50_s1'])
N_CNT = sum(1 for p in D if p['n_wide'] != p['n_s1'])
N_SAU = sum(1 for p in D if p['s_wide'] != p['s_s1'])
# hand-read agrees with S1 on the Saudi count
N_HRAGREE = sum(1 for p in D if p['s_hr'] == p['s_s1'])


def esc(s):
    return html.escape(str(s))


def flag(v):
    if v is None:
        return '<span class="f f-na" title="not hand-read">&ndash;</span>'
    return ('<span class="f f-y">Saudi</span>' if v
            else '<span class="f f-n">&mdash;</span>')


cards = []
for p in D:
    cat = p['ge50_wide'] != p['ge50_s1']
    rows = []
    for a in p['authors']:
        disagree = (a['hr_saudi'] is not None) and (a['hr_saudi'] != a['s1_saudi'])
        rows.append(
            f'<tr class="{"row-s" if a["s1_saudi"] else ""}{" row-x" if disagree else ""}">'
            f'<td class="n">{a["i"]}</td>'
            f'<td class="nm">{esc(a["name"])}</td>'
            f'<td class="af">{esc(a["aff"][:260])}</td>'
            f'<td class="ct">{esc(a["s1"])}</td>'
            f'<td class="fl">{flag(a["s1_saudi"])}</td>'
            f'<td class="fl">{flag(a["hr_saudi"])}</td></tr>')
    same_n = p['n_wide'] == p['n_s1']
    issue = []
    if not same_n:
        issue.append(f'<b>Author count</b> &mdash; the analysis dataset counts '
                     f'<b>{p["n_wide"]}</b>, S1 and the hand-read both count '
                     f'<b>{p["n_s1"]}</b>. The extra entry is a collective/group author, '
                     f'which the project convention excludes.')
    if p['s_wide'] != p['s_s1']:
        who = ', '.join(a['name'] for a in p['authors'] if a['s1_saudi']) or '&mdash;'
        issue.append(f'<b>Saudi count</b> &mdash; dataset says <b>{p["s_wide"]}</b>, '
                     f'S1 says <b>{p["s_s1"]}</b>, hand-read says <b>{p["s_hr"]}</b>. '
                     f'S1&rsquo;s Saudi authors are: {esc(who)}. The dataset&rsquo;s figure is '
                     f'a paper-level total from the 07-16 build and cannot be attributed to '
                     f'named authors.')
    if p['first_wide'] != p['first_s1'] or p['last_wide'] != p['last_s1']:
        bits = []
        if p['first_wide'] != p['first_s1']:
            bits.append(f'first author {p["first_wide"]}&rarr;{p["first_s1"]}')
        if p['last_wide'] != p['last_s1']:
            bits.append(f'last author {p["last_wide"]}&rarr;{p["last_s1"]}')
        issue.append(f'<b>Position flags</b> &mdash; {"; ".join(bits)}.')
    if cat:
        issue.append(f'<b class="hot">Moves Table 1</b> &mdash; <code>pct_saudi_ge50</code> '
                     f'{p["ge50_wide"]} &rarr; {p["ge50_s1"]}.')

    cards.append(f"""
<section class="card{' card-hot' if cat else ''}" id="p{p['pmid']}">
  <header class="ch">
    <div class="chl">
      <div class="pmid">PMID {p['pmid']}{'<span class="tag">moves Table 1</span>' if cat else ''}</div>
      <h2>{esc(p['title'])}</h2>
    </div>
    <table class="mini"><thead><tr><th></th><th>dataset</th><th>S1</th><th>hand-read</th></tr></thead>
    <tbody>
      <tr><td>authors</td><td class="{'x' if not same_n else ''}">{p['n_wide']}</td><td>{p['n_s1']}</td><td>{p['n_hr']}</td></tr>
      <tr><td>Saudi</td><td class="{'x' if p['s_wide'] != p['s_s1'] else ''}">{p['s_wide']}</td><td>{p['s_s1']}</td><td>{p['s_hr']}</td></tr>
      <tr><td>&ge;50%</td><td class="{'x' if cat else ''}">{esc(p['ge50_wide'])}</td><td colspan="2">{esc(p['ge50_s1'])}</td></tr>
    </tbody></table>
  </header>
  <ul class="issue">{''.join(f'<li>{i}</li>' for i in issue)}</ul>
  <div class="tw"><table class="au">
    <thead><tr><th class="n">#</th><th>author</th><th>affiliation as PubMed records it</th>
    <th>S1 country</th><th>S1</th><th>read</th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table></div>
</section>""")

HTML = f"""<title>Stratifier Adjudication Worksheet</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap">
<style>
:root{{
  --accent:#16697a; --accent2:#489fb5;
  --bg:#fbfcfc; --panel:#ffffff; --ink:#1b2b2f; --muted:#5c7075; --line:#dbe6e8;
  --sub:#f2f7f8; --hot:#a8410f; --hotbg:#fdf1ea; --yes:#0f6b4f; --yesbg:#e8f4ef;
  --shadow:0 1px 2px rgba(20,50,60,.05),0 6px 22px rgba(20,50,60,.05);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --body:"Source Sans 3",system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  --mono:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{
  --bg:#0e1a1d; --panel:#132427; --ink:#e8eef0; --muted:#93a9ad; --line:#26383d;
  --sub:#16292d; --accent:#4db5c9; --accent2:#6fc6d6; --hot:#e8a07a; --hotbg:#2a1a13;
  --yes:#5fc79f; --yesbg:#14302a;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.26);
}}}}
:root[data-theme="dark"]{{
  --bg:#0e1a1d; --panel:#132427; --ink:#e8eef0; --muted:#93a9ad; --line:#26383d;
  --sub:#16292d; --accent:#4db5c9; --accent2:#6fc6d6; --hot:#e8a07a; --hotbg:#2a1a13;
  --yes:#5fc79f; --yesbg:#14302a;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 26px rgba(0,0,0,.26);
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:var(--body);
  line-height:1.55;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}}
.wrap{{max-width:1120px;margin:0 auto;padding:40px 22px 90px}}
.eyebrow{{text-transform:uppercase;letter-spacing:.14em;font-size:11.5px;font-weight:700;
  color:var(--accent)}}
h1{{font-family:var(--serif);font-weight:600;font-size:clamp(28px,4vw,42px);line-height:1.1;
  margin:.3em 0 .25em;text-wrap:balance;letter-spacing:-.01em}}
.lede{{font-size:17px;color:var(--muted);max-width:66ch;margin:0 0 26px}}
.lede b{{color:var(--ink);font-weight:600}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0 30px}}
.stat{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px 15px;
  box-shadow:var(--shadow)}}
.statv{{font-family:var(--serif);font-size:26px;font-weight:600;line-height:1}}
.statl{{color:var(--muted);font-size:12.5px;margin-top:5px}}
.legend{{display:flex;flex-wrap:wrap;gap:16px;align-items:center;background:var(--sub);
  border:1px solid var(--line);border-radius:10px;padding:12px 15px;margin-bottom:30px;
  font-size:13px;color:var(--muted)}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  box-shadow:var(--shadow);margin-bottom:22px;overflow:hidden}}
.card-hot{{border-color:var(--hot);border-width:1.5px}}
.ch{{display:flex;gap:20px;justify-content:space-between;align-items:flex-start;
  padding:17px 19px;border-bottom:1px solid var(--line);flex-wrap:wrap}}
.chl{{flex:1 1 460px;min-width:0}}
.pmid{{font-family:var(--mono);font-size:12px;color:var(--accent);font-weight:600;
  display:flex;align-items:center;gap:9px}}
.tag{{background:var(--hotbg);color:var(--hot);border-radius:20px;padding:2px 9px;
  font-family:var(--body);font-size:10.5px;font-weight:700;letter-spacing:.05em;
  text-transform:uppercase}}
.ch h2{{font-family:var(--serif);font-size:17px;font-weight:600;margin:5px 0 0;
  line-height:1.32;text-wrap:balance}}
.mini{{border-collapse:collapse;font-size:12.5px;flex:0 0 auto}}
.mini th{{color:var(--muted);font-weight:600;padding:2px 9px;text-align:right;font-size:11px}}
.mini td{{padding:2px 9px;text-align:right;border-top:1px solid var(--line)}}
.mini td:first-child{{text-align:left;color:var(--muted)}}
.mini td.x{{color:var(--hot);font-weight:700}}
.issue{{margin:0;padding:14px 19px 14px 38px;background:var(--sub);
  border-bottom:1px solid var(--line);font-size:13.5px;color:var(--muted)}}
.issue li{{margin:5px 0}}
.issue b{{color:var(--ink)}}
.issue b.hot{{color:var(--hot)}}
code{{font-family:var(--mono);font-size:.92em;background:var(--bg);padding:1px 5px;
  border-radius:4px;border:1px solid var(--line)}}
.tw{{overflow-x:auto}}
.au{{width:100%;border-collapse:collapse;font-size:12.5px}}
.au th{{position:sticky;top:0;background:var(--panel);text-align:left;color:var(--muted);
  font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.05em;
  padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
.au td{{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top}}
.au tr:last-child td{{border-bottom:none}}
.au .n{{color:var(--muted);width:34px;text-align:right;font-family:var(--mono);font-size:11.5px}}
.au .nm{{font-weight:600;white-space:nowrap}}
.au .af{{color:var(--muted);max-width:520px;line-height:1.4}}
.au .ct{{white-space:nowrap;font-size:12px}}
.au .fl{{text-align:center;white-space:nowrap}}
.row-s{{background:var(--yesbg)}}
.row-x td{{box-shadow:inset 3px 0 0 var(--hot)}}
.f{{font-size:10.5px;font-weight:700;letter-spacing:.03em;border-radius:20px;padding:2px 8px;
  display:inline-block}}
.f-y{{background:var(--yes);color:#fff}}
.f-n{{color:var(--muted)}}
.f-na{{color:var(--line)}}
footer{{margin-top:34px;padding-top:18px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13px;max-width:70ch}}
</style>
<div class="wrap">
  <div class="eyebrow">Manual verification &middot; 24 August 2026</div>
  <h1>Fourteen papers where the analysis dataset and S1 disagree</h1>
  <p class="lede">The Saudi stratifiers in the analysis dataset come from a
  <b>2026-07-16 build</b>; S1 was rebuilt on 07-25 and corrected again this week. They
  disagree on these {len(D)} papers. Every author is listed below with the affiliation each
  source saw, so the counts can be <b>re-derived rather than taken on trust</b>. Nothing has
  been written to the dataset.</p>

  <div class="stats">
    <div class="stat"><div class="statv">{len(D)}</div><div class="statl">papers in dispute</div></div>
    <div class="stat"><div class="statv">{TOT_A}</div><div class="statl">authors listed for checking</div></div>
    <div class="stat"><div class="statv">{N_SAU}</div><div class="statl">differ on Saudi count</div></div>
    <div class="stat"><div class="statv">{N_CNT}</div><div class="statl">differ on author count</div></div>
    <div class="stat"><div class="statv">{N_CAT}</div><div class="statl">move a Table 1 cell</div></div>
    <div class="stat"><div class="statv">{N_HRAGREE}/{len(D)}</div><div class="statl">hand-read agrees with S1</div></div>
  </div>

  <div class="legend">
    <span><span class="f f-y">Saudi</span> counted Saudi by that source</span>
    <span><b style="color:var(--yes)">Tinted row</b> = S1 counts this author Saudi</span>
    <span><b style="color:var(--hot)">Orange edge</b> = hand-read disagrees with S1 on that author</span>
    <span><b>read</b> = independent hand-read of the PDF; &ndash; means that author was not read</span>
  </div>

  {''.join(cards)}

  <footer>The <b>dataset</b> column is a paper-level total from the 07-16 build and cannot be
  attributed to named authors, which is why no per-author flag is shown for it. <b>S1</b> is
  <code>07_25_2026_author_country_long.csv</code>. <b>read</b> is the 385-paper hand-read,
  independent of PubMed. Where all three disagree, the hand-read and S1 were derived
  separately and agree with each other on {N_HRAGREE} of {len(D)} papers.</footer>
</div>"""

open(OUT, 'w', encoding='utf-8').write(HTML)
print(f'wrote {OUT}  ({len(HTML)//1024} KB, {TOT_A} authors over {len(D)} papers)')
