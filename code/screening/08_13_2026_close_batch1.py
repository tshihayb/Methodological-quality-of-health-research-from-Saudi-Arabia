# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Close-out checks for batch 1: STUDY-0769 in Saudi_corr? any Saudi_corr excludes? STUDY-0097 provenance."""
import pandas as pd
pd.set_option('display.width',240); pd.set_option('display.max_colwidth',60); pd.set_option('display.max_rows',60)
def G(r,c):
    v=str(r[c]).strip() if c in r.index else ''
    return '' if v.lower()=='nan' else v

P385=set(pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',dtype=str,keep_default_na=False).PMID.astype(str))

# ---- Saudi_corr sheet ----
sc=pd.read_excel('data/screening/f300_ta_ya_clean.xlsx','Saudi_corr',dtype=str).fillna('')
print("Saudi_corr shape", sc.shape)
sc['in_385']=sc.PMID.str.strip().map(lambda p:'Y' if p in P385 else '')
# any that ended up excluded (not in 385)?
notin=sc[sc.in_385!='Y']
print("Saudi_corr papers NOT in 385:", len(notin))
show=[c for c in ['Seq','PMID','Status_t','Status_y','Study Type_t_new','Study Type_y_new','Agreement','Adjudicaiton','in_385'] if c in sc.columns]
print(notin[show].to_string(index=False))
print("\nSTUDY-0769 in Saudi_corr?", 'STUDY-0769' in set(sc.PMID.str.strip()))
print("STUDY-0769 in Non-Saudi_corr?", 'STUDY-0769' in set(pd.read_excel('data/screening/f300_ta_ya_clean.xlsx','Non-Saudi_corr',dtype=str).fillna('').PMID.str.strip()))
# where is STUDY-0769 in the TA file?
for shn in ['Included','Excluded']:
    d=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx',shn,dtype=str).fillna('')
    hit=d[d.PMID.astype(str).str.strip()=='STUDY-0769']
    if len(hit): print(f"\nSTUDY-0769 in TA '{shn}':"); print(hit.to_string(index=False))

# ---- STUDY-0097 provenance ----
print("\n"+"="*70); print("STUDY-0097 provenance"); print("="*70)
# batch-1 excluded row
exc=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Excluded',dtype=str).fillna('')
h=exc[exc.PMID.astype(str).str.strip()=='STUDY-0097']
print("in batch-1 Excluded sheet:"); print(h[['Seq','PMID','Status_t','Reason for Exclusion_t','Status_y','Reason for Exclusion_y']].to_string(index=False))
# top-up pool file
try:
    pool=pd.read_excel('data/screening/incl or excl of pool of papers to include 3 more papers_YA_TA.xlsx',sheet_name=0,dtype=str).fillna('')
    print("\ntop-up pool file cols:", list(pool.columns))
    hp=pool[pool.PMID.astype(str).str.strip()=='STUDY-0097']
    print("STUDY-0097 in top-up pool?", len(hp)>0)
    if len(hp): print(hp.to_string(index=False))
    print("\nAll top-up pool PMIDs:", sorted(pool.PMID.astype(str).str.strip().tolist()))
except Exception as e:
    print("pool read err:", e)
print("\nSTUDY-0097 in 385?", 'STUDY-0097' in P385)
