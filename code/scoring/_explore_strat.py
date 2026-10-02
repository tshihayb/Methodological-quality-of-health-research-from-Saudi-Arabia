# -*- coding: utf-8 -*-
import pandas as pd
KA=dict(dtype=str,keep_default_na=False,na_values=[])
dom=pd.read_csv('data/scoring/07_30_2026_scored_domain.csv',**KA)
pmids=set(dom.PMID.unique())
print('scored papers:',len(pmids))
w=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',**KA)
w=w[w.PMID.isin(pmids)].copy()
print('\n== affiliation stratifiers (n=305) ==')
for c in ['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_ge50']:
    print(c, dict(w[c].value_counts()))
print('\n== Saudi data use: causal_pop / descriptive_pop ==')
print('causal_pop:', dict(w['causal_pop'].value_counts()))
print('descriptive_pop:', dict(w['descriptive_pop'].value_counts()))
# JCR
j=pd.read_csv('data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv',**KA)
j=j[['PMID','jcr_2022_quartile','sjr_best_quartile','journal']]
m=w[['PMID']].merge(j,on='PMID',how='left')
print('\n== JCR quartile coverage among 305 ==')
print('jcr_2022_quartile:', dict(m['jcr_2022_quartile'].fillna('MISSING(no row)').value_counts()))
print('papers with no JCR row:', m['jcr_2022_quartile'].isna().sum())
print('\n== SJR quartile (fallback) ==')
print('sjr_best_quartile:', dict(m['sjr_best_quartile'].fillna('MISSING').value_counts()))
