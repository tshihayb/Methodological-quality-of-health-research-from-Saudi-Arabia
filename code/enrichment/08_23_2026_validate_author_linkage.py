# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""AUTHOR-LEVEL validation of S1 (countries) and S2 (Saudi institutions) against the PDFs.

The earlier check (08_23_2026_validate_S1_S2_against_pdfs.py) was paper-level: it asked
whether a country/institution appears ANYWHERE in the paper. That cannot catch an author
attached to the wrong value when a co-author legitimately holds it. This one resolves the
author -> affiliation linkage from the paper itself.

Method. We already know every author from PubMed, so the PDF's author list is not parsed.
Instead:
  1. locate the numbered affiliation block  ("1Department of ...  2Faculty of ...")
  2. find each PubMed surname in the header and read the marker digits attached to it
  3. resolve those markers to affiliation text -> country (country_matcher) and
     Saudi institution (saudi_institution_classifier)
  4. compare with what S1/S2 assert for that exact (PMID, author_index)

Papers with a single un-numbered affiliation are handled as their own tier: every author
shares it. Anything that cannot be parsed is reported as NOT CHECKED rather than passed.

Run from the repository root.
"""
import json, os, re, sys, unicodedata
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from country_matcher import detect_country_segment
from saudi_institution_classifier import classify

TXT = 'private/fulltext/pdf-by-pmid'
OUT = 'data/quality-control'
os.makedirs(OUT, exist_ok=True)


def strip_acc(s):
    s = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in s if not unicodedata.combining(c))


def clean(t):
    t = t.replace('­', '')
    t = re.sub(r'-\s*\n\s*(?=[a-z])', '', t)
    t = re.sub(r'(?<=[A-Za-z])-\s+(?=[a-z]{2})', '', t)
    t = strip_acc(t)
    return re.sub(r'[ \t]+', ' ', t)


def norm_name(s):
    return re.sub(r'[^a-z]', '', strip_acc(str(s)).lower())


# An affiliation marker: a 1-2 digit number that introduces a capitalised affiliation.
MARK = re.compile(r'(?:^|[\s.,;)\]])(\d{1,2})\s{0,2}(?=[A-Z][a-zA-Z])')
ORG = re.compile(r'\b(department|dept|college|faculty|school|division|centre|center|'
                 r'institute|unit|ministry|hospital|universit|clinic|laborator|academy|'
                 r'research|program|chair)\b', re.I)
STOP = re.compile(r'\b(abstract|introduction|keywords|summary|correspondence|'
                  r'corresponding author|received|accepted|citation|how to cite)\b', re.I)


def header_of(flat):
    """The front matter: title through the end of the affiliation list."""
    m = STOP.search(flat, 200)
    end = m.start() if m and m.start() > 300 else 4000
    return flat[:min(max(end, 1200), 9000)]


def parse_affils(head):
    """{marker_number: affiliation_text} from a numbered affiliation block."""
    hits = [(int(m.group(1)), m.end()) for m in MARK.finditer(head)]
    if not hits:
        return {}
    # keep the run that starts at 1 and climbs -- author-name superscripts also match
    # MARK, so anchor on the first '1' that is followed by organisation-ish words.
    starts = [i for i, (n, _) in enumerate(hits) if n == 1]
    best = {}
    for s in starts:
        seq, seen = [], 0
        for n, pos in hits[s:]:
            if n == seen + 1:
                seq.append((n, pos))
                seen = n
            elif n <= seen:
                continue
            else:
                break
        if len(seq) < 1:
            continue
        cand = {}
        for j, (n, pos) in enumerate(seq):
            end = seq[j + 1][1] - len(str(seq[j + 1][0])) - 1 if j + 1 < len(seq) else min(len(head), pos + 400)
            body = head[pos:end].strip(' ,;')
            cand[n] = body
        good = sum(1 for v in cand.values() if ORG.search(v) and len(v) > 15)
        if good > len(best.get('__good__', [])) if False else True:
            if good >= max(1, len(cand) // 2) and good > sum(
                    1 for v in best.values() if isinstance(v, str) and ORG.search(v) and len(v) > 15):
                best = cand
    return {k: v for k, v in best.items() if isinstance(v, str)}


def markers_for(head, surname):
    """Digits attached to a surname in the header, e.g. 'ABDELBASSET1,3' -> [1,3]."""
    ns = norm_name(surname)
    if len(ns) < 3:
        return None
    # rebuild a loose pattern so 'Bin Rubaia'an' matches 'Bin Rubaia'an'
    pat = r'[^A-Za-z]*'.join(re.escape(c) for c in ns)
    out = None
    for m in re.finditer(pat, head, re.I):
        tail = head[m.end():m.end() + 14]
        d = re.match(r'\s*((?:\d{1,2}\s*[,–-]\s*)*\d{1,2})(?![\d])', tail)
        if d:
            nums = [int(x) for x in re.findall(r'\d{1,2}', d.group(1))]
            if nums:
                return nums
        if out is None:
            out = []          # surname found but carries no marker
    return out


def main():
    cache = json.load(open('data/authors/07_25_2026_authors_cache_385.json', encoding='utf-8'))
    L = pd.read_csv('data/authors/07_25_2026_author_country_long.csv', encoding='utf-8-sig')
    A = pd.read_csv('data/authors/07_25_2026_saudi_affiliation_long.csv', encoding='utf-8-sig')
    inst_of = {(int(r.PMID), int(r.author_index)): r.institution for r in A.itertuples()}

    rows, pstat = [], []
    for pmid, g in L.groupby('PMID'):
        p = os.path.join(TXT, '%d.txt' % pmid)
        if not os.path.exists(p):
            pstat.append([pmid, 'NO_TEXT', 0, 0])
            continue
        flat = clean(open(p, encoding='utf-8', errors='replace').read())
        head = header_of(flat)
        affs = parse_affils(head)

        # NOTE: an earlier "single affiliation" tier assumed every author shared one
        # affiliation whenever no numbering was found. That is unsound -- on a
        # multi-country EBMT study (STUDY-0737) it labelled all 30 authors "Israel".
        # Only the numbered tier can establish a linkage; everything else is UNPARSED.
        tier = 'numbered' if len(affs) >= 2 else None
        if tier is None:
            pstat.append([pmid, 'UNPARSED', len(g), 0])
            continue

        checked = 0
        for r in g.itertuples():
            idx = int(r.author_index)
            mk = markers_for(head, r.last)
            if not mk:
                rows.append([pmid, idx, r.last, tier, 'AUTHOR_NOT_LOCATED', '', r.primary_country, '', ''])
                continue
            texts = [affs[n] for n in mk if n in affs]
            if not texts:
                rows.append([pmid, idx, r.last, tier, 'MARKER_UNRESOLVED', ';'.join(map(str, mk)),
                             r.primary_country, '', ''])
                continue
            pdf_c = [detect_country_segment(t)[0] for t in texts]
            pdf_c = [c for c in pdf_c if c]
            assigned = {x.strip() for x in re.split(r'\s*;\s*', str(r.all_countries)) if x.strip()}
            ok_c = (not pdf_c) or bool(set(pdf_c) & assigned)
            # institution check only for authors S2 treats as Saudi
            inst_assigned = inst_of.get((pmid, idx), '')
            pdf_i = ''
            ok_i = ''
            if inst_assigned:
                cands = [classify(t)[1] for t in texts if detect_country_segment(t)[0] == 'Saudi Arabia']
                pdf_i = ' | '.join(cands)
                if cands:
                    ok_i = 'MATCH' if inst_assigned in cands else 'MISMATCH'
            checked += 1
            flag = 'ok' if ok_c else 'COUNTRY_MISMATCH'
            if ok_i == 'MISMATCH':
                flag = 'INSTITUTION_MISMATCH' if ok_c else 'BOTH_MISMATCH'
            rows.append([pmid, idx, r.last, tier, flag, ';'.join(map(str, mk)),
                         r.primary_country, ' | '.join(pdf_c), '%s -> %s' % (inst_assigned, pdf_i) if inst_assigned else ''])
        pstat.append([pmid, tier, len(g), checked])

    R = pd.DataFrame(rows, columns=['PMID', 'author_index', 'last', 'tier', 'flag',
                                    'markers', 'assigned_country', 'pdf_country', 'institution'])
    P = pd.DataFrame(pstat, columns=['PMID', 'tier', 'n_authors', 'n_checked'])
    R.to_csv(f'{OUT}/08_23_2026_author_linkage_rows.csv', index=False, encoding='utf-8-sig')
    P.to_csv(f'{OUT}/08_23_2026_author_linkage_papers.csv', index=False, encoding='utf-8-sig')

    tot = len(L)
    print('papers: %d   authors: %d' % (P.PMID.nunique(), tot))
    print()
    print('--- paper parse tier ---')
    print(P.tier.value_counts().to_string())
    print()
    print('--- author rows ---')
    print(R.flag.value_counts().to_string())
    res = R[~R.flag.isin(['AUTHOR_NOT_LOCATED', 'MARKER_UNRESOLVED'])]
    print()
    print('AUTHORS ACTUALLY LINKED: %d of %d (%.1f%%)' % (len(res), tot, 100.0 * len(res) / tot))
    if len(res):
        agree = (res.flag == 'ok').sum()
        print('  linkage agrees with S1/S2: %d of %d = %.2f%%' % (agree, len(res), 100.0 * agree / len(res)))
    print()
    print('wrote', OUT)


if __name__ == '__main__':
    main()
