# -*- coding: utf-8 -*-
"""Supplementary Figure S4 - journal landscape. Print-native, five candidate designs.

ONE figure carrying where the 385 papers were published: the two competing 2022 journal
rankings and how far apart they are, why 87 papers sit in no JCR quartile at all, how
concentrated the 229 journals are, open access, subject field, and the journals themselves.

  A  both rankings + every one of the 229 journals, four columns
  B  both rankings + the SJR x JCR crosstab + the 48 journals that published more than one
  C  the long tail - concentration curve, the 20 largest, the 181 single-paper journals
  D  landscape overview - ranking, access, subject field, publisher country, leading journals
  E  by study task - ranking, access and venue by causal / descriptive / predictive

Same print contract as S1/S2/S7/S8: 180 mm wide, 6.5 pt type floor, Arial embedded,
TIFF RGB / LZW / 600 dpi, and the same assertions - type floor, nothing off the page, no
two text boxes touching, and the page height computed from the constants used to draw.

⚠ QUARTILES ARE ORDERED, so they take a single-hue ramp (dark Q1 -> pale Q4), not five
categorical hues: hue would imply five unrelated kinds. "Not ranked" is NOT a fifth
quartile - it is a different state - so it alone takes a contrasting hue.

⚠ SUBJECT FIELD IS READ PER PAPER, NEVER PER JOURNAL. The by-journal CSV carries
field/subfield/domain columns, but they are one arbitrary paper's OpenAlex topic pinned to
the whole journal: IJERPH is filed there as "Dentistry" although 16 of its 29 papers are
Medicine and only 1 is Dentistry, and Frontiers in Public Health is filed as "Economics".
The by-paper columns are per paper and are the ones used here.

    python code/figures/08_25_2026_S3_journal_landscape_figure.py [A..E]

No argument (or several) emits PNG only, for choosing from. One design letter emits
PDF + TIFF + PNG. Run from the repository root.
"""
import os
import sys
from collections import Counter, OrderedDict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
from PIL import Image
from pypdf import PdfReader

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})

OUTDIR = "outputs/figures"
W, HMAX, MIN_PT = 180.0, 245.0, 6.5
INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#7b848c", "#c8ced2"
ACC = "#0f5c6b"
T_PANEL, T_BODY, T_SMALL = 8.5, 7.0, 6.5

# quartiles: one hue, four values. "Not ranked" is a different state, so a different hue.
# ⚠ TONE, NOT JUST HUE. These are checked in greyscale as well as in colour, because a
# print run may be greyscale and 8% of male readers cannot use the hue at all. Luminance
# (0.299R+0.587G+0.114B): Q1 82 · Q2 131 · Q3 175 · Q4 212 · not ranked 61. "Not ranked"
# used to be #CC6677 at luminance 134 - three points from Q2 - so in greyscale the state
# the docstring insists must NOT read as a quartile read as exactly one.
QC = ["#16697a", "#4f97a3", "#8dbcc4", "#c3dade", "#7A1F35"]
LAB = ["Q1", "Q2", "Q3", "Q4", "Not ranked"]
SJR_L = ["Q1", "Q2", "Q3", "Q4", "-"]
JCR_L = ["Q1", "Q2", "Q3", "Q4", "None"]
# study task - categorical, three levels, Paul Tol muted
TC = {"Causal": "#332288", "Descriptive": "#44AA99", "Predictive": "#AA4499"}
# open-access route - categorical, named after the route it describes.
# ⚠ NO HEX MAY CARRY TWO MEANINGS ON ONE PAGE. hybrid was #44AA99, which is also
# Descriptive, and bronze was #CC6677, which is also "not ranked" - so a bronze segment in
# the access panel sat 20 mm from a rose "not ranked" bar meaning something else entirely.
# The docstring's own rule (a contrasting hue for "not ranked" so it cannot be read as a
# quartile) is worthless if that hue is then reused for an access route.
# ⚠ Fixing the hue collision cost a TONE separation the first time round: moving bronze to
# #882255 (luminance 70) put it 11 points from the green it sits beside (81), where the old
# #CC6677 had been 53 apart. A hairline separator makes two segments countable, not
# distinguishable. #AA6633 is 117 - 36 from green, 24 from hybrid, 44 from closed.
# Luminances now: gold 199 · diamond 188 · hybrid 141 · green 81 · bronze 117 · closed 161.
OAC = OrderedDict([("gold", "#DDCC77"), ("diamond", "#88CCEE"), ("hybrid", "#999933"),
                   ("green", "#117733"), ("bronze", "#AA6633"), ("closed", "#9aa2ab")])
NEUT = "#9aa2ab"


def lum(hexcol, alpha=1.0):
    """perceived luminance 0-255, flattened onto white at the given alpha - what a
    greyscale press sees, and what decides whether a label on top must be white or ink"""
    r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    v = 0.299 * r + 0.587 * g + 0.114 * b
    return v * alpha + 255.0 * (1.0 - alpha)


# ⚠ assert it, rather than trusting the eye: every meaning gets its own hue.
_used = [("Q1", QC[0]), ("Q2", QC[1]), ("Q3", QC[2]), ("Q4", QC[3]), ("not ranked", QC[4]),
         ("accent", ACC), ("neutral", NEUT)] + list(TC.items()) + list(OAC.items())
assert len(set(c.lower() for _, c in _used)) == len(_used) - 1, \
    "a colour carries two meanings: " + str(sorted(_used, key=lambda kv: kv[1]))
#            - 1 because "closed" deliberately shares the neutral grey NEUT
# ⚠ and assert the TONES too, within each scale a reader compares inside one panel. The
# two scales get different thresholds for a reason: the quartile ramp encodes ORDER, and it
# encodes it in tone, so tone alone must separate its levels (18). The access routes are a
# CATEGORICAL scale carrying its own labelled legend and a number inside every segment, so
# hue does the work and tone only has to keep neighbouring segments apart (10).
for _grp, _min, _what in ((QC, 18, "quartile"), (list(OAC.values()), 10, "access route")):
    _l = sorted(lum(c) for c in _grp)
    assert min(b - a for a, b in zip(_l, _l[1:])) >= _min, \
        ("two %s levels are within %d luminance points" % (_what, _min),
         [(c, round(lum(c))) for c in _grp])


# ---------------------------------------------------------------------------- data
P = pd.read_csv("data/journals/08_25_2026_journal_landscape_by_paper_385_public.csv",
                keep_default_na=False)
J = pd.read_csv("data/journals/08_25_2026_journal_landscape_by_journal_385_public.csv",
                keep_default_na=False)
NP, NJ = len(P), len(J)

SJR_N = [int((P.sjr_best_quartile == k).sum()) for k in SJR_L]
JCR_N = [int((P.jcr_2022_quartile == k).sum()) for k in JCR_L]
SJR_J = [int((J.sjr_best_quartile == k).sum()) for k in SJR_L]
JCR_J = [int((J.jcr_2022_quartile == k).sum()) for k in JCR_L]
SJR12, JCR12 = SJR_N[0] + SJR_N[1], JCR_N[0] + JCR_N[1]

# movement between the two rankings, over the papers both rankings place
_q = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
_both = P[(P.sjr_best_quartile != "-") & (P.jcr_2022_quartile != "None")]
BOTH = len(_both)
SAME = int(sum(_q[a] == _q[b] for a, b in zip(_both.sjr_best_quartile, _both.jcr_2022_quartile)))
DOWN = int(sum(_q[b] > _q[a] for a, b in zip(_both.sjr_best_quartile, _both.jcr_2022_quartile)))
UP = int(sum(_q[b] < _q[a] for a, b in zip(_both.sjr_best_quartile, _both.jcr_2022_quartile)))
XTAB = pd.crosstab(P.sjr_best_quartile, P.jcr_2022_quartile)


# ⚠ Precedence, not keyword-hunting. Several notes name more than one thing - a journal can
# be ESCI in 2022 AND delisted in 2024 - and what the reason column must report is why there
# is no 2022 quartile, which is the EARLIEST of these states. Getting the order wrong moves
# two journals and breaks the "54 of 87 delisted or suppressed" figure the Results quote.
def reason(note):
    s = note.lower()
    if "suppress" in s:
        return "JIF suppressed for citation anomalies"
    if "not in jcr by" in s:
        return "Not indexed in Web of Science at all"
    if "esci" in s:
        return "Emerging Sources index in 2022: a JIF, but no quartile"
    if "delist" in s:
        return "Delisted from WoS: no 2022 edition entry"
    return "UNCLASSIFIED: " + note[:60]


RSN_ORDER = ["Delisted from WoS: no 2022 edition entry",
             "Emerging Sources index in 2022: a JIF, but no quartile",
             "Not indexed in Web of Science at all",
             "JIF suppressed for citation anomalies"]
_jn = J[J.jcr_2022_quartile == "None"].copy()
_jn["reason"] = _jn.jcr_note.map(reason)
RSN_P = OrderedDict((r, int(_jn[_jn.reason == r].n_papers.sum())) for r in RSN_ORDER)
RSN_J = OrderedDict((r, int((_jn.reason == r).sum())) for r in RSN_ORDER)
DELSUP = RSN_P[RSN_ORDER[0]] + RSN_P[RSN_ORDER[3]]

# concentration
JS = J.sort_values(["n_papers", "journal"], ascending=[False, True]).reset_index(drop=True)
JS["rank"] = range(1, NJ + 1)
SINGLE = int((JS.n_papers == 1).sum())
MULTI = JS[JS.n_papers > 1].reset_index(drop=True)
TOPN = lambda n: int(JS.n_papers.head(n).sum())

# access, subject, publisher
OA_YES = int((P.scimago_open_access == "Yes").sum())
OA_NO = int((P.scimago_open_access == "No").sum())
OA_ROUTE = OrderedDict((k, int((P.oa_status == k).sum())) for k in OAC)
DOAJ_J = int(P.is_in_doaj.astype(str).isin(["True"]).sum())
OA_J = int((J.scimago_open_access == "Yes").sum())
DOAJ_JN = int(J.is_in_doaj.astype(str).isin(["True"]).sum())
PMC = int((P.in_pmc == "Yes").sum())
# ⚠ per PAPER. The by-journal field column is one paper's topic pinned to a whole journal.
FIELD = Counter(f if f else "(no topic assigned)" for f in P.field).most_common()
DOMAIN = Counter(d if d else "(none)" for d in P.domain).most_common()
PCTRY = Counter(P.publisher_country).most_common()
TASKS = ["Causal", "Descriptive", "Predictive"]
TASK_N = OrderedDict((t, int((P.Study_Type == t).sum())) for t in TASKS)

# ⚠ EVERYTHING DESIGN E PRINTS IS ASSERTED. The first version of this block guarded the
# candidate designs: three of its assertions covered numbers that appear only on designs
# A-D, while the task denominators, the whole access panel, the journal table and the
# "all 11 are predictive" sentence - all of them ON THE SHIPPED FIGURE - were unguarded.
# An assertion that does not cover what ships is decoration.
TASK_Q = OrderedDict(
    (t, {sc: [int((P[P.Study_Type == t][col] == lv).sum()) for lv in L]
         for sc, col, L in (("sjr", "sjr_best_quartile", SJR_L),
                            ("jcr", "jcr_2022_quartile", JCR_L))}) for t in TASKS)
TASK_OA = OrderedDict((t, OrderedDict(
    (k, int(((P.Study_Type == t) & (P.oa_status == k)).sum())) for k in OAC)) for t in TASKS)
# ⚠ "the N largest journals" needs a cut that cannot fall inside a tie. Two journals hold
# 4 papers, so a top-14 broke that tie alphabetically and dropped the better-ranked of the
# pair. Five or more papers is a stated rule with no tie at its boundary.
BIG = JS[JS.n_papers >= 5].reset_index(drop=True)
PUBYEAR = OrderedDict(sorted(Counter(P.pub_year).items()))
# the tasks that appear among the papers SJR does not rank - the panel B sentence is
# generated from this, never hardcoded
SJR_UNRANKED_TASKS = sorted(set(P[P.sjr_best_quartile == "-"].Study_Type))
PUBLISHED_IN_WINDOW = int(sum(v for k, v in PUBYEAR.items() if k <= 2021))
PUBLISHED_AFTER = NP - PUBLISHED_IN_WINDOW

assert (NP, NJ) == (385, 229), (NP, NJ)
assert SJR_N == [184, 125, 61, 4, 11], SJR_N
assert JCR_N == [81, 103, 76, 38, 87], JCR_N
assert list(RSN_P.values()) == [49, 27, 6, 5], RSN_P
assert list(RSN_J.values()) == [4, 22, 5, 2], RSN_J
assert not any(r.startswith("UNCLASSIFIED") for r in _jn.reason), \
    sorted(set(r for r in _jn.reason if r.startswith("UNCLASSIFIED")))
assert (BOTH, SAME, DOWN, UP) == (298, 124, 171, 3), (BOTH, SAME, DOWN, UP)
assert (SINGLE, len(MULTI)) == (181, 48), (SINGLE, len(MULTI))
assert (OA_YES, OA_NO) == (217, 168), (OA_YES, OA_NO)
assert FIELD[0] == ("Medicine", 220), FIELD[0]
assert DELSUP == 54, DELSUP
assert list(TASK_N.values()) == [229, 81, 75], TASK_N
assert TASK_Q["Causal"]["sjr"] == [113, 80, 34, 2, 0], TASK_Q["Causal"]
assert TASK_Q["Causal"]["jcr"] == [47, 67, 45, 20, 50], TASK_Q["Causal"]
assert TASK_Q["Descriptive"]["sjr"] == [33, 24, 22, 2, 0], TASK_Q["Descriptive"]
assert TASK_Q["Descriptive"]["jcr"] == [17, 13, 18, 17, 16], TASK_Q["Descriptive"]
assert TASK_Q["Predictive"]["sjr"] == [38, 21, 5, 0, 11], TASK_Q["Predictive"]
assert TASK_Q["Predictive"]["jcr"] == [17, 23, 13, 1, 21], TASK_Q["Predictive"]
assert [sum(v[sc]) for t, v in TASK_Q.items() for sc in ("sjr", "jcr")] == \
    [229, 229, 81, 81, 75, 75], "a task's quartile segments must sum to its n"
assert list(OA_ROUTE.values()) == [156, 29, 43, 36, 18, 103], OA_ROUTE
assert [sum(v.values()) for v in TASK_OA.values()] == [229, 81, 75], TASK_OA
# ⚠ the panel B sentence claims every SJR-unranked paper is predictive. Assert the CLAIM,
# not just the count behind it: the count was already asserted and would not have caught a
# causal paper moving into an unranked journal.
assert SJR_UNRANKED_TASKS == ["Predictive"], SJR_UNRANKED_TASKS
assert len(BIG) == 13 and int(BIG.n_papers.min()) == 5, len(BIG)
assert int((JS.n_papers == 4).sum()) == 2, "the >=5 cut exists to avoid this tie"
assert (JS.n_causal + JS.n_descriptive + JS.n_predictive == JS.n_papers).all()
# ⚠ the footer states these years. 4 papers published in 2021 sit INSIDE both 2022
# citation windows, which is why the footer no longer claims the rankings were compiled
# before any paper here could be cited in them.
assert PUBYEAR == OrderedDict([(2021, 4), (2022, 340), (2023, 41)]), PUBYEAR
assert (PUBLISHED_IN_WINDOW, PUBLISHED_AFTER) == (4, 381)


def qcol(v, scale):
    """colour for a quartile value as written in the data (SJR uses '-', JCR uses 'None')"""
    lv = SJR_L if scale == "sjr" else JCR_L
    return QC[lv.index(v)] if v in lv else NEUT


def qtxt(v, scale):
    lv = SJR_L if scale == "sjr" else JCR_L
    return LAB[lv.index(v)] if v in lv else "?"


# ---------------------------------------------------------------------------- canvas
class Page(object):
    def __init__(self, h):
        self.h = h
        self.fig = plt.figure(figsize=(W / 25.4, h / 25.4), dpi=600)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(h, 0)
        self.ax.axis("off")
        self.sizes = []
        self.guards = []
        self.ymax = 0.0

    def text(self, x, y, s, pt=T_BODY, col=INK, ha="left", weight="normal"):
        self.sizes.append(pt)
        self.ymax = max(self.ymax, y)
        return self.ax.text(x, y, s, fontsize=pt, color=col, ha=ha, va="baseline",
                            fontweight=weight)

    # ⚠ guard=True registers the rectangle for the bar-over-label check in emit(). The
    # clash test compares TEXT with TEXT, so a bar drawn straight through its own value
    # label passes every assertion and is only visible by eye - design D's "220 (57.1%)"
    # rendered as "20 (57.1%)" because the Medicine bar covered the first digit. Bars that
    # are MEANT to sit under a label (a stacked segment carrying its own number) are not
    # guarded; bars that must stay clear of text are.
    def rect(self, x, y, w, h, col, alpha=1.0, ec="none", lw=0.0, guard=False):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=col, alpha=alpha,
                                    edgecolor=ec, linewidth=lw))
        if guard:
            self.guards.append((x, y, w, h))

    def line(self, x0, y0, x1, y1, col=RULE, lw=0.4, ls="-"):
        self.ax.plot([x0, x1], [y0, y1], color=col, lw=lw, linestyle=ls,
                     solid_capstyle="butt")

    # ⚠ measure() runs several hundred times per design. fig.canvas.draw() renders the whole
    # 600 dpi canvas each call - a five-design run would not finish one design. Draw once for
    # a renderer, reuse it, and cache every (string, size, weight).
    def _renderer(self):
        if getattr(self, "_rend", None) is None:
            self.fig.canvas.draw()
            self._rend = self.fig.canvas.get_renderer()
        return self._rend

    # ⚠ weight is part of the measurement: bold Arial is materially wider than regular.
    def measure(self, s, pt, weight="normal"):
        key = (s, pt, weight)
        if not hasattr(self, "_mcache"):
            self._mcache = {}
        if key in self._mcache:
            return self._mcache[key]
        t = self.ax.text(0, 0, s, fontsize=pt, fontweight=weight)
        w = t.get_window_extent(self._renderer()).width / self.fig.dpi * 25.4
        t.remove()
        self._mcache[key] = w
        return w

    def fit(self, s, max_mm, pt, weight="normal"):
        if self.measure(s, pt, weight) <= max_mm:
            return s
        lo, hi, best = 3, len(s) - 1, s[:3]
        while lo <= hi:
            k = (lo + hi) // 2
            cand = s[:k].rstrip() + "…"
            if self.measure(cand, pt, weight) <= max_mm:
                best, lo = cand, k + 1
            else:
                hi = k - 1
        return best

    def wrap(self, s, max_mm, pt):
        out, cur = [], ""
        for word in s.split(" "):
            cand = (cur + " " + word) if cur else word
            if self.measure(cand, pt) > max_mm and cur:
                out.append(cur)
                cur = word
            else:
                cur = cand
        if cur:
            out.append(cur)
        return out


# ---------------------------------------------------------------------------- layout
TOP, GAP = 5.0, 5.0
FOOT_L = 5                                  # footer lines, asserted against the wrap
FOOT_H = 3.4 + FOOT_L * 3.0 + 1.0           # ⚠ computed from the constant used to draw
H_SUB, H_PLAIN = 10.0, 6.6      # panel head, with and without a sub-title
ROW = 2.65                      # table pitch, as S7/S2
RANK_ROW = 5.2
BAR_ROW = 4.1


def head(p, y0, letter, title, sub=None, x=0.0, sub_w=W):
    """⚠ asserts the panel starts below everything drawn so far - two panels drawn on top of
    each other leave the page bounds intact and only the clash test would see it.
    ⚠ the sub-title is TRUNCATED on measured width, and a panel occupying half the page
    passes its own half as sub_w."""
    assert y0 >= p.ymax - 0.01, ("panel %s starts above the previous panel" % letter,
                                 round(y0, 1), round(p.ymax, 1))
    if letter:
        p.text(x, y0, letter, 9.5, INK, weight="bold")
        p.text(x + 4.8, y0, p.fit(title, sub_w - 5.4, T_PANEL, "bold"), T_PANEL, INK,
               weight="bold")
    if sub:
        # ⚠ ASSERT, don't truncate. A sub-title quietly cut at the panel edge is how design
        # D shipped "…which for a broa…" - the reader loses the sentence and nothing warns.
        assert p.measure(sub, T_SMALL) <= sub_w - 5.4, \
            ("panel %s sub-title is %0.1f mm, %0.1f mm available" % (
                letter, p.measure(sub, T_SMALL), sub_w - 5.4), sub)
        p.text(x + 4.8, y0 + 3.4, sub, T_SMALL, MUT)
    p.ymax = y0
    return y0 + (H_SUB if sub else H_PLAIN)


def barw_for(p, bx, right, labels, pt=T_SMALL, pad=2.5):
    """the width a bar may use before it reaches the value column.
    ⚠ MEASURE the widest value label - a bar sized to a round fraction of the panel ran
    through "220 (57.1%)" and printed it as "20 (57.1%)"."""
    return right - pad - max(p.measure(s, pt) for s in labels) - bx


def para(p, y, s, col=MUT, nlines=1, x=0.0, w=W, pt=T_SMALL):
    """prose, wrapped on measured width and asserted against the height reserved for it.
    ⚠ nlines is a CONTRACT, not a maximum to fill: a one-line note that grows to two when a
    count widens must fail here, not silently overlap the panel below it."""
    lines = p.wrap(s, w, pt)
    assert len(lines) <= nlines, (len(lines), nlines, s[:50])
    for k, ln in enumerate(lines):
        p.text(x, y + k * 3.0, ln, pt, col)
    return y + nlines * 3.0


def seg(p, x, y, w, h, col, v, dark=None, alpha=1.0, ec="none"):
    """one segment of a stacked bar, with its count if the count FITS.
    ⚠ The threshold used to be a flat 7 mm, which suppressed a 5-paper segment (6.7% of a
    task) and left four of six rows in panel B visibly failing to sum to their own n.
    Measure the label instead - a two-digit number needs 3.8 mm, not 7 - and hand back
    whatever still would not fit so the caller can disclose it rather than drop it.
    ⚠ The hairline white separator is what lets two dark segments (green beside bronze)
    stay apart in greyscale."""
    # ⚠ derive the label colour from the fill it sits on. Passing "dark" by index (k < 2)
    # silently goes wrong the moment a palette entry changes tone - which it just did.
    if dark is None:
        dark = lum(col, alpha) < 140
    p.rect(x, y, w, h, col, alpha=alpha, ec=ec, lw=0.5 if ec != "none" else 0.0)
    if w > 0.4:
        p.rect(x + w - 0.22, y, 0.22, h, "white")
    lab = str(v)
    if w >= p.measure(lab, T_SMALL) + 1.4:
        p.text(x + w / 2.0, y + h - 1.0, lab, T_SMALL, "white" if dark else INK, ha="center")
        return None
    return v if v else None


def legend(p, x, y, items, pt=T_SMALL):
    """swatch + label pairs laid out left to right on measured widths"""
    for lab, col in items:
        p.rect(x, y - 1.5, 2.2, 1.8, col)
        p.text(x + 3.0, y, lab, pt, MUT)
        x += 3.0 + p.measure(lab, pt) + 4.4
    return x


# ---------------------------------------------------------------------------- panels
def rank_panel(p, y0, letter="A"):
    """the anchor panel, in every design: the same 385 papers under both 2022 rankings"""
    yc = head(p, y0, letter, "Two rankings of the same 385 papers",
              "filled bar: SCImago SJR 2022   │   open bar: Clarivate JCR 2022 "
              "(journal impact factor)")
    x0, bw, mx = 36.0, 76.0, float(max(SJR_N + JCR_N))
    p.text(134.0, yc - 3.4, "SCImago SJR", T_SMALL, ACC, ha="right")
    p.text(W, yc - 3.4, "Clarivate JCR", T_SMALL, ACC, ha="right")
    for i, lab in enumerate(LAB):
        yy = yc + i * RANK_ROW
        p.text(34.0, yy, lab, T_SMALL, INK, ha="right")
        p.rect(x0, yy - 2.7, bw * SJR_N[i] / mx, 1.9, QC[i])
        p.rect(x0, yy - 0.5, bw * JCR_N[i] / mx, 1.4, "none", ec=QC[i], lw=0.5)
        p.text(134.0, yy, "%d  (%.1f%%)" % (SJR_N[i], 100.0 * SJR_N[i] / NP), T_SMALL, INK,
               ha="right")
        p.text(W, yy, "%d  (%.1f%%)" % (JCR_N[i], 100.0 * JCR_N[i] / NP), T_SMALL, INK,
               ha="right")
    yb = yc + len(LAB) * RANK_ROW
    para(p, yb, "Q1–Q2 holds %d papers (%.1f%%) on SJR but %d (%.1f%%) on JCR. Of the "
                "%d papers both rankings place, %d (%.1f%%) sit LOWER on JCR, %d the same, "
                "%d higher."
         % (SJR12, 100.0 * SJR12 / NP, JCR12, 100.0 * JCR12 / NP, BOTH, DOWN,
            100.0 * DOWN / BOTH, SAME, UP), INK, 1)
    return yb + 1.6


RANK_H = H_SUB + len(LAB) * RANK_ROW + 1.6


def xtab_panel(p, y0, letter):
    yc = head(p, y0, letter, "Where the two rankings disagree",
              "rows SJR 2022, columns JCR 2022; shading is the count, outlined cells "
              "are the papers both rankings put in the SAME quartile")
    lx, cx, cw, rh = 30.0, 34.0, 24.0, 4.7
    mx = float(XTAB.values.max())
    for k, cl in enumerate(JCR_L):
        p.text(cx + k * cw + cw - 3.0, yc - 3.2, LAB[k], T_SMALL, ACC, ha="right")
    for i, sl in enumerate(SJR_L):
        yy = yc + i * rh
        p.text(lx, yy, LAB[i], T_SMALL, INK, ha="right")
        p.rect(31.0, yy - 1.9, 1.6, 1.8, QC[i])
        tot = SJR_N[i]
        for k, cl in enumerate(JCR_L):
            v = int(XTAB.loc[sl, cl]) if (sl in XTAB.index and cl in XTAB.columns) else 0
            x = cx + k * cw
            p.rect(x, yy - 3.2, cw - 2.0, 4.3, ACC, alpha=0.06 + 0.34 * (v / mx) ** 0.5,
                       # ⚠ not-ranked/not-ranked sits on the diagonal but is NOT
                       # agreement - neither ranking places those 11 papers at all.
                       ec=ACC if (i == k and i < 4 and v) else "none", lw=0.6)
            p.text(x + cw - 4.0, yy, str(v) if v else "·", T_SMALL,
                   INK if v else FAINT, ha="right")
        p.text(W, yy, "%d" % tot, T_SMALL, MUT, ha="right")
    yy = yc + len(SJR_L) * rh
    p.text(lx, yy, "all papers", T_SMALL, MUT, ha="right")
    for k, cl in enumerate(JCR_L):
        p.text(cx + k * cw + cw - 4.0, yy, "%d" % JCR_N[k], T_SMALL, MUT, ha="right")
    p.text(W, yy, "%d" % NP, T_SMALL, MUT, ha="right")
    return yy + 1.0


XTAB_H = H_SUB + (len(SJR_L) + 1) * 4.7 + 1.0


def unranked_panel(p, y0, letter, wide=True):
    yc = head(p, y0, letter,
              "Why %d papers have no JCR quartile" % JCR_N[4],
              "%d of the %d (%.0f%%) are in journals the Web of Science had dropped or "
              "suppressed by the 2022 edition" % (DELSUP, JCR_N[4], 100.0 * DELSUP / JCR_N[4]))
    labw, bw = 74.0 if wide else 66.0, 56.0
    mx = float(max(RSN_P.values()))
    for i, r in enumerate(RSN_ORDER):
        yy = yc + i * BAR_ROW
        p.text(labw, yy, p.fit(r, labw - 3.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(labw + 2.0, yy - 1.9, bw * RSN_P[r] / mx, 2.0, QC[4], guard=True)
        p.text(labw + 3.4 + bw * RSN_P[r] / mx, yy, "%d papers" % RSN_P[r], T_SMALL, INK)
        p.text(W, yy, "%d journal%s" % (RSN_J[r], "" if RSN_J[r] == 1 else "s"), T_SMALL,
               FAINT, ha="right")
    return yc + len(RSN_ORDER) * BAR_ROW


UNRANK_H = H_SUB + len(RSN_ORDER) * BAR_ROW


NOTE_L = 2


def unranked_note(p, y):
    """the same content as prose, for a design whose height is spent on the table.
    ⚠ wrapped on MEASURED width - hand-split lines run off the page the moment a count
    changes width."""
    short = {RSN_ORDER[0]: "delisted from WoS", RSN_ORDER[1]: "Emerging Sources index",
             RSN_ORDER[2]: "never indexed in WoS", RSN_ORDER[3]: "JIF suppressed"}
    s = ("Why %d papers have no JCR quartile:  %s.  %d of the %d (%.0f%%) are in journals "
         "the Web of Science had dropped or suppressed by the time the 2022 edition was "
         "compiled." % (JCR_N[4],
                        "  │  ".join("%s %d papers in %d journals"
                                     % (short[r], RSN_P[r], RSN_J[r]) for r in RSN_ORDER),
                        DELSUP, JCR_N[4], 100.0 * DELSUP / JCR_N[4]))
    lines = p.wrap(s, W, T_SMALL)
    assert len(lines) <= NOTE_L, (len(lines), NOTE_L)
    for k, ln in enumerate(lines):
        p.text(0, y + k * 3.0, ln, T_SMALL, INK)
    return y + NOTE_L * 3.0


def access_panel(p, y0, letter):
    yc = head(p, y0, letter, "Open access",
              "route to the article on the fetch date (OpenAlex/Unpaywall); “closed” "
              "is no free copy found, not proof that none exists")
    labw, bw = 30.0, 62.0
    mx = float(max(OA_ROUTE.values()))
    for i, (k, v) in enumerate(OA_ROUTE.items()):
        yy = yc + i * BAR_ROW
        p.text(labw, yy, k, T_SMALL, INK, ha="right")
        p.rect(labw + 2.0, yy - 1.9, bw * v / mx, 2.0, OAC[k], guard=True)
        p.text(labw + 3.4 + bw * v / mx, yy, "%d  (%.1f%%)" % (v, 100.0 * v / NP), T_SMALL, MUT)
    yb = yc + len(OA_ROUTE) * BAR_ROW
    para(p, yb, "By journal rather than article: %d of the %d papers (%.1f%%) are in a "
                "fully open-access journal (%d of %d journals), %d (%.1f%%) in a DOAJ "
                "journal. %d papers (%.1f%%) are in PubMed Central; all %d are MEDLINE-indexed."
         % (OA_YES, NP, 100.0 * OA_YES / NP, OA_J, NJ, DOAJ_J, 100.0 * DOAJ_J / NP,
            PMC, 100.0 * PMC / NP, NP), MUT, 2)
    return yb + 2 * 3.0 + 0.6


ACCESS_H = H_SUB + len(OA_ROUTE) * BAR_ROW + 6.6


def access_bar(p, y0, letter):
    """the same six routes as ONE full-width bar, for a design whose height is spent
    elsewhere - a third of the panel version's height"""
    yc = head(p, y0, letter, "Open access",
              "route to the article on the fetch date (OpenAlex/Unpaywall); “closed” "
              "is no free copy found, not proof that none exists")
    x = 0.0
    for k, v in OA_ROUTE.items():
        wseg = W * v / float(NP)
        p.rect(x, yc - 3.0, wseg, 4.0, OAC[k])
        # ⚠ a segment carries its label only if it is wide enough - 8 mm at 6.5 pt, tuned so
        # the narrowest real segment (bronze, 18/385 = 8.4 mm) still shows its number
        if wseg >= 8.0:
            p.text(x + wseg / 2.0, yc - 0.7, str(v), T_SMALL,
                   "white" if k in ("green", "closed") else INK, ha="center")
        x += wseg
    legend(p, 0.0, yc + 5.4, [("%s %.0f%%" % (k, 100.0 * v / NP), OAC[k])
                              for k, v in OA_ROUTE.items()])
    para(p, yc + 9.4, "By journal rather than article: %d papers (%.1f%%) are in a fully "
                      "open-access journal (%d of %d journals) and %d (%.1f%%) in a DOAJ "
                      "journal. %d (%.1f%%) are in PubMed Central; all %d are MEDLINE-indexed."
         % (OA_YES, 100.0 * OA_YES / NP, OA_J, NJ, DOAJ_J, 100.0 * DOAJ_J / NP, PMC,
            100.0 * PMC / NP, NP), MUT, 2)
    return yc + 9.4 + 2 * 3.0 + 0.6


ACCBAR_H = H_SUB + 9.4 + 6.6


def subject_panel(p, y0, letter, nf=9, x=0.0, w=W):
    """⚠ x/w so this can sit BESIDE another panel rather than below it - stacking the two
    half-page panels cost 46 mm of height for space nothing used."""
    yc = head(p, y0, letter, "Subject field",
              "each paper's own OpenAlex primary topic, not its journal's", sub_w=w)
    items = FIELD[:nf]
    rest = sum(v for _, v in FIELD[nf:])
    labw = x + 0.42 * w
    bx = labw + 2.0
    vals = ["%d  (%.1f%%)" % (v, 100.0 * v / NP) for _, v in FIELD] +            ["%d  (%.1f%%)" % (rest, 100.0 * rest / NP)]
    bw = barw_for(p, bx, x + w, vals)
    mx = float(items[0][1])
    for i, (k, v) in enumerate(items):
        yy = yc + i * BAR_ROW
        p.text(labw, yy, p.fit(k, 0.42 * w - 3.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(bx, yy - 1.9, bw * v / mx, 2.0, ACC if i == 0 else NEUT, guard=True)
        p.text(x + w, yy, "%d  (%.1f%%)" % (v, 100.0 * v / NP), T_SMALL, MUT, ha="right")
    yy = yc + len(items) * BAR_ROW
    p.text(labw, yy, "%d further fields" % len(FIELD[nf:]), T_SMALL, MUT, ha="right")
    p.rect(bx, yy - 1.9, bw * rest / mx, 2.0, "none", ec=NEUT, lw=0.5)
    p.text(x + w, yy, "%d  (%.1f%%)" % (rest, 100.0 * rest / NP), T_SMALL, MUT, ha="right")
    yb = yy + BAR_ROW
    para(p, yb, "By OpenAlex domain: " + " │ ".join(
        "%s %d (%.1f%%)" % (k, v, 100.0 * v / NP) for k, v in DOMAIN if v > 1), MUT, 2,
         x=x, w=w)
    return yb + 2 * 3.0 + 0.6


def subject_h(nf=9):
    return H_SUB + (nf + 1) * BAR_ROW + 6.6


def country_panel(p, y0, letter, nc=8, x=0.0, w=W):
    yc = head(p, y0, letter, "Publisher country of the journal", None, x=x,
              sub_w=w)
    items = PCTRY[:nc]
    rest = sum(v for _, v in PCTRY[nc:])
    labw = x + 0.34 * w
    bx = labw + 2.0
    vals = ["%d  (%.1f%%)" % (v, 100.0 * v / NP) for _, v in PCTRY] +            ["%d  (%.1f%%)" % (rest, 100.0 * rest / NP)]
    bw = barw_for(p, bx, x + w, vals)
    mx = float(items[0][1])
    for i, (k, v) in enumerate(items):
        yy = yc + i * BAR_ROW
        p.text(labw, yy, p.fit(k, 0.34 * w - 3.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(bx, yy - 1.9, bw * v / mx, 2.0, QC[0] if k != "Saudi Arabia" else QC[4],
               guard=True)
        p.text(x + w, yy, "%d  (%.1f%%)" % (v, 100.0 * v / NP), T_SMALL, MUT, ha="right")
    yy = yc + len(items) * BAR_ROW
    p.text(labw, yy, "%d further" % len(PCTRY[nc:]), T_SMALL, MUT, ha="right")
    p.rect(bx, yy - 1.9, bw * rest / mx, 2.0, "none", ec=NEUT, lw=0.5)
    p.text(x + w, yy, "%d  (%.1f%%)" % (rest, 100.0 * rest / NP), T_SMALL, MUT, ha="right")
    return yy + BAR_ROW


def country_h(nc=8):
    return H_PLAIN + (nc + 1) * BAR_ROW


def conc_panel(p, y0, letter, plot_h=54.0, ntop=14):
    """cumulative share of papers over journals ranked by size, with the top-N beside it"""
    yc = head(p, y0, letter, "A very long tail",
              "%d of the %d journals (%.0f%%) published exactly one of the %d papers"
              % (SINGLE, NJ, 100.0 * SINGLE / NJ, NP))
    px, py, pw = 14.0, yc, 74.0
    p.rect(px, py, pw, plot_h, "none", ec=RULE, lw=0.5)
    p.line(px, py + plot_h, px + pw, py, FAINT, 0.5, ":")
    run, xs, ys = 0, [px], [py + plot_h]
    for i, r in JS.iterrows():
        run += r.n_papers
        xs.append(px + pw * (i + 1) / NJ)
        ys.append(py + plot_h - plot_h * run / NP)
    p.ax.plot(xs, ys, color=ACC, lw=1.0)
    run = 0
    for i, r in JS.iterrows():
        run += r.n_papers
        if i + 1 in (10, 20, 50):
            cx, cy = px + pw * (i + 1) / NJ, py + plot_h - plot_h * run / NP
            p.ax.plot([cx], [cy], "o", ms=2.4, color=QC[4])
            p.text(cx + 1.8, cy - 0.8, "top %d → %.1f%%" % (i + 1, 100.0 * run / NP),
                   T_SMALL, INK)
    p.text(px - 1.5, py + 1.6, "100%", T_SMALL, FAINT, ha="right")
    p.text(px - 1.5, py + plot_h, "0%", T_SMALL, FAINT, ha="right")
    p.text(px, py + plot_h + 3.4, "the %d journals, largest first" % NJ, T_SMALL, FAINT)
    p.text(px, py + plot_h + 6.4, "cumulative share of the %d papers; dotted line = every "
                                  "journal one paper" % NP, T_SMALL, FAINT)
    # the largest journals, beside the plot rather than below it
    p.text(W, yc - 3.4, "The %d largest journals, bar colour: SJR quartile" % ntop,
           T_SMALL, ACC, ha="right")
    labw, bw = 152.0, 22.0
    mx = float(JS.n_papers.max())
    for i, r in JS.head(ntop).iterrows():
        yy = yc + 1.0 + i * 3.6
        p.text(labw, yy, p.fit(str(r.journal), 56.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(labw + 2.0, yy - 1.9, bw * r.n_papers / mx, 2.0,
               qcol(r.sjr_best_quartile, "sjr"), guard=True)
        p.text(W, yy, str(int(r.n_papers)), T_SMALL, INK, ha="right")
    # ⚠ the two blocks sit SIDE BY SIDE - take the taller, never the sum
    return max(py + plot_h + 6.4, yc + 1.0 + (ntop - 1) * 3.6) + 1.0


def conc_h(plot_h=54.0, ntop=14):
    return H_SUB + max(plot_h + 6.4, 1.0 + (ntop - 1) * 3.6) + 1.0


def single_panel(p, y0, letter):
    """the 181 journals that published exactly one paper, profiled rather than listed"""
    one = JS[JS.n_papers == 1]
    yc = head(p, y0, letter, "The %d journals that published exactly one paper" % SINGLE,
              "%.1f%% of the journals, %.1f%% of the papers: too many to name, so they "
              "are profiled" % (100.0 * SINGLE / NJ, 100.0 * SINGLE / NP))
    rows = [("SJR quartile", [(LAB[i], int((one.sjr_best_quartile == k).sum()), QC[i])
                              for i, k in enumerate(SJR_L)]),
            ("JCR quartile", [(LAB[i], int((one.jcr_2022_quartile == k).sum()), QC[i])
                              for i, k in enumerate(JCR_L)]),
            ("open access", [("open", int((one.scimago_open_access == "Yes").sum()), QC[0]),
                             ("closed", int((one.scimago_open_access == "No").sum()), NEUT)])]
    # ⚠ The bar has to STOP well short of the recap on the right. At 108 mm wide it ended at
    # 142 and the recap - which is 50 mm of text right-aligned at the page edge - began at
    # 130, so an in-bar label and the recap overlapped. The recap is the complete record
    # (every segment, however thin), so the bar gives way to it, not the other way round.
    x0, bw = 32.0, 84.0
    for i, (lab, segs) in enumerate(rows):
        yy = yc + i * 6.2
        p.text(x0 - 2.0, yy, lab, T_SMALL, INK, ha="right")
        x, tot = x0, float(sum(v for _, v, _ in segs))
        for name, v, col in segs:
            wseg = bw * v / tot
            p.rect(x, yy - 2.9, wseg, 3.4, col)
            s = "%s %d" % (name, v) if wseg >= 15.0 else (str(v) if wseg >= 5.5 else "")
            if s:
                p.text(x + wseg / 2.0, yy - 0.9, s, T_SMALL,
                       "white" if col in (QC[0], QC[1]) else INK, ha="center")
            x += wseg
        p.text(W, yy, " │ ".join("%s %d" % (n, v) for n, v, _ in segs if v), T_SMALL,
               MUT, ha="right")
    return yc + len(rows) * 6.2


SINGLE_H = H_SUB + 3 * 6.2


def task_panel(p, y0, letter):
    yc = head(p, y0, letter, "Venue by study task",
              "each task's papers split across the two rankings; "
              "filled row SJR 2022, open row JCR 2022")
    x0, bw, rh = 44.0, 96.0, 10.4
    for i, t in enumerate(TASKS):
        sub = P[P.Study_Type == t]
        n = TASK_N[t]
        yy = yc + i * rh
        p.text(x0 - 2.0, yy, "%s  n = %d" % (t, n), T_SMALL, INK, ha="right")
        p.rect(x0 - 33.0, yy - 2.2, 1.8, 2.0, TC[t])
        for row, sc in enumerate(("sjr", "jcr")):
            x, missing = x0, []
            for k, v in enumerate(TASK_Q[t][sc]):
                wseg = bw * v / float(n)
                if row == 0:
                    left = seg(p, x, yy - 2.9, wseg, 3.2, QC[k], v)
                else:
                    left = seg(p, x, yy + 1.4, wseg, 3.2, QC[k], v, alpha=0.38, ec=QC[k])
                if left:
                    missing.append("%s %d" % (LAB[k], left))
                x += wseg
            # ⚠ a segment too narrow for its own number is NOT dropped - it is named here,
            # so every row still reconciles with the n printed beside it.
            key = "%s Q1–Q2 %.0f%%" % (sc.upper(), 100.0 * (TASK_Q[t][sc][0]
                                                            + TASK_Q[t][sc][1]) / n)
            p.text(W, yy - 0.8 + row * 4.4, key + ("   · " + ", ".join(missing)
                                                   if missing else ""), T_SMALL, MUT,
                   ha="right")
    yb = yc + len(TASKS) * rh
    # ⚠ generated from the data, including the word "predictive" - see SJR_UNRANKED_TASKS.
    para(p, yb, "Descriptive papers sit lowest on both scales: %.0f%% are in a JCR Q4 "
                "journal against %.0f%% of causal papers. All %d papers whose journal SJR "
                "does not rank are %s."
         % (100.0 * TASK_Q["Descriptive"]["jcr"][3] / TASK_N["Descriptive"],
            100.0 * TASK_Q["Causal"]["jcr"][3] / TASK_N["Causal"],
            SJR_N[4], SJR_UNRANKED_TASKS[0].lower()), INK, 1)
    return yb + 3.0 + 0.6


TASK_H = H_SUB + 3 * 10.4 + 3.6


def task_access_panel(p, y0, letter):
    # ⚠ SAY WHAT "OPEN" MEANS. The panel counted every route but closed - which includes
    # green (a repository copy only; the version of record stays paywalled) and bronze
    # (free to read at the publisher's discretion, no licence). That is the most generous
    # of several defensible definitions and it moves the answer by 12-16 points, so the
    # stricter figure is printed underneath rather than left to the reader to guess.
    yc = head(p, y0, letter, "Open access by study task",
              "route to the article on 25 July 2026; “% open” counts every route except closed")
    x0, bw, rh = 44.0, 96.0, 5.2
    for i, t in enumerate(TASKS):
        n = TASK_N[t]
        yy = yc + i * rh
        p.text(x0 - 2.0, yy, "%s  n = %d" % (t, n), T_SMALL, INK, ha="right")
        x, missing = x0, []
        for k, col in OAC.items():
            v = TASK_OA[t][k]
            wseg = bw * v / float(n)
            left = seg(p, x, yy - 2.6, wseg, 3.0, col, v)
            if left:
                missing.append("%s %d" % (k, left))
            x += wseg
        p.text(W, yy, "%.0f%% open" % (100.0 * (n - TASK_OA[t]["closed"]) / n)
               + ("   · " + ", ".join(missing) if missing else ""), T_SMALL, MUT, ha="right")
    yb = yc + len(TASKS) * rh
    legend(p, 44.0, yb, [(k, v) for k, v in OAC.items()])
    strict = [100.0 * sum(TASK_OA[t][k] for k in ("gold", "diamond", "hybrid")) / TASK_N[t]
              for t in TASKS]
    # ⚠ "free at the publisher" also describes bronze, which is exactly the route being
    # excluded - the distinguishing feature is the licence, not the location.
    para(p, yb + 3.6, "Counting only gold, diamond and hybrid (free at the publisher under "
                      "an open licence): causal %.0f%%, descriptive %.0f%%, predictive %.0f%%."
         % tuple(strict), MUT, 1)
    return yb + 3.6 + 3.0


TASKACC_H = H_SUB + 3 * 5.2 + 3.6 + 3.0


# ---------------------------------------------------------------------------- journal tables
# ⚠ Column positions are fractions of the COLUMN width, and the leftmost of them has to
# clear x = 0 in the FIRST column - a right-aligned rank at 0.040 cw put "10" at -0.9 mm,
# off the page, which only the spill assertion saw. The quartile chips sit clear of the
# right-aligned text beside them, because a chip is a rectangle and the clash test only
# looks at text.
FR_SLIM = dict(rank=.076, name=.098, namemax=.500, pap=.679,
               sjrchip=.726, sjr=.845, jcrchip=.881, jcr=1.0)
FR_WIDE = dict(rank=.040, name=.052, namemax=.440, bar=.520, barmax=.090, pap=.672,
               task=.715, taskstep=.048, sjrchip=.855, sjr=.915, jcrchip=.940, jcr=1.0)


def _quart(p, x, cw, y, val, sc, FR, which):
    """⚠ the chip hangs off the MEASURED left edge of its own label, not off a column
    fraction: at a fraction the gap between chip and letter scales with the column, so the
    same code that looked right in a 42 mm column left a 10 mm hole in a 180 mm one."""
    c, t = qcol(val, sc), qtxt(val, sc)
    lab = "n/a" if t == "Not ranked" else t
    tw = p.measure(lab, T_SMALL)
    p.rect(x + FR[which] * cw - tw - 3.0, y - 1.6, 1.5, 1.7, c, guard=True)
    p.text(x + FR[which] * cw, y, lab, T_SMALL, INK if t != "Not ranked" else FAINT,
           ha="right")


def jrow(p, x, y, cw, r, mode):
    """one journal. mode 'slim' (name, papers, both quartiles) or 'wide' (adds the task mix)"""
    FR = FR_SLIM if mode == "slim" else FR_WIDE
    p.text(x + FR["rank"] * cw, y, str(int(r["rank"])), T_SMALL, FAINT, ha="right")
    p.text(x + FR["name"] * cw, y, p.fit(str(r.journal), FR["namemax"] * cw, T_SMALL),
           T_SMALL, INK)
    if mode == "wide":
        p.rect(x + FR["bar"] * cw, y - 1.75,
               max(FR["barmax"] * cw * r.n_papers / float(JS.n_papers.max()), 0.18), 1.9,
               ACC, guard=True)
    p.text(x + FR["pap"] * cw, y, str(int(r.n_papers)), T_SMALL, INK, ha="right")
    if mode == "wide":
        for k, (fk, col) in enumerate((("n_causal", TC["Causal"]),
                                       ("n_descriptive", TC["Descriptive"]),
                                       ("n_predictive", TC["Predictive"]))):
            v = int(r[fk])
            p.text(x + (FR["task"] + FR["taskstep"] * k) * cw, y, str(v) if v else "·",
                   T_SMALL, col if v else FAINT, ha="right")
    _quart(p, x, cw, y, r.sjr_best_quartile, "sjr", FR, "sjr")
    _quart(p, x, cw, y, r.jcr_2022_quartile, "jcr", FR, "jcr")


def jhead(p, x, y, cw, mode):
    FR = FR_SLIM if mode == "slim" else FR_WIDE
    p.text(x + FR["rank"] * cw, y, "#", T_SMALL, FAINT, ha="right")
    p.text(x + FR["name"] * cw, y, "Journal", T_SMALL, FAINT)
    p.text(x + FR["pap"] * cw, y, "Papers" if mode == "wide" else "Pap.", T_SMALL, FAINT,
           ha="right")
    if mode == "wide":
        for k, lab in enumerate(("C", "D", "P")):
            p.text(x + (FR["task"] + FR["taskstep"] * k) * cw, y, lab, T_SMALL, FAINT,
                   ha="right")
    p.text(x + FR["sjr"] * cw, y, "SJR", T_SMALL, FAINT, ha="right")
    p.text(x + FR["jcr"] * cw, y, "JCR", T_SMALL, FAINT, ha="right")
    p.line(x, y + 1.1, x + cw, y + 1.1, RULE, 0.5)


def jtable(p, y0, letter, title, sub, rows, ncol, mode, gut=4.0, rw=ROW):
    yc = head(p, y0, letter, title, sub)
    cw = (W - gut * (ncol - 1)) / ncol
    per = (len(rows) + ncol - 1) // ncol
    for c in range(ncol):
        jhead(p, c * (cw + gut), yc, cw, mode)
    for i, (_, r) in enumerate(rows.iterrows()):
        ci, ri = i // per, i % per
        jrow(p, ci * (cw + gut), yc + 3.8 + ri * rw, cw, r, mode)
    return yc + 3.8 + (per - 1) * rw


def jtable_h(nrows, ncol, sub=True, rw=ROW):
    per = (nrows + ncol - 1) // ncol
    return (H_SUB if sub else H_PLAIN) + 3.8 + (per - 1) * rw


def tail_note(p, y, journals, nlines, lead=None):
    """⚠ name what fits, then COUNT the rest - a wrapped list of 181 names is 40 lines"""
    # ⚠ truncate each NAME as well as the line. NLM titles carry the sponsoring-society
    # subtitle - "American journal of orthodontics and dentofacial orthopedics : official
    # publication of the American Association of Orthodontists, its constituent societies,
    # and the American Board of Orthodontics" measures 340 mm at 6.5 pt, so one item alone
    # ran a whole line 13 mm off the page.
    items = [p.fit(str(r.journal), 58.0, T_SMALL) for _, r in journals.iterrows()]
    lines, cur, shown = [], "", 0
    for n, it in enumerate(items):
        cand = (cur + ", " + it) if cur else it
        if p.measure(cand, T_SMALL) > W - 2.0:
            lines.append(cur)
            if len(lines) >= nlines - 1:
                shown = n
                break
            cur = it
        else:
            cur = cand
    else:
        if cur:
            lines.append(cur)
        shown = len(items)
    rest = len(items) - shown
    if rest > 0:
        lines.append("… and %d further journals, each with one paper" % rest)
    assert len(lines) <= nlines, (len(lines), nlines)
    # ⚠ a block of names with no lead-in reads as an orphan: the reader meets 170
    # journal titles with nothing saying what set they are.
    if lead:
        p.text(0, y, lead, T_SMALL, INK)
        y += 3.2
    for k, ln in enumerate(lines):
        p.text(0, y + k * 2.9, ln, T_SMALL, MUT)
    return y + nlines * 2.9


def footer(p, y, subject=False, access=True, doaj=False, indexing=False):
    """⚠ wrapped on measured width, never hand-split: the first version was split by hand and
    ran 70 mm off the right edge of the page.
    ⚠ CREDIT ONLY WHAT THE DESIGN SHOWS. This footer described subject field, DOAJ and
    MEDLINE/PMC on a design carrying none of them, inherited from the candidates that did.
    ⚠⚠ AND IT CLAIMED SOMETHING FALSE. "Both were compiled before any paper in this sample
    could be cited in them" is wrong for the 4 papers published in 2021: JCR 2022 counts
    2022 citations to 2020-21 work and SJR 2022 to 2019-21 work, so those four sit inside
    both windows. The claim is worth making - it is what makes the 2022 editions the right
    choice - but it has to be made accurately, and the same sentence appears in the
    Methods."""
    p.line(0, y - 3.4, W, y - 3.4, RULE, 0.5)
    main = ("%d papers in %d journals. Both quartiles are 2022 editions: SCImago SJR (the "
            "journal's best quartile across its Scopus categories) and Clarivate JCR "
            "(impact-factor quartile). Each counts citations made during 2022 to work "
            "published in 2019–2021 (SJR) or 2020–2021 (JCR), so neither edition can have "
            "been shaped by the %d papers here that appeared in 2022 or 2023; the %d "
            "published in 2021 do fall inside both citation windows."
            % (NP, NJ, PUBLISHED_AFTER, PUBLISHED_IN_WINDOW))
    if subject:
        main += (" Subject field is the paper's own OpenAlex primary topic, not its "
                 "journal's.")
    if access:
        main += " Access was resolved on 25 July 2026 and reflects that date."
    src = "Sources: PubMed/NLM (journal identity%s) │ SCImago SJR 2022 │ Clarivate JCR 2022" \
        % (", indexing" if indexing else "")
    if access:
        src += " │ OpenAlex with Unpaywall (access route%s)" % (", topic" if subject else "")
    elif subject:
        src += " │ OpenAlex (topic)"
    src += (" │ DOAJ via OpenAlex." if doaj else ".")
    lines = [(ln, MUT) for ln in p.wrap(main, W, T_SMALL)]
    lines += [(ln, FAINT) for ln in p.wrap(src, W, T_SMALL)]
    assert len(lines) <= FOOT_L, (len(lines), FOOT_L)
    for k, (ln, col) in enumerate(lines):
        p.text(0, y + k * 3.0, ln, T_SMALL, col)


# ---------------------------------------------------------------------------- designs
def design_A():
    """both rankings, then every journal - the complete record, and what it costs"""
    rw = 2.50                 # 229 rows over four columns; at the 2.65 house pitch the page
    h = (TOP + RANK_H + GAP + NOTE_L * 3.0 + GAP + jtable_h(NJ, 4, rw=rw)
         + GAP + FOOT_H)      # comes to 244.8 mm, which is the ceiling deciding the layout
    p = Page(h)
    y = rank_panel(p, TOP, "A")
    y = unranked_note(p, y + GAP)
    y = jtable(p, y + GAP, "B", "Every journal, largest first: all %d" % NJ,
               "chip and letter: SJR then JCR quartile, keyed in panel A; "
               "n/a = that ranking does not place the journal", JS, 4, "slim", rw=rw)
    footer(p, y + GAP + 3.4, access=False)
    return p, h, "Design A"


def design_B():
    """both rankings, the crosstab, and the journals that published more than once"""
    ntail = 3
    h = (TOP + RANK_H + GAP + XTAB_H + GAP + UNRANK_H + GAP
         + jtable_h(len(MULTI), 2) + 4.6 + 3.2 + ntail * 2.9 + GAP + FOOT_H)
    p = Page(h)
    y = rank_panel(p, TOP, "A")
    y = xtab_panel(p, y + GAP, "B")
    y = unranked_panel(p, y + GAP, "C")
    y = jtable(p, y + GAP, "D",
               "The %d journals that published more than one paper" % len(MULTI),
               "C / D / P = causal, descriptive, predictive papers in that journal; "
               "chip and letter: SJR then JCR quartile", MULTI, 2, "wide")
    y = tail_note(p, y + 4.6, JS[JS.n_papers == 1], ntail,
                  lead="The other %d journals published one paper each:" % SINGLE)
    footer(p, y + GAP + 3.4, access=False)
    return p, h, "Design B"


def design_C():
    """the shape of the tail"""
    h = (TOP + RANK_H + GAP + conc_h() + GAP + SINGLE_H + GAP + UNRANK_H + GAP
         + ACCBAR_H + GAP + FOOT_H)
    p = Page(h)
    y = rank_panel(p, TOP, "A")
    y = conc_panel(p, y + GAP, "B")
    y = single_panel(p, y + GAP, "C")
    y = unranked_panel(p, y + GAP, "D")
    y = access_bar(p, y + GAP, "E")
    footer(p, y + GAP + 3.4, doaj=True, indexing=True)
    return p, h, "Design C"


def design_D():
    """the landscape - no long table, and the two half-page panels side by side"""
    ntop, gut = 16, 6.0
    hw = (W - gut) / 2.0
    h = (TOP + RANK_H + GAP + NOTE_L * 3.0 + GAP + ACCBAR_H + GAP
         + max(subject_h(9), country_h(8)) + GAP + jtable_h(ntop, 1) + GAP + FOOT_H)
    p = Page(h)
    y = rank_panel(p, TOP, "A")
    y = unranked_note(p, y + GAP)
    y = access_bar(p, y + GAP, "B")
    # ⚠ side by side: take the TALLER of the two, never the sum
    y0 = y + GAP
    y1 = subject_panel(p, y0, "C", 9, x=0.0, w=hw)
    p.ymax = y0                       # the right-hand panel starts level with the left one
    y2 = country_panel(p, y0, "D", 8, x=hw + gut, w=hw)
    y = max(y1, y2)
    y = jtable(p, y + GAP, "E", "The %d journals that published the most papers" % ntop,
               "C / D / P = causal, descriptive, predictive; chip and letter: SJR then JCR",
               JS.head(ntop), 1, "wide")
    footer(p, y + GAP + 3.4, subject=True, doaj=True, indexing=True)
    return p, h, "Design D"


def design_E():
    """everything stratified by study task"""
    h = (TOP + RANK_H + GAP + TASK_H + GAP + TASKACC_H + GAP + UNRANK_H + GAP
         + jtable_h(len(BIG), 1) + GAP + FOOT_H)
    p = Page(h)
    y = rank_panel(p, TOP, "A")
    y = task_panel(p, y + GAP, "B")
    y = task_access_panel(p, y + GAP, "C")
    y = unranked_panel(p, y + GAP, "D")
    # ⚠ a stated cut, not a top-N: two journals hold 4 papers, so "the 14 largest" broke a
    # tie alphabetically - and dropped [NAME-REDACTED] (SJR Q1 / JCR Q1)
    # while keeping [NAME-REDACTED] (Q2 / not ranked), which made the tail of
    # the table look worse than the data does.
    y = jtable(p, y + GAP, "E",
               "The %d journals that published five or more papers" % len(BIG),
               # ⚠ the em-dash in the two quartile columns is a DATA VALUE, and design E's
               # sub-title had dropped the clause defining it - so the one glyph on the page
               # that needs a key was the only one without one.
               "C / D / P = causal, descriptive, predictive (colours as panel B); "
               "SJR/JCR chips keyed in panel A; n/a = that ranking does not place it",
               BIG, 1, "wide")
    footer(p, y + GAP + 3.4)
    return p, h, "Design E"


# ---------------------------------------------------------------------------- emit
def emit(p, h, stem, tag, formats):
    base = os.path.join(OUTDIR, stem)
    p.fig.canvas.draw()
    rend = p.fig.canvas.get_renderer()
    mm = lambda px: px / p.fig.dpi * 25.4
    assert min(p.sizes) >= MIN_PT, min(p.sizes)
    assert h <= HMAX, (tag, round(h, 1), HMAX)
    spill, boxes = [], []
    for t in p.ax.texts:
        b = t.get_window_extent(rend)
        x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
        if x0 < -0.25 or x1 > W + 0.25 or y0 < -0.25 or y1 > h + 0.25:
            spill.append((round(x0, 1), round(x1, 1), round(y0, 1), round(y1, 1),
                          t.get_text()[:40]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill[:6]
    clash = []
    for i, (ya0, ya1, xa0, xa1, sa) in enumerate(boxes):
        for yb0, yb1, xb0, xb1, sb in boxes[i + 1:]:
            if (xa0 < xb1 - 0.15 and xa1 > xb0 + 0.15
                    and ya0 < yb1 - 0.15 and ya1 > yb0 + 0.15):
                clash.append((sa[:22], sb[:22], round(xa1, 1), round(xb0, 1), round(ya0, 1)))
    assert not clash, clash[:6]
    # ⚠ y is measured upward from the bottom of the canvas by get_window_extent and
    # downward from the top by the drawing code - convert, do not compare raw.
    over = []
    for (gx, gy, gw, gh) in p.guards:
        gx0, gx1, gy0, gy1 = gx, gx + gw, h - (gy + gh), h - gy
        for (ty0, ty1, tx0, tx1, ts) in boxes:
            if (gx0 < tx1 - 0.1 and gx1 > tx0 + 0.1
                    and gy0 < ty1 - 0.1 and gy1 > ty0 + 0.1):
                over.append((ts[:22], round(gx1, 1), round(tx0, 1)))
    assert not over, ("a bar is drawn through a text label", over[:6])

    os.makedirs(OUTDIR, exist_ok=True)
    if "pdf" in formats:
        p.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
    p.fig.savefig(base + ".png", dpi=600, facecolor="white")
    if "tif" in formats:
        im = Image.open(base + ".png")
        rgb = Image.new("RGB", im.size, "white")
        rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
        rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
        im.close()
    plt.close(p.fig)
    if "png" not in formats:
        os.remove(base + ".png")
    if "pdf" in formats:
        for _k, _v in PdfReader(base + ".pdf").pages[0]["/Resources"]["/Font"].items():
            fo = _v.get_object()
            df = fo.get("/DescendantFonts")
            d = df[0].get_object() if df else fo
            desc = d.get("/FontDescriptor")
            assert d.get("/Subtype") != "/Type3" and desc and any(
                x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
            assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
    print("  %-9s %.0f x %.0f mm | smallest type %.1f pt | %s"
          % (tag, W, h, min(p.sizes),
             "  ".join("%s %.0f KB" % (e, os.path.getsize(base + "." + e) / 1024)
                       for e in formats)))


BUILD = OrderedDict([("A", (design_A, "08_25_2026_S3_journal_landscape_designA")),
                     ("B", (design_B, "08_25_2026_S3_journal_landscape_designB")),
                     ("C", (design_C, "08_25_2026_S3_journal_landscape_designC")),
                     ("D", (design_D, "08_25_2026_S3_journal_landscape_designD")),
                     ("E", (design_E, "08_25_2026_S3_journal_landscape_designE"))])

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["E"]
    fmts = ("pdf", "tif", "png") if len(args) == 1 else ("png",)
    print("Supplementary Figure S4 - journal landscape   (%s)" % ", ".join(fmts))
    for k in args:
        fn, stem = BUILD[k]
        pg, hh, tag = fn()
        emit(pg, hh, stem, tag, fmts)
