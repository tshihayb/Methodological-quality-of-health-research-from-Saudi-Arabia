# -*- coding: utf-8 -*-
# Interrogates Yasser's concern: of the confounding-FLAGGED papers that "acknowledged" confounding,
# how many had NO adjustment vs adjusted-with-data-driven-selection? And confirm OK papers are excluded.
import pandas as pd
KA=dict(dtype=str,keep_default_na=False,na_values=[])
w  =pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv',**KA)
dom=pd.read_csv('data/scoring/07_30_2026_scored_domain.csv',**KA)

confVAL=set(dom[(dom.domain=='Confounding bias')&(dom.state=='VAL')].PMID)
confOK =set(dom[(dom.domain=='Confounding bias')&(dom.state=='OK')].PMID)
confREP=set(dom[(dom.domain=='Confounding bias')&(dom.state=='REP')].PMID)

wc=w[w.Study_Type=='Causal'].copy()
wc['ment']=wc['causal_err_disc'].str.lower().str.contains('confounding bias')
wc['noadj']=wc['causal_base_conf_meth'].str.lower().str.contains('no adjustment')
wc['isVAL']=wc.PMID.isin(confVAL)

sub=wc[wc.isVAL]
print('=== confounding VAL (flagged) papers:', len(sub), '===')
print('  base_conf_meth composition:')
print('   - NO adjustment at all      :', int(sub.noadj.sum()),
      '| of them acknowledged confounding:', int((sub.noadj & sub.ment).sum()))
print('   - adjusted WITH a method    :', int((~sub.noadj).sum()),
      '| of them acknowledged confounding:', int((~sub.noadj & sub.ment).sum()))
print('  TOTAL acknowledged (numerator):', int(sub.ment.sum()), '/', len(sub))

# what selection basis did the "adjusted + acknowledged" ones use? (the ones Yasser worries about)
adj_ack=sub[(~sub.noadj)&(sub.ment)]
print('\n=== the', len(adj_ack), 'adjusted-AND-acknowledged papers: confounder-selection basis ===')
print(adj_ack['causal_conf_var_det'].value_counts().to_string())

# confirm properly-scored OK papers are NOT in the base even if they mention confounding
subok=wc[wc.PMID.isin(confOK)]
print('\n=== confounding OK (not flagged) papers:', len(subok),
      '| mention confounding in discussion:', int(subok['causal_err_disc'].str.lower().str.contains('confounding bias').sum()),
      '-> these are EXCLUDED from the insight base (good)')
print('confounding REP (not reported basis):', len(confREP))
