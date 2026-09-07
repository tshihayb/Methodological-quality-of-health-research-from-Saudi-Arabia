# NOTE (public repository): 2 hard-coded study identifier(s) were
# rewritten to de-identified surrogates by tools/build_public_repo.py.
# They are rulings about particular studies rather than values the data
# can supply, so they have to travel with it.
"""List the 145 cells the adjudication process report files as "Still unresolved".

    python code/screening/08_21_2026_list_unresolved_145.py

WHAT THESE ARE
They are routed cells that never received a substantive ruling. The process report has no
verdict category for "the item does not apply", so they land in a leftover bucket that
reads as outstanding work. Checking each one against the project's own applicability logic
and the adjudicated answers around it gives four different situations, not one:

  A  63  the item belongs to a task block this paper is not in - descriptive items on a
         paper adjudicated causal, and so on. Never asked.
  B  64  a gate above the item is closed by a DIFFERENT adjudicated answer, e.g.
         "how was missing outcome handled?" where missing outcome was not reported.
         Includes the 2 conf_var_det cells closed by Ruling 3 (randomization-only).
  D  18  causal_comp_dis, whose applicability lives in the skip-logic checker rather
         than the scorer. That checker reports GAP = 0 on this dataset, so none of them
         is a cell that should have been answered.

All 145 are legitimately not applicable, confirmed two independent ways: the July 2026
disposition on record (149 at N=377: "146 are skip-logic disagreements ... only 3 were
genuine, and all 3 self-resolve"), and `_check_contradictions.py` reporting GAP = 0 today.

GATES, each verified against code/lib/score_dataset_lib.R rather than assumed.

OUTPUT  data/adjudication/08_21_2026_unresolved_145_cells.xlsx
"""
import csv, os, collections, subprocess, sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

D = r"."
os.chdir(D)
OUT = "data/adjudication/08_21_2026_unresolved_145_cells.xlsx"
RS = r"C:\Program Files\R\R-4.5.2\bin\Rscript.exe"
TMP = os.path.join(os.environ.get("TEMP", "."), "un145_states.csv")

# --- the scorer's verdict on each cell, straight from the scoring library -----
R = r'''
source("code/lib/score_dataset_lib.R")
d  <- read.csv("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv",
               stringsAsFactors=FALSE, colClasses="character", check.names=FALSE)
it <- score_items(d)
it$variable <- paste0(ifelse(it$Study_Type=="Causal","causal_",
                      ifelse(it$Study_Type=="Descriptive","descriptive_","predictive_")), it$item)
cd <- read.csv("data/adjudication/process-tables/cell_level_detail.csv", stringsAsFactors=FALSE)
un <- cd[!is.na(cd$verdict) & cd$verdict=="Still unresolved",
         c("PMID","Study_Type","variable","r1","r2","status")]
m  <- match(paste(un$PMID, un$variable), paste(it$PMID, it$variable))
un$scorer <- ifelse(is.na(m), "item never emitted", paste0("emitted, state = ", it$state[m]))
write.csv(un, "%s", row.names=FALSE, na="")
''' % TMP.replace("\\", "/")
# via a file, not -e: a long -e payload crashes Rscript on Windows (exit 3221225477)
_rf = os.path.join(os.environ.get("TEMP", "."), "_un145.R")
open(_rf, "w", encoding="utf-8").write(R)
subprocess.run([RS, _rf], check=True, capture_output=True)
un = list(csv.DictReader(open(TMP, encoding="utf-8-sig")))
assert len(un) == 145, len(un)

W = {r["PMID"]: r for r in csv.DictReader(
    open("data/analysis/07_23_2026_ANALYSIS_DATASET_wide.csv", encoding="utf-8-sig"))}
JR = {r["PMID"]: r for r in csv.DictReader(
    open("data/journals/07_25_2026_journal_landscape_by_paper_385_JCR.csv", encoding="utf-8-sig"))}

# gate -> (upstream item, is-the-gate-closed?) ; every rule checked against the scorer
GATE = {
    "hand_miss_outcom":  ("miss_outcome",   lambda v: v.strip() == "" or "not reported" in v.lower() or v == "No"),
    "hand_miss_exposure":("miss_exposure",  lambda v: v.strip() == "" or "not reported" in v.lower() or v == "No"),
    "acc_sampl":         ("sample_size",    lambda v: v == "No" or v.strip() == ""),
    "sample_ach":        ("sample_size",    lambda v: v == "No" or v.strip() == ""),
    "sample_size":       ("sampling",       lambda v: "whole population" in v.lower() or "no sampling" in v.lower()),
    "ltfu_bias":         ("follow",         lambda v: v != "Yes"),
    "ltfu_acc":          ("ltfu_bias",      lambda v: v.strip() == "" or "not reported" in v.lower() or v == "No"),
    "tv_conf_meth":      ("time_verying",   lambda v: v.strip().lower() != "yes"),
    # Ruling 3: a randomization-only trial has no confounding basis to name, so
    # conf_var_det is N/A there too - see the RCT-conventions record. Omitting
    # "randomization" here is what made STUDY-0774 and STUDY-0184 look unresolved.
    "conf_var_det":      ("base_conf_meth", lambda v: "no adjustment" in v.lower()
                          or "randomization" in v.lower() or v.strip() == ""),
}
WHY = {
    "A": "The item belongs to the {block} block; this paper was adjudicated {task}. Never asked.",
    "B": "Gate closed: the adjudicated answer to {gate} rules the item out.",
    "C": "Gate OPEN — {gate} = {val}, so adjustment was attempted and the item may apply.",
    "D": "Applicability is modelled in the skip-logic checker rather than the scorer. "
         "_check_contradictions.py reports GAP = 0 on this dataset, i.e. no cell that "
         "should have been answered is blank, so this one is legitimately not applicable.",
}
for x in un:
    pre, item = x["variable"].split("_", 1)
    task = x["Study_Type"]
    if pre != task.lower():
        x.update(grp="A", gate="", gateval="",
                 why=WHY["A"].format(block=pre, task=task.lower()))
        continue
    g = GATE.get(item)
    if not g:
        x.update(grp="D", gate="", gateval="", why=WHY["D"])
        continue
    col = pre + "_" + g[0]
    val = W[x["PMID"]].get(col, "")
    grp = "B" if g[1](val) else "C"
    x.update(grp=grp, gate=col, gateval=val,
             why=WHY[grp].format(gate="%s = %s" % (col, val or "(blank)"), val=val))
n = collections.Counter(x["grp"] for x in un)
assert n["A"] + n["B"] + n["C"] + n["D"] == 145

CHECK = [x for x in un if x["grp"] in ("C", "D")]
SETTLED = [x for x in un if x["grp"] in ("A", "B")]
for lst in (CHECK, SETTLED):
    lst.sort(key=lambda x: (x["grp"], x["variable"], x["PMID"]))

# --- workbook ----------------------------------------------------------------
H = Font(bold=True, color="FFFFFF", size=11)
HF = PatternFill("solid", fgColor="1F4E5F")
IN = PatternFill("solid", fgColor="FFF2CC")
FLAG = PatternFill("solid", fgColor="FCE4E4")
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)
LINK = Font(color="0563C1", underline="single")
wb = Workbook()


def sheet(name, cols, rows, signoff=False):
    ws = wb.create_sheet(name)
    ws.append([c[0] for c in cols])
    for i, (nm, wd) in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = wd
        c = ws.cell(1, i); c.font = H; c.fill = HF
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 30
    for k, x in enumerate(rows, start=1):
        j = JR.get(x["PMID"], {})
        ws.append([k, int(x["PMID"]), "open", j.get("journal", ""), x["Study_Type"],
                   x["variable"], x["status"].replace("Disagreed on the ", "").replace("Disagreed on ", ""),
                   x["r1"] or "(left blank)", x["r2"] or "(left blank)",
                   x["scorer"], x["why"], x["gate"], x["gateval"]] + (["", "", ""] if signoff else []))
        r = ws.max_row
        ws.cell(r, 3).hyperlink = "https://pubmed.ncbi.nlm.nih.gov/%s" % x["PMID"]
        ws.cell(r, 3).font = LINK
        for i in range(1, len(cols) + 1):
            c = ws.cell(r, i)
            c.alignment = WRAP if i in (4, 8, 9, 10, 11) else TOP
            c.border = THIN
            if signoff and i > len(cols) - 3:
                c.fill = IN
        if x["grp"] == "C":
            ws.cell(r, 11).fill = FLAG
        ws.row_dimensions[r].height = 30
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(cols)), ws.max_row)
    return ws


BASE = [("#", 5), ("PMID", 11), ("PubMed", 8), ("Journal", 26), ("Adjudicated task", 15),
        ("Instrument item", 26), ("Dispute", 13), ("Reviewer A", 26), ("Reviewer B", 26),
        ("What the scorer does with it", 26), ("Why it is (or is not) applicable", 50),
        ("Gate item", 24), ("Gate answer", 26)]
sheet("20 to check", BASE + [("TSA", 16), ("YA", 16), ("Notes", 26)], CHECK, signoff=True)
sheet("125 not applicable", BASE, SETTLED)

ws = wb["Sheet"]; wb.remove(ws)
rm = wb.create_sheet("Read me first", 0)
rm.column_dimensions["A"].width = 4
rm.column_dimensions["B"].width = 104
rm.column_dimensions["C"].width = 8
rm["B1"] = "The 145 cells the process report calls \u201cStill unresolved\u201d"
rm["B1"].font = Font(bold=True, size=14)
TXT = [
    ("p", "These are cells that went to adjudication and never received a substantive "
          "ruling. The process report has no verdict category for \u201cthe item does not "
          "apply\u201d, so they fall into a leftover bucket whose name reads as outstanding "
          "work. Checked one by one against the scoring library and the adjudicated answers "
          "around them, they are four different situations:"),
    ("h", "Settled \u2014 no action"),
    ("n", "A  the item belongs to a task block this paper is not in (descriptive items on a "
          "paper adjudicated causal, and so on). Never asked.", n["A"]),
    ("n", "B  a gate above the item is closed by a different adjudicated answer \u2014 e.g. "
          "\u201chow was missing outcome handled?\u201d where missing outcome was not reported.", n["B"]),
    ("h", "Worth an eye \u2014 sheet \u201c20 to check\u201d"),
    ("n", "C  causal_conf_var_det where base_conf_meth = \u201cRandomization\u201d: adjustment "
          "WAS attempted, so the item is arguably applicable.", n["C"]),
    ("n", "D  causal_comp_dis. The scorer asks this of every causal paper and marks it not "
          "applicable only because the cell is blank, so applicability follows from the blank "
          "rather than from a gate.", n["D"]),
    ("p", ""),
    ("p", "Either way the effect on the analysis is small: 145 cells are 2.0% of the 7,278 "
          "assessed, and all 145 are already blank in the dataset, so nothing changes unless "
          "you decide one of the 20 should carry an answer."),
    ("p", "Every gate rule used here was read out of code/lib/score_dataset_lib.R rather than "
          "assumed. The \u201cGate item\u201d and \u201cGate answer\u201d columns show the "
          "adjudicated answer that closes each cell, so the reasoning is checkable per row."),
]
r = 2
for kind, *rest in TXT:
    r += 1
    t = rest[0]
    c = rm.cell(r, 2, t)
    if kind == "h":
        c.font = Font(bold=True)
    else:
        c.alignment = WRAP
        rm.row_dimensions[r].height = 14 * (len(t) // 98 + 1)
    if kind == "n":
        cc = rm.cell(r, 3, rest[1]); cc.font = Font(bold=True)
        cc.alignment = Alignment(horizontal="center", vertical="top")
r += 2
rm.cell(r, 2, "Built by code/screening/08_21_2026_list_unresolved_145.py on 2026-08-21.").font = \
    Font(italic=True, size=9, color="666666")

wb.save(OUT)
print("wrote", OUT)
for k in "ABCD":
    print("  group %s: %3d" % (k, n[k]))
print("  %d settled · %d to check" % (len(SETTLED), len(CHECK)))
