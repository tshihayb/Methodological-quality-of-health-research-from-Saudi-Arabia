# -*- coding: utf-8 -*-
"""Prove the funding packets are readable BEFORE handing 385 of them to readers.

A packet that does not physically contain the funding sentence cannot be read correctly,
and the failure is silent: the reader records `not_stated`, which is exactly the label
this whole exercise exists to test. So every packet is checked for containment of the
evidence the pipeline already found -- statements, explicit negatives, and named
acknowledgement text -- before a single agent is spawned.

Run from the repository root.
"""
import io
import os
import re
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PACK = 'data/quality-control/08_25_2026_funding_packets'
STMT = 'data/analysis/08_23_2026_funding_statements_385.csv'
CLS = 'data/analysis/08_23_2026_funding_classified_385.csv'
OUT = 'data/quality-control/08_25_2026_funding_packet_check.csv'


def norm(s):
    """Compare on letters and digits only: the packet re-renders the PDF page by page,
    so whitespace, ligatures and hyphenation differ from the extractor's stored string."""
    s = (str(s).replace('ﬀ', 'ff').replace('ﬁ', 'fi').replace('ﬂ', 'fl')
         .replace('ﬃ', 'ffi').replace('ﬄ', 'ffl').replace('­', ''))
    return re.sub(r'[^a-z0-9]', '', s.lower())


def probe(hay, needle, n=60):
    """Is a distinctive n-character run of `needle` present? Full-string equality fails on
    a statement stitched across a column break; a 60-char run is specific enough that a
    false pass is not credible, and short enough to survive one layout seam."""
    h, x = norm(hay), norm(needle)
    if not x:
        return None
    if len(x) <= n:
        return x in h
    # try the first, middle and last window -- one of them must survive
    wins = [x[:n], x[len(x) // 2: len(x) // 2 + n], x[-n:]]
    return any(w in h for w in wins)


st = pd.read_csv(STMT, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
cl = pd.read_csv(CLS, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
d = st.merge(cl[['PMID', 'funding_3level', 'funding_level_firstpass', 'confidence']],
             on='PMID', how='left')

rows = []
missing_packet = 0
for _, r in d.iterrows():
    pmid = r['PMID']
    p = os.path.join(PACK, pmid + '.txt')
    if not os.path.exists(p):
        missing_packet += 1
        rows.append({'PMID': pmid, 'screen': 'P0_no_packet', 'detail': ''})
        continue
    pk = io.open(p, encoding='utf-8', errors='replace').read()

    stmt = r['funding_statement_verbatim']
    if stmt.strip() and probe(pk, stmt) is False:
        rows.append({'PMID': pmid, 'screen': 'P1_statement_not_in_packet',
                     'label': r['funding_3level'], 'detail': stmt[:220]})

    neg = r['explicit_no_funding_hit'].split(' | ')[0] if r['explicit_no_funding_hit'] else ''
    if neg.strip() and probe(pk, neg, n=40) is False:
        rows.append({'PMID': pmid, 'screen': 'P2_negative_not_in_packet',
                     'label': r['funding_3level'], 'detail': neg[:220]})

    ack = r['sec_acknowledgements']
    if ack.strip() and len(ack) > 40 and probe(pk, ack, n=50) is False:
        rows.append({'PMID': pmid, 'screen': 'P3_ack_not_in_packet',
                     'label': r['funding_3level'], 'detail': ack[:220]})

    # A packet with no money-word sweep AND no labelled section gives the reader nothing
    # to weigh. That is a legitimate finding (a genuinely silent paper) but it must be
    # counted, not discovered one paper at a time by 39 agents.
    if '*** NO MONEY WORD ANYWHERE IN THIS PAPER ***' in pk:
        rows.append({'PMID': pmid, 'screen': 'P4_no_money_word_at_all',
                     'label': r['funding_3level'], 'detail': ''})

    if len(pk) < 2500:
        rows.append({'PMID': pmid, 'screen': 'P5_packet_suspiciously_short',
                     'label': r['funding_3level'], 'detail': str(len(pk))})

out = pd.DataFrame(rows)
print('=' * 88)
print('FUNDING PACKET READABILITY CHECK   (%d papers)' % len(d))
print('=' * 88)
if out.empty:
    print('no findings')
else:
    print(out['screen'].value_counts().to_string())
    for s in ['P0_no_packet', 'P1_statement_not_in_packet', 'P2_negative_not_in_packet',
              'P3_ack_not_in_packet', 'P5_packet_suspiciously_short']:
        sub = out[out['screen'] == s]
        if len(sub):
            print('\n--- %s (%d) ---' % (s, len(sub)))
            for _, x in sub.head(15).iterrows():
                print('  %s  %s' % (x['PMID'], str(x.get('detail', ''))[:150]))
    n4 = (out['screen'] == 'P4_no_money_word_at_all').sum()
    if n4:
        sub = out[out['screen'] == 'P4_no_money_word_at_all']
        print('\n--- P4 no money word anywhere (%d) --- labels: %s'
              % (n4, dict(sub['label'].value_counts())))
        print('  ' + ' '.join(sub['PMID'].tolist()))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print('\n%d rows -> %s' % (len(out), OUT))
