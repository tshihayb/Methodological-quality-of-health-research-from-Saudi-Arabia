# -*- coding: utf-8 -*-
"""Dump batch-1 excluded + correction sheets, and batch-2 disagreement sub-sheets."""
import pandas as pd
pd.set_option('display.width', 260); pd.set_option('display.max_rows', 400)
pd.set_option('display.max_colwidth', 50)

def norm(s):
    return "" if pd.isna(s) else str(s).strip()

print("#"*100); print("BATCH-1  data/screening/f300_ta_ya_TA.xlsx  -> Excluded sheet"); print("#"*100)
ex1 = pd.read_excel("data/screening/f300_ta_ya_TA.xlsx", sheet_name="Excluded")
ex1.columns=[c.strip() for c in ex1.columns]
print("shape", ex1.shape, " Seq range", ex1['Seq'].min(),"-",ex1['Seq'].max())
print("\nStatus_t counts:"); print(ex1['Status_t'].apply(norm).value_counts(dropna=False).to_string())
print("\nStatus_y counts:"); print(ex1['Status_y'].apply(norm).value_counts(dropna=False).to_string())
print("\nReason_t counts:"); print(ex1['Reason for Exclusion_t'].apply(norm).value_counts(dropna=False).to_string())
print("\nReason_y counts:"); print(ex1['Reason for Exclusion_y'].apply(norm).value_counts(dropna=False).to_string())
print("\n--- FULL DUMP batch-1 Excluded ---")
print(ex1[['Seq','PMID','Status_t','Reason for Exclusion_t','Status_y','Reason for Exclusion_y']].to_string(index=False))

print("\n\n"+"#"*100); print("BATCH-1 T_corr (TA corrections)"); print("#"*100)
tc = pd.read_excel("data/screening/f300_ta_ya_TA.xlsx", sheet_name="T_corr"); tc.columns=[c.strip() for c in tc.columns]
print("shape", tc.shape)
print(tc.to_string(index=False))

print("\n\n"+"#"*100); print("BATCH-1 Y_corr (YA corrections)"); print("#"*100)
yc = pd.read_excel("data/screening/f300_ta_ya_TA.xlsx", sheet_name="Y_corr"); yc.columns=[c.strip() for c in yc.columns]
print("shape", yc.shape)
print(yc.to_string(index=False))

print("\n\n"+"#"*100); print("BATCH-1 Included sheet (for corr-author / status columns)"); print("#"*100)
inc1 = pd.read_excel("data/screening/f300_ta_ya_TA.xlsx", sheet_name="Included"); inc1.columns=[c.strip() for c in inc1.columns]
print("shape", inc1.shape, "Seq range", inc1['Seq'].min(),"-",inc1['Seq'].max())
print("cols:", list(inc1.columns))

for sh in ['Talal incl but Yassser excl','Yasser incl but Talal excl','Disagreed reason for exclusion','Disagreed task']:
    print("\n\n"+"#"*100); print("BATCH-2 sub-sheet:", sh); print("#"*100)
    d = pd.read_excel("data/screening/s300_adjudicated.xlsx", sheet_name=sh); d.columns=[c.strip() for c in d.columns]
    print("shape", d.shape)
    print(d.to_string(index=False))
