# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Patch the Saudi-share stratifiers for PMID STUDY-0928 in the canonical wide dataset.

Why: validating S1/S2 against the full texts showed PubMed and the published paper
disagree about author 4 (Syed Muhammad Azfar).

    PubMed          Orthopedic Surgery Department, Jeddah National Hospital, Jeddah, Saudi Arabia
    the paper       Department of Orthopedic, Liaquat College of Medicine and Dentistry, Karachi, Pakistan
                    (JPMA 72:2223, DOI [DOI-REDACTED] -- PDF verified as the right paper)

TSA ruled 2026-08-23 that the PAPER wins. `country_matcher.MANUAL_AUTHOR_COUNTRY` was
updated and the author-country / Saudi-institution maps rebuilt, which drops the paper
from 2 Saudi authors to 1. The wide analysis dataset is built from a different source
with per-PMID overrides, so it does not pick that up automatically.

Only this one paper and only the pct_saudi columns change. first/last/corresponding
author flags are 0 either way. Verified before/after and logged.

Run from the repository root.
"""
import shutil, sys
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WIDE = 'data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv'
PMID = STUDY-0928
NEW = {'n_saudi_authors': 1, 'pct_saudi_authors': round(100 * 1 / 6, 1),
       'pct_saudi_ge50': '<50%', 'pct_saudi_cat3': '<33%', 'pct_saudi_cat4': '<25%'}

W = pd.read_csv(WIDE, encoding='utf-8-sig')
m = W.PMID == PMID
if not m.any():
    sys.exit('PMID %d not in %s' % (PMID, WIDE))

cols = list(NEW) + ['n_authors', 'first_author_saudi', 'last_author_saudi',
                    'corresponding_author_saudi', 'pct_saudi_reliable']
print('BEFORE:')
print(W.loc[m, ['PMID'] + cols].to_string(index=False))

# cross-check against the rebuilt author-level file before touching anything
L = pd.read_csv('data/authors/07_25_2026_author_country_long.csv', encoding='utf-8-sig')
g = L[L.PMID == PMID]
n_auth = len(g)
n_saudi = int(g.all_countries.astype(str).str.contains('Saudi Arabia').sum())
print('\nauthor-level file now says: n_authors=%d  n_saudi=%d' % (n_auth, n_saudi))
if (n_auth, n_saudi) != (6, 1):
    sys.exit('ABORT: author-level file does not match the expected 6/1 -- rerun the maps first.')

shutil.copy2(WIDE, WIDE.replace('.csv', '_prepatch_08_23_2026.csv'))
for k, v in NEW.items():
    W.loc[m, k] = v
W.to_csv(WIDE, index=False, encoding='utf-8-sig')

print('\nAFTER:')
print(pd.read_csv(WIDE, encoding='utf-8-sig').loc[m, ['PMID'] + cols].to_string(index=False))
print('\nbackup written:', WIDE.replace('.csv', '_prepatch_08_23_2026.csv'))
