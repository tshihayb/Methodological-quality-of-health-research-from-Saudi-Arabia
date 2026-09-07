# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Classify the 236 main-sample exclusions by REASON provenance, using the locked workbooks
(which carry `basis` and batch-2 `reason_source`)."""
import pandas as pd

def real(s):
    s=str(s).strip().lower()
    if s in ('','nan'): return None
    if 'corresponding author' in s or 'not from a saudi' in s: return None  # corr-author dropped
    return s

# ---- batch 1: classify from basis + original reviewer reasons ----
b1=pd.read_excel('data/screening/08_13_2026_batch1_exclusions_LOCKED.xlsx','Batch1_audit_108',dtype=str).fillna('')
def b1prov(r):
    b=str(r['basis']).lower(); ta=real(r['TA_reason_orig']); ya=real(r['YA_reason_orig'])
    llm = 'llm' if 'harmoniz' in b else ''
    if 'pool' in b or 'saudi_corr' in b:            return pd.Series(['one reviewer',llm])   # corr-author re-check (YA)
    if 'folded from target' in b:                   return pd.Series(['one reviewer',llm])   # STUDY-0097 TA + panel
    if ta and ya:                                   return pd.Series(['two reviewers (agreed)' if ta==ya else 'two reviewers (reconciled)',llm])
    if ta or ya:                                    return pd.Series(['one reviewer',llm])
    # batch-1 has no exp/outcome step: both original reasons were "corr-author" -> reason came from TA's T_corr re-adjudication
    return pd.Series(['one reviewer',llm])
b1[['prov','llm']]=b1.apply(b1prov,axis=1); b1['batch']='batch-1'

# ---- batch 2: use the reason_source column directly ----
b2=pd.read_excel('data/screening/08_13_2026_batch2_exclusions_LOCKED.xlsx','Batch2_audit_128',dtype=str).fillna('')
def b2prov(r):
    rs=str(r['reason_source']).lower(); b=str(r['basis']).lower()
    llm='llm' if 'harmoniz' in b else ''
    if rs.startswith('both'):
        ta=real(r['TA_reason_orig']); ya=real(r['YA_reason_orig'])
        return pd.Series(['two reviewers (agreed)' if (ta and ya and ta==ya) else 'two reviewers (reconciled)',llm])
    if rs.startswith('ta') or rs.startswith('ya'): return pd.Series(['one reviewer',llm])
    return pd.Series(['neither / panel',llm])       # adjudicated exp/outcome
b2[['prov','llm']]=b2.apply(b2prov,axis=1); b2['batch']='batch-2'

both=pd.concat([b1[['batch','PMID','FINAL_reason','prov','llm']],
                b2[['batch','PMID','FINAL_reason','prov','llm']]],ignore_index=True)

def tab(df,label):
    ag=int((df.prov=='two reviewers (agreed)').sum()); rc=int((df.prov=='two reviewers (reconciled)').sum())
    one=int((df.prov=='one reviewer').sum()); nn=int((df.prov=='neither / panel').sum())
    print(f"{label:<10} two={ag+rc:>4} (agreed {ag}, reconciled {rc})  one={one:>4}  neither/panel={nn:>3}   (n={len(df)})")
    return ag+rc,one,nn
print("="*60); print("REASON PROVENANCE — main sample"); print("="*60)
tab(b1,'batch-1'); tab(b2,'batch-2'); print('-'*40); tw,on,nn=tab(both,'COMBINED')
print()
print("So of the 236 main-sample exclusions, the reason came from:")
print(f"  BOTH reviewers:  {tw}")
print(f"  ONE reviewer:    {on}")
print(f"  NEITHER (both had included; excluded later at exposure/outcome): {nn}")
print()
llm=both[both.llm=='llm']
print(f"Cross-cut — final reason LABEL refined from the abstract by the assistant/LLM: {len(llm)}")
print(f"  (all were reviewer-flagged as excluded — reviewers' reason was 'non-human'/similar, re-labelled Non-health)")
print(f"  by batch: {dict(llm.batch.value_counts())}")
print(f"  PMIDs: {', '.join(sorted(llm.PMID))}")

both.to_csv('data/screening/08_13_2026_reason_provenance.csv',index=False,encoding='utf-8-sig')
print("\nwrote data/screening/08_13_2026_reason_provenance.csv")
