# -*- coding: utf-8 -*-
"""Supplementary Figure S13 - Figure 5's domain prevalences under misclassification of the
item states, with the tipping point and the parameters that drive both.

    python code/figures/08_29_2026_S13_misclassification_overall_figure.py

WHAT THIS IS THE SENSITIVITY OF.  Figure 5 panels A-C report, per domain and task, how many
of the 310 scored studies carry a validity flaw and how many a reporting gap.  Those verdicts
are themselves measured with error: two reviewers read every paper, they agreed on 69.0% of
cells, and adjudication was triggered ONLY by disagreement, so the cells they agreed on were
almost never checked.  This figure asks what the prevalences would be if the agreeing pairs
carried the concordant error rate measured in the calibration rounds.

⚠ THIS IS A SECOND, DIFFERENT SENSITIVITY ANALYSIS, AND THE CAPTION SAYS SO.  Figure 5 panel C
already carries one: the worst-case bound obtained by recoding every reporting gap as a
validity flaw.  That is assumption-free bookkeeping about REPORTING.  This one is about
MISCLASSIFICATION, it needs measured parameters, and the two answer different objections.
Conflating them in the text would be the easiest mistake a reader could make.

TWO PANELS.
  A  baseline against corrected prevalence, both axes, with the 95% simulation interval.
  B  the tipping point: how far the concordant false-positive rate would have to be from the
     rate actually measured before a quantity fell below 70%, 50% and 25%.

⚠ PANEL B'S LAST TWO ROWS ARE THE ONES THE OBJECTION IS ABOUT.  A reviewer complaining about
69% agreement is not asking about one domain; the complaint is "maybe the literature is fine
and you are reading your own noise".  So the paper's two headline claims sit on the same axis
as the domains: every study carrying a validity flaw needs a rate of 0.79 before it drops
below 70%, against a measured maximum of 0.286.  The shaded band is that measured envelope,
and it is drawn so the comparison is made once, visually.  ⚠ "Three or more domains" is the
soft claim and the figure says so: its 70% rung sits INSIDE the band.
⚠ The headline rows force EVERY domain to the same rate at once, which is a simplification -
0.79 is twelve times the rate measured in measurement bias and 2.8 times the largest measured
anywhere.  The per-domain rows above are the finer statement.
⚠ THE PARAMETER TABLE IS NOT A PANEL HERE.  It was, until the panels were split by task on
2026-08-29 and the page ran to 294 mm.  The same table, with more detail, is Supplementary
Methods 7, so the figure carries the RESULT and the supplement carries the parameters.  What a
reader still needs at a glance - which corrections rest on a measured rate and which on a
borrowed one - is carried by marker shape in both panels and named in the notes.

⚠ THE ONE INTERVAL THAT EXCLUDES ITS BASELINE IS THE ONE WITH A BORROWED PARAMETER.
Confounding bias in causal studies, baseline 87.8%, corrects to 66.4% [22.3, 87.3].  Every
other row's interval contains its baseline.  Confounding was flagged by the reference in every
applicable calibration cell, so its false-positive rate is not estimable and is imputed from
selection bias: the open marker says so in panel A, and panel B carries the assumption-free
statement in its place.  Say it in that order, or it reads as a finding rather than as an
artefact of the imputation.

⚠ NOTHING IS LABELLED IN THE MARGIN BESIDE A ROW.  The first build wrote "IMPUTED" and
"interval excludes the observed value" to the right of each panel-A column; at 180 mm the
left column's notes landed inside the right column and struck through its text.  Status is
carried by MARKER SHAPE and explained once, under the panel.  The overlap assertion below is
what caught it, and it is the assertion this figure most needs: the canvas check only sees
text leaving the page, never two labels landing on each other.

HOUSE RECIPE (as PRISMA / Fig 5 / Fig 6 / S12): print-native, never converted from HTML; 180 mm
wide, nothing below 6.5 pt, Arial embedded, TIFF RGB/LZW at 600 dpi.  The build asserts the type
floor, that no text leaves the canvas, that no two text boxes overlap, that no interval is drawn
outside its own axis, and that every by-task baseline reconciles to the published scored dataset.

⚠ ONE SOURCE.  Every number is read from the CSVs written by
code/scoring/08_29_2026_bias_analysis_by_task.R (panel A and the domain rows of panel B),
code/scoring/08_29_2026_can_error_explain_it_away.R (the two headline rows of panel B) and
code/scoring/08_19_2026_calibration_flag_level_epsilon.R (the parameters and the measured
band).  Nothing is re-derived here.

OUTPUT (outputs/figures/)
  08_29_2026_S13_misclassification_overall.{pdf,tif,png}
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
from PIL import Image
from pypdf import PdfReader

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_29_2026_S13_misclassification_overall"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#8b8f94", "#c8ced2"
VALC, REPC = "#0f5c6b", "#8c5a2b"          # validity axis / reporting axis
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM

# ---------------------------------------------------------------------------- data
KA = dict(keep_default_na=False, na_values=["NA", ""])
# ⚠ BY TASK, NOT POOLED (TSA, 2026-08-29). Figure 5 panels A-C are "by domain and study
# task", and the Abstract quotes the CAUSAL figures - measurement bias 100%, confounding
# 87.8%, selection bias 79.9%. Pooled those read 99.7%, 87.8% and 76.8%, so correcting the
# pooled numbers was a sensitivity analysis of numbers adjacent to the paper's claims.
# Pooling is also the operation the Methods reject, and for prevalence it is not even a
# weighted average of the two task rates at the sample's mix: random error applies to 190
# causal and 55 descriptive studies, not 229 and 81.
BA = pd.read_csv("outputs/tables/08_29_2026_bias_analysis_by_task.csv", **KA)
TP = pd.read_csv("outputs/tables/08_29_2026_tipping_point_by_task.csv", **KA)
FL = pd.read_csv("outputs/tables/08_19_2026_calibration_flag_level_by_domain.csv", **KA)
IMP = pd.read_csv("outputs/tables/08_19_2026_calibration_imputed_parameters.csv", **KA)
IMP = IMP[IMP.donor_pool == "usable VAL cells"]

DOMS = ["Random error", "Selection bias", "Measurement bias", "Confounding bias",
        "Missing data", "Mentioning errors", "Conflating task"]
assert set(BA.domain) == set(DOMS), sorted(set(BA.domain) ^ set(DOMS))
TASKS_ = ["Causal", "Descriptive"]
ROWS_A = [(dm, tk) for dm in DOMS for tk in TASKS_
          if len(BA[(BA.domain == dm) & (BA.task == tk)])]
assert len(ROWS_A) == 12, len(ROWS_A)

# ⚠ the baselines must be the published ones, not something this figure re-derived.
# ⚠ NOT read with KA: "NA" is a STATE here, the inapplicable one, and letting pandas turn it
# into a missing value makes `state != "NA"` true for every inapplicable cell. That put
# Conflating task, which applies to the 81 descriptive studies only, on a denominator of 310
# and this check failed at 0.168 against the published 0.642.
DOMCSV = pd.read_csv("data/scoring/07_30_2026_scored_domain.csv", keep_default_na=False)
app = DOMCSV[DOMCSV.state != "NA"]
for _, r in BA.iterrows():
    z = app[(app.domain == r.domain) & (app.Study_Type == r.task)]
    got = float((z.state == r.axis).mean()) if len(z) else 0.0
    assert abs(got - float(r.baseline)) < 1e-9, ("baseline drift", r.domain, r.task, r.axis,
                                                 got, r.baseline)

ROW = lambda ax_, dm, tk: BA[(BA.axis == ax_) & (BA.domain == dm) & (BA.task == tk)].iloc[0]
AXES = [("VAL", "Validity flaw", VALC), ("REP", "Reporting gap", REPC)]


def param_row(dm, ax_):
    z = BA[(BA.axis == ax_) & (BA.domain == dm)]
    src = z.param_source.iloc[0]
    f = FL[(FL.domain == dm) & (FL.axis == ax_)]
    if src == "measured":
        z = f.iloc[0]
        return ("measured", float(z.eps1), float(z.eps1_lo), float(z.eps1_hi),
                float(z.eps0), float(z.eps0_lo), float(z.eps0_hi))
    if src.startswith("imputed"):
        y = IMP[(IMP.domain == dm) & (IMP.axis == ax_)].iloc[0]
        pool = FL[(FL.axis == ax_) & (~FL.degenerate.astype(bool))]
        d1, d0 = pool.loc[pool.eps1.idxmax()], pool.loc[pool.eps0.idxmax()]
        return ("imputed", float(y.eps1_max), float(d1.eps1_lo), float(d1.eps1_hi),
                float(y.eps0_max), float(d0.eps0_lo), float(d0.eps0_hi))
    return ("structural", None, None, None, None, None, None)


PARAMS = [(dm, ax_, param_row(dm, ax_)) for ax_, _lb, _c in AXES for dm in DOMS]
STATUS = {(dm, ax_): p[0] for dm, ax_, p in PARAMS}
NM = sum(1 for p in PARAMS if p[2][0] == "measured")
NI = sum(1 for p in PARAMS if p[2][0] == "imputed")
NS = sum(1 for p in PARAMS if p[2][0] == "structural")
assert (NM, NI, NS) == (7, 3, 4), (NM, NI, NS)

# panel B: only the domains whose prevalence can cross a rung at all
RUNGS = [("e1_to_fall_below_70", "70%"), ("e1_to_fall_below_50", "50%"),
         ("e1_to_fall_below_25", "25%")]


def rungs_of(z):
    return [(lbl, float(z[c])) for c, lbl in RUNGS
            if str(z[c]) not in ("nan", "NA", "") and float(z[c]) > 0]


TPROWS = []
for dm, tk in ROWS_A:
    z = TP[(TP.domain == dm) & (TP.task == tk)]
    # ⚠ RANDOM ERROR IS NOT DRAWN HERE. Its prevalence starts at 31.6% / 25.5%, below two of
    # the three rungs, so its only crossing is the 25% one and the row carries no claim the
    # paper makes. It remains in panel A. Dropping it pays for the two study-level rows below
    # without making the page taller.
    if not len(z) or dm == "Random error":
        continue
    cr = rungs_of(z.iloc[0])
    if cr:
        TPROWS.append((dm, tk, float(z.iloc[0].baseline), cr, "domain"))

# ⚠ THE TWO ROWS THE OBJECTION IS ACTUALLY ABOUT. A reviewer's complaint about 69% agreement
# is not about one domain, it is "maybe the literature is fine and you are reading your own
# noise". These two rows answer that directly: they are the paper's headline claims put on the
# same axis as the domains, so the reader can see how far the rate would have to travel.
# ⚠ SHORT LABELS. Panel B's label gutter is 34 mm; the stored labels ("Flawed in three or
# more domains") overran it and landed on the 70% rung, which for that row sits at 0.043.
# The full wording is in the caption.
EX = pd.read_csv("outputs/tables/08_29_2026_explain_away_thresholds.csv", **KA)
SHORTLAB = {"pct_any_flaw": "Any validity flaw", "pct_ge3_domain": "Three or more domains"}
for q in ("pct_any_flaw", "pct_ge3_domain"):
    z = EX[EX.quantity == q].iloc[0]
    cr = rungs_of(z)
    if cr:
        TPROWS.append((SHORTLAB[q], "all 310", float(z.observed), cr, "headline"))
MV = EX[EX.quantity == "mean_validity"].iloc[0]

# the envelope of what was actually measured, drawn behind every row of panel B
MEAS_MAX = float(FL[(FL.axis == "VAL") & (~FL.degenerate.astype(bool))].eps1.max())
assert abs(MEAS_MAX - 0.286) < 0.01, MEAS_MAX

EXCL = [(r.axis, r.domain, r.task) for _, r in BA.iterrows()
        if str(r.interval_contains_baseline).upper() == "FALSE"]
print("intervals excluding their baseline:", EXCL or "none")

# ---------------------------------------------------------------------------- layout
L, R = 8.0, 3.0
LABW, GAP = 34.0, 8.0
COLW = (W - L - R - LABW - GAP) / 2.0
RH_A, RH_B = 4.4, 9.4

yA = 31.0                                   # first panel-A row
endA = yA + len(ROWS_A) * RH_A
yB = endA + 30.0
endB = yB + len(TPROWS) * RH_B
H = endB + 50.0

fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")


def T(x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="center"):
    assert pt >= MIN_PT - 1e-9, ("type floor", pt, s)
    return ax.text(x, y, s, fontsize=pt, color=c, ha=ha, va=va, fontweight=weight, zorder=5)


X0 = L + LABW
COLX = [X0, X0 + COLW + GAP]
pmap = lambda v, i: COLX[i] + v * COLW
rmap = lambda v: X0 + v * (W - R - X0)

# ---------------------------------------------------------------------------- header
T(L, 7.0, "Domain prevalences under misclassification of the item states",
  pt=T_TITLE, weight="bold")
for k, s in enumerate([
        "Figure 5 reports the verdicts as recorded. Here every item state is perturbed by the "
        "concordant error rates measured in the",
        "calibration rounds, on both axes together, over 2,000 draws with each rate redrawn "
        "from its paper-clustered interval."]):
    T(L, 13.0 + k * line_h(T_HEAD), s, pt=T_HEAD, c=MUT)

# ---------------------------------------------------------------------------- panel A
T(L, yA - 9.5, "A", pt=T_HEAD, weight="bold")
T(L + 5.0, yA - 9.5, "Prevalence among applicable studies, observed against corrected",
  pt=T_HEAD, weight="bold")
for i, (_ax, lb, c) in enumerate(AXES):
    T(COLX[i], yA - 4.6, lb, pt=T_SMALL, c=c, weight="bold")
    for g in (0.0, 0.25, 0.5, 0.75, 1.0):
        ax.plot([pmap(g, i)] * 2, [yA - 2.0, endA - 1.4], color=RULE, lw=0.4, zorder=1)
        T(pmap(g, i), endA + 1.6, "%d" % (g * 100), pt=T_SMALL, c=FAINT, ha="center")
    T(COLX[i] + COLW / 2.0, endA + 5.4, "per cent of applicable studies",
      pt=T_SMALL, c=FAINT, ha="center")

prev_dm = None
for j, (dm, tk) in enumerate(ROWS_A):
    yy = yA + j * RH_A + 1.0
    T(L, yy, dm if dm != prev_dm else "", pt=T_BODY)
    prev_dm = dm
    T(L + 25.5, yy, tk[0], pt=T_SMALL, c=MUT)
    for i, (ax_, _lb, c) in enumerate(AXES):
        r = ROW(ax_, dm, tk)
        if r.param_source == "not applicable":
            T(COLX[i] + 1.0, yy, "no flag of this kind", pt=T_SMALL, c=FAINT)
            continue
        b, med, lo, hi = float(r.baseline), float(r["median"]), float(r.lo), float(r.hi)
        for v in (lo, hi, med, b):
            assert -1e-9 <= v <= 1 + 1e-9, ("value outside its axis", dm, tk, ax_, v)
        imp = str(r.param_source).startswith("imputed")
        ax.plot([pmap(lo, i), pmap(hi, i)], [yy, yy], color=c, lw=1.2, alpha=.55, zorder=3)
        ax.plot([pmap(med, i)], [yy], marker="s" if imp else "o", ms=3.0, zorder=4,
                markerfacecolor="white" if imp else c, markeredgecolor=c, markeredgewidth=0.9)
        ax.plot([pmap(b, i)] * 2, [yy - 1.15, yy + 1.15], color=INK, lw=1.0, zorder=4)
        if str(r.interval_contains_baseline).upper() == "FALSE":
            ax.plot([pmap(b, i)], [yy + 2.0], marker="^", ms=2.6, color=INK, zorder=5)

ax.plot([L, W - R], [endA + 9.0] * 2, color=RULE, lw=0.5)
for k, s in enumerate([
        "Vertical rule = the value Figure 5 reports.  Filled dot = corrected median on a "
        "measured rate.  Open square = corrected median on an imputed rate.",
        "A caret marks the one interval that does not contain its observed value, and it is "
        "an imputed row: see panel B for the statement that domain can carry."]):
    T(L, endA + 12.0 + k * line_h(T_SMALL), s, pt=T_SMALL, c=MUT)

# ---------------------------------------------------------------------------- panel B
T(L, yB - 9.5, "B", pt=T_HEAD, weight="bold")
T(L + 5.0, yB - 9.5,
  "Tipping point: the false-positive rate needed to pull each quantity below a threshold",
  pt=T_HEAD, weight="bold")
for g in (0.0, 0.2, 0.4, 0.6, 0.8, 1.0):
    ax.plot([rmap(g)] * 2, [yB - 2.0, endB - 2.0], color=RULE, lw=0.4, zorder=1)
    T(rmap(g), endB + 1.0, "%.1f" % g, pt=T_SMALL, c=FAINT, ha="center")
T(X0 + (W - R - X0) / 2.0, endB + 4.8,
  "concordant false-positive rate on the validity flag", pt=T_SMALL, c=FAINT, ha="center")

# ⚠ THE BAND IS THE POINT OF THE PANEL. Everything left of it is a rate somebody measured;
# everything right of it is a rate a sceptic would have to assert. Drawn behind every row so
# the comparison is made once, visually, instead of row by row in prose.
ax.add_patch(Rectangle((rmap(0.0), yB - 2.4), rmap(MEAS_MAX) - rmap(0.0),
                       len(TPROWS) * RH_B - 1.0, fc="#e8eef0", ec="none", zorder=0))
T(rmap(MEAS_MAX) + 1.0, yB - 4.4, "rates measured in calibration end here (%.3f)" % MEAS_MAX,
  pt=T_SMALL, c=MUT)

for j, (dm, tk, base, cr, kind) in enumerate(TPROWS):
    yy = yB + j * RH_B + 1.0
    lab_ = dm if kind == "headline" else "%s, %s" % (dm, tk.lower())
    T(L, yy - 1.0, lab_, pt=T_BODY, weight="bold" if kind == "headline" else "normal")
    T(L, yy + 1.9, "observed %.1f%%" % (100 * base), pt=T_SMALL, c=FAINT)
    ax.plot([rmap(0.0), rmap(1.0)], [yy, yy], color=RULE, lw=0.6, zorder=2)
    for lbl, v in cr:
        assert 0 <= v <= 1, ("crossing outside the swept range", dm, tk, lbl, v)
        ax.plot([rmap(v)] * 2, [yy - 1.4, yy + 1.4], color=VALC, lw=1.1, zorder=4)
        T(rmap(v), yy - 2.9, lbl, pt=T_SMALL, c=VALC, ha="center")
    if kind == "headline":
        # no single rate applies: the sweep forces every domain to the same value at once
        T(rmap(0.0) + 1.0, yy + 3.1, "every domain forced to the same rate", pt=T_SMALL, c=MUT)
        continue
    st, e1 = STATUS[(dm, "VAL")], param_row(dm, "VAL")[1]
    if e1 is not None:
        ax.plot([rmap(e1)], [yy], marker="D", ms=3.2, color=INK, zorder=5)
        T(rmap(e1), yy + 3.1, "%.3f%s" % (e1, " imputed" if st == "imputed" else " measured"),
          pt=T_SMALL, c=INK, ha="center")

ax.plot([L, W - R], [endB + 8.4] * 2, color=RULE, lw=0.5)
T(L, endB + 11.4,
  "Shaded band = the range of rates actually measured in calibration; diamond = the rate used "
  "for that domain. A rung to the right of the band is a rate",
  pt=T_SMALL, c=MUT)
T(L, endB + 11.4 + line_h(T_SMALL),
  "nobody measured. The last two rows are the paper's headline claims, and for them every "
  "domain is forced to the same rate at once.",
  pt=T_SMALL, c=MUT)

# ---------------------------------------------------------------------------- footer
yf = endB + 20.0
ax.plot([L, W - R], [yf - 3.0] * 2, color=RULE, lw=0.5)
FOOT = [
    "310 scored studies (229 causal, 81 descriptive). Parameters are measured on the two "
    "calibration rounds, in which every cell was adjudicated whether or",
    "not the reviewers agreed, against the same reference standard that resolved this study's "
    "disagreements; 13 papers, 13 reviewers, intervals bootstrapped",
    "over papers. On each axis the false-positive rate is the probability that the reference "
    "recorded no flag where both reviewers recorded one, and the",
    "false-negative rate the probability that it recorded one where neither did. Seven of the "
    "14 domain-by-axis combinations are measurable, four produce no",
    "flag of that kind, and three could not be measured because the reference recorded the "
    "same state in every applicable calibration cell; those three take the",
    "highest rate measured on the same axis and are drawn with an open marker throughout. "
    "Confounding bias is one of them, which is why panel B rather than",
    "panel A carries the statement for that domain; the rates themselves, with their "
    "intervals, are tabulated in Supplementary Methods 7.",
    "This is NOT the reporting bound of Figure 5 panel C, which recodes every reporting gap as "
    "a validity flaw and assumes nothing; the two answer different",
    "objections and are not comparable. Full parameterisation is in Supplementary Methods 7.",
    "Built by code/figures/08_29_2026_S13_misclassification_overall_figure.py.",
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

# ⚠ THE ASSERTION THIS FIGURE NEEDS. Every defect in the first build was two labels landing on
# each other, and not one of them leaves the canvas. 0.3 mm of slack absorbs kerning only.
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
    print("  %-64s %8.1f KB" % (base + "." + e, os.path.getsize(base + "." + e) / 1024))
