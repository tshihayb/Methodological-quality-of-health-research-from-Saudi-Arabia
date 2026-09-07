# NOTE (public repository): 22 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Batch-2 exclusion reasons: apply established principles, compute tally, list decisions/borderlines."""
import pandas as pd
NH='Non-human / laboratory'; REV='Review (narrative/systematic)'; QUAL='Qualitative research'
NE='Non-empirical (protocol/simulation)'; CR='Case report / series'; NHL='Non-health topic'

rec = pd.read_csv('data/screening/08_13_2026_exclusion_reason_recount_audit.csv', dtype=str).fillna('')
b2 = rec[rec.batch=='batch-2'].copy()
b2['Seq_n']=pd.to_numeric(b2['Seq'],errors='coerce')
print("batch-2 screening exclusions:", len(b2))

# ---- final resolution map (PMID -> (reason, basis)) ----
B2 = {
 # Tier A — reason disagreement -> one reviewer reason / harmonize
 'STUDY-0582':(NH ,'disagreement -> TA Non-human (computational SARS-CoV-2 drug study; biomedical in-silico)'),
 'STUDY-0684':(NE ,'disagreement -> TA Non-empirical (forensic-training commentary; not original research)'),
 'STUDY-0858':(NHL,'harmonize Non-health (Nat Hum Behav: glossary of open-scholarship terms; not health/not a study)'),
 # Tier B — reviewer wrote a comment: follow it
 'STUDY-0998':(NE ,'reviewer comment "RCT protocol" -> Non-empirical (protocol), not Qualitative'),
 'STUDY-0545':(NHL,'reviewer comment "cyber security...not health" -> Non-health'),
 'STUDY-0873':(NHL,'reviewer comment "languages research" -> Non-health'),
 'STUDY-0754':(NHL,'reviewer comment "not health research" -> Non-health'),
 'STUDY-0483':(NHL,'reviewer comment "non-health" -> Non-health'),
 # Tier C — TA-only (YA status blank) -> TA reason
 'STUDY-0323':(NH ,'TA Non-human (YA blank; NB flagged "used in reviewer testing round 1")'),
 'STUDY-0874':(NH ,'TA Non-human (YA blank)'),
 'STUDY-0726':(QUAL,'TA Qualitative (YA blank)'),
 'STUDY-0470':(NH ,'TA Non-human (YA blank)'),
 'STUDY-0054':(NH ,'TA Non-human (YA blank)'),
 'STUDY-0435':(NHL,'TA Non-health (YA blank)'),
 'STUDY-0652':(NH ,'TA Non-human (YA blank)'),
 # Harmonize — clearly non-health (were coded Non-human)
 'STUDY-0278':(NHL,'harmonize Non-health (Sensors: electricity load forecasting; energy/CS)'),
 'STUDY-0602':(NHL,'harmonize Non-health (Sensors: Cloud-of-Things crowd monitoring; IoT)'),
 'STUDY-0353':(NHL,'harmonize Non-health (Comput Intell Neurosci: blockchain economics)'),
 'STUDY-0534':(NHL,'harmonize Non-health (Environ Technol: ML for environmental pollution)'),
 'STUDY-0392':(NHL,'harmonize Non-health (Sensors: LiDAR assistive edge device; engineering) [BORDERLINE]'),
}
BORDERLINE = {'STUDY-0392':'assistive tech for visually-impaired mobility, but the contribution is an engineering device',
              'STUDY-0635':'electrochemical biosensor material ([NAME-REDACTED]) — kept Non-human as biomedical-adjacent; could be Non-health'}

b2['FINAL_reason']=b2.apply(lambda r: B2[r['PMID']][0] if r['PMID'] in B2 else r['RESOLVED_reason'], axis=1)
b2['basis']=b2.apply(lambda r: B2[r['PMID']][1] if r['PMID'] in B2 else 'agreed / adjudicated on record', axis=1)

ORDER=[NH,NHL,REV,QUAL,NE,CR]
t=b2['FINAL_reason'].value_counts()
print("\n"+"="*56); print("BATCH-2 tally (proposed) — %d"%len(b2)); print("="*56)
tot=0
for k in ORDER:
    print(f"  {k:<38} {int(t.get(k,0)):>4}"); tot+=int(t.get(k,0))
print(f"  {'TOTAL':<38} {tot:>4}")
extra=[k for k in t.index if k not in ORDER]
if extra: print("  UNEXPECTED:",{k:int(t[k]) for k in extra})

print("\n--- DECISIONS APPLIED (15 flagged + 5 harmonized non-human->non-health) ---")
for pm,(rn,bs) in B2.items():
    seq=b2[b2.PMID==pm]['Seq'].values
    print(f"  {pm}  -> {rn:<26} | {bs}")
print("\n--- BORDERLINE (your call, like STUDY-0219 was) ---")
for pm,note in BORDERLINE.items():
    cur = b2[b2.PMID==pm]['FINAL_reason'].values
    print(f"  {pm}  currently {cur[0] if len(cur) else '?'}  — {note}")

b2.to_csv('data/screening/08_13_2026_batch2_proposed.csv', index=False, encoding='utf-8-sig')
print("\nwrote data/screening/08_13_2026_batch2_proposed.csv")
