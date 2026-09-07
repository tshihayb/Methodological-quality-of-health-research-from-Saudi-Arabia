# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Systematic sweep of S1/S2 for errors the paper-vs-PubMed checks are BLIND to.

WHY A SWEEP IS NEEDED AT ALL
----------------------------
Every validation in this project so far compares the published paper against PubMed. That
cannot detect an error the two SHARE, and they share plenty, because PubMed's record
descends from the same byline. STUDY-0468 Fanikos is the proven case: the byline prints
affiliation marker "1" (Qassim University) against Ting, Fanikos and Buckley; PubMed
corrects Ting and Buckley to Brigham and Women's but inherits the error for Fanikos. The
hand-read agreed with PubMed, so nothing was ever flagged.

THREE SCREENS, all computable from data already on disk. None of them is proof -- each
produces CANDIDATES for external verification.

  A. MARKER-GROUP ASYMMETRY  (the Fanikos signature, and the strongest signal)
     Within one shared affiliation marker, PubMed contradicts the paper for some authors
     but agrees for others. The agreeing ones are suspect: if the marker was wrong for the
     group, PubMed simply failed to correct that member.

  B. CROSS-PAPER CONTRADICTION
     The same person appears on more than one paper in the corpus with different countries.
     One of the two is wrong, or they hold both -- either way it deserves a look.

  C. SOLE NON-ARABIC NAME AT A SAUDI INSTITUTION
     Weakest and deliberately last: an author whose name matches none of the usual Saudi
     name patterns, sitting alone at a Saudi institution on a paper. Fanikos looked exactly
     like this. High false-positive rate by construction -- Saudi institutions genuinely
     employ many expatriates -- so it is for ranking, never for editing.

Writes candidates only. Nothing here changes S1 or S2.
Run from the repository root.
"""
import io
import re
import sys
import unicodedata
from collections import defaultdict

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

S1 = 'data/authors/07_25_2026_author_country_long.csv'
S2 = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
HR = 'data/authors/08_23_2026_handread_author_affiliations.csv'
OUT = 'data/quality-control/08_24_2026_s1_s2_sweep_candidates.csv'


def norm(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]', '', s.lower())


def saudi(x):
    return 'Saudi Arabia' in str(x or '')


# Name shapes that are overwhelmingly Arabic/Saudi in this corpus. Absence proves nothing;
# it only lowers the prior enough to be worth a human look.
ARABIC_HINT = re.compile(
    r'^(al|el|ibn|bin|abu|abd|abdul|abdel)|'
    r'(allah|ullah|uddin|udeen|zahrani|ghamdi|shehri|otaibi|harbi|qahtani|dosari|'
    r'mutairi|shammari|anazi|juhani|malki|amri|asiri|khaldi|rashidi|subaie|'
    r'ahmed|ahmad|mohamed|mohammed|muhammad|hassan|hussein|ali|omar|khan|ullah|'
    r'saeed|salem|salman|nasser|fahad|faisal|sultan|majed|yousef|ibrahim|mahmoud|'
    r'mostafa|mustafa|abdallah|elsayed|eldin|din)$', re.I)


def main():
    s1 = pd.read_csv(S1, encoding='utf-8-sig')
    s2 = pd.read_csv(S2, encoding='utf-8-sig')
    hr = pd.read_csv(HR, encoding='utf-8-sig')
    hr['verbatim'] = hr.verbatim.fillna('')
    hr['marker'] = hr.marker.fillna('')
    s1['is_saudi'] = s1.all_countries.map(saudi)

    rows = []

    # ---------------- A. marker-group asymmetry ----------------
    hrp = hr[hr.verbatim != ''].copy()
    hrp['read_saudi'] = hrp.verbatim.map(lambda v: 'saudi arabia' in v.lower()
                                         or 'kingdom of saudi' in v.lower())
    # one record per (paper, author): did the PAPER put them in Saudi Arabia?
    pa = hrp.groupby(['PMID', 'author_index']).agg(
        read_saudi=('read_saudi', 'any'),
        marker=('marker', lambda s: ','.join(sorted({x for x in s if x})))).reset_index()
    m = pa.merge(s1[['PMID', 'author_index', 'last', 'is_saudi', 'all_countries']],
                 on=['PMID', 'author_index'], how='inner')
    m['conflict'] = m.read_saudi != m.is_saudi

    for (pmid, mk), g in m[m.marker != ''].groupby(['PMID', 'marker']):
        if len(g) < 2:
            continue
        # the paper put this whole marker group in Saudi Arabia ...
        if not g.read_saudi.all():
            continue
        # ... PubMed contradicted SOME of them, but not all
        n_conf = int(g.conflict.sum())
        if 0 < n_conf < len(g):
            for _, r in g[~g.conflict].iterrows():
                rows.append({
                    'screen': 'A_marker_asymmetry', 'PMID': pmid, 'author_index': r.author_index,
                    'last': r.last, 'data_says': r.all_countries,
                    'why': f'marker {mk!r} shared by {len(g)} authors; PubMed contradicts the '
                           f'paper for {n_conf} of them but agrees for this one',
                    'priority': 1})

    # ---------------- B. cross-paper contradiction ----------------
    s1['nk'] = s1.last.map(norm) + '|' + s1.fore.fillna('').map(lambda x: norm(x)[:6])
    for nk, g in s1[s1.nk.str.len() > 3].groupby('nk'):
        if g.PMID.nunique() < 2:
            continue
        sd = set(g.is_saudi)
        if len(sd) > 1:                      # same person, Saudi on one paper and not another
            for _, r in g.iterrows():
                rows.append({
                    'screen': 'B_cross_paper', 'PMID': r.PMID, 'author_index': r.author_index,
                    'last': r.last, 'data_says': r.all_countries,
                    'why': f'same person on {g.PMID.nunique()} papers with inconsistent '
                           f'Saudi status ({sorted(set(g.PMID))})',
                    'priority': 2})

    # ---------------- C. sole non-Arabic name at a Saudi institution ----------------
    for pmid, g in s2.groupby('PMID'):
        for _, r in g.iterrows():
            if ARABIC_HINT.search(str(r.last)):
                continue
            rows.append({
                'screen': 'C_name_shape', 'PMID': pmid, 'author_index': r.author_index,
                'last': r.last, 'data_says': r.institution,
                'why': 'surname matches no common Saudi name pattern while placed at a '
                       'Saudi institution (weak screen; expatriates are common)',
                'priority': 3})

    out = pd.DataFrame(rows).sort_values(['priority', 'PMID', 'author_index'])
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'{len(out)} candidate rows -> {OUT}\n')
    print(out.screen.value_counts().to_string())
    for s in ['A_marker_asymmetry', 'B_cross_paper']:
        sub = out[out.screen == s]
        print(f'\n===== {s}: {len(sub)} rows over {sub.PMID.nunique()} papers =====')
        for _, r in sub.iterrows():
            print(f'  {r.PMID} idx{r.author_index} {r.last}: {r.data_says}')
            print(f'      {r.why}')
    c = out[out.screen == 'C_name_shape']
    print(f'\n===== C_name_shape: {len(c)} rows (ranking only, NOT findings) =====')
    print('  distinct surnames:', c.last.nunique())


if __name__ == '__main__':
    main()
