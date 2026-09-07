# NOTE (public repository): 1 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Consolidated adjudication master worklist.
#   * PRESERVES, for the 377 papers, each disagreement cell's TA call, YA call, and FINAL
#     adjudicated value (phase I concordant OR phase II) -- nothing overwritten.
#   * APPENDS the 8 batch-6 papers' 39 new disagreement cells with ALL adjudication columns
#     EMPTY (first/second reviewer answers only), for TA+YA to adjudicate jointly.
import csv, warnings
warnings.simplefilter("ignore")
from openpyxl import load_workbook, Workbook

ITEMS_ok=None
# 47 items = the tool items; take them from the batch6 detail (recusal..causal_err_disc)
# --- final adjudicated value per (PMID,variable) from the analysis long dataset ---
finmap={}
for r in csv.DictReader(open("data/analysis/07_23_2026_ANALYSIS_DATASET_long.csv",encoding="utf-8-sig")):
    finmap[(r["PMID"],r["variable"])]=(r["final"],r["source"],r.get("resolution_note",""))
p377=set(k[0] for k in finmap)

def load(f):
    wb=load_workbook(f, read_only=True, data_only=True); ws=wb.active
    hdr=[str(c.value) for c in ws[1]]; ci={h:i for i,h in enumerate(hdr)}
    out={}
    for row in ws.iter_rows(min_row=2, values_only=True):
        key=(str(row[ci["PMID"]]).strip().replace(".0",""), row[ci["variable"]])
        out[key]=row; out.setdefault("_ci",ci)
    ci=out.pop("_ci"); wb.close(); return out, ci

TA,tci=load("private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_TA.xlsx")
YA,yci=load("private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_YA.xlsx")

SRC_PHASE={"TA=YA":"Phase I (TA=YA concordant)","phaseII":"Phase II (joint)","phase2-normalised":"Phase II (joint)",
           "unresolved":"Unresolved","recovered-STUDY-0945":"Phase II (recovered)","skiplogic-resolved":"Resolved by skip-logic"}

OUT=["PMID","Title","Study_Type","adjudicated_exposure","adjudicated_outcome","variable",
     "first_reviewer","second_reviewer","Adjudication_TA","Comments_TA","Adjudication_YA","Comments_YA",
     "Final_adjudicated","phase","Adjudication_type"]
wb=Workbook(); ws=wb.active; ws.title="adjudication_master"; ws.append(OUT)

# ---- 377 rows: every existing disagreement cell (spine = TA progress worklist), 47 items only ----
n377=0
for key,row in TA.items():
    var=key[1]
    if key[0] not in p377: continue
    src=finmap.get(key,("","",""))
    if src[1] in (None,"","agreed"):        # keep only cells that were routed to adjudication
        continue
    yrow=YA.get(key)
    def tg(c): return row[tci[c]] if c in tci and tci[c]<len(row) else ""
    def yg(c): return yrow[yci[c]] if (yrow is not None and c in yci and yci[c]<len(yrow)) else ""
    ws.append([key[0], tg("Title"), tg("Study_Type"), tg("adjudicated_exposure"), tg("adjudicated_outcome"), var,
               tg("first_reviewer"), tg("second_reviewer"),
               tg("Adjduciation_TA"), tg("Comments_TA"), yg("Adjduciation_YA"), yg("Comments_YA"),
               src[0], SRC_PHASE.get(src[1], src[1]), tg("Adjudciation_type")])
    n377+=1

# ---- 39 batch-6 rows: adjudication columns EMPTY ----
b6=load_workbook("private/reviewers/adjudication-worklists/08_08_2026_batch6_Needs_adj.xlsx"); bws=b6.active
bh=[c.value for c in bws[1]]; bci={h:i for i,h in enumerate(bh)}
nnew=0
for row in bws.iter_rows(min_row=2, values_only=True):
    g=lambda c: row[bci[c]] if c in bci else ""
    ws.append([g("PMID"), g("Title"), g("Study_Type"), g("adjudicated_exposure"), g("adjudicated_outcome"), g("variable"),
               g("first_reviewer"), g("second_reviewer"),
               "", "", "", "",                       # TA, Comments_TA, YA, Comments_YA  -> empty
               "",                                    # Final_adjudicated -> empty (joint session)
               "Batch 6 - joint (pending)", ""])
    nnew+=1
b6.close()
wb.save("private/reviewers/adjudication-worklists/08_08_2026_adjudication_master.xlsx")
print(f"wrote private/reviewers/adjudication-worklists/08_08_2026_adjudication_master.xlsx")
print(f"  preserved 377-paper adjudication cells: {n377}")
print(f"  appended batch-6 new cells (empty adjudication): {nnew}")
print(f"  total rows: {n377+nnew}")

# integrity: how many preserved cells already have a non-blank Final_adjudicated
wb2=load_workbook("private/reviewers/adjudication-worklists/08_08_2026_adjudication_master.xlsx"); ws2=wb2.active
rows=list(ws2.iter_rows(min_row=2, values_only=True)); wb2.close()
ci={h:i for i,h in enumerate(OUT)}
filled_final=sum(1 for r in rows if r[ci["Final_adjudicated"]] not in (None,""))
filled_ta=sum(1 for r in rows if r[ci["Adjudication_TA"]] not in (None,""))
filled_ya=sum(1 for r in rows if r[ci["Adjudication_YA"]] not in (None,""))
newblank=sum(1 for r in rows if r[ci["phase"]]=="Batch 6 - joint (pending)" and r[ci["Final_adjudicated"]] in (None,""))
from collections import Counter
print("  Final_adjudicated non-blank:",filled_final,"| TA non-blank:",filled_ta,"| YA non-blank:",filled_ya)
print("  batch-6 rows with EMPTY final (should be 39):",newblank)
print("  phase breakdown:",dict(Counter(r[ci['phase']] for r in rows)))
