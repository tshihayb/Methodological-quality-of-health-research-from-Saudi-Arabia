import json, glob, os
import pandas as pd

# 1. combine batches
rows = []
for f in sorted(glob.glob('data/adjudication/rct-itt-screen/b*.json')):
    rows += json.load(open(f, encoding='utf-8'))
scr = pd.DataFrame(rows)
scr['pmid'] = scr['pmid'].astype(str)
assert len(scr) == 27, len(scr)
assert scr['pmid'].nunique() == 27

# 2. join tool-recorded confounding vars
df = pd.read_csv('data/analysis/07_16_2026_ANALYSIS_DATASET_long.csv', dtype=str)
keep = ['causal_base_conf_meth', 'causal_conf_var_det', 'causal_ltfu_bias',
        'causal_ltfu_acc', 'causal_time_verying']
tool = (df[df.variable.isin(keep)]
        .pivot_table(index='PMID', columns='variable', values='final', aggfunc='first')
        .reindex(columns=keep).reset_index().rename(columns={'PMID': 'pmid'}))
tool['pmid'] = tool['pmid'].astype(str)
m = scr.merge(tool, on='pmid', how='left')

# 3. order: PP-type first, then not-reported, then ITT
order = {'Per-protocol': 0, 'Completers-only': 1, 'Not-reported': 2, 'mITT': 3, 'ITT': 4}
m['ord'] = m['primary_analysis_population'].map(order).fillna(9)
m = m.sort_values(['ord', 'pmid']).drop(columns='ord').reset_index(drop=True)

# 4. write outputs
cols = ['pmid', 'primary_analysis_population', 'reports_any_pp_or_astreated', 'treatment_temporal',
        'pp_adjustment', 'pp_description', 'adherence_handling', 'evidence_quote', 'confidence', 'notes',
        'causal_base_conf_meth', 'causal_conf_var_det', 'causal_ltfu_bias', 'causal_ltfu_acc', 'causal_time_verying']
m = m[cols]
m.to_csv('data/adjudication/07_22_2026_rct_analysis_pop_screen.csv', index=False, encoding='utf-8-sig')
with pd.ExcelWriter('data/adjudication/07_22_2026_rct_analysis_pop_screen.xlsx') as xl:
    m.to_excel(xl, index=False, sheet_name='rct_analysis_pop')

# 5. summaries
print('=== primary_analysis_population (N=27) ===')
print(m['primary_analysis_population'].value_counts().to_string())
print()
print('=== reports_any_pp_or_astreated ===')
print(m['reports_any_pp_or_astreated'].value_counts().to_string())
print()
pp = m[m['reports_any_pp_or_astreated'] == 'yes']
print('=== The %d RCTs reporting a per-protocol-type effect ===' % len(pp))
for _, r in pp.iterrows():
    print('%s | %-15s | %-9s | pp_adj=%-55s | tool.conf_var_det=%s'
          % (r['pmid'], r['primary_analysis_population'], r['treatment_temporal'],
             str(r['pp_adjustment'])[:55], str(r['causal_conf_var_det'])[:45]))
print()
print('temporal split among the PP-type:', pp['treatment_temporal'].value_counts().to_dict())
print('wrote: data/adjudication/07_22_2026_rct_analysis_pop_screen.csv / .xlsx')
