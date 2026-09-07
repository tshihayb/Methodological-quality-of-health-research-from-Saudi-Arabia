# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Mine the CORRESPONDENCE BLOCK of all 385 papers and check it against S1/S2.

WHY
---
STUDY-0161 Almwled: her affiliation footnote reads only "From Administration of mental health
(Almwled), Makkah" -- a department with no parent institution -- so S2 classified her
'(unspecified)'. The correspondence block on the SAME PAGE says "Dr. Amani S. ALmwled,
Administration of Mental Health, King Abdullah Medical City. Makkah, Kingdom of Saudi
Arabia." The institution was printed all along, just not where the pipeline looks.

The pipeline reads PubMed's <Affiliation>, which mirrors the footnote. The correspondence
block is a SEPARATE, unmined source of institution and city.

⚠ A CORRESPONDENCE ADDRESS IS A MAILING ADDRESS. It may legitimately differ from the
author's listed affiliation (a hospital rather than the university department, a PO box, a
home institution while on secondment). So this script separates:

  GAP-FILL      S2 has no city / no named institution, and the block supplies one.
                Safe: it adds information where there was none.
  CONTRADICTION S2 names an institution and the block names a DIFFERENT one.
                NOT automatically an error -- needs adjudication.

Reports only. Writes nothing into S1 or S2.
Run from the repository root.
"""
import io
import os
import re
import sys

import pandas as pd

sys.path.insert(0, 'code/lib')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import saudi_institution_classifier as C          # noqa: E402
from country_matcher import detect_country_segment, SAUDI_CITIES   # noqa: E402

TXT = 'private/fulltext/pdf-by-pmid'
S2F = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
OUT = 'data/quality-control/08_24_2026_correspondence_candidates.csv'

START = re.compile(
    r'(address\s+(?:for\s+)?correspondence(?:\s+and\s+reprint\s+requests?)?\s*(?:to)?\s*:?|'
    r'corresponding\s+author\s*:?|correspondence\s+to\s*:?|correspondence\s*:|'
    r'reprint\s+requests?\s+to\s*:?)', re.I)
# The address ends at the email/ORCID/dates/licence furniture that always follows it.
STOP = re.compile(
    r'(e-?\s?mail|email|\borcid\b|received\s+\d|accepted\s+\d|copyright|©|'
    r'this\s+is\s+an\s+open|doi\s*:|https?://|\bdisclosure\b|conflict\s+of\s+interest|'
    r'\btel\b|\bfax\b|\bphone\b|\bp\.?o\.?\s*box)', re.I)


def clean(s):
    return re.sub(r'\s+', ' ', s).strip(' ,;.:-')


def city_of(s):
    n = s.lower()
    for c in SAUDI_CITIES:
        if re.search(r'\b' + re.escape(c) + r'\b', n):
            return c.title()
    return ''


def main():
    s2 = pd.read_csv(S2F, encoding='utf-8-sig')
    rows = []
    n_block = 0

    for pmid in sorted(s2.PMID.unique()):
        p = os.path.join(TXT, f'{pmid}.txt')
        if not os.path.exists(p):
            continue
        t = re.sub(r'\s+', ' ', open(p, encoding='utf-8', errors='replace').read())
        m = START.search(t)
        if not m:
            continue
        seg = t[m.end():m.end() + 400]
        st = STOP.search(seg)
        if st:
            seg = seg[:st.start()]
        seg = clean(seg)
        if len(seg) < 12:
            continue
        n_block += 1
        # Which author is this? Match a surname from the paper's Saudi authors.
        cand = s2[s2.PMID == pmid]
        segl = re.sub(r'[^a-z ]', ' ', seg.lower())
        for _, r in cand.iterrows():
            ln = re.sub(r'[^a-z]', '', str(r.last).lower())
            if len(ln) < 4 or ln not in re.sub(r'[^a-z]', '', segl):
                continue
            ctry, _ = detect_country_segment(seg)
            typ, inst, tier = C.classify(seg)
            city = city_of(seg)
            named = not str(inst).startswith('(')
            kind = None
            if named and str(r.institution).startswith('('):
                kind = 'GAPFILL_institution'
            elif city and r.city == 'Unspecified':
                kind = 'GAPFILL_city'
            elif named and inst != r.institution:
                kind = 'CONTRADICTION_institution'
            if kind:
                rows.append({'kind': kind, 'PMID': pmid, 'author_index': r.author_index,
                             'last': r.last, 's2_institution': r.institution,
                             's2_city': r.city, 's2_source': r.source,
                             'corr_institution': inst, 'corr_type': typ,
                             'corr_city': city, 'corr_country': ctry,
                             'correspondence_text': seg[:300]})
            break

    out = pd.DataFrame(rows)
    print(f'papers with a parseable correspondence block: {n_block} of {s2.PMID.nunique()}')
    if out.empty:
        print('no candidates'); return
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'{len(out)} candidates -> {OUT}\n')
    print(out.kind.value_counts().to_string())
    for k in ['GAPFILL_institution', 'GAPFILL_city', 'CONTRADICTION_institution']:
        sub = out[out.kind == k]
        if sub.empty:
            continue
        print(f'\n===== {k}: {len(sub)} =====')
        for _, r in sub.iterrows():
            print(f'  {r.PMID} idx{r.author_index} {r.last}')
            print(f'      S2  : {r.s2_institution!r} / city {r.s2_city!r} ({r.s2_source})')
            print(f'      CORR: {r.corr_institution!r} / city {r.corr_city!r} [{r.corr_country}]')
            print(f'      text: {r.correspondence_text[:170]}')


if __name__ == '__main__':
    main()
