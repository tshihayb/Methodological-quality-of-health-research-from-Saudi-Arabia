# -*- coding: utf-8 -*-
"""Figure 5 (methodological quality) as a print-native figure: PDF + TIFF + PNG.

    python code/figures/08_22_2026_quality_scoring_print_figure.py

LAYOUT - option A, "shared spine" (TSA, 2026-08-22)
Figure 5 has six components and the height, not the width, is the binding constraint: each
full-width domain panel is ~110 mm (14 bar rows + 7 headers), so stacking the six naively
runs to ~305 mm against a ~245 mm ceiling.  But THREE of them are indexed by the same
7-domain x 2-task spine - the four-state verdict, the additive severity, and the
"not reported" sensitivity band.  So they share ONE label column and sit as three aligned
chart columns, which turns comparing a domain across the three views into a horizontal
scan and brings the figure to ~215 mm.

That reading matters more since the 2026-08-22 graded re-score: measurement bias now flags
in ~100% of papers, so the four-state panel alone cannot separate anything in that domain -
the severity column beside it is what discriminates.

Bottom rows: transparency x validity and author acknowledgement (D, E), then the study-level
score distributions (F, G).

F IS A DENSITY, G IS A PROBABILITY MASS - AND THAT IS NOT A STYLISTIC CHOICE
Only ONE of the two quantities is continuous.  The weighted validity error score takes 49
distinct values, 65% of them non-integer, because item severities are graded
0/0.25/0.5/0.75/1 - so a kernel density estimates something real, and F is drawn as one
(Gaussian kernel, Silverman bandwidth, written out here because scipy is not installed).
Reporting gaps have NO severity gradient: 7 integer values, and a paper cannot land between
them.  Its probability distribution IS a mass function, so G is drawn as mass at each
integer.  Smoothing G would put density where the variable cannot go.  Each task's curve or
mass is normalised within that task, so the two are comparable in shape despite n = 229
versus 81.

⚠ Panel F plots `error_weighted`, NOT `n_val_flags` - the flag count is still integer, so
plotting it would have made "continuous" a smoothing artefact rather than a property of the
data.  This is the whole reason the panel can be drawn continuously at all.

⚠ ONE SOURCE.  Every number is imported from code/figures/07_30_2026_gen_results_artifact.py,
which also rewrites the HTML artifact on the same run, so the screen and print versions
cannot disagree.  That module reads the scored CSVs; it does not re-derive anything here.

HOUSE RECIPE (as PRISMA / Fig 3 / S7 / S9): built print-native, never converted from the
HTML; 180 mm wide, nothing below 6.5 pt, Arial embedded, TIFF RGB/LZW at 600 dpi.  The
build asserts no text leaves the canvas and no two text boxes overlap.

OUTPUT (outputs/figures/)
  08_22_2026_quality_scoring.{pdf,tif,png}
"""
import os, math, importlib.util
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

D = r"."
os.chdir(D)
_spec = importlib.util.spec_from_file_location("q", "code/figures/07_30_2026_gen_results_artifact.py")
q = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q)                  # also rewrites the HTML - one run, one source

OUT = "outputs/figures/08_22_2026_quality_scoring"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})
PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, FAINT, AC = "#111417", "#4a5259", "#8b8f94", "#0f5c6b"
RULE, BAND = "#c8ced2", "#f2f5f6"
OK, REP, VAL, NA_ = "#0ca30c", "#e08a12", "#d03b3b", "#b4b2a9"
T_TITLE, T_HEAD, T_BODY, T_SMALL = 10.0, 7.5, 6.8, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM

L, R = 8.0, 2.0                                   # page margins
LBL = 33.0                                        # shared domain-label column
GAP = 4.0
COLW = (W - L - R - LBL - 2 * GAP) / 3.0          # three aligned chart columns
BARW = COLW - 9.0                                 # bar, leaving room for its value label
# Panel A carries TWO numbers (validity flaw % and reporting gap %), so its bar is shorter
# than panel B's to make room for them.
BARW_A = COLW - 19.0
# column C's label is the widest of the three ("100→100"), and it sits against the right
# page edge with nothing after it - so that column gets a shorter bar, not a clipped label.
BARW_C = COLW - 16.0
HALF = (W - L - R - 6.0) / 2.0     # the D|E and F|G columns
# tightened 2026-08-22 to buy height for the score-distribution row (F/G) without pushing
# the figure past the 250 mm the S9 table already establishes as this project's ceiling
# Row pitch tightened again to buy the mean-label strip in the distribution grid; the BAR
# keeps its thickness because the padding shrank with the pitch (bh = ROW_H - 1.4, was -1.8).
ROW_H, DOM_H, GRP_GAP = 3.5, 4.3, 0.8

DOMS, DLAB = q.DOMS, q.DLAB
SHORT = {"Mentioning errors": "Mentioning errors\nin the discussion",
         "Conflating task": "Conflating the task"}
TASKS = ["Descriptive", "Causal"]
LABEL = {dm: SHORT.get(dm, DLAB.get(dm, dm)) for dm in q.DOMS}
# ⚠ Domain qualifiers, carried over from the HTML (the print figure had lost them).
# "Mentioning errors" is the load-bearing one: its single item sits on the REPORTING axis,
# so the domain can only ever be OK or a reporting gap and panel A's validity-flaw share is
# 0% BY CONSTRUCTION, not because no paper has the problem — 41% of descriptive and 28% of
# causal papers named no error at all, which is what panel C's 0→41 / 0→28 shows.
# "causal only" / "descriptive only" are NOT repeated: the rows already say
# "not applicable to … studies", and repeating it costs height for nothing.
DNOTE = {"Mentioning errors": "reporting only: never a validity flaw",
         "Random error": "precision, not bias"}

# ---- geometry -----------------------------------------------------------------------------
# ⚠ MEASURE THE PROSE, DO NOT RESERVE FOR IT.  The canvas height was first written with a
# guessed 15 mm for the footnote; it wrapped to one line more than that and the overflow
# assertion caught it at 228.5 mm against 227.1.  A throwaway figure measures the wrapped
# line counts first, so the height is derived from the text that will actually be set.
_mf = plt.figure(figsize=(W / 25.4, 400 / 25.4))
_ma = _mf.add_axes([0, 0, 1, 1]); _ma.set_xlim(0, W); _ma.set_ylim(400, 0); _ma.axis("off")


def _mw(s, pt):
    t = _ma.text(0, 0, s, fontsize=pt, zorder=0)
    w = t.get_window_extent(_mf.canvas.get_renderer()).width / _mf.dpi * 25.4
    t.remove()
    return w


def wrap(s, maxw, pt):
    out, cur = [], ""
    for wd in s.split(" "):
        t = wd if not cur else cur + " " + wd
        if _mw(t, pt) > maxw and cur:
            out.append(cur); cur = wd
        else:
            cur = t
    out.append(cur)
    return out


SUB = ("Every scored item is judged on two axes: whether the study reported enough to be judged, and whether, "
       "given what it reported, it is valid. Each study × domain resolves to one of four states; a domain is "
       "flagged by its weakest link. No study cleared every domain, and %.0f%% carry a validity flaw in "
       "at least three." % (100 * q.ge3 / len(q.stu)))
FOOT = ("Predictive studies carry no bias items and are excluded. A reporting gap marks a study too opaque "
        "to judge, not one shown to be biased; panel C brackets the ruling in which every gap counts as a flaw. "
        "The two measurement-accounting items are scored and never pass, so measurement bias saturates near "
        "100% and it is panel B's severity, not panel A's flag, that separates papers. Distributions are "
        "normalised within each task; densities use a Gaussian kernel at Silverman's bandwidth, counts "
        "are probability masses. K is a THIRD axis, outside transparency: transparency asks whether a "
        "study could be judged, K whether its authors owned what we found. Instrument in Suppl. Table S1.")
D_CAP = ("All three rules on the index panels are means: the two task means, and in red the mean over "
         "all %d papers. Cross-classification of the two indices: %d high/high · %d high transparency, "
         "low validity · %d low/high · %d low/low."
         % (q.N_T, q.Q[("hi", "hi")], q.Q[("hi", "lo")], q.Q[("lo", "hi")], q.Q[("lo", "lo")]))
D_CAP_LINES = wrap(D_CAP, W - L - R - 62.0, T_SMALL)
SUB_LINES = wrap(SUB, W - L - R, T_BODY)
FOOT_LINES = wrap(FOOT, W - L - R, T_SMALL)
plt.close(_mf)

TOP = 6.0
# the 0.5 is the gap the draw pass puts between the title and the sub-line; it belongs in
# the height too, or the canvas comes up exactly 0.5 mm short of what is drawn on it
H_TITLE = line_h(T_TITLE) + 0.5 + len(SUB_LINES) * line_h(T_BODY) + 3.0
H_COLHEAD = 7.5
# ⚠ A domain header is not always one line: "Mentioning errors / in the discussion" wraps
# to two, and with DOM_H fixed at 5 mm its second line landed on top of the task letter
# below it - caught by the text-collision assertion, invisible in the code.
DOM_H_OF = lambda dm: (DOM_H + (len(LABEL[dm].splitlines()) - 1) * line_h(T_BODY)
                       + (line_h(T_SMALL) if dm in DNOTE else 0.0))
H_SPINE = sum(DOM_H_OF(dm) + len(TASKS) * ROW_H + GRP_GAP for dm in DOMS)
# The bottom is now a 2 x 3 distribution grid plus a full-width acknowledgement panel, all
# derived from their own contents rather than reserved as round numbers.
MEAN_STRIP_G = 4.8
DPLOT_H_G = 8.0
ROW_PITCH_G = H_COLHEAD + 1.0 + MEAN_STRIP_G + DPLOT_H_G + 4.0 + 3.0
H_GRID = 2 * ROW_PITCH_G + len(D_CAP_LINES) * line_h(T_SMALL) + 4.0
H_ACK = H_COLHEAD + 1.5 + 5 * 4.4 + 2.0

H_FOOT = len(FOOT_LINES) * line_h(T_SMALL) + 4.0
HEIGHT = (TOP + H_TITLE + H_COLHEAD + H_SPINE + 7.0
          + H_GRID + H_ACK + H_FOOT)

fig = plt.figure(figsize=(W / 25.4, HEIGHT / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(HEIGHT, 0); ax.axis("off")
ax.add_patch(Rectangle((0, 0), W, HEIGHT, fc="white", ec="none", zorder=0))
SIZES = []


def T(x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4):
    SIZES.append(pt)
    return ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)


def width(s, pt, weight="normal"):
    t = ax.text(0, 0, s, fontsize=pt, fontweight=weight, zorder=0)
    w = t.get_window_extent(fig.canvas.get_renderer()).width / fig.dpi * 25.4
    t.remove()
    return w


def bar(x, y, w, h, fc, ec=None):
    ax.add_patch(Rectangle((x, y), w, h, fc=fc, ec=ec or "none", lw=0, zorder=3))


DTASK = {"Descriptive": "#9ec3cc", "Causal": AC}


MEAN_STRIP = 4.8      # clear band above each grid plot, so mean labels never sit on the data


def _axes(tx, yy, w, h, title, note, ylab, strip=0.0):
    T(tx, yy, title, T_HEAD, INK, "bold")
    T(tx, yy + line_h(T_HEAD), note, T_SMALL, FAINT)
    x0 = tx + AXIS_W
    py0 = yy + H_COLHEAD + 1.0 + strip
    ax.add_line(plt.Line2D([x0, x0 + w], [py0 + h] * 2, color=RULE, lw=0.5, zorder=2))
    ax.add_line(plt.Line2D([x0, x0], [py0, py0 + h], color=RULE, lw=0.5, zorder=2))
    T(x0 - 1.4, py0 - 1.4, ylab, T_SMALL, FAINT, ha="right")
    return x0, py0


def _xticks(x0, py0, w, h, xmax, step):
    for v in range(0, int(xmax) + 1, step):
        xv = x0 + v / xmax * w
        T(xv, py0 + h + 1.2, str(v), T_SMALL, FAINT, ha="center")


def _mean_marks(x0, py0, w, h, xmax, means):
    """Mark each task's mean ON the plot rather than reciting it in a caption: a rule at the
    value, a filled dot, the number beside it - in the task's own colour, which is what tells
    the two apart without a second legend."""
    # ⚠ The two labels are STAGGERED by task, and sit inside the plot.  Above the plot there
    # is only ~3 mm before the sub-title, and the two means can be almost identical - gapped
    # domains are 1.15 vs 1.17 - so unstaggered labels land on top of each other.  Caught by
    # the text-collision assertion.
    # ⚠ Labels live in the clear strip ABOVE the plot, staggered by task.  Inside the plot
    # they sat on the bars and curves and the panels read as jammed; and two means can be
    # nearly identical (1.15 vs 1.17), so one row is not enough.
    for j, (tk, mval) in enumerate(means):
        mx = x0 + min(mval / xmax, 1.0) * w
        ly = py0 - MEAN_STRIP + 0.1 + j * line_h(T_SMALL)
        ax.add_line(plt.Line2D([mx, mx], [ly + 1.1, py0 + h], color=DTASK[tk], lw=0.7,
                               linestyle=(0, (2.2, 1.4)), zorder=5))
        ax.add_patch(plt.Circle((mx, ly + 1.1), 0.7, fc=DTASK[tk], ec="none", zorder=6))
        T(mx + 1.5, ly, "%.2f" % mval, T_SMALL, DTASK[tk], "bold")


def _kde(vals, xs, h):
    """Gaussian KDE, written out because scipy is not installed on this machine."""
    n, c = len(vals), 1.0 / math.sqrt(2 * math.pi)
    return [c * sum(math.exp(-0.5 * ((x - v) / h) ** 2) for v in vals) / (n * h) for x in xs]


def _silverman(v):
    """h = 0.9 * min(sd, IQR/1.34) * n^(-1/5); named in the footnote because a density's
    shape depends on it and the reader cannot otherwise see a choice was made."""
    n = len(v)
    m = sum(v) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in v) / (n - 1))
    sv = sorted(v)
    qq = lambda pp: sv[min(int(pp * (n - 1)), n - 1)]
    iqr = qq(0.75) - qq(0.25)
    return 0.9 * (min(sd, iqr / 1.34) if iqr > 0 else sd) * n ** (-0.2)


# =============================================================================
# Title + stat strip
# =============================================================================
y = TOP
T(L, y, "Figure 5. Methodological quality of the %d scored studies" % q.N_T, T_TITLE, INK, "bold")
y += line_h(T_TITLE) + 0.5
assert len(SUB_LINES) <= 3, len(SUB_LINES)
for i, ln in enumerate(SUB_LINES):
    T(L, y + i * line_h(T_BODY), ln, T_BODY, MUT)
y += len(SUB_LINES) * line_h(T_BODY) + 3.0


# =============================================================================
# Panel A — one spine, three aligned chart columns
# =============================================================================
CX = [L + LBL + i * (COLW + GAP) for i in range(3)]
HEADS = [("A  Four-state verdict", "bar: all papers · % of applicable: flaw · gap"),
         ("B  Additive severity", "mean flagged items per paper"),
         ("C  “Not reported” sensitivity", "% of applicable: flaw → worst case")]
for i, (h1, h2) in enumerate(HEADS):
    T(CX[i], y, h1, T_HEAD, INK, "bold")
    T(CX[i], y + line_h(T_HEAD), h2, T_SMALL, FAINT)
T(L, y, "Domain", T_HEAD, FAINT, "bold")
ax.add_line(plt.Line2D([L, W - R], [y + H_COLHEAD - 1.2] * 2, color=INK, lw=0.7, zorder=2))
y += H_COLHEAD

SCALE = q.SCALE
# ⚠ PER TASK, not pooled (TSA, 2026-08-22).  This used to draw one bar per domain spanning
# both rows, which broke the spine's D/C structure AND hid a real difference: selection bias
# does not move at all for descriptive papers (68→68, no reporting gaps) but moves 9 points
# for causal ones (80→89) — pooled, that reads as a uniform 77→83.  Two domains are
# single-task anyway, so the pooled panel silently mixed pooled and single-task bars.
def _sens(dm, tk):
    sub = q.dom[(q.dom.domain == dm) & (q.dom.Study_Type == tk) & (q.dom.state != "NA")]
    n = len(sub)
    if n == 0:
        return None
    v = int((sub.state == "VAL").sum())
    u = int(sub.state.isin(["VAL", "REP"]).sum())
    return 100.0 * v / n, 100.0 * u / n


SENS = {(dm, tk): _sens(dm, tk) for dm in DOMS for tk in TASKS}
# the per-task bands must still reconcile to the pooled figures the HTML reports
for _d, _n, _p, _u in q.sens:
    _parts = [(SENS[(_d, t)], len(q.dom[(q.dom.domain == _d) & (q.dom.Study_Type == t)
                                        & (q.dom.state != "NA")])) for t in TASKS]
    _tot = sum(n for _v, n in _parts)
    _pool = sum(v[0] * n for v, n in _parts if v) / _tot
    assert abs(_pool - _p) < 0.05, ("per-task sensitivity does not pool to q.sens", _d, _pool, _p)
for dm in DOMS:
    y0 = y
    _lines = LABEL[dm].splitlines()
    for j, ln in enumerate(_lines):
        T(L, y + j * line_h(T_BODY), ln, T_BODY, INK, "bold")
    if dm in DNOTE:
        T(L, y + len(_lines) * line_h(T_BODY) - 0.3, DNOTE[dm], T_SMALL, FAINT)
    y += DOM_H_OF(dm)
    for tk in TASKS:
        N, c = q.counts(dm, tk)
        cy = y + 0.6
        bh = ROW_H - 1.4
        T(L + 2.5, y, tk[0], T_SMALL, MUT)
        if N == 0 or c["NA"] == N:
            T(CX[0], y, "not applicable to %s studies" % tk.lower(), T_SMALL, FAINT)
        else:
            # A: four-state, 100% stacked
            x = CX[0]
            for k, col in (("OK", OK), ("REP", REP), ("VAL", VAL), ("NA", NA_)):
                seg = BARW_A * c[k] / N
                if seg > 0:
                    bar(x, cy, seg, bh, col)
                x += seg
            # applicable base, matching panel C and the project's convention - see the
            # HTML generator for what this used to be and why it was wrong.
            # ⚠ BOTH states are printed, coloured to match their bar segments: a single
            # validity-flaw number made "Mentioning errors" read as 0% = no problem, when
            # that domain is reporting-only and its real signal (41% D / 28% C) is the gap.
            _appl = N - c["NA"]
            _fl = 100.0 * c["VAL"] / _appl
            _gp = 100.0 * c["REP"] / _appl
            T(CX[0] + BARW_A + 10.0, y, "%.0f%%" % _fl, T_SMALL, VAL, "bold", ha="right")
            T(CX[0] + BARW_A + 19.0, y, "%.0f%%" % _gp, T_SMALL, REP, "bold", ha="right")
            # B: additive severity
            dv, dr = q.DMEAN[(dm, tk)]
            if dv is not None:
                x = CX[1]
                for v, col in ((dv, VAL), (dr, REP)):
                    seg = BARW * v / SCALE
                    if seg > 0:
                        bar(x, cy, seg, bh, col)
                    x += seg
                T(CX[1] + BARW + 1.5, y, "%.2f" % (dv + dr), T_SMALL, INK)
            # C: the same sensitivity band, on this task's row
            sv = SENS[(dm, tk)]
            if sv is not None:
                pp, uu = sv
                bar(CX[2], cy, BARW_C * pp / 100.0, bh, VAL)
                if uu > pp:
                    bar(CX[2] + BARW_C * pp / 100.0, cy, BARW_C * (uu - pp) / 100.0, bh, REP)
                T(CX[2] + BARW_C + 1.5, y, "%.0f→%.0f%%" % (pp, uu), T_SMALL, INK)
                # panels A and C now report the SAME quantity on the SAME base; assert it,
                # because they are computed in different places
                assert abs(pp - _fl) < 0.6, (dm, tk, pp, _fl)
                # panel A's two numbers must sum to panel C's worst case, by construction
                assert abs(uu - (_fl + _gp)) < 0.6, ("A's flaw+gap must equal C's worst case",
                                                     dm, tk, uu, _fl, _gp)
        y += ROW_H
    ax.add_line(plt.Line2D([L, W - R], [y + GRP_GAP / 2] * 2, color="#eef1f3", lw=0.4, zorder=1))
    y += GRP_GAP

KEY = [("no issue", OK), ("reporting gap", REP), ("validity flaw", VAL), ("not applicable", NA_)]
kx = L
for lab, col in KEY:
    # ⚠ va="top" at the swatch's TOP sets the text low against it.  Centre the label on the
    # swatch's mid-line instead - the same slip was in both key rows.
    bar(kx, y + 0.6, 2.6, 2.6, col)
    T(kx + 3.4, y + 0.6 + 1.3, lab, T_SMALL, MUT, va="center")
    kx += 3.4 + width(lab, T_SMALL) + 5.0
assert kx < W - R, kx
y += 7.0

# =============================================================================
# Bottom row — transparency × validity, and author acknowledgement
# =============================================================================
# =============================================================================
# Panels D-I — the six distributions, as a 2 x 3 grid
#
# ROWS are the two axes of the framework (validity, then transparency); COLUMNS run
# score -> flagged domains -> index, i.e. raw severity, then the coarse count, then the
# normalised version of the same thing.  Reading across a row follows one axis from raw to
# normalised; reading down a column compares the two axes on like terms.
#
# Stacking these as three full-width pairs needed ~48 mm more than the page has.  Three to
# a row costs plot width, which these small distributions can afford, and buys the height.
# =============================================================================
DIST_GAP = 4.0
DCOLW = (W - L - R - 2 * DIST_GAP) / 3.0
AXIS_W = 10.0
DPLOT_W = DCOLW - AXIS_W
DPLOT_H = DPLOT_H_G
ROW_PITCH = ROW_PITCH_G

# flawed / gapped domains per paper, from the domain-level states.  The flawed count is
# asserted against the scorer's own domains_flagged, so this cannot drift from it.
_dom = q.dom[q.dom.state != "NA"]
_st = q.stu.set_index("PMID")
# ⚠ q.dom is read with dtype=str (to keep the literal state "NA" a string) while q.stu is
# not, so their PMIDs are str vs int.  Joining them without casting silently returns zero
# for every paper - which is exactly what the assertion below caught.
_vc = _dom[_dom.state == "VAL"].groupby("PMID").size()
_rc = _dom[_dom.state == "REP"].groupby("PMID").size()
_flaw = {t: [int(_vc.get(str(p), 0)) for p in _st.index[_st.Study_Type == t]] for t in TASKS}
_gap = {t: [int(_rc.get(str(p), 0)) for p in _st.index[_st.Study_Type == t]] for t in TASKS}
assert sorted(sum(_flaw.values(), [])) == sorted(int(x) for x in q.stu.domains_flagged),     "flawed-domain counts must agree with the scorer's domains_flagged"
GRID = [
    [("Validity error score", "weighted by severity: density", "density",
      {t: [float(x) for x in q.stu.loc[q.stu.Study_Type == t, "error_weighted"]] for t in TASKS},
      12.0, 2, None),
     ("Domains with a validity flaw", "count per paper, of 7", "mass",
      {t: _flaw[t] for t in TASKS}, 5.0, 1, None),
     ("Validity index", "1 − flaws / judgeable items", "density",
      {t: [float(x) for x in q.stu.loc[q.stu.Study_Type == t, "validity"]] for t in TASKS},
      1.0, None, float(q.stu.validity.mean()))],
    [("Transparency score", "reporting gaps per paper", "mass",
      {t: [int(x) for x in q.stu.loc[q.stu.Study_Type == t, "n_rep_gaps"]] for t in TASKS},
      6.0, 1, None),
     ("Domains with a reporting gap", "count per paper: too opaque to judge", "mass",
      {t: _gap[t] for t in TASKS}, 3.0, 1, None),
     ("Transparency index", "1 − gaps / applicable items", "density",
      {t: [float(x) for x in q.stu.loc[q.stu.Study_Type == t, "transparency"]] for t in TASKS},
      1.0, None, float(q.stu.transparency.mean()))],
]
LETTERS = "DEFGHI"

# the pooled mean must fall between the two task means - that is the property TSA expected of
# the red rule and the reason it replaced the median.  Assert it rather than trust it.
for _col in ("validity", "transparency"):
    _p = q.stu[_col].mean()
    _lo, _hi = sorted(q.stu.groupby("Study_Type")[_col].mean()[list(TASKS)])
    assert _lo - 1e-9 <= _p <= _hi + 1e-9, ("pooled mean outside the task means", _col, _lo, _p, _hi)

li = 0
for r, row in enumerate(GRID):
    ry = y + r * ROW_PITCH
    for c, (title, note, kind, data, xmax, step, cutoff) in enumerate(row):
        tx = L + c * (DCOLW + DIST_GAP)
        ylab = "density" if kind == "density" else "% of papers"
        x0, py0 = _axes(tx, ry, DPLOT_W, DPLOT_H,
                        "%s  %s" % (LETTERS[li], title), note, ylab, MEAN_STRIP)
        li += 1
        if kind == "density":
            NG = 130
            xs = [xmax * i / (NG - 1) for i in range(NG)]
            cur = {t: _kde(data[t], xs, _silverman(data[t])) for t in TASKS}
            top = max(max(v) for v in cur.values()) * 1.08
            for t in TASKS:
                ax.add_line(plt.Line2D(
                    [x0 + xs[i] / xmax * DPLOT_W for i in range(NG)],
                    [py0 + DPLOT_H - cur[t][i] / top * DPLOT_H for i in range(NG)],
                    color=DTASK[t], lw=1.0, zorder=3))
            if xmax == 1.0:
                for tick in (0.0, 0.5, 1.0):
                    xv = x0 + tick * DPLOT_W
                    T(xv, py0 + DPLOT_H + 1.2, "%.1f" % tick, T_SMALL, FAINT, ha="center")
            else:
                _xticks(x0, py0, DPLOT_W, DPLOT_H, xmax, step)
            mx0, mspan, mmax = x0, DPLOT_W, xmax
        else:
            ks = list(range(int(xmax) + 1))
            pm = {t: [sum(1 for v in data[t] if v == k) / len(data[t]) for k in ks] for t in TASKS}
            top = max(max(v) for v in pm.values()) * 1.08
            slot = DPLOT_W / (len(ks) + 0.5)
            bw = slot * 0.36
            for j, t in enumerate(TASKS):
                for k in ks:
                    if pm[t][k] <= 0:
                        continue
                    bh = pm[t][k] / top * DPLOT_H
                    bar(x0 + (k + 0.25) * slot + (j - 1) * bw + bw * 0.1,
                        py0 + DPLOT_H - bh, bw, bh, DTASK[t])
            for k in ks:
                T(x0 + (k + 0.25) * slot, py0 + DPLOT_H + 1.2, str(k), T_SMALL, FAINT, ha="center")
            mx0, mspan, mmax = x0 + 0.25 * slot, slot * len(ks), float(len(ks))
        # the cut-off, where there is one, IS the median - see the caption
        _mean_marks(mx0, py0, mspan, DPLOT_H, mmax,
                    [(t, sum(data[t]) / len(data[t])) for t in TASKS])
        # the index panels carry the median as well, because it is the high/low cut-off
        if cutoff is not None:
            cx = mx0 + cutoff / mmax * mspan
            ax.add_line(plt.Line2D([cx, cx], [py0, py0 + DPLOT_H], color=VAL, lw=0.9,
                                   linestyle=(0, (2, 1.4)), zorder=5))
            # inside the plot and to the LEFT of its rule: the x-tick labels sit below and
            # the task means sit above-right, so this is the one band that is free
            # ⚠ The red rule is the POOLED MEAN (TSA, 2026-08-22).  It used to be the pooled
            # MEDIAN, and unlabelled beside two per-task means it read as a third mean that
            # inexplicably sat outside them - a median need not fall between group means, and
            # both indices are left-skewed.  All three rules are now means, so the red one
            # falls between the other two, as it must.  The 2x2 cross-classification counts
            # in the caption are still computed on the medians; that is a property of the
            # cross-classification, not of anything drawn here.
            T(cx - 1.2, py0 + 0.3, "all %.2f" % cutoff, T_SMALL, VAL, "bold", ha="right")

y += 2 * ROW_PITCH
for i, ln in enumerate(D_CAP_LINES):
    T(L, y + i * line_h(T_SMALL), ln, T_SMALL, MUT)
kx = L + 108.0
for tk in TASKS:
    bar(kx, y + 0.6, 4.0, 1.4, DTASK[tk])
    T(kx + 5.0, y + 0.6 + 0.7, tk.lower(), T_SMALL, MUT, va="center")
    kx += 5.0 + width(tk.lower(), T_SMALL) + 6.0
assert kx < W - R, kx
y += len(D_CAP_LINES) * line_h(T_SMALL) + 4.0

# --- J and K: acknowledgement, described then scored ------------------------------------
# ⚠ K is the SCORED counterpart of J, and it is a THIRD axis - not part of transparency.
# J asks, per domain, how often a flagged paper named that error; K asks, per paper, what
# share of its OWN flaws it named.  Kept out of the transparency index deliberately: every
# other reporting item is about judgeability (was the information there, independent of our
# verdict), while this is about candour (did they own what we found), and folding it in
# would make the reporting axis a function of the validity result.  See the scorer.
T(L, y, "J  Which errors get acknowledged", T_HEAD, INK, "bold")
T(L, y + line_h(T_HEAD), "of papers flagged in a domain, share naming it", T_SMALL, FAINT)
iy = y + H_COLHEAD + 1.5
IBW = HALF - 47.0
for dm, n, ack, pct in q.insight:
    T(L, iy, dm, T_SMALL, MUT)
    bar(L + 27.0, iy + 0.5, IBW, 2.2, "#e6e9ea")
    if pct > 0:
        bar(L + 27.0, iy + 0.5, IBW * pct / 100.0, 2.2, AC)
    T(L + 27.0 + IBW + 1.5, iy, "%.0f%%  %d/%d" % (pct, ack, n), T_SMALL, INK)
    iy += 4.4

# K - the index itself.  MASS, not density: it is a ratio of small integers, so it takes
# only 10 distinct values and 40% of papers sit exactly on 0.  A kernel density would smear
# that spike into a hump that is not in the data - the same reasoning as panel G.
KX = L + HALF + 6.0
T(KX, y, "K  Acknowledgement index", T_HEAD, INK, "bold")
T(KX, y + line_h(T_HEAD), "share of a paper's OWN flagged domains it names", T_SMALL, FAINT)
_ka = q.stu["acknowledgement"].dropna()
kx0, kpy0 = KX + AXIS_W, y + H_COLHEAD + 1.0 + MEAN_STRIP
KPW, KPH = HALF - AXIS_W, DPLOT_H_G
ax.add_line(plt.Line2D([kx0, kx0 + KPW], [kpy0 + KPH] * 2, color=RULE, lw=0.5, zorder=2))
ax.add_line(plt.Line2D([kx0, kx0], [kpy0, kpy0 + KPH], color=RULE, lw=0.5, zorder=2))
T(kx0 - 1.4, kpy0 - 1.4, "% of papers", T_SMALL, FAINT, ha="right")
_vals = sorted(_ka.unique())
_share = {v: (_ka == v).mean() for v in _vals}
_ktop = max(_share.values()) * 1.08
for v in _vals:
    bh_k = _share[v] / _ktop * KPH
    bar(kx0 + v * KPW - 0.7, kpy0 + KPH - bh_k, 1.4, bh_k, AC)
for tick in (0.0, 0.5, 1.0):
    T(kx0 + tick * KPW, kpy0 + KPH + 1.2, "%.1f" % tick, T_SMALL, FAINT, ha="center")
_mean_marks(kx0, kpy0, KPW, KPH, 1.0,
            [(t, float(q.stu.loc[q.stu.Study_Type == t, "acknowledgement"].mean())) for t in TASKS])
assert abs(_ka.mean() - 0.320) < 0.01, ("acknowledgement index moved", _ka.mean())
y += H_ACK

# =============================================================================
# Footnote
# =============================================================================
ax.add_line(plt.Line2D([L, W - R], [y] * 2, color=RULE, lw=0.5, zorder=2))
y += 2.0
for i, ln in enumerate(FOOT_LINES):
    T(L, y + i * line_h(T_SMALL), ln, T_SMALL, FAINT)
USED = y + len(FOOT_LINES) * line_h(T_SMALL) + 2.0

# =============================================================================
# Checks, then write
# =============================================================================
fig.canvas.draw()
rend = fig.canvas.get_renderer()
mm = lambda px: px / fig.dpi * 25.4
assert min(SIZES) >= MIN_PT, min(SIZES)
assert USED <= HEIGHT + 0.5, ("content overflowed the canvas", USED, HEIGHT)
boxes, spill = [], []
for t in ax.texts:
    b = t.get_window_extent(rend)
    x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
    if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > HEIGHT + 0.2:
        spill.append((round(x0, 1), round(x1, 1), t.get_text()[:40]))
    boxes.append((y0, y1, x0, x1, t.get_text()))
assert not spill, spill
clash = [(a[4][:24], b[4][:24]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
         if a[2] < b[3] - 0.2 and a[3] > b[2] + 0.2 and a[0] < b[1] - 0.2 and a[1] > b[0] + 0.2]
assert not clash, clash[:6]

fig.savefig(OUT + ".pdf", facecolor="white")
fig.savefig(OUT + ".png", dpi=600, facecolor="white")
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(OUT + ".png")
rgb = Image.new("RGB", im.size, "white")
rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
rgb.save(OUT + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
im.close(); plt.close(fig)

from pypdf import PdfReader
for pg in PdfReader(OUT + ".pdf").pages:
    for _k, _v in pg["/Resources"]["/Font"].items():
        fo = _v.get_object(); df = fo.get("/DescendantFonts")
        d = df[0].get_object() if df else fo
        desc = d.get("/FontDescriptor")
        assert d.get("/Subtype") != "/Type3" and desc and any(
            x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
        assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
t = Image.open(OUT + ".tif")
assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0)
t.close()

for ext in ("pdf", "tif", "png"):
    print("  %-52s %8.1f KB" % (OUT + "." + ext, os.path.getsize(OUT + "." + ext) / 1024))
print("  %.0f x %.0f mm, filled to %.0f mm; smallest type %.1f pt" % (W, HEIGHT, USED, MIN_PT))
print("  %d papers · %d clean · %.0f%% >=3 domains · median T/V %.2f/%.2f"
      % (q.N_T, q.clean, 100 * q.ge3 / len(q.stu), q.mt, q.mv))
