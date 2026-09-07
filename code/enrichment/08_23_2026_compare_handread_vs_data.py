"""Compare the hand-read author->affiliation linkage against the live data.

This is a DIFF, not a patch. Nothing here writes to S1, S2 or the stratifiers -- TSA
adjudicates every conflict (decision of 2026-08-23). Four comparisons:

 A. classifier cross-check  detect_country_segment(verbatim) vs the country the reader saw.
    A disagreement is a candidate CLASSIFIER bug, not a data error -- this is how the
    "University of Benin Teaching Hospital is in Nigeria" bug would surface again.
 B. author -> country       vs data/authors/07_25_2026_author_country_long.csv   (S1)
 C. author -> Saudi inst.   vs data/authors/07_25_2026_saudi_affiliation_long.csv (S2)
 D. stratifiers             recomputed first/last-author-Saudi and pct_saudi vs
                            data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv

⚠ THE INDEX-ALIGNMENT GUARD. The hand-read's author_index is position in the PRINTED
byline; S1/S2's author_index is position in PubMed's author list. They usually coincide,
but a collective author entry or a byline the publisher reordered will shift one against
the other -- and a shifted join manufactures mismatches that look exactly like data
errors. So every joined pair is checked on SURNAME first, and pairs whose surnames
disagree are reported as `index_misalignment`, never counted as a linkage disagreement.

⚠ `all_countries` in S1 is "; "-separated, NOT "|"-separated. Getting this wrong once
faked 260 bad countries and 34 papers "missing Saudi Arabia".

Run from the repository root.
"""
import os
import re
import sys
import unicodedata

import pandas as pd

sys.path.insert(0, os.path.join('code', 'lib'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from country_matcher import detect_country_segment          # noqa: E402
from saudi_institution_classifier import classify           # noqa: E402

HANDREAD = 'data/authors/08_23_2026_handread_author_affiliations.csv'
S1 = 'data/authors/07_25_2026_author_country_long.csv'
S2 = 'data/authors/07_25_2026_saudi_affiliation_long.csv'
WIDE = 'data/analysis/08_12_2026_ANALYSIS_DATASET_wide_385.csv'
OUT = 'data/quality-control'


# The reader copies the country as the PAPER prints it; the classifier emits its own
# canonical label. "U.S.A." vs "United States" is not a disagreement, and left unnormalised
# this cosmetic difference would swamp the real signal -- the pilot alone threw 4 of them.
COUNTRY_ALIAS = {
    'usa': 'united states', 'u s a': 'united states', 'us': 'united states',
    'u s': 'united states', 'united states of america': 'united states',
    'america': 'united states',
    'uk': 'united kingdom', 'u k': 'united kingdom', 'great britain': 'united kingdom',
    'england': 'united kingdom', 'scotland': 'united kingdom', 'wales': 'united kingdom',
    'northern ireland': 'united kingdom',
    'ksa': 'saudi arabia', 'kingdom of saudi arabia': 'saudi arabia',
    'uae': 'united arab emirates', 'u a e': 'united arab emirates',
    'turkiye': 'turkey', 'republic of turkiye': 'turkey',
    'korea': 'south korea', 'republic of korea': 'south korea',
    'prc': 'china', "people's republic of china": 'china',
    'russian federation': 'russia', 'czechia': 'czech republic',
    'the netherlands': 'netherlands', 'holland': 'netherlands',
    'egypt arab republic': 'egypt', 'iran islamic republic': 'iran',
}


def norm_country(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'[^a-z ]', ' ', s.lower())
    s = re.sub(r'\s+', ' ', s).strip()
    return COUNTRY_ALIAS.get(s, s)


# NFKD strips combining marks, but these are standalone Latin-extended letters with no
# combining form -- "Karakuła" stayed "Karakua" and failed to match "Karakula", which
# showed up as an index misalignment rather than the identical name it is.
TRANSLIT = str.maketrans({'ł': 'l', 'Ł': 'L', 'ø': 'o', 'Ø': 'O', 'đ': 'd', 'Đ': 'D',
                          'ð': 'd', 'þ': 'th', 'ß': 'ss', 'æ': 'ae', 'Æ': 'AE',
                          'œ': 'oe', 'Œ': 'OE', 'ı': 'i'})


def norm_name(s):
    s = str(s).translate(TRANSLIT)
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]', '', s.lower())


def surnames_match(a, b):
    """Loose surname comparison. Transliteration varies ("Al-Shammari"/"Alshammari"),
    and papers print compound names the citation database splits differently, so a
    containment match in either direction counts."""
    a, b = norm_name(a), norm_name(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def main():
    hr = pd.read_csv(HANDREAD, encoding='utf-8-sig')
    hr['verbatim'] = hr.verbatim.fillna('')
    s1 = pd.read_csv(S1, encoding='utf-8-sig')
    s2 = pd.read_csv(S2, encoding='utf-8-sig')

    # ---------- A. classifier cross-check on every verbatim affiliation ----------
    aff = hr[hr.verbatim != ''].copy()
    aff['country_auto'] = [detect_country_segment(v)[0] for v in aff.verbatim]
    aff['country_read'] = aff.country_read.fillna('')
    a_dis = aff[(aff.country_read != '') & (aff.country_auto.notna())
                & (aff.country_read.map(norm_country)
                   != aff.country_auto.map(norm_country))]
    a_none = aff[aff.country_auto.isna()]
    print('A. CLASSIFIER CROSS-CHECK')
    print(f'   affiliations read           : {len(aff)}')
    print(f'   classifier found a country  : {aff.country_auto.notna().sum()}')
    print(f'   classifier found none       : {len(a_none)}')
    print(f'   ⚠ disagrees with the reader : {len(a_dis)}')
    a_dis.to_csv(f'{OUT}/08_23_2026_handread_classifier_disagreements.csv',
                 index=False, encoding='utf-8-sig')

    # ---------- author level, from the hand-read ----------
    aff['country_final'] = aff.country_auto.fillna(aff.country_read.replace('', pd.NA))
    au = (aff.groupby(['PMID', 'author_index'])
             .agg(last_read=('last', 'first'),
                  countries_read=('country_final',
                                  lambda s: '; '.join(dict.fromkeys(x for x in s if pd.notna(x)))),
                  confidence=('confidence', 'first'),
                  n_affils=('n_affils', 'first'))
             .reset_index())
    au['is_saudi_read'] = au.countries_read.str.contains('Saudi Arabia', na=False)
    # Authors the reader recorded with NO affiliation at all are not comparable: absence
    # of evidence in the paper is not evidence the author is not Saudi.
    noaff = hr[(hr.verbatim == '')][['PMID', 'author_index']].drop_duplicates()

    # ---------- B. author -> country ----------
    s1['is_saudi_s1'] = s1.all_countries.fillna('').str.contains('Saudi Arabia')
    m = au.merge(s1[['PMID', 'author_index', 'last', 'primary_country',
                     'all_countries', 'is_saudi_s1']],
                 on=['PMID', 'author_index'], how='inner', suffixes=('', '_s1'))
    m['aligned'] = [surnames_match(a, b) for a, b in zip(m.last_read, m.last)]
    mis = m[~m.aligned]
    cmp_ = m[m.aligned & (m.countries_read != '')].copy()

    def country_agrees(r):
        read = {norm_country(x) for x in r.countries_read.split(';') if x.strip()}
        have = {norm_country(x) for x in str(r.all_countries or '').split(';') if x.strip()}
        return bool(read & have) if read and have else False

    cmp_['country_ok'] = cmp_.apply(country_agrees, axis=1)
    cmp_['saudi_ok'] = cmp_.is_saudi_read == cmp_.is_saudi_s1
    print('\nB. AUTHOR -> COUNTRY  (vs S1)')
    print(f'   joined author rows            : {len(m)}')
    print(f'   ⚠ index misalignment (skipped): {len(mis)}')
    print(f'   comparable                    : {len(cmp_)}')
    if len(cmp_):
        print(f'   country overlap agrees        : {cmp_.country_ok.sum()} '
              f'({cmp_.country_ok.mean():.2%})')
        print(f'   is-Saudi agrees               : {cmp_.saudi_ok.sum()} '
              f'({cmp_.saudi_ok.mean():.2%})')
    cmp_[~cmp_.country_ok | ~cmp_.saudi_ok].to_csv(
        f'{OUT}/08_23_2026_handread_country_disagreements.csv', index=False, encoding='utf-8-sig')
    mis.to_csv(f'{OUT}/08_23_2026_handread_index_misalignment.csv',
               index=False, encoding='utf-8-sig')

    # ---------- C. author -> Saudi institution ----------
    sa = aff[aff.country_final == 'Saudi Arabia'].copy()
    if len(sa):
        cls = [classify(v) for v in sa.verbatim]
        sa['inst_type_read'] = [c[0] for c in cls]
        sa['institution_read'] = [c[1] for c in cls]
    ms = sa.merge(s2[['PMID', 'author_index', 'last', 'inst_type', 'institution']],
                  on=['PMID', 'author_index'], how='inner', suffixes=('', '_s2'))
    ms['aligned'] = [surnames_match(a, b) for a, b in zip(ms.last, ms.last_s2)]
    msc = ms[ms.aligned].copy()
    if len(msc):
        # An author with two Saudi affiliations legitimately holds two institutions; S2
        # records one row per author-institution, so agreement is containment, not equality.
        agree = (msc.groupby(['PMID', 'author_index'])
                    .apply(lambda g: g.institution_read.iloc[0] in set(g.institution),
                           include_groups=False))
        typ = (msc.groupby(['PMID', 'author_index'])
                  .apply(lambda g: g.inst_type_read.iloc[0] in set(g.inst_type),
                         include_groups=False))
        print('\nC. AUTHOR -> SAUDI INSTITUTION  (vs S2)')
        print(f'   Saudi author-affiliations read: {len(sa)}')
        print(f'   comparable authors            : {len(agree)}')
        print(f'   institution agrees            : {agree.sum()} ({agree.mean():.2%})')
        print(f'   type agrees                   : {typ.sum()} ({typ.mean():.2%})')
        bad = agree[~agree].index.tolist()
        msc[msc.set_index(['PMID', 'author_index']).index.isin(bad)].to_csv(
            f'{OUT}/08_23_2026_handread_institution_disagreements.csv',
            index=False, encoding='utf-8-sig')

    # ---------- D. stratifiers ----------
    # Only papers whose EVERY author carries at least one affiliation can be recomputed.
    # A paper with an unresolved author has an unknown numerator, and an unknown numerator
    # is not a zero.
    full = (au.merge(noaff, on=['PMID', 'author_index'], how='left', indicator=True)
              .query('_merge == "left_only"').drop(columns='_merge'))
    complete = set(full.PMID) - set(noaff.PMID)
    fu = full[full.PMID.isin(complete)]
    strat = (fu.groupby('PMID')
               .apply(lambda g: pd.Series({
                   'n_authors_read': len(g),
                   'n_saudi_read': int(g.is_saudi_read.sum()),
                   'first_saudi_read': bool(g.loc[g.author_index.idxmin(), 'is_saudi_read']),
                   'last_saudi_read': bool(g.loc[g.author_index.idxmax(), 'is_saudi_read']),
               }), include_groups=False).reset_index())
    strat['pct_saudi_read'] = (100 * strat.n_saudi_read / strat.n_authors_read).round(1)

    w = pd.read_csv(WIDE, encoding='utf-8-sig', low_memory=False)
    keep = ['PMID', 'n_authors', 'n_saudi_authors', 'pct_saudi_authors',
            'first_author_saudi', 'last_author_saudi', 'pct_saudi_ge50']
    d = strat.merge(w[keep], on='PMID', how='inner')
    d['first_diff'] = d.first_saudi_read.astype(int) != d.first_author_saudi
    d['last_diff'] = d.last_saudi_read.astype(int) != d.last_author_saudi
    d['nsaudi_diff'] = d.n_saudi_read != d.n_saudi_authors
    d['nauth_diff'] = d.n_authors_read != d.n_authors
    d['ge50_read'] = d.pct_saudi_read >= 50
    d['ge50_diff'] = d.ge50_read != (d.pct_saudi_ge50 == '>=50%')
    print('\nD. STRATIFIERS  (recomputed from the hand-read, vs the wide dataset)')
    print(f'   papers with every author affiliated: {len(d)}')
    for c, lab in [('nauth_diff', 'author count'), ('first_diff', 'first_author_saudi'),
                   ('last_diff', 'last_author_saudi'), ('nsaudi_diff', 'n_saudi_authors'),
                   ('ge50_diff', 'pct_saudi_ge50')]:
        print(f'   {lab:<22}: {int(d[c].sum())} differ')
    d.to_csv(f'{OUT}/08_23_2026_handread_stratifier_diff.csv', index=False, encoding='utf-8-sig')
    print(f'\ndiff files written to {OUT}/08_23_2026_handread_*.csv')


if __name__ == '__main__':
    main()
