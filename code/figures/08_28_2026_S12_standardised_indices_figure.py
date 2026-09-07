# -*- coding: utf-8 -*-
"""Supplementary Figure S12 - the three quality indices, tasks combined by direct
standardisation, for the whole sample and every stratum.

    python code/figures/08_28_2026_S12_standardised_indices_figure.py

WHY STANDARDISED AND NOT POOLED (TSA, 2026-08-28).
Figure 6 reports the three indices within task, because the Methods holds that "pooling would
let task mix masquerade as quality". That is true of CRUDE pooling and it is not a small
worry here: causal papers are 73.9% of the scored sample overall but range from 54.1% of the
JCR Q4 stratum to 83.8% of Q2, and the two tasks differ on every index (validity 0.485 causal
against 0.432 descriptive, transparency 0.845/0.833, acknowledgement 0.310/0.347). A crude
pooled mean therefore partly measures how many causal papers a stratum happens to hold.
Measured against the standardised value, crude pooling moves JCR Q4's validity by -0.012 and
its acknowledgement by +0.017, and it REORDERS the 25 strata on all three indices.

Direct standardisation removes it. Each stratum's two task means are weighted by the scored
sample's own split, 229 causal to 81 descriptive, so every row answers one question: what
would this group look like if it held the sample's mix of tasks? The Overall row is then
exactly the sample mean, which the build asserts.

    M    = w_c * mean_c + w_d * mean_d              w_c = 229/310, w_d = 81/310
    Var  = w_c^2 * sd_c^2 / n_c  +  w_d^2 * sd_d^2 / n_d
    CI   = M +/- 1.96 * sqrt(Var)

⚠ EVERY COLUMN IS ZOOMED, AND THE FIGURE SAYS SO, exactly as Figure 6 does: on the true 0-1
index the standardised means occupy a small part of the scale, so each column is scaled to the
interval its own means and bars occupy and that interval is printed at the column head.

HOUSE RECIPE (as PRISMA / Fig 5 / Fig 6): print-native, 180 mm wide, nothing below 6.5 pt,
Arial embedded, TIFF RGB/LZW at 600 dpi. The build asserts the type floor, that nothing leaves
the canvas, that no interval is clipped, and that the Overall row reconciles to the sample mean.

⚠ ONE SOURCE. Every number is read from the CSVs written by
code/scoring/07_30_2026_stratified_analysis.R. Nothing is re-derived here.

OUTPUT (outputs/figures/)
  08_28_2026_S12_standardised_indices.{pdf,tif,png}
"""
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image
from pypdf import PdfReader

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_28_2026_S12_standardised_indices"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#8b8f94", "#c8ced2"
DOT = "#0f5c6b"
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM

# ---------------------------------------------------------------------------- data
KA = dict(keep_default_na=False, na_values=["NA", ""])   # "None" is the not-ranked JCR LEVEL
su = pd.read_csv("data/scoring/07_30_2026_stratified_summary.csv", **KA)
pl = pd.read_csv("data/scoring/07_30_2026_stratified_paper_level.csv", **KA)
su = su[su.stratifier != "JCR Q1-2 vs Q3-4"].copy()
assert (su.level == "None").any(), "the not-ranked JCR level was read as missing"

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
assert set(s[0] for s in STRATS) == set(su.stratifier.unique())
LVLAB = {">=50%": "\u226550%", "None": "Not ranked", "Academic-only": "Academic only",
         "1-2": "1\u20132", "3-10": "3\u201310"}
lab = lambda v: LVLAB.get(v, v)
LEVELS = [(nm, lv) for nm, lvs in STRATS for lv in lvs]
assert len(LEVELS) == 25, len(LEVELS)

TASKS = ["Causal", "Descriptive"]
TN = {t: int((pl.Study_Type == t).sum()) for t in TASKS}
assert TN["Causal"] == 229 and TN["Descriptive"] == 81, TN
NTOT = TN["Causal"] + TN["Descriptive"]
WT = {t: TN[t] / float(NTOT) for t in TASKS}          # the standard: the sample's own mix

# key · sd key · per-paper column · n column · label · definition
IDX = [("mean_validity", "sd_validity", "validity", "N",
        "Validity index", "1 \u2212 flaws / judgeable items"),
       ("mean_transparency", "sd_transparency", "transparency", "N",
        "Transparency index", "1 \u2212 gaps / applicable items"),
       ("mean_ack", "sd_ack", "acknowledgement", "n_ack_elig",
        "Acknowledgement index", "own flagged domains named")]
ROW = lambda nm, lv, t: su[(su.stratifier == nm) & (su.level == lv) & (su.task == t)].iloc[0]

# ⚠ the acknowledgement index is defined only on papers with something to acknowledge. Every
# one of the 310 carries at least one flagged domain, so that base is the whole sample and the
# same weights apply - asserted rather than assumed.
for t in TASKS:
    got = int(su[(su.stratifier == "Saudi data used") & (su.task == t)]["n_ack_elig"].sum())
    assert got == TN[t], ("acknowledgement base is not the whole task", t, got, TN[t])


def std_mean(nm, lv, m):
    """Directly standardised mean and its 95% half-width for one stratum and one index."""
    M = V = 0.0
    for t in TASKS:
        r = ROW(nm, lv, t)
        n, sd = float(r[m[3]]), float(r[m[1]])
        M += WT[t] * float(r[m[0]])
        V += (WT[t] ** 2) * (sd ** 2) / n
    return M, 1.96 * math.sqrt(V)


def overall(m):
    """The whole-sample row. With the sample's own weights this IS the sample mean."""
    M = V = 0.0
    for t in TASKS:
        v = pl.loc[pl.Study_Type == t, m[2]].dropna()
        M += WT[t] * v.mean()
        V += (WT[t] ** 2) * (v.std(ddof=1) ** 2) / len(v)
    return M, 1.96 * math.sqrt(V)


OVR = {m[0]: overall(m) for m in IDX}
for m in IDX:
    true_mean = pl[m[2]].dropna().mean()
    assert abs(OVR[m[0]][0] - true_mean) < 1e-9, \
        ("the standardised overall row is not the sample mean", m[0])

VALS = {(m[0], nm, lv): std_mean(nm, lv, m) for m in IDX for nm, lv in LEVELS}

# ⚠ the axis range is DERIVED from the widest bar that will be drawn, never a round number.
RNG, BAND = {}, {}
for m in IDX:
    pts = [VALS[(m[0], nm, lv)] for nm, lv in LEVELS] + [OVR[m[0]]]
    lo, hi = min(v - e for v, e in pts), max(v + e for v, e in pts)
    pad = (hi - lo) * 0.06
    RNG[m[0]] = (lo - pad, hi + pad)
    assert RNG[m[0]][0] < lo and hi < RNG[m[0]][1], "an interval is clipped"
    mus = [VALS[(m[0], nm, lv)][0] for nm, lv in LEVELS]
    BAND[m[0]] = max(mus) - min(mus)

# how far crude pooling would have moved each row - the figure's reason for existing
worst = (0.0, None)
for m in IDX:
    for nm, lv in LEVELS:
        crude_n = sum(float(ROW(nm, lv, t)[m[3]]) for t in TASKS)
        crude = sum(float(ROW(nm, lv, t)[m[0]]) * float(ROW(nm, lv, t)[m[3]])
                    for t in TASKS) / crude_n
        b = crude - VALS[(m[0], nm, lv)][0]
        if abs(b) > abs(worst[0]):
            worst = (b, (m[4], nm, lv))
CSHARE = [float(ROW(nm, lv, "Causal")["N"]) /
          (float(ROW(nm, lv, "Causal")["N"]) + float(ROW(nm, lv, "Descriptive")["N"]))
          for nm, lv in LEVELS]
print("causal share across the 25 strata: %.3f to %.3f (overall %.3f)"
      % (min(CSHARE), max(CSHARE), WT["Causal"]))
print("largest crude-pooling distortion: %+.4f on %s, %s / %s"
      % (worst[0], worst[1][0], worst[1][1], worst[1][2]))
for m in IDX:
    print("  %-22s overall %.4f (+/- %.4f) | means span %.4f | axis %.3f to %.3f"
          % (m[4], OVR[m[0]][0], OVR[m[0]][1], BAND[m[0]], RNG[m[0]][0], RNG[m[0]][1]))

# ---------------------------------------------------------------------------- layout
# ⚠ R is 9 mm, not the usual 2: the Overall row prints its value to the right of each column,
# and with a 2 mm margin the third column's label ran off the page.
L, R = 8.0, 9.0
LABW = 46.0                      # row-label gutter
GAP = 5.0
COLW = (W - L - R - LABW - GAP * (len(IDX) - 1)) / len(IDX)
ROWH = 3.5
HEADH = 31.0
rows = []                        # (kind, name, y)
y = HEADH
rows.append(("overall", "All 310 scored studies", y)); y += ROWH + 1.6
for nm, lvs in STRATS:
    rows.append(("head", nm, y)); y += ROWH * 0.95
    for lv in lvs:
        rows.append(("level", (nm, lv), y)); y += ROWH
    y += 1.2
# ⚠ 32 mm, not 20: the footer runs to seven lines at 6.5 pt (about 21 mm) and starts
# ROWH*1.9 below the last row. The canvas assertion catches it if this drifts.
H = y + 32.0

fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
BOXES = []


def T(x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="center"):
    assert pt >= MIN_PT - 1e-9, ("type floor", pt, s)
    t = ax.text(x, y, s, fontsize=pt, color=c, ha=ha, va=va, fontweight=weight, zorder=4)
    BOXES.append((x, y, s, pt))
    return t


x0 = L + LABW
COLX = [x0 + i * (COLW + GAP) for i in range(len(IDX))]
xmap = lambda m, v, i: COLX[i] + (v - RNG[m[0]][0]) / (RNG[m[0]][1] - RNG[m[0]][0]) * COLW

# header
T(L, 7.0, "Quality indices with the two study tasks combined by direct standardisation",
  pt=T_TITLE, weight="bold")
# ⚠ 180 mm at 7.5 pt holds about 130 characters. The assertion below catches an overrun,
# but only after the figure is drawn, so every line here is broken by hand.
for _k, _s in enumerate([
        "Each row weights its causal and descriptive means by the scored sample's own split, "
        "229 to 81, so no row is moved by its task mix.",
        "Bars are 95% confidence intervals and higher is better on all three. Every column is "
        "magnified to the interval its own means occupy."]):
    T(L, 12.4 + _k * 4.0, _s, pt=T_HEAD, c=MUT)

# ⚠ The definition and the axis range go on SEPARATE lines. On one line the widest of them
# ("own flagged domains named  ·  0.13 to 0.48") is about 50 mm, which overruns a 38 mm
# column and, in the third column, the page.
for i, m in enumerate(IDX):
    T(COLX[i], 20.5, "%s  %s" % ("ABC"[i], m[4]), pt=T_HEAD, weight="bold")
    T(COLX[i], 24.0, m[5], pt=T_SMALL, c=FAINT)
    T(COLX[i], 27.3, "axis %.2f to %.2f" % (RNG[m[0]][0], RNG[m[0]][1]), pt=T_SMALL, c=FAINT)
    ax.plot([COLX[i], COLX[i] + COLW], [HEADH - 2.0] * 2, color=INK, lw=0.7, zorder=3)

# the reference rule in every column: the standardised overall mean
for i, m in enumerate(IDX):
    xr = xmap(m, OVR[m[0]][0], i)
    ax.plot([xr, xr], [HEADH - 2.0, rows[-1][2] + ROWH * 0.8], color=INK, lw=0.6, ls=(0, (2, 2)),
            zorder=2)

for kind, name, yy in rows:
    if kind == "head":
        T(L, yy, name, pt=T_BODY, weight="bold", c=INK)
        continue
    if kind == "overall":
        T(L, yy, name, pt=T_BODY, weight="bold")
        for i, m in enumerate(IDX):
            v, e = OVR[m[0]]
            ax.plot([xmap(m, v - e, i), xmap(m, v + e, i)], [yy, yy], color=INK, lw=1.4, zorder=3)
            ax.plot([xmap(m, v, i)], [yy], marker="o", ms=3.4, color=INK, zorder=4)
            T(COLX[i] + COLW + 1.0, yy, "%.2f" % v, pt=T_SMALL, c=INK, weight="bold")
        continue
    nm, lv = name
    T(L + 3.0, yy, lab(lv), pt=T_BODY, c=INK)
    for i, m in enumerate(IDX):
        v, e = VALS[(m[0], nm, lv)]
        ax.plot([xmap(m, v - e, i), xmap(m, v + e, i)], [yy, yy], color=DOT, lw=1.0, zorder=3)
        ax.plot([xmap(m, v, i)], [yy], marker="o", ms=2.6, color=DOT, zorder=4)

yf = rows[-1][2] + ROWH * 1.9
ax.plot([L, W - R], [yf - 3.0] * 2, color=RULE, lw=0.5)
# ⚠ One list entry per PRINTED line. 180 mm at 6.5 pt holds about 150 characters; the
# canvas assertion below catches an overrun, but only after the figure is drawn.
FOOT = [
    "310 scored studies (229 causal, 81 descriptive); predictive studies carry no bias items and "
    "are excluded. This is the task-combined counterpart of Figure 6,",
    "which reports the same three indices within task. Combining is by DIRECT STANDARDISATION, "
    "not pooling: causal papers are %.1f%% of the sample but range" % (WT["Causal"] * 100),
    "from %.1f%% to %.1f%% across these strata, and the two tasks differ on every index, so a "
    "crude pooled mean would partly measure task mix." % (min(CSHARE) * 100, max(CSHARE) * 100),
    "Against the standardised value, crude pooling moves the worst-affected row by %+.3f "
    "(%s, %s)."
    % (worst[0], worst[1][0].lower().replace(" index", ""),
       ("JCR " + worst[1][2]) if "JCR" in worst[1][1] else "%s %s" % (worst[1][1].lower(), worst[1][2])),
    "It would also reorder the 25 strata on all three indices.",
    "The dashed rule in each column is the standardised mean over all 310, which with these "
    "weights is exactly the sample mean. All comparisons are descriptive",
    "and unadjusted. Built by code/figures/08_28_2026_S12_standardised_indices_figure.py.",
]
for k, ln_ in enumerate(FOOT):
    T(L, yf + k * line_h(T_SMALL), ln_, pt=T_SMALL, c=MUT)

# ---------------------------------------------------------------------------- assertions
fig.canvas.draw()
inv = ax.transData.inverted()
for t in ax.texts:
    bb = t.get_window_extent(fig.canvas.get_renderer())
    (xa, ya), (xb, yb) = inv.transform((bb.x0, bb.y0)), inv.transform((bb.x1, bb.y1))
    assert min(xa, xb) >= -0.5 and max(xa, xb) <= W + 0.5, ("text leaves the canvas", t.get_text())
    assert min(ya, yb) >= -0.5 and max(ya, yb) <= H + 0.5, ("text leaves the canvas", t.get_text())

os.makedirs(OUTDIR, exist_ok=True)
base = os.path.join(OUTDIR, STEM)
fig.savefig(base + ".pdf", format="pdf")
fig.savefig(base + ".png", dpi=600)
Image.open(base + ".png").save(base + ".tif", compression="tiff_lzw", dpi=(600, 600))
plt.close(fig)

pg = PdfReader(base + ".pdf").pages[0]
print("\n%.1f x %.1f mm" % (float(pg.mediabox.width) * 25.4 / 72, float(pg.mediabox.height) * 25.4 / 72))
for e in ("pdf", "tif", "png"):
    print("  %-58s %8.1f KB" % (base + "." + e, os.path.getsize(base + "." + e) / 1024))
