# NOTE (public repository): 9 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Rebuild the analysis dataset for the 377 included papers (2026-07-23 round).

Resolution chain per (PMID, variable) cell:
  agreed cell            -> the reviewers' common answer                        source='agreed'
  disagreed, TA == YA    -> that value                                          source='TA=YA'
  disagreed, TA != YA    -> phase-II adjud_final                                source='phaseII'
  PMID STUDY-0945          -> the recovered adjudication in Comments_TA/_YA       source='recovered-STUDY-0945'
  then re-apply the 12 curated fixes carried over from the 07_16 dataset        source preserved
Writes NEW dated files; the 07_16 dataset is left untouched.
"""
import pandas as pd

EXCL = {'STUDY-0136','STUDY-0478',            # no Saudi affiliation
        'STUDY-0449','STUDY-0905',            # incomplete single review
        'STUDY-0956','STUDY-0275','STUDY-0320','STUDY-0927'}   # single review via recusal
HOUSE = {'Reviewer_ID','Timestamp','comments','comments_focus'}

ag = pd.read_excel('private/reviewers/adjudication-worklists/04_17_2026_do_not_Need_adj.xlsx')
ta = pd.read_excel('private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_TA_toolorder.xlsx')
ya = pd.read_excel('private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_YA_toolorder.xlsx')
ph = pd.read_excel('private/reviewers/adjudication-worklists/07_23_2026_TA_YA_Differed_phase_II.xlsx')
cur = pd.read_csv('data/analysis/07_16_2026_ANALYSIS_DATASET_long.csv', dtype=str)
for d in (ag, ta, ya, ph, cur): d['PMID'] = d.PMID.astype(str)

def norm(v):
    """TA/YA comparison rule: casefold + collapse whitespace + sort ;-multiselect parts."""
    s = ' '.join(str(v).strip().casefold().split())
    if s in ('nan',''): return ''
    if ';' in s: s = ';'.join(sorted(p.strip() for p in s.split(';') if p.strip()))
    return s

blank = lambda v: str(v).strip() in ('', 'nan')

TARGET = sorted(set(ta.PMID) - EXCL)
stype  = dict(zip(ta.PMID, ta.Study_Type))
stype.update(dict(zip(ag.PMID, ag.Study_Type)))

phase2 = {(r.PMID, r.variable): r.adjud_final for _, r in ph.iterrows() if not blank(r.adjud_final)}
tam    = {(r.PMID, r.variable): (r.Adjduciation_TA, r.Comments_TA) for _, r in ta.iterrows()}
yam    = {(r.PMID, r.variable): (r.Adjduciation_YA, r.Comments_YA) for _, r in ya.iterrows()}
# PMID STUDY-0945: the Adjduciation_* block is merge-corrupted; the true call is in Comments_*
RECOVER = {v for (p, v) in tam if p == 'STUDY-0945' and not blank(tam[(p, v)][1])} - HOUSE

rows = []
for _, r in ag.iterrows():
    if r.PMID in EXCL or r.variable in HOUSE: continue
    v1, v2 = r.first_reviewer, r.second_reviewer
    val = v1 if not blank(v1) else v2
    rows.append((r.PMID, stype.get(r.PMID), r.variable, val, 'agreed', ''))

for _, r in ta.iterrows():
    if r.PMID in EXCL or r.variable in HOUSE: continue
    k = (r.PMID, r.variable)
    if r.PMID == 'STUDY-0945' and r.variable in RECOVER:
        rows.append((r.PMID, stype.get(r.PMID), r.variable, tam[k][1], 'recovered-STUDY-0945',
                     'corrupt Adjduciation block; true call taken from Comments_TA/_YA')); continue
    tv = tam.get(k, ('',''))[0]; yv = yam.get(k, ('',''))[0]
    if not blank(tv) and not blank(yv) and norm(tv) == norm(yv):
        rows.append((r.PMID, stype.get(r.PMID), r.variable, tv, 'TA=YA', ''))
    elif k in phase2:
        rows.append((r.PMID, stype.get(r.PMID), r.variable, phase2[k], 'phaseII', ''))
    else:
        note = 'skip-logic disagreement (one reviewer N/A)' if (blank(tv) or blank(yv)) else 'pending'
        rows.append((r.PMID, stype.get(r.PMID), r.variable, '', 'unresolved', note))

out = pd.DataFrame(rows, columns=['PMID','Study_Type','variable','final','source','resolution_note'])

# ---- carry forward the 12 curated fixes from the 07_16 dataset ----
carried = 0
cf = cur[cur.source.isin(['phase2-normalised','skiplogic-resolved'])]
idx = {(p, v): i for i, (p, v) in enumerate(zip(out.PMID, out.variable))}
for _, r in cf.iterrows():
    i = idx.get((r.PMID, r.variable))
    if i is not None:
        out.at[i, 'final'] = r.final; out.at[i, 'source'] = r.source
        out.at[i, 'resolution_note'] = 'carried forward from 07_16 dataset'; carried += 1

# ---- split combined "Yes; not accounted" cells into parent + handling item ----
PAIR = {'causal_miss_outcome':'causal_hand_miss_outcom','causal_miss_exposure':'causal_hand_miss_exposure',
        'descriptive_miss_outcome':'descriptive_hand_miss_outcom'}
splits = 0
for i, r in out.iterrows():
    if r.variable in PAIR and 'not accounted' in str(r.final).lower():
        out.at[i, 'final'] = 'Yes'
        out.at[i, 'resolution_note'] = (str(r.resolution_note) + '; split from "Yes; not accounted"').strip('; ')
        j = idx.get((r.PMID, PAIR[r.variable]))
        if j is not None:
            out.at[j, 'final'] = 'No'; out.at[j, 'source'] = r.source
            out.at[j, 'resolution_note'] = 'split from "Yes; not accounted" on ' + r.variable
        splits += 1

# ---- multi-select spacing tidy (same convention the 07_16 dataset used): "a; b;" -> "a;b" ----
def tidy(v):
    s = str(v)
    if s.strip() in ('','nan') or ';' not in s: return v
    return ';'.join(p.strip() for p in s.split(';') if p.strip())
out['final'] = out['final'].map(tidy)

out = out.sort_values(['PMID','variable']).reset_index(drop=True)
out.to_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv', index=False, encoding='utf-8')

print('papers %d | rows %d | curated fixes carried %d | combined cells split %d' % (out.PMID.nunique(), len(out), carried, splits))
print('\nsource breakdown:'); print(out.source.value_counts().to_string())
print('\nStudy_Type:'); print(out.drop_duplicates('PMID').Study_Type.value_counts().to_string())

# ---- INTEGRITY CHECK: reproduce the existing 329 papers ----
old = cur[~cur.variable.isin(HOUSE)][['PMID','variable','final']].rename(columns={'final':'old'})
mg = out.merge(old, on=['PMID','variable'], how='inner')
mg['same'] = mg.final.fillna('').astype(str).str.strip().eq(mg.old.fillna('').astype(str).str.strip())
diff = mg[~mg.same]
print('\nINTEGRITY vs 07_16 dataset: %d shared cells | %d identical | %d differ' % (len(mg), int(mg.same.sum()), len(diff)))
if len(diff):
    print(diff.groupby('PMID').size().sort_values(ascending=False).head(12).to_string())
    diff.to_csv('data/quality-control/07_23_2026_rebuild_diffs.csv', index=False)
    print('  -> wrote data/quality-control/07_23_2026_rebuild_diffs.csv')

# ================= WIDE dataset (one row per paper) + affiliation stratifiers =================
wide = out.pivot_table(index='PMID', columns='variable', values='final', aggfunc='first').reset_index()
wide['Study_Type'] = wide.PMID.map(out.drop_duplicates('PMID').set_index('PMID').Study_Type)
AFF = ['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_authors',
       'pct_saudi_ge50','pct_saudi_cat3','pct_saudi_cat4','n_authors','n_saudi_authors','pct_saudi_reliable']
aff = pd.read_excel('data/authors/07_16_2026_saudi_affiliation_variables.xlsx')
aff['PMID'] = aff.PMID.astype(str)
wide = wide.merge(aff[['PMID'] + AFF], on='PMID', how='left')
front = ['PMID','Study_Type'] + AFF
wide = wide[front + [c for c in wide.columns if c not in front]]
wide.to_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv', index=False, encoding='utf-8')
miss = wide[AFF].isna().sum().sum()
print('\nWIDE: %d papers | %d cols | missing affiliation cells: %d' % (len(wide), len(wide.columns), miss))
print('  stratifier completeness:',
      {c: int(wide[c].notna().sum()) for c in ['first_author_saudi','last_author_saudi','corresponding_author_saudi','pct_saudi_ge50']})
