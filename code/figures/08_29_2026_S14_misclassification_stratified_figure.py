# -*- coding: utf-8 -*-
"""Supplementary Figure S14 - Figure 6's group means under misclassification of the item
states, and the spread across groups that the homogeneity claim actually rests on.

    python code/figures/08_29_2026_S14_misclassification_stratified_figure.py

WHAT THIS IS THE SENSITIVITY OF.  Figure 6 reports the validity, transparency and
acknowledgement indices for 25 groups within each task, and the claim it supports is one of
HOMOGENEITY: the group means sit inside a narrow band.  The obvious objection is that
reviewer misclassification manufactured that narrowness, because non-differential error blurs
real between-group differences toward each other.

⚠ NON-DIFFERENTIALITY IS THE CONDITION UNDER WHICH THAT HAPPENS, NOT A DEFENCE AGAINST IT.
Equal error rates across groups are exactly what attenuates a between-group difference toward
the null, so an observed "no difference" is weaker evidence than it looks.  That is why this
figure exists rather than a sentence asserting the stratified display is unaffected.

TWO PANELS, AND PANEL A IS THE ANSWER.
  A  the SPREAD across the 25 groups, observed against corrected, per index and task.  This
     is the quantity the claim is about; no single group mean is.
  B  the 150 group means themselves, laid out exactly as Figure 6 lays them out, so the two
     can be read side by side.  Observed value as a tick, corrected median as a dot, and the
     2.5th to 97.5th percentile of the draws as the bar.

⚠ EVERY HALF-COLUMN IS ZOOMED, AS IN FIGURE 6, and to a WIDER interval than Figure 6 needs,
because the simulation intervals are far wider than the confidence intervals they replace.
The interval each half-column spans is printed at its head, exactly as Figure 6 prints it.

HOUSE RECIPE (as PRISMA / Fig 5 / Fig 6 / S12 / S13): print-native, never converted from HTML;
180 mm wide, nothing below 6.5 pt, Arial embedded, TIFF RGB/LZW at 600 dpi.  The build asserts
the type floor, that no text leaves the canvas, that no two text boxes overlap, that no
interval is clipped by its own axis, and that the observed values reconcile to the published
stratified analysis.

⚠ ONE SOURCE.  Every number is read from the CSVs written by
code/scoring/08_29_2026_stratified_indices_perturbed.R, which itself reads its groups from
the file Figure 6 is built from.  Nothing is re-derived here.

OUTPUT (outputs/figures/)
  08_29_2026_S14_misclassification_stratified.{pdf,tif,png}
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd
from PIL import Image
from pypdf import PdfReader

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_29_2026_S14_misclassification_stratified"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#8b8f94", "#c8ced2"
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM
# same hue-carries-task rule as Figure 6
DTASK = {"Causal": "#0f5c6b", "Descriptive": "#8c5a2b"}
TASKS = ["Causal", "Descriptive"]

# ---------------------------------------------------------------------------- data
KA = dict(keep_default_na=False, na_values=[])     # "None" is the not-ranked JCR LEVEL
G = pd.read_csv("outputs/tables/08_29_2026_stratified_indices_perturbed.csv", **KA)
S = pd.read_csv("outputs/tables/08_29_2026_stratified_spread_perturbed.csv", **KA)
SU = pd.read_csv("data/scoring/07_30_2026_stratified_summary.csv", **KA)

STRATS = [("Saudi data used", ["Yes", "No"]),
          ("Number of authors", ["1-2", "3-10", "11+"]),
          ("% Saudi authors", [">=50%", "<50%"]),
          ("Corresponding author", ["Saudi", "Non-Saudi"]),
          ("First author", ["Saudi", "Non-Saudi"]),
          ("Last author", ["Saudi", "Non-Saudi"]),
          ("Sector composition", ["Academic-only", "Health-system"]),
          ("Single vs multi-sector", ["Single-sector", "Multi-sector"]),
          ("JCR 2022 quartile", ["Q1", "Q2", "Q3", "Q4", "None"]),
          ("Funding", ["Funded", "Declared none", "Not stated"])]
LEVELS = [(nm, lv) for nm, lvs in STRATS for lv in lvs]
assert len(LEVELS) == 25, len(LEVELS)
LVLAB = {">=50%": "\u226550%", "None": "Not ranked", "Academic-only": "Academic only",
         "1-2": "1\u20132", "3-10": "3\u201310"}
lab = lambda v: LVLAB.get(v, v)

IDX = [("validity", "Validity index", "mean_validity"),
       ("transparency", "Transparency index", "mean_transparency"),
       ("acknowledgement", "Acknowledgement index", "mean_ack")]

ROW = lambda ix, nm, lv, t: G[(G["index"] == ix) & (G.stratifier == nm) &
                              (G.level == lv) & (G.task == t)].iloc[0]

# ⚠ the observed values must be Figure 6's, not something this figure re-derived.
worst = 0.0
for ix, _lb, sucol in IDX:
    for nm, lv in LEVELS:
        for t in TASKS:
            pub = float(SU[(SU.stratifier == nm) & (SU.level == lv) &
                           (SU.task == t)].iloc[0][sucol])
            worst = max(worst, abs(pub - float(ROW(ix, nm, lv, t).observed)))
assert worst < 1e-9, ("observed values drift from the published stratified analysis", worst)
print("150 observed group means reconcile to Figure 6's source, worst difference %.2g" % worst)

NCONT = int((G.interval_contains_observed.astype(str).str.upper() == "TRUE").sum())
print("group means whose interval contains the observed value: %d of %d" % (NCONT, len(G)))
CRUDE = {r["index"]: float(r.observed_spread) for _, r in S.iterrows()
         if r.task == "Both (crude pooling)"}
SCONT = sum(1 for _, r in S.iterrows()
            if float(r.lo) <= float(r.observed_spread) <= float(r.hi))
print("spreads whose interval contains the observed spread: %d of %d" % (SCONT, len(S)))

# zoom range per (index, task) half-column: everything drawn must fit inside it
RNG = {}
for ix, _lb, _c in IDX:
    for t in TASKS:
        z = G[(G["index"] == ix) & (G.task == t)]
        lo = min(z.lo.min(), z.observed.min())
        hi = max(z.hi.max(), z.observed.max())
        pad = (hi - lo) * 0.06
        RNG[(ix, t)] = (lo - pad, hi + pad)

# ---------------------------------------------------------------------------- layout
L, R = 8.0, 3.0
RH, GH, GAP = 2.7, 3.4, 0.8
LBL = 38.0
CW = (W - L - R - LBL) / 3.0
GIN, GOUT = 4.0, 4.0
HW = (CW - GIN - GOUT) / 2.0
CX = [L + LBL + j * CW for j in range(3)]

SPR_RH = 3.0
# ⚠ THE TASK-COMBINED ROW IS STANDARDISED, NOT CRUDELY POOLED (TSA, 2026-08-29). Crude
# pooling takes the range over all 50 means as 50 numbers, and most of that span is the gap
# BETWEEN tasks rather than heterogeneity between groups. The crude value is computed and
# named in the footer so the difference is a measured quantity, but it is not plotted.
SPR_TASKS = ["Causal", "Descriptive", "Both (standardised)"]
SPR_ROWS = [(ix, t) for ix, _lb, _c in IDX for t in SPR_TASKS]
yA = 33.0
endA = yA + len(SPR_ROWS) * SPR_RH + 3 * 3.0 + 2 * 2.0   # + one label row per index
yB = endA + 22.0
H_ROWS = sum(GH + len(lvs) * RH + GAP for _nm, lvs in STRATS)
endB = yB + 11.0 + H_ROWS
H = endB + 30.0

fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")


def T(x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="center"):
    assert pt >= MIN_PT - 1e-9, ("type floor", pt, s)
    return ax.text(x, y, s, fontsize=pt, color=c, ha=ha, va=va, fontweight=weight, zorder=6)


def ln(x0, y0, x1, y1, c, lw, z=3, alpha=1.0):
    ax.plot([x0, x1], [y0, y1], color=c, lw=lw, zorder=z, alpha=alpha, solid_capstyle="butt")


# ---------------------------------------------------------------------------- header
T(L, 7.0, "Group means under misclassification of the item states", pt=T_TITLE, weight="bold")
for k, s in enumerate([
        "Figure 6 reports the indices as recorded. Here every item state is perturbed by the "
        "concordant error rates measured in the calibration",
        "rounds, on both axes together, over 2,000 draws with each rate redrawn from its "
        "paper-clustered interval, and the indices recomputed.",
        "Hue carries task and nothing else."]):
    T(L, 13.0 + k * line_h(T_HEAD), s, pt=T_HEAD, c=MUT)

# ---------------------------------------------------------------------------- panel A
T(L, yA - 9.0, "A", pt=T_HEAD, weight="bold")
T(L + 5.0, yA - 9.0, "Spread across the 25 groups: the quantity the homogeneity claim is about",
  pt=T_HEAD, weight="bold")
SPX0, SPW = L + 54.0, W - R - (L + 54.0) - 22.0
smax = max(float(r.hi) for _, r in S.iterrows()
           if r.task in SPR_TASKS) * 1.06
smap = lambda v: SPX0 + v / smax * SPW
for g in (0.0, 0.05, 0.10, 0.15, 0.20, 0.25):
    if g <= smax:
        ln(smap(g), yA - 2.0, smap(g), endA - 3.0, RULE, 0.4, 1)
        T(smap(g), yA - 4.2, "%.2f" % g, pt=T_SMALL, c=FAINT, ha="center")

y = yA
for bi, (ix, lb, _c) in enumerate(IDX):
    # ⚠ the index label is its own ROW, not a label beside the first task row: at 6.8 pt
    # "Transparency index" is wider than the 22 mm gutter and landed on "Causal".
    T(L, y + 1.0, lb, pt=T_BODY, weight="bold")
    y += 3.0
    for t in SPR_TASKS:
        r = S[(S["index"] == ix) & (S.task == t)].iloc[0]
        obs, cor, lo, hi = (float(r.observed_spread), float(r.corrected_spread),
                            float(r.lo), float(r.hi))
        for v in (obs, cor, lo, hi):
            assert 0 <= v <= smax, ("spread outside its axis", ix, t, v)
        c = DTASK.get(t, INK)
        T(L + 4.0, y + 1.0, t, pt=T_SMALL, c=c)
        ln(smap(lo), y + 1.0, smap(hi), y + 1.0, c, 1.2, 3, 0.55)
        ax.plot([smap(cor)], [y + 1.0], marker="o", ms=2.8, color=c, zorder=5)
        ln(smap(obs), y - 0.15, smap(obs), y + 2.15, INK, 1.0, 5)
        T(W - R, y + 1.0, "%.3f \u2192 %.3f" % (obs, cor), pt=T_SMALL, c=MUT, ha="right")
        y += SPR_RH
    if bi < 2:
        y += 2.0

ln(L, endA + 3.0, W - R, endA + 3.0, RULE, 0.5)
T(L, endA + 6.0,
  "Vertical rule = the spread Figure 6 shows. Dot = corrected median, bar = 2.5th to 97.5th "
  "percentile. All %d intervals contain the observed spread," % len(S),
  pt=T_SMALL, c=MUT)
T(L, endA + 6.0 + line_h(T_SMALL),
  "so misclassification at the measured rates does not account for the narrowness.",
  pt=T_SMALL, c=MUT)

# ---------------------------------------------------------------------------- panel B
T(L, yB - 9.0, "B", pt=T_HEAD, weight="bold")
T(L + 5.0, yB - 9.0, "The 150 group means, laid out as Figure 6 lays them out",
  pt=T_HEAD, weight="bold")
y = yB
for j, (ix, lb, _c) in enumerate(IDX):
    T(CX[j], y, lb, pt=T_HEAD, c=INK, weight="bold")
T(L, y, "Group", pt=T_HEAD, c=FAINT, weight="bold")
yh = y + line_h(T_HEAD) + 1.2
for j, (ix, _lb, _c) in enumerate(IDX):
    for k, t in enumerate(TASKS):
        x0 = CX[j] + k * (HW + GIN)
        a, b = RNG[(ix, t)]
        T(x0 + HW / 2, yh, "%s  %.2f\u2013%.2f" % (t[0], a, b), pt=T_SMALL,
          c=DTASK[t], ha="center")
y = yB + 11.0
ln(L, y - 1.4, W - R, y - 1.4, INK, 0.7)

for nm, lvs in STRATS:
    T(L, y, nm, pt=T_BODY, weight="bold")
    y += GH
    for lv in lvs:
        cy = y + RH / 2 - 0.3
        T(L + 1.5, cy, lab(lv), pt=T_SMALL, c=MUT)
        for j, (ix, _lb, _c) in enumerate(IDX):
            for k, t in enumerate(TASKS):
                x0 = CX[j] + k * (HW + GIN)
                a, b = RNG[(ix, t)]
                sx = lambda v: x0 + (v - a) / (b - a) * HW
                r = ROW(ix, nm, lv, t)
                obs, cor = float(r.observed), float(r.corrected)
                lo, hi = float(r.lo), float(r.hi)
                for v in (obs, cor, lo, hi):
                    assert a - 1e-9 <= v <= b + 1e-9, ("clipped by its own axis", ix, t, lv, v)
                ln(sx(lo), cy, sx(hi), cy, DTASK[t], 0.6, 4, 0.5)
                ax.add_patch(Circle((sx(cor), cy), 0.52, fc=DTASK[t], ec="none", zorder=6))
                ln(sx(obs), cy - 0.95, sx(obs), cy + 0.95, INK, 0.6, 7)
        y += RH
    ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
    y += GAP

# ---------------------------------------------------------------------------- footer
yf = endB + 4.0
ln(L, yf - 3.0, W - R, yf - 3.0, RULE, 0.5)
FOOT = [
    "310 scored studies (229 causal, 81 descriptive). Groups, levels and their order are "
    "Figure 6's, read from the same file, so the two figures cannot be",
    "grouping papers differently. Within each half-column the vertical rule is the value "
    "Figure 6 plots, the dot is the corrected median, and the bar runs from",
    "the 2.5th to the 97.5th percentile of 2,000 draws. Every half-column is magnified to the "
    "interval printed at its head, wider than Figure 6's because",
    "simulation intervals are wider than the confidence intervals they replace. All %d of the "
    "%d group-mean intervals contain their observed value, as do" % (NCONT, len(G)),
    "all %d spread intervals in panel A, so the correction and the uncorrected display are not "
    "distinguishable once parameter uncertainty is propagated;" % len(S),
    "that is a failure to demonstrate a difference, not a demonstration that reviewer error is "
    "absent. The task-combined row of panel A weights each group's",
    "two task means by the sample's own split of 229 causal to 81 descriptive, as "
    "Supplementary Figure S12 does; crude pooling would instead report %.3f, %.3f"
    % (CRUDE["validity"], CRUDE["transparency"]),
    "and %.3f, roughly double each, because most of that span is the gap between the two "
    "tasks rather than heterogeneity between groups. Parameters are in" % CRUDE["acknowledgement"],
    "Supplementary Methods 7. Built by "
    "code/figures/08_29_2026_S14_misclassification_stratified_figure.py.",
]
for k, ln_ in enumerate(FOOT):
    T(L, yf + k * line_h(T_SMALL), ln_, pt=T_SMALL, c=MUT)

# ---------------------------------------------------------------------------- assertions
fig.canvas.draw()
rend = fig.canvas.get_renderer()
inv = ax.transData.inverted()
boxes = []
for t in ax.texts:
    bb = t.get_window_extent(rend)
    (xa, ya), (xb, yb) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
    x0_, x1_ = min(xa, xb), max(xa, xb)
    y0_, y1_ = min(ya, yb), max(ya, yb)
    assert x0_ >= -0.5 and x1_ <= W + 0.5, ("text leaves the canvas", t.get_text())
    assert y0_ >= -0.5 and y1_ <= H + 0.5, ("text leaves the canvas", t.get_text())
    boxes.append((x0_, y0_, x1_, y1_, t.get_text()))

PAD = 0.3
for i in range(len(boxes)):
    for j in range(i + 1, len(boxes)):
        a, b = boxes[i], boxes[j]
        if (a[0] < b[2] - PAD and b[0] < a[2] - PAD
                and a[1] < b[3] - PAD and b[1] < a[3] - PAD):
            raise AssertionError("text boxes overlap:\n    %r\n    %r" % (a[4], b[4]))

os.makedirs(OUTDIR, exist_ok=True)
base = os.path.join(OUTDIR, STEM)
fig.savefig(base + ".pdf", format="pdf")
fig.savefig(base + ".png", dpi=600)
Image.open(base + ".png").save(base + ".tif", compression="tiff_lzw", dpi=(600, 600))
plt.close(fig)

pg = PdfReader(base + ".pdf").pages[0]
print("\n%.1f x %.1f mm" % (float(pg.mediabox.width) * 25.4 / 72, float(pg.mediabox.height) * 25.4 / 72))
for e in ("pdf", "tif", "png"):
    print("  %-66s %8.1f KB" % (base + "." + e, os.path.getsize(base + "." + e) / 1024))
