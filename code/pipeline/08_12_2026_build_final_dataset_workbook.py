# NOTE (public repository): 3 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Send-ready FINAL analysis dataset workbook for co-PI (Yasser).
# wide (1 row/paper): adjudicated exposure+outcome, full stratifier block, affiliation vars,
#                     and tool items ORDERED BY THEIR APPEARANCE IN THE DATA-COLLECTION TOOL.
# long (1 row/PMID x item): provenance, rows ordered by tool appearance within each paper.
import pandas as pd, json
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

# ---- canonical tool order (from code/pipeline/07_19_2026_reorder_to_tool_order.py) ----
TOOL_ORDER = [
 (0,"Reviewer_ID"),(0,"Timestamp"),(1,"recusal"),(2,"task"),
 (3,"descriptive_design"),(3,"descriptive_pop"),
 (4,"descriptive_sampling"),(4,"descriptive_sample_size"),(4,"descriptive_acc_sampl"),(4,"descriptive_sample_ach"),(4,"descriptive_base_sel"),
 (5,"descriptive_outcome_type"),(5,"descriptive_val_outcome"),(5,"descriptive_out_bias_acc"),
 (6,"descriptive_miss_outcome"),(6,"descriptive_hand_miss_outcom"),(7,"descriptive_err_disc"),(8,"descriptive_confl_task"),
 (9,"predictive_design"),(9,"predictive_pop"),
 (10,"causal_design"),(10,"causal_pop"),
 (11,"causal_sampling"),(11,"causal_sample_size"),(11,"causal_acc_sampl"),(11,"causal_sample_ach"),(11,"causal_base_sel"),(11,"causal_comp_dis"),(11,"causal_follow"),(11,"causal_ltfu_bias"),(11,"causal_ltfu_acc"),
 (12,"causal_exposure_type"),(12,"causal_val_exposure"),(12,"causal_diff_or_nondiff_exp"),(12,"causal_exp_bias_acc"),
 (13,"causal_outcome_type"),(13,"causal_val_outcome"),(13,"causal_diff_or_nondiff_out"),(13,"causal_out_bias_acc"),
 (14,"causal_dep_or_indep_misc"),
 (15,"causal_base_conf_meth"),(15,"causal_time_verying"),(15,"causal_tv_conf_meth"),(15,"causal_conf_var_det"),
 (16,"causal_miss_exposure"),(16,"causal_hand_miss_exposure"),(17,"causal_miss_outcome"),(17,"causal_hand_miss_outcom"),
 (18,"causal_err_disc"),(19,"comments"),(19,"comments_focus")]
RANK={v:i for i,(s,v) in enumerate(TOOL_ORDER)}; SECTION={v:s for s,v in TOOL_ORDER}

wide=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',dtype=str,keep_default_na=False)
long=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv',dtype=str,encoding='utf-8-sig',keep_default_na=False)

# ---- adjudicated exposure / outcome (assignment batches + panel rationale) ----
# priority-ordered sources (0=highest): TA/YA final decision for the 3-new pool + the Batch-6
# assignment come first, then the two assignment batches, then the older panel-rationale file.
SRCS=[('data/screening/incl or excl of pool of papers to include 3 more papers_YA_TA.xlsx','Adjudicated_exposure','Adjudicated_outcome',0),
      ('private/reviewers/batch-6-distribution/Batch 6.xlsx','adjudicated_exposure','adjudicated_outcome',1),
      ('private/reviewers/papers_assignment_strat.xlsx','adjudicated_exposure','adjudicated_outcome',2),
      ('private/reviewers/papers_assignment_strat_2.xlsx','adjudicated_exposure','adjudicated_outcome',2),
      ('data/screening/incl_papers_adjudication_rationale.xlsx','Adjudicated_exposure','Adjudicated_outcome',3)]
parts=[]
for f,ec,oc,pri in SRCS:
    d=pd.read_excel(f,dtype=str).fillna(''); d['PMID']=d.PMID.astype(str)
    t=d[['PMID',ec,oc]].rename(columns={ec:'adjudicated_exposure',oc:'adjudicated_outcome'}); t['pri']=pri
    parts.append(t)
ap=pd.concat(parts,ignore_index=True)
ap['has']=(ap.adjudicated_exposure.str.strip()!='')|(ap.adjudicated_outcome.str.strip()!='')
ap=ap.sort_values(['has','pri'],ascending=[False,True]).drop_duplicates('PMID',keep='first')
M=dict(zip(ap.PMID, zip(ap.adjudicated_exposure, ap.adjudicated_outcome)))
# the adjudicated pair is a CAUSAL/DESCRIPTIVE construct; predictive studies use predictive_outcome_llm.
wide['adjudicated_exposure']=wide.apply(lambda r:M.get(r['PMID'],('',''))[0] if r['Study_Type']!='Predictive' else '',axis=1)
wide['adjudicated_outcome'] =wide.apply(lambda r:M.get(r['PMID'],('',''))[1] if r['Study_Type']!='Predictive' else '',axis=1)
gap=[p for p in wide.PMID if wide.loc[wide.PMID==p,'Study_Type'].iloc[0]=='Causal'
     and not (M.get(p,('',''))[0].strip() or M.get(p,('',''))[1].strip())]
print('causal papers with a BLANK adjudicated pair (gap):', gap)

# ---- LLM-extracted outcome for the 75 PREDICTIVE studies (SEIG few-shot; UNVERIFIED) ----
oc=pd.read_csv('data/outcomes/08_08_2026_all_outcomes_classified.csv',dtype=str,keep_default_na=False)
OUT=dict(zip(oc.PMID.astype(str), oc['outcome']))
wide['predictive_outcome_llm']=wide.apply(lambda r: OUT.get(r['PMID'],'') if r['Study_Type']=='Predictive' else '', axis=1)
print('predictive studies with an LLM outcome:', (wide['predictive_outcome_llm'].str.strip()!='').sum(), 'of', (wide.Study_Type=='Predictive').sum())

# ---- full stratifier block (clean derived labels) ----
inst=pd.read_csv('data/authors/07_25_2026_saudi_paper_level.csv',dtype=str,keep_default_na=False)[['PMID','sectors_present','multisector']]
jcr =pd.read_csv('data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv',dtype=str,keep_default_na=False)[['PMID','jcr_2022_quartile']]
HEALTH={'Hospital / medical city','Hospital & research centre','Ministry of Health','Military & security-forces medical'}
inst['comp']=inst['sectors_present'].map(lambda s:'Health-system' if any(p.strip() in HEALTH for p in str(s).split(';')) else 'Academic-only')
inst['msec']=inst['multisector'].map(lambda v:'Multi-sector' if str(v) in ('True','TRUE','1') else 'Single-sector')
jcr['q']=jcr['jcr_2022_quartile'].map(lambda v:v if str(v).strip() in ('Q1','Q2','Q3','Q4') else 'None')
SC=dict(zip(inst.PMID,inst.comp)); MS=dict(zip(inst.PMID,inst.msec)); JQ=dict(zip(jcr.PMID,jcr.q))
cache=json.load(open('data/authors/07_25_2026_authors_cache_385.json',encoding='utf-8'))
TS={p:len([a for a in cache.get(str(p),[]) if str(a.get('last','')).strip()]) for p in wide.PMID}
def pop(r): return {'Causal':r['causal_pop'],'Descriptive':r['descriptive_pop'],'Predictive':r.get('predictive_pop','')}[r['Study_Type']]
def slabel(v): return 'Saudi' if v=='1' else ('Non-Saudi' if v=='0' else '')
def teamcat(n): return 'Single' if n==1 else 'Two' if n==2 else '3–10' if 3<=n<=10 else '11+' if n>=11 else ''
wide['derived_saudi_data_use']=wide.apply(pop,axis=1)
wide['derived_pct_saudi_ge50']=wide['pct_saudi_ge50'].map(lambda v:'≥50%' if v=='>=50%' else ('<50%' if v=='<50%' else v))
wide['derived_first_author_saudi']=wide['first_author_saudi'].map(slabel)
wide['derived_corresponding_author_saudi']=wide['corresponding_author_saudi'].map(slabel)
wide['derived_last_author_saudi']=wide['last_author_saudi'].map(slabel)
wide['derived_sector_composition']=wide.PMID.map(SC).fillna('Academic-only')
wide['derived_single_vs_multisector']=wide.PMID.map(MS).fillna('Single-sector')
wide['derived_jcr_2022_quartile']=wide.PMID.map(JQ).fillna('None')
wide['derived_jcr_q12_vs_q34']=wide['derived_jcr_2022_quartile'].map(lambda q:'Q1-Q2' if q in ('Q1','Q2') else ('Q3-Q4' if q in ('Q3','Q4') else 'None'))
wide['derived_team_size']=wide.PMID.map(lambda p:TS.get(p,''))
wide['derived_team_size_category']=wide.PMID.map(lambda p:teamcat(TS.get(p,0)))

# ---- reorder wide columns: id | adjudicated pair | derived stratifiers | affiliation | tool items (tool order) ----
DERIV=['derived_saudi_data_use','derived_pct_saudi_ge50','derived_first_author_saudi','derived_corresponding_author_saudi',
       'derived_last_author_saudi','derived_sector_composition','derived_single_vs_multisector','derived_jcr_2022_quartile',
       'derived_jcr_q12_vs_q34','derived_team_size','derived_team_size_category']
AFF=['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_authors','pct_saudi_ge50',
     'pct_saudi_cat3','pct_saudi_cat4','n_authors','n_saudi_authors','pct_saudi_reliable']
LEAD=['PMID','Study_Type','adjudicated_exposure','adjudicated_outcome','predictive_outcome_llm']
toolcols=sorted([c for c in wide.columns if c in RANK], key=lambda c:RANK[c])
placed=set(LEAD+DERIV+AFF+toolcols)
leftover=[c for c in wide.columns if c not in placed]
wide=wide[LEAD+DERIV+AFF+toolcols+leftover]

# ---- long: order rows by tool appearance within each paper; add tool_section ----
unmapped=sorted(set(long.variable)-set(RANK))
print('long variables NOT in tool-order map (sorted to end):', unmapped)
long['tool_section']=long.variable.map(lambda v:SECTION.get(v,''))
long['_r']=long.variable.map(lambda v:RANK.get(v,9999))
pseq={p:i for i,p in enumerate(long.PMID.drop_duplicates())}
long['_p']=long.PMID.map(pseq)
long=long.sort_values(['_p','_r']).drop(columns=['_p','_r'])
long=long[['PMID','Study_Type','tool_section','variable','final','source','resolution_note']]

# ---- README ----
nC=(wide.Study_Type=='Causal').sum(); nD=(wide.Study_Type=='Descriptive').sum(); nP=(wide.Study_Type=='Predictive').sum()
readme=[
 ("Assessment of Healthcare Research Quality in Saudi Arabia","FINAL analysis dataset"),
 ("Prepared","2026-08-12  (post inconsistency-resolution worklist)"),("",""),
 ("POPULATION","385 papers = %d Causal / %d Descriptive / %d Predictive"%(nC,nD,nP)),
 ("Scored for bias","310 (Causal + Descriptive). Predictive has no epidemiological bias items."),("",""),
 ("SHEETS",""),
 ("  wide","One row per paper (385). Columns grouped: identifiers, adjudicated exposure/outcome, derived stratifiers (prefix 'derived_'), affiliation variables, then tool items in TOOL ORDER."),
 ("  long","One row per PMID x item (18,095), with 'source' + 'resolution_note' provenance; rows ordered by tool appearance within each paper; 'tool_section' = tool section number."),("",""),
 ("ADJUDICATED PAIR",""),
 ("  adjudicated_exposure / _outcome","The TSA+YA-predetermined selected pair. Descriptive papers have an OUTCOME only (no exposure). Predictive papers have NEITHER (diagnostic/prognostic)."),
 ("  known gap","1 causal paper has a blank pair: %s (to be filled)."%(", ".join(gap) if gap else "none")),
 ("  predictive_outcome_llm","Outcome for the 75 PREDICTIVE studies (which have no adjudicated pair), extracted by LLM using the SEIG rule with the 310 adjudicated outcomes as few-shot examples. AI — UNVERIFIED, pending TSA/YA sign-off; this covers ALL 75 predictive papers. (Until 2026-08-26 two of them, STUDY-0504 and STUDY-0401, carried a hardcoded 'prior human value' that the adjudication record does not support; TSA ruled they revert to the machine determination.) Per-paper confidence/source/rationale live in data/outcomes/08_08_2026_all_outcomes_classified.csv."),("",""),
 ("STRATIFIERS (derived_ columns)","saudi_data_use · pct_saudi_ge50 · first/corresponding/last_author_saudi · sector_composition (Academic-only vs Health-system) · single_vs_multisector · jcr_2022_quartile · jcr_q12_vs_q34 · team_size · team_size_category"),("",""),
 ("VALUE CONVENTIONS",""),
 ("  'skipped' / 'should be skipped'","Not Applicable — map to NA before analysis."),
 ("  'Not reported or unknown'","Treated as bias present (standard risk-of-bias convention)."),
 ("  blank 'final'","Unresolved skip-logic disagreement (one reviewer N/A) — treat as NA (145 cells)."),("",""),
 ("PROVENANCE (long 'source')","agreed / TA=YA / phaseII / batch6-* = routine workflow; worklist-2026-08-12 = 51 worklist cells; recovered-STUDY-0945 / phase2-normalised / skiplogic-resolved / batch6-split = 23 curated fixes."),
 ("VARIABLE NAMING","Tool items prefixed by task: causal_ / descriptive_ / predictive_ . Order follows the data-collection form (Sections 2-19)."),
 ("Design labels","Kept as reviewers/adjudicators coded them (the worklist relabelled no design or follow-up)."),("",""),
 ("COMPANION FILES (separate)","data/quality-control/08_12_2026_all_manual_edits_audit.xlsx (74 hand-edits) · data/scoring/08_12_2026_known_data_caveats.xlsx (6 caveats / 19 studies)."),
 ("Plain CSVs","data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv / _long.csv (identical data, project folder)."),
]
rd=pd.DataFrame(readme, columns=["Item","Detail"])

out='data/analysis/08_12_2026_final_analysis_dataset_385.xlsx'
with pd.ExcelWriter(out, engine='openpyxl') as xw:
    rd.to_excel(xw,sheet_name='README',index=False); wide.to_excel(xw,sheet_name='wide',index=False); long.to_excel(xw,sheet_name='long',index=False)
    fill=PatternFill('solid',fgColor='16697A'); hf=Font(bold=True,color='FFFFFF')
    for sh in ['README','wide','long']:
        ws=xw.sheets[sh]; ws.freeze_panes='A2'
        for c in ws[1]: c.font=hf; c.fill=fill
    rm=xw.sheets['README']; rm.column_dimensions['A'].width=40; rm.column_dimensions['B'].width=105
    for c in rm['A']: c.font=Font(bold=True)
    ww=xw.sheets['wide']
    for i,col in enumerate(wide.columns,1):
        ww.column_dimensions[get_column_letter(i)].width=min(30,max(11,int(wide[col].map(lambda v:len(str(v))).max())+2))
    lw=xw.sheets['long']
    for i,wd in enumerate([12,12,10,32,42,20,55],1): lw.column_dimensions[get_column_letter(i)].width=wd
print('wrote',out,'| wide',wide.shape,'| long',long.shape)
print('wide column order (first 20):',list(wide.columns[:20]))
