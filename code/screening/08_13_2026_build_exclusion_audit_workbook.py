# NOTE (public repository): 24 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""Build the exclusion-reason audit workbook for TSA/YA verification + print detail."""
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

rec = pd.read_csv('data/screening/08_13_2026_exclusion_reason_recount_audit.csv', dtype=str).fillna('')
rec['Seq_n'] = pd.to_numeric(rec['Seq'], errors='coerce')
rec['link'] = 'https://pubmed.ncbi.nlm.nih.gov/' + rec['PMID'] + '/'

# ---- clean breakdown by batch ----
clean = rec[rec.flag_tier == '']
print("CLEAN assignments =", len(clean))
for b in ['batch-1','batch-2']:
    print(f"\n{b} clean (n={len(clean[clean.batch==b])}):")
    print(clean[clean.batch==b].FINAL_reason.value_counts().to_string())

TIER = {'A':'Reason DISAGREEMENT — both gave different substantive reasons; no adjudicated reason on record',
        'B':'Reason vs COMMENT mismatch — reviewer wrote a category but the free-text comment points elsewhere (often non-health)',
        'C':'TA-only — YA left the status blank (tail of batch-2, Seq 595-621); TA gave a clear reason',
        'D':'DISPOSITION UNCERTAIN — a reviewer re-included the paper (or no reason recorded) yet it is absent from the final 385'}

# ---- best-effort suggestions for flagged ----
SUGG = {
 'STUDY-0836':'contested: Non-human vs Systematic review — pick one (both are valid exclusions)',
 'STUDY-0190':'contested: Non-human vs Non-empirical(simulation)',
 'STUDY-0219':'contested: Non-human vs Narrative review',
 'STUDY-0681':'contested: Non-human vs Non-empirical(simulation)',
 'STUDY-0582':'contested: Non-human vs Non-empirical(simulation)',
 'STUDY-0684':'comment "two pages, not original research" -> Non-empirical / editorial',
 'STUDY-0858':'comment "a glossary! / not health related" -> Non-health (or Other non-empirical)',
 'STUDY-0998':'comment "RCT protocol" -> Non-empirical (protocol, no results) rather than Qualitative',
 'STUDY-0545':'comment "cyber security, not health" -> Non-health',
 'STUDY-0873':'comment "non-health / languages research" -> Non-health',
 'STUDY-0754':'comment "non-health / not health research" -> Non-health',
 'STUDY-0483':'comment "non-health" -> Non-health',
 'STUDY-0323':'comment "used in testing round 1" -> pilot/test paper; confirm it is an exclusion (TA: Non-human)',
 'STUDY-0874':'YA blank; use TA reason (Non-human)','STUDY-0726':'YA blank; use TA reason (Qualitative)',
 'STUDY-0470':'YA blank; use TA reason (Non-human)','STUDY-0054':'YA blank; use TA reason (Non-human)',
 'STUDY-0435':'YA blank; use TA reason (Non-health)','STUDY-0652':'YA blank; use TA reason (Non-human)',
 'STUDY-0374':'Both first-pass "corr-author"; TA re-included (Causal) but not in 385 — is there a Saudi author? include or exclude-why?',
 'STUDY-0168':'Both first-pass "corr-author"; TA re-included (Causal) but not in 385 — Saudi author? include or exclude-why?',
 'STUDY-0683':'Both first-pass "corr-author"; TA re-included (Causal) but not in 385 — Saudi author? include or exclude-why?',
 'STUDY-0849':'TA re-included (Causal); YA said Non-human; not in 385 — adjudicate include vs Non-human',
 'STUDY-0769':'Included-sheet: TA Include(Predictive) vs YA Exclude; not in 385; no reason recorded — adjudicate',
}
rec['best_effort'] = rec['PMID'].map(SUGG).fillna('')

flagged = rec[rec.flag_tier != ''].copy().sort_values(['flag_tier','batch','Seq_n'])
print("\n" + "="*80); print("FLAGGED FOR TSA/YA VERIFICATION  (n=%d)"%len(flagged)); print("="*80)
for t in ['D','A','B','C']:
    sub = flagged[flagged.flag_tier==t]
    print(f"\n--- TIER {t}  (n={len(sub)}) — {TIER[t]}")
    for _, r in sub.iterrows():
        print(f"  Seq {r['Seq']:>4} PMID {r['PMID']}  [{r['batch']}]  TA='{r['TA_reason_orig']}' YA='{r['YA_reason_orig']}'  {r['tcorr']}")
        print(f"           method: {r['assignment_method']}")
        if r['evidence']: print(f"           evidence: {r['evidence']}")
        print(f"           >> {r['best_effort']}")

# ================= build workbook =================
AC='16697A'
readme = pd.DataFrame({'Item':[
    'EXCLUSION-REASON RECOUNT — PRISMA screening exclusions','Prepared','Rule','','Scope','Ground truth',
    'Key change vs provisional','','Method: batch-1','Method: batch-2','','Flag tiers (see Needs_verification)',
    'Tier A','Tier B','Tier C','Tier D','','Separate PRISMA steps (NOT counted here)'],
    'Detail':[
    'Reason each screening-excluded paper was excluded, recomputed under the agreed/adjudicated rule.',
    '2026-08-13',
    'Count the reason where BOTH reviewers agreed; where they disagreed, use the adjudicated reason.',
    '',
    '233 papers with final_disposition = "Excluded at screening" (batch-1 = 107, batch-2 = 126).',
    'The canonical 385 analysis set (data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv) decides inclusion.',
    'The "corresponding-author-not-Saudi" first-pass filter was RELAXED to "any Saudi author"; the '
    'T_corr sheet re-adjudicated those 78 papers (re-Included, or re-Excluded with a real reason). '
    'Result: there is NO standalone "corr-author-not-Saudi" final exclusion category (provisional had 12).',
    '',
    'data/screening/f300_ta_ya_TA.xlsx: Excluded + Included sheets, folding in the T_corr re-adjudication.',
    'data/screening/s300_adjudicated.xlsx: All sheet (incl. Exclusion-after-adjudication) + 4 disagreement sub-sheets.',
    '',
    '24 papers could not be assigned cleanly; grouped into 4 tiers:',
    TIER['A'], TIER['B'], TIER['C'], TIER['D'],'',
    'full-text-not-found (2), target-reached (13), 3-more panel (4), no-Saudi-affiliation (2), COI (1).']})

# summary tally (clean + primary-resolved)
def tally(df, col):
    t = df[col].value_counts()
    return t
clean_t = clean.FINAL_reason.value_counts()
prim_t = rec[~rec.flag_tier.isin(['D'])]['FINAL_reason'].map(lambda s: s.split(' | ')[0]).value_counts()
order = ['Non-human / laboratory','Review (narrative/systematic)','Qualitative research',
         'Non-empirical (protocol/simulation)','Case report / series','Non-health topic']
prov = {'Non-human / laboratory':178,'Review (narrative/systematic)':14,'Qualitative research':11,
        'Non-empirical (protocol/simulation)':8,'Case report / series':6,'Non-health topic':1}
srows=[]
for k in order:
    srows.append({'Exclusion reason':k,'Provisional (old)':prov.get(k,0),
                  'Corrected — clean only':int(clean_t.get(k,0)),
                  'Corrected — disagreements folded to primary':int(prim_t.get(k,0))})
srows.append({'Exclusion reason':'Corr. author not Saudi (REMOVED)','Provisional (old)':12,
              'Corrected — clean only':0,'Corrected — disagreements folded to primary':0})
srows.append({'Exclusion reason':'Reason not recorded / disposition uncertain','Provisional (old)':3,
              'Corrected — clean only':len(rec[rec.flag_tier=='D']),
              'Corrected — disagreements folded to primary':len(rec[rec.flag_tier=='D'])})
srows.append({'Exclusion reason':'TOTAL screening exclusions','Provisional (old)':233,
              'Corrected — clean only':209,
              'Corrected — disagreements folded to primary':233})
summ = pd.DataFrame(srows)

audit = rec.sort_values(['batch','Seq_n'])[['Seq','PMID','link','batch','TA_reason_orig','YA_reason_orig',
    'tcorr','adjudicated_reason','assignment_method','FINAL_reason','flag_tier','evidence','best_effort']]
needs = flagged[['flag_tier','Seq','PMID','link','batch','TA_reason_orig','YA_reason_orig','tcorr',
                 'assignment_method','evidence','best_effort']]

out='data/screening/08_13_2026_exclusion_reason_audit.xlsx'
with pd.ExcelWriter(out, engine='openpyxl') as xw:
    readme.to_excel(xw,sheet_name='README',index=False)
    summ.to_excel(xw,sheet_name='Summary_tally',index=False)
    audit.to_excel(xw,sheet_name='Full_audit_233',index=False)
    needs.to_excel(xw,sheet_name='Needs_verification_24',index=False)
    hf=Font(bold=True,color='FFFFFF'); fill=PatternFill('solid',fgColor=AC)
    for sh in xw.sheets:
        ws=xw.sheets[sh]; ws.freeze_panes='A2'
        for c in ws[1]: c.font=hf; c.fill=fill; c.alignment=Alignment(vertical='top',wrap_text=True)
    xw.sheets['README'].column_dimensions['A'].width=30; xw.sheets['README'].column_dimensions['B'].width=110
    for c in xw.sheets['README']['A']: c.font=Font(bold=True); c.alignment=Alignment(vertical='top')
    for c in xw.sheets['README']['B']: c.alignment=Alignment(vertical='top',wrap_text=True)
    for shn,df in [('Summary_tally',summ),('Full_audit_233',audit),('Needs_verification_24',needs)]:
        ws=xw.sheets[shn]
        for i,col in enumerate(df.columns,1):
            wdt=min(60,max(11,int(df[col].map(lambda v:len(str(v))).max())+2))
            ws.column_dimensions[get_column_letter(i)].width=wdt
print("\nwrote", out)
