# NOTE (public repository): 8 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Provisional 385 inconsistency scan = 377 final dataset + the 5 new causal/descriptive batch-6
# papers using their AGREED reviewer values (disagreed/pending cells left blank). Predictive adds nothing.
import csv, importlib.util
import pandas as pd

# ---- 377 long ----
long377=list(csv.DictReader(open("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv",encoding="utf-8-sig")))

# ---- 8 new papers: build long rows from the cell detail ----
TASK={"STUDY-0401":"Predictive","STUDY-0658":"Causal","STUDY-0161":"Causal","STUDY-0275":"Predictive",
      "STUDY-0449":"Predictive","STUDY-0320":"Causal","STUDY-0927":"Causal","STUDY-0905":"Descriptive"}
cd=list(csv.DictReader(open("data/adjudication/08_08_2026_batch6_cell_detail.csv",encoding="utf-8-sig")))
newrows=[]
pending=[]  # (PMID, variable) cells that are disagreed -> will be set by tomorrow's adjudication
for c in cd:
    st=c["status"]
    if st=="Reviewers agreed":
        val=c["first_reviewer"]; src="batch6-agreed"
    elif st=="Not applicable to either reviewer":
        val=""; src="batch6-NA"
    else:                                    # disagreement -> pending joint adjudication
        val=""; src="batch6-pending"; pending.append((c["PMID"],c["variable"]))
    newrows.append({"PMID":c["PMID"],"Study_Type":c["Study_Type"],"variable":c["variable"],
                    "final":val,"source":src,"resolution_note":""})

# ---- write provisional 385 long ----
allrows=long377+newrows
with open("08_08_2026_PROVISIONAL_385_long.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f, fieldnames=["PMID","Study_Type","variable","final","source","resolution_note"])
    w.writeheader(); w.writerows(allrows)

# ---- run the existing checker on 377 and provisional-385 ----
spec=importlib.util.spec_from_file_location("chk","code/pipeline/_check_contradictions.py")
chk=importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)

def run(path,label):
    W=chk.load(path); R=chk.soft(W); g,e=chk.skiplogic(W)
    npap=sum(len(w) for w in W.values())
    return {"label":label,"papers":npap,"GAP":len(g),"EXTRA":len(e),
            "soft":{k:sorted(v) for k,v in R.items()}, "gaps":g}

a=run("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv","377")
b=run("08_08_2026_PROVISIONAL_385_long.csv","385 (provisional)")

KEYS=['S1','S8','S2','S9','S6a','S6b','S7','S22','S10C','S11C','S10D','S11D','S3','S4C','S4D',
      'S12','S13C','S13D','S15','S16','S17C','S17D','S5','S5b','S18','S19','S23','S24']
print(f"causal+descriptive papers: 377->{a['papers']}   provisional-385->{b['papers']} (+{b['papers']-a['papers']})")
print(f"HARD skip-logic GAP: 377={a['GAP']}  385prov={b['GAP']} (+{b['GAP']-a['GAP']})   EXTRA: {a['EXTRA']}/{b['EXTRA']}")
print("\nSOFT rule counts (377 -> 385prov), and which NEW papers were added:")
newpmids=set(TASK[p] for p in TASK)  # not used
b6=set(["STUDY-0658","STUDY-0161","STUDY-0320","STUDY-0927","STUDY-0905"])
for k in KEYS:
    n377=len(a['soft'][k]); n385=len(b['soft'][k])
    added=[p for p in b['soft'][k] if p in b6]
    tag = f"   <-- new: {','.join(added)}" if added else ""
    if n377 or n385: print(f"  {k:<5} {n377:>3} -> {n385:>3}{tag}")

# GAP delta detail for new papers
print("\nNew-paper GAP items (from AGREED parents; only firm ones):")
gp385=set((t,p,par,child) for (t,p,par,pv,child,cv) in b['gaps'])
gp377=set((t,p,par,child) for (t,p,par,pv,child,cv) in a['gaps'])
for row in b['gaps']:
    if row[1] in b6: print("  ",row[1],row[2],"->",row[4])

print(f"\nPENDING batch-6 cells (final set by tomorrow's joint adjudication) that could still create/clear inconsistencies: {len(pending)}")
# which pending cells are on inconsistency-DRIVING items
DRIVERS={"design","follow","sampling","sample_size","base_sel","base_conf_meth","conf_var_det","time_verying",
         "tv_conf_meth","miss_outcome","miss_exposure","ltfu_bias","outcome_type","val_outcome","val_exposure","confl_task"}
drv=[(p,v) for (p,v) in pending if v.split("_",1)[-1] in DRIVERS]
print(f"  of which on inconsistency-driving items ({len(drv)}):")
for p,v in drv: print("   ",p,v)
