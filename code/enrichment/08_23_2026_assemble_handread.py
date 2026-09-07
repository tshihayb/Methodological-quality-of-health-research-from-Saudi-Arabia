"""Assemble the hand-read batch JSONs into one long author-affiliation table.

Validates before it writes. The failure mode that matters here is a SILENT one: a batch
that never landed, a paper dropped from a batch, or an author_index reused -- each of
those looks like clean data downstream and quietly changes a denominator. So coverage and
key uniqueness are assertions, not warnings.

Outputs
  data/authors/08_23_2026_handread_author_affiliations.csv   one row per (author, affiliation)
  data/quality-control/08_23_2026_handread_paper_status.csv  one row per paper

Run from the repository root.
"""
import glob
import json
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HANDREAD = 'data/quality-control/08_23_2026_handread'
MANIFEST = os.path.join(HANDREAD, 'batches.json')
OUT_ROWS = 'data/authors/08_23_2026_handread_author_affiliations.csv'
OUT_PAPERS = 'data/quality-control/08_23_2026_handread_paper_status.csv'

PAPER_STATUS = {'resolved', 'partial', 'unresolvable'}
LINKAGE = {'explicit', 'positional', 'single', 'none'}
CONF = {'high', 'medium', 'low'}


def main():
    with open(MANIFEST, encoding='utf-8') as f:
        manifest = json.load(f)
    expected_batches = {m['batch'] for m in manifest}
    expected_pmids = {p for m in manifest for p in m['pmids']}

    files = sorted(glob.glob(os.path.join(HANDREAD, 'batch_*.json')))
    got_batches = {os.path.basename(f)[6:8] for f in files}
    missing = sorted(expected_batches - got_batches)
    if missing:
        print(f'⚠ {len(missing)} batch file(s) not written yet: {", ".join(missing)}')

    rows, papers, problems = [], [], []
    for fp in files:
        with open(fp, encoding='utf-8') as f:
            try:
                d = json.load(f)
            except json.JSONDecodeError as e:
                problems.append(f'{os.path.basename(fp)}: invalid JSON -- {e}')
                continue
        batch = str(d.get('batch', os.path.basename(fp)[6:8]))
        for p in d.get('papers', []):
            pmid = int(p['PMID'])
            st, lk = p.get('status'), p.get('linkage')
            if st not in PAPER_STATUS:
                problems.append(f'{pmid}: bad status {st!r}')
            if lk not in LINKAGE:
                problems.append(f'{pmid}: bad linkage {lk!r}')
            auths = p.get('authors', []) or []
            idx = [a.get('author_index') for a in auths]
            if len(set(idx)) != len(idx):
                problems.append(f'{pmid}: duplicate author_index')
            if idx and sorted(idx) != list(range(1, len(idx) + 1)):
                problems.append(f'{pmid}: author_index not 1..n (got {sorted(idx)[:5]}...)')
            if p.get('n_authors') not in (None, len(auths)):
                problems.append(f'{pmid}: n_authors {p.get("n_authors")} != {len(auths)} entries')

            papers.append({'PMID': pmid, 'batch': batch, 'n_authors': len(auths),
                           'status': st, 'linkage': lk, 'layout': p.get('layout', ''),
                           'note': p.get('note', '')})
            for a in auths:
                if a.get('confidence') not in CONF:
                    problems.append(f'{pmid} idx {a.get("author_index")}: '
                                    f'bad confidence {a.get("confidence")!r}')
                affs = a.get('affiliations') or []
                base = {'PMID': pmid, 'batch': batch,
                        'author_index': a.get('author_index'),
                        'last': (a.get('last') or '').strip(),
                        'fore': (a.get('fore') or '').strip(),
                        'markers': ','.join(a.get('markers') or []),
                        'is_corresponding': bool(a.get('is_corresponding')),
                        'confidence': a.get('confidence'),
                        'n_affils': len(affs),
                        'author_note': a.get('note', '')}
                if not affs:
                    rows.append({**base, 'affil_ordinal': None, 'marker': '',
                                 'verbatim': '', 'country_read': ''})
                for af in affs:
                    rows.append({**base,
                                 'affil_ordinal': af.get('ordinal'),
                                 'marker': af.get('marker', ''),
                                 'verbatim': (af.get('verbatim') or '').strip(),
                                 'country_read': (af.get('country') or '').strip()})

    df = pd.DataFrame(rows)
    pf = pd.DataFrame(papers)

    if pf.empty:
        print('no papers assembled'); return

    dup = pf[pf.duplicated('PMID', keep=False)]
    if not dup.empty:
        problems.append(f'papers appearing in more than one batch: '
                        f'{sorted(dup.PMID.unique().tolist())}')
    got = set(pf.PMID)
    absent = sorted(expected_pmids - got)
    extra = sorted(got - expected_pmids)
    if extra:
        problems.append(f'papers not in any batch assignment: {extra}')

    os.makedirs(os.path.dirname(OUT_ROWS), exist_ok=True)
    df.to_csv(OUT_ROWS, index=False, encoding='utf-8-sig')
    pf.to_csv(OUT_PAPERS, index=False, encoding='utf-8-sig')

    print(f'batches present : {len(got_batches)}/{len(expected_batches)}')
    print(f'papers          : {len(pf)}/{len(expected_pmids)}'
          + (f'   ⚠ {len(absent)} not yet read' if absent else ''))
    print(f'author entries  : {df.drop_duplicates(["PMID", "author_index"]).shape[0]}')
    print(f'affiliation rows: {len(df[df.verbatim != ""])}')
    print(f'\nwrote {OUT_ROWS}\nwrote {OUT_PAPERS}')
    print('\npaper status:'); print(pf.status.value_counts().to_string())
    print('\nlinkage basis:'); print(pf.linkage.value_counts().to_string())
    print('\nauthor confidence:')
    print(df.drop_duplicates(['PMID', 'author_index']).confidence.value_counts().to_string())

    if problems:
        print(f'\n⚠ {len(problems)} VALIDATION PROBLEM(S):')
        for x in problems[:40]:
            print('  -', x)
        if len(problems) > 40:
            print(f'  ... and {len(problems) - 40} more')
    else:
        print('\n✅ no validation problems')


if __name__ == '__main__':
    main()
