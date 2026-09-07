# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Reconcile the Saudi-authorship stratifiers in the wide analysis dataset against the
author-country file they are supposed to describe.

WHY: the wide builder takes `n_saudi_authors` / `pct_saudi_*` / `first_` / `last_` /
`corresponding_author_saudi` from a separate source with PER-PMID OVERRIDES. It does NOT
recompute them from data/authors/07_25_2026_author_country_long.csv. So every correction
made to the author file since the wide dataset was built is invisible there unless someone
patched it explicitly -- STUDY-0928 was patched on 2026-08-23, and the hand-read pilot then
found STUDY-0531 still carrying its pre-correction values.

This asks the question in general: for how many of the 385 papers do the two disagree, and
on what? It reads only; it changes nothing.

Run from the repository root.
"""
import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

S1 = 'data/authors/07_25_2026_author_country_long.csv'
WIDE = 'data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv'
OUT = 'data/quality-control/08_23_2026_wide_vs_author_files_diff.csv'


def main():
    s1 = pd.read_csv(S1, encoding='utf-8-sig')
    # ⚠ all_countries is "; "-separated, NOT "|"-separated.
    s1['is_saudi'] = s1.all_countries.fillna('').str.contains('Saudi Arabia')

    g = s1.groupby('PMID')
    rec = pd.DataFrame({
        'n_authors_s1': g.size(),
        'n_saudi_s1': g.is_saudi.sum(),
        # is_first / is_last are the author file's own flags -- safer than min/max of
        # author_index, which collective-author entries would shift.
        'first_saudi_s1': g.apply(lambda d: bool(d.loc[d.is_first.astype(bool), 'is_saudi'].any()),
                                  include_groups=False),
        'last_saudi_s1': g.apply(lambda d: bool(d.loc[d.is_last.astype(bool), 'is_saudi'].any()),
                                 include_groups=False),
    }).reset_index()
    rec['pct_saudi_s1'] = (100 * rec.n_saudi_s1 / rec.n_authors_s1).round(1)

    w = pd.read_csv(WIDE, encoding='utf-8-sig', low_memory=False)
    keep = ['PMID', 'n_authors', 'n_saudi_authors', 'pct_saudi_authors',
            'first_author_saudi', 'last_author_saudi', 'pct_saudi_ge50',
            'pct_saudi_cat3', 'pct_saudi_cat4']
    d = rec.merge(w[keep], on='PMID', how='outer', indicator=True)
    if (d._merge != 'both').any():
        print('⚠ PMIDs not in both files:')
        print(d[d._merge != 'both'][['PMID', '_merge']].to_string(index=False))
    d = d[d._merge == 'both'].drop(columns='_merge')

    d['d_nauth'] = d.n_authors_s1 != d.n_authors
    d['d_nsaudi'] = d.n_saudi_s1 != d.n_saudi_authors
    d['d_first'] = d.first_saudi_s1.astype(int) != d.first_author_saudi
    d['d_last'] = d.last_saudi_s1.astype(int) != d.last_author_saudi
    d['d_ge50'] = (d.pct_saudi_s1 >= 50) != (d.pct_saudi_ge50 == '>=50%')
    dcols = ['d_nauth', 'd_nsaudi', 'd_first', 'd_last', 'd_ge50']
    d['any_diff'] = d[dcols].any(axis=1)

    print(f'papers compared: {len(d)}')
    for c, lab in zip(dcols, ['author count', 'n_saudi_authors', 'first_author_saudi',
                              'last_author_saudi', 'pct_saudi_ge50']):
        print(f'  {lab:<22}: {int(d[c].sum())} disagree')
    print(f'  {"ANY":<22}: {int(d.any_diff.sum())} papers')

    bad = d[d.any_diff]
    bad.to_csv(OUT, index=False, encoding='utf-8-sig')
    if len(bad):
        print(f'\n{len(bad)} disagreeing paper(s) -> {OUT}\n')
        show = ['PMID', 'n_authors_s1', 'n_authors', 'n_saudi_s1', 'n_saudi_authors',
                'pct_saudi_s1', 'pct_saudi_authors', 'first_saudi_s1', 'first_author_saudi',
                'last_saudi_s1', 'last_author_saudi', 'pct_saudi_ge50']
        pd.set_option('display.width', 250)
        print(bad[show].to_string(index=False))
    else:
        print('\n✅ the wide stratifiers match the author-country file for every paper')


if __name__ == '__main__':
    main()
