# NOTE (public repository): 17 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
import json
import pandas as pd

# --- selected exposure-outcome pair (3-file fallback) ---
def load(fn, ec, oc):
    x = pd.read_excel(fn, dtype=str); x['PMID'] = x['PMID'].astype(str).str.strip()
    return x.set_index('PMID')[[ec, oc]].rename(columns={ec:'e', oc:'o'})
srcs = [load('private/reviewers/papers_assignment_strat.xlsx','adjudicated_exposure','adjudicated_outcome'),
        load('private/reviewers/papers_assignment_strat_2.xlsx','adjudicated_exposure','adjudicated_outcome'),
        load('data/screening/incl_papers_adjudication_rationale.xlsx','Adjudicated_exposure','Adjudicated_outcome')]
def pair(p, f):
    for s in srcs:
        if p in s.index:
            v = s.loc[p, f]
            if isinstance(v, pd.Series):
                v = v.dropna().iloc[0] if len(v.dropna()) else None
            if pd.notna(v) and str(v).strip() and str(v).strip().lower() != 'nan':
                return str(v).strip()
    return ''

# --- raw agent screens ---
raw = {}
grpmap = {'data/adjudication/followup-screen/cohort.json':'cohort','data/adjudication/followup-screen/cc_A.json':'case-control','data/adjudication/followup-screen/cc_B.json':'case-control','data/adjudication/followup-screen/xsec_prepost.json':'xsec/prepost'}
for fn in ['data/adjudication/followup-screen/cohort.json','data/adjudication/followup-screen/cc_A.json','data/adjudication/followup-screen/cc_B.json','data/adjudication/followup-screen/xsec_prepost.json']:
    for r in json.load(open('data/adjudication/followup-screen/'+fn, encoding='utf-8')):
        r['group'] = grpmap[fn]
        raw[str(r['pmid'])] = r

# --- pair-anchored FINAL calls (auditable per-PMID) ---
FINAL = {
 'STUDY-0326': ('Cohort','Yes','FOLLOW No->Yes','pair Age->Hyponatremia: incident outcome tracked daily = cohort follow-up'),
 'STUDY-0471': ('Pre/post','Yes','FOLLOW No->Yes','pair Music->anxiety: same 18 people pre/post'),
 'STUDY-0331': ('Cross-sectional','No','FOLLOW Yes->No','pair tx-stage->Candida: 3 groups of different patients, cross-sectional'),
 'STUDY-0093': ('Cross-sectional (ecological/hospital-level)','No','FOLLOW Yes->No','pair public/private hospital->compliance: units are hospitals, no persons followed'),
 'STUDY-0202': ('Cross-sectional','No','FOLLOW Yes->No  [FLIPPED by pair-anchoring]','pair CCT->IOP is a cross-sectional Pearson correlation; TPRK before/after is a DIFFERENT relationship'),
 'STUDY-0845': ('Cross-sectional','No','DESIGN Cohort->Cross-sectional','pair ABO->COVID+: fixed germline trait vs [NAME-REDACTED] status (case-base), not cohort'),
 'STUDY-0306': ('Cross-sectional','No','DESIGN Cohort->Cross-sectional','pair nocturnal BP->visuospatial: both in one overnight session'),
 'STUDY-0878': ('Cross-sectional (repeated)','No','DESIGN Cohort->Cross-sectional','pair pandemic phase->physical function: serial anonymous cross-sections'),
 'STUDY-0676': ('Cross-sectional','No','DESIGN Cohort->Cross-sectional','pair oral hygiene->secondary caries: single exam'),
 'STUDY-0149': ('Case-control','No','none (follow=No confirmed)','pair blood type->COVID+: fixed exposure; base-level=Yes edge but investigator No'),
 'STUDY-0589': ('Case-control','No','none','pair MMP1 SNP->POAG: germline, prevalent'),
 'STUDY-0119': ('Case-control','No','none','pair Tfh cells->COVID severity: biomarker measured post-diagnosis'),
 'STUDY-0590': ('Case-control','No','none','pair HLA genotype->H. pylori: germline'),
 'STUDY-0991': ('Case-control','No','none','pair MTHFR->ASM response: germline'),
 'STUDY-0017': ('Case-control','No','none (investigator-level No; base-level Yes)','pair stress->acute stroke: INTERSTROKE incident cases = the base-level edge case'),
 'STUDY-0911': ('Case-control','No','none','pair CCND1->breast carcinoma: germline+biomarker'),
 'STUDY-0460': ('Case-control','No','none (optional design->Cross-sectional)','pair vitamin D3->COVID: authors call it cross-sectional'),
}

rows = []
for p, (fd, ff, action, why) in FINAL.items():
    r = raw[p]
    rows.append({
        'pmid': p,
        'group': r['group'],
        'selected_exposure': pair(p,'e'),
        'selected_outcome': pair(p,'o'),
        'recorded_design': r['recorded_design'],
        'recorded_follow': r['recorded_follow'],
        'final_design_for_pair': fd,
        'final_follow': ff,
        'design_changes': str(fd).split(' (')[0] not in str(r['recorded_design']),
        'follow_changes': ff != r['recorded_follow'],
        'ACTION': action,
        'pair_anchored_rationale': why,
        'cc_case_type': r.get('cc_case_type',''),
        'cc_control_sampling': r.get('cc_control_sampling',''),
        'follow_base_level': r.get('follow_base_level',''),
        'follow_investigator_level': r.get('follow_investigator_level',''),
        'evidence_quote': r.get('evidence_quote',''),
        'confidence': r.get('confidence',''),
        'agent_notes': r.get('notes',''),
    })
df = pd.DataFrame(rows)
order = {'FOLLOW':0,'DESIGN':1,'none':2}
df['k'] = df['ACTION'].str.split().str[0].map(lambda x: order.get(x,3))
df = df.sort_values(['k','pmid']).drop(columns='k').reset_index(drop=True)

df.to_csv('data/adjudication/07_22_2026_followup_S1_S22_resolution.csv', index=False, encoding='utf-8-sig')
with pd.ExcelWriter('data/adjudication/07_22_2026_followup_S1_S22_resolution.xlsx') as xl:
    df.to_excel(xl, index=False, sheet_name='followup_resolution')

print('rows:', len(df), '| follow changes:', int(df['follow_changes'].sum()), '| design changes:', int(df['design_changes'].sum()))
print()
print(df[['pmid','selected_exposure','selected_outcome','recorded_design','recorded_follow','final_design_for_pair','final_follow','ACTION']].to_string(index=False, max_colwidth=26))
print()
print('wrote data/adjudication/07_22_2026_followup_S1_S22_resolution.csv / .xlsx (with selected-pair columns)')
