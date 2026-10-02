# -*- coding: utf-8 -*-
"""Trace which corr-author-not-Saudi exclusions reached the Non-Saudi_corr re-check pool."""
import pandas as pd
pd.set_option('display.width',240); pd.set_option('display.max_rows',200); pd.set_option('display.max_colwidth',52)

def G(r,c):
    v=str(r[c]).strip() if c in r.index else ''
    return '' if v.lower()=='nan' else v

# ---- canonical 385 ----
P385=set(pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',dtype=str,keep_default_na=False).PMID.astype(str))

# ---- clean file: the two groups ----
ns=pd.read_excel('data/screening/f300_ta_ya_clean.xlsx','Non-Saudi_corr',dtype=str).fillna('')
sc=pd.read_excel('data/screening/f300_ta_ya_clean.xlsx','Saudi_corr',dtype=str).fillna('')
ns_ids=set(ns.PMID.str.strip()); sc_ids=set(sc.PMID.str.strip())
print("Non-Saudi_corr pool n=%d | Saudi_corr n=%d | overlap=%d"%(len(ns_ids),len(sc_ids),len(ns_ids&sc_ids)))

# ---- TA file: excluded + corr sheets ----
exc=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Excluded',dtype=str).fillna('')
tcorr=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','T_corr',dtype=str).fillna('')
ycorr=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Y_corr',dtype=str).fillna('')
def is_corr(s): return 'corresponding author' in s.lower() or 'not from a saudi' in s.lower()
TA_corr={G(r,'PMID') for _,r in exc.iterrows() if is_corr(G(r,'Reason for Exclusion_t'))}
YA_corr={G(r,'PMID') for _,r in exc.iterrows() if is_corr(G(r,'Reason for Exclusion_y'))}
tcorr_ids=set(tcorr.PMID.str.strip()); ycorr_ids=set(ycorr.PMID.str.strip())
print("Excluded-sheet corr-author: TA=%d YA=%d union=%d | T_corr=%d Y_corr=%d"%(
    len(TA_corr),len(YA_corr),len(TA_corr|YA_corr),len(tcorr_ids),len(ycorr_ids)))
union_corr=TA_corr|YA_corr

# ---- which corr-author exclusions reached the Non-Saudi_corr pool? ----
inpool = union_corr & ns_ids
notpool = union_corr - ns_ids
print("\nCorr-author exclusions: %d total | %d reached Non-Saudi_corr pool | %d did NOT"%(
    len(union_corr),len(inpool),len(notpool)))

# For those NOT in the pool: what was the OTHER reviewer's (non-corr) reason?
excmap={G(r,'PMID'):(G(r,'Reason for Exclusion_t'),G(r,'Reason for Exclusion_y')) for _,r in exc.iterrows()}
print("\n--- corr-author excl NOT in the re-check pool (test the 'pre-filtered by another criterion' hunch) ---")
rows=[]
for pm in sorted(notpool):
    rt,ry=excmap.get(pm,('',''))
    other = ry if is_corr(rt) and not is_corr(ry) else (rt if is_corr(ry) and not is_corr(rt) else (rt+' / '+ry))
    both_corr = is_corr(rt) and is_corr(ry)
    rows.append(dict(PMID=pm,TA_reason=rt,YA_reason=ry,both_corr='BOTH corr' if both_corr else '',
                     other_reason=other, in_385='Y' if pm in P385 else '',
                     in_Saudi_corr='Y' if pm in sc_ids else ''))
nd=pd.DataFrame(rows)
print(nd.to_string(index=False))
print("\ncount both-corr (no other reason) among not-in-pool:", (nd.both_corr=='BOTH corr').sum())
print("count with an OTHER reason among not-in-pool:", (nd.both_corr=='').sum())

# ---- the Non-Saudi_corr pool itself: decisions + reasons + 385 outcome ----
print("\n"+"="*80); print("Non-Saudi_corr RE-CHECK POOL (70) — full dump"); print("="*80)
ns2=ns.copy()
ns2['in_385']=ns2.PMID.str.strip().map(lambda p:'Y' if p in P385 else '')
show=[c for c in ['Seq','PMID','Status_y','Status_t','Study Type_y_new','Study Type_t_new','Agreement','Adjudicaiton','in_385'] if c in ns2.columns]
print(ns2[show].to_string(index=False))
