# NOTE (public repository): 5 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Emits TWO versions of Table 2, differing only in how the "(select all that apply)" items are shown:
#   combo    -> every answered COMBINATION, each paper counted once  (columns sum to 100%)
#   marginal -> how often each individual OPTION was selected        (columns do NOT sum to 100%)
# In both versions the Flagged column stays PAPER-level, so the two are directly comparable.
import pandas as pd, html as H, re as RE
df = pd.read_csv('data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv', dtype=str)
NA_RAW = {'skipped','should be skipped'}

# task denominators are derived from the data, never hardcoded
_pap  = df.drop_duplicates('PMID')
N_D   = int((_pap.Study_Type == 'Descriptive').sum())
N_C   = int((_pap.Study_Type == 'Causal').sum())
N_T   = N_D + N_C
# ⚠ DERIVE THE SAMPLE SIZE, NEVER STATE IT.  The footnote used to read "the 2026-07-23
# dataset (377 included papers)" - hardcoded, and wrong since 2026-08-08, when the
# canonical dataset was overwritten to 385 WITHOUT the filename changing.  A submission
# table was telling reviewers the wrong sample size.
N_ALL = int(_pap.PMID.nunique())
assert N_ALL == N_T + int((_pap.Study_Type == 'Predictive').sum()), N_ALL
PCT_D = 100.0 * N_D / N_T
PCT_C = 100.0 * N_C / N_T

# ---- cross-variable applicability: an item can be N/A because of ANOTHER item's answer ----
# Confounder-selection basis (TSA ruling 2026-07-23): the question asks HOW confounders were chosen,
# so it only applies where confounders were actually selected. Excluded when
#   (a) base_conf_meth = "No adjustment" only            -> nothing was adjusted, so nothing was selected
#   (b) randomization-only trials                        -> randomisation selects no confounders
# STRICT reading: (b) excludes all randomization-only papers. To switch to the lenient reading
# (keep the 4 baseline-covariate-adjusted per-protocol trials), add them to _CVD_KEEP below.
_CVD_KEEP = set()   # lenient alternative: {'STUDY-0669','STUDY-0040','STUDY-0764','STUDY-0567'}
_cau  = df[df.Study_Type=='Causal'].pivot_table(index='PMID', columns='variable', values='final', aggfunc='first')
_bcm  = _cau.get('causal_base_conf_meth', pd.Series(dtype=str)).fillna('')
_noadj    = _bcm.str.lower().str.contains('no adjustment')
_randonly = _bcm.str.strip().str.lower() == 'randomization'
ITEM_NA_PMIDS = {'conf_var_det': {str(i) for i in _cau.index[_noadj | _randonly]} - _CVD_KEEP}

def SPLIT_OPTS(v):
    """Split one select-all-that-apply answer into its selected options.

    ⚠ FIXED 2026-08-22.  This was RE.split(r'[;,]', v), and a comma is NOT always a
    delimiter: one option's own text carries two of them —

        "Instrumental variable analysis besides randomization (difference-in-difference,
         regression discontinuity design, and interrupted time series)"

    — so the published table split that single answer into three rows, INVENTING two
    confounding methods that the instrument does not offer ("regression discontinuity
    design", "and interrupted time series)") and truncating the real one mid-parenthesis.
    One causal paper, one answer, three fabricated rows.

    A comma cannot simply be dropped from the delimiter set either: one paper answered
    "Random error, Selection bias;Confounding bias" on the errors-mentioned item, where the
    comma genuinely separates two selections.  So ';' always splits, and ',' splits only
    OUTSIDE parentheses, which is the difference between the two cases.
    """
    parts, buf, depth = [], [], 0
    for ch in v:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth = max(0, depth - 1)
        if ch == ';' or (ch == ',' and depth == 0):
            parts.append(''.join(buf)); buf = []
        else:
            buf.append(ch)
    parts.append(''.join(buf))
    return parts


# the two answers the rule above turns on, asserted so a data refresh cannot silently
# change what this function is protecting against
assert SPLIT_OPTS('Regression;Instrumental variable analysis besides randomization '
                  '(difference-in-difference, regression discontinuity design, and '
                  'interrupted time series)') == [
    'Regression', 'Instrumental variable analysis besides randomization '
                  '(difference-in-difference, regression discontinuity design, and '
                  'interrupted time series)']
assert [p.strip() for p in SPLIT_OPTS('Random error, Selection bias;Confounding bias')] == [
    'Random error', 'Selection bias', 'Confounding bias']


def eq(x):  return lambda v: v==x
def has(x): return lambda v: x.lower() in v.lower()
def sw(x):  return lambda v: v.startswith(x)
ANY_TRUE = lambda v: True
ANYMETH = lambda v: any(k in v.lower() for k in ['regression','matching','stratification','propensity','restriction','inverse probability','randomization'])

VALID = [ (has('criterion'),'Criterion validity',False),(has('content/face'),'Content / face validity',False),
          (eq('No'),'No validation',True),(has('does not usually require'),'N/A — validation not needed',None) ]
MISSR = [ (eq('No'),'No',False),(eq('Yes'),'Yes',False),(eq('Not reported or unknown'),'Not reported',True) ]
# missing data is split: was it handled at all (scored), then HOW (descriptive, among those that handled)
HANDLED  = [ (eq('No'),'No — not handled',True),(has('Yes'),'Yes — handled',False) ]
HANDMETH = [ (eq('No'),'na',None),                                     # not handled -> the method question doesn't apply
             (has('multiple imputation'),'Multiple imputation',False),
             (has('predicted value using regression'),'Single imputation — regression-predicted value',False),
             (has('last value carried forward'),'Single imputation — last value carried forward',False),
             (has('mean value'),'Single imputation — mean value',False),
             (has('indicator'),'Missing-indicator category',False) ]
# confounding is split the same way: was any adjustment attempted (scored), then WHICH method(s)
CONF_ATT = [ (has('No adjustment'),'No — no adjustment attempted',True),(ANYMETH,'Yes — a method was used',False) ]
# the tool never asks whether measurement bias EXISTS — it goes straight to direction/accounting, i.e. presence is assumed
PRESENT  = [ (ANY_TRUE,'Present (assumed for every study)',False) ]
YESNO_NOprob = [ (eq('Yes'),'Yes',False),(eq('No'),'No',True) ]
OBJSUBJ = [ (eq('Objective'),'Objective',False),(eq('Subjective'),'Subjective',False) ]
DIFF = [ (sw('Differential'),'Differential',True),(sw('Non-differential'),'Non-differential',False) ]

# ---- multi-select ("select all that apply") items: list every answered COMBINATION, each paper counted once ----
def COMBO(flagfn, okfn, norm, skipfn=None, optflag=None): return ('COMBO', flagfn, okfn, norm, skipfn, optflag)
NOFLAG = lambda v: False
noadj  = lambda v: 'no adjustment' in v.lower()
# per-OPTION problem test, used only by the marginal version's rows
cvd_optflag = lambda p: not ('directed acyclic' in p.lower() or 'previous literature' in p.lower())
err_optflag = lambda p: 'none of the above' in p.lower()

SHORT_MAP=[('Inverse probability of treatment weighting','IPTW'),('Propensity score','PS'),
 ('No adjustment for baseline and time-varying confounding was done','No adjustment'),
 ('No adjustment for baseline confounding was done','No adjustment'),
 ('Based on Directed Acyclic Graphs (DAGs)/subject matter expertise','DAGs / subject-matter expertise'),
 ('Based on previous literature','Previous literature'),
 ('Based on statistical criteria','Statistical criteria'),
 ('Based on change of estimate','Change of estimate'),
 ('Based on none of the above','None of the above')]
# variant flags (set per output file in the VARIANTS loop below)
LONGNAMES = False   # True -> keep IPTW / PS / DAGs spelled out in full
DROPTF    = False   # True -> omit the Total and Flagged columns
SHORT_MAP_LONG=[('No adjustment for baseline and time-varying confounding was done','No adjustment'),
 ('No adjustment for baseline confounding was done','No adjustment'),
 ('Based on Directed Acyclic Graphs (DAGs)/subject matter expertise','Directed acyclic graphs / subject-matter expertise'),
 ('Based on previous literature','Previous literature'),
 ('Based on statistical criteria','Statistical criteria'),
 ('Based on change of estimate','Change of estimate'),
 ('Based on none of the above','None of the above')]
def shorten(v):
    for a,b in (SHORT_MAP_LONG if LONGNAMES else SHORT_MAP): v=v.replace(a,b)
    return v.replace(';','; ')

# baseline / time-varying confounding method
bcm_flag = lambda v: 'no adjustment' in v.lower()
bcm_ok   = lambda v: ANYMETH(v) or 'no adjustment' in v.lower()
# confounder-selection basis: NOT an error only when a DAG/subject-matter or previous-literature basis is named
CVD_KEYS = ['directed acyclic','previous literature','statistical criteria','change of estimate','none of the above','no adjustment']
cvd_ok   = lambda v: any(k in v.lower() for k in CVD_KEYS)
cvd_flag = lambda v: not ('directed acyclic' in v.lower() or 'previous literature' in v.lower())
# errors mentioned in the discussion: canonicalise so delimiter/case variants merge, then sort to taxonomy order
ERR_CANON=[('random error','Random error'),('selection bias','Selection bias'),('measurement bias','Measurement bias'),
           ('confounding bias','Confounding bias'),('missing data','Missing data')]
def err_norm(v):
    low=v.lower()
    if 'none of the above' in low: return 'None mentioned'
    parts=[lab for key,lab in ERR_CANON if key in low]
    return '; '.join(parts) if parts else v
err_ok   = lambda v: ('none of the above' in v.lower()) or any(k in v.lower() for k,_ in ERR_CANON)
err_flag = lambda v: 'none of the above' in v.lower()

# (domain, subdomain, stem, label, scope, type, rules, na_label, depth)
ITEMS = [
 ('Random error','','sampling','Sampling approach','both','classifier',
    [(has('whole population'),'Whole population (census)',False),(ANY_TRUE,'A sample was taken',False)],'N/A',0),
 ('Random error','','sampling','If sampled — random or non-random?','both','classifier',
    [(has('whole population'),'na',None),(eq('Random'),'Random',False),(eq('Non-random'),'Non-random',False)],'N/A',1),
 ('Random error','','sample_size','Sample-size calculation done?','both','reporting',
    [(eq('Yes'),'Yes',False),(eq('No'),'No',True)],'N/A',1),
 ('Random error','','acc_sampl','Accounted for ineligibility, non-response, loss to follow-up, change in exposure status, etc. in the sample-size calculation?','both','validity',
    [(eq('Yes'),'Yes',False),(eq('No'),'No',True)],'N/A',2),
 ('Random error','','sample_ach','Required sample size achieved?','both','validity',
    [(eq('Yes'),'Yes',False),(eq('No'),'No',True)],'N/A',2),

 ('Selection bias','','base_sel','Baseline selection bias presence?','both','classifier',
    [(eq('Yes'),'Baseline selection bias present',False),(eq('No'),'Baseline selection bias present',False),
     (has('No baseline selection bias'),'No baseline selection bias present',False)],'N/A',0),
 ('Selection bias','','base_sel','Baseline selection bias accounted for?','both','validity',
    [(has('No baseline selection bias'),'na',None),(eq('Yes'),'Accounted for',False),(eq('No'),'Not accounted for',True)],'N/A',1),
 ('Selection bias','','comp_dis','Compared responders vs non-responders?','causal','reporting',
    [(eq('Yes'),'Compared',False),(eq('No'),'Not compared',True)],'N/A',1),
 ('Selection bias','','follow','Follow-up presence in the study?','causal','gate',
    [(eq('Yes'),'Follow-up present',False),(eq('No'),'No follow-up',False)],'N/A',0),
 ('Selection bias','','ltfu_bias','Loss-to-follow-up bias presence?','causal','reporting',
    [(eq('Yes'),'Yes',True),(eq('Not reported or unknown'),'Not reported',True),(eq('No'),'No',False)],'N/A',1),
 ('Selection bias','','ltfu_acc','Loss-to-follow-up bias accounted for?','causal','validity',
    [(eq('Yes'),'Yes',False),(eq('No'),'No',True)],'N/A',2),

 ('Measurement bias','Outcome measurement','outcome_type','Nature of the outcome','both','classifier',OBJSUBJ,'N/A',0),
 ('Measurement bias','Outcome measurement','val_outcome','Validated outcome measurement?','both','both',VALID,'N/A',0),
 ('Measurement bias','Outcome measurement','out_bias_acc','Outcome measurement bias presence?','both','classifier',PRESENT,'N/A',0),
 ('Measurement bias','Outcome measurement','diff_or_nondiff_out','Outcome misclassification differential?','causal','classifier',DIFF,'N/A',1),
 ('Measurement bias','Outcome measurement','out_bias_acc','Outcome measurement bias accounted for?','both','validity',YESNO_NOprob,'N/A',1),
 ('Measurement bias','Exposure measurement','exposure_type','Nature of the exposure','causal','classifier',OBJSUBJ,'N/A',0),
 ('Measurement bias','Exposure measurement','val_exposure','Validated exposure measurement?','causal','both',VALID,'N/A',0),
 ('Measurement bias','Exposure measurement','exp_bias_acc','Exposure measurement bias presence?','causal','classifier',PRESENT,'N/A',0),
 ('Measurement bias','Exposure measurement','diff_or_nondiff_exp','Exposure misclassification differential?','causal','classifier',DIFF,'N/A',1),
 ('Measurement bias','Exposure measurement','exp_bias_acc','Exposure measurement bias accounted for?','causal','validity',YESNO_NOprob,'N/A',1),
 ('Measurement bias','Relation of exposure & outcome measurement biases','dep_or_indep_misc','Exposure measurement bias independent or dependent of the outcome measurement bias?','causal','validity',
    [(eq('Independent'),'Independent',False),(eq('Dependent'),'Dependent',True)],'N/A',0),

 ('Confounding bias','','base_conf_meth','Baseline confounding adjustment/control attempted?','causal','validity',CONF_ATT,'N/A',0),
 ('Confounding bias','','base_conf_meth','Baseline confounding method? (select all that apply)','causal','classifier',
    COMBO(NOFLAG,ANYMETH,shorten,noadj),'N/A',1),
 ('Confounding bias','','time_verying','Time-varying effect estimated?','causal','gate',
    [(eq('Yes'),'Yes',False),(eq('No'),'No',False)],'N/A',0),
 ('Confounding bias','','tv_conf_meth','Time-varying confounding adjustment/control attempted?','causal','validity',CONF_ATT,'N/A',1),
 ('Confounding bias','','tv_conf_meth','Time-varying confounding method? (select all that apply)','causal','classifier',
    COMBO(NOFLAG,ANYMETH,shorten,noadj),'N/A',2),
 ('Confounding bias','','conf_var_det','Confounder-selection basis? (select all that apply)','causal','both',
    COMBO(cvd_flag,cvd_ok,shorten,None,cvd_optflag),'N/A',0),

 ('Missing data','Outcome','miss_outcome','Any missing outcome?','both','reporting',MISSR,'N/A',0),
 ('Missing data','Outcome','hand_miss_outcom','Missing outcome handled?','both','validity',HANDLED,'N/A',1),
 ('Missing data','Outcome','hand_miss_outcom','Missing-outcome handling method?','both','classifier',HANDMETH,'N/A',2),
 ('Missing data','Exposure','miss_exposure','Any missing exposure?','causal','reporting',MISSR,'N/A',0),
 ('Missing data','Exposure','hand_miss_exposure','Missing exposure handled?','causal','validity',HANDLED,'N/A',1),
 ('Missing data','Exposure','hand_miss_exposure','Missing-exposure handling method?','causal','classifier',HANDMETH,'N/A',2),

 ('Mentioning errors in limitation/discussion','','err_disc','Errors qualitatively mentioned in the discussion? (select all that apply)','both','reporting',
    COMBO(err_flag,err_ok,err_norm,None,err_optflag),'N/A',0),
 ('Conflating the task','','confl_task','Investigated an association beyond describing the sample?','descriptive','validity',
    [(eq('Yes'),'Yes — investigated association',True),(eq('No'),'No',False)],'N/A',0),
]

def othlab(v):
    t = v if len(v)<=52 else v[:51]+'…'
    return 'Other / uncodable — “%s”'%t

def classify(val, rules, na_label):
    v=(val if pd.notna(val) else '').strip()
    if v=='' or v in NA_RAW: return (na_label,'na')        # structural skip (parent branched away) -> reduces applicable base, row folded into base line
    for pred,label,prob in rules:
        if pred(v):
            if label=='na': return (na_label,'na')          # structural skip mapped by a rule (e.g., "whole population" for the random/non-random item)
            if prob is None: return (label,'nna')           # substantive N/A (e.g., "validation not needed"): stays a visible response + in the base, but not flaggable
            return (label, 'prob' if prob else 'ok')
    return (othlab(v),'other')

def counts(task, stem, rules, na_label):
    v=('descriptive_' if task=='Descriptive' else 'causal_')+stem
    sub=df[(df.Study_Type==task)&(df.variable==v)]
    if sub.empty: return None
    s=sub['final']
    gate=ITEM_NA_PMIDS.get(stem,set())                      # PMIDs where another item makes this one N/A
    pids=list(sub['PMID'].astype(str))
    out={}; order=[]
    if isinstance(rules,tuple) and rules[0]=='COMBO':
        _,flagfn,okfn,norm,skipfn = rules[:5]
        for pid,val in zip(pids,s):
            vv=(val if pd.notna(val) else '').strip()
            if pid in gate or vv=='' or vv in NA_RAW or (skipfn and skipfn(vv)): lab,kind=na_label,'na'
            else:
                lab = norm(vv) if okfn(vv) else othlab(vv)
                kind = 'other' if not okfn(vv) else ('prob' if flagfn(vv) else 'ok')
            if lab not in out: out[lab]=[0,kind]; order.append(lab)
            out[lab][0]+=1; out[lab][1]=kind
        rank={'ok':0,'prob':0,'other':1,'na':2}
        return out, sorted(out, key=lambda k:(rank.get(out[k][1],0), -out[k][0], k))
    for _,lab,_ in rules:
        lab2 = na_label if lab=='na' else lab
        if lab2 not in out: out[lab2]=[0,None]; order.append(lab2)
    for pid,val in zip(pids,s):
        lab,kind = (na_label,'na') if pid in gate else classify(val, rules, na_label)
        if lab not in out: out[lab]=[0,kind]; order.append(lab)
        out[lab][0]+=1; out[lab][1]=kind
    return out, order

def marginal_counts(task, stem, rules, na_label):
    """Per-OPTION selection frequency for a select-all-that-apply item: a paper that ticked 3
    options is counted in all 3, so these columns do NOT sum to 100%. Denominator is still the
    applicable base, so each % reads '<x>% of applicable papers selected this option'."""
    v=('descriptive_' if task=='Descriptive' else 'causal_')+stem
    sub=df[(df.Study_Type==task)&(df.variable==v)]
    if sub.empty: return None
    s=sub['final']; gate=ITEM_NA_PMIDS.get(stem,set()); pids=list(sub['PMID'].astype(str))
    _,flagfn,okfn,norm,skipfn = rules[:5]
    optflag = rules[5] if len(rules)>5 else None
    out={}
    def bump(lab,kind):
        if lab not in out: out[lab]=[0,kind]
        out[lab][0]+=1; out[lab][1]=kind
    for pid,val in zip(pids,s):
        vv=(val if pd.notna(val) else '').strip()
        if pid in gate or vv=='' or vv in NA_RAW or (skipfn and skipfn(vv)): continue   # not applicable -> excluded, same base as the combo version
        if not okfn(vv): bump(othlab(vv),'other'); continue
        seen=set()
        for part in SPLIT_OPTS(vv):
            p=part.strip()
            if not p: continue
            lab=norm(p)
            if lab in seen: continue                                     # a repeated option within one paper counts once
            seen.add(lab)
            bump(lab,'prob' if (optflag and optflag(p)) else 'ok')
    rank={'ok':0,'prob':0,'other':1,'na':2}
    return out, sorted(out, key=lambda k:(rank.get(out[k][1],0), -out[k][0], k))

def pct(n,N):
    if not n or not N: return '<span class="z">0</span>'
    return '%d <span class="pct">(%.1f)</span>'%(n,100.0*n/N)

def flag_stats(R):
    # (flagged n, applicable n) for one task, derived from the SAME classification the rows use
    if R is None: return (None,None)
    out=R[0]
    flagged=sum(val[0] for val in out.values() if val[1]=='prob')
    applic =sum(val[0] for val in out.values() if val[1] not in ('na','nna'))
    return (flagged, applic)

def flagcell(typ, scope, dR, cR):
    if typ in ('classifier','gate'):
        return '<td class="flagcell"><span class="ns">not scored</span></td>'
    fd,ad=flag_stats(dR); fc,ac=flag_stats(cR)
    lines=[]
    if scope in ('both','descriptive') and ad:
        lines.append('<div class="fgrow" title="%d of %d applicable flagged — Descriptive"><span class="fk">D</span><span class="fp">%.1f</span></div>'%(fd,ad,100.0*fd/ad))
    if scope in ('both','causal') and ac:
        lines.append('<div class="fgrow" title="%d of %d applicable flagged — Causal"><span class="fk">C</span><span class="fp">%.1f</span></div>'%(fc,ac,100.0*fc/ac))
    if not lines: return '<td class="flagcell"><span class="z">—</span></td>'
    return '<td class="flagcell"><div class="fg">%s</div></td>'%''.join(lines)

DOM_ORDER=['Random error','Selection bias','Measurement bias','Confounding bias','Missing data',
           'Mentioning errors in limitation/discussion','Conflating the task']
NTOT={'both':N_T,'causal':N_C,'descriptive':N_D}
SCTAG={'causal':('Causal only','sc-c'),'descriptive':('Descriptive only','sc-d'),'both':('Both','sc-b')}
TYPE={'reporting':('rep','Reporting'),'validity':('val','Validity'),'both':('repval','Rep + Val'),'gate':('gate','Gate'),'classifier':('cls','Classifier')}

def na_sum(R): return sum(v[0] for v in R[0].values() if v[1]=='na') if R else None

def build(marginal):
  rows=[]
  NC = 3 if DROPTF else 5
  for dom in DOM_ORDER:
    rows.append(('<tr class="dom"><td colspan="%d">'%NC)+'<span class="dl"><span class="dt"></span>%s</span></td></tr>'%H.escape(dom))
    cursub=None
    for item in [it for it in ITEMS if it[0]==dom]:
        d,sub,stem,label,scope,typ,rules,na,depth = item
        if sub!=cursub:
            cursub=sub
            if sub: rows.append('<tr class="subdom"><td colspan="%d"><span class="sdl">%%s</span></td></tr>'%NC%H.escape(sub))
        dep = depth>=1
        sctag,sccls=SCTAG[scope]; tcls,tlab=TYPE[typ]
        dR=counts('Descriptive',stem,rules,na); cR=counts('Causal',stem,rules,na)
        # dR/cR always stay PAPER-level (they drive the applicable base and the Flagged column);
        # only the displayed response rows switch to per-option counts in the marginal version.
        is_combo = isinstance(rules,tuple) and rules[0]=='COMBO'
        if marginal and is_combo:
            dD=marginal_counts('Descriptive',stem,rules,na); cD=marginal_counts('Causal',stem,rules,na)
        else:
            dD,cD = dR,cR
        Ntot=NTOT[scope]
        nad=na_sum(dR); nac=na_sum(cR); nat=(nad or 0)+(nac or 0)
        pad=16+depth*22; padc=30+depth*22
        # ⚠ The SLIM variant carries the SCOPE badge but not the TYPE badge (TSA,
        # 2026-08-22).  Classifier / Reporting / Validity / Gate / Rep + Val say how an item
        # is SCORED, and this table is descriptive - that belongs to Figure 4 and to
        # Supplementary Table S1, which already give it per item.  Scope stays because it
        # says which papers an item was PUT to, which is what the two columns mean.
        tags=('<span class="tags"><span class="sc %s">%s</span></span>'%(sccls,sctag) if DROPTF
              else '<span class="tags"><span class="sc %s">%s</span> <span class="tp %s">%s</span></span>'
                   %(sccls,sctag,tcls,tlab))
        prefix='<span class="arw">&#8627;</span> ' if dep else ''
        fcell=flagcell(typ,scope,dR,cR)
        app_d=None if dR is None else N_D-nad
        app_c=None if cR is None else N_C-nac
        app_t=Ntot-nat
        has_base = nat>0   # any structural N/A -> show the applicable base on the item line and compute the rows within it
        cls='item dep' if dep else 'item'
        if has_base:
            dba='<span class="ndash">—</span>' if dR is None else '<span class="nav">%d</span>'%app_d
            cba='<span class="ndash">—</span>' if cR is None else '<span class="nav">%d</span>'%app_c
            if DROPTF:
                rows.append('<tr class="%s"><td class="inm" style="padding-left:%dpx"><span class="q">%s%s</span>%s '
                            '<span class="nalbl">applies to &#8594;</span></td>'
                            '<td class="nac">%s</td><td class="nac">%s</td></tr>'%(cls,pad,prefix,H.escape(label),tags,dba,cba))
            else:
                rows.append('<tr class="%s"><td class="inm" style="padding-left:%dpx"><span class="q">%s%s</span>%s '
                            '<span class="nalbl">applies to &#8594;</span></td><td class="tc nac"><span class="nav">%d</span></td>'
                            '<td class="nac">%s</td><td class="nac">%s</td>%s</tr>'%(cls,pad,prefix,H.escape(label),tags,app_t,dba,cba,fcell))
        else:
            if DROPTF:
                rows.append('<tr class="%s"><td class="inm" colspan="3" style="padding-left:%dpx"><span class="q">%s%s</span>%s</td></tr>'%(cls,pad,prefix,H.escape(label),tags))
            else:
                rows.append('<tr class="%s"><td class="inm" colspan="4" style="padding-left:%dpx"><span class="q">%s%s</span>%s</td>%s</tr>'%(cls,pad,prefix,H.escape(label),tags,fcell))
        order=[]
        for R in (cD,dD):
            if R:
                for lab in R[1]:
                    if lab not in order: order.append(lab)
        for lab in order:
            kind=(cD[0].get(lab,[0,None])[1] if (cD and lab in cD[0]) else (dD[0].get(lab,[0,None])[1] if (dD and lab in dD[0]) else 'na'))
            if has_base and kind=='na': continue
            dn=None if dD is None else dD[0].get(lab,[0,'na'])[0]
            cn=None if cD is None else cD[0].get(lab,[0,'na'])[0]
            tn=(dn or 0)+(cn or 0)
            bd,bc,bt = (app_d,app_c,app_t) if has_base else (N_D,N_C,Ntot)
            # ⚠ The SLIM variant is the manuscript's Table 2 and is DESCRIPTIVE (TSA,
            # 2026-08-22): it reports how papers answered and does not mark which answer
            # counts as a problem.  That belongs to Figure 4 and to Supplementary Table S1's
            # "response counted as a problem" column; saying it in three places is three
            # places to drift.  The full and by-option variants keep the marker, because
            # their Flagged column is DEFINED in terms of it.
            dot='<span class="pf"></span>' if (kind=='prob' and not DROPTF) else ''
            dcell='<span class="ndash">—</span>' if dD is None else pct(dn,bd)
            ccell='<span class="ndash">—</span>' if cD is None else pct(cn,bc)
            if DROPTF:
                rows.append('<tr class="cat %s"><th scope="row" style="padding-left:%dpx">%s%s</th><td>%s</td><td>%s</td></tr>'
                            %(kind,padc,dot,H.escape(lab),dcell,ccell))
            else:
                rows.append('<tr class="cat %s"><th scope="row" style="padding-left:%dpx">%s%s</th><td class="tc">%s</td><td>%s</td><td>%s</td><td class="flagcell"></td></tr>'
                            %(kind,padc,dot,H.escape(lab),pct(tn,bt),dcell,ccell))
  return ''.join(rows)

PAGE=r'''<title>Item response distribution by domain and study task__TITLESUF__</title>
<style>
:root{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;
--prob:#a6432a;--serif:"Iowan Old Style","Palatino Linotype","Book Antiqua",Palatino,Georgia,serif;
--sans:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;}
@media (prefers-color-scheme:dark){:root{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}}
:root[data-theme="light"]{--paper:#fbfaf7;--panel:#fff;--ink:#1b2029;--muted:#616b78;--faint:#8b95a1;--accent:#16697a;
--accent-soft:#e4eef0;--accent-line:#bcd6db;--hair:#e6e3dc;--hair-strong:#d4d0c6;--row:#f6f4ef;--totbg:#eef5f6;--prob:#a6432a;}
:root[data-theme="dark"]{--paper:#12151a;--panel:#171b21;--ink:#e9edf1;--muted:#9aa4b1;--faint:#727c89;
--accent:#5bb5c6;--accent-soft:#17303a;--accent-line:#2b4a54;--hair:#272c34;--hair-strong:#333944;--row:#1c2027;--totbg:#152a30;--prob:#e39b81;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.5;-webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,60px) 20px}
.wrap{max-width:1060px;margin:0 auto}
.tabtag{display:inline-block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line);padding:3px 9px;border-radius:5px;margin:0 0 12px}
.eyebrow{font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:600;margin:0 0 10px}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(24px,3.6vw,33px);line-height:1.14;letter-spacing:-.01em;margin:0 0 14px;text-wrap:balance;max-width:24ch}
.lede{color:var(--muted);font-size:15px;max-width:72ch;margin:0 0 20px}
.lede b{color:var(--ink);font-weight:600}
.key{display:flex;flex-wrap:wrap;gap:9px 18px;align-items:center;font-size:12.5px;color:var(--muted);margin:0 0 22px}
.tscroll{overflow-x:auto;border:1px solid var(--hair);border-radius:11px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:760px}
thead th{position:sticky;top:0;background:var(--panel);text-align:right;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--faint);font-weight:600;padding:12px 16px 9px;border-bottom:2px solid var(--ink)}
thead th.h0{text-align:left}
thead th.htot{background:var(--totbg);color:var(--accent)}
thead th span{display:block;font-size:10px;color:var(--faint);font-weight:500;margin-top:1px}
tr.dom td{padding:16px 16px 5px;border-bottom:1px solid var(--hair-strong)}
.dl{display:flex;align-items:center;gap:9px;font-weight:700;font-size:12px;letter-spacing:.09em;text-transform:uppercase;color:var(--accent)}
.dl .dt{width:7px;height:7px;border-radius:50%;background:var(--accent)}
tr.subdom td{padding:12px 16px 2px}
.sdl{display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.sdl:before{content:"";width:16px;height:1px;background:var(--hair-strong);display:inline-block}
tr.item td.inm{padding-top:12px;padding-bottom:4px;padding-right:16px;border-top:1px solid var(--hair)}
tr.item.dep td.inm{border-top:1px dotted var(--hair)}
.item .q{font-weight:600;color:var(--ink);font-size:13.5px}
.arw{color:var(--faint);font-weight:400}
.nalbl{font-size:10px;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);margin-left:4px}
td.nac{text-align:right;font-variant-numeric:tabular-nums;padding:12px 16px 4px;border-top:1px dotted var(--hair)}
td.nac.tc{background:var(--totbg)}
.nav{color:var(--muted);font-weight:600;font-size:12.5px}
.tags{display:inline-flex;gap:6px;margin-left:9px;vertical-align:middle}
.sc,.tp{font-size:10px;letter-spacing:.04em;text-transform:uppercase;font-weight:600;padding:1px 6px;border-radius:4px;white-space:nowrap}
.sc-b{color:var(--muted);background:transparent;border:1px solid var(--hair-strong)}
.sc-c{color:var(--accent);background:var(--accent-soft);border:1px solid var(--accent-line)}
.sc-d{color:var(--muted);background:transparent;border:1px dashed var(--hair-strong)}
.tp{border:1px solid var(--hair-strong);color:var(--muted)}
.tp.gate,.tp.cls{border-style:dotted;color:var(--faint)}
tr.cat th{text-align:left;font-weight:400;color:var(--muted);padding:5px 16px;white-space:normal}
tr.cat td{text-align:right;font-variant-numeric:tabular-nums;padding:5px 16px;color:var(--ink);white-space:nowrap}
tr.cat td.tc{background:var(--totbg);font-weight:600}
tr.cat.prob th{color:var(--prob);font-weight:600}
tr.cat.prob td{color:var(--prob)}
tr.cat.other th{font-style:italic}
tr.cat:hover th,tr.cat:hover td{background:var(--row)}
.pct{color:var(--faint);font-size:12px;font-weight:400}
tr.cat.prob .pct{color:var(--prob);opacity:.8}
.z{color:var(--faint)}.ndash{color:var(--faint)}
.pf{width:7px;height:7px;border-radius:2px;background:var(--prob);display:inline-block;margin-right:7px;vertical-align:middle}
th[scope="row"]{position:sticky;left:0;background:var(--panel);z-index:1}
tr.cat:hover th[scope="row"]{background:var(--row)}
.foot{margin-top:20px;color:var(--faint);font-size:12.5px;max-width:92ch;line-height:1.6}
.foot b{color:var(--muted)} .foot code{background:var(--accent-soft);color:var(--accent);padding:1px 5px;border-radius:4px}
thead th.hflag{background:var(--totbg);color:var(--accent);border-left:2px solid var(--hair-strong)}
td.flagcell{text-align:right;border-left:2px solid var(--hair);vertical-align:middle;padding:6px 15px;white-space:nowrap;background:var(--totbg)}
tr.item td.flagcell{border-top:1px solid var(--hair)}
tr.item.dep td.flagcell{border-top:1px dotted var(--hair)}
tr.dom td,tr.subdom td{border-left:none}
.fg{display:flex;flex-direction:column;gap:1px;align-items:flex-end}
.fgrow{display:flex;gap:7px;align-items:baseline;justify-content:flex-end}
.fk{font-size:9px;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);font-weight:700;min-width:9px;text-align:left}
.fp{font-variant-numeric:tabular-nums;font-weight:700;color:var(--ink);font-size:13.5px}
.fp::after{content:"%";font-size:9px;font-weight:600;color:var(--faint);margin-left:1px}
.flagcell .ns{font-size:10px;color:var(--faint);font-style:italic}
tr.cat:hover td.flagcell{background:var(--row)}
</style>
<div class="wrap">
<span class="tabtag">__TAG__</span>
<p class="eyebrow">Assessment of Healthcare Research Quality · Saudi Arabia</p>
<h1>Item response distribution by domain and study task</h1>
__LEDE__
__KEY__
<div class="tscroll"><table>
__THEAD__
<tbody>__TBODY__</tbody></table></div>
<p class="foot"><b>Reading the table.</b> Items that apply to <b>every</b> paper: rows are n (% of the column&#8217;s __NT__ / __ND__ / __NC__). <b>Items with an &#8220;applies to &#8594;&#8221; line</b> don&#8217;t apply to all papers: the item-line number is the count it <b>applies to</b>, and the response rows below are n (% <b>of that applicable base</b>). The rest were skipped by a parent question (those items are <b>indented</b>) or were not applicable &mdash; e.g. <i>Any missing outcome</i> applies to 260 because the corrupt paper noted below is blank.
<b>Confounder-selection basis &mdash; applicability rule.</b> This item asks <i>how</i> confounders were chosen, so it applies only where confounders were actually selected. It is <b>not applicable</b> when (i) <i>baseline confounding method</i> = &#8220;No adjustment&#8221; alone &mdash; nothing was adjusted, so nothing was selected (74 papers); or (ii) the study is a <b>randomization-only trial</b> &mdash; randomisation balances confounders without selecting any (26 papers, all verified to have the randomised treatment as their adjudicated exposure). The residual gap to <i>baseline confounding method</i> is precisely the randomization-only trials, which used a method but selected no confounders. Trials reporting an <b>unadjusted per-protocol or completers-only</b> effect are excluded here as well, since they too selected nothing &mdash; that error belongs to the analysis-population indicator, not to this item.
__SELFOOT__
<b>Other / uncodable</b> rows name the recorded value where an answer does not fit the item&#8217;s options. <b>PMID STUDY-0945 &mdash; whose adjudication block was shifted by one field &mdash; has now been re-adjudicated and is corrected in this dataset</b>, so the strays it previously produced across <i>baseline selection bias</i>, <i>compare responders</i>, <i>independent/dependent</i>, <i>baseline confounding method</i> and <i>confounder-selection basis</i> are gone.
__FLAGFOOT__
<b>Precondition &#8594; detail.</b> Each domain now states the precondition before the detail: <i>baseline selection bias presence</i>, <i>outcome / exposure measurement bias presence</i>, <i>baseline &amp; time-varying confounding adjustment attempted</i>, and <i>missing outcome / exposure handled</i>. The detail item beneath each one is computed <b>only among the papers that meet it</b> &mdash; the confounding <i>method</i> lists are among the papers that attempted adjustment, and the missing-data <i>handling method</i> lists are among the papers that handled it. The error is scored <b>once</b>, on the item that carries it (<i>accounted for</i> / <i>attempted</i> / <i>handled</i>); the companion <i>presence</i> and <i>method</i> items are descriptive, so nothing is double-counted. <b>Measurement bias presence is 100% by construction</b> &mdash; the tool never asks whether measurement bias exists, it goes straight to its direction and whether it was accounted for, so presence is assumed for every study. Numbers reflect the canonical analysis dataset of <b>__NALL__ included papers</b> &mdash; the <b>__NT__</b> descriptive and causal papers appraised here plus the predictive papers, which carry no epidemiological bias items &mdash; and incorporate the completed phase-II adjudication and the STUDY-0945 correction. The confounder-selection scoping rule above <b>is</b> applied; the follow/design relabels and the exposure-validity convention are <b>not</b> yet, so the <i>exposure/outcome measurement</i> flag rates remain upper bounds.</p>
</div>'''
SHARED_SEL = ('The four <b>select-all-that-apply</b> items are <i>Baseline</i> / <i>time-varying confounding method</i>, '
 '<i>Confounder-selection basis</i> and <i>Errors mentioned in the discussion</i> (IPTW = inverse-probability-of-treatment weighting; PS = propensity score). '
 'For <i>Errors mentioned</i>, delimiter and capitalisation variants were canonicalised so equivalent selections merge '
 '(one &#8220;Random error, Selection bias;Confounding bias&#8221; and one lower-case &#8220;measurement bias&#8221;), and selections are listed in taxonomy order.')

SELFOOT_COMBO = ('<b>Select-all-that-apply items &mdash; by combination.</b> '+SHARED_SEL+
 ' Every answered <b>combination</b> is listed verbatim and each paper is counted <b>once</b>, so these percentages <b>sum to 100</b>. '
 '<i>Confounder-selection basis</i> counts a combination as <b>not</b> an error when it names a DAG/subject-matter or previous-literature basis, '
 'and as flagged otherwise (statistical criteria, change of estimate, none of the above, no adjustment). '
 'A companion version of this table lists these items <b>by individual option</b> instead.')

_SEL_MARG_CORE = ('<b>Select-all-that-apply items &mdash; by individual option.</b> '+SHARED_SEL+
 ' Each row is <b>one option</b>, counted every time it was selected: a paper that ticked three options appears in all three rows, so these percentages '
 '<b>do not sum to 100</b> and the rows are not mutually exclusive. The denominator is still the applicable base, so each cell reads '
 '&#8220;<i>n</i> papers (<i>x</i>% of applicable) selected this option&#8221;. ')
_SEL_MARG_TAIL = ('A companion version of this table lists these items <b>by full combination</b> (summing to 100%) instead.')
# ⚠ The flagged sentences below name a Flagged column and a "flagged row", neither of which
# exists in the slim variant since it became descriptive (2026-08-22).  They are appended
# only where they are true.
_SEL_MARG_FLAG = ('<b>The Flagged column remains paper-level</b> and is identical to the by-combination version, so the two are directly comparable &mdash; note that a paper '
 'selecting both a DAG basis and statistical criteria contributes to the flagged <i>Statistical criteria</i> row here, yet is not a flagged <i>paper</i>, '
 'because at paper level a named DAG/subject-matter or previous-literature basis takes precedence. ')
SELFOOT_MARG      = _SEL_MARG_CORE + _SEL_MARG_FLAG + _SEL_MARG_TAIL
SELFOOT_MARG_SLIM = _SEL_MARG_CORE + _SEL_MARG_TAIL

FLAGFOOT=('<b>Flagged column.</b> Flagged &#247; applicable, where <i>flagged</i> counts the '
 '<span class="pf"></span>-marked response(s) and the <i>applicable base</i> excludes not-applicable '
 'and skipped answers (and, for the validity items, &#8220;validation not needed&#8221;). '
 'It is computed on the same applicable base as the response rows, so the two reconcile. '
 'Classifiers and gates are <i>not scored</i>.')

VARIANTS=[(False,'outputs/tables/07_22_2026_table2_item_distribution.html','Table 2','',
   'For the four <b>select-all-that-apply</b> items every answered <b>combination</b> is listed, each paper counted once, so those columns sum to 100%.',SELFOOT_COMBO),
 (True,'outputs/tables/07_22_2026_table2_item_distribution_by_option.html','Table 2 · by option',' — by option',
   '<b>This is the per-option variant:</b> for the four <b>select-all-that-apply</b> items it shows <b>how often each individual option was selected</b> &mdash; a paper ticking three options is counted in all three, so those columns <b>do not sum to 100%</b>.',SELFOOT_MARG),
 (True,'outputs/tables/07_23_2026_table2_item_distribution_by_option_slim.html','Table 2 · by option (slim)',' — by option, slim','<b>This is the slim per-option variant:</b> the four <b>select-all-that-apply</b> items show <b>how often each individual option was selected</b>, so those columns <b>do not sum to 100%</b>; method names are written out in full.',SELFOOT_MARG_SLIM)]

TH_FULL='<thead><tr><th class="h0">Domain / item / response</th><th class="htot">Total<span>n = __NT__ (100%)</span></th><th>Descriptive<span>n = __ND__ (__PD__%)</span></th><th>Causal<span>n = __NC__ (__PC__%)</span></th><th class="hflag">Flagged<span>% of applicable</span></th></tr></thead>'
TH_SLIM='<thead><tr><th class="h0">Domain / item / response</th><th>Descriptive<span>n = __ND__ (__PD__%)</span></th><th>Causal<span>n = __NC__ (__PC__%)</span></th></tr></thead>'
K_FULL='<div class="key">\n<span><span class="pf"></span> problem response</span>\n<span><span class="sc sc-c">Causal only</span> / <span class="sc sc-d">Descriptive only</span></span>\n<span><span class="tp cls">Classifier</span> not scored</span>\n<span>&#8627; dependent — % is within the applicable base</span>\n<span><b class="fk" style="color:var(--ink)">Flagged</b> = flagged &#247; applicable, by task (hover for n)</span>\n</div>'
K_SLIM='<div class="key">\n<span><span class="sc sc-c">Causal only</span> / <span class="sc sc-d">Descriptive only</span></span>\n<span>&#8627; dependent — % is within the applicable base</span>\n</div>'
L_FULL='<p class="lede">Response distribution of every tool item across seven domains, for the <b>__NT__ descriptive and causal papers</b>. The first value column pools both tasks (<b>Total</b>); the next two stratify by <b>Descriptive</b> (__PD__% of the __NT__) and <b>Causal</b> (__PC__%). Where an item doesn&#8217;t apply to every paper &mdash; a parent question skipped it, or it was not applicable &mdash; the <b>count it applies to</b> sits on the item line (&#8220;applies&nbsp;to&nbsp;&#8594;&#8221;) and its category percentages are computed <b>within that base</b>; items a parent question gates are also <b>indented (&#8627;)</b>. Items that apply to all papers are percentaged of the column total. The <span class="pf"></span>marker flags the problem response, and the right-hand <b>Flagged</b> column reads off the <b>share of applicable papers</b> carrying it &mdash; split by task (<b>D</b> descriptive, <b>C</b> causal), the number that feeds the prevalence analysis. __SELLEDE__</p>'
L_SLIM='<p class="lede">Response distribution of every tool item across seven domains, shown separately for the <b>__ND__ descriptive</b> (__PD__%) and <b>__NC__ causal</b> (__PC__%) papers of the __NT__ scored. This slim variant omits the pooled <i>Total</i> and the <i>Flagged</i> summary so each task can be read on its own. Where an item doesn&#8217;t apply to every paper &mdash; a parent question skipped it, or it was not applicable &mdash; the <b>count it applies to</b> sits on the item line (&#8220;applies&nbsp;to&nbsp;&#8594;&#8221;) and its category percentages are computed <b>within that base</b>; items a parent question gates are also <b>indented (&#8627;)</b>. Items that apply to all papers are percentaged of their task column. This table is <b>descriptive</b>: it reports how the papers answered, and does not mark which answer counts as a methodological problem &mdash; that is given in <b>Figure 4</b> and in <b>Supplementary Table S1</b>. __SELLEDE__</p>'
for marginal,fn,tag,tsuf,sellede,selfoot in VARIANTS:
    slim = fn.endswith('_slim.html')
    globals()['DROPTF']=slim; globals()['LONGNAMES']=slim
    html=(PAGE.replace('__TBODY__',build(marginal)).replace('__TAG__',tag)
              .replace('__THEAD__', TH_SLIM if slim else TH_FULL)
              .replace('__KEY__',   K_SLIM if slim else K_FULL)
              .replace('__LEDE__',  L_SLIM if slim else L_FULL)
              # the slim variant has no Flagged column and no problem marker, so the
              # footnote defining them would describe things that are not on the page
              .replace('__FLAGFOOT__', '' if slim else FLAGFOOT)
              .replace('__NALL__',str(N_ALL))
              .replace('__NT__',str(N_T)).replace('__ND__',str(N_D)).replace('__NC__',str(N_C))
              .replace('__PD__','%.1f'%PCT_D).replace('__PC__','%.1f'%PCT_C)
              .replace('__TITLESUF__',tsuf).replace('__SELLEDE__',sellede).replace('__SELFOOT__',selfoot))
    if slim:
        html=html.replace('(IPTW = inverse-probability-of-treatment weighting; PS = propensity score)',
                          '(method names are written out in full in this variant, with no abbreviations)')
    open(fn,'w',encoding='utf-8').write(html)
    print('wrote',fn)
print('OK — both versions (by combination / by option) generated')
