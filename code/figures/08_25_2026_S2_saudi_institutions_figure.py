# -*- coding: utf-8 -*-
"""Supplementary Figure S3 - Saudi institutions. Print-native, six candidate designs.

ONE figure carrying institution type, individual institutions, and both levels of analysis:
author positions / first / last (author level) and papers (paper level), plus the sector
BOUNDS the author ruled on 2026-08-24.

  A  grouped within institution type, all 116   (matches the chosen S1 design)
  B  ranked, all 116
  C  the 30 largest in full, the remaining 86 summarised
  D  geography - institution type, cities, leading institutions
  E  paper level throughout - sectors per paper, lead institution, bounds, papers
  F  concentration - how top-heavy the base is

Same print contract as S1/S7/S8: 180 mm wide, 6.5 pt type floor, Arial embedded,
TIFF RGB / LZW / 600 dpi, and the same assertions - type floor, nothing off the page, no
two text boxes touching.

⚠ COLOUR. Twelve institution types is past any qualitative scheme, and hue is not a
ranking device. The five types holding 96.6% of positions get a Paul Tol *muted* hue; the
seven trailing types share one neutral grey.

⚠ THE BOUNDS ARE THE POINT. Each author position is credited to ONE institution - the
top-level employer named in that author's first Saudi affiliation block. Where an
affiliation names several, the others are unrecorded, so a paper can lose a sector but
never gain one. Every design therefore reports health-system and multi-sector as a RANGE
(single-institution rule -> union rule), per the author's 2026-08-24 ruling.

    python code/figures/08_25_2026_S2_saudi_institutions_figure.py [A..F]

No argument (or several) emits PNG only, for choosing from. One design letter emits
PDF + TIFF + PNG. Run from the repository root.
"""
import os
import sys
from collections import Counter

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
TOL = {"University": "#332288", "Hospital / medical city": "#CC6677",
       "Hospital & research centre": "#44AA99",
       "Military & security-forces medical": "#117733", "Ministry of Health": "#DDCC77"}
NEUT = "#9aa2ab"
T_PANEL, T_BODY, T_SMALL = 8.5, 7.0, 6.5
col_of = lambda t: TOL.get(t, NEUT)

# ---------------------------------------------------------------------------- data
inst = pd.read_csv("data/authors/07_25_2026_saudi_institution_counts.csv", keep_default_na=False)
typ = pd.read_csv("data/authors/07_25_2026_saudi_institution_type_counts.csv", keep_default_na=False)
city = pd.read_csv("data/authors/07_25_2026_saudi_city_counts.csv", keep_default_na=False)
pap = pd.read_csv("data/authors/07_25_2026_saudi_paper_level.csv", dtype=str, keep_default_na=False)
aff = pd.read_csv("data/authors/07_25_2026_saudi_affiliation_long.csv", dtype=str, keep_default_na=False)

NAUTH, NPAP = len(aff), len(pap)
aff["f"] = (aff.is_first == "True").astype(int)
aff["l"] = (aff.is_last == "True").astype(int)
_g = aff.groupby("institution").agg(first=("f", "sum"), last=("l", "sum")).reset_index()
I = inst.merge(_g, on="institution", how="left").fillna(0)

# ---- disclosure control: an institution is named only if 5 papers stand behind it
# ⚠ 56 of the 116 institutions carry exactly ONE paper. Naming such an institution
# names the paper: a reader who knows a 2022 Saudi health paper came out of it has
# a single candidate, and this study says of every paper in it that it is flawed.
# The bar chart is a bitmap, so no text scanner downstream can catch this - it has
# to be right here. The tail keeps its positions, its papers and its count; it
# loses only its names, which no reading of the figure depended on.
K_MIN_PAPERS = 5
_OTHER = "Other institutions (fewer than %d papers each)" % K_MIN_PAPERS
if "n_categories" not in I.columns:
    I["n_categories"] = 1        # 1 institution per row; the public tree ships a
                                 # pre-collapsed row that says how many it stands for
I["first"] = I["first"].astype(int)
I["last"] = I["last"].astype(int)
_small = I[(I.papers < K_MIN_PAPERS) & (I.institution != _OTHER)]
_tail = I[(I.papers < K_MIN_PAPERS) | (I.institution == _OTHER)]
# ⚠ The tail is held as SCALARS, not as a row. A row would be drawn: it carries
# 194 positions, more than all but four named institutions, and every design
# would seat it among them as though it were one large employer.
TAIL_INST = int(_tail.n_categories.sum())
TAIL_POS = int(_tail.author_appearances.sum())
TAIL_PAPERS = int(_tail.papers.sum())        # a sum over institutions, so a paper
TAIL_FIRST = int(_tail["first"].sum())       # spanning two of them counts twice
TAIL_LAST = int(_tail["last"].sum())
if len(_small):
    aff.loc[aff.institution.isin(_small.institution), "institution"] = _OTHER
I = I[~I.index.isin(_tail.index)].copy()
NINST = int(I.n_categories.sum()) + TAIL_INST     # 116, named or not
NNAMED = len(I)
I = I.sort_values("author_appearances", ascending=False).reset_index(drop=True)
I["rank"] = range(1, len(I) + 1)
MAXA, MAXP = int(I.author_appearances.max()), int(I.papers.max())
MAXROLE = int(max(I["first"].max(), I["last"].max()))

# ⚠ The same threshold on the sector table. A row reporting that one institution
# of some sector contributed one paper is a sentence about that paper, and a
# reader who can name the body has found it. Five sector types, eight papers
# between them, merge. The types are not named here for the same reason.
_OTHER_TYPE = "Other sectors"
_st = typ[(typ.papers_involving < K_MIN_PAPERS) & (typ.inst_type != _OTHER_TYPE)]
if len(_st):
    _tagg = {c: (int(_st[c].sum()) if _st[c].dtype.kind in "if" else "")
             for c in typ.columns}
    _tagg["inst_type"] = _OTHER_TYPE
    _tagg["pct_authors"] = round(100.0 * int(_st.author_appearances.sum()) / NAUTH, 1)
    typ = pd.concat([typ[~typ.index.isin(_st.index)],
                     pd.DataFrame([_tagg])], ignore_index=True)
    I.loc[I.inst_type.isin(_st.inst_type), "inst_type"] = _OTHER_TYPE
    aff.loc[aff.inst_type.isin(_st.inst_type), "inst_type"] = _OTHER_TYPE
typ = typ.sort_values("author_appearances", ascending=False).reset_index(drop=True)
TYPES = [t for t in typ.inst_type if len(I[I.inst_type == t])]

pap["ns"] = pap.n_sectors.astype(int)
SEC = [("1 sector", int((pap.ns == 1).sum())), ("2", int((pap.ns == 2).sum())),
       ("3", int((pap.ns == 3).sum())), ("4 or more", int((pap.ns >= 4).sum()))]
HEALTH = {"Hospital / medical city", "Hospital & research centre", "Ministry of Health",
          "Military & security-forces medical"}
_ish = lambda s: any(p.strip() in HEALTH for p in str(s).split(";"))
HS_LO, HS_HI = int(pap.health_system.isin(["True", "TRUE", "1"]).sum()), int(pap.health_system_union.isin(["True", "TRUE", "1"]).sum())
MS_LO = int(pap.multisector.isin(["True", "TRUE", "1"]).sum())
MS_HI = int(pap.multisector_union.isin(["True", "TRUE", "1"]).sum())
LEADT = Counter(pap.lead_saudi_type).most_common()
CITY = city.sort_values("author_appearances", ascending=False).reset_index(drop=True)
RIYADH = int(CITY.iloc[0].author_appearances)
NOCITY = int(CITY[CITY.city == "Unspecified"].author_appearances.sum())

assert NAUTH == 1520 and NINST == 116 and NPAP == 385, (NAUTH, NINST, NPAP)
assert (HS_LO, HS_HI, MS_LO, MS_HI) == (115, 129, 80, 101), (HS_LO, HS_HI, MS_LO, MS_HI)


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

    def text(self, x, y, s, pt=T_BODY, col=INK, ha="left", weight="normal", count=True):
        if count:
            self.sizes.append(pt)
        return self.ax.text(x, y, s, fontsize=pt, color=col, ha=ha, va="baseline",
                            fontweight=weight)

    def rect(self, x, y, w, h, col, alpha=1.0, ec="none", lw=0.0):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=col, alpha=alpha,
                                    edgecolor=ec, linewidth=lw))

    def line(self, x0, y0, x1, y1, col=RULE, lw=0.4, ls="-"):
        self.ax.plot([x0, x1], [y0, y1], color=col, lw=lw, linestyle=ls,
                     solid_capstyle="butt")

    # ⚠ measure() is called several hundred times per design (116 institution names, the
    # type labels, the tail wrap). Drawing the whole 600 dpi canvas for each measurement -
    # which is what fig.canvas.draw() does - made a six-design run exceed ten minutes
    # without finishing the first one. Draw ONCE for a renderer, then reuse it, and cache
    # every (string, size) result.
    def _renderer(self):
        if getattr(self, "_rend", None) is None:
            self.fig.canvas.draw()
            self._rend = self.fig.canvas.get_renderer()
        return self._rend

    # ⚠ weight is part of the measurement. Bold Arial is materially wider than regular, and
    # measuring the group headers at normal weight while DRAWING them bold let six of them
    # run off the right edge of the page - caught only by the spill assertion.
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
        # binary search rather than a linear walk down from len(s): a 60-character
        # institution name in a 20 mm column is ~40 wasted measurements each.
        lo, hi, best = 3, len(s) - 1, s[:3]
        while lo <= hi:
            k = (lo + hi) // 2
            cand = s[:k].rstrip() + "…"
            if self.measure(cand, pt, weight) <= max_mm:
                best, lo = cand, k + 1
            else:
                hi = k - 1
        return best


# ---------------------------------------------------------------------------- layout
# ⚠ These are tuned so the TALLEST design (A: 12 type rows + 116 institutions + 12 group
# headers over three columns + the bounds panel) lands inside the 245 mm page. At the first
# values it came to 256.4 mm and the height assertion caught it. Loosening any of them
# without re-running every design is how a figure silently goes over a page.
ROW = 2.65                            # S7 runs the same pitch at 6.5 pt
TOP = 5.0
TYP_HEAD, TYP_ROW = 8.0, 4.2          # the type panel stacks TWO bars per row
BND_HEAD, BND_ROW = 10.0, 4.7
FOOT_H = 9.5
GAP = 5.2

# column fractions. Three-column designs are tighter, so they carry no % column - the
# share is in the type panel and is derivable from the count.
FR2 = dict(rank=.034, chip=.046, name=.064, abar=.360, abw=.105, an=.560, sh=.625,
           r1=.715, r2=.800, pbar=.822, pbw=.065, pn=1.0)
FR3 = dict(rank=.040, chip=.055, name=.077, abar=.430, abw=.090, an=.610, sh=None,
           r1=.740, r2=.850, pbar=.870, pbw=.055, pn=1.0)


def inst_row(p, x, y, cw, r, FR, rank=None, chip=True):
    c = col_of(r.inst_type)
    if rank is not None:
        p.text(x + cw * FR["rank"], y, str(rank), T_SMALL, FAINT, ha="right")
    if chip:
        p.rect(x + cw * FR["chip"], y - 1.6, 0.85, 1.9, c)
    nmax = cw * (FR["abar"] - FR["name"]) - 1.4
    p.text(x + cw * FR["name"], y, p.fit(str(r.institution), nmax, T_SMALL), T_SMALL, INK)
    p.rect(x + cw * FR["abar"], y - 1.75,
           max(cw * FR["abw"] * r.author_appearances / MAXA, 0.18), 1.9, c)
    p.text(x + cw * FR["an"], y, str(int(r.author_appearances)), T_SMALL, INK, ha="right")
    if FR["sh"]:
        p.text(x + cw * FR["sh"], y, "%.1f" % (100.0 * r.author_appearances / NAUTH),
               T_SMALL, MUT, ha="right")
    for key, fk in (("first", "r1"), ("last", "r2")):
        v = int(r[key])
        rr = x + cw * FR[fk]
        if v:
            tw = min(cw * .070, 9.0)
            p.rect(rr + 0.8 - tw, y - 2.2, tw, 2.8, c,
                   alpha=0.10 + 0.58 * (v / float(MAXROLE)) ** 0.5)
        p.text(rr, y, str(v) if v else "·", T_SMALL, INK if v else FAINT, ha="right")
    p.rect(x + cw * FR["pbar"], y - 1.75,
           max(cw * FR["pbw"] * r.papers / MAXP, 0.18), 1.9, c, alpha=0.42)
    p.text(x + cw * FR["pn"], y, str(int(r.papers)), T_SMALL, INK, ha="right")


def inst_header(p, x, y, cw, FR, rank=True):
    p.text(x + cw * FR["abar"], y - 3.4, "AUTHOR LEVEL", 5.6, "#0f5c6b", count=False)
    p.text(x + cw * FR["pn"], y - 3.4, "PAPER LEVEL", 5.6, "#0f5c6b", ha="right", count=False)
    if rank:
        p.text(x + cw * FR["rank"], y, "#", T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["name"], y, "Institution", T_SMALL, FAINT)
    p.text(x + cw * FR["abar"], y, "Authors", T_SMALL, FAINT)
    if FR["sh"]:
        p.text(x + cw * FR["sh"], y, "%", T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["r1"], y, "First", T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["r2"], y, "Last", T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["pn"], y, "Papers", T_SMALL, FAINT, ha="right")
    p.line(x, y + 1.1, x + cw, y + 1.1, RULE, 0.5)


def type_panel(p, y0, letter="A"):
    p.text(0, y0, letter, 9.5, INK, weight="bold")
    p.text(4.6, y0, "By institution type", T_PANEL, INK, weight="bold")
    p.text(4.6, y0 + 3.4, "filled bar: Saudi author positions (author level)   │   open bar: "
           "papers involving that type (paper level)", T_SMALL, MUT)
    # ⚠ The two bars stack, but their LABELS must not: at a 4.2 mm pitch a label under the
    # open bar lands on the next row's value label. Both numbers therefore sit on the row
    # baseline in fixed right-aligned columns, clear of the bars.
    lab, bx, bw = 44.0, 46.0, 60.0
    C_AUTH, C_PAP = 128.0, 152.0
    mxa = float(typ.author_appearances.max())
    p.text(C_AUTH, y0 + TYP_HEAD - 3.6, "POSITIONS", 5.6, "#0f5c6b", ha="right", count=False)
    p.text(C_PAP, y0 + TYP_HEAD - 3.6, "PAPERS", 5.6, "#0f5c6b", ha="right", count=False)
    for i, r in typ.iterrows():
        yy = y0 + TYP_HEAD + i * TYP_ROW
        c = col_of(r.inst_type)
        p.text(lab, yy, p.fit(str(r.inst_type), 41.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(bx, yy - 2.5, bw * r.author_appearances / mxa, 1.7, c)
        p.rect(bx, yy - 0.5, bw * r.papers_involving / mxa, 1.3, "none", ec=c, lw=0.4)
        p.text(C_AUTH, yy, "%d (%.1f%%)" % (r.author_appearances, r.pct_authors),
               T_SMALL, INK, ha="right")
        p.text(C_PAP, yy, "%d" % r.papers_involving, T_SMALL, MUT, ha="right")
        p.text(W, yy, "%d institution%s" % (r.distinct_institutions,
                                            "" if r.distinct_institutions == 1 else "s"),
               T_SMALL, FAINT, ha="right")
    return y0 + TYP_HEAD + len(typ) * TYP_ROW


def bounds_panel(p, y0, letter):
    p.text(0, y0, letter, 9.5, INK, weight="bold")
    p.text(4.6, y0, "The sector stratifiers are bounds, not points", T_PANEL, INK, weight="bold")
    p.text(4.6, y0 + 3.4, "each position is credited to ONE institution, so a paper can lose a "
           "sector but never gain one; ● single-institution rule   ● union rule",
           T_SMALL, MUT)
    rows = [("Health-system papers", HS_LO, HS_HI), ("Academic-only papers", NPAP - HS_HI, NPAP - HS_LO),
            ("Multi-sector papers", MS_LO, MS_HI), ("Single-sector papers", NPAP - MS_HI, NPAP - MS_LO)]
    x0, wpl = 46.0, 62.0
    for i, (lab, lo, hi) in enumerate(rows):
        yy = y0 + BND_HEAD + i * BND_ROW
        p.text(44.0, yy, lab, T_SMALL, INK, ha="right")
        p.line(x0 + wpl * lo / NPAP, yy - 0.8, x0 + wpl * hi / NPAP, yy - 0.8, RULE, 1.4)
        p.ax.plot([x0 + wpl * lo / NPAP], [yy - 0.8], "o", ms=2.6, color=TOL["University"])
        p.ax.plot([x0 + wpl * hi / NPAP], [yy - 0.8], "o", ms=2.6, color=TOL["Hospital / medical city"])
        p.text(x0 + wpl * hi / NPAP + 2.6, yy, "%d – %d   (%.1f – %.1f%%)"
               % (lo, hi, 100.0 * lo / NPAP, 100.0 * hi / NPAP), T_SMALL, INK)
    return y0 + BND_HEAD + len(rows) * BND_ROW


def hbars(p, y0, letter, title, sub, items, colf, valf, labw=44.0, barw=62.0, rh=4.2):
    # letter="" draws an UNLABELLED block, for a set of bars that sits beside another panel
    # rather than below it - drawing a second panel letter at x=0 put it on top of the first.
    off = 8.4
    if letter:
        p.text(0, y0, letter, 9.5, INK, weight="bold")
        p.text(4.6, y0, title, T_PANEL, INK, weight="bold")
    else:
        off = 6.0
    if sub:
        p.text(4.6, y0 + 3.4, sub, T_SMALL, MUT)
    elif letter:
        off = 6.0
    mx = float(max(v for _, v in items)) or 1.0
    for i, (lab, v) in enumerate(items):
        yy = y0 + off + i * rh
        p.text(labw, yy, p.fit(str(lab), labw - 3.0, T_SMALL), T_SMALL, INK, ha="right")
        p.rect(labw + 2.0, yy - 1.9, barw * v / mx, 2.0, colf(lab))
        p.text(labw + 3.2 + barw * v / mx, yy, valf(v), T_SMALL, MUT)
    return y0 + off + len(items) * rh


def footer(p, y):
    p.text(0, y, "%s Saudi author positions across %d institutions and %d papers. Each position "
           "is credited to the top-level employer named in that author's first Saudi "
           "affiliation block." % (format(NAUTH, ","), NINST, NPAP), T_SMALL, MUT)
    p.text(0, y + 3.0, "The %d institutions with %d or more papers are named. Riyadh holds %d "
           "positions (%.1f%%); a further %d name no city. First and Last are author level."
           % (NNAMED, K_MIN_PAPERS, RIYADH, 100.0 * RIYADH / NAUTH, NOCITY), T_SMALL, MUT)


# ---------------------------------------------------------------------------- designs
def _grid(p, seq, ytab, ncol, cw, gut, rows_per, FR, grouped):
    ci, ri, cur = 0, 0, None
    for kind, a in seq:
        if ri >= rows_per and ci < ncol - 1:
            # ⚠ do NOT draw the column header here - every design already draws all of them
            # up front. Drawing again put identical text at identical coordinates, which the
            # clash assertion correctly reported as a label overlapping itself.
            ci, ri = ci + 1, 0
            if kind == "R" and cur and grouped:
                x = ci * (cw + gut)
                p.rect(x, ytab + 4.0 - 2.2, cw, 3.0, col_of(cur), alpha=0.14)
                p.text(x + 1.2, ytab + 4.0,
                       p.fit("%s (continued)" % cur, cw - 3.0, T_SMALL, "bold"),
                       T_SMALL, INK, weight="bold")
                ri += 1
        x = ci * (cw + gut)
        y = ytab + 4.0 + ri * ROW
        if kind == "H":
            cur = a
            t = typ[typ.inst_type == a].iloc[0]
            p.rect(x, y - 2.2, cw, 3.0, col_of(a), alpha=0.14)
            p.text(x + 1.2, y, p.fit("%s: %d positions, %d inst., %d papers"
                                     % (a, t.author_appearances, t.distinct_institutions,
                                        t.papers_involving), cw - 3.0, T_SMALL, "bold"),
                   T_SMALL, INK, weight="bold")
        else:
            inst_row(p, x, y, cw, a, FR, rank=int(a["rank"]) if not grouped else None,
                     chip=not grouped)
        ri += 1


def design_A():
    seq = []
    for t in TYPES:
        seq.append(("H", t))
        for _, r in I[I.inst_type == t].iterrows():
            seq.append(("R", r))
    ncol, gut = 3, 4.0
    rows_per = (len(seq) + ncol - 1) // ncol + 1
    cw = (W - gut * (ncol - 1)) / ncol
    h_typ = TYP_HEAD + len(typ) * TYP_ROW
    ytab = TOP + h_typ + GAP + 6.4 + 4.0
    h = ytab + 4.0 + (rows_per - 1) * ROW + GAP + BND_HEAD + 4 * BND_ROW + FOOT_H
    p = Page(h)
    yb = type_panel(p, TOP)
    y2 = yb + GAP
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "Every institution, grouped within type: all %d" % NINST,
           T_PANEL, INK, weight="bold")
    for c in range(ncol):
        inst_header(p, c * (cw + gut), ytab, cw, FR3, rank=False)
    _grid(p, seq, ytab, ncol, cw, gut, rows_per, FR3, grouped=True)
    yb2 = ytab + 4.0 + (rows_per - 1) * ROW + GAP
    bounds_panel(p, yb2, "C")
    footer(p, yb2 + BND_HEAD + 4 * BND_ROW + 3.0)
    return p, h, "Design A"


def design_B():
    seq = [("R", r) for _, r in I.iterrows()]
    ncol, gut = 3, 4.0
    rows_per = (len(seq) + ncol - 1) // ncol
    cw = (W - gut * (ncol - 1)) / ncol
    h_typ = TYP_HEAD + len(typ) * TYP_ROW
    ytab = TOP + h_typ + GAP + 6.4 + 4.0
    h = ytab + 4.0 + (rows_per - 1) * ROW + GAP + BND_HEAD + 4 * BND_ROW + FOOT_H
    p = Page(h)
    yb = type_panel(p, TOP)
    y2 = yb + GAP
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "Every institution, ranked: all %d" % NINST, T_PANEL, INK, weight="bold")
    for c in range(ncol):
        inst_header(p, c * (cw + gut), ytab, cw, FR3, rank=True)
    _grid(p, seq, ytab, ncol, cw, gut, rows_per, FR3, grouped=False)
    yb2 = ytab + 4.0 + (rows_per - 1) * ROW + GAP
    bounds_panel(p, yb2, "C")
    footer(p, yb2 + BND_HEAD + 4 * BND_ROW + 3.0)
    return p, h, "Design B"


def design_C():
    n, rw = NNAMED, 3.0   # still roomier than A/B's 2.65; 3.6 put the page at 261.7 mm
    h_typ = TYP_HEAD + len(typ) * TYP_ROW
    ytab = TOP + h_typ + GAP + 6.4 + 4.0
    NTL = 3
    h = (ytab + 4.0 + (n - 1) * rw + 6.0 + 7.4 + NTL * 2.9 + GAP
         + BND_HEAD + 4 * BND_ROW + FOOT_H)
    p = Page(h)
    yb = type_panel(p, TOP)
    y2 = yb + GAP
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "The %d institutions with %d or more papers" % (n, K_MIN_PAPERS),
           T_PANEL, INK, weight="bold")
    inst_header(p, 0, ytab, W, FR2, rank=True)
    for i, r in I.head(n).iterrows():
        inst_row(p, 0, ytab + 4.0 + i * rw, W, r, FR2, rank=int(r["rank"]))
    yt = ytab + 4.0 + (n - 1) * rw + 6.0
    p.text(0, yt, "C", 9.5, INK, weight="bold")
    p.text(4.6, yt, "The remaining %d institutions, not named" % TAIL_INST,
           T_PANEL, INK, weight="bold")
    p.text(4.6, yt + 3.4, "%d institutions │ %d positions (%.1f%%) │ first %d │ last %d"
           % (TAIL_INST, TAIL_POS, 100.0 * TAIL_POS / NAUTH, TAIL_FIRST, TAIL_LAST),
           T_SMALL, MUT)
    # ⚠ THESE ARE NOT NAMED, AND THE OMISSION IS THE POINT. 56 of the 116
    # institutions carry a single paper. Naming one names that paper, and this
    # study holds that every paper in it is flawed. The counts above are the
    # whole of what the figure ever used them for.
    lines = ["Each has fewer than %d papers in the sample. Naming an institution "
             "that appears once would identify" % K_MIN_PAPERS,
             "the paper and its authors, so the tail is reported as a total. "
             "Its positions and authorships are",
             "included in panel A and in the sector bounds below."]
    assert len(lines) <= NTL, (len(lines), NTL)
    for k, ln in enumerate(lines):
        p.text(4.6, yt + 7.4 + k * 2.9, ln, T_SMALL, MUT)
    yb2 = yt + 7.4 + NTL * 2.9 + GAP
    bounds_panel(p, yb2, "D")
    footer(p, yb2 + BND_HEAD + 4 * BND_ROW + 3.0)
    return p, h, "Design C"


def design_D():
    ncity, ninst, rh = 12, 18, 3.6      # at 13/18/4.2 the page came to 261.9 mm
    h = (TOP + TYP_HEAD + len(typ) * TYP_ROW + GAP + 8.4 + ncity * rh + GAP
         + 6.0 + ninst * rh + GAP + BND_HEAD + 4 * BND_ROW + FOOT_H)
    p = Page(h)
    yb = type_panel(p, TOP)
    ct = [(r.city, int(r.author_appearances)) for _, r in CITY.head(ncity).iterrows()]
    y2 = hbars(p, yb + GAP, "B", "Across the Kingdom: positions by city",
               "“Unspecified” is an affiliation naming no city, not a place",
               ct, lambda l: NEUT if l == "Unspecified" else TOL["University"],
               lambda v: "%d (%.1f%%)" % (v, 100.0 * v / NAUTH), rh=rh)
    it = [(r.institution, int(r.author_appearances)) for _, r in I.head(ninst).iterrows()]
    tmap = dict(zip(I.institution, I.inst_type))
    y3 = hbars(p, y2 + GAP, "C", "Leading institutions", None, it,
               lambda l: col_of(tmap.get(l, "")), lambda v: str(v), labw=62.0, barw=48.0,
               rh=rh)
    yb2 = y3 + GAP
    bounds_panel(p, yb2, "D")
    footer(p, yb2 + BND_HEAD + 4 * BND_ROW + 3.0)
    return p, h, "Design D"


def design_E():
    nlead, npap_i = 7, 16
    h = (TOP + 8.4 + len(SEC) * 5.0 + GAP + 8.4 + nlead * 4.4 + GAP
         + BND_HEAD + 4 * BND_ROW + GAP + 6.0 + npap_i * 4.2 + FOOT_H)
    p = Page(h)
    y1 = hbars(p, TOP, "A", "Saudi institution types per paper",
               "how many distinct Saudi sectors appear on one paper", SEC,
               lambda l: TOL["University"],
               lambda v: "%d (%.1f%%)" % (v, 100.0 * v / NPAP), rh=5.0)
    lt = [(k or "(none)", v) for k, v in LEADT[:nlead]]
    y2 = hbars(p, y1 + GAP, "B", "Lead Saudi institution type",
               "the institution of the first Saudi author on each paper", lt, col_of,
               lambda v: "%d (%.1f%%)" % (v, 100.0 * v / NPAP), labw=62.0, barw=48.0, rh=4.4)
    y3 = bounds_panel(p, y2 + GAP, "C")
    it = [(r.institution, int(r.papers)) for _, r in I.nlargest(npap_i, "papers").iterrows()]
    tmap = dict(zip(I.institution, I.inst_type))
    y4 = hbars(p, y3 + GAP, "D", "Institutions by number of papers (paper level)", None, it,
               lambda l: col_of(tmap.get(l, "")), lambda v: str(v), labw=62.0, barw=48.0)
    footer(p, y4 + 3.0)
    return p, h, "Design E"


def design_F():
    ntop = 14
    plot_h = 62.0
    # ⚠ the top-N bars sit BESIDE the concentration plot, not below it, so the height takes
    # the taller of the two - adding them put the page at 252.5 mm for space never used.
    h = (TOP + TYP_HEAD + len(typ) * TYP_ROW + GAP
         + max(8.4 + plot_h + 8.0, 6.0 + ntop * 4.2) + GAP
         + BND_HEAD + 4 * BND_ROW + FOOT_H)
    p = Page(h)
    yb = type_panel(p, TOP)
    y2 = yb + GAP
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "Concentration: cumulative share of Saudi author positions",
           T_PANEL, INK, weight="bold")
    px, py, pw = 16.0, y2 + 8.4, 78.0
    p.rect(px, py, pw, plot_h, "none", ec=RULE, lw=0.5)
    run, xs, ys = 0, [px], [py + plot_h]
    for i, r in I.iterrows():
        run += r.author_appearances
        xs.append(px + pw * (i + 1) / NINST)
        ys.append(py + plot_h - plot_h * run / NAUTH)
    p.ax.plot(xs, ys, color="#16697a", lw=1.0)
    p.line(px, py + plot_h, px + pw, py, FAINT, 0.5, ":")
    run = 0
    for i, r in I.iterrows():
        run += r.author_appearances
        if i + 1 in (10, 20, 30):
            cx, cy = px + pw * (i + 1) / NINST, py + plot_h - plot_h * run / NAUTH
            p.ax.plot([cx], [cy], "o", ms=2.4, color=TOL["Hospital / medical city"])
            p.text(cx + 1.6, cy - 1.0, "top %d → %.1f%%" % (i + 1, 100.0 * run / NAUTH),
                   T_SMALL, INK)
    p.text(px, py + plot_h + 3.4, "institutions, ranked by author positions", T_SMALL, FAINT)
    it = [(r.institution, int(r.author_appearances)) for _, r in I.head(ntop).iterrows()]
    tmap = dict(zip(I.institution, I.inst_type))
    p.text(150.0, y2 + 3.0, "The %d largest, by author positions" % ntop, T_SMALL, FAINT,
           ha="right")
    y3 = hbars(p, y2 + 4.0, "", None, None, it, lambda l: col_of(tmap.get(l, "")),
               lambda v: str(v), labw=150.0, barw=22.0)
    yb2 = max(py + plot_h + 8.0, y3) + GAP
    bounds_panel(p, yb2, "D")
    footer(p, yb2 + BND_HEAD + 4 * BND_ROW + 3.0)
    return p, h, "Design F"


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
            spill.append((round(x0, 1), round(x1, 1), t.get_text()[:40]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill[:6]
    clash = []
    for i, (ya0, ya1, xa0, xa1, sa) in enumerate(boxes):
        for yb0, yb1, xb0, xb1, sb in boxes[i + 1:]:
            if (xa0 < xb1 - 0.15 and xa1 > xb0 + 0.15
                    and ya0 < yb1 - 0.15 and ya1 > yb0 + 0.15):
                clash.append((sa[:20], sb[:20], round(xa1, 1), round(xb0, 1)))
    assert not clash, clash[:6]

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


BUILD = {"A": (design_A, "08_25_2026_S2_saudi_institutions_designA"),
         "B": (design_B, "08_25_2026_S2_saudi_institutions_designB"),
         "C": (design_C, "08_25_2026_S2_saudi_institutions_designC"),
         "D": (design_D, "08_25_2026_S2_saudi_institutions_designD"),
         "E": (design_E, "08_25_2026_S2_saudi_institutions_designE"),
         "F": (design_F, "08_25_2026_S2_saudi_institutions_designF")}

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["C"]
    fmts = ("pdf", "tif", "png") if len(args) == 1 else ("png",)
    print("Supplementary Figure S3 - Saudi institutions   (%s)" % ", ".join(fmts))
    for k in args:
        fn, stem = BUILD[k]
        pg, hh, tag = fn()
        emit(pg, hh, stem, tag, fmts)
