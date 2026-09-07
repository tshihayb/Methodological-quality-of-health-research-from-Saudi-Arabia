# NOTE (public repository): 12 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Patch the Saudi authorship stratifiers for the 14 papers where the analysis dataset
disagrees with S1. TSA adjudicated 2026-08-24: take the correct value from each -- which on
all 14 is S1's.

WHY THEY DISAGREED
------------------
`08_12_2026_ANALYSIS_DATASET_wide_385.csv` takes these columns from
`data/authors/07_16_2026_saudi_affiliation_variables.xlsx` -- a 2026-07-16 build on the older
`pubmed_authors_cache.json` -- and does NOT recompute from the author files. S1 was rebuilt
on 07-25 and corrected ten times on 08-24. Three mechanisms produced the 14 disagreements:

  1. STALE CORRECTION   STUDY-0531 -- S1 carries the documented KFSHRC fix (all 3 authors
                        Saudi); the dataset predates it and still says 1.
  2. COLLECTIVE AUTHOR  the 07-16 build counted a group entry ("European Study Group ...")
                        as a real author. The project convention excludes those.
  3. SAUDI OVER-COUNT   the older Saudi matcher flagged authors the current one does not.

EVIDENCE. The 385-paper hand-read -- independent of PubMed -- confirms S1 on 13 of 14, and
matches S1's AUTHOR COUNT on all 14. The 14th (STUDY-0468) is the Fanikos paper, where the
hand-read agrees with the dataset only because reader and PubMed both descend from the byline
that mis-marks him; TSA's external-evidence precedence ruling puts S1's 3 above both.
TSA manually verified STUDY-0531, STUDY-0737 and STUDY-0350 -- one instance of each mechanism.

Patches ONLY the analysis dataset. Regenerates nothing.
Run from the repository root.
"""
import io
import shutil
import sys

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ⚠ TWO wide datasets carry these columns and BOTH must be patched.
#   08_12_..._385.csv is the current analysis dataset (scoring, stratified analysis).
#   07_23_..._wide.csv is what code/tables/_gen_table1.py actually reads -- so patching only
#   the 08-12 file leaves TABLE 1 UNCHANGED. That was nearly missed: the two were identical
#   on these columns except for the earlier STUDY-0928 patch, which had reached only 08-12.
WIDES = ['data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv',
         'data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv']
S1F = 'data/authors/07_25_2026_author_country_long.csv'
GOLD = 'data/authors/07_16_2026_saudi_affiliation_variables.xlsx'
DIFF = 'data/quality-control/08_23_2026_wide_vs_author_files_diff.csv'


def cat4(p):
    return '<25%' if p < 25 else ('25-50%' if p <= 50 else ('>50-75%' if p <= 75 else '>75%'))


def cat3(p):
    # Tertiles INCLUSIVE at the exact thirds: verified to reproduce the dataset's own
    # categories from its own pct on all 385 rows (0 mismatches). A naive p<33 / p<=67
    # rule misplaces the 33.3% and 66.7% papers and fabricates a 25-paper shift.
    return '<33%' if p <= 33.34 else ('>67%' if p >= 66.66 else '33-67%')


def patch(WIDE):
    BACKUP = WIDE.replace('data/analysis/', 'data/analysis/_pre_stratifier_patch_')
    s1 = pd.read_csv(S1F, encoding='utf-8-sig')
    s1['sa'] = s1.all_countries.fillna('').str.contains('Saudi Arabia')
    w = pd.read_csv(WIDE, encoding='utf-8-sig', low_memory=False)
    targets = sorted(w.PMID.astype(int).tolist())
    gold = pd.read_excel(GOLD)
    gold['PMID'] = gold.PMID.astype(int)

    shutil.copy(WIDE, BACKUP)
    print(f'backup -> {BACKUP}\npatching {len(targets)} papers\n')

    changes = []
    for p in targets:
        g = s1[s1.PMID == p]
        if g.empty:
            print(f'  !! {p} absent from S1 -- skipped')
            continue
        n, ns = len(g), int(g.sa.sum())
        pct = round(100 * ns / n, 1)
        new = {'n_authors': n, 'n_saudi_authors': ns, 'pct_saudi_authors': pct,
               'pct_saudi_ge50': '>=50%' if pct >= 50 else '<50%',
               'pct_saudi_cat3': cat3(pct), 'pct_saudi_cat4': cat4(pct),
               'first_author_saudi': int(bool(g[g.is_first].sa.any())),
               'last_author_saudi': int(bool(g[g.is_last].sa.any()))}

        # ⚠⚠ DO NOT DERIVE corresponding_author_saudi FROM S1 BY SURNAME.
        # An earlier version of this script did, and CORRUPTED 7 papers:
        #   * STUDY-0402, STUDY-0728, STUDY-0936, STUDY-0125, STUDY-0053 -- CO-CORRESPONDING papers.
        #     The convention is "Saudi-corresponding if ANY corresponding author is Saudi";
        #     the gold file stores only ONE corr_author name, so a single-name lookup misses
        #     the second, Saudi one and wrongly flips 1 -> 0.
        #   * STUDY-0700, STUDY-0199 -- SHARED SURNAME. Two authors called Mohamed / Louati, one
        #     Saudi and one not. `.any()` over the surname match wrongly flips 0 -> 1;
        #     STUDY-0700's corresponding author is fixed by the email (@med.tanta.eg, Egypt).
        # The column was independently verified on 2026-08-24: 326 unambiguous
        # single-corresponding papers, 0 disagreements with S1. It does not need patching.
        # Only this one paper was adjudicated as needing a change, so only it is applied.
        if p == STUDY-0531:
            new['corresponding_author_saudi'] = 1   # Bohlega (KFSHRC) is Saudi

        i = w.index[w.PMID == p][0]
        for col, v in new.items():
            if col not in w.columns:
                continue
            old = w.at[i, col]
            if str(old) != str(v):
                changes.append((p, col, old, v))
                w.at[i, col] = v

    w.to_csv(WIDE, index=False, encoding='utf-8-sig')
    print(f'{len(changes)} cell(s) changed across {len({c[0] for c in changes})} papers\n')
    cur = None
    for p, col, old, v in changes:
        if p != cur:
            print(f'  {p}')
            cur = p
        print(f'      {col:<28} {old!r:>10}  ->  {v!r}')

    # ---- verification: the patched file must now agree with S1 everywhere ----
    w2 = pd.read_csv(WIDE, encoding='utf-8-sig', low_memory=False)
    rec = s1.groupby('PMID').agg(n=('sa', 'size'), ns=('sa', 'sum')).reset_index()
    rec = (rec.merge(s1[s1.is_first].groupby('PMID').sa.any().rename('fs'), on='PMID')
              .merge(s1[s1.is_last].groupby('PMID').sa.any().rename('ls'), on='PMID'))
    m = rec.merge(w2[['PMID', 'n_authors', 'n_saudi_authors',
                      'first_author_saudi', 'last_author_saudi']], on='PMID')
    bad = m[(m.n != m.n_authors) | (m.ns != m.n_saudi_authors)
            | (m.fs.astype(int) != m.first_author_saudi)
            | (m.ls.astype(int) != m.last_author_saudi)]
    print(f'\nVERIFY: papers still disagreeing with S1: {len(bad)}')
    if len(bad):
        print(bad.to_string(index=False))
    print('\nTable 1 marginals after the patch:')
    for c in ['first_author_saudi', 'last_author_saudi']:
        print(f'  {c:<26} {int((w2[c] == 1).sum())} Saudi')
    for c in ['pct_saudi_ge50', 'pct_saudi_cat3', 'pct_saudi_cat4']:
        print(f'  {c:<26} {w2[c].value_counts().to_dict()}')


if __name__ == '__main__':
    for f in WIDES:
        patch(f)
