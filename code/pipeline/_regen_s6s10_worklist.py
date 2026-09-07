# NOTE (public repository): 11 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
import pandas as pd

papers = ['STUDY-0431','STUDY-0385','STUDY-0499','STUDY-0532','STUDY-0561','STUDY-0829',
          'STUDY-0336','STUDY-0783','STUDY-0437','STUDY-0345','STUDY-0520']

# recorded values + pair
df = pd.read_csv('data/analysis/07_16_2026_ANALYSIS_DATASET_long.csv', dtype=str)
vs = ['causal_design','descriptive_design','causal_sampling','descriptive_sampling',
      'causal_base_sel','descriptive_base_sel','causal_base_conf_meth']
piv = df[df.variable.isin(vs)].pivot_table(index='PMID', columns='variable', values='final', aggfunc='first')
st = df.groupby('PMID')['Study_Type'].first()
def load(fn,ec,oc):
    x=pd.read_excel(fn,dtype=str); x['PMID']=x['PMID'].astype(str).str.strip()
    return x.set_index('PMID')[[ec,oc]].rename(columns={ec:'e',oc:'o'})
srcs=[load('private/reviewers/papers_assignment_strat.xlsx','adjudicated_exposure','adjudicated_outcome'),
      load('private/reviewers/papers_assignment_strat_2.xlsx','adjudicated_exposure','adjudicated_outcome'),
      load('data/screening/incl_papers_adjudication_rationale.xlsx','Adjudicated_exposure','Adjudicated_outcome')]
def gp(p,f):
    for s in srcs:
        if p in s.index:
            v=s.loc[p,f]
            if isinstance(v,pd.Series): v=v.dropna().iloc[0] if len(v.dropna()) else None
            if pd.notna(v) and str(v).strip().lower() not in ('','nan'): return str(v).strip()
    return ''

RCT_FALSE = ('S10/S11','NO CHANGE','', 'No baseline selection bias (correct)', 'high',
    'RCT: non-random SAMPLING is an external-validity issue; randomization guarantees no baseline SELECTION bias between arms. S10/S11 rule is a false alarm here.','')
R = {
 'STUDY-0431': ('S6a + S10/S11','DESIGN Cohort->RCT','RCT','No baseline selection bias (correct, as RCT)','high',
    'TCZ-HCQ vs TCZ-RMV randomly allocated (random-number table; reg. [TRIAL-REG-REDACTED]); "prospective cohort" is an author mislabel. Randomized => no baseline selection bias.',
    'Simple randomization was made by allocating patients using a table of random numbers.'),
 'STUDY-0385': ('S6a','DESIGN Cohort->RCT','RCT','(base_sel recorded "No"; keep)','medium',
    'MD+ECL vs MD-only randomly allocated to arms; PASS a priori power calc + blinded examiner. Wording imprecise ("probability sampling"), no mechanism named.',
    'The participants who willingly consented were randomly allocated into 3 groups according to the probability sampling technique.'),
 'STUDY-0499': ('S6b','NO CHANGE','RCT (keep)','','high',
    'Genuine double-blind placebo-controlled RCT; base_conf_meth="No adjustment" = randomization-only convention (Ruling 1). S6b is a coding note, not an error.',
    '(verified earlier: ITT, double-blind, placebo-controlled)'),
 'STUDY-0532': RCT_FALSE, 'STUDY-0561': RCT_FALSE, 'STUDY-0829': RCT_FALSE,
 'STUDY-0336': RCT_FALSE, 'STUDY-0783': RCT_FALSE, 'STUDY-0437': RCT_FALSE,
 'STUDY-0345': ('S10/S11','NO CHANGE','', 'No baseline selection bias (correct)','high',
    'Descriptive: complete 30-yr tumor-registry census of ALL eligible MPM patients (25,276 screened) -- not a cherry-picked sample. base_sel="No" correct; rule false alarm.',
    'the Department of Medical Oncology tumor registry at KAMC identified a total of 25,276 oncology patients from 1993-2022'),
 'STUDY-0520': ('S10/S11','FIX base_sel: selection bias PRESENT','', 'Selection bias present (testing-indication/spectrum)','high',
    'Descriptive HSV seroprevalence from a CLINICALLY-TESTED population (TORCH/infants <6mo, 77% IgG+ maternal antibodies) -- unrepresentative for a population-prevalence target; authors attribute low estimate to sample composition. base_sel="No" understates it. Nuance: took ALL archived records (no investigator cherry-picking), so depends whether the item captures spectrum/testing-indication bias.',
    'The study comprises cases tested for HSV antibodies for different medical conditions and checkups over five years'),
}

rows=[]
for p in papers:
    t=st.get(p,''); pre='descriptive_' if t=='Descriptive' else 'causal_'
    r=piv.loc[p] if p in piv.index else None
    fam,action,final_design,final_bsel,conf,finding,ev = R[p]
    rows.append({
        'pmid':p,'family':fam,'Study_Type':t,
        'selected_exposure':gp(p,'e'),'selected_outcome':gp(p,'o'),
        'recorded_design': (r.get(pre+'design') if r is not None else ''),
        'recorded_sampling': (r.get(pre+'sampling') if r is not None else ''),
        'recorded_base_sel': (r.get(pre+'base_sel') if r is not None else ''),
        'recorded_base_conf_meth': (r.get('causal_base_conf_meth') if r is not None else ''),
        'ACTION':action,'final_design':final_design,'final_base_sel':final_bsel,
        'finding':finding,'evidence_quote':ev,'confidence':conf,
    })
out=pd.DataFrame(rows)
order={'DESIGN':0,'FIX':1,'NO':2}
out['k']=out['ACTION'].str.split().str[0].map(lambda x: order.get(x,3))
out=out.sort_values(['k','pmid']).drop(columns='k').reset_index(drop=True)
out.to_csv('data/adjudication/07_22_2026_S6_S10_resolution.csv',index=False,encoding='utf-8-sig')
with pd.ExcelWriter('data/adjudication/07_22_2026_S6_S10_resolution.xlsx') as xl:
    out.to_excel(xl,index=False,sheet_name='S6_S10_resolution')
chg=out[out['ACTION']!='NO CHANGE']
print('rows:',len(out),'| changes:',len(chg),'| no-change:',len(out)-len(chg))
print(out[['pmid','family','Study_Type','ACTION','confidence']].to_string(index=False))
print()
print('wrote data/adjudication/07_22_2026_S6_S10_resolution.csv / .xlsx')
