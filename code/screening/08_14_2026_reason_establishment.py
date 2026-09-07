# NOTE (public repository): 22 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""5-way breakdown of HOW each of the 236 screening-exclusion reasons was established."""
import pandas as pd
def real(s):
    s=str(s).strip().lower()
    if s in ('','nan') or 'corresponding author' in s or 'not from a saudi' in s: return None
    return s
b1=pd.read_excel('data/screening/08_13_2026_batch1_exclusions_LOCKED.xlsx','Batch1_audit_108',dtype=str).fillna('')
b2=pd.read_excel('data/screening/08_13_2026_batch2_exclusions_LOCKED.xlsx','Batch2_audit_128',dtype=str).fillna('')
b1['batch']='b1'; b2['batch']='b2'
A=pd.concat([b1[['batch','PMID','TA_reason_orig','YA_reason_orig','basis']],
             b2[['batch','PMID','TA_reason_orig','YA_reason_orig','basis']]],ignore_index=True)
# reviewer/panel RE-ADJUDICATED (human) — include/exclude conflicts + both-"corr-author" re-checks:
STATUS_ADJ={'STUDY-0769','STUDY-0374','STUDY-0168','STUDY-0849','STUDY-0683',            # batch-1 Saudi_corr + Non-Saudi_corr pool
            'STUDY-0696','STUDY-0572','STUDY-0543','STUDY-0763','STUDY-0211','STUDY-0996','STUDY-0673'}  # batch-2 sub-sheets
T_CORR={'STUDY-0408','STUDY-0348','STUDY-0546','STUDY-0716','STUDY-0169','STUDY-0328'}     # both wrote "corr-author"; TA re-adjudicated
REVIEWER_ADJ=STATUS_ADJ|T_CORR
EXP_OUTCOME={'STUDY-0846','STUDY-0668','STUDY-0500','STUDY-0080'}                      # both INCLUDED; reason set later, no reviewer reason
def cat(r):
    pm=r['PMID']
    if pm in EXP_OUTCOME:  return '5 no reviewer reason -> LLM determined'
    if pm in REVIEWER_ADJ: return '2 disagreement -> reviewer-adjudicated'
    ta,ya=real(r['TA_reason_orig']),real(r['YA_reason_orig'])
    if ta and ya and ta==ya:      return '1 both agreed'
    if ta and ya and ta!=ya:      return '3 reason-disagreement -> LLM adjudicated'
    if ta or ya:                  return '4 one reviewer -> LLM 2nd opinion'
    return '?? unexpected'
A['cat']=A.apply(cat,axis=1)
print("HOW THE 236 SCREENING-EXCLUSION REASONS WERE ESTABLISHED")
print("="*64)
order=['1 both agreed','2 disagreement -> reviewer-adjudicated',
       '3 reason-disagreement -> LLM adjudicated','4 one reviewer -> LLM 2nd opinion',
       '5 no reviewer reason -> LLM determined']
tot=0
for k in order:
    n=int((A.cat==k).sum()); tot+=n; print(f"  {n:>4}  {k}")
print(f"  {tot:>4}  TOTAL")
# how many involve LLM at all
llm=int(A.cat.isin(order[2:]).sum())
print(f"\n  LLM involved (cat 3+4+5): {llm}   |   human-only (cat 1+2): {tot-llm}")
print("\n  by batch:", dict(A.groupby('batch').size()))
A[['batch','PMID','TA_reason_orig','YA_reason_orig','cat']].to_csv('data/screening/08_14_2026_reason_establishment.csv',index=False,encoding='utf-8-sig')
print("wrote data/screening/08_14_2026_reason_establishment.csv")
