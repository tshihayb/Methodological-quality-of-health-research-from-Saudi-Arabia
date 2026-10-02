# NOTE (public repository): 4 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
import pandas as pd
import html as _h
import json

w = pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv', dtype=str)
N = len(w)

# team size — count authors with a REAL surname; collective/group entries are not authors
# (differs from the raw n_authors field for 4 papers: STUDY-0737, STUDY-0821, STUDY-0970, STUDY-0017)
# canonical 385 author cache (the old data/authors/pubmed_authors_cache.json lacks the 3 newly-included papers)
_ts = pd.read_csv('data/scoring/07_30_2026_team_size_385.csv', dtype=str)[['PMID', 'team_cat']]
w = w.merge(_ts, on='PMID', how='left')

# unified design + Saudi data use, keyed off the task
def pick(row, stem):
    return row.get({'Causal':'causal_','Descriptive':'descriptive_','Predictive':'predictive_'}[row['Study_Type']]+stem)
w['design'] = w.apply(lambda r: pick(r,'design'), axis=1)
w['saudi_data'] = w.apply(lambda r: pick(r,'pop'), axis=1)

SHORT = {
 'Randomized clinical trial (including all types of randomized experiments)':'Randomized clinical trial',
 'Cohort (including clinical trials without randomization)':'Cohort',
}
w['design'] = w['design'].map(lambda d: SHORT.get(d, d))

# --- institution sector (Academic-only vs Health-system), single/multi-sector, JCR quartile ---
# derivations mirror code/scoring/07_30_2026_stratified_analysis.R, extended to ALL 385 papers (incl. predictive)
_inst = pd.read_csv('data/authors/07_25_2026_saudi_paper_level.csv', dtype=str, keep_default_na=False)[['PMID','health_system','multisector','health_system_union','multisector_union']]
_jcr  = pd.read_csv('data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv', dtype=str, keep_default_na=False)[['PMID','jcr_2022_quartile']]
_HEALTH = {'Hospital / medical city','Hospital & research centre','Ministry of Health','Military & security-forces medical'}
_inst['comp_lab'] = _inst['health_system'].map(
    lambda v: 'Health-system' if str(v) in ('True','TRUE','1') else 'Academic-only')
_inst['msec_lab'] = _inst['multisector'].map(lambda v: 'Multi-sector' if str(v) in ('True','TRUE','1') else 'Single-sector')
# UPPER BOUND on both sector stratifiers (TSA ruling 2026-08-24: report bounds, don't choose).
# S2 credits each Saudi author to ONE institution -- the top-level employer named in their
# first Saudi affiliation block -- so where an affiliation names several (176 of 1,520
# author-appearances, 11.6%; 08_24_2026_institution_choice_sensitivity.py) the others are
# dropped BEFORE the paper-level union is taken. A paper can therefore lose a sector but
# never gain one. `sectors_present_union` credits every institution each author is on record
# for; the two together bracket the truth. Footnote numbers below are computed, never typed.
_inst['comp_lab_u'] = _inst['health_system_union'].map(
    lambda v: 'Health-system' if str(v) in ('True','TRUE','1') else 'Academic-only')
_inst['msec_lab_u'] = _inst['multisector_union'].map(lambda v: 'Multi-sector' if str(v) in ('True','TRUE','1') else 'Single-sector')
_jcr['jcr'] = _jcr['jcr_2022_quartile'].map(lambda v: v if str(v).strip() in ('Q1','Q2','Q3','Q4') else 'None')
w = (w.merge(_inst[['PMID','comp_lab','msec_lab','comp_lab_u','msec_lab_u']], on='PMID', how='left')
       .merge(_jcr[['PMID','jcr']], on='PMID', how='left'))
w['comp_lab']=w['comp_lab'].fillna('Academic-only'); w['msec_lab']=w['msec_lab'].fillna('Single-sector'); w['jcr']=w['jcr'].fillna('None')
w['comp_lab_u']=w['comp_lab_u'].fillna(w['comp_lab']); w['msec_lab_u']=w['msec_lab_u'].fillna(w['msec_lab'])

# --- the sector BOUND, computed for the footnote ---
BOUND = {
    'hs_lo': int((w.comp_lab=='Health-system').sum()), 'hs_hi': int((w.comp_lab_u=='Health-system').sum()),
    'ao_lo': int((w.comp_lab=='Academic-only').sum()), 'ao_hi': int((w.comp_lab_u=='Academic-only').sum()),
    'ms_lo': int((w.msec_lab=='Multi-sector').sum()),  'ms_hi': int((w.msec_lab_u=='Multi-sector').sum()),
    'ss_lo': int((w.msec_lab=='Single-sector').sum()), 'ss_hi': int((w.msec_lab_u=='Single-sector').sum()),
    'moved_comp': int(((w.comp_lab=='Academic-only') & (w.comp_lab_u=='Health-system')).sum()),
    'moved_msec': int(((w.msec_lab=='Single-sector') & (w.msec_lab_u=='Multi-sector')).sum()),
}
# largest study-task percentage shift between the two rules, over the four sector columns
_shift = 0.0
for _lo, _hi, _lvl in [('comp_lab','comp_lab_u','Academic-only'), ('comp_lab','comp_lab_u','Health-system'),
                       ('msec_lab','msec_lab_u','Single-sector'), ('msec_lab','msec_lab_u','Multi-sector')]:
    _a, _b = w[w[_lo]==_lvl], w[w[_hi]==_lvl]
    for _t in ['Descriptive','Predictive','Causal']:
        if len(_a) and len(_b):
            _shift = max(_shift, abs((_a.Study_Type==_t).mean()-(_b.Study_Type==_t).mean())*100)
BOUND['max_shift'] = round(_shift, 1)

# --- funding (PANEL B) ---
# Read the ADJUDICATED file, not the classifier's output: 28 of the machine's labels were
# overturned by the blind hand-read of all 385 papers and the rulings of 2026-08-25
# (docs/provenance/08_25_2026_funding_rulings.md). `funding_3level_machine` and `apc_only`
# travel with it so the sensitivity below is computed, never typed.
_fund = pd.read_csv('data/analysis/08_25_2026_funding_ADJUDICATED_385.csv', dtype=str,
                    keep_default_na=False)[['PMID', 'funding_3level', 'funding_3level_machine',
                                            'funding_level_firstpass', 'apc_only']]
assert set(_fund.PMID) == set(w.PMID), 'funding file does not cover the same 385 papers'
w = w.merge(_fund, on='PMID', how='left')
assert w.funding_3level.notna().all() and (w.funding_3level != '').all()

# Funder origin is defined ONLY among the funded; the 6-level column carries it.
w['fund_origin'] = w.apply(
    lambda r: {'local': 'Saudi funder', 'international': 'International funder',
               'both': 'Both'}.get(r['funding_level_firstpass'], '')
    if r['funding_3level'] == 'funded' else '', axis=1)
N_FUNDED = int((w.funding_3level == 'funded').sum())

TASKS = ['Descriptive','Predictive','Causal']
# design order within task = overall frequency desc, then name
design_order = {}
for t in TASKS:
    vc = w.loc[w.Study_Type==t,'design'].value_counts()
    design_order[t] = sorted(vc.index, key=lambda d:(-vc[d], str(d)))

# strata: (group_label, level_label, boolean mask)
S = w['saudi_data']; P = w['pct_saudi_ge50']
strata = [
 ('', 'Overall', pd.Series(True, index=w.index)),
 ('Saudi data use', 'Yes', S=='Yes'), ('Saudi data use', 'No', S=='No'),
 ('Number of authors', '1–2', w.team_cat=='1-2'),
 ('Number of authors', '3–10', w.team_cat=='3-10'), ('Number of authors', '11+', w.team_cat=='11+'),
 ('% Saudi authors', '≥50%', P=='>=50%'), ('% Saudi authors', '<50%', P=='<50%'),
 ('Corresponding author', 'Saudi', w.corresponding_author_saudi=='1'), ('Corresponding author', 'Non-Saudi', w.corresponding_author_saudi=='0'),
 ('First author', 'Saudi', w.first_author_saudi=='1'), ('First author', 'Non-Saudi', w.first_author_saudi=='0'),
 ('Last author', 'Saudi', w.last_author_saudi=='1'), ('Last author', 'Non-Saudi', w.last_author_saudi=='0'),
 ('Sector composition', 'Academic-only', w.comp_lab=='Academic-only'), ('Sector composition', 'Health-system', w.comp_lab=='Health-system'),
 ('Single vs multi-sector', 'Single-sector', w.msec_lab=='Single-sector'), ('Single vs multi-sector', 'Multi-sector', w.msec_lab=='Multi-sector'),
 ('JCR 2022 quartile', 'Q1', w.jcr=='Q1'), ('JCR 2022 quartile', 'Q2', w.jcr=='Q2'), ('JCR 2022 quartile', 'Q3', w.jcr=='Q3'), ('JCR 2022 quartile', 'Q4', w.jcr=='Q4'), ('JCR 2022 quartile', 'Not ranked', w.jcr=='None'),
]
def cell(n, denom):
    if denom == 0 or n == 0 and denom == 0: return '<span class="z">—</span>'
    pct = 100.0*n/denom if denom else 0
    return '%d <span class="pct">(%.1f)</span>' % (n, pct)


def build_panel(strata, minwidth):
    """Render one panel: rows = study task -> nested designs, columns = the strata given.

    Factored out when funding was added as PANEL B. Table 1 was already at its width limit
    at 24 value columns / 2160px, so the funding stratifiers are a second panel rather than
    three more columns -- the print and .docx versions cannot take another column group.

    Each stratum is (group_label, level_label, mask, base). `base` is the denominator for the
    column's *share* line only; it is N everywhere except the funder-origin group, which is
    defined only among the funded and so is shown as a share of those.
    """
    masks = [m for _, _, m, _ in strata]
    Ns = [int(m.sum()) for m in masks]
    rows = []
    for t in TASKS:
        tmask = w.Study_Type == t
        tcells = ''.join('<td>%s</td>' % cell(int((m & tmask).sum()), Nc)
                         for m, Nc in zip(masks, Ns))
        rows.append('<tr class="task"><th scope="row">%s</th>%s</tr>' % (t, tcells))
        for d in design_order[t]:
            dmask = tmask & (w.design == d)
            # design % is WITHIN task within each stratum
            dcells = ''
            for m, Nc in zip(masks, Ns):
                n = int((m & dmask).sum()); tn = int((m & tmask).sum())
                dcells += '<td>%s</td>' % cell(n, tn)
            rows.append('<tr class="dsn"><th scope="row">%s</th>%s</tr>'
                        % (_h.escape(str(d)), dcells))

    g_spans = []
    for g, _, _, _ in strata:                      # contiguous runs of the same group label
        if g_spans and g_spans[-1][0] == g:
            g_spans[-1][1] += 1
        else:
            g_spans.append([g, 1])
    grp = '<th class="corner" rowspan="2" scope="col">Study task / design</th>'
    for name, span in g_spans:
        label = name or 'Overall'
        cls = 'gh overall' if label == 'Overall' else 'gh'
        grp += '<th class="%s" colspan="%d" scope="colgroup">%s</th>' % (cls, span,
                                                                        _h.escape(label))
    lvl = ''
    for (_, lab, _, base), Nc in zip(strata, Ns):
        cls = 'lh overall' if lab == 'Overall' else 'lh'
        share = '100%' if Nc == base else '%.1f%%' % (100.0 * Nc / base)
        lvl += ('<th class="%s" scope="col">%s<span class="ln">n=%d (%s)</span></th>'
                % (cls, _h.escape(lab), Nc, share))
    return ('<div class="tscroll"><table style="min-width:%dpx">'
            '<thead><tr class="grow">%s</tr><tr class="lrow">%s</tr></thead>'
            '<tbody>%s</tbody></table></div>' % (minwidth, grp, lvl, ''.join(rows)))


strata = [(g, l, m, N) for g, l, m in strata]
TABLE = build_panel(strata, 2160)

# ---- PANEL B: funding
F = w['funding_3level']; O = w['fund_origin']
strata_f = [
    ('', 'Overall', pd.Series(True, index=w.index), N),
    ('Funding status', 'Funded', F == 'funded', N),
    ('Funding status', 'Non-funded', F == 'non_funded', N),
    ('Funding status', 'Not stated', F == 'not_stated', N),
    ('Funder origin (of the %d funded)' % N_FUNDED, 'Saudi funder', O == 'Saudi funder', N_FUNDED),
    ('Funder origin (of the %d funded)' % N_FUNDED, 'International funder',
     O == 'International funder', N_FUNDED),
    ('Funder origin (of the %d funded)' % N_FUNDED, 'Both', O == 'Both', N_FUNDED),
]
TABLE_F = build_panel(strata_f, 980)

# ---- the R2 sensitivity, computed for the funding footnote ----
# R2 ruled that publication money (an article-processing charge, an open-access agreement) is
# not research funding. 10 papers are `not_stated` on that rule ALONE and carry `apc_only`;
# counting them as funded is the one substitution that could reasonably be argued.
_alt = w['funding_3level'].where(w['apc_only'] != '1', 'funded')
FUND = {
    'n_apc': int((w['apc_only'] == '1').sum()),
    'f_lo': int((w.funding_3level == 'funded').sum()), 'f_hi': int((_alt == 'funded').sum()),
    'ns_hi': int((w.funding_3level == 'not_stated').sum()),
    'ns_lo': int((_alt == 'not_stated').sum()),
    'n_changed': int((w.funding_3level != w.funding_3level_machine).sum()),
}
FUND['f_lo_p'] = '%.1f' % (100.0 * FUND['f_lo'] / N)
FUND['f_hi_p'] = '%.1f' % (100.0 * FUND['f_hi'] / N)
FUND['ns_hi_p'] = '%.1f' % (100.0 * FUND['ns_hi'] / N)
FUND['ns_lo_p'] = '%.1f' % (100.0 * FUND['ns_lo'] / N)
_fs = 0.0
for _lvl in ('funded', 'not_stated'):
    _a, _b = w[w.funding_3level == _lvl], w[_alt == _lvl]
    for _t in TASKS:
        if len(_a) and len(_b):
            _fs = max(_fs, abs((_a.Study_Type == _t).mean() - (_b.Study_Type == _t).mean()) * 100)
FUND['max_shift'] = '%.1f' % _fs
# The true "silent" count: papers with no funding vocabulary anywhere. NOT the same as
# `not_stated`, which by design contains papers that print money words tied to publication,
# to thanks, or to an ethics body. Conflating the two would overstate the silence -- so the
# footnote states both, and reads the number rather than carrying a literal that would rot
# the moment a ruling changed.
_q = json.load(open('data/provenance/08_25_2026_funding_quantities.json', encoding='utf-8'))
assert _q['n_papers'] == N and _q['not_stated'] == int((w.funding_3level == 'not_stated').sum()), \
    'funding quantities are stale — re-run 08_25_2026_verify_adjudicated_funding.py'
FUND['silent'] = _q['no_funding_vocabulary']
FUND['silent_p'] = '%.1f' % (100.0 * FUND['silent'] / N)
FUND['nostmt'] = _q['no_funding_statement']

PAGE = '''<title>Study tasks and designs by Saudi affiliation, team size, institution sector, journal quartile, and funding</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--ovl:#eef5f6;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--ovl:#152a30;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--ovl:#eef5f6;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--ovl:#152a30;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5;
-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,60px) 20px}
.wrap{max-width:1120px;margin:0 auto}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(25px,3.6vw,34px);line-height:1.14;letter-spacing:-.01em;
margin:0 0 14px;text-wrap:balance;max-width:26ch}
.lede{color:var(--muted);font-size:15px;max-width:70ch;margin:0 0 26px}
.lede b{color:var(--ink);font-weight:600}
.tscroll{overflow-x:auto;border:1px solid var(--hair);border-radius:11px;background:var(--panel)}
table{border-collapse:collapse;font-size:13.5px;min-width:2160px;width:100%}
th,td{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
thead .grow th{padding:12px 12px 6px;font-family:var(--serif);font-weight:600;font-size:13px;color:var(--ink);
text-align:center;border-bottom:1px solid var(--hair)}
thead .grow th.gh{letter-spacing:.01em}
thead .lrow th{padding:4px 12px 10px;font-size:12px;font-weight:600;color:var(--muted);text-align:right;
border-bottom:2px solid var(--ink);vertical-align:bottom}
thead th.overall{background:var(--ovl)}
.lh{position:relative}
.lh .ln{display:block;font-size:10.5px;font-weight:500;color:var(--faint);letter-spacing:.03em;margin-top:1px}
th.corner{text-align:left;vertical-align:bottom;padding:12px 14px 10px;font-family:var(--sans);font-size:11px;
letter-spacing:.06em;text-transform:uppercase;color:var(--faint);font-weight:600;border-bottom:2px solid var(--ink)}
th[scope="row"]{text-align:left;font-weight:400;white-space:normal}
tbody td,tbody th{padding:7px 12px}
td{color:var(--ink)}
.pct{color:var(--faint);font-size:12px}
.z{color:var(--faint)}
tr.task th[scope="row"]{font-family:var(--serif);font-weight:600;font-size:15px}
tr.task{border-top:1px solid var(--hair-strong)}
tr.task td{font-weight:600}
tr.dsn th[scope="row"]{padding-left:26px;color:var(--muted);font-size:13px}
tr.dsn td{color:var(--muted)}
tbody tr:hover td,tbody tr:hover th[scope="row"]{background:var(--row)}
/* sticky label + overall */
th.corner,th[scope="row"]{position:sticky;left:0;background:var(--panel);z-index:2}
tbody tr:hover th[scope="row"]{background:var(--row)}
td.ovcol,.overall{}
colgroup .ov{background:var(--ovl)}
.foot{margin-top:20px;color:var(--faint);font-size:12.5px;max-width:88ch;line-height:1.6}
.foot b{color:var(--muted)}
.foot code{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
.tabtag{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;
color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line);padding:3px 9px;border-radius:5px;margin:0 0 12px}
.panel{font-family:var(--serif);font-weight:600;font-size:17px;margin:34px 0 4px;color:var(--ink);
padding-left:11px;border-left:3px solid var(--accent-line)}
.psub{color:var(--muted);font-size:13.5px;margin:0 0 12px;max-width:78ch}
</style>
<div class="wrap">
<span class="tabtag">Table 1</span>
<p class="eyebrow">Assessment of Healthcare Research Quality · Saudi Arabia</p>
<h1>Study tasks and designs, overall and by Saudi affiliation, team size, institution sector, journal quartile, and funding</h1>
<p class="lede">Distribution of the <b>__N__ included papers</b> across the three predetermined study tasks and, within each task, their study designs. The first block stratifies by Saudi data use, <b>team size</b> (number of authors), four Saudi-affiliation measures, the <b>institutional sector</b> of the Saudi authors, and the journal’s <b>JCR 2022 quartile</b>; the second stratifies by <b>funding</b>, coded from the full text of every paper. Values are <b>n (%)</b>: study-task rows are the percentage of the column; design rows are the percentage <b>within that task</b>.</p>
<p class="panel">Saudi affiliation, team size, institution sector, and journal quartile</p>
__TABLE__
<p class="panel">Funding</p>
<p class="psub">Funding is a separate block rather than four more columns: the table above is already at its printable width. Same rows, same percentage conventions. (The .docx version splits these same columns into lettered panels A–D purely to fit the page; the split there carries no other meaning.)</p>
__TABLEF__
<p class="foot">
<b>Column denominators</b> are shown under each heading as <i>n</i> (% of the __N__); every stratifier is complete (no missing values), so each stratifier’s levels sum to __N__ and to 100%. <b>Study-task</b> rows give n (% of the column N); indented <b>design</b> rows give n (% of that task within the column) and sum to the task above. <b>Saudi data use</b> = the study used data from Saudi Arabia (tool item, per task). <b>% Saudi authors</b> = <code>&#8805;50%</code> vs <code>&lt;50%</code> of the author list Saudi-affiliated. <b>Corresponding / First / Last author</b> = that author’s affiliation is Saudi vs non-Saudi. <b>Number of authors</b> = team size, counting only authors with a real surname (collective/group entries are not authors); median 6, IQR 4–9, range 1–377. <b>Sector composition</b> = at least one Saudi author at a hospital, medical city, Ministry of Health, or military-health body (Health-system) versus university/academic only. <b>Single vs multi-sector</b> = whether the paper’s Saudi authors span more than one Saudi institution type. <b>JCR 2022 quartile</b> = Clarivate Journal Citation Reports 2022 impact-factor quartile; <i>Not ranked</i> = no 2022 <i>quartile</i>, which is not the same as no impact factor — 27 of these 87 papers are in Emerging Sources Citation Index journals that carry a JIF but are assigned no quartile, 49 in journals delisted before the 2022 edition, 5 in journals whose JIF was suppressed, and 6 in journals not in the Web of Science Core Collection at all (Supplementary Methods 4). Predictive designs are Diagnostic and Prognostic (no epidemiological bias items — see Table 2). Study tasks and designs are as originally coded by the reviewers/adjudicators; the 2026-08-12 inconsistency-resolution worklist kept these (no design or follow-up was relabelled).
<br><br><b>The two sector stratifiers are bounds, not points.</b> Each Saudi author is credited to the <i>single</i> institution their affiliation names as top-level employer; where an affiliation names more than one, the others are not recorded, so a paper can lose a sector but never gain one. Crediting instead every institution each author is on record for moves __MOVEDC__ papers from Academic-only to Health-system and __MOVEDM__ from single- to multi-sector, giving <b>Health-system __HSHI__</b> (Academic-only __AOHI__) and <b>Multi-sector __MSHI__</b> (Single-sector __SSHI__). The columns above use the single-institution rule (__HSLO__ and __MSLO__); read the pair as a bound. Within it no study-task percentage moves by more than __SHIFT__ points and no ordering changes.<br><br><b>Two cautions on the stratifiers.</b> (i) <b>Corresponding author is largely redundant with first author</b>: the corresponding author <i>is</i> the first author in 67.3% of papers and the last in 24.1% (first-or-last 84.8%), and <code>corresponding_author_saudi</code> agrees with <code>first_author_saudi</code> 90.9% of the time versus 79.2% with last. Where first and last disagree, the corresponding author follows the <i>first</i>. Treat first vs last as the substantive contrast. (ii) <b>Team size is confounded with Saudi affiliation</b> (Spearman &#8722;0.36 with % Saudi authors): every single-author paper is ≥50% Saudi (Saudi by inclusion) and 84.0% of one- or two-author papers are entirely Saudi, versus 43.3% of 11+ author papers reaching ≥50% Saudi, so for small teams the % Saudi measure is largely degenerate. Read the team-size columns as collaboration scale, not as a further affiliation measure.
<br><br><b>Funding.</b> Coded from the full text of all __N__ papers. <b>Funded</b> = the paper states that this study received money, or personnel or equipment paid for by a named body, a named scheme, or a grant number. <b>Non-funded</b> = the paper explicitly declares it received none. <b>Not stated</b> = the paper does not resolve either way. <b>Funder origin</b> is defined only among the __NFUNDED__ funded papers and its three columns sum to them, not to __N__. Every label was machine-extracted, then independently re-read by hand against the paper text; __NCHANGED__ of the machine's labels were overturned, and the rulings behind them are recorded per paper in <code>data/adjudication/08_25_2026_funding_rulings.csv</code>.
<br><br><b>“Not stated” is not the same as silence, and neither is the transparency finding.</b> A publication fee — an article-processing charge, or an open-access agreement — is not research funding, so a paper whose only money pays for publication is recorded as <i>not stated</i>: it has told you nothing about whether the research itself was funded. The same holds for thanks carrying no money, and for a deanship named only as the ethics approver. Three quantities therefore differ and should not be interchanged: <b>__NSHI__ papers (__NSHIP__%) do not state research funding</b>; <b>__NOSTMT__ print no funding statement at all</b>; and <b>__SILENT__ (__SILENTP__%) contain no funding vocabulary anywhere</b> — the strictest reading of “says nothing about funding”.
<br><br><b>The publication-fee rule is the one substitution worth testing.</b> __NAPC__ papers are <i>not stated</i> on that rule alone; counting their publication money as research funding instead would give <b>funded __FHI__ (__FHIP__%)</b> and <i>not stated</i> <b>__NSLO__ (__NSLOP__%)</b>, against <b>__FLO__ (__FLOP__%)</b> and <b>__NSHI__ (__NSHIP__%)</b> here. Within that bound no study-task percentage moves by more than __FSHIFT__ points and no ordering changes. Funding is a <b>descriptive stratifier</b>: nothing in this table supports a causal claim linking funders to study quality.
</p>
</div>'''
PAGE = (PAGE.replace('__TABLE__', TABLE).replace('__TABLEF__', TABLE_F)
            .replace('__N__', str(N)).replace('__NFUNDED__', str(N_FUNDED)))
for _k, _v in [('__NCHANGED__', FUND['n_changed']), ('__NAPC__', FUND['n_apc']),
               ('__FLO__', FUND['f_lo']), ('__FLOP__', FUND['f_lo_p']),
               ('__FHI__', FUND['f_hi']), ('__FHIP__', FUND['f_hi_p']),
               ('__NSHI__', FUND['ns_hi']), ('__NSHIP__', FUND['ns_hi_p']),
               ('__NSLO__', FUND['ns_lo']), ('__NSLOP__', FUND['ns_lo_p']),
               ('__FSHIFT__', FUND['max_shift']), ('__SILENT__', FUND['silent']),
               ('__SILENTP__', FUND['silent_p']), ('__NOSTMT__', FUND['nostmt'])]:
    PAGE = PAGE.replace(_k, str(_v))
for _k, _v in [('__HSHI__', BOUND['hs_hi']), ('__AOHI__', BOUND['ao_hi']),
               ('__MSHI__', BOUND['ms_hi']), ('__SSHI__', BOUND['ss_hi']),
               ('__HSLO__', BOUND['hs_lo']), ('__MSLO__', BOUND['ms_lo']),
               ('__MOVEDC__', BOUND['moved_comp']), ('__MOVEDM__', BOUND['moved_msec']),
               ('__SHIFT__', BOUND['max_shift'])]:
    PAGE = PAGE.replace(_k, str(_v))

open('outputs/tables/07_22_2026_table1_task_design.html','w',encoding='utf-8').write(PAGE)

# console sanity check
print('N =', N, '| task:', dict(w.Study_Type.value_counts()))
print('saudi_data:', dict(w.saudi_data.value_counts(dropna=False)))
print('column Ns:', {lvl: int(m.sum()) for _, lvl, m, _ in strata})
print('funding  :', {lvl: int(m.sum()) for _, lvl, m, _ in strata_f})
assert sum(int(m.sum()) for g, _, m, _ in strata_f if g == 'Funding status') == N
assert sum(int(m.sum()) for g, _, m, _ in strata_f if g.startswith('Funder origin')) == N_FUNDED
print('R2 bound : funded %s (%s%%) -> %s (%s%%); max task shift %s pts'
      % (FUND['f_lo'], FUND['f_lo_p'], FUND['f_hi'], FUND['f_hi_p'], FUND['max_shift']))
_left = [tok for tok in ('__N__', '__TABLE__', '__TABLEF__', '__SILENT__', '__NAPC__',
                         '__FHI__', '__NSHI__', '__FSHIFT__', '__NOSTMT__', '__NFUNDED__',
                         '__NCHANGED__') if tok in PAGE]
assert not _left, 'unsubstituted placeholders: %s' % _left
print('wrote outputs/tables/07_22_2026_table1_task_design.html')
