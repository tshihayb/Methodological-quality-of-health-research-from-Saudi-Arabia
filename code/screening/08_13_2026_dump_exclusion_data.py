# -*- coding: utf-8 -*-
"""Dump the exclusion-reason data for the recount."""
import pandas as pd
pd.set_option('display.width', 240); pd.set_option('display.max_rows', 400)
pd.set_option('display.max_colwidth', 55)

def norm(s):
    if pd.isna(s): return ""
    return str(s).strip()

print("#"*100)
print("BATCH-2  data/screening/s300_adjudicated.xlsx  ->  All sheet")
print("#"*100)
allb2 = pd.read_excel("data/screening/s300_adjudicated.xlsx", sheet_name="All")
allb2.columns = [c.strip() for c in allb2.columns]
# Seq range
print("Seq range:", allb2['Seq'].min(), "-", allb2['Seq'].max(), " n_rows=", len(allb2))
for c in ['Status_ta','Status_ya','Exclusion after adjudication']:
    print(f"\nVALUE COUNTS  [{c}]:")
    print(allb2[c].apply(norm).value_counts(dropna=False).to_string())

# Excluded set: any where adjudicated exclusion is set, OR either reviewer excluded
print("\n--- 'Exclusion after adjudication' non-blank rows: reasons ---")
exadj = allb2[allb2['Exclusion after adjudication'].apply(norm)!=""]
print("n =", len(exadj))
print(exadj['Reason'].apply(norm).value_counts(dropna=False).to_string())

print("\n--- Cross-tab: both reviewers' status ---")
allb2['st_ta']=allb2['Status_ta'].apply(norm); allb2['st_ya']=allb2['Status_ya'].apply(norm)
print(pd.crosstab(allb2['st_ta'], allb2['st_ya']))

# Full per-row dump for batch-2
print("\n--- FULL ROW DUMP (batch-2 All) ---")
cols=['Seq','PMID','Status_ta','Status_ya','Reason for Exclusion_ta','Reason for Exclusion_ya','Exclusion after adjudication','Reason']
print(allb2[cols].to_string(index=False))
