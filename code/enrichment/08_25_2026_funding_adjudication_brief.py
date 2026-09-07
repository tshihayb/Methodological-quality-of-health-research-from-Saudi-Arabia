# -*- coding: utf-8 -*-
"""Turn the hand-read worklist into a document TSA can actually rule on.

The worklist CSV is the record; it is not a decision aid. Most of its rows are flags that
change nothing, and the rows that DO change something mostly fall into a handful of
recurring situations rather than being 28 separate judgement calls. This script groups the
live decisions by (machine label -> reader call) x dominant flag, prints both sides'
verbatim evidence under each group, and states what each grouped ruling would do to the
headline percentages.

⚠ Every count printed here is CONDITIONAL — nothing has been written back to the funding
datasets. `funded` is reported as a RANGE across the undecided rulings, the same convention
the institution-choice sensitivity used for Table 1.

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

HR = 'data/quality-control/08_25_2026_funding_handread'
MERGED = HR + '/08_25_2026_funding_handread_merged.csv'
OUT = HR + '/08_25_2026_FUNDING_ADJUDICATION_BRIEF.md'


def cut(s, n):
    s = ' '.join(str(s or '').split())
    return s if len(s) <= n else s[:n - 1] + '…'


ADJ = 'data/quality-control/08_25_2026_funding_adjudication_items.csv'
WL = 'data/analysis/08_23_2026_funding_review_worklist.csv'

d = pd.read_csv(MERGED, encoding='utf-8-sig', dtype=str).fillna('')
d['agree'] = (d['hr_call'] == d['funding_3level']).astype(int)
d.loc[d['hr_call'] == 'unclear', 'agree'] = 0

# `already_queued` lives on the worklist, not the merged file -- recompute from the two
# sources so this brief does not depend on the order the two scripts are run in.
known = set()
for path in (ADJ, WL):
    if os.path.exists(path):
        known |= set(pd.read_csv(path, dtype=str, encoding='utf-8-sig')['PMID'].str.strip())
d['already_queued'] = d['PMID'].isin(known).astype(int).astype(str)

live = d[d['agree'] == 0].copy()
live['dominant_flag'] = live['hr_flags'].str.split(';').str[0].replace('', '(no flag)')
live['transition'] = live['funding_3level'] + ' → ' + live['hr_call']

L = []
A = L.append
A('# Funding hand-read — decisions owed (2026-08-25)\n')
A('Blind hand-read of all %d papers by 39 independent readers. Nothing below has been '
  'written into the funding datasets.\n' % len(d))

n_ag = int(d['agree'].sum())
A('## Headline\n')
A('- agreement with the machine: **%d / %d (%.1f%%)**' % (n_ag, len(d), 100.0 * n_ag / len(d)))
A('- live decisions (disagreement or `unclear`): **%d**' % len(live))
A('- machine confidence on those: %s'
  % ', '.join('%s %d' % (k, v) for k, v in live['confidence'].value_counts().items()))
A('- already queued by the machine (7 adjudication items / 49-row worklist): **%d**; '
  'newly found: **%d**\n'
  % (int(live['already_queued'].astype(int).sum()),
     len(live) - int(live['already_queued'].astype(int).sum())))

A('### Current machine counts, and the range once these are ruled\n')
cur = d['funding_3level'].value_counts()
A('| category | machine now | if every reader call is accepted |')
A('|---|---|---|')
prop = d['hr_call'].replace('unclear', '').value_counts()
for k in ('funded', 'non_funded', 'not_stated'):
    lo = int(prop.get(k, 0))
    A('| %s | %d (%.1f%%) | %d + up to %d unclear |'
      % (k, int(cur.get(k, 0)), 100.0 * int(cur.get(k, 0)) / len(d), lo,
         int((d['hr_call'] == 'unclear').sum())))
A('')
A('The `unclear` papers are unallocated by design — each is a genuine contradiction inside '
  'the paper, not a reader failure.\n')

A('## Decisions, grouped by the situation that recurs\n')
groups = (live.groupby(['transition', 'dominant_flag'])
          .size().sort_values(ascending=False))
for (trans, flag), n in groups.items():
    sub = live[(live['transition'] == trans) & (live['dominant_flag'] == flag)]
    A('---\n')
    A('### %s — %s  (%d paper%s)\n' % (trans, flag, n, '' if n == 1 else 's'))
    for _, r in sub.iterrows():
        A('**%s** · machine conf `%s`%s'
          % (r['PMID'], r['confidence'],
             ' · *already queued*' if r['already_queued'] == '1' else ''))
        A('- paper says: %s' % cut(r['hr_verbatim'], 420))
        if r['hr_heading']:
            A('- under heading: `%s`' % cut(r['hr_heading'], 60))
        if r['hr_note']:
            A('- reader: %s' % cut(r['hr_note'], 300))
        if r['funding_statement_verbatim']:
            A('- machine held: %s' % cut(r['funding_statement_verbatim'], 260))
        A('')

A('---\n')
A('## Flags that change no call (confirmations, no ruling needed)\n')
conf = d[(d['agree'] == 1) & (d['hr_flags'] != '')]
tally = {}
for s in conf['hr_flags']:
    for f in s.split(';'):
        tally[f] = tally.get(f, 0) + 1
A('%d papers where the reader saw a trap, flagged it, and still reached the machine\'s '
  'label:\n' % len(conf))
for k, v in sorted(tally.items(), key=lambda x: -x[1]):
    A('- `%s` — %d' % (k, v))
A('')

with io.open(OUT, 'w', encoding='utf-8') as f:
    f.write('\n'.join(L))
print('\n'.join(L[:40]))
print('\n...\nwrote %s (%d lines)' % (OUT, len(L)))
