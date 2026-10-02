import json
import pandas as pd

files = {'cohort':'data/adjudication/followup-screen/cohort.json','cc_A':'data/adjudication/followup-screen/cc_A.json','cc_B':'data/adjudication/followup-screen/cc_B.json','xsec_prepost':'data/adjudication/followup-screen/xsec_prepost.json'}
rows = []
for grp, fn in files.items():
    for r in json.load(open('data/adjudication/followup-screen/'+fn, encoding='utf-8')):
        r['group'] = grp
        rows.append(r)
df = pd.DataFrame(rows)
df['pmid'] = df['pmid'].astype(str)
assert len(df) == 17, len(df)

def final_follow(r):
    if str(r['group']).startswith('cc'):
        return r.get('follow_investigator_level') or 'No'
    w = str(r.get('which_value_is_wrong',''))
    rf = r['recorded_follow']
    if w == 'follow':
        return 'No' if rf == 'Yes' else 'Yes'
    if w == 'depends':
        return 'No'   # person-level ("same person") rule
    return rf         # design fix / consistent -> follow unchanged

def action(r):
    if str(r['group']).startswith('cc'):
        base = r.get('follow_base_level')
        tag = 'base-level=Yes EDGE CASE' if base == 'Yes' else 'cross-sectional substance'
        return 'no follow change (follow=No correct under same-person rule); ' + tag
    w = str(r.get('which_value_is_wrong',''))
    fix = r.get('recommended_fix','')
    if w == 'follow':  return 'FIX FOLLOW -> ' + fix
    if w == 'design':  return 'FIX DESIGN -> ' + fix
    if w == 'depends': return 'DEPENDS -> ' + fix
    return fix

df['final_follow_same_person'] = df.apply(final_follow, axis=1)
df['follow_changes'] = df['final_follow_same_person'] != df['recorded_follow']
df['action'] = df.apply(action, axis=1)

# order columns
common = ['pmid','group','recorded_design','recorded_follow','actual_design',
          'individual_followup_2plus_timepoints','final_follow_same_person','follow_changes',
          'which_value_is_wrong','recommended_fix','action',
          'cc_case_type','cc_control_sampling','cc_nested_or_population','follow_base_level','follow_investigator_level',
          'prepost_data_level','time_structure','evidence_quote','confidence','notes']
for c in common:
    if c not in df.columns: df[c] = ''
df = df[common].fillna('')

# sort: follow changes first, then design fixes, then CC
df['sortkey'] = df.apply(lambda r: (0 if r['follow_changes'] else (1 if str(r['which_value_is_wrong'])=='design' else 2)), axis=1)
df = df.sort_values(['sortkey','pmid']).drop(columns='sortkey').reset_index(drop=True)

df.to_csv('data/adjudication/07_22_2026_followup_S1_S22_resolution.csv', index=False, encoding='utf-8-sig')
with pd.ExcelWriter('data/adjudication/07_22_2026_followup_S1_S22_resolution.xlsx') as xl:
    df.to_excel(xl, index=False, sheet_name='followup_resolution')

print('=== ACTION SUMMARY (17 papers) ===')
fixfollow = df[df['action'].str.startswith('FIX FOLLOW')]
fixdesign = df[df['action'].str.startswith('FIX DESIGN')]
depends = df[df['action'].str.startswith('DEPENDS')]
cc = df[df['group'].str.startswith('cc')]
print('FIX FOLLOW  (%d):' % len(fixfollow))
for _,r in fixfollow.iterrows(): print('   %s  %s  [%s]'%(r['pmid'], r['recommended_fix'], r['confidence']))
print('FIX DESIGN, follow already correct (%d):' % len(fixdesign))
for _,r in fixdesign.iterrows(): print('   %s  %s  [%s]'%(r['pmid'], r['recommended_fix'], r['confidence']))
print('DEPENDS (%d):' % len(depends))
for _,r in depends.iterrows(): print('   %s  %s'%(r['pmid'], r['recommended_fix']))
print('CASE-CONTROL (%d): follow=No stands under same-person rule' % len(cc))
for _,r in cc.iterrows():
    print('   %s  case=%s samp=%s  base=%s invest=%s  [%s]'%(
        r['pmid'], r['cc_case_type'], r['cc_control_sampling'], r['follow_base_level'], r['follow_investigator_level'], r['confidence']))
print()
print('Net follow-value changes:', int(df['follow_changes'].sum()), '/ 17')
print('wrote data/adjudication/07_22_2026_followup_S1_S22_resolution.csv / .xlsx')
