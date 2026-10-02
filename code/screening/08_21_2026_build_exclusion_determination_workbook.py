"""Build the TSA/YA exclusion-reason determination workbook.

    python code/screening/08_21_2026_build_exclusion_determination_workbook.py

WHAT THIS IS FOR
236 records were excluded at screening. This workbook puts in front of TSA and YA every
paper whose exclusion reason does not rest on two recorded screener judgements, so that
each one ends up resting on a named human decision instead of on a language model, a
default, or one person.

THE RULE (TSA, 2026-08-21), applied uniformly rather than paper by paper:
if either screener never recorded an exclusion reason, that screener records one now.

⚠ PROVENANCE IS TRACED TO THE ORIGINAL SCREENING WORKBOOKS, NOT THE MASTER CSV.
`08_13_2026_exclusion_final_master.csv` loses the adjudications: a blank exclusion-reason
cell on the *Include* side of a status disagreement reads there as "one reviewer only", and
a reason recorded in the *study-type* column reads as "no reason recorded". Reasons are
therefore collected from every place a screener could have written one:
  f300_ta_ya_TA.xlsx     Excluded · T_corr (TSA's corresponding-author re-review) · Y_corr ·
                         Included (study-type disagreement column)
  f300_ta_ya_clean.xlsx  Saudi_corr and Non-Saudi_corr pools (adjudication + reasons)
  s300_adjudicated.xlsx  All + the four disagreement sheets (adjudication + `reason adj`)
"Corresponding author was not from a Saudi institution" is NOT counted as a reason: that
criterion was relaxed and the answer withdrawn.

HOW THE 236 COME OUT

  162  both screeners recorded the same reason and it is the reason on file   - settled
    9  both recorded the same reason but the file says something else         - SIGN-OFF
       (the Non-health harmonisation applied when the batches were locked)
    7  both recorded a reason, the two disagree, never adjudicated            - ADJUDICATE
   54  only one screener ever recorded a reason (YA missing 36, TSA missing 18) - RECORD
    4  neither screener recorded a reason                                     - RECORD

So 65 papers need a determination and 9 need a sign-off. Completing them puts all 236 on a
named human decision, removes the language model from this step entirely, and makes
Supplementary Methods 2's provenance sentence true as written.

OUTPUT
  data/screening/08_21_2026_exclusion_reason_determination_TSA_YA.xlsx
"""
import csv, os, collections
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

D = r"."
os.chdir(D)
OUT = "data/screening/08_21_2026_exclusion_reason_determination_TSA_YA.xlsx"

REASONS = [
    "Non-human / laboratory",
    "Non-health topic",
    "Review (narrative/systematic)",
    "Qualitative research",
    "Non-empirical (protocol/simulation)",
    "Case report / series",
]
SUPP_WORDING = {
    "Non-human / laboratory": ("Non-human research", 174),
    "Non-health topic": ("Non-health-related research", 22),
    "Review (narrative/systematic)": ("Review article", 14),
    "Qualitative research": ("Qualitative research", 11),
    "Non-empirical (protocol/simulation)": ("Non-empirical or simulation-only study", 9),
    "Case report / series": ("Case report or case series", 6),
}
# the free-text answers the screening forms allowed -> the six categories
NORM = {
    "non-human research": "Non-human / laboratory",
    "non-health": "Non-health topic",
    "narrative review": "Review (narrative/systematic)",
    "systematic review": "Review (narrative/systematic)",
    "qualitative research": "Qualitative research",
    "case report/series": "Case report / series",
    "non-emperical data (simulation)": "Non-empirical (protocol/simulation)",
    "non-empirical data": "Non-empirical (protocol/simulation)",
}
TIER = {"": "clean (agreed or adjudicated on record)",
        "A": "A - reason disagreement",
        "B": "B - reason contradicted the screener's own comment",
        "C": "C - TA only, YA blank",
        "D": "D - disposition uncertain, coded from the PubMed record"}


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8-sig")))


def is_reason(v):
    """Did a screener actually record an exclusion reason here?"""
    v = (v or "").strip()
    if not v or v.lower() == "nan":
        return False
    return "corresponding author" not in v.lower() and "not from a saudi" not in v.lower()


def cat_of(v):
    return NORM.get((v or "").split("  [")[0].strip().lower(), "")


def rows_of(path, name):
    w = load_workbook("data/screening/" + path, data_only=True)[name]
    hdr = [str(c.value).strip() if c.value else "" for c in next(w.iter_rows(min_row=1, max_row=1))]
    for row in w.iter_rows(min_row=2, values_only=True):
        d = {h: (str(v).strip() if v not in (None, "") else "") for h, v in zip(hdr, row) if h}
        if d.get("PMID") and d["PMID"] != "None":
            yield d


def collect_screener_reasons():
    """Every place either screener could have recorded a reason, in one pass.

    Returns TA, YA (PMID -> "reason  [where it was written]"), INC (who voted Include)
    and ADJ (PMID -> (where, decision, adjudicated reason)).
    """
    TA, YA, INC, ADJ = {}, {}, {}, {}

    def put(d, pm, val, src):
        if is_reason(val) and pm not in d:
            d[pm] = "%s  [%s]" % (val.strip(), src)

    for d in rows_of("f300_ta_ya_TA.xlsx", "Excluded"):
        put(TA, d["PMID"], d.get("Reason for Exclusion_t"), "batch-1 screening")
        put(YA, d["PMID"], d.get("Reason for Exclusion_y"), "batch-1 screening")
    for d in rows_of("f300_ta_ya_TA.xlsx", "T_corr"):
        if d.get("Status_t_new") == "Exclude":
            put(TA, d["PMID"], d.get("Reason for Exclusion_t_new"), "TSA corr-author re-review")
        elif d.get("Status_t_new") == "Include":
            INC[d["PMID"]] = "TSA, at the corresponding-author re-review"
    for d in rows_of("f300_ta_ya_TA.xlsx", "Y_corr"):
        put(YA, d["PMID"], d.get("Reason for Exclusion_y"), "YA corr-author re-check")
    for d in rows_of("f300_ta_ya_TA.xlsx", "Included"):
        if d.get("Status_y") == "Exclude":
            put(YA, d["PMID"], d.get("Disagreement on study type"),
                "batch-1 Included sheet, study-type column")
        if d.get("Status_t") == "Include":
            INC.setdefault(d["PMID"], "TSA, at batch-1 screening")
    for nm in ("Saudi_corr", "Non-Saudi_corr"):
        for d in rows_of("f300_ta_ya_clean.xlsx", nm):
            if d.get("Status_y") == "Exclude":
                put(YA, d["PMID"], d.get("Study Type_y_new"), nm + " pool")
            elif d.get("Status_y") == "Include":
                INC[d["PMID"]] = "YA, in the " + nm + " pool"
            if d.get("Status_t") == "Exclude":
                put(TA, d["PMID"], d.get("Study Type_t_new"), nm + " pool")
            elif d.get("Status_t") == "Include":
                INC[d["PMID"]] = "TSA, in the " + nm + " pool"
            if d.get("Adjudicaiton"):
                reason = d.get("Study Type_y_new") if d.get("Status_y") == "Exclude" \
                         else d.get("Study Type_t_new")
                ADJ[d["PMID"]] = ("f300_ta_ya_clean.xlsx :: " + nm,
                                  d["Adjudicaiton"], reason or "")
    for d in rows_of("s300_adjudicated.xlsx", "All"):
        put(TA, d["PMID"], d.get("Reason for Exclusion_ta"), "batch-2 screening")
        put(YA, d["PMID"], d.get("Reason for Exclusion_ya"), "batch-2 screening")
        if d.get("Status_ta") == "Include":
            INC[d["PMID"]] = "TSA, at batch-2 screening"
        if d.get("Status_ya") == "Include":
            INC[d["PMID"]] = "YA, at batch-2 screening"
    for nm, col in (("Talal incl but Yassser excl", "Adjudicated"),
                    ("Yasser incl but Talal excl", "adjud")):
        for d in rows_of("s300_adjudicated.xlsx", nm):
            ADJ[d["PMID"]] = ("s300_adjudicated.xlsx :: " + nm,
                              d.get(col, ""), d.get("reason adj", ""))
    return TA, YA, INC, ADJ


def load_basis():
    """The rationale written for each of the 35 lock-time overrides.

    ⚠ The lock scripts saved it into the two LOCKED workbooks and the master-CSV write
    path never copied it across, which is why the master's own basis column is empty.
    """
    out = {}
    for d in rows_of("08_13_2026_batch1_exclusions_LOCKED.xlsx", "Batch1_audit_108"):
        out[d["PMID"]] = d.get("basis", "")
    for d in rows_of("08_13_2026_batch2_exclusions_LOCKED.xlsx", "Batch2_audit_128"):
        out[d["PMID"]] = d.get("basis", "")
    return out


def basis_kind(b):
    if not b:
        return "(no rationale recorded)"
    if b.startswith("agreed"):
        return "Taken straight from the screening record"
    if b.startswith(("harmoniz", "harmonize")):
        return "Harmonised to Non-health at lock time"
    if b.startswith("reviewer comment"):
        return "Read off the screener's own free-text comment"
    if "(YA blank)" in b or "(TA blank)" in b:
        return "The one screener who answered"
    if b.startswith(("disagreement", "reason-disagreement")):
        return "Disagreement, one screener's reason taken"
    if b.startswith(("Non-Saudi_corr", "Saudi_corr")):
        return "Corresponding-author re-check pool"
    if "folded" in b or "mislabelled" in b:
        return "Folded in from another PRISMA step"
    return "Other"


# =============================================================================
# Assemble
# =============================================================================
est = {r["PMID"]: r for r in rd("data/screening/08_14_2026_reason_establishment.csv")}
mas = {r["PMID"]: r for r in rd("data/screening/08_13_2026_exclusion_final_master.csv")}
tit = {r["PMID"]: r for r in rd("data/screening/08_13_2026_all236_titles.csv")}
LLM = {r["PMID"]: r for r in rd("data/screening/08_13_2026_llm_56_classification.csv")}
assert len(est) == len(mas) == len(tit) == 236, "the 236 census must hold"
TA, YA, INC, ADJ = collect_screener_reasons()
BAS = load_basis()

ACTIONS = {
    "adjudicate": ("Both recorded a reason and the two DISAGREE - never adjudicated",
                   "agree one reason between you"),
    "both": ("NEITHER screener recorded a reason", "both of you record one"),
    "ta": ("TSA never recorded a reason - TSA voted to include it, or gave only the "
           "withdrawn corresponding-author answer", "TSA records one"),
    "ya": ("YA never recorded a reason - YA voted to include it, or gave only the "
           "withdrawn corresponding-author answer", "YA records one"),
}
rows = []
for pmid in est:
    m, t = mas[pmid], tit[pmid]
    ta, ya = TA.get(pmid, ""), YA.get(pmid, "")
    tc, yc = cat_of(ta), cat_of(ya)
    final = m["FINAL_reason"]
    aw, ad, ar = ADJ.get(pmid, ("", "", ""))
    lm = LLM.get(pmid)
    followed = ""
    if lm:
        followed = ("the language model" if lm["agree"] == "DIFFER" and final == lm["mine"]
                    else "the screener" if lm["agree"] == "DIFFER" else "both, they agreed")
    if tc and yc and tc == yc:
        state, action = ("settled", "") if final == tc else ("signoff", "")
    elif tc and yc:
        state, action = "todo", "adjudicate"
    elif tc or yc:
        state, action = "todo", ("ya" if tc else "ta")
    else:
        state, action = "todo", "both"
    bas = BAS.get(pmid, "")
    rows.append(dict(
        pmid=pmid, state=state, action=action, batch=m["batch"],
        title=t["title"], journal=t["journal"], pubtype=t["pubtype"],
        ta=ta or "(never recorded one)", ya=ya or "(never recorded one)",
        ta_cat=tc, ya_cat=yc, included_by=INC.get(pmid, ""),
        adj_where=aw, adj_dec=ad, adj_reason=ar,
        final=final, resolved=m["RESOLVED_reason"] or "",
        conflict=bool(m["RESOLVED_reason"]) and m["RESOLVED_reason"] != final,
        basis=bas, basis_kind=basis_kind(bas), tier=TIER.get(m["flag_tier"], m["flag_tier"]),
        llm_mine=lm["mine"] if lm else "", llm_agree=lm["agree"] if lm else "",
        llm_followed=followed,
        link="https://pubmed.ncbi.nlm.nih.gov/%s" % pmid))

todo = [r for r in rows if r["state"] == "todo"]
sign = [r for r in rows if r["state"] == "signoff"]
done = [r for r in rows if r["state"] == "settled"]
nact = collections.Counter(r["action"] for r in todo)
assert len(todo) + len(sign) + len(done) == 236
ORDER = ["adjudicate", "both", "ta", "ya"]
todo.sort(key=lambda r: (ORDER.index(r["action"]), r["pmid"]))
sign.sort(key=lambda r: r["pmid"])
done.sort(key=lambda r: r["pmid"])

# --- styling ------------------------------------------------------------------
H = Font(bold=True, color="FFFFFF", size=11)
HF = PatternFill("solid", fgColor="1F4E5F")
SUBF = PatternFill("solid", fgColor="DCE6EC")
IN = PatternFill("solid", fgColor="FFF2CC")
FLAG = PatternFill("solid", fgColor="FCE4E4")
TITLE = Font(bold=True, size=14)
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")
CEN = Alignment(horizontal="center", vertical="top")
THIN = Border(*[Side(style="thin", color="D9D9D9")] * 4)
LINK = Font(color="0563C1", underline="single")

wb = Workbook()


def header(ws, cols, height=34):
    ws.append([c[0] for c in cols])
    for i, (name, width) in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = width
        c = ws.cell(1, i)
        c.font = H; c.fill = HF
        c.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = height


def dropdown(ws, ref):
    dv = DataValidation(type="list", formula1='"%s"' % ",".join(REASONS),
                        allow_blank=True, showDropDown=False)
    dv.error = "Pick one of the six categories, or leave blank and explain in Notes."
    dv.errorTitle = "Not one of the six reasons"
    ws.add_data_validation(dv)
    dv.add(ref)


# =============================================================================
# Sheet 1 - instructions
# =============================================================================
ws = wb.active
ws.title = "Read me first"
ws.column_dimensions["A"].width = 4
ws.column_dimensions["B"].width = 100
ws.column_dimensions["C"].width = 10
ws.column_dimensions["D"].width = 44
ws["B1"] = "Exclusion reasons for TSA and YA to determine"
ws["B1"].font = TITLE
BLOCKS = [
    ("h", "What this is"),
    ("p", "236 records were excluded at screening. This workbook contains every paper whose "
          "exclusion reason does not rest on two recorded screener judgements, so that each "
          "one can end up resting on a named human decision rather than on a language model, "
          "a default, or one person."),
    ("h", "The rule this workbook applies"),
    ("p", "If either of you never recorded an exclusion reason for a paper, that person "
          "records one now. Applied uniformly. What matters is not whether a reason exists "
          "for a paper, but whether both of you gave one."),
    ("h", "Where the reasons were read from"),
    ("p", "Not from the summary CSV, which loses adjudications, but from the original "
          "screening workbooks: the batch-1 Excluded, Included, T_corr and Y_corr sheets; the "
          "Saudi_corr and Non-Saudi_corr pools; and the batch-2 All sheet with its four "
          "disagreement sheets. Every column in which either of you could have written a "
          "reason was read, and each reason below is shown with the sheet it came from."),
    ("p", "\"Corresponding author was not from a Saudi institution\" is not counted as a "
          "reason. That criterion was relaxed to \"any Saudi author\" and the answer withdrawn, "
          "so a paper where one of you gave only that answer counts as having no reason from "
          "that person. That is why many papers are here."),
    ("h", "How the 236 come out"),
    ("h", "How to fill it in"),
    ("p", "1.  Sheet \"65 to determine\" is grouped by what is needed, hardest first: the "
          "seven where you both recorded a reason and disagreed, the four where neither of you "
          "recorded one, then the papers where one of you did not."),
    ("p", "2.  Fill your own column independently. Where only one of you is missing a reason "
          "the other's is shown, with the sheet it came from - you may of course take a "
          "different view."),
    ("p", "3.  Where you agree, copy it into \"Agreed final reason\". Where you do not, discuss "
          "and record the outcome there with a line in \"Notes\"."),
    ("p", "4.  Sheet \"9 to sign off\" is a different job: on those you both recorded the same "
          "reason and the file says something else. Confirm or reject the change."),
    ("h", "Why it is worth doing"),
    ("p", "It removes the language model from this step - one of the three declared "
          "language-model data uses in the AI-use declaration - and it makes the provenance "
          "sentence in Supplementary Methods 2 true as written."),
    ("h", "The six reason categories"),
]
r = 2
for kind, text in BLOCKS:
    r += 1
    c = ws.cell(r, 2, text)
    if kind == "h":
        c.font = BOLD
        if text == "How the 236 come out":
            for label, n_, tag in (
                    ("both recorded the same reason, and it is the reason on file", len(done), "settled"),
                    ("both recorded the same reason, the file says something else", len(sign), "SIGN OFF"),
                    ("both recorded a reason and they disagree, never adjudicated", nact["adjudicate"], "ADJUDICATE"),
                    ("only YA recorded one, so TSA never did", nact["ta"], "TSA RECORDS ONE"),
                    ("only TSA recorded one, so YA never did", nact["ya"], "YA RECORDS ONE"),
                    ("neither of you recorded one", nact["both"], "BOTH RECORD ONE")):
                r += 1
                ws.cell(r, 2, "      " + label).alignment = WRAP
                ws.cell(r, 3, n_).alignment = CEN
                ws.cell(r, 3).font = BOLD
                ws.cell(r, 4, tag).font = Font(bold=(tag != "settled"),
                                               color="666666" if tag == "settled" else "A8471F")
    else:
        c.alignment = WRAP
        ws.row_dimensions[r].height = 14 * (len(text) // 95 + 1)
r += 1
for i, t in enumerate(["Category (use these exact words)", "Current n",
                       "As it appears in Supplementary Methods 2"], start=2):
    ws.cell(r, i, t).font = H
    ws.cell(r, i).fill = HF
for reason in REASONS:
    r += 1
    ws.cell(r, 2, reason)
    ws.cell(r, 3, SUPP_WORDING[reason][1]).alignment = CEN
    ws.cell(r, 4, SUPP_WORDING[reason][0])
r += 1
ws.cell(r, 2, "Total").font = BOLD
ws.cell(r, 3, 236).font = BOLD
ws.cell(r, 3).alignment = CEN
r += 2
ws.cell(r, 2, "Built by code/screening/08_21_2026_build_exclusion_determination_workbook.py "
              "on 2026-08-21 from the original screening workbooks. If a determination changes "
              "a count, the PRISMA figure and Supplementary Methods 2 are regenerated from the "
              "data.").font = Font(italic=True, size=9, color="666666")
ws.cell(r, 2).alignment = WRAP

# =============================================================================
# Sheet 2 - the 65
# =============================================================================
C2 = [("#", 5), ("PMID", 11), ("PubMed", 9), ("Title", 54), ("Journal", 20),
      ("Publication type", 15), ("Who voted to include it", 26),
      ("TSA recorded, and where", 34), ("YA recorded, and where", 34),
      ("Adjudication on record", 30), ("Decision", 11), ("Adjudicated reason", 20),
      ("Reason currently on file", 24), ("Audit column, where it differs", 22),
      ("Where the reason on file came from", 32), ("Rationale recorded at lock time", 36),
      ("Language model said", 22), ("Model vs screener", 15), ("Which was followed", 18),
      ("TSA determination", 24), ("YA determination", 24), ("Agreed final reason", 24),
      ("Notes", 28)]
ws2 = wb.create_sheet("65 to determine")
header(ws2, C2)
n = 0
ranges = []
for act in ORDER:
    grp = [x for x in todo if x["action"] == act]
    if not grp:
        continue
    what, do = ACTIONS[act]
    ws2.append(["", "", "", "%s  —  %d paper%s   ➜  %s"
                % (what, len(grp), "s" if len(grp) > 1 else "", do)])
    hr = ws2.max_row
    ws2.cell(hr, 4).font = Font(bold=True, color="1F4E5F", size=11)
    for i in range(1, len(C2) + 1):
        ws2.cell(hr, i).fill = SUBF
    ws2.row_dimensions[hr].height = 20
    start = ws2.max_row + 1
    for rw in grp:
        n += 1
        ws2.append([n, int(rw["pmid"]), "open", rw["title"], rw["journal"], rw["pubtype"],
                    rw["included_by"], rw["ta"], rw["ya"],
                    rw["adj_where"], rw["adj_dec"], rw["adj_reason"],
                    rw["final"], rw["resolved"] if rw["conflict"] else "",
                    rw["basis_kind"], rw["basis"],
                    rw["llm_mine"], rw["llm_agree"], rw["llm_followed"], "", "", "", ""])
        r = ws2.max_row
        ws2.cell(r, 3).hyperlink = rw["link"]; ws2.cell(r, 3).font = LINK
        for i in range(1, len(C2) + 1):
            c = ws2.cell(r, i)
            c.alignment = WRAP if i in (4, 7, 8, 9, 10, 15, 16) else TOP
            c.border = THIN
            if i in (20, 21, 22, 23):
                c.fill = IN
        if rw["ta"].startswith("(never"):
            ws2.cell(r, 8).font = Font(italic=True, color="A8471F")
        if rw["ya"].startswith("(never"):
            ws2.cell(r, 9).font = Font(italic=True, color="A8471F")
        if rw["llm_followed"] == "the language model":
            ws2.cell(r, 19).fill = FLAG; ws2.cell(r, 19).font = BOLD
        if rw["conflict"]:
            ws2.cell(r, 14).fill = FLAG
        ws2.row_dimensions[r].height = 30
    ranges.append("T%d:V%d" % (start, ws2.max_row))
for ref in ranges:
    dropdown(ws2, ref)
ws2.freeze_panes = "D2"

# =============================================================================
# Sheet 3 - the 9 to sign off
# =============================================================================
C3 = [("#", 5), ("PMID", 11), ("PubMed", 9), ("Title", 56), ("Journal", 20),
      ("What you BOTH recorded", 26), ("Reason on file instead", 24),
      ("Audit column", 22), ("Rationale recorded at lock time", 44),
      ("Language model said", 22), ("Which was followed", 18),
      ("TSA sign-off", 24), ("YA sign-off", 24), ("Notes", 28)]
ws3 = wb.create_sheet("9 to sign off")
header(ws3, C3)
for i, rw in enumerate(sign, start=1):
    ws3.append([i, int(rw["pmid"]), "open", rw["title"], rw["journal"],
                rw["ta_cat"], rw["final"], rw["resolved"] if rw["conflict"] else "",
                rw["basis"], rw["llm_mine"], rw["llm_followed"], "", "", ""])
    r = ws3.max_row
    ws3.cell(r, 3).hyperlink = rw["link"]; ws3.cell(r, 3).font = LINK
    for j in range(1, len(C3) + 1):
        c = ws3.cell(r, j)
        c.alignment = WRAP if j in (4, 9) else TOP
        c.border = THIN
        if j in (12, 13, 14):
            c.fill = IN
    ws3.cell(r, 7).fill = FLAG
    ws3.row_dimensions[r].height = 30
dropdown(ws3, "L2:N%d" % ws3.max_row)
ws3.freeze_panes = "D2"
foot = ws3.max_row + 2
ws3.cell(foot, 2,
         "You both wrote the same reason; the file says something else. Eight of these nine are "
         "the Non-health harmonisation applied when the batches were locked - engineering, IT "
         "and environmental papers moved from Non-human to Non-health. It was a documented rule "
         "with a per-paper rationale (the column above), and batch-1's README records the lock "
         "decisions as yours, but it is not what the screening record says. Confirm or reject.")
ws3.cell(foot, 2).alignment = WRAP
ws3.merge_cells(start_row=foot, start_column=2, end_row=foot, end_column=9)
ws3.row_dimensions[foot].height = 60

# =============================================================================
# Sheet 4 - the settled 162
# =============================================================================
C4 = [("#", 5), ("PMID", 11), ("PubMed", 9), ("Title", 60), ("Journal", 22),
      ("TSA recorded, and where", 34), ("YA recorded, and where", 34),
      ("Reason on file", 26), ("Correction, only if you spot an error", 28)]
ws4 = wb.create_sheet("162 settled")
header(ws4, C4)
for i, rw in enumerate(done, start=1):
    ws4.append([i, int(rw["pmid"]), "open", rw["title"], rw["journal"],
                rw["ta"], rw["ya"], rw["final"], ""])
    r = ws4.max_row
    ws4.cell(r, 3).hyperlink = rw["link"]; ws4.cell(r, 3).font = LINK
    for j in range(1, len(C4) + 1):
        ws4.cell(r, j).alignment = WRAP if j in (4, 6, 7) else TOP
        ws4.cell(r, j).border = THIN
    ws4.cell(r, 9).fill = IN
    ws4.row_dimensions[r].height = 28
dropdown(ws4, "I2:I%d" % ws4.max_row)
ws4.freeze_panes = "D2"
ws4.auto_filter.ref = "A1:I%d" % ws4.max_row

# =============================================================================
# Sheet 5 - where the reason on file came from
# =============================================================================
wsp = wb.create_sheet("Where the reason came from")
wsp.column_dimensions["A"].width = 4
wsp.column_dimensions["B"].width = 100
wsp.column_dimensions["C"].width = 10
wsp.column_dimensions["D"].width = 46
wsp["B1"] = "What \"Reason on file\" is, and where it came from"
wsp["B1"].font = TITLE
CHAIN = [
    ("p", "Every sheet shows the same column. \"Reason on file\" is FINAL_reason in "
          "data/screening/08_13_2026_exclusion_final_master.csv - the column the published "
          "counts are built from; its tally is exactly the 174 / 22 / 14 / 11 / 9 / 6 printed "
          "in Supplementary Methods 2. It reached that state in five steps."),
    ("h", "1.  The screeners' own answers"),
    ("p", "Recorded on the screening forms, in whichever sheet and column the workflow put "
          "them. Shown here verbatim, each with its source."),
    ("h", "2.  The recount audit, 13 August  ->  RESOLVED_reason"),
    ("p", "08_13_2026_recount_exclusion_reasons.py rebuilt the reason for all 236: the agreed "
          "reason where both agreed, the adjudicated reason where they disagreed. Its README "
          "records that 209 could be assigned cleanly and 24 needed best-effort coding from "
          "the PubMed title and abstract, adding \"please verify these\". That verification was "
          "never done, and is part of what this workbook is asking for."),
    ("h", "3.  A language model, on 56 single-screener papers"),
    ("p", "08_13_2026_llm_classify_56.py determined the reason independently from title and "
          "abstract, using the papers both screeners had agreed on as worked examples. It "
          "agreed with the screener on 37 and differed on 19. Where it differed, the published "
          "reason followed the screener 10 times and the model 9 times - flagged \"the language "
          "model\" in the \"Which was followed\" column. Eight of those nine moved a paper from "
          "Non-human to Non-health topic."),
    ("h", "4.  Locking the batches  ->  FINAL_reason"),
    ("p", "08_13_2026_lock_batch1.py and _lock_batch2.py set FINAL_reason = RESOLVED_reason "
          "except for 35 hard-coded overrides, each with a written rationale - the \"Rationale "
          "recorded at lock time\" column. ⚠ That rationale was written into the two LOCKED "
          "workbooks and never copied into the master CSV, so the master's own basis column "
          "reads empty; this workbook reads it back out."),
    ("p", "The largest override is the Non-health harmonisation: 14 papers recorded by the "
          "screeners as \"Non-human research\" but which are engineering, IT or environmental "
          "work. Eight of them are on the sign-off sheet, because for those the two screeners "
          "had agreed with each other."),
    ("h", "5.  Labelling the provenance, 14 August"),
    ("p", "08_14_2026_reason_establishment.py assigned the five categories quoted in "
          "Supplementary Methods 2 (169 / 18 / 7 / 38 / 4). It described provenance; it changed "
          "no reason. ⚠ Its labels came from the master CSV, so they inherit its blind spots - "
          "papers TSA and YA did adjudicate appear there as unadjudicated, which is why this "
          "workbook goes back to the screening workbooks instead."),
    ("h", "So: the rationale behind every one of the 236, counted"),
]
r = 2
for kind, text in CHAIN:
    r += 1
    c = wsp.cell(r, 2, text)
    if kind == "h":
        c.font = BOLD
    else:
        c.alignment = WRAP
        wsp.row_dimensions[r].height = 14 * (len(text) // 95 + 1)
r += 1
for i, h in enumerate(["What the rationale on file says", "n", "Where those papers are now"],
                      start=2):
    c = wsp.cell(r, i, h); c.font = H; c.fill = HF
    c.alignment = Alignment(wrap_text=True, vertical="center")
kind_n = collections.Counter(x["basis_kind"] for x in rows)
where = collections.defaultdict(collections.Counter)
LABEL = {"todo": "to determine", "signoff": "to sign off", "settled": "settled"}
for x in rows:
    where[x["basis_kind"]][LABEL[x["state"]]] += 1
for k, v in kind_n.most_common():
    r += 1
    wsp.cell(r, 2, k).alignment = WRAP
    wsp.cell(r, 3, v).alignment = CEN
    wsp.cell(r, 4, " · ".join("%s: %d" % (a, b) for a, b in sorted(where[k].items()))).alignment = WRAP
    if k != "Taken straight from the screening record":
        for i in (2, 3):
            wsp.cell(r, i).fill = FLAG
r += 1
wsp.cell(r, 2, "Total").font = BOLD
wsp.cell(r, 3, 236).font = BOLD
wsp.cell(r, 3).alignment = CEN
r += 2
wsp.cell(r, 2, "⚠ \"Taken straight from the screening record\" is the DEFAULT string, written "
               "for every paper not in an override list. It means no override was applied - not "
               "that anyone checked the paper.").font = Font(italic=True, color="A8471F")
wsp.cell(r, 2).alignment = WRAP
wsp.row_dimensions[r].height = 34

# =============================================================================
# Sheet 6 - where the two files disagree
# =============================================================================
ws6 = wb.create_sheet("Where the files disagree")
ws6.column_dimensions["A"].width = 4
ws6["B1"] = "12 papers where the published column and the audit column disagree"
ws6["B1"].font = TITLE
ws6["B3"] = ("FINAL_reason is what the published counts are built from; RESOLVED_reason is "
             "what the 13 August audit resolved the same paper to. Ten of the twelve are "
             "\"Non-health topic\" against \"Non-human / laboratory\" - a precedence question, "
             "since a computer-science paper is both non-human and non-health - but it moves "
             "papers between two published counts, so it is worth settling once rather than "
             "paper by paper.")
ws6["B3"].alignment = WRAP
ws6.row_dimensions[3].height = 58
C6 = [("PMID", 11), ("PubMed", 9), ("Title", 58), ("Which sheet", 20),
      ("FINAL_reason (published)", 26), ("RESOLVED_reason (audit)", 26),
      ("Which is right?", 24), ("Notes", 26)]
for i, (name, width) in enumerate(C6, start=2):
    ws6.column_dimensions[get_column_letter(i)].width = width
    c = ws6.cell(5, i, name); c.font = H; c.fill = HF
    c.alignment = Alignment(wrap_text=True, vertical="center")
ws6.row_dimensions[5].height = 32
SHEETNAME = {"todo": "65 to determine", "signoff": "9 to sign off", "settled": "162 settled"}
r = 5
for rw in sorted([x for x in rows if x["conflict"]], key=lambda x: (x["state"], x["pmid"])):
    r += 1
    ws6.cell(r, 2, int(rw["pmid"]))
    c = ws6.cell(r, 3, "open"); c.hyperlink = rw["link"]; c.font = LINK
    ws6.cell(r, 4, rw["title"]).alignment = WRAP
    ws6.cell(r, 5, SHEETNAME[rw["state"]])
    ws6.cell(r, 6, rw["final"]).alignment = WRAP
    ws6.cell(r, 7, rw["resolved"]).alignment = WRAP
    ws6.cell(r, 8).fill = IN
    ws6.cell(r, 9).fill = IN
    for i in range(2, len(C6) + 2):
        ws6.cell(r, i).border = THIN
    ws6.row_dimensions[r].height = 30
dropdown(ws6, "H6:H%d" % r)

wb.save(OUT)

# =============================================================================
# The simple fill-in file: the 65, nothing else
#
# Same classification, stripped to what TSA and YA actually have to touch. Where one of
# them already recorded a reason it is pre-filled with their own answer mapped to the six
# categories, so the empty highlighted cell is the only thing to look at. Every reason
# cell carries the same six-item dropdown.
# =============================================================================
SIMPLE = "data/screening/08_21_2026_exclusion_reasons_TO_FILL_65.xlsx"
NEED = {"ta": "TSA to record", "ya": "YA to record",
        "both": "Both to record", "adjudicate": "Agree one between you"}
w2 = Workbook()
s1 = w2.active
s1.title = "65 to fill"
CS = [("#", 5), ("PMID", 11), ("PubMed", 8), ("Title", 66), ("Journal", 22), ("Type", 15),
      ("What is needed", 21), ("TSA reason", 27), ("YA reason", 27),
      ("Agreed final reason", 27), ("Notes", 30)]
s1.append([c[0] for c in CS])
for i, (name, width) in enumerate(CS, start=1):
    s1.column_dimensions[get_column_letter(i)].width = width
    c = s1.cell(1, i)
    c.font = H; c.fill = HF
    c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
s1.row_dimensions[1].height = 30
for i, rw in enumerate(todo, start=1):
    s1.append([i, int(rw["pmid"]), "open", rw["title"], rw["journal"], rw["pubtype"],
               NEED[rw["action"]], rw["ta_cat"], rw["ya_cat"], "", ""])
    r = s1.max_row
    s1.cell(r, 3).hyperlink = rw["link"]; s1.cell(r, 3).font = LINK
    s1.cell(r, 3).alignment = CEN
    for j in range(1, len(CS) + 1):
        c = s1.cell(r, j)
        c.alignment = WRAP if j in (4, 7) else TOP
        c.border = THIN
    # the cells that still need an answer
    for j in (8, 9, 10):
        if not s1.cell(r, j).value:
            s1.cell(r, j).fill = IN
    s1.row_dimensions[r].height = 30
dropdown(s1, "H2:J%d" % s1.max_row)
s1.freeze_panes = "D2"
s1.auto_filter.ref = "A1:K%d" % s1.max_row

s2 = w2.create_sheet("How to fill this in")
s2.column_dimensions["A"].width = 4
s2.column_dimensions["B"].width = 96
s2.column_dimensions["C"].width = 12
s2["B1"] = "How to fill this in"
s2["B1"].font = TITLE
NOTE = [
    "These are the 65 screening exclusions whose reason does not rest on two recorded "
    "screener judgements. The other 171 need nothing from you.",
    "",
    "Yellow cells are the ones to fill. Every reason cell is a dropdown holding the six "
    "categories - click the cell and pick one.",
    "",
    "Where a cell is already filled, that is your own answer from the screening forms, "
    "mapped to the six categories. You are not bound by it.",
    "",
    "\"What is needed\" says whose answer is missing:",
    "      TSA to record        TSA voted to include the paper, or gave only the withdrawn "
    "corresponding-author answer, so no exclusion reason from TSA exists",
    "      YA to record         the same, for YA",
    "      Both to record       neither of you recorded a reason",
    "      Agree one between you    you both recorded a reason and they differ; this was "
    "never adjudicated",
    "",
    "Fill your own column independently, then agree the third. Use Notes for anything that "
    "needs saying, or if none of the six categories fits.",
    "",
    "Filter column G to work through your own rows: TSA has 18 plus the 4 and the 7, YA has "
    "36 plus the 4 and the 7.",
    "",
    "\"Corresponding author was not from a Saudi institution\" is not one of the six. That "
    "criterion was relaxed to \"any Saudi author\" and the answer withdrawn, which is why so "
    "many of these papers are missing a reason from one of you.",
]
r = 2
for t in NOTE:
    r += 1
    c = s2.cell(r, 2, t)
    c.alignment = WRAP
    if t.startswith("      "):
        c.font = Font(size=10)
    s2.row_dimensions[r].height = 14 * (len(t) // 92 + 1)
r += 2
for i, t in enumerate(["The six reason categories", "Current n"], start=2):
    s2.cell(r, i, t).font = H
    s2.cell(r, i).fill = HF
for reason in REASONS:
    r += 1
    s2.cell(r, 2, reason)
    s2.cell(r, 3, SUPP_WORDING[reason][1]).alignment = CEN
r += 2
s2.cell(r, 2, "The full picture - who recorded what, which sheet it came from, and the 9 "
              "papers needing a sign-off rather than a determination - is in "
              "08_21_2026_exclusion_reason_determination_TSA_YA.xlsx.").font = \
    Font(italic=True, size=9, color="666666")
s2.cell(r, 2).alignment = WRAP
w2.save(SIMPLE)

print("wrote", OUT)
print("wrote", SIMPLE, "(the simple one: %d rows)" % len(todo))
print("  to determine  %3d  %s" % (len(todo), dict(nact)))
print("  to sign off   %3d" % len(sign))
print("  settled       %3d" % len(done))
print("  ---")
print("  TSA must record a reason for %d papers; YA for %d; both for %d; %d to adjudicate."
      % (nact["ta"], nact["ya"], nact["both"], nact["adjudicate"]))
