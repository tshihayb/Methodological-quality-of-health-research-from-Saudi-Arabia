# NOTE (public repository): 6 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Known data-quality caveats register (design/method/follow-up mismatches kept as reviewer-coded).
# For manuscript limitations reporting + quantification. Built 2026-08-12 from TSA notes.
import pandas as pd
w=pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',dtype=str,keep_default_na=False)
def opts(v): return [x.strip() for x in str(v).split(';') if x.strip()]
def short(d): return str(d).split(' (')[0]
c=w[w.Study_Type=='Causal'].copy(); c['dshort']=c['causal_design'].map(short)

# ---- derive each caveat's study set ----
A=['STUDY-0431','STUDY-0385']
rct=c['causal_design'].str.startswith('Randomized clinical trial')
has_rand=c['causal_base_conf_meth'].map(lambda v:'Randomization' in opts(v))
noadj=c['causal_base_conf_meth'].map(lambda v:'no adjustment' in v.lower())
B=list(c[rct & noadj & ~has_rand].PMID)
C=list(c[(c['causal_design']=='Cross-sectional') & (c['causal_follow']=='Yes')].PMID)
LONG={'Randomized clinical trial','Cohort','Pre/post'}
capD=c[c['dshort'].isin(LONG) & (c['causal_follow']=='No')]
E=['STUDY-0345','STUDY-0520']

def flds(pm, keys):
    r=w[w.PMID==pm].iloc[0]; pfx='causal_' if r['Study_Type']=='Causal' else 'descriptive_'
    return "; ".join(f"{k}={short(r.get(pfx+k,''))}" for k in keys)

rows=[]
def add(cid,name,rule,pmid,domain,impl,keptas,correct,fields):
    r=w[w.PMID==pmid].iloc[0]
    rows.append([cid,name,rule,pmid,r['Study_Type'],short(r['causal_design'] if r['Study_Type']=='Causal' else r['descriptive_design']),
                 fields,domain,impl,keptas,correct])

for pm in A: add("C1","Design misclassified: coded Cohort but randomized","S6a",pm,"Selection bias",
    "Really an RCT (randomization is the confounding method). As Cohort, its non-random sample + 'no baseline SB' reads as an S10/S11 mismatch; as RCT that pairing is correct. Confounding is unaffected (method-based RCT exemption fires regardless of the design label).",
    "Kept as Cohort (2 reviewers agreed)","N/A (design kept by decision)", flds(pm,['design','sampling','base_sel','base_conf_meth']))
for pm in B: add("C2","RCT coded 'No adjustment' for confounding","S6b",pm,"Confounding bias",
    "Falsely scored as NOT controlling confounding (currently confounding=VAL). As an RCT, randomization controlled confounding, so this should be exempt/OK. CORRECTABLE: the scorer's design=='RCT' arm never fires (stored design is the long string), so only base_conf_meth='Randomization' triggers the exemption.",
    "Kept as recorded ('No adjustment')","YES — teach scorer to treat design=RCT as randomization-exempt", flds(pm,['design','base_conf_meth','conf_var_det']))
for pm in C: add("C3","Cross-sectional design but follow-up = Yes","S1",pm,"Selection bias (LTFU)",
    "Cross-sectional studies have no follow-up, yet follow=Yes makes the loss-to-follow-up items applicable; each currently carries an LTFU reporting gap (ltfu_bias='Not reported'). Inflates the apparent LTFU/selection reporting burden for cross-sectional work.",
    "Kept as follow=Yes (reviewer-coded)","N/A (follow kept by decision)", flds(pm,['design','follow','ltfu_bias','ltfu_acc']))
for pm in capD.PMID:
    legit = " (may be legitimately single-timepoint — worklist ruled follow=No correct)" if pm=='STUDY-0792' else ""
    add("C4","Longitudinal design but follow-up = No","S22",pm,"Selection bias (LTFU)",
    "follow=No triggers the skip-logic that SKIPS ltfu_bias and ltfu_acc, so loss-to-follow-up bias is never assessed — masked — for a design that should assess it."+legit,
    "Kept as follow=No (reviewer-coded)","N/A (follow kept by decision)", flds(pm,['design','follow','ltfu_bias','ltfu_acc']))
for pm in E: add("C5","Non-random sample but 'No baseline selection bias' (non-RCT)","S10/S11",pm,"Selection bias",
    "A non-random sample coded 'No baseline selection bias' masks the baseline selection bias AND skips the responder-vs-non-responder comparison (comp_dis). Understates selection-bias prevalence. STUDY-0520 is the reviewer-confirmed genuine error kept as-is.",
    "Kept as 'No baseline SB' (reviewer-coded)","N/A (kept by decision)", flds(pm,['design','sampling','base_sel','comp_dis']))

# --- C6 (added 2026-08-12): S5 contradiction that survives into the Table 2 display ---
add("C6","RCT with an adjustment method but conf_var_det = 'No adjustment'","S5","STUDY-0429","Confounding bias",
    "Reports Regression (a real selection-based method) in base_conf_meth yet 'No adjustment' as the confounder-selection basis (S5 contradiction). Because it is Randomization;Regression (not pure randomization-only), Table 2's N/A rule does not drop it, so it appears as the lone 'No adjustment' in the confounder-selection-basis breakdown (1 of 112) and inflates that base by 1 (112 vs 111). SCORING is unaffected (RCT randomization exemption -> confounding=OK); the anomaly is confined to the Table 2 descriptive display.",
    "Kept raw 'No adjustment' (worklist #85 decided 'skip', not yet applied)",
    "YES - set conf_var_det='should be skipped' -> base 112->111, row->0; scoring unchanged",
    flds("STUDY-0429",['design','base_conf_meth','conf_var_det']))

reg=pd.DataFrame(rows, columns=["Caveat","Name","Rule","PMID","Study_Type","Design","Recorded_fields","Domain_affected","Implication","Kept_as","Correctable"])

# summary
summ=(reg.groupby(["Caveat","Name","Rule","Domain_affected"])
        .agg(n_studies=("PMID","nunique"), PMIDs=("PMID", lambda s:", ".join(sorted(s)))).reset_index())
# caveat-4 design breakdown
d4=capD['dshort'].map({'Randomized clinical trial':'RCT'}).fillna(capD['dshort']).value_counts()
d4txt="C4 by design: "+" · ".join(f"{k} {v}" for k,v in d4.items())

out='outputs/tables/08_12_2026_known_data_caveats.xlsx'
with pd.ExcelWriter(out, engine='openpyxl') as xw:
    summ.to_excel(xw, sheet_name='summary', index=False)
    reg.to_excel(xw, sheet_name='per_study', index=False)
    for sh,df in [('summary',summ),('per_study',reg)]:
        ws=xw.sheets[sh]
        for i,col in enumerate(df.columns,1):
            ws.column_dimensions[chr(64+i)].width=min(70,max(12,int(df[col].map(lambda v:len(str(v))).max())+2))
print("wrote",out,"|",len(reg),"study-rows across",reg.Caveat.nunique(),"caveats")
print(summ[['Caveat','Name','Rule','Domain_affected','n_studies','PMIDs']].to_string(index=False))
print("\n"+d4txt)
print("\nTotal distinct studies flagged:", reg.PMID.nunique())
