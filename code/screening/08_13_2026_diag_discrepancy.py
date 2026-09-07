# -*- coding: utf-8 -*-
"""Compare my excluded-at-screening set against the ledger's, and dump CONFLICT/flagged papers."""
import pandas as pd
pd.set_option('display.width',240); pd.set_option('display.max_colwidth',70); pd.set_option('display.max_rows',60)

led = pd.read_excel('data/screening/08_12_2026_screening_ledger.xlsx','screening_ledger', dtype=str).fillna('')
ledger_excl = set(led[led.final_disposition=='Excluded at screening'].PMID)
ftnf = set(led[led.final_disposition=='Excluded — full text not found'].PMID)
print("ledger 'Excluded at screening' n =", len(ledger_excl))
print("ledger full-text-not-found:", sorted(ftnf))
print()
# which batch are the full-text-not-found in?
print(led[led.PMID.isin(ftnf)][['Seq','PMID','screening_batch','TA_exclusion_reason','YA_exclusion_reason','full_text_found','comments']].to_string(index=False))
print()

# my set
mine = pd.read_csv('data/screening/08_13_2026_exclusion_reason_recount_audit.csv', dtype=str).fillna('')
myset = set(mine.PMID)
print("my set n =", len(myset))
print("IN MINE not in ledger:", sorted(myset - ledger_excl))
print("IN ledger not in mine:", sorted(ledger_excl - myset))
print()
# batch-1 Included-sheet paper that is excluded-at-screening
inc1 = pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Included', dtype=str).fillna('')
inc1_pmids = set(inc1.PMID.str.strip())
b1_ledger_excl = led[(led.screening_batch.str.startswith('batch-1')) & (led.final_disposition=='Excluded at screening')]
print("batch-1 excluded-at-screening from Included sheet:")
print(b1_ledger_excl[b1_ledger_excl.PMID.isin(inc1_pmids)][['Seq','PMID','TA_status','YA_status','TA_task','YA_task','comments']].to_string(index=False))
print()
# dump CONFLICT + flagged
print("="*70); print("CONFLICT / flagged rows in my audit"); print("="*70)
fl = mine[mine.needs_verification!='No']
print(fl[['Seq','PMID','batch','TA_reason_orig','YA_reason_orig','tcorr','assignment_method','FINAL_reason','evidence']].to_string(index=False))
