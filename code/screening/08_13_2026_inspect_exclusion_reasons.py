# -*- coding: utf-8 -*-
"""Inspect the exclusion-reason columns in batch-1 and batch-2 screening files."""
import pandas as pd, sys
pd.set_option('display.width', 200); pd.set_option('display.max_columns', 60)
pd.set_option('display.max_colwidth', 60)

def show(path):
    print("="*90); print("FILE:", path)
    xl = pd.ExcelFile(path)
    print("SHEETS:", xl.sheet_names)
    for sh in xl.sheet_names:
        df = xl.parse(sh)
        print("-"*80); print(f"  SHEET '{sh}'  shape={df.shape}")
        print("  COLS:", list(df.columns))

show("data/screening/f300_ta_ya_TA.xlsx")
show("data/screening/s300_adjudicated.xlsx")
