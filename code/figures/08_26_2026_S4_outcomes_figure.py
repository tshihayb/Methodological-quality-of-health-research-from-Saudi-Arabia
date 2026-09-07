# -*- coding: utf-8 -*-
"""Supplementary Figure S1 - study outcomes. Print-native, five candidate designs.

ONE figure carrying what the 385 papers measured: the 13 categories in their 4 domains plus
the residual Other, the way the mix shifts with study task, and - a first-class fact after the
2026-08-26 sweep - which outcomes a reviewer adjudicated and which are provisional.

  A  combined first: categories grouped by domain, then the category x task matrix
  B  task-forward: the domain mix per task, then every category's profile across the tasks
  C  provenance: every category drawn twice, all 385 against the 310 reviewers adjudicated
  D  divergence: one row per category, a dot per task at its within-task share
  E  one bar per category, segmented by task, with the domain and provenance summaries

Same print contract as Supplementary Figures S2, S3, S10 and S11: 180 mm wide, 6.5 pt type
floor, Arial embedded, TIFF RGB / LZW / 600 dpi, and the same three assertions - type floor,
nothing off the page, and no two text boxes touching.

⚠ COLOUR. Hue encodes domain and nothing else; magnitude is always bar length. Four domain
fills are chosen for GREYSCALE separation and the spacing is asserted below - supplements are
frequently printed in greyscale, and the S3 rebuild showed that fixing a hue collision can
silently destroy a tone separation. The residual *Other* is drawn as an OPEN hatched bar
rather than a fifth fill: five well-separated greys do not exist in this range, and an open
bar also says "residual" without needing a colour at all.

⚠ PROVENANCE IS HATCHED, NOT TINTED. 75 of the 385 outcomes were determined by a language
model and are provisional. Tinting them would make lightness carry both domain and provenance;
a hatch is orthogonal to hue and to tone, and survives greyscale.

    python code/figures/08_26_2026_S4_outcomes_figure.py [A..E]

No argument (or several) emits PNG only, for choosing from. One design letter emits
PDF + TIFF + PNG. Run from the repository root.
"""
import csv
import os
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from PIL import Image
from pypdf import PdfReader

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial",
                            "hatch.linewidth": 0.35})

OUTDIR = "outputs/figures"
SRC = "data/outcomes/08_08_2026_all_outcomes_classified.csv"

W = 180.0                 # journal single-figure width, mm
HMAX = 245.0              # page height less margins
MIN_PT = 6.5              # journal type floor; asserted
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#7b848c", "#c8ced2"
T_PANEL, T_BODY, T_SMALL = 8.5, 7.0, 6.5

TASKS = ["Descriptive", "Causal", "Predictive"]
CATORDER = ["1.1", "1.2", "1.3", "1.4", "1.5", "2.1", "2.2", "2.3",
            "3.1", "3.2", "3.3", "4.1", "OTHER"]
DOMS = ["1", "2", "3", "4", "9"]
DOMLAB = {"1": "Clinical / biomedical", "2": "Patient-reported & functional",
          "3": "Knowledge, attitudes & behaviours", "4": "Health-system & process",
          "9": "Other (no health outcome)"}
# Paul Tol muted, ordered by descending darkness so greyscale reads as an ordering too.
DCOL = {"1": "#332288", "2": "#117733", "3": "#CC6677", "4": "#DDCC77", "9": "none"}
SHORT = {"1.1": "Mortality & survival",
         "1.2": "Disease occurrence / diagnosis",
         "1.3": "Severity, progression, complications",
         "1.4": "Physiological, lab & imaging",
         "1.5": "Treatment / procedure response",
         "2.1": "Clinical, functional & symptom scales",
         "2.2": "Mental health & psychological status",
         "2.3": "Satisfaction & care experience",
         "3.1": "Knowledge & awareness",
         "3.2": "Attitudes, perceptions & willingness",
         "3.3": "Health behaviours & adherence",
         "4.1": "Utilization, cost, process & workforce",
         "OTHER": "Other"}
TASKHATCH = {"Descriptive": "", "Causal": "///", "Predictive": "..."}


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


_fills = [DCOL[d] for d in ("1", "2", "3", "4")]
_l = [_lum(c) for c in _fills]
assert all(_l[i + 1] - _l[i] >= 0.10 for i in range(len(_l) - 1)), \
    "domain fills lose greyscale separation: %s" % [round(x, 3) for x in _l]

# ---------------------------------------------------------------------------- data
rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
N = len(rows)
TT = Counter(r["Study_Type"] for r in rows)
CT = Counter((r["category"], r["Study_Type"]) for r in rows)
CTOT = Counter(r["category"] for r in rows)
DTOT = Counter(r["domain"] for r in rows)
DT = Counter((r["domain"], r["Study_Type"]) for r in rows)
PROV = Counter(r["category"] for r in rows if r["source"].startswith("machine"))
DPROV = Counter(r["domain"] for r in rows if r["source"].startswith("machine"))
ADJ = {c: CTOT[c] - PROV[c] for c in CATORDER}
NPROV = sum(PROV.values())
NADJ = N - NPROV
DOMOF = {c: ("9" if c == "OTHER" else c.split(".")[0]) for c in CATORDER}

assert N == 385 and NADJ == 310 and NPROV == 75, (N, NADJ, NPROV)
assert TT["Causal"] == 229 and TT["Descriptive"] == 81 and TT["Predictive"] == 75, TT
assert CTOT["1.2"] == 93 and CTOT["1.4"] == 74 and CTOT["OTHER"] == 13, \
    (CTOT["1.2"], CTOT["1.4"], CTOT["OTHER"])
assert ADJ["1.2"] == 62 and ADJ["1.4"] == 61, (ADJ["1.2"], ADJ["1.4"])
assert [DTOT[d] for d in DOMS] == [223, 60, 71, 18, 13], [DTOT[d] for d in DOMS]
assert all(r["Study_Type"] == "Predictive" for r in rows
           if r["source"].startswith("machine")), \
    "a non-predictive row is provisional - the provenance wording assumes otherwise"

PCT = lambda a, b: (100.0 * a / b) if b else 0.0


# ---------------------------------------------------------------------------- canvas
class Page(object):
    """A figure addressed in millimetres, origin top-left."""

    def __init__(self, h):
        self.h = h
        self.fig = plt.figure(figsize=(W / 25.4, h / 25.4), dpi=600)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")
        self.sizes = []
        self.guards = []

    def text(self, x, y, s, pt=T_BODY, col=INK, ha="left", weight="normal", style="normal"):
        self.sizes.append(pt)
        return self.ax.text(x, y, s, fontsize=pt, color=col, ha=ha, va="baseline",
                            fontweight=weight, fontstyle=style)

    def rect(self, x, y, w, h, col, alpha=1.0, ec="none", lw=0.0, hatch=None, guard=False):
        # ⚠ guard=True registers the rectangle for the rect-vs-text assertion. S3 printed
        # "220 (57.1%)" as "20 (57.1%)" because a bar was drawn straight through its own
        # value label and every text-vs-text check passed.
        kw = dict(facecolor=col, alpha=alpha, edgecolor=ec, linewidth=lw)
        if hatch:
            kw["hatch"] = hatch
            if ec == "none":
                kw["edgecolor"] = "#ffffff"
                kw["linewidth"] = 0.0
        self.ax.add_patch(Rectangle((x, y), w, h, **kw))
        if guard:
            self.guards.append((x, y, x + w, y + h))

    def line(self, x0, y0, x1, y1, col=RULE, lw=0.4):
        self.ax.plot([x0, x1], [y0, y1], color=col, lw=lw, solid_capstyle="butt")

    def measure(self, s, pt):
        """Width of `s` in mm, measured, not estimated."""
        t = self.ax.text(0, 0, s, fontsize=pt)
        self.fig.canvas.draw()
        w = t.get_window_extent(self.fig.canvas.get_renderer()).width / self.fig.dpi * 25.4
        t.remove()
        return w

    def fit(self, s, max_mm, pt):
        if self.measure(s, pt) <= max_mm:
            return s
        for k in range(len(s) - 1, 2, -1):
            cand = s[:k].rstrip() + "…"
            if self.measure(cand, pt) <= max_mm:
                return cand
        return s[:3]


# ---------------------------------------------------------------------------- pieces
TOP = 5.0
GAP = 7.0
ROW = 4.3            # category row pitch, mm
DOMHEAD = 4.6        # domain header block
FOOT_H = 11.0
LABW = 56.0          # category-label column
BARX = 58.0
BARW = 74.0


def panel_label(p, y, letter, title, sub=None):
    p.text(0, y, letter, 9.5, INK, weight="bold")
    p.text(4.6, y, title, T_PANEL, INK, weight="bold")
    if sub:
        p.text(4.6, y + 3.4, sub, T_SMALL, MUT)
    return y + (7.6 if sub else 4.6)


def legend_domains(p, x, y, incl_other=True, lead=3.4):
    """Domain key. Wraps to a second line rather than running off the page - design B put
    the five entries at x=34 on the first cut and 'Other' landed 32 mm past the trim."""
    cx, rows = x, 0
    for d in DOMS:
        if d == "9" and not incl_other:
            continue
        lab = DOMLAB[d]
        need = 4.0 + p.measure(lab, T_SMALL) + 5.5
        if cx + need > W and cx > x:
            cx, rows = x, rows + 1
        yy = y + rows * lead
        if d == "9":
            p.rect(cx, yy - 1.8, 3.0, 2.0, "none", ec=MUT, lw=0.4, hatch="xxx")
        else:
            p.rect(cx, yy - 1.8, 3.0, 2.0, DCOL[d])
        p.text(cx + 4.0, yy, lab, T_SMALL, MUT)
        cx += need
    return y + (rows + 1) * lead


def provenance_note(p, y, mode="words"):
    """Provenance key.

    ⚠ `mode` must match what the design actually draws. The first cut printed a HATCHED
    swatch on every design, including three that never hatch for provenance and one (E)
    where the hatch means study task - one mark carrying two meanings, and a key crediting
    an encoding the figure does not use. Both are S3 defect classes.
      hatch   - the design fills the provisional part of each bar with a hatch (design A)
      openbar - the design draws the adjudicated subset as an open bar (design C)
      words   - the design does not encode provenance graphically; say it in prose
    """
    lab = "Provenance"
    p.text(0, y, lab, T_SMALL, INK, weight="bold")
    x = p.measure(lab, T_SMALL) + 3.0
    if mode == "words":
        # ⚠ wrap by measurement: as one p.text() this ran 15.7 mm past the trim.
        return para(p, x, y, "%d of the %d outcomes were adjudicated by the two reviewers; "
                             "the other %d are provisional, determined by a language model and "
                             "pending sign-off (every one a predictive study)."
                    % (NADJ, N, NPROV), 2, W - x) - 3.0
    p.rect(x, y - 1.8, 3.0, 2.0, DCOL["1"])
    t1 = "%d adjudicated by the two reviewers" % NADJ
    p.text(x + 4.0, y, t1, T_SMALL, MUT)
    x2 = x + 4.0 + p.measure(t1, T_SMALL) + 5.0
    if mode == "hatch":
        p.rect(x2, y - 1.8, 3.0, 2.0, DCOL["1"], hatch="////")
        t2 = ("%d provisional, hatched, pending reviewer sign-off "
              "(every one a predictive study)" % NPROV)
    else:
        p.rect(x2, y - 1.8, 3.0, 2.0, "none", ec=INK, lw=0.45)
        t2 = ("open bar: the %d adjudicated only, so the gap to the filled bar is the "
              "provisional %d" % (NADJ, NPROV))
    p.text(x2 + 4.0, y, t2, T_SMALL, MUT)
    return y


def para(p, x, y, s, nlines, width=W, pt=T_SMALL, col=MUT, lead=3.0):
    """Wrap by MEASUREMENT and assert the line count. nlines is a contract: a one-line note
    that grows to two must fail here rather than silently overlap the block below."""
    words, lines, cur = s.split(), [], ""
    for wd in words:
        cand = (cur + " " + wd) if cur else wd
        if p.measure(cand, pt) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    assert len(lines) <= nlines, (len(lines), nlines, lines)
    for i, ln in enumerate(lines):
        p.text(x, y + i * lead, ln, pt, col)
    return y + len(lines) * lead


def footer(p, y):
    para(p, 0, y,
         "One outcome per paper, so every count is also a paper count. Categories are the "
         "predefined codebook of twelve categories across four domains plus a residual Other. "
         "%d of the %d outcomes (%.0f%%) are provisional machine determinations, all of them "
         "in the predictive arm, so every pooled count above mixes them with the %d the two "
         "reviewers adjudicated." % (NPROV, N, PCT(NPROV, N), NADJ), 3)


def cat_bar_block(p, y0, denom_all=True):
    """13 category bars grouped under their domain headers. Returns the y after the block."""
    mx = max(CTOT[c] for c in CATORDER)
    y = y0
    for d in DOMS:
        cats = [c for c in CATORDER if DOMOF[c] == d]
        p.rect(0, y - 2.4, W, 3.3, DCOL[d] if d != "9" else "#eeeeee",
               alpha=0.13 if d != "9" else 1.0)
        p.text(1.2, y, DOMLAB[d], T_SMALL, INK, weight="bold")
        p.text(W, y, "%d papers  ·  %.0f%%" % (DTOT[d], PCT(DTOT[d], N)),
               T_SMALL, MUT, ha="right")
        y += DOMHEAD
        for c in cats:
            tot, prov = CTOT[c], PROV[c]
            p.text(LABW, y, p.fit(SHORT[c], LABW - 3.0, T_BODY), T_BODY, INK, ha="right")
            wtot = BARW * tot / mx
            wadj = BARW * (tot - prov) / mx
            if d == "9":
                p.rect(BARX, y - 2.1, wtot, 2.4, "none", ec=MUT, lw=0.4, hatch="xxx")
            else:
                p.rect(BARX, y - 2.1, wadj, 2.4, DCOL[d])
                if prov:
                    p.rect(BARX + wadj, y - 2.1, wtot - wadj, 2.4, DCOL[d], hatch="////")
            p.text(BARX + wtot + 1.6, y, "%d" % tot, T_BODY, INK, weight="bold")
            p.text(W, y, "%.1f%%" % PCT(tot, N), T_SMALL, MUT, ha="right")
            y += ROW
        y += 1.2
    return y


def cat_bar_h(nrows=13):
    return len(DOMS) * (DOMHEAD + 1.2) + nrows * ROW


def matrix_block(p, y0, within=True):
    """Category x task counts, with within-task % beneath each count."""
    colx = [96.0, 122.0, 148.0, W]
    p.text(LABW, y0, "Outcome category", T_SMALL, MUT, ha="right")
    for i, t in enumerate(TASKS):
        p.text(colx[i], y0, "%s  n=%d" % (t, TT[t]), T_SMALL, MUT, ha="right")
    p.text(colx[3], y0, "All %d" % N, T_SMALL, MUT, ha="right")
    p.line(0, y0 + 1.2, W, y0 + 1.2, INK, 0.5)
    y = y0 + 1.2
    for d in DOMS:
        for c in [x for x in CATORDER if DOMOF[x] == d]:
            y += ROW
            p.rect(0.0, y - 2.0, 2.2, 2.2, DCOL[d] if d != "9" else "none",
                   ec=MUT if d == "9" else "none", lw=0.4, hatch="xxx" if d == "9" else None)
            p.text(LABW, y, p.fit(SHORT[c], LABW - 4.0, T_BODY), T_BODY, INK, ha="right")
            for i, t in enumerate(TASKS):
                v = CT[(c, t)]
                p.text(colx[i], y, "%d" % v if v else "–", T_BODY,
                       INK if v else FAINT, ha="right")
                if within and v:
                    p.text(colx[i] + 0.0, y + 2.5, "%.0f%%" % PCT(v, TT[t]),
                           T_SMALL, FAINT, ha="right")
            p.text(colx[3], y, "%d" % CTOT[c], T_BODY, DCOL[d] if d != "9" else MUT,
                   ha="right", weight="bold")
            y += 2.9 if within else 0.0
    p.line(0, y + 1.4, W, y + 1.4, RULE, 0.4)
    return y + 4.0


def matrix_h(within=True):
    return 1.2 + 13 * (ROW + (2.9 if within else 0.0)) + 4.0


def stacked_by_task(p, y0):
    """Three 100% bars, one per task, segmented by domain. Thin segments are named beside."""
    bx, bw = 34.0, 118.0
    y = y0
    for t in TASKS:
        p.text(30.0, y + 1.2, "%s" % t, T_BODY, INK, ha="right", weight="bold")
        p.text(30.0, y + 4.4, "n=%d" % TT[t], T_SMALL, MUT, ha="right")
        x = bx
        tiny = []
        for d in DOMS:
            v = DT[(d, t)]
            if not v:
                continue
            w = bw * v / TT[t]
            if d == "9":
                p.rect(x, y - 1.4, w, 5.4, "none", ec=MUT, lw=0.4, hatch="xxx")
            else:
                p.rect(x, y - 1.4, w, 5.4, DCOL[d])
            lab = "%d" % v
            if p.measure(lab, T_SMALL) + 1.6 <= w:
                col = "#ffffff" if d in ("1", "2") else INK
                p.text(x + w / 2.0, y + 2.2, lab, T_SMALL, col, ha="center")
            else:
                tiny.append("%s %d" % (DOMLAB[d].split(" ")[0].rstrip(","), v))
            x += w
        if tiny:
            p.text(bx + bw + 2.0, y + 2.2, "  ·  ".join(tiny), T_SMALL, MUT)
        y += 9.0
    return y


def stacked_h():
    return 3 * 9.0


# ---------------------------------------------------------------------------- designs
def design_A():
    """Combined first, then the task split. Closest in spirit to the retired HTML."""
    h = TOP + 7.6 + cat_bar_h() + GAP + 7.6 + matrix_h(False) + GAP + 4.0 + 4.0 + FOOT_H
    p = Page(h)
    y = panel_label(p, TOP, "A", "What the %d papers measured" % N,
                    "one outcome per paper, grouped into the four domains and the residual "
                    "Other; hatched = provisional")
    y = cat_bar_block(p, y)
    y += GAP
    y = panel_label(p, y, "B", "The same outcomes by study task",
                    "counts; a dash means no paper of that task fell in the category")
    y = matrix_block(p, y, within=False)
    y += GAP - 3.0
    y = legend_domains(p, 0.0, y) + 0.6
    yp = provenance_note(p, y, "hatch")
    footer(p, yp + 4.0)
    return p, h, "Design A"


def design_B():
    """Task-forward, the way S3's chosen design is. The mix shift is the finding."""
    h = TOP + 7.6 + stacked_h() + 5.0 + GAP + 7.6 + matrix_h(True) + GAP + 7.0 + FOOT_H
    p = Page(h)
    y = panel_label(p, TOP, "A", "The domain mix shifts with the study task",
                    "each bar is one task's outcomes, segmented by domain; segments too "
                    "narrow to carry a number are named beside the bar")
    y = stacked_by_task(p, y)
    y = legend_domains(p, 0.0, y + 1.0) + GAP - 3.4
    y = panel_label(p, y, "B", "Every category, within each task",
                    "count, and beneath it that category's share of the task's outcomes")
    y = matrix_block(p, y, within=True)
    y += GAP - 4.0
    yp = provenance_note(p, y)
    footer(p, yp + 4.0)
    return p, h, "Design B"


def design_C():
    """Provenance in the foreground: every category drawn twice."""
    ROW2 = 5.6
    h = TOP + 7.6 + (len(DOMS) * (DOMHEAD + 1.2) + 13 * ROW2) + GAP + 7.6 + stacked_h() \
        + 5.0 + GAP + 4.0 + FOOT_H
    p = Page(h)
    y = panel_label(p, TOP, "A", "All %d outcomes, and the %d the reviewers adjudicated"
                    % (N, NADJ),
                    "upper bar: all %d  |  lower open bar: the %d adjudicated outcomes only. "
                    "Where the two disagree, the claim rests on provisional data." % (N, NADJ))
    mx = max(CTOT[c] for c in CATORDER)
    for d in DOMS:
        p.rect(0, y - 2.4, W, 3.3, DCOL[d] if d != "9" else "#eeeeee",
               alpha=0.13 if d != "9" else 1.0)
        p.text(1.2, y, DOMLAB[d], T_SMALL, INK, weight="bold")
        p.text(W, y, "%d  ·  %d adjudicated" % (DTOT[d], DTOT[d] - DPROV[d]),
               T_SMALL, MUT, ha="right")
        y += DOMHEAD
        for c in [x for x in CATORDER if DOMOF[x] == d]:
            p.text(LABW, y + 0.6, p.fit(SHORT[c], LABW - 3.0, T_BODY), T_BODY, INK, ha="right")
            wa, wj = BARW * CTOT[c] / mx, BARW * ADJ[c] / mx
            if d == "9":
                p.rect(BARX, y - 2.2, wa, 2.1, "none", ec=MUT, lw=0.4, hatch="xxx")
            else:
                p.rect(BARX, y - 2.2, wa, 2.1, DCOL[d])
            p.rect(BARX, y + 0.5, wj, 2.1, "none", ec=INK, lw=0.45)
            p.text(BARX + max(wa, wj) + 1.6, y - 0.4, "%d" % CTOT[c], T_BODY, INK,
                   weight="bold")
            p.text(BARX + max(wa, wj) + 1.6, y + 2.4, "%d" % ADJ[c], T_SMALL, MUT)
            y += ROW2
        y += 1.2
    y += GAP
    y = panel_label(p, y, "B", "The domain mix by study task",
                    "every provisional outcome is a predictive study, so the predictive bar "
                    "is the one that rests entirely on them")
    y = stacked_by_task(p, y)
    y = legend_domains(p, 0.0, y + 1.0) + GAP - 7.4
    yp = provenance_note(p, y, "openbar")
    footer(p, yp + 4.0)
    return p, h, "Design C"


def design_D():
    """Divergence: the spread between the three task dots IS the finding."""
    ROW2 = 5.6
    AX0, AXW = 62.0, 96.0
    mxp = max(PCT(CT[(c, t)], TT[t]) for c in CATORDER for t in TASKS)
    top = 10 * (int(mxp / 10) + 1)
    h = TOP + 7.6 + 8.0 + 13 * ROW2 + GAP + 7.6 + matrix_h(False) + GAP + 9.5 + FOOT_H
    p = Page(h)
    y = panel_label(p, TOP, "A", "How far the tasks diverge, category by category",
                    "each dot is that category's share of one task's outcomes; the wider the "
                    "spread, the more the task decides what is measured")
    for g in range(0, top + 1, 10):
        x = AX0 + AXW * g / top
        p.line(x, y + 1.0, x, y + 5.0 + 13 * ROW2, RULE, 0.3)
        p.text(x, y, "%d%%" % g, T_SMALL, FAINT, ha="center")
    y += 5.0
    mk = {"Descriptive": "o", "Causal": "s", "Predictive": "^"}
    for c in CATORDER:
        d = DOMOF[c]
        p.text(LABW, y + 0.8, p.fit(SHORT[c], LABW - 4.0, T_BODY), T_BODY, INK, ha="right")
        xs = [AX0 + AXW * PCT(CT[(c, t)], TT[t]) / top for t in TASKS]
        p.line(min(xs), y, max(xs), y, MUT, 0.5)
        for t, x in zip(TASKS, xs):
            p.ax.plot([x], [y], marker=mk[t], markersize=3.1,
                      markerfacecolor=DCOL[d] if d != "9" else "#ffffff",
                      markeredgecolor=INK, markeredgewidth=0.4, linestyle="none")
        p.text(W, y + 0.8, "%d" % CTOT[c], T_BODY, INK, ha="right", weight="bold")
        y += ROW2
    y += GAP - 2.0
    cx = 0.0
    for t in TASKS:
        p.ax.plot([cx + 1.2], [y - 0.8], marker=mk[t], markersize=3.1,
                  markerfacecolor="#ffffff", markeredgecolor=INK, markeredgewidth=0.4,
                  linestyle="none")
        p.text(cx + 3.4, y, "%s (n=%d)" % (t, TT[t]), T_SMALL, MUT)
        cx += 3.4 + p.measure("%s (n=%d)" % (t, TT[t]), T_SMALL) + 6.0
    y += 6.5
    y = panel_label(p, y, "B", "The counts behind the dots", None)
    y = matrix_block(p, y, within=False)
    y += GAP - 4.0
    yp = provenance_note(p, y)
    footer(p, yp + 4.0)
    return p, h, "Design D"


def design_E():
    """One bar per category, segmented by task: size and mix in the same mark."""
    ROW2 = 4.8
    h = TOP + 7.6 + (len(DOMS) * (DOMHEAD + 1.2) + 13 * ROW2) + GAP + 7.6 + 5 * 5.6 \
        + GAP + 5.0 + 4.0 + FOOT_H
    p = Page(h)
    y = panel_label(p, TOP, "A", "Every category, and who measures it",
                    "bar length is the count; the segments are the descriptive, causal and "
                    "predictive papers within it")
    mx = max(CTOT[c] for c in CATORDER)
    for d in DOMS:
        p.rect(0, y - 2.4, W, 3.3, DCOL[d] if d != "9" else "#eeeeee",
               alpha=0.13 if d != "9" else 1.0)
        p.text(1.2, y, DOMLAB[d], T_SMALL, INK, weight="bold")
        p.text(W, y, "%d papers  ·  %.0f%%" % (DTOT[d], PCT(DTOT[d], N)),
               T_SMALL, MUT, ha="right")
        y += DOMHEAD
        for c in [x for x in CATORDER if DOMOF[x] == d]:
            p.text(LABW, y, p.fit(SHORT[c], LABW - 3.0, T_BODY), T_BODY, INK, ha="right")
            x = BARX
            for t in TASKS:
                v = CT[(c, t)]
                if not v:
                    continue
                w = BARW * v / mx
                if d == "9":
                    p.rect(x, y - 2.1, w, 2.4, "none", ec=MUT, lw=0.4,
                           hatch=TASKHATCH[t] if TASKHATCH[t] else "xxx")
                else:
                    p.rect(x, y - 2.1, w, 2.4, DCOL[d], hatch=TASKHATCH[t] or None,
                           ec="#ffffff", lw=0.3)
                x += w
            p.text(x + 1.6, y, "%d" % CTOT[c], T_BODY, INK, weight="bold")
            p.text(W, y, "%.1f%%" % PCT(CTOT[c], N), T_SMALL, MUT, ha="right")
            y += ROW2
        y += 1.2
    y += GAP
    y = panel_label(p, y, "B", "Domain totals", None)
    for d in DOMS:
        p.text(LABW, y, DOMLAB[d], T_BODY, INK, ha="right")
        w = BARW * DTOT[d] / max(DTOT.values())
        if d == "9":
            p.rect(BARX, y - 2.1, w, 2.4, "none", ec=MUT, lw=0.4, hatch="xxx")
        else:
            p.rect(BARX, y - 2.1, w, 2.4, DCOL[d])
        p.text(BARX + w + 1.6, y, "%d" % DTOT[d], T_BODY, INK, weight="bold")
        p.text(W, y, "%.1f%%  ·  %d provisional" % (PCT(DTOT[d], N), DPROV[d]),
               T_SMALL, MUT, ha="right")
        y += 5.6
    y += GAP - 4.0
    cx = 0.0
    for t in TASKS:
        p.rect(cx, y - 1.8, 3.0, 2.0, DCOL["1"], hatch=TASKHATCH[t] or None,
               ec="#ffffff", lw=0.3)
        p.text(cx + 4.0, y, "%s (n=%d)" % (t, TT[t]), T_SMALL, MUT)
        cx += 4.0 + p.measure("%s (n=%d)" % (t, TT[t]), T_SMALL) + 6.0
    y += 4.0
    yp = provenance_note(p, y)
    footer(p, yp + 4.0)
    return p, h, "Design E"


# ---------------------------------------------------------------------------- emit
def emit(p, h, stem, tag, formats=("png",)):
    base = os.path.join(OUTDIR, stem)
    p.fig.canvas.draw()
    rend = p.fig.canvas.get_renderer()
    mm = lambda px: px / p.fig.dpi * 25.4
    assert min(p.sizes) >= MIN_PT, min(p.sizes)
    assert h <= HMAX, (h, HMAX)
    spill, boxes = [], []
    for t in p.ax.texts:
        b = t.get_window_extent(rend)
        x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
        if x0 < -0.25 or x1 > W + 0.25 or y0 < -0.25 or y1 > h + 0.25:
            spill.append((round(x0, 1), round(x1, 1), round(y0, 1), round(y1, 1),
                          t.get_text()[:44]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill[:6]
    clash = []
    for i, (ya0, ya1, xa0, xa1, sa) in enumerate(boxes):
        for yb0, yb1, xb0, xb1, sb in boxes[i + 1:]:
            if (xa0 < xb1 - 0.15 and xa1 > xb0 + 0.15
                    and ya0 < yb1 - 0.15 and ya1 > yb0 + 0.15):
                clash.append((sa[:22], sb[:22], round(xa1, 1), round(xb0, 1)))
    assert not clash, clash[:6]

    os.makedirs(OUTDIR, exist_ok=True)
    if "pdf" in formats:
        p.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
    png = base + ".png"
    p.fig.savefig(png, dpi=600, facecolor="white")
    if "tif" in formats:
        im = Image.open(png)
        rgb = Image.new("RGB", im.size, "white")
        rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
        rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        im.close()
    plt.close(p.fig)
    if "png" not in formats:
        os.remove(png)

    if "pdf" in formats:
        for _k, _v in PdfReader(base + ".pdf").pages[0]["/Resources"]["/Font"].items():
            fo = _v.get_object()
            df = fo.get("/DescendantFonts")
            d = df[0].get_object() if df else fo
            desc = d.get("/FontDescriptor")
            assert d.get("/Subtype") != "/Type3" and desc and any(
                x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
            assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
    if "tif" in formats:
        t = Image.open(base + ".tif")
        assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0), \
            (t.mode, t.tag_v2.get(259), t.info.get("dpi"))
        t.close()
    sz = Image.open(base + ".png")
    px = sz.size
    sz.close()
    print("  %-9s %.0f x %.0f mm | %d x %d px | smallest type %.1f pt"
          % (tag, W, h, px[0], px[1], min(p.sizes)))
    for ext in formats:
        fp = base + "." + ext
        print("      %-62s %8.1f KB" % (fp, os.path.getsize(fp) / 1024))


BUILD = {"A": (design_A, "08_26_2026_S4_outcomes_designA"),
         "B": (design_B, "08_26_2026_S4_outcomes_designB"),
         "C": (design_C, "08_26_2026_S4_outcomes_designC"),
         "D": (design_D, "08_26_2026_S4_outcomes_designD"),
         "E": (design_E, "08_26_2026_S4_outcomes_designE")}

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["C"]
    fmts = ("png",) if len(args) > 1 else ("pdf", "tif", "png")
    print("Supplementary Figure S1 - study outcomes   (%s)" % ", ".join(fmts))
    for k in args:
        fn, stem = BUILD[k]
        pg, hh, tag = fn()
        emit(pg, hh, stem, tag, fmts)
