# NOTE (public repository): 8 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Build the 385 WIDE analysis dataset = pivot of the 385 long + affiliation stratifiers.
# 382 papers get stratifiers from data/authors/07_16_2026_saudi_affiliation_variables.xlsx; the 3 newly-included
# papers (STUDY-0658, STUDY-0401, STUDY-0161) get stratifiers derived from the 385 author-country work.
import pandas as pd
import warnings; warnings.simplefilter("ignore")

AFF=['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_authors',
     'pct_saudi_ge50','pct_saudi_cat3','pct_saudi_cat4','n_authors','n_saudi_authors','pct_saudi_reliable']

long=pd.read_csv("data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv", dtype=str)
long["PMID"]=long.PMID.astype(str)
wide=long.pivot_table(index="PMID", columns="variable", values="final", aggfunc="first").reset_index()
st=long.drop_duplicates("PMID").set_index("PMID").Study_Type
wide["Study_Type"]=wide.PMID.map(st)

aff=pd.read_excel("data/authors/07_16_2026_saudi_affiliation_variables.xlsx"); aff["PMID"]=aff.PMID.astype(str)
aff=aff[["PMID"]+AFF]

# --- 3 newly-included papers: derived stratifiers. VERIFIED 2026-08-12 vs PubMed + PDFs (all correct):
#     STUDY-0658 n_saudi=1 = Quhal (#6, dual affil: Vienna + King Fahad Specialist Hospital, Dammam);
#              first=Laukhtina/AT, last=corr=Shariat/Vienna -> all non-Saudi.
#     STUDY-0401 n_saudi=1 = Al-Sofiani (#16); first=last=corr=Klonoff/US(corr)/Kovatchev -> non-Saudi.
#     STUDY-0161 all-Saudi (8/8) -> first/last/corr Saudi. ---
new=pd.DataFrame([
 {"PMID":"STUDY-0658","first_author_saudi":0,"last_author_saudi":0,"corresponding_author_saudi":0,
  "pct_saudi_authors":round(100*1/23,1),"pct_saudi_ge50":"<50%","pct_saudi_cat3":"<33%","pct_saudi_cat4":"<25%",
  "n_authors":23,"n_saudi_authors":1,"pct_saudi_reliable":True},
 {"PMID":"STUDY-0401","first_author_saudi":0,"last_author_saudi":0,"corresponding_author_saudi":0,
  "pct_saudi_authors":round(100*1/94,1),"pct_saudi_ge50":"<50%","pct_saudi_cat3":"<33%","pct_saudi_cat4":"<25%",
  "n_authors":94,"n_saudi_authors":1,"pct_saudi_reliable":True},
 {"PMID":"STUDY-0161","first_author_saudi":1,"last_author_saudi":1,"corresponding_author_saudi":1,
  "pct_saudi_authors":100.0,"pct_saudi_ge50":">=50%","pct_saudi_cat3":">67%","pct_saudi_cat4":">75%",
  "n_authors":8,"n_saudi_authors":8,"pct_saudi_reliable":True},
])
aff=pd.concat([aff[~aff.PMID.isin(new.PMID)], new], ignore_index=True)

wide=wide.merge(aff, on="PMID", how="left")
front=["PMID","Study_Type"]+AFF
wide=wide[front+[c for c in wide.columns if c not in front]]
wide.to_csv("data/analysis/08_08_2026_ANALYSIS_DATASET_wide_385.csv", index=False, encoding="utf-8")

miss=wide[AFF].isna().sum()
print("WIDE 385: %d papers x %d cols" % (len(wide), len(wide.columns)))
print("Study_Type:", wide.Study_Type.value_counts().to_dict())
print("affiliation missing per col:", {c:int(miss[c]) for c in AFF if miss[c]>0} or "none")
print("stratifier completeness:", {c:int(wide[c].notna().sum()) for c in ['first_author_saudi','corresponding_author_saudi','pct_saudi_ge50','n_authors']})
# sanity: the 8 batch-6 papers present with stratifiers
b6=["STUDY-0401","STUDY-0658","STUDY-0161","STUDY-0275","STUDY-0449","STUDY-0320","STUDY-0927","STUDY-0905"]
print("\nbatch-6 papers in wide:", wide[wide.PMID.isin(b6)][["PMID","Study_Type","first_author_saudi","corresponding_author_saudi","pct_saudi_ge50","n_authors"]].to_string(index=False))
