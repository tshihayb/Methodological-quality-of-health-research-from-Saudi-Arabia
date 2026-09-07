# -*- coding: utf-8 -*-
"""Apply the 2026-08-25 funding rulings and write the ADJUDICATED dataset.

WHY A SEPARATE DATASET, NOT AN EDIT IN PLACE
--------------------------------------------
The classifier's output is a *machine* product and must stay reproducible: re-running
`08_23_2026_classify_funding.py` has to keep producing the same file. So the rulings live in
their own CSV and this script joins the two into a THIRD file. Nothing here writes back into
`08_23_2026_funding_classified_385.csv`, and re-running the classifier cannot silently erase
a ruling. Downstream consumers (Table 1, the stratified analysis, Figure 6) read the
adjudicated file.

THE RULES (each row of the rulings CSV names the one it was decided under)
-------------------------------------------------------------------------
  R1  The unit is research funding for THIS study. A journal's field label is not the
      author's claim; the sentence inside it is.
  R2  Publication money is not research funding. Where the only money named is tied to
      publication (APC, "funding the publication", an open-access/read-and-publish
      agreement, "the role of this funding is to publish"), the paper has said nothing about
      research funding -> not_stated. If it ALSO carries an explicit research declaration,
      that declaration governs.
  R3  Thanks without money is not funding. Thanks to a body with no money word, no named
      scheme and no grant number -> not_stated, even printed under a Funding heading.
  R4  Ethics approval is never funding.
  R5  A study-level declaration governs, UNLESS a positive statement is both (a) attached to
      THIS work -- not to a named individual, not to a different study or dataset -- and
      (b) specific: a named scheme, a grant/award number, or an explicit money verb tied to
      the work. Both conditions, not either.
  R6  Template placeholders are not declarations ("Not applicable" used identically across a
      journal's boilerplate fields) -> not_stated.
  R7  Personnel money counts when disclosed for this work and not contradicted: a named
      scholarship or fellowship paying an author, with no study-level declaration -> funded.
  R8  "Self-sponsored" and "has not declared a specific grant" are explicit negatives
      -> non_funded.

★ `apc_only` marks the rows that are `not_stated` SOLELY because the money was publication
money. R2 is the single most consequential ruling here, so it is built to be reversible:
flipping those rows back to `funded` reproduces the pre-ruling counts exactly, which is what
the sensitivity analysis needs.

Run from the repository root.
"""
import io
import os
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

CLS = 'data/analysis/08_23_2026_funding_classified_385.csv'
RUL = 'data/adjudication/08_25_2026_funding_rulings.csv'
OUT = 'data/analysis/08_25_2026_funding_ADJUDICATED_385.csv'

LEVELS = ('funded', 'non_funded', 'not_stated')
SIX = ('local', 'international', 'both', 'declared_none', 'not_stated', 'needs_review')

cl = pd.read_csv(CLS, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
ru = pd.read_csv(RUL, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')

# ---- guard rails. A ruling file is hand-written, so every assumption is checked.
assert len(cl) == 385, 'classifier file is not 385 rows'
assert ru['PMID'].is_unique, 'duplicate PMID in the rulings file'
unknown = set(ru['PMID']) - set(cl['PMID'])
assert not unknown, 'ruling for a PMID outside the 385: %s' % unknown
bad = ru[~ru['ruled_3level'].isin(LEVELS)]
assert bad.empty, 'bad ruled_3level: %s' % bad['PMID'].tolist()
bad = ru[~ru['ruled_6level'].isin(SIX)]
assert bad.empty, 'bad ruled_6level: %s' % bad['PMID'].tolist()

# the rulings file records what the machine said; if it has drifted from the live classifier
# the ruling was written against a different dataset and must not be applied blind.
chk = ru.merge(cl[['PMID', 'funding_3level']], on='PMID', how='left')
drift = chk[chk['machine_3level'] != chk['funding_3level']]
assert drift.empty, ('rulings were written against different machine labels: %s'
                     % drift[['PMID', 'machine_3level', 'funding_3level']].to_dict('records'))

d = cl.merge(ru[['PMID', 'ruled_3level', 'ruled_6level', 'rule', 'apc_only', 'reason']],
             on='PMID', how='left')
d['funding_3level_machine'] = d['funding_3level']
d['funding_6level_machine'] = d['funding_level_firstpass']
d['adjudicated'] = d['ruled_3level'].notna().astype(int)
d['changed'] = ((d['adjudicated'] == 1) & (d['ruled_3level'] != d['funding_3level'])).astype(int)
d['funding_3level'] = d['ruled_3level'].fillna(d['funding_3level'])
d['funding_level_firstpass'] = d['ruled_6level'].fillna(d['funding_level_firstpass'])
d['adjudication_rule'] = d['rule'].fillna('')
d['adjudication_reason'] = d['reason'].fillna('')
d['apc_only'] = pd.to_numeric(d['apc_only'], errors='coerce').fillna(0).astype(int)
d = d.drop(columns=['ruled_3level', 'ruled_6level', 'rule', 'reason'])

before = cl['funding_3level'].value_counts()
after = d['funding_3level'].value_counts()

print('=' * 92)
print('FUNDING RULINGS APPLIED  (2026-08-25)')
print('=' * 92)
print('rulings recorded : %d   (of which change the label: %d; confirmations: %d)'
      % (len(ru), int(d['changed'].sum()), len(ru) - int(d['changed'].sum())))
print('\n%-12s %10s %10s %8s' % ('category', 'machine', 'adjudicated', 'delta'))
for k in LEVELS:
    b, a = int(before.get(k, 0)), int(after.get(k, 0))
    print('%-12s %10s %10s %+8d   (%.1f%% -> %.1f%%)'
          % (k, b, a, a - b, 100.0 * b / 385, 100.0 * a / 385))
assert int(after.sum()) == 385 and set(after.index) <= set(LEVELS)

print('\nby rule:')
print(d[d['adjudicated'] == 1]['adjudication_rule'].value_counts().to_string())

print('\nmoves:')
mv = d[d['changed'] == 1]
print(pd.crosstab(mv['funding_3level_machine'], mv['funding_3level']).to_string())

# ---- R2 sensitivity: the one ruling that could reasonably go the other way
apc = d[d['apc_only'] == 1]
alt = d['funding_3level'].copy()
alt[d['apc_only'] == 1] = 'funded'
print('\n★ R2 sensitivity — if publication money DID count as research funding')
print('   %d papers are not_stated on R2 alone (%s)' % (len(apc), ' '.join(apc['PMID'])))
print('   funded %d -> %d (%.1f%% -> %.1f%%)   not_stated %d -> %d (%.1f%% -> %.1f%%)'
      % (int(after.get('funded', 0)), int((alt == 'funded').sum()),
         100.0 * int(after.get('funded', 0)) / 385, 100.0 * int((alt == 'funded').sum()) / 385,
         int(after.get('not_stated', 0)), int((alt == 'not_stated').sum()),
         100.0 * int(after.get('not_stated', 0)) / 385,
         100.0 * int((alt == 'not_stated').sum()) / 385))

d.to_csv(OUT, index=False, encoding='utf-8-sig')
print('\nwrote %s' % OUT)
print('⚠ %s is UNTOUCHED and still reproduces from the classifier.' % CLS)
