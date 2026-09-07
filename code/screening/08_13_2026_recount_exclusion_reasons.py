# NOTE (public repository): 18 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
"""
Exclusion-reason recount for the PRISMA (agreed/adjudicated rule).  v2
Rule (user 2026-08-13): count the reason where BOTH reviewers agreed; where they
disagreed, use the adjudicated reason. Fold in batch-1 T_corr re-adjudication
(the "corresponding author not Saudi" first-pass filter was relaxed to "any Saudi author").

Scope = the 233 papers with final_disposition == 'Excluded at screening'.
Separate PRISMA steps (NOT in this recount): full-text-not-found(2), target-reached(13),
3-more panel(4), no-Saudi-affiliation(2), COI(1).
Ground truth for inclusion = the canonical 385 analysis set.
"""
import pandas as pd

# ---------- canonical population + separate (non-screening) exclusion buckets ----------
w = pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv', dtype=str, keep_default_na=False)
P385 = set(w.PMID.astype(str))
LATE = {'STUDY-0956':'COI (YA co-author)','STUDY-0136':'no Saudi affiliation','STUDY-0478':'no Saudi affiliation'}
TARGET_EXCL = {'STUDY-0439','STUDY-0274','STUDY-0020','STUDY-0082','STUDY-0480','STUDY-0187','STUDY-0033',
               'STUDY-0509','STUDY-0316','STUDY-0448','STUDY-0593','STUDY-0785','STUDY-0097'}
FT_NOT_FOUND = {'STUDY-0500','STUDY-0080'}   # ledger routes these to reports-not-retrieved

def G(r, c):
    v = str(r[c]).strip() if c in r.index else ''
    return '' if v.lower() == 'nan' else v

def canon(s):
    s = (s or '').strip().lower()
    if s == '': return ''
    if 'corresponding author' in s or 'not from a saudi' in s: return 'CORR_NOT_SAUDI'
    if 'non-human' in s or 'non human' in s: return 'Non-human / laboratory'
    if 'simulation' in s or 'emperical' in s or 'empirical' in s: return 'Non-empirical (protocol/simulation)'
    if 'narrative review' in s or 'systematic review' in s or s == 'review': return 'Review (narrative/systematic)'
    if 'qualitative' in s: return 'Qualitative research'
    if 'case report' in s or 'case series' in s: return 'Case report / series'
    if 'non-health' in s or 'non health' in s: return 'Non-health topic'
    return 'OTHER: ' + s

# ---------- batch-1: Excluded sheet + Included sheet + T_corr ----------
exc1 = pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Excluded', dtype=str).fillna('')
inc1 = pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','Included', dtype=str).fillna('')
tcorr = pd.read_excel('data/screening/f300_ta_ya_TA.xlsx','T_corr', dtype=str).fillna('')
tcorr_map = {G(r,'PMID'): dict(ns=G(r,'Status_t_new'), nr=G(r,'Reason for Exclusion_t_new'),
                               nt=G(r,'Study Type_t_new'), note=G(r,'Unnamed: 8')) for _,r in tcorr.iterrows()}

# ---------- batch-2: All sheet + sub-sheets ----------
allb2 = pd.read_excel('data/screening/s300_adjudicated.xlsx','All', dtype=str).fillna('')
sub_status = {}
for sh, dc in [('Talal incl but Yassser excl','Adjudicated '), ('Yasser incl but Talal excl','adjud')]:
    d = pd.read_excel('data/screening/s300_adjudicated.xlsx', sh, dtype=str).fillna('')
    for _, r in d.iterrows(): sub_status[G(r,'PMID')] = G(r,dc)

def disp_excl_at_screening(pm, ft=''):
    """True iff this screened PMID is a screening-reason exclusion (not a separate PRISMA bucket)."""
    if pm in P385 or pm in TARGET_EXCL or pm in LATE or pm in FT_NOT_FOUND: return False
    if ft and 'no found' in ft.lower(): return False
    return True

records = []
def add(seq, pm, batch, rt, ry, tc, adj, method, final, tier, evidence=''):
    records.append(dict(Seq=seq, PMID=pm, batch=batch, TA_reason_orig=rt, YA_reason_orig=ry,
        tcorr=tc, adjudicated_reason=adj, assignment_method=method, FINAL_reason=final,
        flag_tier=tier, evidence=evidence))

# ===== BATCH 1 — Excluded sheet =====
for _, r in exc1.iterrows():
    pm = G(r,'PMID')
    if not disp_excl_at_screening(pm): continue
    seq = G(r,'Seq'); rt = G(r,'Reason for Exclusion_t'); ry = G(r,'Reason for Exclusion_y')
    crt, cry = canon(rt), canon(ry); tc = tcorr_map.get(pm)
    tcinfo = (f"new={tc['ns']}/{tc['nr'] or tc['nt']}" if tc else '')
    if tc and tc['ns'].lower().startswith('exclude'):
        fr = canon(tc['nr']); add(seq, pm,'batch-1', rt, ry, tcinfo, tc['nr'],
            'adjudicated (T_corr re-review)', fr, '' if fr and not fr.startswith('OTHER') else 'A', tc['note'])
    elif tc and tc['ns'].lower().startswith('include'):
        add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'CONFLICT: T_corr re-included but absent from 385',
            'DISPOSITION UNCERTAIN', 'D', tc['note'])
    else:
        if crt not in ('','CORR_NOT_SAUDI') and cry not in ('','CORR_NOT_SAUDI'):
            if crt == cry: add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'agreed', crt, '')
            else: add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'DISAGREED reasons, no adjudication', crt+' | '+cry, 'A')
        elif crt not in ('','CORR_NOT_SAUDI') and cry == 'CORR_NOT_SAUDI':
            add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'TA real reason (YA corr-author, dropped)', crt, '')
        elif cry not in ('','CORR_NOT_SAUDI') and crt == 'CORR_NOT_SAUDI':
            add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'YA real reason (TA corr-author, dropped)', cry, '')
        elif crt == 'CORR_NOT_SAUDI' and cry == 'CORR_NOT_SAUDI':
            add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'both corr-author, NOT re-adjudicated', 'No Saudi author?', 'D')
        else:
            add(seq, pm,'batch-1', rt, ry, tcinfo, '', 'single/other', crt or cry, 'A')

# ===== BATCH 1 — Included sheet: status disagreements that ended up excluded =====
for _, r in inc1.iterrows():
    pm = G(r,'PMID')
    if not disp_excl_at_screening(pm): continue
    seq = G(r,'Seq'); st = G(r,'Status_t'); sy = G(r,'Status_y')
    add(seq, pm,'batch-1', '', '', f"Incl-sheet TA={st}/{sy}", '',
        'status disagreement (Included sheet), no reason recorded', 'NO REASON RECORDED', 'D',
        f"TA_task={G(r,'Study Type_t')} YA_task={G(r,'Study Type_y')}")

# ===== BATCH 2 =====
for _, r in allb2.iterrows():
    pm = G(r,'PMID')
    if not disp_excl_at_screening(pm): continue
    seq = G(r,'Seq'); ta = G(r,'Status_ta'); ya = G(r,'Status_ya')
    rt = G(r,'Reason for Exclusion_ta'); ry = G(r,'Reason for Exclusion_ya')
    exadj = G(r,'Exclusion after adjudication'); radj = G(r,'Reason')
    crt, cry = canon(rt), canon(ry)
    ev = '; '.join(x for x in [G(r,'Comments_ta'), G(r,'Comments_ya')] if x)
    if exadj:
        fr = canon(radj); add(seq, pm,'batch-2', rt, ry, '', radj, 'adjudicated (exp/outcome determination)',
            fr, '' if fr and not fr.startswith('OTHER') else 'A', (radj+'; '+ev).strip('; '))
    elif ta == 'Exclude' and ya == 'Exclude':
        if crt and cry and crt == cry: add(seq, pm,'batch-2', rt, ry, '', '', 'agreed', crt, '', ev)
        elif crt and not cry: add(seq, pm,'batch-2', rt, ry, '', '', 'single reason (both excluded)', crt, ('B' if ev else ''), ev)
        elif cry and not crt: add(seq, pm,'batch-2', rt, ry, '', '', 'single reason (both excluded)', cry, ('B' if ev else ''), ev)
        elif crt and cry and crt != cry: add(seq, pm,'batch-2', rt, ry, '', '', 'DISAGREED reasons, no adjudication', crt+' | '+cry, 'A', ev)
        else: add(seq, pm,'batch-2', rt, ry, '', '', 'both exclude, no reason', '(none)', 'A', ev)
    else:
        adjs = sub_status.get(pm, '')
        if adjs.lower().startswith('exclude'):
            er = ry if (ya=='Exclude' and ry) else (rt if (ta=='Exclude' and rt) else (rt or ry))
            fr = canon(er); add(seq, pm,'batch-2', rt, ry, f'sub-adj=Exclude', er,
                'adjudicated (status disagreement -> Exclude)', fr, '' if fr and not fr.startswith('OTHER') else 'A', ev)
        elif adjs.lower().startswith('include'):
            add(seq, pm,'batch-2', rt, ry, 'sub-adj=Include', '', 'CONFLICT: sub-adj Include but absent from 385',
                'DISPOSITION UNCERTAIN', 'D', ev)
        else:
            add(seq, pm,'batch-2', rt, ry, '', '', 'TA-only (YA status blank)', canon(rt or ry) or '(none)', 'C', ev)

rec = pd.DataFrame(records).sort_values(['batch','Seq'])
print("Total screening-exclusions:", len(rec), "(expect 233:  b1=107 + b2=126)")
print("  by batch:", rec.batch.value_counts().to_dict())

# collapse the disagreement 'A|B' finals into a primary category = TA's (listed first)
def primary(fr):
    return fr.split(' | ')[0] if ' | ' in fr else fr
rec['FINAL_primary'] = rec['FINAL_reason'].map(primary)

clean = rec[rec.flag_tier == '']
print("\n"+"="*64); print("CORRECTED TALLY — clean assignments only (n=%d)"%len(clean)); print("="*64)
print(clean.FINAL_reason.value_counts().to_string())
print("\n"+"="*64); print("If disagreements resolved to PRIMARY (TA-listed) reason (n=%d)"%len(rec[~rec.flag_tier.isin(['D'])])); print("="*64)
print(rec[~rec.flag_tier.isin(['D'])].FINAL_primary.value_counts().to_string())
print("\nflag tiers:", rec.flag_tier.replace('','(clean)').value_counts().to_dict())

rec.to_csv('data/screening/08_13_2026_exclusion_reason_recount_audit.csv', index=False, encoding='utf-8-sig')
print("\nwrote data/screening/08_13_2026_exclusion_reason_recount_audit.csv")
