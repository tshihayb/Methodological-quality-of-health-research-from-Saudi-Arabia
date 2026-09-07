# NOTE (public repository): 19 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# SCREENING LEDGER v2 — anchored on the ordered 1000-paper sampling frame.
# Frame/order: data/screening/first1000sample_21-12-23.xlsx (Seq 1-1000).  Screening decisions (authoritative):
#   batch-1 (Seq 1-300) = data/screening/f300_ta_ya_TA.xlsx (Included + Excluded sheets, full first batch)
#   batch-2 (Seq 301-621) = data/screening/s300_adjudicated.xlsx (All + disagreement sub-sheets)
#   Seq 622-1000 = never screened (sampling target of 385 includes reached at Seq 621)
# + the 3-more panel pool (papers NOT in the 1000). in_final_385 is authoritative from the analysis set.
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

w=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',dtype=str,keep_default_na=False)
P385=set(w.PMID.astype(str))
LATE={'STUDY-0956':'Excluded — co-authored by YA (conflict of interest)',
      'STUDY-0136':'Excluded — no Saudi affiliation','STUDY-0478':'Excluded — no Saudi affiliation'}
# top-up candidates set aside because the N=385 sample-size target was already reached (regular exclusions)
TARGET_EXCL={'STUDY-0439','STUDY-0274','STUDY-0020','STUDY-0082','STUDY-0480','STUDY-0187','STUDY-0033',
             'STUDY-0509','STUDY-0316','STUDY-0448','STUDY-0593','STUDY-0785','STUDY-0097'}
def ntask(v):
    v=str(v).strip().lower()
    if v in('causal','causa'):return 'Causal'
    if v in('descriptive','desc','descx'):return 'Descriptive'
    if v in('predictive','pred'):return 'Predictive'
    if v in('exclude','excluded'):return 'Exclude'
    return str(v).strip().title() if v else ''
def G(r,c): return str(r[c]).strip() if c in r.index and str(r[c]).strip() else ''
BL=dict(ta_s='',ya_s='',ta_t='',ya_t='',adj='',ta_r='',ya_r='',ft='',comm='')

# ---- batch-1 map from f300_ta_ya_TA (Included + Excluded) ----
b1={}
inc=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Included',dtype=str).fillna('')
for _,r in inc.iterrows():
    b1[G(r,'PMID')]=dict(ta_s=G(r,'Status_t'),ya_s=G(r,'Status_y'),ta_t=ntask(G(r,'Study Type_t')),ya_t=ntask(G(r,'Study Type_y')),
        adj=ntask(G(r,'Study Type_t_new')) or ntask(G(r,'Study Type_t')),ta_r='',ya_r='',ft='',comm=G(r,'Unnamed: 12'))
exc=pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Excluded',dtype=str).fillna('')
for _,r in exc.iterrows():
    b1[G(r,'PMID')]=dict(ta_s=G(r,'Status_t'),ya_s=G(r,'Status_y'),ta_t='',ya_t='',adj='',
        ta_r=G(r,'Reason for Exclusion_t'),ya_r=G(r,'Reason for Exclusion_y'),ft='',comm='')

# ---- batch-2 map from s300 (All + adjudication sub-sheets) ----
adjmap={}
for sh,dc in [('Talal incl but Yassser excl','Adjudicated '),('Yasser incl but Talal excl','adjud')]:
    d=pd.read_excel('data/screening/s300_adjudicated.xlsx',sh,dtype=str).fillna('')
    for _,r in d.iterrows(): adjmap[G(r,'PMID')]=('Exclude' if G(r,dc)=='Exclude' else (ntask(G(r,'study type adj')) or 'Include'))
for _,r in pd.read_excel('data/screening/s300_adjudicated.xlsx','Disagreed task',dtype=str).fillna('').iterrows():
    adjmap[G(r,'PMID')]=ntask(G(r,'adj type'))
b2={}
for _,r in pd.read_excel('data/screening/s300_adjudicated.xlsx','All',dtype=str).fillna('').iterrows():
    pm=G(r,'PMID'); ta,ya=G(r,'Status_ta'),G(r,'Status_ya')
    adj=adjmap.get(pm, ('Exclude' if ta=='Exclude' and ya=='Exclude' else (ntask(G(r,'Study Type_ta')) or 'Include') if ta=='Include' and ya=='Include' else ''))
    b2[pm]=dict(ta_s=ta,ya_s=ya,ta_t=ntask(G(r,'Study Type_ta')),ya_t=ntask(G(r,'Study Type_ya')),adj=adj,
        ta_r=G(r,'Reason for Exclusion_ta'),ya_r=G(r,'Reason for Exclusion_ya'),
        ft=G(r,'Full text found or not'),comm='; '.join(x for x in [G(r,'Comments_ta'),G(r,'Comments_ya'),G(r,'Exclusion after adjudication')] if x))

# ---- frame: first1000sample in Seq order ----
s1=pd.read_excel('data/screening/first1000sample_21-12-23.xlsx','Sheet 1',dtype=str).fillna('')
s1=s1[s1.PMID.str.strip()!=''].copy(); s1['seq']=pd.to_numeric(s1.Seq,errors='coerce')
rows=[]
def rec(seq,pmid,batch,m,corr=''):
    rows.append(dict(Seq=seq,PMID=str(pmid).strip(),screening_batch=batch,corr_author_saudi=corr,
        TA_status=m['ta_s'],YA_status=m['ya_s'],TA_task=m['ta_t'],YA_task=m['ya_t'],
        reviewers_agreed=('Yes' if m['ta_s'] and m['ta_s']==m['ya_s'] else ('No' if m['ta_s'] and m['ya_s'] else '')),
        adjudicated_task_or_decision=m['adj'],TA_exclusion_reason=m['ta_r'],YA_exclusion_reason=m['ya_r'],
        full_text_found=m['ft'],comments=m['comm']))
for _,r in s1.sort_values('seq').iterrows():
    pm=G(r,'PMID'); sq=r['seq']
    if sq<=300: rec(int(sq),pm,'batch-1 (Seq 1-300)',b1.get(pm,BL))
    elif sq<=621: rec(int(sq),pm,'batch-2 (Seq 301-621)',b2.get(pm,BL))
    else: rec(int(sq),pm,'not screened (Seq 622-1000)',BL)
# ---- 3-more pool (post-hoc panel review; skip any already in the 1000 frame) ----
frame_pmids=set(s1.PMID.astype(str))
for _,r in pd.read_excel('data/screening/incl or excl of pool of papers to include 3 more papers_YA_TA.xlsx','Sheet1',dtype=str).fillna('').iterrows():
    pm=G(r,'PMID');
    if not pm or pm in frame_pmids: continue  # candidate already in the 1000 frame -> recorded once at its Seq position
    st=G(r,'Status'); m=dict(ta_s=st,ya_s=st,ta_t=ntask(G(r,'Study Type')),ya_t=ntask(G(r,'Study Type')),
        adj=('Exclude' if st=='Exclude' else ntask(G(r,'Study Type')) or 'Include'),ta_r=G(r,'Reason for Exclusion'),
        ya_r=G(r,'Reason for Exclusion'),ft='',comm=G(r,'Comments'))
    rec('',pm,'3-more pool (panel)',m,'Saudi' if G(r,'Has Saudi author')=='Yes' else G(r,'Has Saudi author'))

led=pd.DataFrame(rows)
led['in_final_385']=led.PMID.map(lambda p:'Yes' if p in P385 else 'No')
def dispo(r):
    pm=r['PMID']
    if pm in P385: return 'Included — in final analysis (385)'
    if pm in TARGET_EXCL: return 'Excluded — sample-size target of N=385 already reached'
    if pm in LATE: return LATE[pm]
    if r['screening_batch'].startswith('not screened'): return 'Not screened (Seq 622-1000; target reached)'
    if '3-more' in r['screening_batch']: return 'Excluded — 3-more panel review'
    if 'no found' in r['full_text_found'].lower(): return 'Excluded — full text not found'
    return 'Excluded at screening'
led['final_disposition']=led.apply(dispo,axis=1)
led=led[['Seq','PMID','screening_batch','corr_author_saudi','TA_status','YA_status','TA_task','YA_task',
         'reviewers_agreed','adjudicated_task_or_decision','TA_exclusion_reason','YA_exclusion_reason',
         'full_text_found','comments','in_final_385','final_disposition']]

# ---- checks ----
print('rows',len(led),'| unique PMID',led.PMID.nunique(),'| in-385',(led.in_final_385=='Yes').sum())
print('by batch:',led.screening_batch.value_counts().to_dict())
print('disposition:')
for k,v in led.final_disposition.value_counts().items(): print(f'   {v:>4}  {k[:66]}')

# ---- PRISMA summary + README ----
# computed straight from the ledger dispositions so the cascade is always internally consistent
n_notscr=int(led.final_disposition.str.startswith('Not screened').sum())
n_excl=int(led.final_disposition.str.startswith('Excluded').sum())
n_scr=n_excl+385
n3new=int((~led[led.screening_batch.str.startswith('3-more')].PMID.isin(frame_pmids)).sum())
summ=pd.DataFrame({'Stage':['Randomly sampled (ordered frame, Seq 1-1000)',
    'Not screened (Seq 622-1000; sample-size target of N=385 reached)',
    'Screened (Seq 1-621 in order + %d-paper top-up pool)'%n3new,'   Excluded',
    '   Included in the final analysis (N=385)'],
    'n':[1000,n_notscr,n_scr,n_excl,385]})
readme=pd.DataFrame({'Item':['SCREENING LEDGER (PRISMA) — 1000 sample -> 385','Prepared','','FLOW',
    '  frame','  batch-1 (Seq 1-300)','  batch-2 (Seq 301-621)','  Seq 622-1000','  +3 added','','COLUMNS',
    '  Seq','  TA_/YA_status,_task','  adjudicated_task_or_decision','  in_final_385','  final_disposition','',
    'EXCLUSIONS (regular)','3-more pool (target logic)','NOTE: first1000 Status'],
    'Detail':['TA (Talal) + YA (Yasser) screening of the ordered 1000-paper sample down to the final 385.','2026-08-12','',
    '','data/screening/first1000sample_21-12-23.xlsx — the 1000 randomly sampled papers in Seq order (the eligible pool).',
    'data/screening/f300_ta_ya_TA.xlsx (Included+Excluded) — full first batch, 300 papers.',
    'data/screening/s300_adjudicated.xlsx (All + 4 disagreement sub-sheets) — 321 papers.',
    'Never screened — screening stopped once the target of 385 includes was reached at Seq 621 (all final-included papers fall in Seq 1-621).',
    'incl or excl ...YA_TA.xlsx — panel pool NOT in the 1000; 3 added (STUDY-0658, STUDY-0401, STUDY-0161).','',
    '','Position in the randomly-ordered sample (blank for the 3-more pool).',
    'Independent Talal / Yasser include-exclude + study-task calls.','Final call after adjudication (Causal/Descriptive/Predictive/Exclude).',
    'Yes if the PMID is in the final 385 analysis set (authoritative).','Included / Included-then-excluded / Excluded / Not screened / panel-not-added.','',
    'All treated as regular exclusions: STUDY-0956 (YA co-author, COI); STUDY-0136 + STUDY-0478 (no Saudi affiliation); and 13 top-up candidates (STUDY-0439, STUDY-0274, STUDY-0020, STUDY-0082, STUDY-0480, STUDY-0187, STUDY-0033, STUDY-0509, STUDY-0316, STUDY-0448, STUDY-0593, STUDY-0785, STUDY-0097) set aside because N=385 was already reached.',
    'The 3-more panel marked 8 Saudi-authored papers Include; 3 were ADDED to meet the sample-size target of N=385. The other 5 (STUDY-0439, STUDY-0274, STUDY-0082, STUDY-0509, STUDY-0448) were SURPLUS — not added because the target was already reached (not a quality/eligibility exclusion).',
    'first1000sample.Status is an early PARTIAL pass (filled only to Seq 449) and was later revised; used here ONLY for Seq order, not as the decision — the batch files are authoritative.']})

out='data/screening/08_12_2026_screening_ledger.xlsx'
with pd.ExcelWriter(out,engine='openpyxl') as xw:
    readme.to_excel(xw,sheet_name='README',index=False); summ.to_excel(xw,sheet_name='PRISMA_summary',index=False)
    led.to_excel(xw,sheet_name='screening_ledger',index=False)
    fill=PatternFill('solid',fgColor='16697A'); hf=Font(bold=True,color='FFFFFF')
    for sh in xw.sheets:
        ws=xw.sheets[sh]; ws.freeze_panes='A2'
        for c in ws[1]: c.font=hf; c.fill=fill
    xw.sheets['README'].column_dimensions['A'].width=34; xw.sheets['README'].column_dimensions['B'].width=104
    for c in xw.sheets['README']['A']: c.font=Font(bold=True)
    lw=xw.sheets['screening_ledger']
    for i,col in enumerate(led.columns,1):
        lw.column_dimensions[get_column_letter(i)].width=min(38,max(9,int(led[col].map(lambda v:len(str(v))).max())+2))
print('wrote',out)
