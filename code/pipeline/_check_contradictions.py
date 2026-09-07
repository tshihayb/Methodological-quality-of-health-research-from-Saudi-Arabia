# -*- coding: utf-8 -*-
"""Re-run every hard skip-logic and soft-dependency check. Validated by reproducing the
catalogue's 329-era counts, then applied to the rebuilt 377 dataset."""
import sys
import pandas as pd

NA_RAW = {'skipped', 'should be skipped'}
def na(v):  return str(v).strip() in ('', 'nan') or str(v).strip() in NA_RAW
def has(v, s): return s.lower() in str(v).lower()
def opt(v, s): return any(x.strip().lower() == s.lower() for x in str(v).split(';'))  # whole selected option

def load(path):
    df = pd.read_csv(path, dtype=str)
    out = {}
    for t, pre in [('Causal', 'causal_'), ('Descriptive', 'descriptive_')]:
        sub = df[df.Study_Type == t]
        w = sub.pivot_table(index='PMID', columns='variable', values='final', aggfunc='first')
        w.columns = [c[len(pre):] if c.startswith(pre) else c for c in w.columns]
        out[t] = w
    return out

REAL_METH = lambda v: (not na(v)) and (not has(v, 'no adjustment'))
NAMES_BASIS = lambda v: (not na(v)) and (not has(v, 'no adjustment'))
LONGITUDINAL = ['Cohort', 'Case-crossover', 'Pre/post', 'Quasi-experimental', 'Randomized clinical trial']
IVMETH = lambda v: has(v, 'instrumental variable') or has(v, 'difference-in-diff') or has(v, 'discontinuity') or has(v, 'interrupted')

def soft(W):
    C, D = W['Causal'], W['Descriptive']
    g = lambda w, c: w[c] if c in w.columns else pd.Series('', index=w.index)
    R = {}
    des, fol, tv, tvm, bcm, cvd = (g(C,'design'), g(C,'follow'), g(C,'time_verying'),
                                   g(C,'tv_conf_meth'), g(C,'base_conf_meth'), g(C,'conf_var_det'))
    R['S1']  = C.index[(des == 'Cross-sectional') & (fol == 'Yes')]
    R['S8']  = C.index[(fol == 'Yes') & (des.isin(['Cross-sectional', 'Ecological']))]
    R['S2']  = C.index[(fol == 'No') & (tv == 'Yes')]
    R['S9']  = C.index[(tv == 'Yes') & (fol != 'Yes')]
    R['S6a'] = C.index[bcm.map(lambda v: opt(v, 'Randomization')) & ~des.astype(str).str.startswith('Randomized')]
    R['S6b'] = C.index[des.astype(str).str.startswith('Randomized') & ~bcm.map(lambda v: opt(v, 'Randomization'))]
    R['S7']  = C.index[des.astype(str).str.startswith('Quasi') & ~bcm.map(IVMETH)]
    R['S22'] = C.index[des.astype(str).str.startswith(tuple(LONGITUDINAL)) & (fol == 'No')]
    for tag, w in [('C', C), ('D', D)]:
        smp, bs = g(w, 'sampling'), g(w, 'base_sel')
        v = w.index[(smp == 'Non-random') & bs.map(lambda x: has(x, 'No baseline selection bias'))]
        R['S10' + tag] = v; R['S11' + tag] = v
    R['S3']  = C.index[g(C,'val_exposure').map(lambda v: has(v, 'does not usually require')) & (g(C,'exposure_type') != 'Objective')]
    for tag, w in [('C', C), ('D', D)]:
        R['S4' + tag] = w.index[g(w,'val_outcome').map(lambda v: has(v, 'does not usually require')) & (g(w,'outcome_type') != 'Objective')]
        R['S13' + tag] = w.index[(g(w,'out_bias_acc') == 'Yes') & ~g(w,'val_outcome').map(lambda v: has(v, 'criterion'))]
        R['S17' + tag] = w.index[g(w,'hand_miss_outcom').map(lambda v: has(v, 'imputation')) & (g(w,'miss_outcome') != 'Yes')]
    R['S12'] = C.index[(g(C,'exp_bias_acc') == 'Yes') & ~g(C,'val_exposure').map(lambda v: has(v, 'criterion'))]
    R['S15'] = C.index[~g(C,'ltfu_acc').map(na) & (g(C,'ltfu_bias') != 'Yes')]
    R['S16'] = C.index[g(C,'hand_miss_exposure').map(lambda v: has(v, 'imputation')) & (g(C,'miss_exposure') != 'Yes')]
    R['S5']  = C.index[bcm.map(REAL_METH) & ~cvd.map(NAMES_BASIS)]
    R['S5b'] = C.index[cvd.map(NAMES_BASIS) & ~bcm.map(REAL_METH)]
    R['S18'] = C.index[bcm.map(lambda v: has(v, 'no adjustment')) & cvd.map(NAMES_BASIS)]
    R['S19'] = C.index[tvm.map(REAL_METH) & (tv != 'Yes')]
    R['S23'] = C.index[tvm.map(REAL_METH) & bcm.map(lambda v: has(v, 'no adjustment'))]
    R['S24'] = C.index[tvm.map(REAL_METH) & ~cvd.map(NAMES_BASIS)]
    return R

# hard skip-logic, keyed by CHILD: a child is applicable only if NO parent triggers a skip.
# (Doing this parent-first double-counts children that have two parents, e.g. acc_sampl.)
WHOLEPOP = lambda v: has(v, 'whole population')
IS_NO    = lambda v: str(v).strip() == 'No'
NO_OR_NR = lambda v: str(v).strip() in ('No', 'Not reported or unknown')
NOBASESB = lambda v: has(v, 'No baseline selection bias')
CHILD_PARENTS = {
    'sample_size':        [('sampling', WHOLEPOP)],
    'acc_sampl':          [('sampling', WHOLEPOP), ('sample_size', IS_NO)],
    'sample_ach':         [('sampling', WHOLEPOP), ('sample_size', IS_NO)],
    'comp_dis':           [('base_sel', NOBASESB)],
    'ltfu_bias':          [('follow', IS_NO)],
    'ltfu_acc':           [('follow', IS_NO), ('ltfu_bias', NO_OR_NR)],
    'tv_conf_meth':       [('time_verying', IS_NO)],
    'hand_miss_exposure': [('miss_exposure', NO_OR_NR)],
    'hand_miss_outcom':   [('miss_outcome', NO_OR_NR)],
}

def skiplogic(W):
    gaps, extras = [], []
    for t, w in W.items():
        for kid, parents in CHILD_PARENTS.items():
            if kid not in w.columns: continue
            ps = [(pn, fn) for pn, fn in parents if pn in w.columns]
            if not ps: continue
            for pmid in w.index:
                pvals = [(pn, w.at[pmid, pn]) for pn, _ in ps]
                if any(na(pv) for _, pv in pvals): continue      # parent unanswered -> applicability indeterminate
                skipped = [(pn, pv) for (pn, fn), (_, pv) in zip(ps, pvals) if fn(pv)]
                kv = w.at[pmid, kid]
                if skipped:
                    if not na(kv):
                        pn, pv = skipped[0]
                        extras.append((t, pmid, pn, str(pv)[:34], kid, str(kv)[:30]))
                elif na(kv):
                    pn, pv = pvals[-1]
                    gaps.append((t, pmid, pn, str(pv)[:34], kid, ''))
    return gaps, extras

if __name__ == '__main__':
 for path, label in [('data/analysis/07_16_2026_ANALYSIS_DATASET_long.csv', '329 (validation)'),
                     ('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv', '377 (new)')]:
     W = load(path); R = soft(W); g, e = skiplogic(W)
     npap = sum(len(w) for w in W.values())
     print('=' * 74); print('%s   causal+descriptive papers = %d' % (label, npap)); print('=' * 74)
     print('  HARD skip-logic:  GAP = %d   EXTRA = %d' % (len(g), len(e)))
     if e:
         print('    EXTRAs:')
         for x in e[:12]: print('      %s %s  %s=%s  ->  %s=%s' % x)
     print('  SOFT rules:')
     for k in ['S1','S8','S2','S9','S6a','S6b','S7','S22','S10C','S11C','S10D','S11D','S3','S4C','S4D',
               'S12','S13C','S13D','S15','S16','S17C','S17D','S5','S5b','S18','S19','S23','S24']:
         v = R.get(k, [])
         mark = '' if len(v) == 0 else ('   <-- ' + ', '.join(sorted(v)[:9]) + ('...' if len(v) > 9 else ''))
         print('    %-5s %3d%s' % (k, len(v), mark))
     pd.DataFrame(g, columns=['task','PMID','parent','parent_value','child','child_value']).to_csv(
         '07_23_2026_skiplogic_gaps_%s.csv' % label.split()[0], index=False)
     print()
