# NOTE (public repository): 23 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Combine adjudicated (310 desc+causal) + machine-extracted (75 predictive) outcomes into one
# classified table for the 385, and emit category x task summaries.
import csv, glob, os, re, json, sys
from collections import defaultdict, Counter

CATLAB={
 "1.1":"Mortality & survival","1.2":"Disease occurrence / diagnosis",
 "1.3":"Severity, progression, complications & safety","1.4":"Physiological, lab & imaging measures",
 "1.5":"Treatment / procedure response & success","2.1":"Clinical, functional & symptom scales (incl. QoL)",
 "2.2":"Mental health & psychological status","2.3":"Satisfaction & care experience",
 "3.1":"Knowledge & awareness","3.2":"Attitudes, perceptions & willingness",
 "3.3":"Health behaviors, practices & adherence","4.1":"Utilization, cost, process & workforce","OTHER":"Other"}
DOMAIN={"1.1":"1","1.2":"1","1.3":"1","1.4":"1","1.5":"1","2.1":"2","2.2":"2","2.3":"2",
 "3.1":"3","3.2":"3","3.3":"3","4.1":"4","OTHER":"9"}
DOMLAB={"1":"Clinical / biomedical","2":"Patient-reported & functional","3":"Knowledge, attitudes & behaviors","4":"Health-system & process","9":"Other"}
CATORDER=["1.1","1.2","1.3","1.4","1.5","2.1","2.2","2.3","3.1","3.2","3.3","4.1","OTHER"]

def norm_cat(c):
    c=(c or "").strip()
    c=c.replace(" ","")
    return c if c in CATLAB else ("OTHER" if c.upper().startswith("OTHER") else c)

# Predictive overrides after review/cross-check (keyed by PMID):
#  - 1 UNDETERMINED algorithm paper -> concrete non-clinical "Other" label (still machine-sourced)
#
# 2026-08-26 (TSA ruling): the two "prior TSA/YA outcome" overrides for STUDY-0504 and STUDY-0401
# were REMOVED. The instrument has no outcome field for predictive studies -- every outcome cell
# for both papers reads "Not applicable to either reviewer" -- so no reviewer outcome ever
# existed, and the two hardcoded strings had no source in the record. Both papers now take the
# machine determination like every other predictive study, so the predictive arm is uniform:
# 310 adjudicated (descriptive + causal) and 75 machine (SEIG, unverified).
# Re-read against the PDFs on 2026-08-26 confirmed the machine values on the merits:
#   STUDY-0504 - Methods define PH as mean PAP >=25 mmHg and it is the ROC target; both reviewers
#              agreed the predictive design is Diagnostic, so the target is the condition (1.2),
#              not the continuous pressure the removed override named (1.4).
#   STUDY-0401 - Methods state the model predicts THE CLINICIAN RANKING; "very low glucose", the
#              string the removed override named, is one of the seven AGP predictors, not the DV.
PRED_OVERRIDE={
 "STUDY-0659":{"outcome":"COVID-19 chest X-ray image segmentation quality (PSNR/SSIM/FSIM)","category":"OTHER",
             "source":"machine (SEIG, unverified)","confidence":"Low","note":"Methods|single|optimization/segmentation algorithm paper; image-quality metrics, no health dependent variable"},
}

# ---------------------------------------------------------------------------------------
# CATEGORY RULINGS, 2026-08-26. TSA delegated these ("do your best guess here") after the S4
# sweep found near-identical constructs in different categories. They change no outcome TEXT
# and no paper's task -- only which of the 13 categories an outcome sits in. Each is grounded
# in the codebook, not in a new scheme, and each is REVERSIBLE: drop a principle from
# ACTIVE_PRINCIPLES and re-run to restore the pre-ruling categories for that group.
#
#  P1  Workforce attributes of health professionals -> 4.1, whether self-rated or measured.
#      The codebook lists "workforce attributes (competence, workload)" under 4.1 and anchors
#      it with "Nurses' competence"; 4.1 therefore beats 2.1 (scales) and 3.2 (perceptions).
#  P2  A study whose reported RESULT is an instrument's psychometric properties has no health
#      dependent variable -> OTHER. Applies only where reliability/validity/agreement IS the
#      result; a paper that also answers a substantive health question keeps its category
#      (STUDY-0032 validates OCI-12 *and* tests orthorexia/OCD overlap, so it stays 2.2).
#  P3  A method paper whose reported results are image-quality metrics (PSNR/SSIM/FSIM/MAE)
#      has no health dependent variable -> OTHER. Verified against each paper's Results.
#  P4  General academic attainment is not a health outcome -> OTHER. Clinical/professional
#      competence of trainee health professionals stays 4.1 (STUDY-0445 is unchanged).
#  P5  An objectively measured physiological quantity -> 1.4 even when an earlier rule fires
#      on a word in its name ("functional" -> 2.1, "loss" -> 1.3).
#  P6  Receipt or population uptake of a procedure is utilisation -> 4.1, not 1.5.
#
# CONSIDERED AND DELIBERATELY LEFT: STUDY-0840 "Disability-adjusted life years (DALYs)" in 2.1.
# DALYs is a composite of mortality and disability and belongs cleanly to no category here;
# moving it without a principled destination would be a coin flip, so it stays and is recorded.
ACTIVE_PRINCIPLES={"P1","P2","P3","P4","P5","P6"}
CAT_RULINGS={
 # P1 -- workforce attributes of health professionals
 "STUDY-0144":("4.1","P1","nurses' emergency preparedness: workforce attribute, was 2.1"),
 "STUDY-0843":("4.1","P1","nurses' perceived disaster preparedness: workforce attribute, was 3.2"),
 "STUDY-0337":("4.1","P1","nurse interns' critical thinking disposition: workforce attribute, was 2.1"),
 "STUDY-0130":("4.1","P1","nurses' caring score: workforce attribute, was 2.1"),
 # P2 -- the result is the instrument's psychometrics
 "STUDY-0883":("OTHER","P2","SRS-30 reliability/validity; Results are Cronbach alpha, was 2.1"),
 "STUDY-0835":("OTHER","P2","OHIP version scoring recommendations; Results are inter-version r, was 2.1"),
 "STUDY-0892":("OTHER","P2","SOC-13 CFA; Results are reliability and factor structure, was 2.2"),
 "STUDY-0712":("OTHER","P2","Arabic IPQ-R validity; Results are internal consistency, was 3.2"),
 "STUDY-0847":("OTHER","P2","Ar-GHQ-12 psychometric analysis; Results are factor solution, was 2.2"),
 "STUDY-0297":("OTHER","P2","telepractice stuttering assessment; aim is validity/reliability of the mode, was 2.1"),
 # P3 -- image-quality metrics only
 "STUDY-0563":("OTHER","P3","brain-MR synthesis; Results are MSE/MAE/PSNR/SSIM only, was 1.4"),
 "STUDY-0856":("OTHER","P3","MS-lesion contrast enhancement; Results are entropy/EME/AMBE/PSNR/SSIM/FSIM only, was 1.2"),
 # P4 -- general academic attainment
 "STUDY-0656":("OTHER","P4","academic achievement (GPA), not a health outcome, was 2.1"),
 # P5 -- measured physiological quantity
 "STUDY-0700":("1.4","P5","pulmonary function test (FVC) is spirometry; 'functional' had routed it to 2.1"),
 "STUDY-0597":("1.4","P5","systemic bone loss measured by BMD; 'loss' had routed it to 1.3 (STUDY-0477 BMD is 1.4)"),
 # P6 -- procedure utilisation
 "STUDY-0393":("4.1","P6","global HCT activity: transplant rates per 10 million population, was 1.5"),
}

rows=[]  # PMID, Study_Type, outcome, category, source, confidence, extra
# --- adjudicated desc+causal ---
for r in csv.DictReader(open("data/outcomes/08_08_2026_outcomes_classified.csv",encoding="utf-8-sig")):
    rows.append({"PMID":r["PMID"].strip(),"Study_Type":r["Study_Type"],"outcome":r["adjudicated_outcome"],
                 "category":norm_cat(r["cat"]),"source":"adjudicated (TSA/YA)","confidence":"","note":r.get("source_file","")})
adj_pmids={x["PMID"] for x in rows}

# --- machine predictive from batch tsvs ---
# 2026-08-26: this glob was still the flat-root "pred_outcomes_batch*.tsv" left over from before
# the 2026-08-17 reorg. Run from the repo root it matched NOTHING, and the script went on to
# write a 310-row table with Predictive: 0 over the shipped data and exit 0. Path fixed here;
# the coverage check below is now fatal so a repeat cannot reach the writes.
PRED_GLOB="data/outcomes/pred_outcomes_batch*.tsv"
pred_files=sorted(glob.glob(PRED_GLOB))
if not pred_files:
    sys.exit("FATAL: no predictive batch files matched %s -- refusing to write a partial table"%PRED_GLOB)
pred_seen=set()
raw_undetermined=[]
for f in pred_files:
    with open(f,encoding="utf-8-sig") as fh:
        lines=[ln.rstrip("\n") for ln in fh if ln.strip()]
    if not lines: continue
    start=1 if lines[0].lower().startswith("pmid") else 0
    for ln in lines[start:]:
        parts=ln.split("\t")
        if len(parts)<5:
            print("WARN malformed row in",f,":",ln[:80]); continue
        pmid=parts[0].strip()
        outcome=parts[1].strip()
        source_section=parts[2].strip() if len(parts)>2 else ""
        timepoint=parts[3].strip() if len(parts)>3 else ""
        category=norm_cat(parts[4]) if len(parts)>4 else "OTHER"
        confidence=parts[5].strip() if len(parts)>5 else ""
        rationale=parts[6].strip() if len(parts)>6 else ""
        if pmid in pred_seen:
            print("DUP predictive pmid",pmid,"in",f); continue
        pred_seen.add(pmid)
        if outcome.strip().upper()=="UNDETERMINED": raw_undetermined.append(pmid)
        rec={"PMID":pmid,"Study_Type":"Predictive","outcome":outcome,"category":category,
             "source":"machine (SEIG, unverified)","confidence":confidence,
             "note":"%s|%s|%s"%(source_section,timepoint,rationale)}
        if pmid in PRED_OVERRIDE:
            ov=PRED_OVERRIDE[pmid]; rec.update({k:ov[k] for k in ov}); rec["category"]=norm_cat(rec["category"])
        rows.append(rec)

# --- apply the 2026-08-26 category rulings ---
_by_pmid={r["PMID"]:r for r in rows}
applied=[]
for pmid,(newcat,prin,why) in CAT_RULINGS.items():
    if prin not in ACTIVE_PRINCIPLES: continue
    r=_by_pmid.get(pmid)
    if r is None:
        sys.exit("FATAL: ruling for %s but that PMID is not in the table"%pmid)
    old=r["category"]
    if old==newcat:
        sys.exit("FATAL: ruling for %s is a no-op (already %s) -- stale ruling table"%(pmid,newcat))
    r["category"]=newcat
    r["note"]=("%s | ruling %s 2026-08-26: %s -> %s; %s"%(r["note"],prin,old,newcat,why)).strip(" |")
    applied.append((pmid,old,newcat,prin))
print("category rulings applied:",len(applied),"of",len(CAT_RULINGS),
      "| principles active:",sorted(ACTIVE_PRINCIPLES))
for pmid,old,new,prin in sorted(applied,key=lambda x:(x[3],x[0])):
    print("   %s  %-5s -> %-5s  %s"%(pmid,old,new,prin))

# --- validate against the 385 ---
land={str(r["PMID"]).strip():r["Study_Type"] for r in csv.DictReader(open("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv",encoding="utf-8-sig"))}
allpmids={x["PMID"] for x in rows}
missing=[p for p in land if p not in allpmids]
extra=[p for p in allpmids if p not in land]
badcat=[x for x in rows if x["category"] not in CATLAB]
print("total rows:",len(rows),"| unique PMIDs:",len(allpmids),"| of 385")
print("MISSING from 385 coverage:",len(missing), missing[:20])
print("EXTRA (not in 385):",len(extra), extra[:20])
print("bad category codes:",len(badcat), [(x['PMID'],x['category']) for x in badcat][:10])
# Report UNDETERMINED on the RAW machine rows, before PRED_OVERRIDE. Checking the post-override
# rows made this guard unfireable for exactly the PMIDs it exists to catch (STUDY-0659's batch-3
# outcome literally IS "UNDETERMINED"), so it printed a false all-clear.
print("UNDETERMINED predictive (raw, pre-override):",len(raw_undetermined), raw_undetermined,
      "-> resolved by PRED_OVERRIDE:",[p for p in raw_undetermined if p in PRED_OVERRIDE])
still=[x["PMID"] for x in rows if x["outcome"].strip().upper()=="UNDETERMINED"]
print("UNDETERMINED still unresolved:",len(still), still)

# --- refuse to write a partial or malformed table ---
if missing or extra or badcat or still:
    sys.exit("FATAL: coverage/validation failed (missing=%d extra=%d bad_category=%d undetermined=%d)"
             " -- refusing to overwrite the shipped outcomes table"%(len(missing),len(extra),len(badcat),len(still)))

# --- write combined ---
with open("data/outcomes/08_08_2026_all_outcomes_classified.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["PMID","Study_Type","outcome","category","cat_label","domain","domain_label","source","confidence","note"])
    for x in sorted(rows,key=lambda r:(r["Study_Type"],CATORDER.index(r["category"]) if r["category"] in CATORDER else 99)):
        d=DOMAIN[x["category"]]
        w.writerow([x["PMID"],x["Study_Type"],x["outcome"],x["category"],CATLAB[x["category"]],d,DOMLAB[d],x["source"],x["confidence"],x["note"]])
print("wrote data/outcomes/08_08_2026_all_outcomes_classified.csv")

# --- summaries: category x task and domain x task ---
tasks=["Descriptive","Causal","Predictive"]
catcount={c:{t:0 for t in tasks} for c in CATORDER}
for x in rows: catcount[x["category"]][x["Study_Type"]]+=1
domcount=defaultdict(lambda:{t:0 for t in tasks})
for c in CATORDER:
    for t in tasks: domcount[DOMAIN[c]][t]+=catcount[c][t]
summary={"tasks":tasks,"task_totals":{t:sum(catcount[c][t] for c in CATORDER) for t in tasks},
         "cat":{c:{"label":CATLAB[c],"domain":DOMAIN[c],"counts":catcount[c],"total":sum(catcount[c].values())} for c in CATORDER},
         "dom":{d:{"label":DOMLAB[d],"counts":dict(domcount[d]),"total":sum(domcount[d].values())} for d in ["1","2","3","4","9"]}}
json.dump(summary,open("data/outcomes/08_08_2026_outcomes_summary.json","w",encoding="utf-8"),indent=1,ensure_ascii=False)
print("wrote data/outcomes/08_08_2026_outcomes_summary.json")
print("\ntask totals:",summary["task_totals"])
print("\ncategory x task:")
for c in CATORDER:
    cc=catcount[c]; tot=sum(cc.values())
    if tot: print("  %-6s D%-3d C%-3d P%-3d  tot%-4d  %s"%(c,cc["Descriptive"],cc["Causal"],cc["Predictive"],tot,CATLAB[c]))
