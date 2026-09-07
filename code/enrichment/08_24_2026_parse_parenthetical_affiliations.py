# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""Parse the "surname in parentheses" affiliation style, and VALIDATE it against the hand-read.

THE PROBLEM
-----------
[NAME-REDACTED] and [NAME-REDACTED] print ONE affiliation sentence for the whole byline and key
each author by surname in parentheses:

    "From the Department of Clinical [NAME-REDACTED] (Alghamdi), College of Medicine
     (Alshahrani, Alghamdi, Almohaini, Alsayat), Imam Mohammad Ibn Saud Islamic University,
     and from College of Medicine (Alharbi), King Saud University, Riyadh, Kingdom of Saudi
     Arabia."

PubMed hands that identical string to EVERY author, so the S2 builder collapses it to one
institution per author and never reads the keys. The 385-paper hand-read found this puts 12
authors on the wrong institution across 5 papers.

⚠ THE INSTITUTION IS NOT ALWAYS AFTER THE GROUP. Two orders occur:
    "... Department of Pediatrics (Names), King Abdulaziz Medical City ..."   <- after
    "... from King Abdullah International Medical Research Center (Names) ..." <- BEFORE
and a group may name no institution of its own, inheriting the next one downstream
(Alghamdi above belongs to Imam Mohammad Ibn Saud Islamic University, named two clauses
later). So resolution is: look forward to the next named institution before the following
group; else look backward within this clause; else scan forward past the next group.

This script only REPORTS. It writes nothing into S2. Run it, read the per-paper diff against
the hand-read, and only then decide whether the parser is trustworthy.

Run from the repository root.
"""
import io
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.join('code', 'lib'))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import saudi_institution_classifier as C          # noqa: E402
from country_matcher import SAUDI_CITIES          # noqa: E402

# A city name closes an address, so a group followed by one does not inherit the next
# institution downstream. "Kingdom of Saudi Arabia" ends the whole sentence and is not a
# terminator for an individual group, so it is deliberately absent here.
CITY_WORDS = list(SAUDI_CITIES)

CACHE = 'data/authors/07_25_2026_authors_cache_385.json'
HANDREAD = 'data/authors/08_23_2026_handread_author_affiliations.csv'
OUT = 'data/quality-control/08_24_2026_parenthetical_parse.csv'

# A surname group: "(Alghamdi)" or "(Alshahrani, Alghamdi, Almohaini, Alsayat)".
# Requires capitalised, mostly-alphabetic tokens so it does not match "(2022)" or "(n=45)".
PAREN = re.compile(r'\(([A-Z][A-Za-z\-’\'\. ]+(?:,\s*[A-Z][A-Za-z\-’\'\. ]+)*)\)')


def compact(s):
    return re.sub(r'[^a-z0-9]', '', str(s).lower())


def named_spans(text):
    """Every TIER-1/TIER-2 named institution in `text`, as (start, end, type, canon).

    Positions are located by finding each alias in the COMPACTED string and mapping back
    to the original, so alias matching stays identical to `classify()`.
    """
    comp, idx = [], []
    for i, ch in enumerate(text):
        c = ch.lower()
        if c.isalnum():
            comp.append(c)
            idx.append(i)
    comp = ''.join(comp)
    out = []
    for typ, canon, keys in list(C.TIER1) + list(C.TIER2):
        for k in keys:
            start = 0
            while True:
                p = comp.find(k, start)
                if p < 0:
                    break
                out.append((idx[p], idx[min(p + len(k) - 1, len(idx) - 1)], typ, canon))
                start = p + 1
    out.sort()
    # Drop a match fully contained in a longer one at the same place (alias overlap).
    keep = []
    for s in out:
        if not any(o[0] <= s[0] and s[1] <= o[1] and (o[1] - o[0]) > (s[1] - s[0]) for o in out):
            keep.append(s)
    return keep


def key(name):
    """Surname key tolerant of the ways the two sources spell the same person.

    PubMed's `last` and the printed parenthetical group disagree on spacing, case and
    stray initials -- "NourEldein"/"Nour Eldein", "ALOsaimi"/"Alosaimi", "Y Hakami"/
    "Hakami". Compacting to lowercase letters fixes the first two; the third needs the
    trailing token as well, so callers try both.
    """
    return re.sub(r'[^a-z]', '', str(name).lower())


def keys_of(name):
    toks = [t for t in re.split(r'[\s\.]+', str(name).strip()) if t]
    out = {key(name)}
    if len(toks) > 1:
        out.add(key(toks[-1]))          # leading initial: "Y Hakami" -> "hakami"
        # TRAILING initial, used to disambiguate two authors sharing a surname:
        # "(Alsergani, Alyamani, Aljohani M, Aljohani A, ...)" -> "aljohani".
        if len(toks[-1].strip('.')) == 1:
            out.add(key(' '.join(toks[:-1])))
    return {k for k in out if k}


def _window(aff, groups, insts, cities, semis, gi):
    """The span of `aff` that belongs to group `gi` -- ONE definition, used by both parse()
    and parse_blocks(). They had separate copies of this logic and drifted: parse() reported
    [NAME-REDACTED] for the wrong author of STUDY-0149 while parse_blocks() gave it to
    nobody. Two implementations of one rule is how that happens.

    A SEMICOLON IS A CLAUSE BOUNDARY and it outranks a group boundary. STUDY-0149 prints both
    orders in one sentence -- "From Plan and Research Department (Khogeer), General
    Directorate ..., Ministry of Health; From [NAME-REDACTED] (Shebly), Ministry of
    Health, Makkah" -- so Khogeer's span must stop at the ';' and Shebly's must start there,
    picking up the hospital printed BEFORE his key. The hand-read agrees on both authors.
    """
    gs, ge, _ = groups[gi]
    nxt = groups[gi + 1][0] if gi + 1 < len(groups) else len(aff)
    prv = groups[gi - 1][1] if gi > 0 else 0
    _ps = max([s for s in semis if s < gs], default=None)
    _ns = min([s for s in semis if s >= ge], default=None)
    cl_lo = _ps + 1 if (_ps is not None and _ps >= prv) else None
    cl_hi = _ns if (_ns is not None and _ns < nxt) else None
    if any(ge <= i[0] < nxt for i in insts):          # institution follows the names
        return (cl_lo if cl_lo is not None else gs, cl_hi if cl_hi is not None else nxt)
    if any(prv <= i[0] < gs for i in insts):          # institution precedes the names
        return (cl_lo if cl_lo is not None else prv, ge)
    if not any(ge <= c < nxt for c in cities):        # inherit downstream, no city in between
        return (gs, next((i[1] + 1 for i in insts if i[0] >= ge), len(aff)))
    return (gs, cl_hi if cl_hi is not None else nxt)  # own, unnamed address (city closes it)


def parse(aff, surnames=()):
    """-> {surname_key: [(type, canon), ...]} for one shared parenthetical affiliation string.

    `surnames` is the paper's author list. It is REQUIRED to tell this style apart from
    parenthesised acronyms: STUDY-0852 prints "…King Saud Bin Abdul Aziz University for Health
    Sciences (KSAU-HS), King Abdulaziz Medical City… | King Abdullah International Medical
    Research Centre (KAIMRC), National Guard Health Affairs (NGHA)…" — three parenthetical
    groups, none of them names. Firing on that paper would have rewritten five authors from
    a plain two-block affiliation. So: unless the groups actually match author surnames,
    this is not the parenthetical-key style and the parser declines.
    """
    groups = [(m.start(), m.end(), [n.strip() for n in m.group(1).split(',') if n.strip()])
              for m in PAREN.finditer(aff)]
    if len(groups) < 2:
        return {}
    want = {k for s in surnames for k in keys_of(s)}
    matched = {k for _, _, names in groups for n in names for k in keys_of(n)} & want
    if len(matched) < 2:
        return {}
    insts = named_spans(aff)
    cities = [m.start() for c in CITY_WORDS
              for m in re.finditer(r'\b' + re.escape(c) + r'\b', aff, re.I)]
    semis = [m.start() for m in re.finditer(r';', aff)]
    res = {}
    for gi, (gs, ge, names) in enumerate(groups):
        # EVERY named institution inside this group's own span -- not just the first: one
        # clause routinely names the whole National Guard trio (KAMC + KAIMRC + KSAU-HS)
        # and the author genuinely holds all three. The span itself, including the city
        # guard that stops a group inheriting an institution downstream, is _window().
        lo, hi = _window(aff, groups, insts, cities, semis, gi)
        cand = [i for i in insts if lo <= i[0] < hi]
        for n in names:
            for k in keys_of(n):
                res.setdefault(k, [])
                for c in cand:
                    v = (c[2], c[3])
                    if v not in res[k]:
                        res[k].append(v)
    return res


def parse_blocks(aff, surnames=()):
    """-> {surname_key: affiliation TEXT for that author}.

    This is what the S2 builder consumes. It deliberately returns the author's slice of the
    shared sentence rather than a classified institution, so `classify()` keeps deciding
    WHICH institution wins exactly as it does everywhere else. The parser's only job is to
    stop an author being handed a slice that belongs to somebody else.
    """
    groups = [(m.start(), m.end(), [n.strip() for n in m.group(1).split(',') if n.strip()])
              for m in PAREN.finditer(aff)]
    if len(groups) < 2:
        return {}
    want = {k for s in surnames for k in keys_of(s)}
    if len({k for _, _, names in groups for n in names for k in keys_of(n)} & want) < 2:
        return {}
    insts = named_spans(aff)
    cities = [m.start() for c in CITY_WORDS
              for m in re.finditer(r'\b' + re.escape(c) + r'\b', aff, re.I)]
    # A SEMICOLON IS A CLAUSE BOUNDARY, and it is stronger than a group boundary.
    # STUDY-0149 prints both orders in one sentence:
    #   "… From Plan and Research Department (Khogeer), General Directorate …, Ministry of
    #    Health; From [NAME-REDACTED] (Shebly), Ministry of Health, Makkah …"
    # Without this, Khogeer's slice ran forward to Shebly's key and swallowed "; From Ajyad
    # Emergency Hospital" -- an institution that is Shebly's -- while Shebly's slice started
    # at his own key and never saw it. Clipping each slice to its own semicolon-delimited
    # clause gives the phrase to the author it belongs to, in either order.
    semis = [m.start() for m in re.finditer(r';', aff)]
    out = {}
    for gi, (gs, ge, names) in enumerate(groups):
        lo, hi = _window(aff, groups, insts, cities, semis, gi)
        seg = aff[lo:hi].strip(' ,;.')
        for n in names:
            for k in keys_of(n):
                prev = out.get(k, '')
                out[k] = (prev + ' ; ' + seg).strip(' ;') if prev and seg not in prev else (prev or seg)
    return out


def main():
    cache = json.load(open(CACHE, encoding='utf-8'))
    hr = pd.read_csv(HANDREAD, encoding='utf-8-sig')
    hr['verbatim'] = hr.verbatim.fillna('')

    rows, papers = [], 0
    agree = disagree = 0
    for pmid, rec in cache.items():
        auths = rec['authors'] if isinstance(rec, dict) and 'authors' in rec else rec
        affs = {(a.get('aff') or '') for a in auths if (a.get('aff') or '').strip()}
        if len(affs) != 1:
            continue
        aff = next(iter(affs))
        got = parse(aff, [(a.get("last") or "") for a in auths])
        if not got:
            continue
        papers += 1
        print('=' * 104)
        print(f'PMID {pmid}  ({len(auths)} authors)')
        for i, a in enumerate(auths, 1):
            last = (a.get('last') or '').strip()
            mine = next((got[k] for k in keys_of(last) if k in got), None)
            # what the hand-read recorded for this author, classified the same way
            v = [x for x in hr[(hr.PMID == int(pmid)) & (hr.author_index == i)].verbatim if x.strip()]
            read = []
            for x in v:
                t, canon, _ = C.classify(x)
                if (t, canon) not in read:
                    read.append((t, canon))
            read_s = {c for _, c in read}
            mine_s = {c for _, c in (mine or [])}
            if mine is None:
                verdict = 'no-group'
            elif not read_s:
                verdict = 'no-handread'
            elif mine_s & read_s:
                verdict = 'OK'
                agree += 1
            else:
                verdict = '*** DIFFERS ***'
                disagree += 1
            ps = '; '.join(sorted(mine_s)) or '-'
            rs = '; '.join(sorted(read_s)) or '-'
            print(f'  idx{i:<3} {last:<20} parser={ps:<52} handread={rs:<52} {verdict}')
            rows.append({'PMID': pmid, 'author_index': i, 'last': last,
                         'parser': '; '.join(sorted(mine_s)),
                         'handread': '; '.join(sorted(read_s)), 'verdict': verdict})

    pd.DataFrame(rows).to_csv(OUT, index=False, encoding='utf-8-sig')
    print()
    print(f'papers parsed: {papers}')
    print(f'authors where parser and hand-read overlap : {agree}')
    print(f'authors where they DISAGREE                : {disagree}')
    print(f'-> {OUT}')


if __name__ == '__main__':
    main()
