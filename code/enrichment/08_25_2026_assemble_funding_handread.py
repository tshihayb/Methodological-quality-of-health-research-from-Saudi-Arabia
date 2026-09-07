# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Assemble the 39 blind funding hand-read batches, then diff them against the machine
classifier and emit an adjudication worklist.

The readers never saw `funding_3level`. This script is the first place the two sources meet,
so it is also the first place either can be shown wrong. It does three things and writes
nothing back into the funding datasets:

  1. ASSEMBLE   load every batch_*.json, validate the record schema, and account for all
                385 PMIDs. ⚠ The previous sweep of this kind silently lost 122 papers when
                11 of 33 readers died; a missing paper must be a loud number here, never an
                empty row.
  2. DIFF       reader call vs machine 3-level label, per paper.
  3. WORKLIST   every disagreement, every `unclear`, and every flagged special case
                (APC waiver, industry disclaimer, ethics body, ...) with BOTH sides'
                evidence side by side, ready for TSA to rule on.

Run from the repository root.
"""
import glob
import io
import json
import os
import re
import sys

import pandas as pd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HR = 'data/quality-control/08_25_2026_funding_handread'
CLS = 'data/analysis/08_23_2026_funding_classified_385.csv'
STMT = 'data/analysis/08_23_2026_funding_statements_385.csv'
CANON = 'data/analysis/07_25_2026_canonical_385_pmids.csv'
ADJ = 'data/quality-control/08_25_2026_funding_adjudication_items.csv'
WL = 'data/analysis/08_23_2026_funding_review_worklist.csv'
MERGED = HR + '/08_25_2026_funding_handread_merged.csv'
WORK = HR + '/08_25_2026_funding_handread_worklist.csv'

CALLS = {'funded', 'not_funded', 'not_stated', 'unclear'}
# ⚠ The protocol asks readers for `not_funded`; the machine column spells the same category
# `non_funded`. Diffing the raw strings scored 8 exact agreements as disagreements on the
# pilot batches. Canonicalise to the MACHINE's vocabulary before any comparison.
CANON_CALL = {'not_funded': 'non_funded', 'non_funded': 'non_funded',
              'funded': 'funded', 'not_stated': 'not_stated', 'unclear': 'unclear'}
FLAGS = {'apc_waiver', 'industry_disclaimer', 'ethics_body', 'in_kind',
         'credit_role', 'coi_boilerplate', 'literature_mention'}


def load_batches():
    recs, problems = [], []
    files = sorted(glob.glob(os.path.join(HR, 'batch_*.json')))
    for f in files:
        try:
            data = json.load(io.open(f, encoding='utf-8'))
        except Exception as e:
            problems.append((os.path.basename(f), 'UNREADABLE', str(e)[:120]))
            continue
        if not isinstance(data, list):
            problems.append((os.path.basename(f), 'NOT_A_LIST', type(data).__name__))
            continue
        for r in data:
            if not isinstance(r, dict) or 'pmid' not in r:
                problems.append((os.path.basename(f), 'BAD_RECORD', str(r)[:120]))
                continue
            call = str(r.get('call', '')).strip().lower()
            if call not in CALLS:
                problems.append((os.path.basename(f), 'BAD_CALL',
                                 '%s -> %r' % (r.get('pmid'), r.get('call'))))
            fl = r.get('flags') or []
            if isinstance(fl, str):
                fl = [x.strip() for x in re.split(r'[;,]', fl) if x.strip()]
            bad = [x for x in fl if x not in FLAGS]
            if bad:
                problems.append((os.path.basename(f), 'UNKNOWN_FLAG',
                                 '%s -> %s' % (r.get('pmid'), bad)))
            recs.append({
                'PMID': str(r['pmid']).strip(),
                'batch': re.sub(r'\D', '', os.path.basename(f)),
                'hr_call_raw': call,
                'hr_call': CANON_CALL.get(call, call),
                'hr_verbatim': str(r.get('verbatim', '') or ''),
                'hr_heading': str(r.get('heading', '') or ''),
                'hr_location': str(r.get('location', '') or ''),
                'hr_funders': str(r.get('funders', '') or ''),
                'hr_grant_ids': str(r.get('grant_ids', '') or ''),
                'hr_flags': ';'.join(x for x in fl if x in FLAGS),
                'hr_note': str(r.get('note', '') or ''),
            })
    return pd.DataFrame(recs), problems, files


def main():
    hr, problems, files = load_batches()
    canon = [str(r).strip() for r in
             pd.read_csv(CANON, encoding='utf-8-sig', dtype=str)['PMID']]

    print('=' * 92)
    print('FUNDING HAND-READ — ASSEMBLY')
    print('=' * 92)
    print('batch files            : %d' % len(files))
    print('records read           : %d' % len(hr))
    if len(hr):
        dup = hr[hr.duplicated('PMID', keep=False)].sort_values('PMID')
        print('duplicate PMIDs        : %d' % (len(dup)))
        if len(dup):
            print('  ' + ' '.join(sorted(set(dup['PMID']))))
            hr = hr.drop_duplicates('PMID', keep='first')
    got = set(hr['PMID']) if len(hr) else set()
    missing = [p for p in canon if p not in got]
    extra = sorted(got - set(canon))
    print('papers covered         : %d / %d' % (len(canon) - len(missing), len(canon)))
    print('MISSING                : %d' % len(missing))
    if missing:
        print('  ' + ' '.join(missing))
    if extra:
        print('NOT IN THE 385         : %s' % ' '.join(extra))
    if problems:
        print('\nschema problems (%d):' % len(problems))
        for f, kind, det in problems[:40]:
            print('  %-16s %-14s %s' % (f, kind, det))

    if not len(hr):
        print('\nno reader output yet — nothing to diff')
        return

    cl = pd.read_csv(CLS, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
    st = pd.read_csv(STMT, encoding='utf-8-sig', dtype={'PMID': str}).fillna('')
    d = hr.merge(cl[['PMID', 'funding_3level', 'funding_level_firstpass', 'confidence',
                     'basis', 'local_funders', 'intl_funders', 'declared_no_funding',
                     'oa_agreement_only', 'statement_source']],
                 on='PMID', how='left')
    d = d.merge(st[['PMID', 'funding_statement_verbatim', 'explicit_no_funding_hit',
                    'sec_acknowledgements']],
                on='PMID', how='left')
    d['agree'] = (d['hr_call'] == d['funding_3level']).astype(int)
    d.loc[d['hr_call'] == 'unclear', 'agree'] = 0

    os.makedirs(HR, exist_ok=True)
    d.to_csv(MERGED, index=False, encoding='utf-8-sig')

    print('\n' + '=' * 92)
    print('DIFF vs THE MACHINE  (%d papers read)' % len(d))
    print('=' * 92)
    print('\nreader calls:')
    print(d['hr_call'].value_counts().to_string())
    print('\nmachine labels (same papers):')
    print(d['funding_3level'].value_counts().to_string())
    print('\ncross-tab  rows = reader, cols = machine:')
    print(pd.crosstab(d['hr_call'], d['funding_3level']).to_string())
    n_ag = int(d['agree'].sum())
    print('\nagreement: %d / %d  (%.1f%%)' % (n_ag, len(d), 100.0 * n_ag / len(d)))

    flagged = d[d['hr_flags'].str.len() > 0]
    if len(flagged):
        print('\nreader flags:')
        tally = {}
        for s in flagged['hr_flags']:
            for f in s.split(';'):
                tally[f] = tally.get(f, 0) + 1
        for k, v in sorted(tally.items(), key=lambda x: -x[1]):
            print('  %-22s %d' % (k, v))

    work = d[(d['agree'] == 0) | (d['hr_flags'].str.len() > 0)].copy()
    work['reason'] = work.apply(
        lambda r: 'UNCLEAR' if r['hr_call'] == 'unclear'
        else ('DISAGREE %s->%s' % (r['funding_3level'], r['hr_call'])
              if r['agree'] == 0 else 'FLAG_ONLY'), axis=1)

    # ▶ The cut that decides how much this sweep was worth. A disagreement the machine had
    # ALREADY queued (the 7 open adjudication items, or the 49-row low/medium confidence
    # worklist) is a confirmation. One the machine filed as HIGH confidence and never
    # queued is a genuine catch -- it is exactly the class the V1-V6 screens cannot reach,
    # because a high-confidence wrong answer raises no flag.
    known = set()
    for path, col in ((ADJ, 'PMID'), (WL, 'PMID')):
        if os.path.exists(path):
            known |= set(pd.read_csv(path, dtype=str, encoding='utf-8-sig')[col].str.strip())
    work['already_queued'] = work['PMID'].isin(known).astype(int)
    work = work.sort_values(['already_queued', 'reason', 'PMID'])
    work.to_csv(WORK, index=False, encoding='utf-8-sig')

    print('\nworklist: %d rows -> %s' % (len(work), WORK))
    print(work['reason'].str.split(' ').str[0].value_counts().to_string())

    dis = work[work['reason'].str.startswith(('DISAGREE', 'UNCLEAR'))]
    if len(dis):
        newly = dis[dis['already_queued'] == 0]
        print('\ndisagreements + unclear : %d' % len(dis))
        print('  already queued by the machine (7 adjudication items / 49-row worklist): %d'
              % (len(dis) - len(newly)))
        print('  NEW — machine gave no signal                                        : %d'
              % len(newly))
        if len(newly):
            print('\n  new, by machine confidence: %s'
                  % dict(newly['confidence'].value_counts()))
            print('  %-10s %-12s %-12s %-6s %s' % ('PMID', 'machine', 'reader', 'conf', 'note'))
            for _, r in newly.iterrows():
                print('  %-10s %-12s %-12s %-6s %s'
                      % (r['PMID'], r['funding_3level'], r['hr_call'], r['confidence'],
                         str(r['hr_note'])[:96]))
    # ▶ Ruling #2 (APC / read-and-publish waivers) was written for ONE paper, STUDY-0423.
    # If the readers find a cluster of papers whose only money is a publication fee, the
    # ruling stops being a footnote and starts moving the headline percentages -- so the
    # population it would touch is printed explicitly, with the machine's current label.
    for flag in ('apc_waiver', 'industry_disclaimer', 'ethics_body', 'in_kind'):
        sub = d[d['hr_flags'].str.contains(flag, na=False)]
        if not len(sub):
            continue
        print('\n--- reader flag %s: %d papers ---' % (flag, len(sub)))
        print(pd.crosstab(sub['hr_call'], sub['funding_3level']).to_string())
        moves = sub[sub['agree'] == 0]
        if len(moves):
            print('  would move: ' + ' '.join(
                '%s(%s->%s)' % (r['PMID'], r['funding_3level'], r['hr_call'])
                for _, r in moves.iterrows()))

    print('\nmerged  : %s' % MERGED)


if __name__ == '__main__':
    main()
