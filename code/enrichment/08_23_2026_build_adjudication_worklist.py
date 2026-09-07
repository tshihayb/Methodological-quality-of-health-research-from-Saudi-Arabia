"""Build ONE adjudication worklist from the hand-read diffs.

Everything the hand-read turns up lands in five separate diff CSVs, each keyed
differently. That is fine for debugging and useless for deciding. This collapses them
into a single sheet with one row per decision, each carrying the evidence needed to make
it without opening another file: what the PAPER prints, what the DATA says, which
mechanism explains the gap, and which downstream artefact moves if the ruling goes
against the data.

Nothing here writes to S1, S2 or the stratifiers.

Conflict kinds
  country          hand-read vs S1 (author -> country)
  institution      hand-read vs S2 (author -> Saudi institution)
  stratifier       recomputed first/last/n_saudi/pct vs the wide dataset
  wide_vs_s1       the wide dataset vs the author-country file (no hand-read needed)
  index_align      the byline order and PubMed's author order do not line up
  unreadable       the paper does not print the linkage at all

Run from the repository root, AFTER 08_23_2026_compare_handread_vs_data.py.
"""
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QC = 'data/quality-control'
OUT = f'{QC}/08_23_2026_ADJUDICATION_WORKLIST.csv'
HANDREAD = 'data/authors/08_23_2026_handread_author_affiliations.csv'
PAPERS = f'{QC}/08_23_2026_handread_paper_status.csv'


def load(path, **kw):
    return pd.read_csv(path, encoding='utf-8-sig', **kw) if os.path.exists(path) else pd.DataFrame()


def main():
    rows = []
    hr = load(HANDREAD)

    def paper_text(pmid, idx):
        """Every affiliation the reader transcribed for one author, joined."""
        if hr.empty:
            return ''
        s = hr[(hr.PMID == pmid) & (hr.author_index == idx)].verbatim.dropna()
        return ' || '.join(x for x in s if str(x).strip())

    # --- country: hand-read vs S1 -------------------------------------------------
    d = load(f'{QC}/08_23_2026_handread_country_disagreements.csv')
    for _, r in d.iterrows():
        rows.append({
            'kind': 'country', 'PMID': r.PMID, 'author_index': r.author_index,
            'author': r.get('last_read', ''),
            'paper_says': r.get('countries_read', ''),
            'data_says': r.get('all_countries', ''),
            'confidence': r.get('confidence', ''),
            'affects': 'Suppl. Fig. S1 (author countries)'
                       + ('; Saudi counts & stratifiers'
                          if 'Saudi' in str(r.get('countries_read', '')) + str(r.get('all_countries', ''))
                          else ''),
            'evidence': paper_text(r.PMID, r.author_index)[:600]})

    # --- institution: hand-read vs S2 ---------------------------------------------
    d = load(f'{QC}/08_23_2026_handread_institution_disagreements.csv')
    for (pmid, idx), g in (d.groupby(['PMID', 'author_index']) if not d.empty else []):
        rows.append({
            'kind': 'institution', 'PMID': pmid, 'author_index': idx,
            'author': g.iloc[0].get('last', ''),
            'paper_says': f"{g.iloc[0].get('institution_read', '')} "
                          f"({g.iloc[0].get('inst_type_read', '')})",
            'data_says': '; '.join(sorted({f"{a} ({b})" for a, b in
                                           zip(g.institution, g.inst_type)})),
            'confidence': g.iloc[0].get('confidence', ''),
            'affects': 'Suppl. Fig. S2 (Saudi institutions)',
            'evidence': paper_text(pmid, idx)[:600]})

    # --- stratifiers: recomputed vs wide -------------------------------------------
    d = load(f'{QC}/08_23_2026_handread_stratifier_diff.csv')
    if not d.empty:
        flags = [('nauth_diff', 'n_authors', 'n_authors_read', 'n_authors'),
                 ('first_diff', 'first_author_saudi', 'first_saudi_read', 'first_author_saudi'),
                 ('last_diff', 'last_author_saudi', 'last_saudi_read', 'last_author_saudi'),
                 ('nsaudi_diff', 'n_saudi_authors', 'n_saudi_read', 'n_saudi_authors'),
                 ('ge50_diff', 'pct_saudi_ge50', 'ge50_read', 'pct_saudi_ge50')]
        for _, r in d.iterrows():
            for flag, var, readcol, datacol in flags:
                if bool(r.get(flag)):
                    rows.append({
                        'kind': 'stratifier', 'PMID': r.PMID, 'author_index': '',
                        'author': var,
                        'paper_says': r.get(readcol), 'data_says': r.get(datacol),
                        'confidence': '', 'affects': f'Table 1 stratifier `{var}`',
                        'evidence': f"read {r.get('n_saudi_read')}/{r.get('n_authors_read')} "
                                    f"Saudi = {r.get('pct_saudi_read')}%; "
                                    f"wide {r.get('n_saudi_authors')}/{r.get('n_authors')} "
                                    f"= {r.get('pct_saudi_authors')}%"})

    # --- wide vs S1 (independent of the hand-read) ---------------------------------
    d = load(f'{QC}/08_23_2026_wide_vs_author_files_diff.csv')
    for _, r in d.iterrows():
        which = [n for f, n in [('d_nauth', 'n_authors'), ('d_nsaudi', 'n_saudi_authors'),
                                ('d_first', 'first_author_saudi'),
                                ('d_last', 'last_author_saudi'),
                                ('d_ge50', 'pct_saudi_ge50')] if bool(r.get(f))]
        rows.append({
            'kind': 'wide_vs_s1', 'PMID': r.PMID, 'author_index': '',
            'author': ', '.join(which),
            'paper_says': f"S1: {r.get('n_saudi_s1')}/{r.get('n_authors_s1')} Saudi "
                          f"({r.get('pct_saudi_s1')}%)",
            'data_says': f"wide: {r.get('n_saudi_authors')}/{r.get('n_authors')} Saudi "
                         f"({r.get('pct_saudi_authors')}%)",
            'confidence': '',
            'affects': 'Table 1 stratifiers',
            'evidence': 'wide is built from 07_16_2026_saudi_affiliation_variables.xlsx; '
                        'S1 is the 07_25 rebuild. Two vintages, not a recompute.'})

    # --- index alignment -----------------------------------------------------------
    d = load(f'{QC}/08_23_2026_handread_index_misalignment.csv')
    for _, r in d.iterrows():
        rows.append({
            'kind': 'index_align', 'PMID': r.PMID, 'author_index': r.author_index,
            'author': f"paper: {r.get('last_read', '')} / data: {r.get('last', '')}",
            'paper_says': r.get('countries_read', ''), 'data_says': r.get('all_countries', ''),
            'confidence': r.get('confidence', ''),
            'affects': 'nothing yet — the join was SKIPPED, not counted as a disagreement',
            'evidence': paper_text(r.PMID, r.author_index)[:600]})

    # --- papers whose linkage the paper simply does not print ----------------------
    pf = load(PAPERS)
    if not pf.empty:
        for _, r in pf[pf.status != 'resolved'].iterrows():
            rows.append({
                'kind': 'unreadable', 'PMID': r.PMID, 'author_index': '',
                'author': f"{r.n_authors} authors", 'paper_says': r.status,
                'data_says': '', 'confidence': '',
                'affects': 'these authors cannot corroborate or contradict S1/S2',
                'evidence': f"linkage={r.linkage}; {str(r.get('layout', ''))[:200]} "
                            f"{str(r.get('note', ''))[:200]}"})

    if not rows:
        print('no conflicts to adjudicate'); return
    out = pd.DataFrame(rows)
    order = {'country': 0, 'institution': 1, 'stratifier': 2, 'wide_vs_s1': 3,
             'index_align': 4, 'unreadable': 5}
    out = out.sort_values(['kind', 'PMID'], key=lambda s: s.map(order) if s.name == 'kind' else s)
    out.to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'{len(out)} decisions -> {OUT}\n')
    print(out.kind.value_counts().to_string())


if __name__ == '__main__':
    main()
