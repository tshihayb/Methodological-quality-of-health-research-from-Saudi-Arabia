# NOTE (public repository): 8 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Batch-6 two-reviewer agreement + needs-adjudication for the 8 papers that complete the 377 -> 385.
# Replicates the code/sas/05_19_2025_analysis.sas logic: stack the two valid reviews per paper (lower reviewer
# ID = first_reviewer), compare the 47 tool items; needs_adjudication = first_reviewer != second_reviewer
# (normalised per 07_24 R norm1). Recusals excluded, multi-submissions deduped (task-match then earliest).
import csv, glob, re, os, warnings, json
warnings.simplefilter("ignore")
from openpyxl import load_workbook, Workbook

# ---- canonical column order (verified against the Google-Forms header) ----
CANON=["Timestamp","PMID","recusal","task",
 "descriptive_design","descriptive_pop","descriptive_sampling","descriptive_sample_size","descriptive_acc_sampl",
 "descriptive_sample_ach","descriptive_base_sel","descriptive_outcome_type","descriptive_val_outcome",
 "descriptive_out_bias_acc","descriptive_miss_outcome","descriptive_hand_miss_outcom","descriptive_err_disc","descriptive_confl_task",
 "predictive_design","predictive_pop",
 "causal_design","causal_pop","causal_sampling","causal_sample_size","causal_acc_sampl","causal_sample_ach","causal_base_sel",
 "causal_comp_dis","causal_follow","causal_ltfu_bias","causal_ltfu_acc",
 "causal_exposure_type","causal_val_exposure","causal_diff_or_nondiff_exp","causal_exp_bias_acc",
 "causal_outcome_type","causal_val_outcome","causal_diff_or_nondiff_out","causal_out_bias_acc","causal_dep_or_indep_misc",
 "causal_base_conf_meth","causal_time_verying","causal_tv_conf_meth","causal_conf_var_det",
 "causal_miss_exposure","causal_hand_miss_exposure","causal_miss_outcome","causal_hand_miss_outcom","causal_err_disc",
 "comments","comments_focus"]
assert len(CANON)==51
ITEMS=CANON[2:49]                 # the 47 tool items (recusal..causal_err_disc)
assert len(ITEMS)==47

# ---- normalisation (byte-for-byte the 07_24 R norm1) ----
def norm1(v):
    s="" if v is None else str(v)
    s=re.sub(r"\s+"," ",s.strip().lower())
    if s=="nan": s=""
    if ";" in s:
        p=[x.strip() for x in s.split(";")]; p=[x for x in p if x]
        s=";".join(sorted(p))          # python default sort == radix/byte order
    return s

# ---- the 8 papers: (PMID, task) and the two reviewers (any order) ----
PAPERS={
 "STUDY-0401":("Predictive",[2,13]), "STUDY-0658":("Causal",[7,9]), "STUDY-0161":("Causal",[7,10]),
 "STUDY-0275":("Predictive",[5,8]),  "STUDY-0449":("Predictive",[7,13]),
 "STUDY-0320":("Causal",[4,8]),      "STUDY-0927":("Causal",[8,12]), "STUDY-0905":("Descriptive",[6,7]),
}

# ---- latest file per reviewer we need ----
def rev_file(rid):
    c=f"08_08_2026_Reviewer_{rid}.csv"
    if os.path.exists(c): return ("csv",c)
    for pat in (f"04_15_2026_Reviewer_{rid}.xlsx", f"05_19_2025_Reviewer_{rid}.xlsx"):
        if os.path.exists(pat): return ("xlsx",pat)
    raise FileNotFoundError(rid)

def load_rows(rid):
    kind,f=rev_file(rid)
    if kind=="csv":
        rows=list(csv.reader(open(f,encoding="utf-8-sig")))[1:]
    else:
        wb=load_workbook(f, read_only=True, data_only=True); ws=wb.worksheets[0]
        rows=[["" if c is None else str(c) for c in r] for r in ws.iter_rows(values_only=True)][1:]
        wb.close()
    out=[]
    for r in rows:
        r=list(r)+[""]*(51-len(r))
        out.append(dict(zip(CANON,r[:51])))
    return out, os.path.basename(f)

def pick_review(rid, pmid, ptask):
    rows,fname=load_rows(rid)
    cand=[r for r in rows if str(r["PMID"]).strip().replace(".0","")==pmid
          and not str(r["recusal"]).startswith("Yes")]
    if not cand: return None,fname,0
    if len(cand)>1:                       # dedup: prefer task match, then earliest timestamp
        m=[r for r in cand if r["task"]==ptask]
        cand = m if m else cand
        cand = sorted(cand, key=lambda r:str(r["Timestamp"]))[:1]
    return cand[0],fname,len(cand)

# ---- paper metadata (Title / exposure / outcome) from private/reviewers/batch-6-distribution/Batch 6.xlsx ----
meta={}
wb=load_workbook("private/reviewers/batch-6-distribution/Batch 6.xlsx", read_only=True, data_only=True); ws=wb.worksheets[0]
it=ws.iter_rows(values_only=True); h=[str(x) if x is not None else "" for x in next(it)]
hl=[x.lower() for x in h]
def gi(name):
    for i,x in enumerate(hl):
        if x==name: return i
    return None
ip,it_,ie,io,ist=gi("pmid"),gi("title"),gi("adjudicated_exposure"),gi("adjudicated_outcome"),gi("study_type")
for r in it:
    if ip is None or r[ip] is None: continue
    p=str(r[ip]).strip().replace(".0","")
    meta[p]={"Title":(r[it_] if it_ is not None else "") or "",
             "adjudicated_exposure":(r[ie] if ie is not None else "") or "",
             "adjudicated_outcome":(r[io] if io is not None else "") or "",
             "Study_Type_b6":(r[ist] if ist is not None else "") or ""}
wb.close()

# ---- build the cell-level comparison ----
cells=[]; picklog=[]
for pmid,(ptask,revs) in PAPERS.items():
    lo,hi=sorted(revs)
    r_lo,f_lo,n_lo=pick_review(lo,pmid,ptask)
    r_hi,f_hi,n_hi=pick_review(hi,pmid,ptask)
    picklog.append((pmid,ptask,lo,f_lo,n_lo,hi,f_hi,n_hi,
                    r_lo["Timestamp"] if r_lo else "MISSING", r_hi["Timestamp"] if r_hi else "MISSING"))
    assert r_lo and r_hi, f"missing review {pmid}"
    for v in ITEMS:
        a=r_lo[v]; b=r_hi[v]; na=norm1(a); nb=norm1(b)
        if na=="" and nb=="": status="Not applicable to either reviewer"
        elif na!="" and nb!="" and na==nb: status="Reviewers agreed"
        elif na!="" and nb!="": status="Disagreed on the answer"
        else: status="Disagreed on applicability"
        cells.append({"PMID":pmid,"Study_Type":ptask,"variable":v,
                      "first_reviewer":("" if a is None else str(a)),
                      "second_reviewer":("" if b is None else str(b)),
                      "first_rid":lo,"second_rid":hi,"status":status,
                      "assessed":status!="Not applicable to either reviewer",
                      "needs_adj":status in ("Disagreed on the answer","Disagreed on applicability")})

# ---- per-paper + overall summary ----
print("=== review selection (dedup/recusal handling) ===")
for pmid,ptask,lo,fl,nl,hi,fh,nh,tl,th in picklog:
    print(f"  {pmid} [{ptask:<11}] first=Rev{lo}({os.path.splitext(fl)[0][-2:] if False else fl.split('_')[0]}) second=Rev{hi}  | picked ts {tl} / {th}")
print("\n=== per-paper cell breakdown (47 items) ===")
print(f"{'PMID':<10}{'task':<12}{'assessed':>9}{'agreed':>8}{'dis_ans':>8}{'dis_appl':>9}{'needs_adj':>10}")
tot={"assessed":0,"agreed":0,"dis_ans":0,"dis_appl":0,"needs":0}
for pmid,(ptask,_) in PAPERS.items():
    cc=[c for c in cells if c["PMID"]==pmid]
    a=sum(c["assessed"] for c in cc); ag=sum(c["status"]=="Reviewers agreed" for c in cc)
    da=sum(c["status"]=="Disagreed on the answer" for c in cc); dp=sum(c["status"]=="Disagreed on applicability" for c in cc)
    nd=da+dp
    tot["assessed"]+=a; tot["agreed"]+=ag; tot["dis_ans"]+=da; tot["dis_appl"]+=dp; tot["needs"]+=nd
    print(f"{pmid:<10}{ptask:<12}{a:>9}{ag:>8}{da:>8}{dp:>9}{nd:>10}")
print(f"{'TOTAL(8)':<10}{'':<12}{tot['assessed']:>9}{tot['agreed']:>8}{tot['dis_ans']:>8}{tot['dis_appl']:>9}{tot['needs']:>10}")
print(f"\n8 papers: {len(cells)} cells = {8*47}; assessed {tot['assessed']}; agreement {100*tot['agreed']/tot['assessed']:.1f}% of assessed; needs adjudication {tot['needs']}")

# ---- existing 377 numbers from the worklists (47 items only) ----
def load_wl(f):
    wb=load_workbook(f, read_only=True, data_only=True); ws=wb.worksheets[0]
    it=ws.iter_rows(values_only=True); hh=[str(x) for x in next(it)]
    vi=hh.index("variable"); pi=hh.index("PMID"); fi=hh.index("first_reviewer"); si=hh.index("second_reviewer")
    rows=[]
    for r in it:
        if r[vi] in ITEMS:
            fr="" if r[fi] is None else norm1(r[fi]); sr="" if r[si] is None else norm1(r[si])
            rows.append((str(r[pi]).strip().replace(".0",""), r[vi], fr, sr))
    wb.close(); return rows
L=list(csv.DictReader(open("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv",encoding="utf-8-sig")))
p377=set(x["PMID"] for x in L)
# do_not_Need = first==second (INCLUDES both-blank = N/A-to-either); split it
dna377=[x for x in load_wl("private/reviewers/adjudication-worklists/04_17_2026_do_not_Need_adj.xlsx") if x[0] in p377]
needs377=[x for x in load_wl("private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_TA.xlsx") if x[0] in p377]
agreed377 = sum(1 for x in dna377 if x[2]!="")          # both answered, same -> genuine agreement
naboth377 = sum(1 for x in dna377 if x[2]=="")          # both blank -> not applicable to either
ass377 = agreed377 + len(needs377)
grid377 = 377*47
def blk(name,papers,grid,ass,agr,need,naboth):
    print(f"  {name}: papers {papers} | grid {grid} | N/A-to-either {naboth} | assessed {ass} "
          f"| agreed {agr} ({100*agr/ass:.1f}%) | NEEDS ADJUDICATION {need} | don't-need {grid-need}")
print(f"\n=== needs / doesn't-need, 47 items ===")
blk("Existing 377", 377, grid377, ass377, agreed377, len(needs377), naboth377)
blk("Batch-6 8   ", 8, 8*47, tot['assessed'], tot['agreed'], tot['needs'], 8*47-tot['assessed'])
blk("COMBINED 385", 385, grid377+8*47, ass377+tot['assessed'], agreed377+tot['agreed'],
    len(needs377)+tot['needs'], naboth377+(8*47-tot['assessed']))

# ---- write outputs ----
# 1. cell-level detail
with open("data/adjudication/08_08_2026_batch6_cell_detail.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f, fieldnames=["PMID","Study_Type","variable","first_rid","second_rid","first_reviewer","second_reviewer","status","assessed","needs_adj"])
    w.writeheader()
    for c in cells: w.writerow(c)

BASE=["PMID","Title","Study_Type","adjudicated_exposure","adjudicated_outcome","variable","first_reviewer","second_reviewer","complete"]
def write_xlsx(fn, rows, extra_cols=()):
    wb=Workbook(); ws=wb.active; ws.append(list(BASE)+list(extra_cols))
    for c in rows:
        m=meta.get(c["PMID"],{})
        ws.append([c["PMID"],m.get("Title",""),c["Study_Type"],m.get("adjudicated_exposure",""),
                   m.get("adjudicated_outcome",""),c["variable"],c["first_reviewer"],c["second_reviewer"],1]
                  +[""]*len(extra_cols))
    wb.save(fn); return sum(1 for _ in rows)

needs_rows=[c for c in cells if c["needs_adj"]]
# do_not_Need matches the SAS (first==second): genuine agreements + N/A-to-either (both blank)
dna_rows=[c for c in cells if not c["needs_adj"]]
n1=write_xlsx("private/reviewers/adjudication-worklists/08_08_2026_batch6_Needs_adj.xlsx", needs_rows,
              extra_cols=["Adjduciation_TA","Comments_TA","Adjudciation_done_TA","Adjudciation_type"])
n2=write_xlsx("private/reviewers/adjudication-worklists/08_08_2026_batch6_do_not_Need_adj.xlsx", dna_rows)
print(f"\nwrote data/adjudication/08_08_2026_batch6_cell_detail.csv ({len(cells)} cells)")
print(f"wrote private/reviewers/adjudication-worklists/08_08_2026_batch6_Needs_adj.xlsx ({n1} disagreement rows, phase-I ready)")
print(f"wrote private/reviewers/adjudication-worklists/08_08_2026_batch6_do_not_Need_adj.xlsx ({n2} agreement rows)")
