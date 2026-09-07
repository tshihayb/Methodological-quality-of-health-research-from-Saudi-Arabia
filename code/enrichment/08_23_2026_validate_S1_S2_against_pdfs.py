# -*- coding: utf-8 -*-
"""Validate Supplementary Figures S1 (author countries) and S2 (Saudi institutions)
against the full text of all 385 papers.

Both figures are built from PubMed affiliation strings. This checks them against the
papers themselves, which is an INDEPENDENT source: PubMed's affiliation field is
keyed by the publisher and is routinely truncated, reordered, or missing.

Two directions, because they fail differently:

  PRECISION  every country / institution asserted for a paper should be findable in
             that paper's text. A miss is strong evidence of a wrong assignment.
  RECALL     a country found in the paper's affiliation header that was NOT assigned
             is a candidate omission. Noisier -- author bylines, journal addresses and
             reference lists all name countries -- so it is reported for review, not
             treated as an error.

Run from the repository root.
"""
import os, re, sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import country_matcher as cm
from saudi_institution_classifier import TIER1, TIER2, _compact, _norm

TXT = 'private/fulltext/pdf-by-pmid'
OUT = 'data/quality-control'
HEADER_CHARS = 6000          # affiliations live on page 1 in almost every layout
os.makedirs(OUT, exist_ok=True)


import unicodedata


def clean_text(t):
    t = t.replace('­', '')
    t = re.sub(r'-\s*\n\s*(?=[a-z])', '', t)
    t = re.sub(r'(?<=[A-Za-z])-\s+(?=[a-z]{2})', '', t)
    # Strip accents: papers print "México", "Türkiye", "Córdoba". Without this the
    # country patterns miss them and the affiliation looks absent when it is not.
    t = unicodedata.normalize('NFKD', t)
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', t)


ORGISH = re.compile(
    r'\b(department|dept\.?|college|faculty|universit|hospital|institute|institut|school|'
    r'centre|center|ministry|clinic|laborator|division|unit|academy|research)\b', re.I)
# Publisher / journal boilerplate that names a country but is not anyone's affiliation.
NOT_AFFIL = re.compile(
    r'(licensee|copyright|©|[NAME-REDACTED]\s+nature|[NAME-REDACTED]-verlag|verlag|\bMDPI\b|'
    r'publishers?,?\s+inc|\bISSN\b|doi\s*:|creativecommons|all rights reserved|'
    r'this article is an open access|j\s+clin\s+pract|access this article|'
    r'how to cite|terms of the creative commons)', re.I)


def affil_segments(head):
    """Header pieces that plausibly ARE affiliations."""
    out = []
    for seg in re.split(r'\s*[;\n]\s*|(?<=[a-z])\.\s+(?=[A-Z])', head):
        seg = seg.strip()
        if len(seg) < 12 or len(seg) > 300:
            continue
        if NOT_AFFIL.search(seg) or not ORGISH.search(seg):
            continue
        out.append(seg)
    return out


# ---------------- lookups ----------------
ALIASES = {}                                  # canonical institution -> [compact aliases]
for _t, canon, al in list(TIER1) + list(TIER2):
    ALIASES.setdefault(canon, []).extend(al)

CVAR = {c: re.compile(r'\b(?:' + '|'.join(v) + r')\b', re.I)
        for c, v in cm.COUNTRY_VARIANTS.items()}
# Spellings a paper may use that the affiliation matcher's list does not carry. These
# are for the VALIDATOR only -- they decide whether a country is findable in the PDF,
# never how an author is classified.
_PDF_ONLY = {'Turkey': ['turkiye'], 'Netherlands': ['the netherlands'],
             'Czech Republic': ['czechia'], 'Ivory Coast': ["cote d'ivoire"]}
for _c, _extra in _PDF_ONLY.items():
    if _c in cm.COUNTRY_VARIANTS:
        CVAR[_c] = re.compile(r'\b(?:' + '|'.join(list(cm.COUNTRY_VARIANTS[_c]) + _extra) + r')\b', re.I)

# ---------------- assignments under test ----------------
L = pd.read_csv('data/authors/07_25_2026_author_country_long.csv', encoding='utf-8-sig')
A = pd.read_csv('data/authors/07_25_2026_saudi_affiliation_long.csv', encoding='utf-8-sig')

paper_countries = {}
for pmid, g in L.groupby('PMID'):
    s = set()
    for v in g['all_countries'].dropna():
        # all_countries is "; "-separated for dual-affiliation authors
        s.update(x.strip() for x in re.split(r'\s*;\s*', str(v)) if x.strip())
    for v in g['primary_country'].dropna():
        s.add(str(v).strip())
    paper_countries[str(pmid)] = {c for c in s if c and c.lower() != 'nan'}

paper_insts = {str(p): sorted(set(g['institution'])) for p, g in A.groupby('PMID')}

pmids = [r.strip() for r in
         pd.read_csv('data/analysis/07_25_2026_canonical_385_pmids.csv',
                     encoding='utf-8-sig')['PMID'].astype(str)]

# ---------------- run ----------------
c_rows, i_rows, r_rows = [], [], []
no_text = []

for pmid in pmids:
    p = os.path.join(TXT, pmid + '.txt')
    if not os.path.exists(p):
        no_text.append(pmid)
        continue
    raw = open(p, encoding='utf-8', errors='replace').read()
    flat = clean_text(raw)
    head = flat[:HEADER_CHARS]
    comp = _compact(flat)
    nrm = _norm(flat)

    # --- S1 precision: is every asserted country findable in the paper? ---
    for c in sorted(paper_countries.get(pmid, ())):
        rx = CVAR.get(c)
        if rx is None:
            c_rows.append([pmid, c, 'NO_VARIANT_PATTERN', ''])
            continue
        in_head = bool(rx.search(head))
        in_doc = bool(rx.search(flat))
        if not in_doc:
            c_rows.append([pmid, c, 'ABSENT_FROM_PDF', ''])
        elif not in_head:
            c_rows.append([pmid, c, 'not_in_header_but_in_body', ''])

    # --- S1 recall: countries named in an AFFILIATION-LIKE segment of the header ---
    # Scanning the whole header is useless: it is dominated by publisher addresses
    # ("Licensee MDPI, Basel, Switzerland"), journal abbreviations ("Niger J Clin
    # Pract") and body prose ("originating in Wuhan, China").
    assigned = paper_countries.get(pmid, set())
    for seg in affil_segments(head):
        for c, rx in CVAR.items():
            if c in assigned:
                continue
            m = rx.search(seg)
            if m:
                r_rows.append([pmid, c, seg[:200]])

    # --- S2 precision: is every asserted Saudi institution findable? ---
    for inst in paper_insts.get(pmid, ()):
        if inst.startswith('(') or inst.startswith('Private practice'):
            i_rows.append([pmid, inst, 'PLACEHOLDER', ''])
            continue
        al = ALIASES.get(inst)
        if not al:
            i_rows.append([pmid, inst, 'NO_ALIASES_KNOWN', ''])
            continue
        hit = next((a for a in al if a in comp), None)
        if not hit:
            i_rows.append([pmid, inst, 'ABSENT_FROM_PDF', ''])

C = pd.DataFrame(c_rows, columns=['PMID', 'country', 'flag', 'note'])
I = pd.DataFrame(i_rows, columns=['PMID', 'institution', 'flag', 'note'])
R = pd.DataFrame(r_rows, columns=['PMID', 'country_in_header_not_assigned', 'context'])
C.to_csv(f'{OUT}/08_23_2026_validate_S1_countries.csv', index=False, encoding='utf-8-sig')
I.to_csv(f'{OUT}/08_23_2026_validate_S2_institutions.csv', index=False, encoding='utf-8-sig')
R.to_csv(f'{OUT}/08_23_2026_validate_S1_recall_candidates.csv', index=False, encoding='utf-8-sig')

n_c = sum(len(paper_countries.get(p, ())) for p in pmids)
n_i = sum(len(paper_insts.get(p, ())) for p in pmids)
print('papers checked        : %d   (no text: %d)' % (len(pmids) - len(no_text), len(no_text)))
print('country assertions    : %d' % n_c)
print('institution assertions: %d' % n_i)
print()
print('--- S1 PRECISION (countries) ---')
print(C.flag.value_counts().to_string() if len(C) else '  clean')
print('  ABSENT_FROM_PDF: %d of %d = %.2f%%' %
      ((C.flag == 'ABSENT_FROM_PDF').sum(), n_c, 100.0 * (C.flag == 'ABSENT_FROM_PDF').sum() / n_c))
print()
print('--- S2 PRECISION (institutions) ---')
print(I.flag.value_counts().to_string() if len(I) else '  clean')
print('  ABSENT_FROM_PDF: %d of %d = %.2f%%' %
      ((I.flag == 'ABSENT_FROM_PDF').sum(), n_i, 100.0 * (I.flag == 'ABSENT_FROM_PDF').sum() / n_i))
print()
print('--- S1 RECALL candidates (header country not assigned) ---')
print('  rows: %d across %d papers' % (len(R), R.PMID.nunique() if len(R) else 0))
if len(R):
    print(R.country_in_header_not_assigned.value_counts().head(15).to_string())
print()
print('wrote 3 files to', OUT)
