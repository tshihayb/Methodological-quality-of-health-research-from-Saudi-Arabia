"""Post-correction audit of S1 and S2: invariants, residuals, and LATENT matcher collisions.

Run after the 2026-08-24 corrections to answer "is anything else wrong?" by checking rather
than asserting. Nothing here modifies data.

The `de`->Delaware and `Al`->Alabama collisions were both found by ACCIDENT, one row at a
time. Check E generalises that: it walks the whole US-state-abbreviation table looking for
tokens that are also ordinary words in institution names or non-English prepositions, and
reports which ones are live in this corpus.

Run from the repository root.
"""
import io
import re
import sys

import pandas as pd

sys.path.insert(0, 'code/lib')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import country_matcher as CM                     # noqa: E402

S1 = 'data/authors/07_25_2026_author_country_long.csv'
S2 = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
HR = 'data/authors/08_23_2026_handread_author_affiliations.csv'


def hdr(t):
    print('\n' + '=' * 92)
    print(t)
    print('=' * 92)


def main():
    s1 = pd.read_csv(S1, encoding='utf-8-sig')
    s2 = pd.read_csv(S2, encoding='utf-8-sig')
    hr = pd.read_csv(HR, encoding='utf-8-sig')
    hr['verbatim'] = hr.verbatim.fillna('')
    s1['is_saudi'] = s1.all_countries.fillna('').str.contains('Saudi Arabia')
    issues = []

    # ---- A. S1 <-> S2 must agree on exactly who is Saudi -------------------------
    hdr('A. S1 <-> S2 consistency')
    k1 = set(map(tuple, s1[s1.is_saudi][['PMID', 'author_index']].values))
    k2 = set(map(tuple, s2[['PMID', 'author_index']].values))
    print(f'  Saudi authors in S1: {len(k1)}   rows in S2: {len(k2)}')
    for lbl, s in [('in S1 but MISSING from S2', k1 - k2), ('in S2 but NOT Saudi in S1', k2 - k1)]:
        print(f'  {lbl}: {len(s)}')
        if s:
            issues.append(f'{lbl}: {sorted(s)[:10]}')
            for x in sorted(s)[:10]:
                print('      ', x)

    # ---- B. duplicate keys -------------------------------------------------------
    hdr('B. duplicate (PMID, author_index)')
    for nm, df in [('S1', s1), ('S2', s2)]:
        d = df[df.duplicated(['PMID', 'author_index'], keep=False)]
        print(f'  {nm}: {len(d)} duplicate rows')
        if len(d):
            issues.append(f'{nm} has duplicate keys')

    # ---- C. inclusion criterion --------------------------------------------------
    hdr('C. every paper must have >=1 Saudi author')
    z = s1.groupby('PMID').is_saudi.any()
    bad = sorted(z[~z].index.tolist())
    print(f'  papers with NO Saudi author: {len(bad)} {bad if bad else ""}')
    print(f'  papers in S1: {s1.PMID.nunique()}   papers in S2: {s2.PMID.nunique()}')
    if bad:
        issues.append(f'papers with no Saudi author: {bad}')

    # ---- D. authors the hand-read could never corroborate -------------------------
    hdr('D. residual UNVERIFIED authors')
    noaff = hr[hr.verbatim == ''][['PMID', 'author_index']].drop_duplicates()
    m = noaff.merge(s1[['PMID', 'author_index', 'last', 'is_saudi', 'all_countries']],
                    on=['PMID', 'author_index'], how='inner')
    print(f'  paper prints NO affiliation for: {len(m)} authors '
          f'({int(m.is_saudi.sum())} of them counted Saudi)')
    for _, r in m[m.is_saudi].iterrows():
        print(f'      {r.PMID} idx{r.author_index} {r.last} -> {r.all_countries}')
    hrk = set(map(tuple, hr[['PMID', 'author_index']].drop_duplicates().values))
    s1k = set(map(tuple, s1[['PMID', 'author_index']].values))
    print(f'  in S1 but never hand-read at all: {len(s1k - hrk)}')

    # ---- E. LATENT US-state-abbreviation collisions -------------------------------
    hdr('E. US state-abbreviation collisions (generalises the `de`/`al` bugs)')
    abbr = set(CM.US_STATE_ABBR) | set(getattr(CM, 'US_STATE_ABBR_EXTRA', set()))
    # tokens that are also ordinary words / foreign prepositions found in institution names
    risky = {'al', 'de', 'la', 'in', 'or', 'me', 'oh', 'ok', 'id', 'hi', 'pa', 'va', 'ma',
             'mo', 'ms', 'mt', 'ne', 'nv', 'ar', 'co', 'ct', 'ga', 'ia', 'ks', 'ky', 'sc',
             'sd', 'nd', 'nc', 'ny', 'tn', 'tx', 'ut', 'vt', 'wa', 'wi', 'wv', 'wy', 'un'}
    risky &= abbr
    print(f'  state abbreviations that are also common words/prepositions: {sorted(risky)}')
    # which are LIVE in the corpus -- i.e. actually decide a country for some affiliation?
    live = {}
    for _, r in s1.iterrows():
        pass
    import json
    cache = json.load(open('data/authors/07_25_2026_authors_cache_385.json', encoding='utf-8'))
    n_seg = 0
    for pmid, rec in cache.items():
        auths = rec['authors'] if isinstance(rec, dict) and 'authors' in rec else rec
        for i, a in enumerate(auths, 1):
            for seg in re.split(r'\s*[|;]\s*', a.get('aff') or ''):
                if not seg.strip():
                    continue
                n_seg += 1
                c, how = CM.detect_country_segment(seg)
                if how != 'us-state-abbr':
                    continue
                toks = [re.sub(r'[^a-z]', '', t) for t in re.split(r'[,\s;]+', seg.lower())]
                toks = [t for t in toks if t]
                trig = next((t for t in reversed(toks[-5:]) if t in abbr), None)
                if trig in risky:
                    live.setdefault(trig, []).append((pmid, i, a.get('last'), seg[:110]))
    print(f'  affiliation segments scanned: {n_seg}')
    print(f'  LIVE risky-token decisions: {sum(len(v) for v in live.values())}')
    for t, v in sorted(live.items()):
        print(f'    token {t!r}: {len(v)}')
        for x in v[:4]:
            print(f'        {x[0]} idx{x[1]} {x[2]}: {x[3]}')
        issues.append(f'us-state-abbr token {t!r} decides {len(v)} affiliation(s)')

    # ---- F. placeholders / weak classifications in S2 ------------------------------
    hdr('F. S2 placeholders and weak classifications')
    ph = s2[s2.institution.astype(str).str.startswith('(')]
    print(f'  placeholder institution rows: {len(ph)}')
    for _, r in ph.iterrows():
        print(f'      {r.PMID} idx{r.author_index} {r.last}: {r.institution!r} ({r.inst_type})')
    print(f'  city == "Unspecified": {(s2.city == "Unspecified").sum()}')
    print('  tier mix:', s2.tier.value_counts().to_dict())
    print('  source mix:', s2.source.value_counts().to_dict())

    # ---- G. non-Saudi city leaking into S2 -----------------------------------------
    hdr('G. sanity: S2 rows whose block resolves to a NON-Saudi country')
    bad2 = []
    for _, r in s2.iterrows():
        b = str(r.saudi_block or '')
        if not b.strip():
            continue
        c, _ = CM.detect_country_segment(b)
        if c and c != 'Saudi Arabia':
            bad2.append((r.PMID, r.author_index, r.last, c, b[:90]))
    print(f'  rows whose own block resolves NON-Saudi: {len(bad2)}')
    for x in bad2[:12]:
        print(f'      {x[0]} idx{x[1]} {x[2]} -> {x[3]}: {x[4]}')
    if bad2:
        issues.append(f'{len(bad2)} S2 rows whose block resolves to a non-Saudi country')

    hdr('SUMMARY')
    if issues:
        print(f'{len(issues)} item(s) needing attention:')
        for i in issues:
            print('  -', i)
    else:
        print('no invariant violations found')


if __name__ == '__main__':
    main()
