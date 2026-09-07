# NOTE (public repository): 5 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Build the FINAL 385 long dataset (377 + 8 batch-6 papers with their joint adjudications) and
# re-run the inconsistency checker. Reports the delta vs 377 and flags unresolved / combined cells.
import csv, importlib.util
import warnings; warnings.simplefilter("ignore")
from openpyxl import load_workbook

# ---- 377 long ----
long377=list(csv.DictReader(open("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv",encoding="utf-8-sig")))

# ---- adjudicated finals for the 39 disagreement cells ----
wb=load_workbook("private/reviewers/adjudication-worklists/08_08_2026_adjudication_master.xlsx"); ws=wb.active
H=[c.value for c in ws[1]]; ci={h:i for i,h in enumerate(H)}
fin={}
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[ci['phase']]=="Batch 6 - joint (pending)":
        fin[(str(r[ci['PMID']]),r[ci['variable']])]=("" if r[ci['Final_adjudicated']] is None else str(r[ci['Final_adjudicated']]).strip())
wb.close()

# ---- classify each new-paper cell (agreed / NA / disagreed) from the detail ----
cd=list(csv.DictReader(open("data/adjudication/08_08_2026_batch6_cell_detail.csv",encoding="utf-8-sig")))
newrows=[]; unresolved=[]; combined=[]
extra_children={}   # (PMID, child_var) -> value, from splitting "Yes; no handling"
for c in cd:
    pmid,var,st=c["PMID"],c["variable"],c["status"]
    if st=="Reviewers agreed":
        val=c["first_reviewer"]; src="batch6-agreed"
    elif st=="Not applicable to either reviewer":
        val=""; src="batch6-NA"
    else:
        val=fin.get((pmid,var),""); src="batch6-adjudicated"
        if val=="": unresolved.append((pmid,var))
        # split combined "Yes; no handling"/"Yes; not accounted" into parent=Yes + handling=No
        low=val.lower()
        if low.startswith("yes") and ("no handling" in low or "not accounted" in low or "; no" in low):
            combined.append((pmid,var,val))
            val="Yes"
            child = var.replace("miss_exposure","hand_miss_exposure").replace("miss_outcome","hand_miss_outcom")
            if child!=var: extra_children[(pmid,child)]="No"
    newrows.append({"PMID":pmid,"Study_Type":c["Study_Type"],"variable":var,"final":val,"source":src,"resolution_note":""})
# apply the split children (overwrite the corresponding new row if present)
for i,r in enumerate(newrows):
    k=(r["PMID"],r["variable"])
    if k in extra_children:
        newrows[i]["final"]=extra_children[k]; newrows[i]["source"]="batch6-split"
        del extra_children[k]
for (pmid,child),v in extra_children.items():   # child row not present (was collapsed) -> add
    st=[r for r in cd if r["PMID"]==pmid][0]["Study_Type"]
    newrows.append({"PMID":pmid,"Study_Type":st,"variable":child,"final":v,"source":"batch6-split","resolution_note":""})

allrows=long377+newrows
with open("data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f, fieldnames=["PMID","Study_Type","variable","final","source","resolution_note"])
    w.writeheader(); w.writerows(allrows)
print("wrote data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv  (rows:",len(allrows),")")
print("  unique PMIDs:",len(set(r["PMID"] for r in allrows)))
if unresolved: print("  ⚠ UNRESOLVED finals (left blank):", unresolved)
if combined: print("  ⚠ combined 'Yes; no handling' split:", [(p,v) for p,v,_ in combined])

# ---- run checker on 377 and 385 ----
spec=importlib.util.spec_from_file_location("chk","code/pipeline/_check_contradictions.py")
chk=importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
def run(path):
    W=chk.load(path); R=chk.soft(W); g,e=chk.skiplogic(W)
    return W,R,g,e
W7,R7,g7,e7=run("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv")
W8,R8,g8,e8=run("data/analysis/08_08_2026_ANALYSIS_DATASET_long_385.csv")
b6=set(["STUDY-0658","STUDY-0161","STUDY-0320","STUDY-0927","STUDY-0905"])
KEYS=['S1','S8','S2','S9','S6a','S6b','S7','S22','S10C','S11C','S10D','S11D','S3','S4C','S4D',
      'S12','S13C','S13D','S15','S16','S17C','S17D','S5','S5b','S18','S19','S23','S24']
print("\n=== FINAL 385 inconsistency inventory (377 -> 385) ===")
print(f"HARD skip-logic GAP: {len(g7)} -> {len(g8)}   EXTRA: {len(e7)} -> {len(e8)}")
gnew=[row for row in g8 if row[1] in b6]
if gnew:
    print("  new-paper GAP items:")
    for row in gnew: print("     ",row[1],row[2],"=",row[3],"->",row[4])
print("SOFT rules that changed or involve a new paper:")
for k in KEYS:
    s7=set(R7.get(k,[])); s8=set(R8.get(k,[]))
    added=sorted(s8-s7); removed=sorted(s7-s8); newp=[p for p in s8 if p in b6]
    if added or removed or newp:
        print(f"  {k:<5} {len(s7)}->{len(s8)}"
              + (f"  +{added}" if added else "") + (f"  -{removed}" if removed else ""))
print("\n(no line = unchanged from 377)")
