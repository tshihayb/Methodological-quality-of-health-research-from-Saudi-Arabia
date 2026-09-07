# -*- coding: utf-8 -*-
"""Compare the PDF-only author reconstruction against S1 / S2 / the author stratifiers.

Input  : data/quality-control/08_23_2026_pdf_author_affiliations.csv   (PDFs only)
Against: data/authors/07_25_2026_author_country_long.csv               (S1)
         data/authors/07_25_2026_saudi_affiliation_long.csv            (S2)

Authors are aligned by SURNAME within a paper, never by position alone, so a
disagreement about the author list cannot masquerade as a disagreement about a country.

Run from the repository root.
"""
import os, re, sys, unicodedata
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = 'data/quality-control'


def deacc(s):
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c))


def surname_key(s):
    """Last alphabetic token, lowercased -- 'A.R. AZAB' -> 'azab', 'Bin Sebayel' -> 'sebayel'."""
    toks = [t for t in re.split(r'[^A-Za-z]+', deacc(s)) if len(t) > 1]
    return toks[-1].lower() if toks else ''


P = pd.read_csv(f'{OUT}/08_23_2026_pdf_author_affiliations.csv', encoding='utf-8-sig')
L = pd.read_csv('data/authors/07_25_2026_author_country_long.csv', encoding='utf-8-sig')
A = pd.read_csv('data/authors/07_25_2026_saudi_affiliation_long.csv', encoding='utf-8-sig')
inst_of = {(int(r.PMID), int(r.author_index)): str(r.institution) for r in A.itertuples()}

P['key'] = P.pdf_name.map(surname_key)
L['key'] = L.last.map(surname_key)

rows, papers = [], []
for pmid, pg in P.groupby('PMID'):
    lg = L[L.PMID == int(pmid)]
    if lg.empty:
        continue

    # Paper-level rows: the extractor could not read the byline markers but established
    # that EVERY affiliation in the paper is in one country, so every author is too.
    # Compare that against each author individually.
    if len(pg) == 1 and str(pg.iloc[0].pdf_name) == '(all authors)':
        pr = pg.iloc[0]
        pdf_c = str(pr.pdf_countries).strip()
        pdf_i = str(pr.pdf_saudi_institutions).strip()
        for lr in lg.itertuples():
            pm_cs = {x.strip() for x in re.split(r'\s*;\s*', str(lr.all_countries)) if x.strip()}
            c_flag = 'ok' if pdf_c in pm_cs else 'COUNTRY_MISMATCH'
            pdf_sa = pdf_c == 'Saudi Arabia'
            pm_sa = 'Saudi Arabia' in pm_cs
            s_flag = 'ok' if pdf_sa == pm_sa else ('SAUDI_ONLY_IN_PDF' if pdf_sa else 'SAUDI_ONLY_IN_PUBMED')
            pm_i = inst_of.get((int(pmid), int(lr.author_index)), '')
            if pdf_i and pm_i and not pdf_i.startswith('('):
                i_flag = 'ok' if pm_i == pdf_i else 'INSTITUTION_MISMATCH'
            else:
                i_flag = 'no_pdf_institution' if pm_i else ''
            rows.append([pmid, 0, '(all authors)', lr.author_index, c_flag, s_flag, i_flag,
                         '%s -> %s' % (lr.all_countries, pdf_c), '%s -> %s' % (pm_i, pdf_i)])
        papers.append([pmid, len(lg), len(lg), len(lg), 'paper_level'])
        continue
    n_pdf, n_pm = len(pg), len(lg)
    matched = 0
    used = set()
    for _, pr in pg.iterrows():
        cand = lg[(lg.key == pr.key) & (~lg.author_index.isin(used))]
        if cand.empty:
            rows.append([pmid, pr.pdf_ordinal, pr.pdf_name, '', 'NOT_IN_PUBMED', '', '', '', ''])
            continue
        lr = cand.iloc[0]
        used.add(int(lr.author_index))
        matched += 1

        # Only judge an author whose EVERY affiliation marker resolved. A dual-affiliated
        # author with one affiliation unparsed would otherwise look like a data
        # disagreement when it is really a partial parse on our side.
        full = int(getattr(pr, 'all_markers_resolved', 1) or 0)

        pdf_cs = [c.strip() for c in str(pr.pdf_countries).split('|') if c.strip() and c.strip() != 'nan']
        pm_cs = {x.strip() for x in re.split(r'\s*;\s*', str(lr.all_countries)) if x.strip()}
        c_flag = 'partial_parse' if not full else ''
        if full and pdf_cs:
            c_flag = 'ok' if set(pdf_cs) & pm_cs else 'COUNTRY_MISMATCH'
        elif full:
            c_flag = 'no_pdf_country'

        pdf_sa = 'Saudi Arabia' in pdf_cs
        pm_sa = 'Saudi Arabia' in pm_cs
        if not full or not pdf_cs:
            s_flag = 'partial_parse'
        else:
            s_flag = 'ok' if (pdf_sa == pm_sa) else ('SAUDI_ONLY_IN_PDF' if pdf_sa else 'SAUDI_ONLY_IN_PUBMED')

        pdf_i = [i.strip() for i in str(pr.pdf_saudi_institutions).split('|')
                 if i.strip() and i.strip() != 'nan']
        # a placeholder is a failure to name, not a competing answer
        pdf_i = [i for i in pdf_i if not i.startswith('(') and not i.startswith('Private practice')]
        pm_i = inst_of.get((int(pmid), int(lr.author_index)), '')
        i_flag = ''
        if not full:
            i_flag = 'partial_parse'
        elif pdf_i and pm_i:
            i_flag = 'ok' if pm_i in pdf_i else 'INSTITUTION_MISMATCH'
        elif pm_i and not pdf_i:
            i_flag = 'no_pdf_institution'

        rows.append([pmid, pr.pdf_ordinal, pr.pdf_name, lr.author_index, c_flag or 'no_pdf_country',
                     s_flag, i_flag, '%s -> %s' % (lr.all_countries, ' | '.join(pdf_cs)),
                     '%s -> %s' % (pm_i, ' | '.join(pdf_i))])
    papers.append([pmid, n_pdf, n_pm, matched, 'count_ok' if n_pdf == n_pm else 'COUNT_DIFF'])

R = pd.DataFrame(rows, columns=['PMID', 'pdf_ordinal', 'pdf_name', 'pubmed_index',
                                'country_flag', 'saudi_flag', 'institution_flag',
                                'country_detail', 'institution_detail'])
S = pd.DataFrame(papers, columns=['PMID', 'n_authors_pdf', 'n_authors_pubmed', 'n_matched', 'count_flag'])
R.to_csv(f'{OUT}/08_23_2026_pdf_vs_pubmed_authors.csv', index=False, encoding='utf-8-sig')
S.to_csv(f'{OUT}/08_23_2026_pdf_vs_pubmed_papers.csv', index=False, encoding='utf-8-sig')

m = R[R.pubmed_index != '']
print('papers compared      : %d' % len(S))
print('  author count agrees: %d (%.1f%%)' % ((S.count_flag == 'count_ok').sum(),
                                              100.0 * (S.count_flag == 'count_ok').sum() / len(S)))
print('authors in the PDFs  : %d' % len(R))
print('  matched to a PubMed author by surname: %d' % len(m))
print('  present in the PDF but NOT in PubMed : %d' % (R.country_flag == 'NOT_IN_PUBMED').sum())
print()
for col, label in [('country_flag', 'COUNTRY'), ('saudi_flag', 'IS-SAUDI'), ('institution_flag', 'INSTITUTION')]:
    sub = m[m[col].isin(['ok']) | m[col].str.contains('MISMATCH|ONLY', na=False)]
    good = (sub[col] == 'ok').sum()
    print('%-12s comparable %4d   agree %4d   = %.2f%%' % (label, len(sub), good,
                                                           100.0 * good / len(sub) if len(sub) else 0))
    bad = sub[sub[col] != 'ok']
    if len(bad):
        print('     ', bad[col].value_counts().to_dict())
print()
print('wrote', OUT)
