# NOTE (public repository): 12 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""
Map the countries of every author across the 385 included papers (and the 377 analysis set).

Primary source  : data/authors/pubmed_authors_cache.json (PubMed E-utilities author + affiliation blocks)
Classifier       : country_matcher.detect_country  (rightmost-country-per-block; primary = first block)
Enrichment       : gold PDF-verified notes in data/authors/07_16_2026_saudi_affiliation_variables.xlsx
                   for the 51 authors PubMed left without an affiliation (7 papers), plus 3
                   truncated-fragment authors resolved from within-paper institutional context.

Validation       : reproduces the gold "any_saudi_author" flag 385/385.

Outputs (project dir):
  data/authors/07_25_2026_author_country_long.csv      one row per author-appearance (pmid x author)
  data/authors/07_25_2026_country_counts.csv           country x {author-appearances, first, last, corr, papers}
  data/authors/07_25_2026_paper_country_summary.csv    one row per paper: roles, #countries, international flag
Run: PYTHONUTF8=1 python code/enrichment/07_25_2026_map_author_countries.py
"""
import json, os, re, sys
import pandas as pd
# Run from the repository root; the shared modules live in code/lib.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'lib'))
from country_matcher import detect_country, MANUAL_AUTHOR_COUNTRY

CACHE = 'data/authors/07_25_2026_authors_cache_385.json'   # canonical 385 = 377 analysed + 8 added (5 re-review + 3 new); excludes STUDY-0956/STUDY-0136/STUDY-0478
GOLD  = 'data/authors/07_16_2026_saudi_affiliation_variables.xlsx'
ANALYSIS_WIDE = 'data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv'

# ---- Enrichment for the 51 authors PubMed left with no affiliation (verified from gold PDF notes) ----
# Papers where the gold note confirms EVERY author holds a Saudi affiliation:
ALL_SAUDI_PAPERS = {'STUDY-0135', 'STUDY-0109', 'STUDY-0047', 'STUDY-0429'}
# Papers with a documented mix -> per-surname exceptions; everyone else in them is Saudi:
MIXED_PAPER_EXCEPTIONS = {
    'STUDY-0245': {'Karobari': 'Cambodia', 'Heboyan': 'Armenia'},   # rest Saudi (note: 9/11 Saudi)
    'STUDY-0336': {'Divakar': 'India'},                              # India/Zambia; rest Saudi (4/5)
    'STUDY-0030': {'Shafi': 'Pakistan'},                             # rest Saudi (7/8)
}

def enrich_no_affil(pmid, last):
    """Return a country for an author PubMed left without an affiliation, else None."""
    if pmid in ALL_SAUDI_PAPERS:
        return 'Saudi Arabia'
    if pmid in MIXED_PAPER_EXCEPTIONS:
        return MIXED_PAPER_EXCEPTIONS[pmid].get(last, 'Saudi Arabia')
    return None

def author_country(pmid, a):
    """Return (primary_country, all_countries, source) for one author dict."""
    last = a.get('last', '').strip()
    key = (str(pmid), last)
    if key in MANUAL_AUTHOR_COUNTRY:
        # The override may be a single country or an ordered list. Lists were added
        # 2026-08-24: the hand-read found dual-country authors whose override cannot be
        # expressed as one string (e.g. Al-Tawfiq = Saudi Arabia + United States). The
        # FIRST entry is the primary (first-listed) affiliation, matching detect_country.
        v = MANUAL_AUTHOR_COUNTRY[key]
        allc = [v] if isinstance(v, str) else list(v)
        return allc[0], allc, 'manual-context'
    aff = a.get('aff', '').strip()
    if aff:
        prim, allc = detect_country(aff)
        if prim:
            return prim, allc, 'pubmed-affil'
        return None, [], 'pubmed-affil-unresolved'
    # no affiliation in PubMed -> try gold-note enrichment
    e = enrich_no_affil(str(pmid), last)
    if e:
        return e, [e], 'pdf-gold-note'
    return None, [], 'no-affiliation'

def main():
    d = json.load(open(CACHE, 'r', encoding='utf-8'))
    gold = pd.read_excel(GOLD).set_index('PMID')
    try:
        analysis_pmids = set(pd.read_csv(ANALYSIS_WIDE)['PMID'].astype(int))
    except Exception:
        analysis_pmids = set()

    rows = []
    for pmid, authors in d.items():
        reals = [a for a in authors if a.get('last', '').strip()]
        n = len(reals)
        for i, a in enumerate(reals):
            prim, allc, src = author_country(pmid, a)
            rows.append(dict(
                PMID=int(pmid),
                author_index=i + 1,
                n_authors=n,
                last=a.get('last', '').strip(),
                fore=a.get('fore', '').strip(),
                is_first=(i == 0),
                is_last=(i == n - 1),
                primary_country=prim,
                all_countries='; '.join(allc),
                n_countries_author=len(allc),
                dual_affiliation=(len(allc) > 1),
                source=src,
                in_analysis_377=(int(pmid) in analysis_pmids),
            ))
    L = pd.DataFrame(rows)
    L.to_csv('data/authors/07_25_2026_author_country_long.csv', index=False, encoding='utf-8-sig')

    # ---------- validation: any_saudi vs gold ----------
    my_any = L.groupby('PMID').apply(
        lambda g: g['all_countries'].str.contains('Saudi Arabia').any())
    g_any = gold['any_saudi_author'].fillna(1).astype(bool)  # STUDY-0047 note = all Saudi
    cmp = pd.DataFrame({'mine': my_any, 'gold': g_any}).dropna()
    agree = (cmp['mine'] == cmp['gold']).sum()
    print(f"VALIDATION any_saudi_author vs gold: {agree}/{len(cmp)} "
          f"({agree/len(cmp)*100:.1f}%)")

    # ---------- paper-level summary ----------
    psum = []
    for pmid, g in L.groupby('PMID'):
        countries = []
        for cs in g['all_countries']:
            for c in [x.strip() for x in cs.split(';') if x.strip()]:
                if c not in countries:
                    countries.append(c)
        fa = g[g.is_first]['primary_country'].iloc[0] if g.is_first.any() else None
        la = g[g.is_last]['primary_country'].iloc[0] if g.is_last.any() else None
        psum.append(dict(
            PMID=pmid, n_authors=g['n_authors'].iloc[0],
            first_author_country=fa, last_author_country=la,
            n_distinct_countries=len(countries),
            countries='; '.join(countries),
            international=(len(countries) > 1),
            has_saudi=('Saudi Arabia' in countries),
            in_analysis_377=g['in_analysis_377'].iloc[0],
        ))
    P = pd.DataFrame(psum)
    P.to_csv('data/authors/07_25_2026_paper_country_summary.csv', index=False, encoding='utf-8-sig')

    # ---------- corresponding-author country ----------
    # ⚠ REWRITTEN 2026-08-24. The old version matched gold's `corr_author` against an author's
    # surname and gave up otherwise, which made Suppl. Fig. S1 report **207** Saudi
    # corresponding authors while Table 1 reported **246** -- the same quantity, 39 papers
    # apart, in one submission package. The gold file records the corresponding author by TEN
    # methods and only some of them yield a bare surname:
    #     marker+name 280 · single-email 25 · marker+address 19 (NO NAME AT ALL -- identified
    #     from the PDF's affiliation marker and address) · manual-TSA/YA 16 (FULL NAMES) ·
    #     europepmc-xml 13 · email-domain-sa 11 (the field holds EMAIL ADDRESSES) ·
    #     email-name-match 10 · marker+name(v2) 6 · single-author 4 · marker+email 1
    # so 331 fields are a bare surname, 24 a full name, 11 an email, and 19 are empty.
    #
    # ⚠ And matching on surname alone is not just incomplete, it is WRONG on 9 papers where
    # two authors share the surname: the old code unioned the countries of everyone who
    # matched, which is how STUDY-0700 and STUDY-0199 (one Saudi Mohamed/Louati and one not) were
    # counted Saudi-corresponding when the hand-coded flag says they are not.
    #
    # Tiers, most specific first. `corresponding_author_saudi` from the ANALYSIS DATASET --
    # the same column Table 1 reads -- is AUTHORITATIVE on Saudi status, so the figure and
    # the table cannot drift again. It is hand-coded and PDF-confirmed, and it encodes the
    # standing convention that a paper is Saudi-corresponding if ANY of its corresponding
    # authors is Saudi (gold stores only one name, so a name lookup misses the second).
    corr_flag = {}
    try:
        _aw = pd.read_csv(ANALYSIS_WIDE, dtype=str)
        corr_flag = {int(r.PMID): str(r.corresponding_author_saudi)
                     for r in _aw.itertuples() if str(r.corresponding_author_saudi) in ('0', '1')}
    except Exception:
        pass

    def _countries_of(sub):
        cs = set()
        for x in sub['all_countries'].fillna(''):
            cs |= {y.strip() for y in x.split(';') if y.strip()}
        return cs

    corr_ctry, corr_how, corr_unresolved = {}, {}, []
    for pmid in sorted(set(L.PMID)):
        sub_all = L[L.PMID == pmid]
        r = gold.loc[pmid] if pmid in gold.index else None
        field = str(r.get('corr_author')) if r is not None and isinstance(r.get('corr_author'), str) else ''
        email_f = str(r.get('corr_email')) if r is not None and isinstance(r.get('corr_email'), str) else ''
        mails = re.findall(r'[\w\.\-\+]+@[\w\.\-]+', field + ' ' + email_f)
        names = [n.strip() for n in re.split(r'[;,]', field) if n.strip() and '@' not in n]
        got, how = set(), None
        # 1) a name -- the whole field, else its last token for "Ragab K. Elnaggar".
        #    UNIQUE matches only: an ambiguous surname identifies nobody.
        for n in names:
            for cand in (n.strip(), re.split(r'[\s\.]+', n.strip())[-1]):
                hit = sub_all[sub_all.last.str.lower() == cand.lower()]
                if len(hit) == 1:
                    got |= _countries_of(hit); how = 'name'; break
        # 2) an email -- the author whose own affiliation text carries it
        if not got and mails:
            for m in mails:
                hit = sub_all[sub_all.author_index.map(
                    lambda i, p=pmid: m.lower() in (d[str(p)][int(i) - 1].get('aff') or '').lower())]
                if len(hit) >= 1:
                    got |= _countries_of(hit); how = 'email'
        # 3) the hand-coded flag decides SAUDI, in both directions. It cannot name a foreign
        #    country, so a non-Saudi paper with no resolvable author stays uncounted rather
        #    than being guessed at.
        f = corr_flag.get(pmid)
        if f == '1' and 'Saudi Arabia' not in got:
            got.add('Saudi Arabia'); how = how or 'flag'
        elif f == '0' and 'Saudi Arabia' in got:
            got.discard('Saudi Arabia')
        if got:
            corr_ctry[pmid] = got
        else:
            corr_unresolved.append(pmid)
        corr_how[pmid] = how or 'unresolved'
    _hc = pd.Series(list(corr_how.values())).value_counts().to_dict()
    print(f"\ncorresponding author resolved by: {_hc}")
    print(f"  Saudi-corresponding papers: {sum('Saudi Arabia' in v for v in corr_ctry.values())}"
          f"  (must equal Table 1's corresponding_author_saudi)")
    print(f"  no country resolvable: {len(corr_unresolved)} papers, all flagged non-Saudi "
          f"-- foreign corresponding-author counts are a LOWER BOUND for these")

    # ---------- country counts table ----------
    # CONVENTION (TSA, 2026-08-24): count an author under EVERY country they hold, not just
    # the first-listed one -- "an author counts as Saudi if ANY of their affiliations is
    # Saudi". Previously `author_appearances`, `first_author` and `last_author` were built
    # from `primary_country` while `papers_with_>=1_author` already used `all_countries`,
    # so the file contradicted itself AND contradicted Table 1: Fig. S1 reported 225 Saudi
    # first authors against Table 1's 252. By-any gives 252 and the two now agree.
    # ⚠ CONSEQUENCE: a dual-affiliated author is counted once in EACH of their countries, so
    # `author_appearances` sums to 3,829, NOT to the 3,508 author rows. That is intended for
    # a "countries represented" chart, but the figure must say so.
    def vc_any(df):
        from collections import Counter
        c = Counter()
        for x in df['all_countries'].fillna(''):
            for k in {y.strip() for y in x.split(';') if y.strip()}:
                c[k] += 1
        return pd.Series(c)

    appearances = vc_any(L)
    first_c = vc_any(L[L.is_first])
    last_c = vc_any(L[L.is_last])
    corr_c = pd.Series({k: v for k, v in
                        __import__('collections').Counter(
                            c for cs in corr_ctry.values() for c in cs).items()})
    # papers with >=1 author from country
    papers_with = {}
    for pmid, g in L.groupby('PMID'):
        seen = set()
        for cs in g['all_countries']:
            for c in [x.strip() for x in cs.split(';') if x.strip()]:
                seen.add(c)
        for c in seen:
            papers_with[c] = papers_with.get(c, 0) + 1
    papers_with = pd.Series(papers_with)

    counts = pd.DataFrame({
        'author_appearances': appearances,
        'first_author': first_c,
        'last_author': last_c,
        'corresponding_author': corr_c,
        'papers_with_>=1_author': papers_with,
    }).fillna(0).astype(int)
    counts = counts.sort_values('author_appearances', ascending=False)
    counts.index.name = 'country'
    counts.to_csv('data/authors/07_25_2026_country_counts.csv', encoding='utf-8-sig')

    # ---------- console report ----------
    print(f"\nReal author-appearances: {len(L)}   with a country: {L['primary_country'].notna().sum()}"
          f"   ({L['primary_country'].notna().mean()*100:.2f}%)")
    print(f"Unresolved: {L['primary_country'].isna().sum()}   distinct countries: {L['primary_country'].nunique()}")
    print(f"Source mix: {L['source'].value_counts().to_dict()}")
    print(f"\nPapers: {P.PMID.nunique()}   international (>1 country): {P.international.sum()} "
          f"({P.international.mean()*100:.1f}%)   median #countries/paper: {P.n_distinct_countries.median():.0f}")
    print("\n===== TOP 25 COUNTRIES (by author-appearances) =====")
    print(counts.head(25).to_string())
    print("\n===== ALL COUNTRIES: total", len(counts), "=====")
    print('; '.join(f"{c}({n})" for c, n in counts['author_appearances'].items()))

if __name__ == '__main__':
    main()
