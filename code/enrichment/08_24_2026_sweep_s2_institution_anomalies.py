# NOTE (public repository): 9 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Systematic sweep of S2 (Saudi author-appearance -> INSTITUTION) for attribution errors.

WHY THIS EXISTS
---------------
08_24_2026_sweep_s1_s2_anomalies.py swept S1, i.e. COUNTRY. S2 asserts something strictly
harder -- WHICH Saudi institution each author belongs to -- and its two proven failure modes
were both invisible to the checks in place at the time:

  * the parenthetical-key bug ([NAME-REDACTED] house style): one shared affiliation sentence,
    authors keyed by surname in parentheses, S2 collapsing it to one institution for
    everybody. Paper-level containment scored S2 at 100% throughout, because the recorded
    institution really was named on the paper -- just not for those authors.
  * "Center for Outcomes Research in Liver Disease": a Washington DC entity recorded as a
    Saudi research centre, because PubMed's own string is corrupt.

Both are now fixed. The question this sweep answers is the same one the S1 sweep answered
for Fanikos: HOW MANY MORE ARE THERE? Each screen is built so that it can be run against
the PRE-FIX backup of S2, where the answer is known, before it is believed on live data.

TWELVE SCREENS, all computable from data already on disk. None is proof; each produces
CANDIDATES. Nothing here writes to S1 or S2. Full write-up and verdicts:
docs/provenance/08_24_2026_S2_institution_sweep.md

  A1 SHARED-STRING, MULTI-INSTITUTION      the parenthetical signature, generalised: every
                                           author on the paper shares ONE affiliation string
                                           that names >=2 Saudi institutions, and S2 hands
                                           them all the same one. Linkage is unknowable from
                                           the string alone -- unless keys are printed (A2).
  A2 KEYS PRINTED BUT NOT USED             that string carries parenthesised groups matching
                                           author surnames, yet the parser declined it.
  A3 INHERITED ATTRIBUTION                 the author's own keyed clause names no institution,
                                           so what S2 records was inherited from a neighbour
                                           (STUDY-0161 Almwled). NOT a multi-institution case,
                                           which is why A1 cannot see it.
  B  MULTI-INSTITUTION AUTHOR              the author's own affiliation names >=2 Saudi
                                           institutions; S2 has one slot. Quantifies the
                                           structural cap (the STUDY-0442 AlShomar case).
  C  RECOMPUTE / STALENESS                 re-derive every row from the author cache with the
                                           live classifier and diff against what S2 stores.
                                           Catches a stale CSV or an undocumented override.
  D  ALIAS NEAR-MISS                       the block names something that LOOKS like a
                                           curated institution but misses the alias list
                                           (STUDY-0928's "King Abdula Aziz University").
  D2 NAMED FACILITY UNDER AN UMBRELLA      the block names a specific facility with no Tier-1
                                           alias, so the row takes an umbrella name AND the
                                           umbrella's sector ("Ministry of Health").
  E  FOREIGN TEXT INSIDE A SAUDI BLOCK     the CORLD signature: the block that produced a
                                           Saudi institution also names a foreign country.
  E2 TWO COUNTRIES IN ONE SEGMENT          corpus-wide: the rightmost-country rule keeps one.
  E3 SAUDI INSTITUTION, FOREIGN COUNTRY    the Abdelwahid signature; the only direction that
                                           can ADD Saudi authors.
  F  CITY INSTABILITY                      one canonical institution recorded in >1 city.
  F2 CITY FROM AN EMAIL ADDRESS            extract_city() scans the whole block with rfind(),
                                           so a city inside an address wins on position.
  G  TYPE INSTABILITY                      one canonical institution recorded with >1 sector.
  H  CROSS-PAPER CONTRADICTION             the same person at different Saudi institutions on
                                           different papers.
  I  WEAK CLASSIFICATION INVENTORY         every row not resolved by a Tier-1 named entry.

Run from the repository root:
    PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python code/enrichment/08_24_2026_sweep_s2_institution_anomalies.py
"""
import difflib
import io
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

try:                                   # several blocks below print non-cp1252 characters
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join('code', 'lib'))
sys.path.insert(0, os.path.join('code', 'enrichment'))

from country_matcher import COUNTRY_VARIANTS, detect_country_segment  # noqa: E402
import saudi_institution_classifier as SIC                            # noqa: E402

_map = __import__('07_25_2026_map_saudi_institutions')
extract_city = _map.extract_city
first_saudi_block = _map.first_saudi_block
names_institution = _map.names_institution
CORRESPONDENCE_CITY = _map.CORRESPONDENCE_CITY
_pp = __import__('08_24_2026_parse_parenthetical_affiliations')
parse_blocks, keys_of = _pp.parse_blocks, _pp.keys_of

S2_LIVE = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
S2_PREFIX = 'data/authors/_pre_handread_backup_07_25_2026_saudi_affiliation_long.csv'
S1 = 'data/authors/07_25_2026_author_country_long.csv'
CACHE = 'data/authors/07_25_2026_authors_cache_385.json'
OUT = 'data/quality-control/08_24_2026_s2_sweep_candidates.csv'

# ---------------------------------------------------------------------------------------
# alias machinery -- ask the same question classify() asks, never a looser string match
# ---------------------------------------------------------------------------------------
ALIASES = ([(c, t, a) for t, c, al in SIC.TIER1 for a in al] +
           [(c, t, a) for t, c, al in SIC.TIER2 for a in al])
# The Tier-2 catch-all 'ministryof' is a substring of every spelled-out ministry; span
# containment (below) removes it, but it is also never an institution NAME in its own right.
GENERIC_CANON = {'General government / ministry'}


def _s(x):
    """Blank for NaN/None -- pandas hands float('nan') to these helpers for empty cells."""
    if x is None or (isinstance(x, float) and x != x):
        return ''
    return str(x)


def alias_hits(text):
    """Every curated institution alias occurring in `text`, with contained spans removed.

    Containment matters: 'ministryof' sits inside 'ministryofhealth', 'shaqra' inside
    'shaqrauniversity'. Without the filter a single institution counts as two and the
    multi-institution screens fill with noise.
    """
    c = SIC._compact(_s(text))
    raw = []
    for canon, typ, a in ALIASES:
        start = 0
        while True:
            i = c.find(a, start)
            if i < 0:
                break
            raw.append((i, i + len(a), typ, canon))
            start = i + 1
    keep = []
    for h in raw:
        if any(g is not h and g[0] <= h[0] and g[1] >= h[1] and (g[1] - g[0]) > (h[1] - h[0])
               for g in raw):
            continue
        keep.append(h)
    return keep


def named_canons(text):
    """Ordered-unique canonical institutions named in `text`."""
    out = []
    for _, _, _, canon in sorted(alias_hits(text)):
        if canon not in out and canon not in GENERIC_CANON:
            out.append(canon)
    return out


TIER1_CANONS = {c for t, c, al in SIC.TIER1}


def named_canons_t1(text):
    """Only TIER-1 named institutions. Tier 2 is umbrella ministries -- "Ministry of Health"
    is as much an Egyptian phrase as a Saudi one, so it cannot carry a country claim."""
    return [c for c in named_canons(text) if c in TIER1_CANONS]


def norm_person(last, fore):
    def n(s):
        s = unicodedata.normalize('NFKD', str(s or ''))
        s = ''.join(ch for ch in s if not unicodedata.combining(ch))
        return re.sub(r'[^a-z]', '', s.lower())
    return n(last) + '|' + n(fore)[:6]


_FOREIGN = []
for _country, _vars in COUNTRY_VARIANTS.items():
    if _country == 'Saudi Arabia':
        continue
    for _v in _vars:
        if len(re.sub(r'\\|\W', '', _v)) < 4:      # 'uk', 'usa' etc. are too collision-prone
            continue
        _FOREIGN.append((_country, re.compile(r'\b' + _v + r'\b', re.I)))


# A country name is not the only foreign marker, and in the one proven case it was absent:
# CORLD's block reads "... Washington District of Columbia, Riyadh, Saudi Arabia" -- a US
# PLACE, no country word anywhere. So the screen also carries US state names and the curated
# foreign cities.
from country_matcher import CITY_COUNTRY, US_STATES_FULL  # noqa: E402

_FOREIGN_PLACE = [('United States', 'US: ' + s, re.compile(r'\b' + re.escape(s) + r'\b', re.I))
                  for s in list(US_STATES_FULL) + ['district of columbia']]
_FOREIGN_PLACE += [(c, c + ' (' + city + ')', re.compile(r'\b' + re.escape(city) + r'\b', re.I))
                   for city, c in CITY_COUNTRY.items()]

_SAUDI_RX = re.compile(r'\b(saudi arabia|kingdom of saudi arabia|saudia arabia|saudi araba|'
                       r'saudi arbia|k\.?s\.?a\.?)\b', re.I)


def foreign_hits(text):
    """(country, human-readable marker) for every foreign marker in `text`.

    WARNING: countries and places must resolve to the SAME key. A first cut kept 'Australia'
    and 'Australia (sydney)' as two separate markers, so "University of Sydney, Sydney,
    Australia" looked like a two-country segment and screen E2 filled with 170 rows of that
    noise. The COUNTRY is what the screens reason about; the marker is only for evidence.
    """
    n = re.sub(r'\s+', ' ', _s(text))
    hits = [(c, c) for c, rx in _FOREIGN if rx.search(n)]
    hits += [(c, lbl) for c, lbl, rx in _FOREIGN_PLACE if rx.search(n)]
    return hits


def foreign_countries(text):
    return sorted({c for c, _ in foreign_hits(text)})


def foreign_markers(text):
    return sorted({lbl for _, lbl in foreign_hits(text)})



# Phrases worth fuzzy-matching against the curated list (screen D)
_INST_WORD = re.compile(
    r'universit|college|hospital|medical city|medical complex|medical cent|research cent'
    r'|institute|clinic|polyclinic|ministry|authority|council|commission|centre|center', re.I)


def near_miss(block, recorded):
    """Institution-shaped phrases in `block` that RESOLVE TO NOTHING yet closely resemble a
    curated canonical name. Returns (phrase, canon, ratio) or None.

    ⚠ The segment must itself be unresolved. A first cut compared every institution-shaped
    segment against every alias and produced 64 rows of pure noise -- "Taif University" is
    0.897 similar to "Taibah University", "King Abdulaziz Medical City" 0.894 to "King
    Abdullah Medical City". Those are DIFFERENT REAL INSTITUTIONS that the classifier already
    told apart correctly. The only interesting case is a phrase the alias list cannot place at
    all, which is exactly what a misspelling produces.
    """
    hit_canons = set(named_canons(block))
    best = None
    for seg in re.split(r'[,;|]', _s(block)):
        seg = seg.strip()
        if len(seg) < 8 or not _INST_WORD.search(seg):
            continue
        if named_canons(seg):
            continue                      # the segment already resolves -- nothing to recover
        cseg = SIC._compact(seg)
        for canon, typ, a in ALIASES:
            if canon in hit_canons or canon in GENERIC_CANON:
                continue
            r = difflib.SequenceMatcher(None, cseg, a).ratio()
            if r >= 0.88 and (best is None or r > best[2]):
                best = (seg, canon, round(r, 3))
    if best and best[1] != recorded:
        return best
    return None


# ---------------------------------------------------------------------------------------
# screens
# ---------------------------------------------------------------------------------------
def run_screens(s2, cache, s1, label, screens=None):
    """Run the screens over one vintage of S2. Returns a list of candidate dicts."""
    rows = []
    want = (lambda s: screens is None or s in screens)
    reals = {str(p): [a for a in au if a.get('last', '').strip()] for p, au in cache.items()}
    s2 = s2.copy()
    s2['PMID'] = s2.PMID.astype(str)

    # ---------------- A1 / A2: shared string, multiple institutions ----------------
    if want('A'):
        for pmid, g in s2.groupby('PMID'):
            auth = reals.get(pmid, [])
            affs = {(a.get('aff') or '').strip() for a in auth if (a.get('aff') or '').strip()}
            if len(affs) != 1:
                continue                        # per-author strings: linkage is not at risk
            shared = next(iter(affs))
            canons = named_canons(shared)
            recorded = sorted(set(g.institution))
            keyed = set(g.source) & {'paper-parenthetical', 'paper-correspondence'}
            surnames = [a.get('last', '') for a in auth]
            parsed = parse_blocks(shared, surnames) or {}

            # A3: the author's OWN keyed clause names no institution at all, so whatever S2
            # records for them was inherited from someone else's clause. This is the
            # STUDY-0161 Almwled signature ("Administration of mental health (Almwled),
            # Makkah, ... King Saud University"), and it is NOT a multi-institution case --
            # only one curated institution appears in the whole string -- so A1 cannot see
            # it. Runs before the >=2 gate for exactly that reason.
            if parsed:
                for _, r in g.iterrows():
                    slice_text = next((parsed[k] for k in keys_of(str(r.last)) if k in parsed),
                                      None)
                    if slice_text is None or named_canons(slice_text):
                        continue
                    if not canons:
                        continue            # nothing to inherit; the string names nobody
                    rows.append({
                        'screen': 'A3_inherited_attribution', 'PMID': pmid,
                        'author_index': r.author_index, 'last': r.last,
                        'recorded': f'{r.institution} (source={r.source})',
                        'evidence': f'own clause: "{slice_text[:80]}"',
                        'why': 'this author\'s own parenthetical clause names no institution; '
                               'the recorded one comes from elsewhere in the shared string',
                        'priority': 1})

            if len(canons) < 2:
                continue
            if len(g) >= 2 and len(recorded) == 1 and not keyed:
                rows.append({
                    'screen': 'A1_shared_string_multi_inst', 'PMID': pmid, 'author_index': '',
                    'last': f'{len(g)} Saudi authors', 'recorded': recorded[0],
                    'evidence': ' | '.join(canons),
                    'why': f'one shared affiliation string names {len(canons)} Saudi '
                           f'institutions; all {len(g)} Saudi authors recorded at the same one '
                           f'and no per-author key was used',
                    'priority': 1})
            if parsed and not keyed:
                rows.append({
                    'screen': 'A2_keys_printed_not_used', 'PMID': pmid, 'author_index': '',
                    'last': f'{len(g)} Saudi authors', 'recorded': '; '.join(recorded),
                    'evidence': '; '.join(f'{k}->{v[:60]}' for k, v in list(parsed.items())[:4]),
                    'why': 'the shared string carries parenthesised surname keys the build did '
                           'not use for these rows',
                    'priority': 1})

    # ---------------- B: author holds >=2 Saudi institutions ----------------
    if want('B'):
        for r in s2.itertuples():
            auth = reals.get(r.PMID, [])
            if r.author_index - 1 >= len(auth):
                continue
            aff = auth[r.author_index - 1].get('aff') or ''
            saudi_parts = [b for b in re.split(r'\s*[|;]\s*', aff)
                           if detect_country_segment(b)[0] == 'Saudi Arabia']
            canons = named_canons(' | '.join(saudi_parts))
            if len(canons) >= 2:
                rows.append({
                    'screen': 'B_multi_institution_author', 'PMID': r.PMID,
                    'author_index': r.author_index, 'last': r.last, 'recorded': r.institution,
                    'evidence': ' | '.join(canons),
                    'why': f'this author\'s own Saudi affiliation text names {len(canons)} '
                           f'institutions; S2 records one',
                    'priority': 2})

    # ---------------- C: recompute from the cache with the live classifier ----------------
    if want('C'):
        for r in s2.itertuples():
            auth = reals.get(r.PMID, [])
            if r.author_index - 1 >= len(auth):
                rows.append({'screen': 'C_recompute', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': r.institution, 'evidence': 'author index past cache',
                             'why': 'S2 row has no counterpart in the author cache',
                             'priority': 1})
                continue
            aff = auth[r.author_index - 1].get('aff') or ''
            src = r.source
            if src == 'manual-context':
                continue                        # by construction not derivable from the text
            block = str(r.saudi_block or '')
            if src == 'pubmed-affil':
                fresh_block = first_saudi_block(aff) or ''
                if SIC._compact(fresh_block) != SIC._compact(block):
                    rows.append({'screen': 'C_recompute', 'PMID': r.PMID,
                                 'author_index': r.author_index, 'last': r.last,
                                 'recorded': block[:90], 'evidence': fresh_block[:90],
                                 'why': 'stored saudi_block differs from the block the cache '
                                        'yields now (stale CSV or changed splitter)',
                                 'priority': 1})
                    continue
            typ, inst, tier = SIC.classify(block)
            if src == 'paper-parenthetical':
                # replicate the build's MINIMAL CHANGE rule exactly
                whole = first_saudi_block(aff)
                if whole:
                    o_typ, o_inst, o_tier = SIC.classify(whole)
                    if o_inst != inst and names_institution(block, o_inst):
                        typ, inst, tier = o_typ, o_inst, o_tier
            if (inst, typ, tier) != (r.institution, r.inst_type, r.tier):
                rows.append({'screen': 'C_recompute', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': f'{r.institution} / {r.inst_type} / tier{r.tier}',
                             'evidence': f'{inst} / {typ} / tier{tier}',
                             'why': f'live classifier disagrees with the stored row '
                                    f'(source={src})',
                             'priority': 1})
                continue
            # city, with the two documented fallbacks
            city = extract_city(block) if block else 'Unspecified'
            if city == 'Unspecified' and src == 'paper-parenthetical':
                city = extract_city(first_saudi_block(aff) or aff or '')
            if city in ('Unspecified', '', None) and (r.PMID, r.author_index) in CORRESPONDENCE_CITY:
                city = CORRESPONDENCE_CITY[(r.PMID, r.author_index)]
            if (city or 'Unspecified') != r.city:
                rows.append({'screen': 'C_recompute', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': f'city={r.city}', 'evidence': f'city={city}',
                             'why': 'stored city differs from the recomputed one',
                             'priority': 2})

    # ---------------- D: alias near-miss ----------------
    if want('D'):
        seen = set()
        for r in s2.itertuples():
            key = (SIC._compact(str(r.saudi_block))[:120], r.institution)
            if key in seen:
                continue
            seen.add(key)
            nm = near_miss(r.saudi_block, r.institution)
            if nm:
                rows.append({'screen': 'D_alias_near_miss', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': r.institution,
                             'evidence': f'"{nm[0][:70]}" ~ {nm[1]} ({nm[2]})',
                             'why': 'block names something within one or two characters of a '
                                    'curated institution but matches no alias',
                             'priority': 2})

    # ---------------- D2: a NAMED facility recorded under an umbrella ----------------
    # The 2026-08-23 finding was that rows printing "(hospital/clinic, unnamed)" were never
    # unnamed -- the names were simply absent from Tier 1. The same thing can happen one tier
    # up and it is worse there: an unmatched hospital name inside a block that also carries a
    # Ministry-of-Health badge resolves to "Ministry of Health", which changes the SECTOR as
    # well as the name, and the sector feeds Table 1. Screen D only catches names that
    # RESEMBLE a curated entry; this one catches names with no curated neighbour at all.
    if want('D2'):
        _DEPT = re.compile(r'^(department|dept|division|administration|deputyship|unit|'
                           r'general directorate|directorate|section|programme|program|'
                           r'college|faculty|school|chair|research department)\b', re.I)
        _FACILITY = re.compile(r'hospital|medical cent|medical complex|medical city|clinic|'
                               r'health cent|dental cent|polyclinic|institute', re.I)
        for r in s2[s2.tier >= 2].itertuples():
            for seg in re.split(r'[,;|]', _s(r.saudi_block)):
                seg = seg.strip()
                if len(seg) < 8 or _DEPT.match(seg) or not _FACILITY.search(seg):
                    continue
                if named_canons(seg):
                    continue
                rows.append({
                    'screen': 'D2_named_facility_under_umbrella', 'PMID': r.PMID,
                    'author_index': r.author_index, 'last': r.last,
                    'recorded': f'{r.institution} / {r.inst_type} (tier {r.tier})',
                    'evidence': f'block names "{seg}"',
                    'why': 'the block names a specific facility that matches no Tier-1 alias, '
                           "so the row carries an umbrella name and the umbrella's sector",
                    'priority': 1})

    # ---------------- E: foreign country named inside the Saudi block ----------------
    if want('E'):
        for r in s2.itertuples():
            fc = foreign_markers(r.saudi_block)
            if fc:
                rows.append({'screen': 'E_foreign_text_in_block', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': r.institution, 'evidence': '; '.join(fc),
                             'why': 'the block that produced this Saudi institution also names '
                                    'a foreign country (the CORLD signature)',
                             'priority': 1})

    # ---------------- E2: two countries inside ONE unsplit segment, corpus-wide ----------
    # Screen E turned up two blocks that name a foreign university and a Saudi one joined by
    # the word "and", with no '|' or ';' between them. detect_country_segment() takes the
    # RIGHTMOST country, so one of the two is silently dropped. Which one is dropped decides
    # whether the miss costs a foreign appearance (harmless to the Saudi count) or a SAUDI
    # one (STUDY-0519 Abdelwahid -- a real, corrected error). This runs the check over every
    # author in the corpus, not just the ones S2 already contains.
    if want('E2'):
        for pmid, auth in reals.items():
            for i, a in enumerate(auth, start=1):
                for seg in re.split(r'\s*[|;]\s*', a.get('aff') or ''):
                    if len(seg.strip()) < 10:
                        continue
                    marks = set(foreign_countries(seg))   # canonical countries, deduped
                    saudi_here = bool(_SAUDI_RX.search(seg))
                    if len(marks) + (1 if saudi_here else 0) < 2:
                        continue
                    resolved = detect_country_segment(seg)[0]
                    if saudi_here and resolved != 'Saudi Arabia':
                        kind, prio = 'SAUDI DROPPED', 1
                    elif resolved == 'Saudi Arabia':
                        kind, prio = 'foreign appearance dropped', 2
                    else:
                        kind, prio = 'two foreign markers', 3
                    rows.append({
                        'screen': 'E2_two_countries_one_segment', 'PMID': pmid,
                        'author_index': i, 'last': a.get('last', ''),
                        'recorded': f'resolved -> {resolved}',
                        'evidence': f'{kind}: markers {sorted(marks | ({"Saudi Arabia"} if saudi_here else set()))} '
                                    f'in "{seg.strip()[:110]}"',
                        'why': 'one affiliation segment names more than one country; the '
                               'rightmost-country rule keeps only one of them',
                        'priority': prio})

    # ---------------- E3: a Saudi institution named, but the segment resolves FOREIGN ----
    # The Abdelwahid signature, and the one direction that can only ADD Saudi authors.
    # STUDY-0519: "[NAME-REDACTED] (JAFH), Suez Canal University, Ismailia, Egypt."
    # -- one segment, two institutions, one country word, and the country word is the wrong
    # one. E2 cannot see it: no Saudi country marker appears anywhere in the segment, so
    # there is nothing for a country-vs-country comparison to compare. What IS there is a
    # curated Saudi institution sitting in a segment the matcher calls foreign.
    if want('E3'):
        s1_saudi = {(str(p), int(i)) for p, i, ac in
                    zip(s1.PMID, s1.author_index, s1.all_countries.fillna(''))
                    if 'Saudi Arabia' in ac}
        for pmid, auth in reals.items():
            for i, a in enumerate(auth, start=1):
                for seg in re.split(r'\s*[|;]\s*', a.get('aff') or ''):
                    if len(seg.strip()) < 10:
                        continue
                    t1 = named_canons_t1(seg)
                    if not t1:
                        continue
                    resolved = detect_country_segment(seg)[0]
                    if resolved == 'Saudi Arabia':
                        continue
                    already = (pmid, i) in s1_saudi
                    rows.append({
                        'screen': 'E3_saudi_institution_foreign_country', 'PMID': pmid,
                        'author_index': i, 'last': a.get('last', ''),
                        'recorded': f'S1 resolves -> {resolved}'
                                    + ('  [author already Saudi via another block]' if already
                                       else '  [NOT Saudi in S1]'),
                        'evidence': f'{" | ".join(t1)} in "{seg.strip()[:110]}"',
                        'why': 'a curated Saudi institution is named in a segment the country '
                               'matcher resolves to a foreign country',
                        'priority': 3 if already else 1})

    # ---------------- F2: city taken from inside an email address ----------------------
    # extract_city() scans the whole block with rfind(), so any city name occurring inside an
    # EMAIL wins on position -- the documented substring trap that once matched "Arabi" inside
    # drarabie@ksmc.med.sa. Re-extract with addresses stripped and diff.
    if want('F2'):
        for r in s2.itertuples():
            block = _s(r.saudi_block)
            if '@' not in block:
                continue
            stripped = re.sub(r'\S+@\S+', ' ', block)
            fresh = extract_city(stripped) if stripped.strip() else 'Unspecified'
            if fresh != r.city:
                rows.append({
                    'screen': 'F2_city_from_email', 'PMID': r.PMID,
                    'author_index': r.author_index, 'last': r.last,
                    'recorded': f'city={r.city}', 'evidence': f'without the email address: '
                                f'city={fresh}  |  block: {block[:120]}',
                    'why': 'the recorded city is only present inside an email address',
                    'priority': 1})

    # ---------------- F / G: one institution, several cities / sectors ----------------
    if want('F'):
        for inst, g in s2.groupby('institution'):
            cities = sorted({c for c in g.city if c and c != 'Unspecified'})
            if len(cities) > 1:
                rows.append({'screen': 'F_city_instability', 'PMID': '',
                             'author_index': '', 'last': f'{len(g)} rows', 'recorded': inst,
                             'evidence': '; '.join(f'{c}={n}' for c, n in
                                                   Counter(g.city).most_common()),
                             'why': f'recorded in {len(cities)} cities',
                             'priority': 3})
    if want('G'):
        for inst, g in s2.groupby('institution'):
            types = sorted(set(g.inst_type))
            if len(types) > 1:
                rows.append({'screen': 'G_type_instability', 'PMID': '', 'author_index': '',
                             'last': f'{len(g)} rows', 'recorded': inst,
                             'evidence': '; '.join(types),
                             'why': 'the same institution name carries more than one sector',
                             'priority': 1})

    # ---------------- H: same person, different institution across papers ----------------
    if want('H'):
        s2['person'] = [norm_person(a, b) for a, b in zip(s2.last, s2.fore)]
        for person, g in s2[s2.person.str.len() > 3].groupby('person'):
            if g.PMID.nunique() < 2 or g.institution.nunique() < 2:
                continue
            for r in g.itertuples():
                rows.append({'screen': 'H_cross_paper', 'PMID': r.PMID,
                             'author_index': r.author_index, 'last': r.last,
                             'recorded': r.institution,
                             'evidence': '; '.join(f'{p}:{i}' for p, i in
                                                   zip(g.PMID, g.institution)),
                             'why': f'same name on {g.PMID.nunique()} papers at '
                                    f'{g.institution.nunique()} different institutions',
                             'priority': 2})

    # ---------------- I: weak classifications ----------------
    if want('I'):
        for r in s2[s2.tier != 1].itertuples():
            rows.append({'screen': 'I_weak_classification', 'PMID': r.PMID,
                         'author_index': r.author_index, 'last': r.last,
                         'recorded': f'{r.institution} (tier {r.tier})',
                         'evidence': str(r.saudi_block)[:90],
                         'why': 'not resolved to a curated Tier-1 named institution',
                         'priority': 3})

    for row in rows:
        row['vintage'] = label
    return rows


def main():
    cache = json.load(open(CACHE, 'r', encoding='utf-8'))
    s1 = pd.read_csv(S1, encoding='utf-8-sig')
    live = pd.read_csv(S2_LIVE, encoding='utf-8-sig')

    print('=' * 92)
    print('S2 INSTITUTION SWEEP')
    print('=' * 92)
    print(f'live S2: {len(live)} rows, {live.PMID.nunique()} papers, '
          f'{live.institution.nunique()} institutions')

    # ---- validation: do the screens recover the KNOWN errors in the pre-fix vintage? ----
    val = None
    if os.path.exists(S2_PREFIX):
        pre = pd.read_csv(S2_PREFIX, encoding='utf-8-sig')
        val = run_screens(pre, cache, s1, 'pre-fix', screens={'A', 'E'})
        known = {'STUDY-0952', 'STUDY-0630', 'STUDY-0149', 'STUDY-0320', 'STUDY-0161'}
        flagged = {r['PMID'] for r in val if r['screen'].startswith('A')}
        print(f'\nVALIDATION against the pre-fix backup ({len(pre)} rows)')
        print(f'  screen A flags {len(flagged)} papers: {sorted(flagged)}')
        print(f'  of the 5 papers the hand-read proved wrong, recovered: '
              f'{sorted(known & flagged)}  ({len(known & flagged)}/5)')
        print(f'  missed: {sorted(known - flagged)}')
        e_pre = [r for r in val if r['screen'] == 'E_foreign_text_in_block']
        print(f'  screen E flags {len(e_pre)} rows pre-fix '
              f'(CORLD/STUDY-0821 present: '
              f'{any(r["PMID"] == "STUDY-0821" for r in e_pre)})')

    rows = run_screens(live, cache, s1, 'live')
    out = pd.DataFrame(rows)
    if len(out):
        out = out.sort_values(['priority', 'screen', 'PMID', 'author_index'])
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        out.to_csv(OUT, index=False, encoding='utf-8-sig')

    print(f'\n{len(out)} candidate rows -> {OUT}\n')
    print(out.screen.value_counts().to_string())

    for s in ['A1_shared_string_multi_inst', 'A2_keys_printed_not_used',
              'A3_inherited_attribution', 'C_recompute',
              'E2_two_countries_one_segment', 'E3_saudi_institution_foreign_country',
              'D2_named_facility_under_umbrella', 'F2_city_from_email',
              'D_alias_near_miss', 'E_foreign_text_in_block', 'G_type_instability',
              'B_multi_institution_author', 'H_cross_paper', 'F_city_instability']:
        sub = out[out.screen == s] if len(out) else pd.DataFrame()
        print(f'\n===== {s}: {len(sub)} rows =====')
        for _, r in sub.iterrows():
            head = f'{r.PMID} idx{r.author_index} {r.last}'.strip()
            print(f'  {head}: {r.recorded}')
            print(f'      {r.why}')
            if r.evidence:
                print(f'      evidence: {r.evidence}')
    if len(out):
        i = out[out.screen == 'I_weak_classification']
        print(f'\n===== I_weak_classification: {len(i)} rows =====')
        print(i.recorded.value_counts().to_string() if len(i) else '  none')


if __name__ == '__main__':
    main()
