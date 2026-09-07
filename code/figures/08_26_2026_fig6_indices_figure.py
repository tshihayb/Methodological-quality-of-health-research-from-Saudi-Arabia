# -*- coding: utf-8 -*-
"""Figure 6 — the three quality indices by group, as a print-native figure: PDF + TIFF + PNG.

    python code/figures/08_26_2026_fig6_indices_figure.py

DESIGN 3B, chosen by TSA on 2026-08-26 from ten candidates across two measure sets.

WHAT IT SHOWS.  Group means of Figure 5's three NORMALISED indices — validity, transparency and
acknowledgement (Figure 5 panels F, I and K) — stratified by the ten grouping variables Figure 6
has always used.  Those three are the only quality measures in the study that are rates over
each paper's own applicable items, so they are the only ones that share a scale and can sit
side by side.  The raw scores cannot: a descriptive paper carries fewer items than a causal one,
so its error score is smaller by construction.

⚠ EVERY COLUMN IS ZOOMED, AND THE FIGURE SAYS SO.  On the true 0–1 index the 25 group means of
each task fall inside a band of about a tenth of the scale; drawn there, the figure would be
three vertical smudges.  Each half-column is therefore scaled to the interval its own group
means and their confidence bars occupy, and that interval is PRINTED at the head of the column,
so a reader can see how much magnification they are being shown.  The confidence bars are what
stop the zoom misleading: almost every one spans its own task mean.

⚠ NO SECOND COLOUR.  The candidate drew the four intervals that clear their task mean in red;
TSA asked for one treatment for all (2026-08-26), so hue now carries TASK and nothing else, and
the four are named in the sub-line instead.  A reader can still find them — they are the four
bars that do not touch their dashed rule.

⚠ THE PANEL LETTERS ARE THIS FIGURE'S, NOT FIGURE 5'S.  The candidate carried F/I/K over from
Figure 5, which would have made Figure 6 open at panel F.  They are A, B, C here; the footnote
records the correspondence.

HOUSE RECIPE (as PRISMA / Fig 5 / S1–S4): built print-native, never converted from HTML; 180 mm
wide, nothing below 6.5 pt, Arial embedded, TIFF RGB/LZW at 600 dpi.  The build asserts the type
floor, that no text leaves the canvas, that no two text boxes overlap, that the two task colours
stay apart in greyscale, and that no interval is clipped by its own axis.

⚠ ONE SOURCE.  Every number is read from the CSVs written by
code/scoring/07_30_2026_stratified_analysis.R.  Nothing is re-derived here.

OUTPUT (outputs/figures/)
  08_26_2026_fig6_indices.{pdf,tif,png}
"""
import os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from matplotlib.colors import to_rgb
import pandas as pd
from PIL import Image
from pypdf import PdfReader

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_26_2026_fig6_indices"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

PT2MM = 25.4 / 72.0
W, HMAX, MIN_PT = 180.0, 245.0, 6.5
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#8b8f94", "#c8ced2"
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM
L, R = 8.0, 2.0
TASKS = ["Descriptive", "Causal"]
DTASK = {"Descriptive": "#9ec3cc", "Causal": "#0f5c6b"}

# ⚠ hue carries TASK and nothing else, and supplements are routinely printed in greyscale, so
# the two fills must stay apart in tone as well.  Asserted, not assumed.
_lum = lambda c: sum(w * (v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
                     for w, v in zip((0.2126, 0.7152, 0.0722), to_rgb(c)))
assert abs(_lum(DTASK["Descriptive"]) - _lum(DTASK["Causal"])) >= 0.10, \
    "the two task colours lose greyscale separation"

# ---------------------------------------------------------------------------- data
KA = dict(keep_default_na=False, na_values=["NA", ""])   # "None" is the not-ranked JCR LEVEL
su = pd.read_csv("data/scoring/07_30_2026_stratified_summary.csv", **KA)
pl = pd.read_csv("data/scoring/07_30_2026_stratified_paper_level.csv", **KA)
su = su[su.stratifier != "JCR Q1-2 vs Q3-4"].copy()      # a coarsening of the quartile; not drawn
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
NLEV = len(LEVELS)

# key · sd key · per-paper column · n column · label · definition
IDX = [("mean_validity", "sd_validity", "validity", "N",
        "Validity index", "1 \u2212 flaws / judgeable items"),
       ("mean_transparency", "sd_transparency", "transparency", "N",
        "Transparency index", "1 \u2212 gaps / applicable items"),
       ("mean_ack", "sd_ack", "acknowledgement", "n_ack_elig",
        "Acknowledgement index", "own flagged domains named")]
ROW = lambda nm, lv, t: su[(su.stratifier == nm) & (su.level == lv) & (su.task == t)].iloc[0]
TN = {t: int((pl.Study_Type == t).sum()) for t in TASKS}
assert TN["Causal"] == 229 and TN["Descriptive"] == 81, TN

# all-paper mean of each index, per task — the reference rule in every half-column
PM = {(m[0], t): float(pl.loc[pl.Study_Type == t, m[2]].dropna().mean()) for m in IDX
      for t in TASKS}
# the group means must average back to it (weighted by the same n the mean was taken over)
for m in IDX:
    for t in TASKS:
        for nm, _lvs in STRATS:
            g = su[(su.stratifier == nm) & (su.task == t)]
            assert abs((g[m[0]] * g[m[3]]).sum() / g[m[3]].sum() - PM[(m[0], t)]) < 1e-6, \
                ("group means do not reconcile to the task mean", m[0], t, nm)

CI = lambda r, m: 1.96 * float(r[m[1]]) / math.sqrt(float(r[m[3]]))
# ⚠ the axis range is DERIVED from the widest bar that will be drawn, never a round number.
# A hardcoded ceiling is what let Figure 6 publish 28 clipped bars through the graded re-score.
RNG = {}
for m in IDX:
    for t in TASKS:
        vs = [(float(ROW(nm, lv, t)[m[0]]), CI(ROW(nm, lv, t), m)) for nm, lv in LEVELS]
        lo, hi = min(v - e for v, e in vs), max(v + e for v, e in vs)
        pad = (hi - lo) * 0.06
        RNG[(m[0], t)] = (lo - pad, hi + pad)
        assert RNG[(m[0], t)][0] < lo and hi < RNG[(m[0], t)][1], "an interval is clipped"
# how wide the group means themselves are, on the true 0-1 scale — the magnification the
# reader is being shown, quoted in the sub-line
# ⚠ 2026-08-29: BAND IS PER TASK, and was not. It was max-min over the whole frame, which
# holds BOTH tasks, so the subtitle paired a per-task count ("all 25 group means of a task")
# with a 50-mean pooled span (0.14, 0.07, 0.30). Every column of this figure is drawn within
# task, so the pooled span is not the quantity the sentence is about. Taking the LARGER of the
# two task bands keeps the claim true of either task read alone, and it is the tighter claim:
# 0.09, 0.07, 0.25 against the 0.14, 0.07, 0.30 that was printed. The numbers were right; the
# sentence they were in was not.
BAND = {m[0]: max(max(su[su.task == t][m[0]].max() - su[su.task == t][m[0]].min(), 0)
                  for t in TASKS) for m in IDX}
POOLED = {m[0]: max(su[m[0]].max() - su[m[0]].min(), 0) for m in IDX}
for m in IDX:
    assert BAND[m[0]] <= POOLED[m[0]] + 1e-12, ("a task band cannot exceed the pooled span", m[0])

# which intervals do NOT reach their own task mean — no longer drawn in a second colour, so
# they are named instead
CLEAR = [(m, nm, lv, t) for nm, lv in LEVELS for m in IDX for t in TASKS
         if abs(float(ROW(nm, lv, t)[m[0]]) - PM[(m[0], t)]) > CI(ROW(nm, lv, t), m)]
NCELL = NLEV * len(IDX) * len(TASKS)
assert NCELL == 150 and len(CLEAR) == 4, (NCELL, len(CLEAR))
SH = {"Number of authors": "team size", "JCR 2022 quartile": "JCR"}
_name = lambda nm, lv: "%s %s" % (SH.get(nm, nm.lower()),
                                  lab(lv)[0].lower() + lab(lv)[1:] if lv == "None" else lab(lv))
CLEARTXT = "; ".join("%s, %s (%s)" % (_name(nm, lv), m[4].lower().replace(" index", ""), t.lower())
                     for m, nm, lv, t in CLEAR)

# ---------------------------------------------------------------------------- canvas
fig0 = plt.figure(figsize=(W / 25.4, 400 / 25.4))
ax0 = fig0.add_axes([0, 0, 1, 1]); ax0.set_xlim(0, W); ax0.set_ylim(400, 0); ax0.axis("off")


def _w(s, pt, weight="normal"):
    t = ax0.text(0, 0, s, fontsize=pt, fontweight=weight, zorder=0)
    v = t.get_window_extent(fig0.canvas.get_renderer()).width / fig0.dpi * 25.4
    t.remove()
    return v


def wrap(s, maxw, pt):
    out, cur = [], ""
    for wd in s.split(" "):
        t = wd if not cur else cur + " " + wd
        if _w(t, pt) > maxw and cur:
            out.append(cur); cur = wd
        else:
            cur = t
    out.append(cur)
    return out


SUB = ("Group means of the three quality indices, the only measures in this study that are "
       "rates over each paper's own applicable items and therefore share one scale. Every "
       "column is magnified: on the true 0\u20131 index all %d group means of a task fall "
       "inside a band of %.2f, %.2f and %.2f respectively, and the interval each column "
       "actually spans is printed at its head. The bars are 95%% confidence intervals; "
       "%d of the %d include their own task mean."
       % (NLEV, BAND["mean_validity"], BAND["mean_transparency"], BAND["mean_ack"],
          NCELL - len(CLEAR), NCELL))
NOTE = ("The %d that do not: %s." % (len(CLEAR), CLEARTXT))
FOOT = ("%d scored studies (%d causal, %d descriptive); predictive studies carry no bias items "
        "and are excluded. Panels A, B and C are the group-stratified counterparts of Figure "
        "5's panels F, I and K. Higher is better on all three. Descriptive and causal papers "
        "carry different numbers of scored items, so each task is drawn on its own scale and "
        "the two are never compared to each other. n is given as descriptive | causal; for the "
        "acknowledgement index it is the papers with at least one flagged domain, i.e. those "
        "with something to acknowledge. All comparisons are associational and unadjusted: "
        "group membership is not randomised and the groups are not balanced on topic, journal "
        "or team size. Instrument in Suppl. Table S1; "
        "code/scoring/07_30_2026_stratified_analysis.R."
        % (TN["Causal"] + TN["Descriptive"], TN["Causal"], TN["Descriptive"]))
SUB_LINES = wrap(SUB, W - L - R, T_BODY)
NOTE_LINES = wrap(NOTE, W - L - R, T_SMALL)
FOOT_LINES = wrap(FOOT, W - L - R, T_SMALL)
plt.close(fig0)
assert len(SUB_LINES) <= 4, SUB_LINES
assert len(NOTE_LINES) <= 3, NOTE_LINES

# ---- geometry, derived from the content rather than reserved -------------------------------
RH, GH, GAP = 3.3, 4.4, 1.2
LBL = 38.0
CW = (W - L - R - LBL) / 3.0
GIN, GOUT = 4.0, 4.0                      # between the two task halves, and after the column
HW = (CW - GIN - GOUT) / 2.0
TOP = 6.0
H_TITLE = line_h(T_TITLE) + 0.6 + len(SUB_LINES) * line_h(T_BODY) + 1.2 \
    + len(NOTE_LINES) * line_h(T_SMALL) + 3.0
H_COLHEAD = line_h(T_HEAD) + line_h(T_SMALL) + 1.4 + line_h(T_SMALL) + 2.4
H_ROWS = sum(GH + len(lvs) * RH + GAP for _nm, lvs in STRATS)
H_KEY = 8.4
H_FOOT = len(FOOT_LINES) * line_h(T_SMALL) + 4.0
HEIGHT = TOP + H_TITLE + H_COLHEAD + H_ROWS + H_KEY + H_FOOT

fig = plt.figure(figsize=(W / 25.4, HEIGHT / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(HEIGHT, 0); ax.axis("off")
ax.add_patch(Rectangle((0, 0), W, HEIGHT, fc="white", ec="none", zorder=0))
SIZES = []


def T(x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4):
    SIZES.append(pt)
    return ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)


def ln(x0, y0, x1, y1, c=RULE, lw=0.5, z=2, ls="-"):
    ax.add_line(plt.Line2D([x0, x1], [y0, y1], color=c, lw=lw, zorder=z, linestyle=ls))


def width(s, pt, weight="normal"):
    """Measure on THIS canvas — the throwaway one used for the wrap pass is already closed."""
    t = ax.text(0, 0, s, fontsize=pt, fontweight=weight, zorder=0)
    v = t.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi * 25.4
    t.remove()
    return v


# ---------------------------------------------------------------------------- draw
y = TOP
T(L, y, "Figure 6. Does methodological quality differ by group?", T_TITLE, INK, "bold")
y += line_h(T_TITLE) + 0.6
for s in SUB_LINES:
    T(L, y, s, T_BODY, MUT)
    y += line_h(T_BODY)
y += 1.2
for s in NOTE_LINES:
    T(L, y, s, T_SMALL, FAINT)
    y += line_h(T_SMALL)
y += 3.0

CX = [L + LBL + j * CW for j in range(3)]
for j, m in enumerate(IDX):
    T(CX[j], y, "%s  %s" % ("ABC"[j], m[4]), T_HEAD, INK, "bold")
    T(CX[j], y + line_h(T_HEAD), m[5], T_SMALL, FAINT)
T(L, y, "Group", T_HEAD, FAINT, "bold")
yh = y + line_h(T_HEAD) + line_h(T_SMALL) + 1.4
for j, m in enumerate(IDX):
    for k, t in enumerate(TASKS):
        x0 = CX[j] + k * (HW + GIN)
        a, b = RNG[(m[0], t)]
        T(x0 + HW / 2, yh, "%s  %.2f\u2013%.2f" % (t[0], a, b), T_SMALL, DTASK[t], ha="center")
y += H_COLHEAD
ln(L, y - 1.4, W - R, y - 1.4, INK, 0.7)
ytop = y

for nm, lvs in STRATS:
    T(L, y, nm, T_BODY, INK, "bold")
    y += GH
    for lv in lvs:
        r = {t: ROW(nm, lv, t) for t in TASKS}
        cy = y + RH / 2 - 0.3
        T(L + 1.5, cy, lab(lv), T_SMALL, MUT, va="center")
        T(L + LBL - 2.5, cy, "%d|%d" % (int(r["Descriptive"].N), int(r["Causal"].N)),
          T_SMALL, FAINT, ha="right", va="center")
        for j, m in enumerate(IDX):
            for k, t in enumerate(TASKS):
                x0 = CX[j] + k * (HW + GIN)
                a, b = RNG[(m[0], t)]
                sx = lambda v: x0 + (v - a) / (b - a) * HW
                v, e = float(r[t][m[0]]), CI(r[t], m)
                # one treatment for every interval: hue is task and nothing else
                ln(sx(v - e), cy, sx(v + e), cy, DTASK[t], 0.6, 4)
                ax.add_patch(Circle((sx(v), cy), 0.62, fc=DTASK[t], ec="none", zorder=6))
        y += RH
    ln(L, y + GAP / 2, W - R, y + GAP / 2, "#eef1f3", 0.4, 1)
    y += GAP

for j, m in enumerate(IDX):
    for k, t in enumerate(TASKS):
        x0 = CX[j] + k * (HW + GIN)
        a, b = RNG[(m[0], t)]
        mx = x0 + (PM[(m[0], t)] - a) / (b - a) * HW
        ln(mx, ytop, mx, y - GAP, INK, 0.6, 5, (0, (2.0, 1.4)))

T(L, y, "dashed rule in each half-column = the mean over all that task's papers \u00b7 dot = "
  "the group mean \u00b7 bar = its 95% confidence interval", T_SMALL, MUT)
y += 4.2
kx = L
for t in TASKS:
    ax.add_patch(Rectangle((kx, y + 0.4), 4.0, 1.5, fc=DTASK[t], ec="none", zorder=3))
    T(kx + 5.0, y + 1.15, "%s studies · n=%d" % (t.lower(), TN[t]), T_SMALL, MUT, va="center")
    kx += 5.0 + width("%s studies · n=%d" % (t.lower(), TN[t]), T_SMALL) + 8.0
assert kx < W - R, kx
y += H_KEY - 4.2

ln(L, y, W - R, y, RULE, 0.5)
y += 2.0
for s in FOOT_LINES:
    T(L, y, s, T_SMALL, FAINT)
    y += line_h(T_SMALL)
USED = y + 2.0

# ---------------------------------------------------------------------------- checks, emit
fig.canvas.draw()
rend = fig.canvas.get_renderer()
mm = lambda px: px / fig.dpi * 25.4
assert min(SIZES) >= MIN_PT, min(SIZES)
assert USED <= HEIGHT + 0.5, ("content overflowed the canvas", USED, HEIGHT)
assert HEIGHT <= HMAX, (HEIGHT, HMAX)
boxes, spill = [], []
for t in ax.texts:
    b = t.get_window_extent(rend)
    x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
    if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > HEIGHT + 0.2:
        spill.append((round(x0, 1), round(x1, 1), t.get_text()[:40]))
    boxes.append((y0, y1, x0, x1, t.get_text()))
assert not spill, spill[:6]
clash = [(a[4][:24], b[4][:24]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
         if a[2] < b[3] - 0.2 and a[3] > b[2] + 0.2 and a[0] < b[1] - 0.2 and a[1] > b[0] + 0.2]
assert not clash, clash[:6]

base = os.path.join(OUTDIR, STEM)
fig.savefig(base + ".pdf", facecolor="white")
fig.savefig(base + ".png", dpi=600, facecolor="white")
Image.MAX_IMAGE_PIXELS = None
im = Image.open(base + ".png")
rgb = Image.new("RGB", im.size, "white")
rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
im.close(); plt.close(fig)

for pg in PdfReader(base + ".pdf").pages:
    for _k, _v in pg["/Resources"]["/Font"].items():
        fo = _v.get_object(); df = fo.get("/DescendantFonts")
        d = df[0].get_object() if df else fo
        desc = d.get("/FontDescriptor")
        assert d.get("/Subtype") != "/Type3" and desc and any(
            x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
        assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
tf = Image.open(base + ".tif")
assert tf.mode == "RGB" and tf.tag_v2[259] == 5 and tf.info["dpi"] == (600.0, 600.0)
tf.close()

for ext in ("pdf", "tif", "png"):
    print("  %-46s %8.1f KB" % (base + "." + ext, os.path.getsize(base + "." + ext) / 1024))
print("  %.0f x %.0f mm, filled to %.0f mm; smallest type %.1f pt" % (W, HEIGHT, USED, MIN_PT))
print("  %d groups x 3 indices x 2 tasks = %d intervals; %d do not reach their task mean"
      % (NLEV, NCELL, len(CLEAR)))
for m in IDX:
    print("     %-22s band over group means %.3f   D %.2f-%.2f  C %.2f-%.2f"
          % (m[4], BAND[m[0]], *RNG[(m[0], "Descriptive")], *RNG[(m[0], "Causal")]))
