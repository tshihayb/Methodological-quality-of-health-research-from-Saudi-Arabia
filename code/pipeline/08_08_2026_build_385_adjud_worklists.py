# NOTE (public repository): 8 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
# -*- coding: utf-8 -*-
# Build 385 versions of the four adjudication worklists the 07_24 report reads, folding in batch 6.
# Batch-6's 39 disagreements were resolved in a single JOINT TA+YA session, so we record them as
# concordant (Adjduciation_TA == Adjduciation_YA == the joint final) -> they read as "Phase I
# concordant" with the joint value; footnoted in the report. Reviewer_ID rows added for the rid map.
import warnings; warnings.simplefilter("ignore")
from openpyxl import load_workbook, Workbook
import csv

B6=["STUDY-0401","STUDY-0658","STUDY-0161","STUDY-0275","STUDY-0449","STUDY-0320","STUDY-0927","STUDY-0905"]
PAIR={"STUDY-0401":(2,13),"STUDY-0658":(7,9),"STUDY-0161":(7,10),"STUDY-0275":(5,8),
      "STUDY-0449":(7,13),"STUDY-0320":(4,8),"STUDY-0927":(8,12),"STUDY-0905":(6,7)}

def load(f):
    wb=load_workbook(f); ws=wb.active
    hdr=[c.value for c in ws[1]]
    rows=[list(r) for r in ws.iter_rows(min_row=2, values_only=True)]
    wb.close(); return hdr, rows
def save(f, hdr, rows):
    wb=Workbook(); ws=wb.active; ws.append(hdr)
    for r in rows: ws.append(r)
    wb.save(f)
def drop_b6(hdr, rows):
    pi=hdr.index("PMID")
    return [r for r in rows if str(r[pi]).strip().replace(".0","") not in B6]

# --- batch-6 detail: disagreement r1/r2 + joint final ---
cd=list(csv.DictReader(open("data/adjudication/08_08_2026_batch6_cell_detail.csv",encoding="utf-8-sig")))
wb=load_workbook("private/reviewers/adjudication-worklists/08_08_2026_adjudication_master.xlsx"); ws=wb.active
mh=[c.value for c in ws[1]]; mci={h:i for i,h in enumerate(mh)}
finmap={}
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[mci['phase']]=="Batch 6 - joint (pending)":
        finmap[(str(r[mci['PMID']]),r[mci['variable']])]=r[mci['Final_adjudicated']]
wb.close()
# metadata (Title/exposure/outcome) from batch6 Needs_adj
wb=load_workbook("private/reviewers/adjudication-worklists/08_08_2026_batch6_Needs_adj.xlsx"); ws=wb.active
bh=[c.value for c in ws[1]]; bci={h:i for i,h in enumerate(bh)}
meta={}
for r in ws.iter_rows(min_row=2, values_only=True):
    meta[str(r[bci['PMID']])]=(r[bci['Title']],r[bci['Study_Type']],r[bci['adjudicated_exposure']],r[bci['adjudicated_outcome']])
wb.close()

dis=[c for c in cd if c["needs_adj"]=="True"]
dna=[c for c in cd if c["needs_adj"]!="True"]

# ---------- ag (do_not_Need): + batch-6 non-disagreement cells ----------
hdr,rows=load("private/reviewers/adjudication-worklists/04_17_2026_do_not_Need_adj.xlsx"); rows=drop_b6(hdr,rows)
ci={h:i for i,h in enumerate(hdr)}
for c in dna:
    t=meta.get(c["PMID"],("","","",""))
    row=[""]*len(hdr)
    row[ci["PMID"]]=c["PMID"]; row[ci["Title"]]=t[0]; row[ci["Study_Type"]]=c["Study_Type"]
    row[ci["adjudicated_exposure"]]=t[2]; row[ci["adjudicated_outcome"]]=t[3]; row[ci["variable"]]=c["variable"]
    row[ci["first_reviewer"]]=c["first_reviewer"]; row[ci["second_reviewer"]]=c["second_reviewer"]; row[ci["complete"]]=1
    rows.append(row)
save("private/reviewers/adjudication-worklists/08_08_2026_do_not_Need_adj_385.xlsx", hdr, rows)
print("ag_385:", len(rows), "rows")

# ---------- ta / ya: + batch-6 39 disagreements (adj = joint final) + Reviewer_ID rows ----------
def build_adj(src, adjcol, commentcol, donecol):
    hdr,rows=load(src); rows=drop_b6(hdr,rows); ci={h:i for i,h in enumerate(hdr)}
    # disagreement rows (same order as `dis`)
    for c in dis:
        t=meta.get(c["PMID"],("","","",""))
        fin=finmap.get((c["PMID"],c["variable"]),"")
        row=[""]*len(hdr)
        row[ci["PMID"]]=c["PMID"]; row[ci["Title"]]=t[0]; row[ci["Study_Type"]]=c["Study_Type"]
        row[ci["adjudicated_exposure"]]=t[2]; row[ci["adjudicated_outcome"]]=t[3]; row[ci["variable"]]=c["variable"]
        row[ci["first_reviewer"]]=c["first_reviewer"]; row[ci["second_reviewer"]]=c["second_reviewer"]; row[ci["complete"]]=1
        row[ci[adjcol]]=fin
        if "Adjudciation_type" in ci: row[ci["Adjudciation_type"]]="Full"
        rows.append(row)
    # Reviewer_ID rows (only needed in TA for the rid map, but add to both for parallelism)
    for p in B6:
        lo,hi=PAIR[p]
        row=[""]*len(hdr)
        row[ci["PMID"]]=p; row[ci["variable"]]="Reviewer_ID"
        row[ci["first_reviewer"]]=lo; row[ci["second_reviewer"]]=hi; row[ci["complete"]]=1
        rows.append(row)
    save(src.replace("07_22_2026_","08_08_2026_").replace("_toolorder",""), hdr, rows)
    return len(rows)
n_ta=build_adj("private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_TA_toolorder.xlsx","Adjduciation_TA","Comments_TA","Adjudciation_done_TA")
n_ya=build_adj("private/reviewers/adjudication-worklists/07_22_2026_Needs_adj_progress_YA_toolorder.xlsx","Adjduciation_YA","Comments_YA","Adjudciation_done_YA")
print("ta_385:", n_ta, "| ya_385:", n_ya)

# ---------- ph (phase II): unchanged (batch-6 not added; they read as concordant) ----------
hdr,rows=load("private/reviewers/adjudication-worklists/07_23_2026_TA_YA_Differed_phase_II.xlsx"); rows=drop_b6(hdr,rows)
save("private/reviewers/adjudication-worklists/08_08_2026_TA_YA_Differed_phase_II_385.xlsx", hdr, rows)
print("ph_385:", len(rows), "rows (unchanged)")
print("\nwrote: private/reviewers/adjudication-worklists/08_08_2026_do_not_Need_adj_385.xlsx / _Needs_adj_progress_TA_385.xlsx / _YA_385.xlsx / _TA_YA_Differed_phase_II_385.xlsx")
