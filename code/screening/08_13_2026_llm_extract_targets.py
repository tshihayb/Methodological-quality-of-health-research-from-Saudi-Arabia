# -*- coding: utf-8 -*-
"""Extract the 3 target groups (7 disagree, 4 no-reason, 56 single-reviewer) + the 169 agreed
few-shot examples; fetch titles (all) + abstracts (targets)."""
import pandas as pd, urllib.request, json, time

prov=pd.read_csv('data/screening/08_13_2026_reason_provenance.csv',dtype=str).fillna('')
b1=pd.read_excel('data/screening/08_13_2026_batch1_exclusions_LOCKED.xlsx','Batch1_audit_108',dtype=str).fillna('')
b2=pd.read_excel('data/screening/08_13_2026_batch2_exclusions_LOCKED.xlsx','Batch2_audit_128',dtype=str).fillna('')
b1['batch']='batch-1'; b2['batch']='batch-2'
info=pd.concat([b1[['batch','PMID','TA_reason_orig','YA_reason_orig','FINAL_reason','basis']],
                b2[['batch','PMID','TA_reason_orig','YA_reason_orig','FINAL_reason','basis']]],ignore_index=True)
d=prov.merge(info,on=['batch','PMID'],how='left',suffixes=('','_i'))
# prefer merged FINAL_reason
d['FINAL_reason']=d['FINAL_reason_i'].where(d['FINAL_reason_i'].notna(),d['FINAL_reason'])

def grp(row):
    p=row['prov']
    if p=='two reviewers (reconciled)': return 'A_disagree(7)'
    if p=='neither / panel':            return 'B_noreason(4)'
    if p=='one reviewer':               return 'C_single(56)'
    return ''
d['group']=d.apply(grp,axis=1)
targets=d[d.group!=''].copy()
agreed=d[d.prov=='two reviewers (agreed)'].copy()
print("targets:",len(targets)," | groups:",dict(targets.group.value_counts()))
print("agreed few-shot:",len(agreed))

# reviewer's substantive recorded reason (for the single-reviewer agreement check)
def canon(s):
    s=str(s).strip().lower()
    if s in ('','nan') or 'corresponding author' in s or 'not from a saudi' in s: return ''
    if 'non-human' in s: return 'Non-human / laboratory'
    if 'simulation' in s or 'emperical' in s or 'empirical' in s: return 'Non-empirical (protocol/simulation)'
    if 'narrative review' in s or 'systematic review' in s or s=='review': return 'Review (narrative/systematic)'
    if 'qualitative' in s: return 'Qualitative research'
    if 'case report' in s or 'case series' in s: return 'Case report / series'
    if 'non-health' in s or 'non health' in s: return 'Non-health topic'
    return s
def revreason(r):
    ta,ya=canon(r['TA_reason_orig']),canon(r['YA_reason_orig'])
    if ta and ya: return ta+' | '+ya
    return ta or ya or '(from re-check/pool)'
targets['reviewer_reason']=targets.apply(revreason,axis=1)

targets[['group','batch','PMID','TA_reason_orig','YA_reason_orig','reviewer_reason','FINAL_reason','basis']].to_csv(
    'data/screening/08_13_2026_llm_targets.csv',index=False,encoding='utf-8-sig')
agreed[['batch','PMID','FINAL_reason']].to_csv('data/screening/08_13_2026_llm_agreed_fewshot.csv',index=False,encoding='utf-8-sig')

# ---- fetch titles (all 236) + abstracts (67 targets) ----
allids=list(d.PMID); tgtids=list(targets.PMID)
def esummary(ids):
    out={}
    for i in range(0,len(ids),150):
        u='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&retmode=json&id='+','.join(ids[i:i+150])
        r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read().decode('utf-8','replace'))
        res=r.get('result',{})
        for pm in res.get('uids',[]): out[pm]=(res[pm].get('source',''),res[pm].get('title',''),res[pm].get('pubtype',[]))
        time.sleep(0.34)
    return out
tt=esummary(allids)
pd.DataFrame([{'PMID':k,'journal':v[0],'title':v[1],'pubtype':'; '.join(v[2]) if isinstance(v[2],list) else v[2]} for k,v in tt.items()]).to_csv(
    'data/screening/08_13_2026_all236_titles.csv',index=False,encoding='utf-8-sig')
print("wrote titles for",len(tt),"papers")

# abstracts for targets -> file
u='https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&rettype=abstract&retmode=text&id='+','.join(tgtids)
ab=urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=60).read().decode('utf-8','replace')
open('data/screening/08_13_2026_target_abstracts.txt','w',encoding='utf-8').write(ab)
print("wrote target abstracts (%d chars) for %d papers"%(len(ab),len(tgtids)))
print("\nwrote data/screening/08_13_2026_llm_targets.csv + _llm_agreed_fewshot.csv + _all236_titles.csv")
