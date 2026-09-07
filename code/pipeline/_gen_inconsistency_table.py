# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Full inventory of hard skip-logic + soft-dependency inconsistencies on the 377 dataset."""
import html as H
import pandas as pd
import _check_contradictions as CC

W = CC.load('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv')
W0 = CC.load('data/analysis/07_16_2026_ANALYSIS_DATASET_long.csv')
R, R0 = CC.soft(W), CC.soft(W0)
gaps, extras = CC.skiplogic(W)
gaps0, _ = CC.skiplogic(W0)
G = pd.DataFrame(gaps, columns=['task', 'PMID', 'parent', 'pval', 'child', 'cval'])
G0 = pd.DataFrame(gaps0, columns=['task', 'PMID', 'parent', 'pval', 'child', 'cval'])

RULES = [
 ('HARD', 'GAP', 'Parent makes the child applicable, but the child was never answered', ''),
 ('HARD', 'EXTRA', 'Parent makes the child not applicable, yet a value survives', ''),
 ('Design', 'S1',  'design = Cross-sectional &rArr; follow &ne; Yes', ''),
 ('Design', 'S8',  'follow = Yes &rArr; design not Cross-sectional / Ecological', 'same 3 papers as S1 &mdash; no Ecological paper has follow=Yes'),
 ('Design', 'S2',  'follow = No &rArr; time-varying effect &ne; Yes', ''),
 ('Design', 'S9',  'time-varying effect = Yes &rArr; follow = Yes', ''),
 ('Design', 'S6a', '&ldquo;Randomization&rdquo; among methods &rArr; design = RCT', ''),
 ('Design', 'S6b', 'design = RCT &rArr; &ldquo;Randomization&rdquo; among methods', ''),
 ('Design', 'S7',  'design = Quasi-experimental &rArr; an IV / DiD / RDD / ITS method is listed', 'now a real pass &mdash; STUDY-0268 exists and lists the IV method'),
 ('Design', 'S22', 'longitudinal design (Cohort, Case-crossover, Pre/post, Quasi-exp, RCT) &rArr; follow &ne; No', ''),
 ('Sampling', 'S10C', 'causal: sampling = Non-random &rArr; base_sel &ne; &ldquo;No baseline SB&rdquo;', 'mostly RCTs &mdash; the rule conflates non-random <i>sampling</i> with baseline <i>selection bias</i>'),
 ('Sampling', 'S11C', 'causal: converse of S10C', 'same papers as S10C'),
 ('Sampling', 'S10D', 'descriptive: sampling = Non-random &rArr; base_sel &ne; &ldquo;No baseline SB&rdquo;', ''),
 ('Sampling', 'S11D', 'descriptive: converse of S10D', 'same papers as S10D'),
 ('Measurement', 'S3',  'val_exposure = &ldquo;objective, not required&rdquo; &rArr; exposure_type = Objective', ''),
 ('Measurement', 'S4C', 'causal: val_outcome = &ldquo;objective, not required&rdquo; &rArr; outcome_type = Objective', ''),
 ('Measurement', 'S4D', 'descriptive: same as S4C', ''),
 ('Measurement', 'S12', 'exp_bias_acc = Yes &rArr; val_exposure = criterion', ''),
 ('Measurement', 'S13C', 'causal: out_bias_acc = Yes &rArr; val_outcome = criterion', ''),
 ('Measurement', 'S13D', 'descriptive: same as S13C', ''),
 ('LTFU', 'S15', 'ltfu_acc has a value &rArr; ltfu_bias = Yes', ''),
 ('Missing data', 'S16',  'hand_miss_exposure = imputation &rArr; miss_exposure = Yes', ''),
 ('Missing data', 'S17C', 'causal: hand_miss_outcome = imputation &rArr; miss_outcome = Yes', ''),
 ('Missing data', 'S17D', 'descriptive: same as S17C', ''),
 ('Confounding', 'S5',  'base_conf_meth = a real method &rArr; conf_var_det names a selection basis', '24 of the 31 are randomization-only &rArr; <b>moot under Ruling&nbsp;3</b>; 7 genuine, of which STUDY-0613 is the deliberate &ldquo;couldn&rsquo;t be known&rdquo; blank'),
 ('Confounding', 'S5b', 'conf_var_det names a basis &rArr; base_conf_meth = a real method', ''),
 ('Confounding', 'S18', 'base_conf_meth = &ldquo;No adjustment&rdquo; &rArr; conf_var_det also none / no adjustment', ''),
 ('Confounding', 'S19', 'tv_conf_meth = a real method &rArr; time-varying effect = Yes', 'catalogue&rsquo;s 2 were auto-resolved when the EXTRAs were cleared'),
 ('Confounding', 'S23', 'tv_conf_meth = a real method &rArr; base_conf_meth &ne; &ldquo;No adjustment&rdquo;', ''),
 ('Confounding', 'S24', 'tv_conf_meth = a real method &rArr; conf_var_det names a basis', 'catalogue&rsquo;s 3 auto-resolved likewise'),
]

def stats(rid):
    if rid == 'GAP':   return len(G), G.PMID.nunique(), len(G0), G0.PMID.nunique()
    if rid == 'EXTRA': return len(extras), len({x[1] for x in extras}), 0, 0
    v, v0 = list(R.get(rid, [])), list(R0.get(rid, []))
    return len(v), len(set(v)), len(v0), len(set(v0))

rows, tot_pap = '', set()
cur_fam = None
for fam, rid, rule, note in RULES:
    n, npap, n0, npap0 = stats(rid)
    if rid == 'GAP':   tot_pap |= set(G.PMID)
    elif rid == 'EXTRA': tot_pap |= {x[1] for x in extras}
    else: tot_pap |= set(R.get(rid, []))
    if fam != cur_fam:
        cur_fam = fam
        rows += '<tr class="fam"><td colspan="6">%s</td></tr>' % ('Hard skip-logic' if fam == 'HARD' else fam)
    delta = '' if n == n0 else ('<span class="up">+%d</span>' % (n - n0) if n > n0 else '<span class="dn">%d</span>' % (n - n0))
    cls = 'zero' if n == 0 else ('changed' if n != n0 else '')
    rows += ('<tr class="%s"><th scope="row"><span class="rid">%s</span></th><td class="rule">%s</td>'
             '<td class="num">%s</td><td class="num">%s</td><td class="num prev">%d / %d</td>'
             '<td class="note">%s</td></tr>') % (
        cls, rid, rule,
        ('<b>%d</b> %s' % (n, delta)) if n else '<span class="z">0</span>',
        ('<b>%d</b>' % npap) if npap else '<span class="z">0</span>', n0, npap0, note)

gap_break = ''.join('<tr><th scope="row">%s</th><td class="num"><b>%d</b></td><td class="num">%d</td></tr>'
                    % (c, int(v), G[G.child == c].PMID.nunique())
                    for c, v in G.child.value_counts().items())
nz = sum(1 for f, r, _, _ in RULES if stats(r)[0] > 0)

PAGE = '''<title>Inventory of hard and soft inconsistencies (377 dataset)</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--prob:#a6432a;--ok:#2f6b4f;
--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--prob:#a6432a;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,60px) 20px}
.wrap{max-width:1120px;margin:0 auto}
.tabtag{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line);padding:3px 9px;border-radius:5px;margin:0 0 12px}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.4vw,32px);line-height:1.14;margin:0 0 14px;max-width:30ch}
.lede{color:var(--muted);font-size:15px;max-width:78ch;margin:0 0 18px}.lede b{color:var(--ink);font-weight:600}
.cards{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 22px}
.card{border:1px solid var(--hair);border-radius:9px;padding:9px 14px;background:var(--panel);min-width:132px}
.card .n{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums}.card .l{font-size:11.5px;color:var(--muted)}
.card.hot{border-color:var(--prob)}.card.hot .n{color:var(--prob)}
.tscroll{overflow-x:auto;border:1px solid var(--hair);border-radius:11px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:900px}
thead th{position:sticky;top:0;background:var(--panel);text-align:left;font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);font-weight:600;padding:11px 12px 9px;border-bottom:2px solid var(--ink);vertical-align:bottom}
thead th.num,td.num{text-align:right}
tr.fam td{padding:14px 12px 5px;font-weight:700;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);border-bottom:1px solid var(--hair-strong)}
tbody th[scope="row"]{text-align:left;padding:8px 12px;border-top:1px solid var(--hair);white-space:nowrap;font-weight:400}
tbody td{padding:8px 12px;border-top:1px solid var(--hair);vertical-align:top}
.rid{font-weight:700;font-variant-numeric:tabular-nums;color:var(--ink)}
td.rule{color:var(--muted);min-width:330px}
td.num{font-variant-numeric:tabular-nums;white-space:nowrap}
td.prev{color:var(--faint);font-size:12px;background:var(--totbg)}
td.note{color:var(--faint);font-size:11.5px;max-width:290px}
tr.zero .rid,tr.zero td.num b{color:var(--faint)}
tr.changed td.num b{color:var(--prob)}
.up{color:var(--prob);font-weight:700;font-size:11.5px}.dn{color:var(--accent);font-weight:700;font-size:11.5px}
.z{color:var(--faint)}
tbody tr:hover td,tbody tr:hover th[scope="row"]{background:var(--row)}
h2{font-family:var(--serif);font-size:18px;margin:26px 0 10px;font-weight:600}
.small{max-width:640px}
.foot{margin-top:20px;color:var(--faint);font-size:12.5px;max-width:94ch;line-height:1.6}.foot b{color:var(--muted)}
</style>
<div class="wrap">
<span class="tabtag">Data quality</span>
<p class="eyebrow">Assessment of Healthcare Research Quality &middot; Saudi Arabia</p>
<h1>Inventory of hard and soft inconsistencies</h1>
<p class="lede">Every hard skip-logic check and all 28 soft-dependency rules, re-run on the rebuilt <b>377-paper dataset</b> (305 descriptive + causal). <b>Items</b> counts flagged cells; <b>papers</b> counts distinct PMIDs, which differ wherever one paper trips a rule more than once. The <b>329</b> column is the previous dataset, and the checker was validated by reproducing its published counts exactly (GAP&nbsp;=&nbsp;43, EXTRA&nbsp;=&nbsp;0).</p>
<div class="cards">
<div class="card hot"><div class="n">__GAP__</div><div class="l">skip-logic GAPs (was 43)</div></div>
<div class="card"><div class="n">0</div><div class="l">skip-logic EXTRAs</div></div>
<div class="card hot"><div class="n">__NZ__</div><div class="l">rules with &gt;0 violations</div></div>
<div class="card"><div class="n">__CLEAN__</div><div class="l">rules clean at zero</div></div>
<div class="card"><div class="n">__TP__</div><div class="l">distinct papers involved</div></div>
</div>
<div class="tscroll"><table>
<thead><tr><th>Rule</th><th>Condition</th><th class="num">Items</th><th class="num">Papers</th><th class="num">329: items / papers</th><th>Note</th></tr></thead>
<tbody>__ROWS__</tbody></table></div>
<h2>Skip-logic GAPs by child item</h2>
<div class="tscroll small"><table style="min-width:420px">
<thead><tr><th>Child item never answered</th><th class="num">Items</th><th class="num">Papers</th></tr></thead>
<tbody>__GAPB__</tbody></table></div>
<p class="foot"><b>Hard vs soft.</b> <i>Hard</i> checks follow the form&rsquo;s own branching: a GAP is a child the parent makes applicable but nobody answered; an EXTRA is a value surviving on a branch the parent closed. <i>Soft</i> rules are logical expectations the form never enforced, so a violation flags a contradiction to adjudicate, not necessarily an error.
<b>Counting.</b> Soft rules are evaluated per paper, so items and papers coincide; only the skip-logic GAPs can hit one paper repeatedly. S8 and S11C/S11D are converses of S1 and S10C/S10D and flag the same papers, so the distinct-paper total is well below the column sum.
<b>Reading the changes.</b> Growth from 329 to 377 is modest because the 48 added papers were adjudicated to the same standard. The four rules that moved are S6b, S22, S10C/S11C and S5 &mdash; and S5&rsquo;s apparent jump is almost entirely randomization-only trials, which Ruling&nbsp;3 makes not-applicable for <i>confounder-selection basis</i>.</p>
</div>'''
PAGE = (PAGE.replace('__ROWS__', rows).replace('__GAPB__', gap_break)
            .replace('__GAP__', str(len(G))).replace('__NZ__', str(nz))
            .replace('__CLEAN__', str(len(RULES) - nz)).replace('__TP__', str(len(tot_pap))))
open('outputs/reports/07_23_2026_inconsistency_inventory.html', 'w', encoding='utf-8').write(PAGE)
print('rules %d | with violations %d | clean %d | GAP %d | EXTRA %d | distinct papers %d'
      % (len(RULES), nz, len(RULES) - nz, len(G), len(extras), len(tot_pap)))
