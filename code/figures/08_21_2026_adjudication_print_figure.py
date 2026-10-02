# -*- coding: utf-8 -*-
"""Figure 3 (adjudication) as a submission-ready journal figure: PDF, TIFF, PNG.

    python code/figures/08_21_2026_adjudication_print_figure.py

WHAT IT SHOWS, AND WHY ONLY THIS
The process report behind this figure runs to eight sections. A manuscript figure can
carry two things, and the legend already names them: the flow from grid to final call,
and what adjudication did to the reviewers' answers.

  Panel A  the flow, starting one step earlier than the report does. 18,095 -> 7,278 is
           the step that most needs to be visible: "69% agreement" is unreadable without
           the denominator, because the same data computed across the whole grid would
           read about 88%. Showing that the smaller, harsher denominator was used is the
           strongest single thing this figure can do.
  Panel B  what the 2,257 disputes became. 84.5% of the rulings reproduced an answer one
           of the reviewers had already given, which is the answer to "two people imposed
           their own view on 2,257 cells".

Everything else - per-item disagreement rates, workload per paper, the two adjudicators
compared, the phase-II asymmetry, the position/identity confound - belongs in
Supplementary Methods, not here. Two of those are self-criticisms and must survive the
move rather than disappear in it.

⚠ THE 145 ARE NOT AN OUTSTANDING TASK
The process report files 145 routed cells as "Still unresolved". They are cells where one
reviewer answered an item and the other marked it not applicable - a disagreement about
whether the question applies. They never went to adjudication: they went to the skip-logic
GAP/EXTRA workstream, which closed on 2026-08-12 (45 gap fills + 6 conf_var_det, tagged
`worklist-2026-08-12`). For the rest, BLANK IS THE CORRECT FINAL VALUE, so nothing needed
rewriting and the `unresolved` source tag was never replaced - and the process analysis has
no verdict category for "not applicable", so it prints them as still unresolved.

Confirmed two ways: the disposition on record at N=377 ("146 are skip-logic disagreements
... only 3 were genuine, and all 3 self-resolve" - the two `conf_var_det` cells closing
under Ruling 3, randomization-only), and `code/pipeline/_check_contradictions.py` reporting
**GAP = 0, EXTRA = 0** on the canonical dataset: no cell the skip logic says should have
been answered is blank. Per-cell evidence:
data/adjudication/08_21_2026_unresolved_145_cells.xlsx
⚠ Do not re-derive this from the scorer alone: score_dataset_lib.R does not model
`comp_dis` applicability, which leaves 18 cells looking open when they are not.

⚠ READING THE SOURCE CSV: it is written by R, so a missing value is a BARE `NA` while a
recorded answer is quoted. Reading it without that distinction turns 145 missing rulings
into 145 recorded "NA" answers and inverts the finding. Counts here come from the
pre-computed status/phase1/verdict columns, which are quoted strings, and `p2` is the one
place the bare-NA rule is applied explicitly.

OUTPUT (outputs/figures/)  08_21_2026_adjudication_flow.{pdf,tif,png}
"""
import csv, os, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_21_2026_adjudication_flow"
SRC = "data/adjudication/process-tables/cell_level_detail.csv"

matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})
PT2MM = 25.4 / 72.0
W = 180.0

INK, MUT, AC = "#111417", "#4a5259", "#0f5c6b"
BD, FILL = "#9aa3a9", "#ffffff"
GREY_F, GREY_B = "#f2f0ec", "#9aa3a9"
AMF, AMB, AMT = "#f6ead7", "#b57f2a", "#7a4d0d"
ARR = "#6f787e"
BAR = {"first": "#2c7f92", "second": "#5aa8b8", "over": "#c9922f", "none": "#b9c0c4"}

T_TITLE, T_HEAD, T_SUB, T_NUM, T_SMALL, T_BAND = 9.5, 7.5, 6.6, 8.5, 6.5, 6.8
LEAD, PADX, PADY = 1.30, 2.6, 2.2
SPINE_X, SPINE_W = 12.0, 66.0
SIDE_X, SIDE_W = 82.0, 96.0
SPINE_CX = SPINE_X + SPINE_W / 2
RAIL_X = 5.0
line_h = lambda pt: pt * LEAD * PT2MM
box_h = lambda rows: PADY * 2 + sum(line_h(r[1]) for r in rows)


# =============================================================================
# Counts, read from the data rather than typed in
# =============================================================================
rows = list(csv.reader(open(SRC, encoding="utf-8-sig")))
hdr, cd = rows[0], [dict(zip(rows[0], r)) for r in rows[1:] if r]
status = collections.Counter(x["status"] for x in cd)
routed = [x for x in cd if x["status"].startswith("Disagreed")]
phase1 = collections.Counter(x["phase1"] for x in routed)
verdict = collections.Counter(x["verdict"] for x in routed)
# `p2` is bare NA when the cell never reached the joint sitting - see the header note
in_p2 = sum(1 for x in routed if x["p2"] not in ("", "NA"))
p2_from_discord = sum(1 for x in routed
                      if x["p2"] not in ("", "NA") and x["phase1"].startswith("Phase I discordant"))
p2_from_single = in_p2 - p2_from_discord

GRID = len(cd)
NA_BOTH = status["Not applicable to either reviewer"]
ASSESSED = GRID - NA_BOTH
AGREED = status["Reviewers agreed"]
ROUTED = len(routed)
CONFLICT = status["Disagreed on the answer"]
APPLIC = status["Disagreed on applicability"]
CONCORD = phase1["Phase I concordant (TA = YA)"]
DISCORD = phase1["Phase I discordant -> phase II"]
ONECALL = phase1["Only one adjudicator recorded a call"]
UP1 = verdict["Upheld the first reviewer"]
UP2 = verdict["Upheld the second reviewer"]
OVER = verdict["Overrode both reviewers"]
NONE = verdict["Still unresolved"]
RULED = UP1 + UP2 + OVER
assert AGREED + ROUTED == ASSESSED and CONFLICT + APPLIC == ROUTED
assert CONCORD + DISCORD + ONECALL == ROUTED and RULED + NONE == ROUTED
PAPERS, ITEMS = 385, GRID // 385
pc = lambda n, d: 100.0 * n / d
f = lambda n: "{:,}".format(n)


class Fig:
    def __init__(self, h):
        self.fig = plt.figure(figsize=(W / 25.4, h / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(h, 0); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, h, fc="white", ec="none", zorder=0))

    def rect(self, x, y, w, h, fc=FILL, ec=BD, lw=0.5, r=1.4, z=2):
        self.ax.add_patch(FancyBboxPatch((x + r, y + r), w - 2 * r, h - 2 * r,
            boxstyle="round,pad=%.3f,rounding_size=%.3f" % (r, r),
            fc=fc, ec=ec, lw=lw, zorder=z, mutation_aspect=1))

    def text(self, x, y, s, pt=T_SUB, c=INK, weight="normal", ha="left", z=4, va="top"):
        self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)

    def box(self, x, y, w, rows, fc=FILL, ec=BD):
        h = box_h(rows); self.rect(x, y, w, h, fc, ec)
        ty = y + PADY
        for r in rows:
            s, pt, c, wt = r[:4]
            self.text(x + PADX, ty, s, pt, c, wt)
            if len(r) > 4 and r[4]:
                self.text(x + w - PADX, ty, r[4], pt, INK, "bold", ha="right")
            ty += line_h(pt)
        return h

    def arrow(self, x1, y1, x2, y2, colour=ARR, lw=0.6, dashed=False):
        self.ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
            mutation_scale=5.0, lw=lw, color=colour, zorder=3, shrinkA=0, shrinkB=0,
            linestyle=(0, (2.2, 1.6)) if dashed else "solid"))

    def side_arrow(self, y_top, h_spine):
        y = y_top + h_spine / 2
        self.arrow(SPINE_X + SPINE_W, y, SIDE_X, y)

    def band(self, y0, y1, label):
        self.ax.add_patch(Rectangle((RAIL_X, y0), 1.1, y1 - y0, fc=AC, ec="none",
                                    alpha=0.9, zorder=2))
        self.ax.text(RAIL_X - 1.0, (y0 + y1) / 2, label.upper(), fontsize=T_BAND, color=AC,
                     fontweight="bold", ha="center", va="center", rotation=90, zorder=4)


# =============================================================================
# Content
# =============================================================================
GRIDB = [("Judgement cells in the grid", T_HEAD, INK, "bold"),
         ("%d papers × %d instrument items" % (PAPERS, ITEMS), T_SUB, MUT, "normal"),
         ("n = " + f(GRID), T_NUM, INK, "bold")]
NEVER = [("Never asked: the instrument branches", T_SUB, MUT, "bold", f(NA_BOTH)),
         ("a descriptive paper is never asked the causal items, so these cells", T_SMALL, MUT, "normal"),
         ("were put to neither reviewer", T_SMALL, MUT, "normal")]
ASSESSB = [("Assessed: at least one reviewer answered", T_HEAD, INK, "bold"),
           ("the denominator for every agreement statistic reported", T_SUB, MUT, "normal"),
           ("n = " + f(ASSESSED), T_NUM, AC, "bold")]
AGREEB = [("Reviewers agreed outright", T_SUB, MUT, "bold", "%s  (%.1f%%)" % (f(AGREED), pc(AGREED, ASSESSED))),
          ("never re-examined; adjudication was triggered only by disagreement", T_SMALL, MUT, "normal")]
ROUTEB = [("Routed to adjudication", T_HEAD, INK, "bold"),
          ("n = " + f(ROUTED), T_NUM, AC, "bold")]
TYPEB = [("Two kinds of dispute", T_SUB, MUT, "bold"),
         ("conflicting answers: both answered, the answers differ", T_SMALL, MUT, "normal", f(CONFLICT)),
         ("applicability: one answered, the other judged the item not to apply", T_SMALL, MUT, "normal", f(APPLIC))]
P1B = [("Phase I: TSA and YA ruled independently", T_HEAD, INK, "bold"),
       ("blinded to reviewer identity, both responses visible", T_SUB, MUT, "normal")]
## Concordance is quoted on the cells where BOTH adjudicators ruled, which is the
## denominator the process report uses. Quoting it over all routed cells instead would
## give a different number for the same fact and read as a discrepancy with the supplement.
BOTH_RULED = CONCORD + DISCORD
P1S = [("Outcome of the independent pass", T_SUB, MUT, "bold"),
       ("agreed with each other, on the " + f(BOTH_RULED) + " cells both of them ruled",
        T_SMALL, MUT, "normal", "%s  (%.1f%%)" % (f(CONCORD), pc(CONCORD, BOTH_RULED))),
       ("differed, and went to phase II", T_SMALL, MUT, "normal", f(DISCORD)),
       ("only one of them recorded a ruling", T_SMALL, MUT, "normal", f(ONECALL))]
P2B = [("Phase II: joint resolution", T_HEAD, INK, "bold"),
       ("%s cells taken to a joint sitting: %s where phase I differed" % (f(in_p2), f(p2_from_discord)), T_SUB, MUT, "normal"),
       ("and %d where only one adjudicator had ruled" % p2_from_single, T_SUB, MUT, "normal")]
FINB = [("Final adjudicated dataset", T_HEAD, "#ffffff", "bold"),
        ("%s rulings: every applicable cell" % f(RULED), T_NUM, "#ffffff", "bold"),
        ("used as the reference standard for every analysis", T_SMALL, "#d9e9ec", "normal")]
## The split is computed, not typed: an item whose task prefix differs from the paper's
## adjudicated task was never asked at all; the rest are ruled out by an answer upstream.
NA_OTHER_TASK = sum(1 for x in routed if x["verdict"] == "Still unresolved"
                    and x["variable"].split("_", 1)[0] != x["Study_Type"].lower())
NA_GATED = NONE - NA_OTHER_TASK
NOB = [("Not applicable: no ruling required", T_SUB, MUT, "bold",
        "%s  (%.1f%%)" % (f(NONE), pc(NONE, ROUTED))),
       ("one reviewer answered an item the instrument does not ask for that paper:", T_SMALL, MUT, "normal"),
       ("%d belong to a task block the paper is not in, %d sit under an answer that rules the item out"
        % (NA_OTHER_TASK, NA_GATED), T_SMALL, MUT, "normal")]

GAP, TOP = 5.0, 15.0


def layout():
    y, cur = {}, TOP
    for key, spine, side in (("grid", GRIDB, NEVER), ("assess", ASSESSB, AGREEB),
                             ("route", ROUTEB, TYPEB), ("p1", P1B, P1S),
                             ("p2", P2B, None), ("final", FINB, NOB)):
        y[key] = cur
        cur += max(box_h(spine), box_h(side) if side else 0) + GAP
    y["bar"] = cur + 4.0
    return y["bar"] + 26.0, y


H, Y = layout()
fg = Fig(H)
fg.text(SPINE_X, 4.0, "Adjudication of reviewer disagreements", T_TITLE, INK, "bold")
fg.text(SPINE_X, 4.0 + line_h(T_TITLE),
        "Every cell in which the two reviewers differed, and what the two adjudicators did with it",
        T_SUB, MUT)

h_grid = fg.box(SPINE_X, Y["grid"], SPINE_W, GRIDB)
h_nev = fg.box(SIDE_X, Y["grid"], SIDE_W, NEVER, fc=GREY_F, ec=GREY_B)
fg.side_arrow(Y["grid"], h_grid)

h_ass = fg.box(SPINE_X, Y["assess"], SPINE_W, ASSESSB)
fg.box(SIDE_X, Y["assess"], SIDE_W, AGREEB, fc=GREY_F, ec=GREY_B)
fg.arrow(SPINE_CX, Y["grid"] + h_grid, SPINE_CX, Y["assess"])
fg.side_arrow(Y["assess"], h_ass)

h_rt = fg.box(SPINE_X, Y["route"], SPINE_W, ROUTEB)
fg.box(SIDE_X, Y["route"], SIDE_W, TYPEB, fc=GREY_F, ec=GREY_B)
fg.arrow(SPINE_CX, Y["assess"] + h_ass, SPINE_CX, Y["route"])
fg.side_arrow(Y["route"], h_rt)

h_p1 = fg.box(SPINE_X, Y["p1"], SPINE_W, P1B)
fg.box(SIDE_X, Y["p1"], SIDE_W, P1S, fc=GREY_F, ec=GREY_B)
fg.arrow(SPINE_CX, Y["route"] + h_rt, SPINE_CX, Y["p1"])
fg.side_arrow(Y["p1"], h_p1)

h_p2 = fg.box(SPINE_X, Y["p2"], SPINE_W, P2B)
fg.arrow(SPINE_CX, Y["p1"] + h_p1, SPINE_CX, Y["p2"])

h_fin = fg.box(SPINE_X, Y["final"], SPINE_W, FINB, fc=AC, ec=AC)
fg.box(SIDE_X, Y["final"], SIDE_W, NOB, fc=GREY_F, ec=GREY_B)
fg.arrow(SPINE_CX, Y["p2"] + h_p2, SPINE_CX, Y["final"])
fg.side_arrow(Y["final"], h_fin)

fg.band(Y["grid"], Y["grid"] + h_grid, "Grid")
fg.band(Y["assess"] - 0.5, Y["route"] + h_rt + 0.5, "Agreement")
fg.band(Y["p1"] - 0.5, Y["p2"] + h_p2 + 0.5, "Adjudication")
fg.band(Y["final"] - 0.5, Y["final"] + h_fin + 0.5, "Reference")

# =============================================================================
# Panel B — what became of the 2,257
# =============================================================================
by = Y["bar"]
fg.text(SPINE_X, by, "What adjudication did to the reviewers' answers", T_HEAD, INK, "bold")
fg.text(SPINE_X, by + line_h(T_HEAD),
        "All %s routed cells. %.1f%% of the %s rulings reproduced an answer one of the reviewers had already given."
        % (f(ROUTED), pc(UP1 + UP2, RULED), f(RULED)), T_SUB, MUT)

bar_y = by + line_h(T_HEAD) + line_h(T_SUB) + 3.0
bar_x, bar_w, bar_h = SPINE_X, W - SPINE_X - 12.0, 7.0
segs = [("Upheld the first reviewer", UP1, BAR["first"], "#ffffff"),
        ("Upheld the second reviewer", UP2, BAR["second"], "#ffffff"),
        ("Overrode both: a third answer", OVER, BAR["over"], "#ffffff"),
        ("Not applicable", NONE, BAR["none"], INK)]
x = bar_x
for lab, n, col, txtc in segs:
    w = bar_w * n / ROUTED
    fg.ax.add_patch(Rectangle((x, bar_y), w, bar_h, fc=col, ec="white", lw=0.6, zorder=2))
    # 8 mm is enough for "145" over "6.4%" at 6.5 pt; the narrowest segment here is 10 mm,
    # so every category carries its own count rather than leaving the reader to subtract
    if w > 8:
        fg.ax.text(x + w / 2, bar_y + bar_h / 2, "%s\n%.1f%%" % (f(n), pc(n, ROUTED)),
                   fontsize=T_SMALL, color=txtc, ha="center", va="center", zorder=4,
                   fontweight="bold", linespacing=1.25)
    x += w
# legend under the bar, one row. The swatch is 2.6 mm tall and the label is centred on
# it vertically - hanging the label from the swatch's top edge leaves the text riding high.
lx, sw = bar_x, 2.6
sw_y = bar_y + bar_h + 2.8
for lab, n, col, _ in segs:
    fg.ax.add_patch(Rectangle((lx, sw_y), sw, sw, fc=col, ec="none", zorder=2))
    fg.text(lx + sw + 1.4, sw_y + sw / 2, lab, T_SMALL, MUT, va="center")
    lx += sw + 1.4 + len(lab) * T_SMALL * 0.48 * PT2MM + 5.0

# =============================================================================
# Write and self-check
# =============================================================================
base = os.path.join(OUTDIR, STEM)
fg.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
fg.fig.savefig(base + ".png", dpi=600, facecolor="white")
from PIL import Image
_p = Image.open(base + ".png")
_rgb = Image.new("RGB", _p.size, "white")
_rgb.paste(_p, mask=_p.split()[3] if _p.mode == "RGBA" else None)
_rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
_p.close(); plt.close(fg.fig)

from pypdf import PdfReader
_r = PdfReader(base + ".pdf")
for _k, _v in _r.pages[0]["/Resources"]["/Font"].items():
    _fo = _v.get_object(); _df = _fo.get("/DescendantFonts")
    _d = _df[0].get_object() if _df else _fo
    _desc = _d.get("/FontDescriptor")
    assert _d.get("/Subtype") != "/Type3" and _desc and any(
        x in _desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), _fo.get("/BaseFont")
_t = Image.open(base + ".tif")
assert _t.mode == "RGB" and _t.tag_v2[259] == 5 and _t.info["dpi"] == (600.0, 600.0)
_t.close()

for ext in ("pdf", "png", "tif"):
    p = base + "." + ext
    print("  %-54s %7.1f KB" % (p, os.path.getsize(p) / 1024))
print("  %.0f x %.0f mm · smallest type %.1f pt · PDF fonts embedded, TIFF RGB/LZW" % (W, H, T_SMALL))
print("  census: %s grid · %s assessed · %s agreed · %s routed · %s ruled · %s without a ruling"
      % (f(GRID), f(ASSESSED), f(AGREED), f(ROUTED), f(RULED), f(NONE)))
