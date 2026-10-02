"""Check a hand-read batch against the hand-transcribed gold file.

The gold file (data/authors/08_23_2026_pdf_affiliations_gold.csv) is a partial
transcription -- 47 rows over 7 papers, not every author -- so this checks CONTAINMENT:
for every gold (PMID, author_index) it asks whether the hand-read recorded the same
surname and an affiliation matching the gold one. It does not penalise the hand-read for
holding authors the gold file never covered.

Matching on affiliation text is deliberately loose (case-folded, accent-stripped,
punctuation and whitespace collapsed) because the two sources were transcribed
independently and differ in trailing periods and word spacing, not in substance.

Run from the repository root:  python code/enrichment/08_23_2026_check_handread_vs_gold.py
"""
import glob
import json
import os
import re
import sys
import unicodedata

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

GOLD = 'data/authors/08_23_2026_pdf_affiliations_gold.csv'
HANDREAD = 'data/quality-control/08_23_2026_handread'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()


def load_handread(pattern='batch_*.json'):
    rows = []
    for fp in sorted(glob.glob(os.path.join(HANDREAD, pattern))):
        with open(fp, encoding='utf-8') as f:
            d = json.load(f)
        for p in d['papers']:
            for a in p.get('authors', []):
                affs = a.get('affiliations') or [{}]
                for af in affs:
                    rows.append({'PMID': int(p['PMID']), 'author_index': a['author_index'],
                                 'last': a.get('last', ''), 'fore': a.get('fore', ''),
                                 'markers': ','.join(a.get('markers') or []),
                                 'is_corresponding': a.get('is_corresponding'),
                                 'confidence': a.get('confidence', ''),
                                 'affil_ordinal': af.get('ordinal'),
                                 'marker': af.get('marker', ''),
                                 'verbatim': af.get('verbatim', ''),
                                 'country': af.get('country', ''),
                                 'paper_status': p.get('status'), 'linkage': p.get('linkage'),
                                 'batch': d.get('batch'), 'src': os.path.basename(fp)})
    return pd.DataFrame(rows)


def main():
    hr = load_handread()
    if hr.empty:
        print('no hand-read batches found'); return
    gold = pd.read_csv(GOLD, encoding='utf-8-sig')
    gp = sorted(gold.PMID.unique())
    hr_gold = hr[hr.PMID.isin(gp)]
    print(f'hand-read: {len(hr)} affiliation rows over {hr.PMID.nunique()} papers')
    print(f'gold: {len(gold)} rows over {len(gp)} papers; '
          f'{hr_gold.PMID.nunique()} of them present in the hand-read\n')

    hit = miss = namebad = 0
    for _, g in gold.iterrows():
        cand = hr_gold[(hr_gold.PMID == g.PMID) & (hr_gold.author_index == g.author_index)]
        if cand.empty:
            print(f'  MISSING author  {g.PMID} idx {g.author_index} ({g.last})')
            miss += 1
            continue
        if norm(cand.iloc[0]['last']) != norm(g['last']):
            print(f'  SURNAME differs {g.PMID} idx {g.author_index}: '
                  f'gold "{g["last"]}" vs read "{cand.iloc[0]["last"]}"')
            namebad += 1
        gn = norm(g.affiliation_verbatim)
        ok = any(norm(v) == gn or norm(v) in gn or gn in norm(v) for v in cand.verbatim)
        if ok:
            hit += 1
        else:
            miss += 1
            print(f'  AFFIL differs   {g.PMID} idx {g.author_index} ({g.last})')
            print(f'      gold: {g.affiliation_verbatim[:120]}')
            for v in cand.verbatim:
                print(f'      read: {str(v)[:120]}')

    n = len(gold)
    print(f'\ngold containment: {hit}/{n} = {hit / n:.1%}   (misses {miss}, surname diffs {namebad})')
    print('\nconfidence mix over the whole hand-read:')
    print(hr.drop_duplicates(['PMID', 'author_index']).confidence.value_counts().to_string())
    print('\npaper status:')
    print(hr.drop_duplicates('PMID').paper_status.value_counts().to_string())
    print('\nlinkage basis:')
    print(hr.drop_duplicates('PMID').linkage.value_counts().to_string())


if __name__ == '__main__':
    main()
