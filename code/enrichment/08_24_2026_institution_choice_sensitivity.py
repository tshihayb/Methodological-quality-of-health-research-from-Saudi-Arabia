# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""How much of S2 -- and of Table 1's sector rows -- rests on WHICH named institution is
picked when an author's affiliation names several?

The question STUDY-0852 raised. That paper's five Saudi authors share
    "...College of Medicine, King Saud Bin Abdul Aziz University for Health Sciences
     (KSAU-HS), King Abdulaziz Medical City, Jeddah, Saudi Arabia. |
     King Abdullah International Medical Research Centre (KAIMRC), National Guard Health
     Affairs (NGHA), Jeddah, Saudi Arabia."
and S2 records King Abdulaziz Medical City for all five, because classify() takes the
RIGHTMOST Tier-1 alias in the FIRST Saudi block. That single choice decides the paper's
sector, and therefore whether Table 1 counts it Health-system or Academic-only.

Two selection rules are in play and neither is announced anywhere in the outputs:
  1. FIRST SAUDI BLOCK   -- when the author has several affiliation blocks, S2 uses the
     first one that resolves to Saudi Arabia (07_25_2026_map_saudi_institutions.first_saudi_block)
  2. RIGHTMOST ALIAS     -- within that block, the alias closest to the city wins, on the
     assumption that the top-level employer is printed last
     (saudi_institution_classifier._rightmost)

This script measures how often each rule is load-bearing, whether the alternatives differ in
SECTOR (the part that reaches Table 1), and what Table 1's two sector rows would read under
three defensible rules:

  A  first block, rightmost alias      -- what S2 does today
  B  first block, leftmost alias       -- "the employing unit is named first"
  C  union of every named institution  -- authors genuinely hold all of them (the standing
                                          National Guard ruling); one institution per author
                                          for Fig. S2, but the PAPER-level sector set is a
                                          union, which is what sectors_present asks for

Writes candidates only. Run from the repository root.
"""
import io
import json
import os
import re
import sys
from collections import Counter

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join('code', 'lib'))
sys.path.insert(0, os.path.join('code', 'enrichment'))

from country_matcher import detect_country_segment            # noqa: E402
import saudi_institution_classifier as SIC                    # noqa: E402
_sw = __import__('08_24_2026_sweep_s2_institution_anomalies')
alias_hits, _s = _sw.alias_hits, _sw._s

S2 = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
CACHE = 'data/authors/07_25_2026_authors_cache_385.json'
PAPER = 'data/authors/07_25_2026_saudi_paper_level.csv'
OUT = 'data/quality-control/08_24_2026_institution_choice_sensitivity.csv'

# Table 1's own definition -- code/tables/_gen_table1.py line 31
HEALTH = {'Hospital / medical city', 'Hospital & research centre', 'Ministry of Health',
          'Military & security-forces medical'}
GENERIC = {'General government / ministry'}


def candidates(text):
    """[(pos, type, canon)] for every curated institution named in `text`, left to right,
    each canon kept once at its leftmost position."""
    seen, out = {}, []
    for start, _end, typ, canon in sorted(alias_hits(text)):
        if canon in GENERIC or canon in seen:
            continue
        seen[canon] = start
        out.append((start, typ, canon))
    return out


def main():
    s2 = pd.read_csv(S2, encoding='utf-8-sig')
    cache = json.load(open(CACHE, 'r', encoding='utf-8'))
    reals = {str(p): [a for a in au if a.get('last', '').strip()] for p, au in cache.items()}

    rows = []
    for r in s2.itertuples():
        auth = reals[str(r.PMID)]
        aff = auth[r.author_index - 1].get('aff') or '' if r.author_index - 1 < len(auth) else ''
        blocks = [b for b in re.split(r'\s*[|;]\s*', aff)
                  if detect_country_segment(b)[0] == 'Saudi Arabia']
        chosen_block = _s(r.saudi_block)
        in_block = candidates(chosen_block)
        all_saudi = candidates(' | '.join(blocks)) or in_block

        # which rule decided this row?
        rules = []
        if len(in_block) > 1:
            rules.append('rightmost-in-block')
        if len(blocks) > 1 and {c for _, _, c in all_saudi} != {c for _, _, c in in_block}:
            rules.append('first-block')
        decided = '+'.join(rules) if rules else 'single'

        alt_a = r.institution
        alt_b = in_block[0][2] if in_block else r.institution           # leftmost named
        # C = every institution there is EVIDENCE for, which must include the one S2 recorded.
        # Unioning only what the affiliation string names is not enough: STUDY-0161 Almwled's
        # institution comes from the paper's CORRESPONDENCE block (King Abdullah Medical City),
        # and her affiliation text names only King Saud University -- so a names-only union
        # would silently REMOVE her Hospital sector and C would stop being a bound. The
        # A-subset-of-C invariant below is what caught that.
        types_all = {t for _, t, _ in all_saudi} | {r.inst_type}
        rows.append(dict(
            PMID=r.PMID, author_index=r.author_index, last=r.last,
            decided_by=decided,
            n_named_in_block=len(in_block), n_named_total=len(all_saudi),
            rule_A=alt_a, rule_A_type=r.inst_type,
            rule_B=alt_b, rule_B_type=next((t for _, t, c in in_block if c == alt_b),
                                           r.inst_type),
            all_named='; '.join(c for _, _, c in all_saudi),
            all_types='; '.join(sorted(types_all)),
            type_ambiguous=len(types_all) > 1))
    D = pd.DataFrame(rows)
    D['A_vs_B_differs'] = D.rule_A != D.rule_B
    D['A_vs_B_type_differs'] = D.rule_A_type != D.rule_B_type
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    D.to_csv(OUT, index=False, encoding='utf-8-sig')

    N = len(D)
    print('=' * 92)
    print('WHICH RULE DECIDED EACH S2 ROW')
    print('=' * 92)
    print(D.decided_by.value_counts().to_string())
    amb = D[D.decided_by != 'single']
    print(f'\nrows where a selection rule was load-bearing : {len(amb)} / {N} '
          f'({len(amb)/N*100:.1f}%)  over {amb.PMID.nunique()} papers')
    print(f'  ...of those, the alternatives differ in SECTOR: {int(amb.type_ambiguous.sum())} '
          f'rows over {amb[amb.type_ambiguous].PMID.nunique()} papers')
    print(f'  rightmost vs leftmost picks a different institution: '
          f'{int(D.A_vs_B_differs.sum())} rows;  different SECTOR: '
          f'{int(D.A_vs_B_type_differs.sum())} rows')

    # ---------------- paper-level sector sets under the three rules ----------------
    pub = pd.read_csv(PAPER, encoding='utf-8-sig')
    pub_sets = {int(p): {t.strip() for t in str(s).split(';')}
                for p, s in zip(pub.PMID, pub.sectors_present)}

    def marginals(sets_by_paper, label):
        hs = sum(1 for s in sets_by_paper.values() if s & HEALTH)
        ms = sum(1 for s in sets_by_paper.values() if len(s) > 1)
        print(f'  {label:<44} Health-system {hs:>3} / Academic-only {len(sets_by_paper)-hs:>3}'
              f'   |  Multi {ms:>3} / Single {len(sets_by_paper)-ms:>3}')
        return hs, ms

    # A: the sector of the ONE institution S2 kept, unioned over the paper's Saudi authors.
    # C: the sectors of EVERY curated institution those authors name.
    #
    # The fallback matters and is the whole reason two earlier passes disagreed by one paper.
    # When an author's Saudi text names no curated institution at all (tier-3 rows, the two
    # manual-context rows with an empty block, "private practice"), C has nothing to union --
    # and the answer is NOT "Other/unspecified", it is the sector S2 recorded. `types_all`
    # above already falls back that way, which is what makes C a strict superset of A.
    setsA = {p: set(g.rule_A_type) for p, g in D.groupby('PMID')}
    setsB = {p: set(g.rule_B_type) for p, g in D.groupby('PMID')}
    setsC = {p: {t for ts in g.all_types for t in ts.split('; ')} for p, g in D.groupby('PMID')}
    bad = [p for p in setsA if not setsA[p] <= setsC[p]]
    print(f'\n  INVARIANT  A subset of C on all 385 papers: {not bad}'
          + (f'  VIOLATIONS: {bad}' if bad else ''))

    print('\n' + '=' * 92)
    print('TABLE 1 SECTOR ROWS UNDER EACH RULE   (385 papers)')
    print('=' * 92)
    marginals(pub_sets, 'published (saudi_paper_level.csv)')
    a = marginals(setsA, 'A  first block, rightmost alias  [current]')
    b = marginals(setsB, 'B  first block, leftmost alias')
    c = marginals(setsC, 'C  union of every named institution')

    print('\n  reproduces the published file:', setsA == pub_sets)
    flipA_B = [p for p in setsA if bool(setsA[p] & HEALTH) != bool(setsB[p] & HEALTH)]
    flipA_C = [p for p in setsA if bool(setsA[p] & HEALTH) != bool(setsC[p] & HEALTH)]
    msA_C = [p for p in setsA if (len(setsA[p]) > 1) != (len(setsC[p]) > 1)]
    # ---- the two bounds, per paper, for the record ----
    hs_move = sorted(p for p in setsA if not (setsA[p] & HEALTH) and (setsC[p] & HEALTH))
    ms_move = sorted(p for p in setsA if len(setsA[p]) == 1 and len(setsC[p]) > 1)
    pd.DataFrame([{'PMID': p,
                   'sectors_A': '; '.join(sorted(setsA[p])),
                   'sectors_C': '; '.join(sorted(setsC[p])),
                   'comp_A': 'Health-system' if setsA[p] & HEALTH else 'Academic-only',
                   'comp_C': 'Health-system' if setsC[p] & HEALTH else 'Academic-only',
                   'msec_A': 'Multi-sector' if len(setsA[p]) > 1 else 'Single-sector',
                   'msec_C': 'Multi-sector' if len(setsC[p]) > 1 else 'Single-sector'}
                  for p in sorted(setsA)]).to_csv(
        'data/quality-control/08_24_2026_sector_bounds_by_paper.csv',
        index=False, encoding='utf-8-sig')
    print(f'\n  Academic-only -> Health-system under C: {len(hs_move)} papers {hs_move}')
    print(f'  Single-sector -> Multi-sector under C: {len(ms_move)} papers {ms_move}')

    print(f'\n  papers flipping Health-system A->B: {len(flipA_B)} {sorted(flipA_B)}')
    print(f'  papers flipping Health-system A->C: {len(flipA_C)} {sorted(flipA_C)}')
    print(f'  papers flipping Single->Multi  A->C: {len(msA_C)}')

    print('\n' + '=' * 92)
    print('THE SINGLE-SECTOR PAPERS WHOSE LABEL RESTS ON ONE PICK')
    print('=' * 92)
    risky = []
    for p, g in D.groupby('PMID'):
        if len(setsA[p]) != 1:
            continue
        if not g.type_ambiguous.any():
            continue
        risky.append((p, sorted(setsA[p])[0], sorted(setsC[p]),
                      'Health-system' if setsA[p] & HEALTH else 'Academic-only',
                      'Health-system' if setsC[p] & HEALTH else 'Academic-only'))
    print(f'{len(risky)} single-sector papers where the authors name >1 sector:')
    for p, a1, c1, la, lc in risky:
        mark = '  <-- LABEL CHANGES' if la != lc else ''
        print(f'  {p}: recorded [{a1}] -> all named {c1}   {la} / {lc}{mark}')
    print(f'\n-> {OUT}')


if __name__ == '__main__':
    main()
