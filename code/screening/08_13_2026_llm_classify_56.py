# NOTE (public repository): 56 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""LLM (assistant) fresh determination for the 56 single-reviewer exclusions, vs the one reviewer's reason."""
import pandas as pd
NH='Non-human / laboratory'; REV='Review (narrative/systematic)'; QUAL='Qualitative research'
NE='Non-empirical (protocol/simulation)'; CR='Case report / series'; NHL='Non-health topic'

t=pd.read_csv('data/screening/08_13_2026_llm_targets.csv',dtype=str).fillna('')
ti=pd.read_csv('data/screening/08_13_2026_all236_titles.csv',dtype=str).fillna('')
c=t[t.group=='C_single(56)'].merge(ti[['PMID','journal','title']],on='PMID',how='left')

# reviewer reason for the 10 corr-author re-check (pool/T_corr) papers
REV_POOL={'STUDY-0374':NH,'STUDY-0168':NH,'STUDY-0683':REV,'STUDY-0769':NH,'STUDY-0408':NH,
          'STUDY-0348':NH,'STUDY-0546':QUAL,'STUDY-0716':NH,'STUDY-0169':NH,'STUDY-0328':NE}
c['rev']=c.apply(lambda r: REV_POOL.get(r['PMID'], r['reviewer_reason']), axis=1)

# my fresh determination (from title + abstract, grounded in the agreed anchors)
MY={
'STUDY-0811':NH,'STUDY-0716':NHL,'STUDY-0374':NH,'STUDY-0169':NH,'STUDY-0348':NH,'STUDY-0301':NHL,'STUDY-0363':NHL,
'STUDY-0546':QUAL,'STUDY-0247':NH,'STUDY-0168':NH,'STUDY-0937':NE,'STUDY-0529':NH,'STUDY-0599':NH,'STUDY-0675':NH,
'STUDY-0588':NH,'STUDY-0964':REV,'STUDY-0218':NE,'STUDY-0683':NE,'STUDY-0087':NH,'STUDY-0097':NH,'STUDY-0524':NH,
'STUDY-0718':NH,'STUDY-0798':NH,'STUDY-0039':NHL,'STUDY-0779':REV,'STUDY-0328':NE,'STUDY-0408':NH,'STUDY-0496':NH,
'STUDY-0616':NH,'STUDY-0881':NHL,'STUDY-0075':NH,'STUDY-0570':REV,'STUDY-0884':NHL,'STUDY-0849':NH,'STUDY-0769':NH,
'STUDY-0765':NHL,'STUDY-0696':NE,'STUDY-0572':NHL,'STUDY-0998':NE,'STUDY-0545':NHL,'STUDY-0873':NHL,'STUDY-0543':NH,
'STUDY-0763':NH,'STUDY-0754':NHL,'STUDY-0211':NHL,'STUDY-0483':NHL,'STUDY-0673':NH,'STUDY-0586':NHL,'STUDY-0996':NE,
'STUDY-0323':NH,'STUDY-0874':NHL,'STUDY-0726':QUAL,'STUDY-0470':NHL,'STUDY-0054':NH,'STUDY-0435':NHL,'STUDY-0652':NH}
# already applied as Non-health in the locked files (my heuristic harmonization)
ALREADY={'STUDY-0301','STUDY-0363','STUDY-0881','STUDY-0545','STUDY-0873','STUDY-0754','STUDY-0483','STUDY-0586','STUDY-0998','STUDY-0435'}
c['mine']=c.PMID.map(MY)
c['agree']=c.apply(lambda r:'AGREE' if r['mine']==r['rev'] else 'DIFFER', axis=1)
c['status']=c.apply(lambda r: '' if r['agree']=='AGREE' else ('(already in lock)' if r['PMID'] in ALREADY else 'NEW correction'), axis=1)

n=len(c); ag=(c.agree=='AGREE').sum()
print(f"56 single-reviewer:  AGREE {ag}  DIFFER {n-ag}   (exact-category agreement {ag/n:.0%})")
print()
diff=c[c.agree=='DIFFER']
print("DIFFERENCES (my determination vs the one reviewer):")
for _,r in diff.sort_values('status').iterrows():
    print(f"  {r['PMID']}  mine={r['mine'][:22]:<22} rev={r['rev'][:26]:<26} {r['status']:<16} {r['title'][:52]}")
print()
# nature of differences
nh_split=diff[(diff.mine==NHL)&(diff.rev==NH)]
ne_split=diff[(diff.mine==NHL)&(diff.rev==NE)]
other=diff[~((diff.mine==NHL)&(diff.rev.isin([NH,NE])))]
print(f"  of the {len(diff)} differences:")
print(f"    {len(nh_split)+len(ne_split)}  I split Non-health out of the reviewer's broad 'non-human'/'non-empirical'")
print(f"    {len(other)}  design refinements (protocol/qualitative/review):")
for _,r in other.iterrows(): print(f"       {r['PMID']}  mine={r['mine'][:20]:<20} rev={r['rev'][:20]}")
print()
new=diff[diff.status=='NEW correction']
print(f"NEW corrections not yet in the locked files: {len(new)}")
print("  PMIDs:", ', '.join(new.PMID))

c[['PMID','journal','title','rev','mine','agree','status']].to_csv('data/screening/08_13_2026_llm_56_classification.csv',index=False,encoding='utf-8-sig')
print("\nwrote data/screening/08_13_2026_llm_56_classification.csv")
