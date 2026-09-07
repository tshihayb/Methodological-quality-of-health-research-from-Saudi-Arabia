# NOTE (public repository): 5 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Assign the 385 papers to hand-read batches.

Batch 00 is a PILOT: the 7 hand-transcribed gold papers plus 5 known-hard layouts. It runs
first and is checked against the gold file before the rest fan out -- 31 more readers
producing the wrong shape is a far more expensive mistake than one pilot.

The remaining 373 are stratified by the machine parser's status so every batch carries a
mix of easy and hard papers. Grouping the hard ones together would concentrate the
judgement calls in a handful of readers and make their output incomparable with the rest.

Run from the repository root.
"""
import json
import os

import pandas as pd

STATUS = 'data/quality-control/08_23_2026_pdf_author_parse_status.csv'
GOLD = 'data/authors/08_23_2026_pdf_affiliations_gold.csv'
OUT = 'data/quality-control/08_23_2026_handread'
PER_BATCH = 12

# Known-hard layouts, one per failure family documented in the linkage memo.
PILOT_HARD = [
    STUDY-1007,   # symbol-keyed footnote, byline symbols inline not superscript
    STUDY-0914,   # footnote affiliations with NO keys ("; and the")
    STUDY-0455,   # NO_AFFIL_BLOCK; the paper that broke the `single_affiliation` shortcut
    STUDY-0531,   # truncated affiliations ("Divisions of Neurology and.")
    STUDY-0337,   # second affiliations printed only in the tail "Author details" block
]


def main():
    os.makedirs(OUT, exist_ok=True)
    st = pd.read_csv(STATUS, encoding='utf-8-sig')
    gold = sorted(pd.read_csv(GOLD, encoding='utf-8-sig').PMID.unique().tolist())

    pilot = gold + PILOT_HARD
    assert len(set(pilot)) == len(pilot), 'pilot has a duplicate'

    rest = st[~st.PMID.isin(pilot)].copy()
    # Interleave hard and easy: sort by status then PMID, then deal round-robin.
    rest['hard'] = (rest.status != 'OK').astype(int)
    rest = rest.sort_values(['hard', 'PMID'], ascending=[False, True])
    n_batches = -(-len(rest) // PER_BATCH)
    buckets = [[] for _ in range(n_batches)]
    for i, pmid in enumerate(rest.PMID.tolist()):
        buckets[i % n_batches].append(int(pmid))

    manifest = [{'batch': '00', 'kind': 'pilot', 'pmids': pilot}]
    for i, b in enumerate(buckets, start=1):
        manifest.append({'batch': f'{i:02d}', 'kind': 'main', 'pmids': sorted(b)})

    with open(os.path.join(OUT, 'batches.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1)

    covered = sorted(p for m in manifest for p in m['pmids'])
    assert covered == sorted(st.PMID.astype(int).tolist()), 'batching lost or duplicated a paper'

    hard = set(st[st.status != 'OK'].PMID)
    print(f'{len(manifest)} batches over {len(covered)} papers')
    for m in manifest:
        nh = sum(1 for p in m['pmids'] if p in hard)
        print(f"  batch {m['batch']} ({m['kind']}): {len(m['pmids']):2d} papers, {nh} hard")


if __name__ == '__main__':
    main()
