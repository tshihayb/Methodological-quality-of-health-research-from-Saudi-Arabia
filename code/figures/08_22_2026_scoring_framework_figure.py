# -*- coding: utf-8 -*-
"""The scoring framework as a manuscript figure: what is scored, and how a study
becomes a score.  PDF, TIFF, PNG, print-native.

    python code/figures/08_22_2026_scoring_framework_figure.py

WHY A FIGURE AND NOT A TABLE
The framework was a 7-row summary table in the Methods.  What that table could not
carry is the part the prose spends most of its words on: the four mutually
exclusive states, the weakest-link roll-up, and the fact that every domain has its
own denominator.  Those are structural and read better drawn.  The full instrument
- every item, in the reviewer's own wording, with the response that counts as a
problem - goes to the supplement instead, where a reader can check it item by item.

⚠ IT IMPORTS THE INSTRUMENT TABLE, AND THAT REGENERATES IT.  ITEMS, the counts and
the census all come from code/tables/08_22_2026_scoring_framework.py, so the figure
and the supplementary table cannot disagree.  Importing it re-runs its checks: the
item wording against the instrument PDF, and the scored-item set against the
scorer's own output.  If either has drifted, this figure will not build.

⚠ THE COUNTS ARE 22 AND 10, as of 2026-08-22.  They were 20 and 9 for a day, after the
manuscript's old Table 1 was found to have miscounted; then the two measurement-accounting
items were promoted from recorded-only to scored, taking both totals up by one per task.
Never type these - they come from the table module and are asserted against the scorer.

OUTPUT (outputs/figures/)  08_22_2026_scoring_framework.{pdf,tif,png}
"""
import os, sys, importlib.util
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, FancyBboxPatch

D = r"."
os.chdir(D)
_spec = importlib.util.spec_from_file_location(
    "sf", "code/tables/08_22_2026_scoring_framework.py")
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)                       # regenerates the table; see header

# ⚠ HOW MANY ITEMS ARE GRADED IS COUNTED, NOT TYPED. The footnote read "Three ordinal items
# are graded rather than binary" as a fixed string; the scored data holds FIVE - validation of
# exposure and of outcome, handling of missing exposure and outcome data, and determination of
# confounders. Three is the number of KINDS, five the number of items, and the figure said
# items. An item counts as graded when its severity takes more than the two binary values.
import pandas as _pd
# ⚠ na_values MUST be empty here. "NA" is a STATE in this file, the inapplicable one, and
# reading it as a missing value makes the `state != "NA"` filter below a no-op: it kept all
# 4,847 primary rows instead of the 4,030 applicable ones. Found 2026-08-29. _NGRADED came
# out 5 either way, because every graded item already carries severity 0 among its applicable
# responses and the inapplicable rows only add another 0, but the filter was not doing its job.
_it = _pd.read_csv("data/scoring/07_30_2026_scored_items_long.csv",
                   keep_default_na=False, na_values=[])
_it = _it[_it.primary.astype(str) == "True"].copy()
_it["_sev"] = _pd.to_numeric(_it.severity, errors="coerce").fillna(0)
_sc = _it[_it.state != "NA"]
_NGRADED = sum(1 for _i, _s in _sc.groupby("item") if _s._sev.nunique() > 2)
_NGRADED_WORD = {3: "Three", 4: "Four", 5: "Five", 6: "Six"}[_NGRADED]
assert _NGRADED == 5, ("the graded-item count moved; the footnote names three KINDS and this "
                       "many items, so both halves of that sentence need re-checking", _NGRADED)

OUTDIR, STEM = "outputs/figures", "08_22_2026_scoring_framework"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial",
                            "mathtext.fontset": "custom", "mathtext.rm": "Arial",
                            "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold",
                            "mathtext.default": "regular"})
PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, AC = "#111417", "#4a5259", "#0f5c6b"
RULE, GRID_C, BAND = "#c8ced2", "#e6eaec", "#f6f7f8"
REP, VAL, OFF = "#5aa8b8", "#1b6b7a", "#c9ced2"
STATE = {"na": "#b9c0c4", "ok": "#5f9e6e", "rep": "#c9922f", "val": "#b5563f"}
T_TITLE, T_PANEL, T_BODY, T_SMALL = 9.5, 8.0, 7.0, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM

LAB_X, TEXT_W = 10.0, 168.0
GAP = 7.5
CX = {"C": 62.0, "D": 124.0}                       # left edge of each task's item strip
SQ, SQGAP = 3.1, 1.0                               # item square and the space after it


class Page:
    def __init__(self, H):
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(H, 0); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="none", zorder=0))
        self.sizes, self.ymax = [], 0.0

    def T(self, x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4):
        self.sizes.append(pt)
        self.ymax = max(self.ymax, y + (line_h(pt) if va == "top" else
                                        line_h(pt) / 2 if va == "center" else 0.0))
        return self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)

    def width(self, s, pt):
        t = self.ax.text(0, 0, s, fontsize=pt, zorder=0)
        w = t.get_window_extent(self.fig.canvas.get_renderer()).width / self.fig.dpi * 25.4
        t.remove()
        return w

    def wrap(self, s, pt=T_SMALL, maxw=None):
        maxw = TEXT_W if maxw is None else maxw
        out, line = [], ""
        for word in s.split(" "):
            trial = word if not line else line + " " + word
            if self.width(trial, pt) > maxw and line:
                out.append(line); line = word
            else:
                line = trial
        if line:
            out.append(line)
        return out

    def block(self, x, y, lines, pt=T_SMALL, c=MUT):
        for i, ln in enumerate(lines):
            self.T(x, y + i * line_h(pt), ln, pt, c)
        return len(lines) * line_h(pt)

    def notes(self, y, paras, pt=T_SMALL, maxw=None, x=LAB_X):
        for s in ([paras] if isinstance(paras, str) else paras):
            for ln in self.wrap(s, pt, maxw):
                self.T(x, y, ln, pt, MUT)
                y += line_h(pt)
        return y

    def head(self, y, letter, title, sub=""):
        assert y >= self.ymax - 0.05, (letter, round(y, 1), round(self.ymax, 1))
        self.T(LAB_X - 6.0, y, letter, T_PANEL, INK, "bold")
        self.T(LAB_X, y, title, T_PANEL, INK, "bold")
        self.ax.add_line(plt.Line2D([LAB_X - 6.0, W - 1.0], [y + line_h(T_PANEL) + 0.6] * 2,
                                    color=RULE, lw=0.5, zorder=2))
        return self.notes(y + line_h(T_PANEL) + 1.8, sub) if sub else y + line_h(T_PANEL) + 1.8

    def chip(self, x, y, w, h, fc, ec=None, r=1.0):
        self.ax.add_patch(FancyBboxPatch((x + r, y + r), w - 2 * r, h - 2 * r,
                                         boxstyle="round,pad=%.3f,rounding_size=%.3f" % (r, r),
                                         fc=fc, ec=ec or fc, lw=0.5, zorder=2, mutation_aspect=1))


# =============================================================================
# Content, read out of the instrument table
# =============================================================================
DOMS = [d for d in sf.DOM_ORDER
        if any(x[2] == d and x[6] == sf.SCORED_ROLE for x in sf.ITEMS)]


def cells(task, dom):
    """The items of one domain for one task, in instrument order, as axis codes."""
    out = []
    for item, t, d, _q, _f, axis, role, _c in sf.ITEMS:
        if t == task and d == dom and role != sf.GATE:
            out.append(("rep" if axis == "reporting" else "val") if role == sf.SCORED_ROLE else "off")
    return out


def page(H):
    p = Page(H)
    p.T(4.0, 4.0, "How each study was scored", T_TITLE, INK, "bold")
    p.notes(4.0 + line_h(T_TITLE),
            "The instrument asks a different set of questions of each study task, and every answer "
            "resolves to one of four states. Predictive studies are assigned no bias items and are "
            "not scored, leaving %d of the %d papers appraised."
            % (sf.CENSUS["causal"] + sf.CENSUS["descriptive"], sf.CENSUS["total"]),
            x=4.0, maxw=W - 8.0)

    # ---- panel A: which items apply, by domain and task --------------------
    y = p.head(15.5, "A", "What is scored, by domain and study task",
               "One square per item, in the order the instrument asks them. Colour marks whether "
               "an item asks what was reported or how well it was done. Every square shown counts "
               "toward the score.")
    y += 1.4
    for t in ("C", "D"):
        p.T(CX[t], y, sf.TASKNAME[t], T_BODY, INK, "bold")
        p.T(CX[t], y + line_h(T_BODY), "%d papers" % sf.CENSUS[sf.TASKNAME[t].lower()],
            T_SMALL, MUT)
    y += line_h(T_BODY) + line_h(T_SMALL) + 1.6
    ROW = 5.6
    for i, dom in enumerate(DOMS):
        yc = y + ROW * i
        if i % 2 == 0:
            p.ax.add_patch(Rectangle((LAB_X - 5.2, yc - 0.6), W - LAB_X + 4.4, ROW,
                                     fc=BAND, ec="none", zorder=1))
        p.T(LAB_X, yc + ROW / 2 - 0.6, dom, T_SMALL, INK, va="center")
        for t in ("C", "D"):
            cs = cells(t, dom)
            if not cs:
                p.T(CX[t] + 0.4, yc + ROW / 2 - 0.6, "not asked", T_SMALL, "#9aa3a9", va="center")
                continue
            x = CX[t]
            for c in cs:
                if c == "off":
                    p.chip(x, yc + ROW / 2 - 0.6 - SQ / 2, SQ, SQ, "white", OFF)
                else:
                    p.chip(x, yc + ROW / 2 - 0.6 - SQ / 2, SQ, SQ, REP if c == "rep" else VAL)
                x += SQ + SQGAP
            n = sum(1 for c in cs if c != "off")
            p.T(x + 1.6, yc + ROW / 2 - 0.6, str(n), T_SMALL, INK, "bold", va="center")
    y += ROW * len(DOMS) + 1.0
    p.ax.add_line(plt.Line2D([LAB_X - 5.2, W - 1.0], [y] * 2, color=RULE, lw=0.5, zorder=2))
    y += 1.6
    p.T(LAB_X, y, "Items entering the score", T_SMALL, INK, "bold")
    for t in ("C", "D"):
        p.T(CX[t], y, "%d" % sf.N_SCORED[t], T_BODY, AC, "bold")
        p.T(CX[t] + 6.0, y + 0.5, "of %d asked" % sf.N_TOTAL[t], T_SMALL, MUT)
    y += line_h(T_BODY) + 1.4
    lx = LAB_X
    for lab, col, ec in (("reporting item \u2014 was it reported?", REP, None),
                         ("validity item \u2014 was it done well?", VAL, None)):
        p.chip(lx, y + 0.2, SQ, SQ, col, ec)
        p.T(lx + SQ + 1.4, y + 0.2 + SQ / 2, lab, T_SMALL, MUT, va="center")
        lx += SQ + 1.4 + p.width(lab, T_SMALL) + 6.0
    assert lx < W, lx
    y = p.notes(y + SQ + 2.4,
                "Two gate questions, on whether the study had follow-up and whether it estimated a "
                "time-varying effect, route the conditional items above and are never scored. "
                "Randomised trials analysed by intention to treat are exempt from the "
                "confounding-control item. %s ordinal items, of three kinds (validation of "
                "exposure and of outcome, handling of missing exposure and outcome data, and "
                "determination of confounders), are graded rather than binary: their options "
                "run best to worst and carry equally spaced severities from 0 to 1, so a "
                "weaker attempt costs less than none. The full instrument, with the response "
                "counted as a problem and the severity it carries, is Supplementary Table S1."
                % _NGRADED_WORD)

    # ---- panel B: the four states -----------------------------------------
    y = p.head(y + GAP, "B", "Every study \u00d7 item resolves to one of four states",
               "The two middle states are kept apart deliberately: a transparency deficit and a "
               "methodological weakness are different problems with different remedies, and a "
               "single \u201cunclear\u201d category conceals which is which.")
    y += 1.2
    BOXW, BOXH = (W - LAB_X - 2.0 - 3 * 3.0) / 4.0, 13.0
    for i, (k, name, defn) in enumerate((
            ("na", "Not applicable", "the instrument does not ask this of this paper"),
            ("ok", "No issue", "reported, and judged sound"),
            ("rep", "Reporting gap", "not reported in enough detail to judge"),
            ("val", "Validity flaw", "reported, and judged unfavourably"))):
        x = LAB_X + i * (BOXW + 3.0)
        p.chip(x, y, BOXW, BOXH, "white", RULE)
        p.ax.add_patch(Rectangle((x + 1.2, y + 1.2), 1.4, BOXH - 2.4, fc=STATE[k], ec="none", zorder=3))
        p.T(x + 4.0, y + 1.8, name, T_SMALL, INK, "bold")
        for j, ln in enumerate(p.wrap(defn, T_SMALL, BOXW - 5.4)):
            p.T(x + 4.0, y + 1.8 + line_h(T_SMALL) * (j + 1), ln, T_SMALL, MUT)
    y += BOXH + 2.2
    y = p.notes(y, "\u201cSkipped\u201d and \u201cshould be skipped\u201d are not applicable. "
                   "\u201cNot reported or unknown\u201d is a reporting gap, never a pass.")

    # ---- panel C: roll-up and denominators ---------------------------------
    y = p.head(y + GAP, "C", "From items to domains to study-level measures")
    y += 1.0
    ARROW = "#6f787e"
    steps = [("items", "each applicable item carries one of the four states above"),
             ("domain", "the WORST state among its applicable items \u2014 a validity flaw if any "
                        "item is flawed, a reporting gap if none is flawed but one cannot be "
                        "judged, no issue only when all are sound"),
             ("study", "error score, the flawed items counted and again severity-weighted, "
                       "compared within task only; transparency index, the share of applicable "
                       "items reported adequately; validity index, the share of judgeable items "
                       "passed")]
    # Three cards left to right, with an arrow between them - the same language as
    # panel B, so the page reads as one figure.  The earlier version stacked the steps
    # and drew a vertical arrow per step: they sat under the right-aligned labels and
    # took their length from each paragraph's height, so no two matched and the column
    # read as clutter.  Horizontal arrows between card edges are uniform by
    # construction and cannot drift when a definition gets longer.
    AGAP = 7.0
    CW = (W - LAB_X - 2.0 - 2 * AGAP) / 3.0
    wrapped = [(lab, p.wrap(defn, T_SMALL, CW - 5.0)) for lab, defn in steps]
    CH = line_h(T_SMALL) + 1.2 + max(len(w) for _l, w in wrapped) * line_h(T_SMALL) + 2.6
    for i, (lab, lines) in enumerate(wrapped):
        x = LAB_X + i * (CW + AGAP)
        p.chip(x, y, CW, CH, "white", RULE)
        p.ax.add_patch(Rectangle((x + 1.2, y + 1.2), 1.4, CH - 2.4, fc=AC, ec="none", zorder=3))
        p.T(x + 4.0, y + 1.6, lab, T_SMALL, AC, "bold")
        p.block(x + 4.0, y + 1.6 + line_h(T_SMALL) + 1.2, lines, c=MUT)
        if i < 2:
            p.ax.add_patch(FancyArrowPatch((x + CW + 1.4, y + CH / 2),
                                           (x + CW + AGAP - 1.4, y + CH / 2),
                                           arrowstyle="-|>", mutation_scale=6.0, lw=0.7,
                                           color=ARROW, zorder=3, shrinkA=0, shrinkB=0))
    y += CH + 2.4
    p.bottom = p.notes(y + 0.6,
                       "Applicability is decided study by study, so each domain's denominator is "
                       "the number of studies it applies to, not the full sample; every prevalence "
                       "reported is computed on that base. Applicable bases and full definitions "
                       "are in Supplementary Methods 6.")
    return p


# =============================================================================
# Two-pass build, then the checks nothing else makes
# =============================================================================
_p = page(400.0); plt.close(_p.fig)
H = _p.bottom + 4.0
p = page(H)

base = os.path.join(OUTDIR, STEM)
p.fig.canvas.draw()
rend = p.fig.canvas.get_renderer()
mm = lambda px: px / p.fig.dpi * 25.4
assert min(p.sizes) >= MIN_PT, min(p.sizes)
assert H <= 245.0, H
boxes, spill = [], []
for t in p.ax.texts:
    b = t.get_window_extent(rend)
    x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
    if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > H + 0.2:
        spill.append((round(x0, 1), round(x1, 1), t.get_text()[:60]))
    boxes.append((y0, y1, x0, x1, t.get_text()))
assert not spill, spill
clash = [(a[4][:30], b[4][:30]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
         if a[2] < b[3] - 0.2 and a[3] > b[2] + 0.2 and a[0] < b[1] - 0.2 and a[1] > b[0] + 0.2]
assert not clash, clash[:6]

p.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
p.fig.savefig(base + ".png", dpi=600, facecolor="white")
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
im = Image.open(base + ".png")
rgb = Image.new("RGB", im.size, "white")
rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
im.close(); plt.close(p.fig)

from pypdf import PdfReader
for _k, _v in PdfReader(base + ".pdf").pages[0]["/Resources"]["/Font"].items():
    fo = _v.get_object(); df = fo.get("/DescendantFonts")
    d = df[0].get_object() if df else fo
    desc = d.get("/FontDescriptor")
    assert d.get("/Subtype") != "/Type3" and desc and any(
        x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
    assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
t = Image.open(base + ".tif")
assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0)
t.close()

for ext in ("pdf", "tif", "png"):
    print("  %-56s %8.1f KB" % (base + "." + ext, os.path.getsize(base + "." + ext) / 1024))
print("  %.0f x %.0f mm, smallest type %.1f pt" % (W, H, min(p.sizes)))
print("  %d causal and %d descriptive scored items across %d domains"
      % (sf.N_SCORED["C"], sf.N_SCORED["D"], len(DOMS)))
