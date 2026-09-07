# NOTE (public repository): 9 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Fetch titles+journals for all 'Non-human'-coded exclusions and flag clearly-non-health ones."""
import pandas as pd, urllib.request, json, time

rec = pd.read_csv('data/screening/08_13_2026_exclusion_reason_recount_audit.csv', dtype=str).fillna('')
# apply the locked batch-1 decisions to RESOLVED so the non-human set is current
B1_FIX = {'STUDY-0836':'Non-human / laboratory','STUDY-0190':'Non-human / laboratory',
          'STUDY-0219':'Non-human / laboratory','STUDY-0681':'Non-human / laboratory',
          'STUDY-0769':'Non-human / laboratory','STUDY-0374':'Non-human / laboratory',
          'STUDY-0168':'Non-human / laboratory','STUDY-0849':'Non-human / laboratory',
          'STUDY-0683':'Review (narrative/systematic)'}
rec['RES']=rec.apply(lambda r: B1_FIX.get(r['PMID'], r['RESOLVED_reason']), axis=1)
nh = rec[rec.RES=='Non-human / laboratory'][['PMID','batch']].copy()
print("Non-human-coded exclusions:", len(nh), " | by batch:", nh.batch.value_counts().to_dict())

ids = nh.PMID.tolist()
titles={}
for i in range(0,len(ids),100):
    chunk=ids[i:i+100]
    url='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id='+','.join(chunk)
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    d=json.loads(urllib.request.urlopen(req,timeout=40).read().decode('utf-8','replace'))
    res=d.get('result',{})
    for pm in res.get('uids',[]):
        titles[pm]=(res[pm].get('source',''), res[pm].get('title',''))
    time.sleep(0.34)

# heuristic flag for clearly-non-health journals/keywords
NONHEALTH_JOURNALS = ['sensors','ieee','access','electronics','applied sciences','mathematics','symmetry',
    'computers','computer','informatics','sustainability','energies','processes','polymers','materials',
    'water','chemosphere','environmental','psycholinguist','linguist','education','arabica','entropy',
    'algorithms','machine learning','neural','fractals','micromachines','photonics','remote sens']
NONHEALTH_KW = ['network','iot','internet of things','blockchain','encryption','cryptograph','cyber',
    'smart city','vehicular','face recognition','traffic','wireless','5g','6g','antenna','image classif',
    'deep learning model','machine learning','linguistic','language','glossary','anomaly detection',
    'intrusion','authentication','privacy','optimization algorithm','routing','sentiment']
rows=[]
for pm in ids:
    src,tt=titles.get(pm,('',''))
    s=(src+' '+tt).lower()
    jflag=any(j in src.lower() for j in NONHEALTH_JOURNALS)
    kflag=any(k in s for k in NONHEALTH_KW)
    rows.append(dict(PMID=pm, batch=nh.set_index('PMID').loc[pm,'batch'], journal=src, title=tt[:95],
                     candidate_nonhealth='YES' if (jflag or kflag) else ''))
out=pd.DataFrame(rows)
cand=out[out.candidate_nonhealth=='YES']
print("\nCANDIDATE non-health (needs eyeball):", len(cand), " | by batch:", cand.batch.value_counts().to_dict())
print("="*70)
for b in ['batch-1','batch-2']:
    sub=cand[cand.batch==b]
    print(f"\n--- {b}  ({len(sub)}) ---")
    for _,r in sub.iterrows(): print(f"  {r['PMID']}  [{r['journal']}]  {r['title']}")
out.to_csv('data/screening/08_13_2026_nonhuman_titles.csv', index=False, encoding='utf-8-sig')
print("\nwrote data/screening/08_13_2026_nonhuman_titles.csv  (full list of",len(out),"non-human papers)")
