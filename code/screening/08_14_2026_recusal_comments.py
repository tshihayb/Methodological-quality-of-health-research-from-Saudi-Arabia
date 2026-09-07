# NOTE (public repository): 5 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Pull the recusal explanation (comment field) for each recused paper from the recusing reviewer's responses."""
import pandas as pd, glob, os
PMID_COL='What was the PMID of the research paper?'
REC_COL='Do you wish to recuse yourself from reviewing this study for any reason?'
CMT_COL='Do you have any comments?'
REL_COL='What is/are the comment/comments related to?'
recusals=[('8','R7','STUDY-0956'),('13','R12','STUDY-0275'),('7','R6','STUDY-0320'),
          ('13','R12','STUDY-0927'),('2','R2','STUDY-0183')]

def load_reviewer(n):
    frames=[]
    for pat in [f'05_19_2025_Reviewer_{n}.xlsx',f'04_15_2026_Reviewer_{n}.xlsx',f'08_08_2026_Reviewer_{n}.csv']:
        if os.path.exists(pat):
            d=pd.read_csv(pat,dtype=str) if pat.endswith('.csv') else pd.read_excel(pat,dtype=str)
            d['__src']=pat; frames.append(d)
    return frames

def getcol(d,name):
    for c in d.columns:
        if str(c).strip()==name: return c
    # fuzzy
    for c in d.columns:
        if name[:30].lower() in str(c).strip().lower(): return c
    return None

for n,name,pmid in recusals:
    print('='*90); print(f'RECUSAL: reviewer {n} ({name})  paper {pmid}')
    found=False
    for d in load_reviewer(n):
        pc=getcol(d,PMID_COL)
        if pc is None: continue
        hit=d[d[pc].astype(str).str.strip()==pmid]
        for _,r in hit.iterrows():
            found=True
            rc=getcol(d,REC_COL); cc=getcol(d,CMT_COL); rl=getcol(d,REL_COL)
            print("  [src %s]" % r['__src'])
            print("    recuse? : %s" % (r[rc] if rc else '(col?)'))
            print("    comment : %s" % (r[cc] if cc else '(col?)'))
            print("    related : %s" % (r[rl] if rl else '(col?)'))
    if not found: print("  (no row found for this PMID in this reviewer's exports)")
