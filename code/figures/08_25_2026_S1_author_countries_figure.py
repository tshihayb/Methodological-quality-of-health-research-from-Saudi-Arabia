# -*- coding: utf-8 -*-
"""Supplementary Figure S2 - author countries. Print-native, three candidate designs.

ONE figure carrying, in a single display:
  panel A  author positions by world region, at BOTH levels - a filled bar for author
           positions (author level) and an open bar for the number of papers carrying at
           least one author from that region (paper level)
  panel B  every country: author positions, share, first / last / corresponding author
           counts (author level) and number of papers (paper level)

  A  rank-ordered, all 104 countries in two columns, region carried by a colour chip
  B  grouped within region, region subtotals in place  (recommended)
  C  the 30 largest in full, the remaining 74 summarised

Built to the same print contract as Supplementary Figures S10 and S11
(code/figures/08_22_2026_adjudication_supplement_figure.py): 180 mm wide, 6.5 pt type
floor, Arial embedded, TIFF RGB / LZW / 600 dpi, and the same three assertions - type
floor, nothing off the page, and no two text boxes touching.

⚠ Colour is Paul Tol's *muted* qualitative scheme. Chosen over Okabe-Ito because
Okabe-Ito's yellow (#F0E442) has too little contrast against white for a 1 mm bar, and
supplements are frequently printed in greyscale. Hue only ever encodes region; magnitude
is always length or tint, never hue.

⚠ Two things this figure fixes in the S1 it replaces. (1) Shares are computed on the
3,832 COUNTRY CREDITS, not the 3,508 distinct author positions - 306 authors carry
affiliations in more than one country, and the old figure quoted one denominator in its
lede and divided by the other in its table. (2) Saudi Arabia is on all 385 papers by
inclusion criteria; it is set out as an anchor row rather than left to flatten the bars
for every other country.

    python code/figures/08_25_2026_S1_author_countries_figure.py [A B C]

Run from the repository root.
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
CC = "data/analysis/08_25_2026_author_countries_S1.csv"
PS = "data/authors/07_25_2026_paper_country_summary.csv"
AL = "data/authors/07_25_2026_author_country_long.csv"

W = 180.0                 # journal single-figure width, mm
HMAX = 245.0              # page height less margins
MIN_PT = 6.5              # journal type floor; asserted
PT2MM = 25.4 / 72.0

INK, MUT, FAINT, RULE = "#111417", "#4a5259", "#7b848c", "#c8ced2"
TOL = {"Gulf": "#332288", "Europe": "#117733", "Asia": "#CC6677", "Americas": "#DDCC77",
       "Other Arab": "#44AA99", "Sub-Saharan Africa": "#882255", "Oceania": "#AA4499"}
T_PANEL, T_BODY, T_SMALL = 8.5, 7.0, 6.5

# ---------------------------------------------------------------------------- data
cc = pd.read_csv(CC, encoding="utf-8-sig")
for c in ("authors", "first", "last", "corr", "papers", "rank"):
    cc[c] = cc[c].astype(int)
import json as _json
_agg = _json.load(open("data/analysis/08_25_2026_author_countries_aggregates.json",
                       encoding="utf-8"))

TOT = int(cc.authors.sum())
UNIQ = _agg["n_author_positions"]
NPAP = _agg["n_papers"]
NDUAL = _agg["n_dual_country"]
SA = "Saudi Arabia"
REGOF = dict(zip(cc.country, cc.region))     # built BEFORE the collapse below,
                                             # so panel A still resolves every
                                             # country named in ps.countries

# ---- disclosure control: a country is named only if 5 papers stand behind it
# ⚠ 25 of the 104 countries carry exactly ONE paper. A row saying that a single
# paper in this sample has an author in some particular country identifies that
# paper to anyone holding the 2022 Saudi frame, and this study says of every
# paper in it that it is flawed. Naming the countries here would leak precisely
# what the row does, so this comment does not. It is the same disclosure the institution
# figure had, in the same supplement, and it is a bitmap, so nothing downstream
# can catch it. The tail keeps its positions, its authorships and its count
# within each region, and loses only the names.
K_MIN_PAPERS = 5
# ⚠ Short, because the country column is 32 mm and a longer label truncates to
# "Other countries (fe...". The threshold is stated in the footer instead.
_OTHER = "Other countries"
if "n_categories" not in cc.columns:
    cc["n_categories"] = 1
_small = cc[(cc.papers < K_MIN_PAPERS) & (cc.country != _OTHER) & (cc.country != SA)]
if len(_small):
    _agg = (_small.groupby("region", as_index=False)
            .agg(authors=("authors", "sum"), first=("first", "sum"),
                 last=("last", "sum"), corr=("corr", "sum"),
                 papers=("papers", "sum"), n_categories=("n_categories", "sum")))
    _agg["country"] = _OTHER
    _agg["rank"] = 0
    cc = pd.concat([cc[~cc.index.isin(_small.index)], _agg], ignore_index=True)
NCTRY = int(cc.n_categories.sum())           # 104, named or not
NNAMED = int((cc.country != _OTHER).sum())

reg = cc.groupby("region").agg(authors=("authors", "sum"), first=("first", "sum"),
                               last=("last", "sum"), corr=("corr", "sum"),
                               nctry=("n_categories", "sum")).reset_index()
# ⚠ nctry sums n_categories, not rows: after the collapse a region's tail is one
# row standing for many countries, and counting rows would report Europe as 12
# countries when it has 36.
_rp = Counter(_agg["region_papers"])
reg["papers"] = reg.region.map(lambda g: _rp.get(g, 0))
reg = reg.sort_values("authors", ascending=False).reset_index(drop=True)

# the aggregate row is pinned last within its region: sorted on size it lands
# among the named countries and reads as though it were one of them
srt = (cc.assign(_tail=(cc.country == _OTHER).astype(int))
         .sort_values(["_tail", "authors"], ascending=[True, False])
         .reset_index(drop=True))
NONSA = srt[srt.country != SA].reset_index(drop=True)
SAROW = srt[srt.country == SA].iloc[0]
MAXA = int(NONSA.authors.max())
MAXROLE = int(max(NONSA["first"].max(), NONSA["last"].max(), NONSA["corr"].max()))
MAXP = int(NONSA.papers.max())

assert TOT == 3832 and UNIQ == 3508 and NPAP == 385 and NCTRY == 104, \
    (TOT, UNIQ, NPAP, len(cc))


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

    def text(self, x, y, s, pt=T_BODY, col=INK, ha="left", weight="normal", style="normal"):
        self.sizes.append(pt)
        return self.ax.text(x, y, s, fontsize=pt, color=col, ha=ha, va="baseline",
                            fontweight=weight, fontstyle=style)

    def rect(self, x, y, w, h, col, alpha=1.0, ec="none", lw=0.0):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=col, alpha=alpha,
                                    edgecolor=ec, linewidth=lw))

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
        """Truncate to fit, measured. Char-count truncation is what let 'Bosnia and
        Herzegovina' overrun its column in the screen mock-up."""
        if self.measure(s, pt) <= max_mm:
            return s
        for k in range(len(s) - 1, 2, -1):
            cand = s[:k].rstrip() + "…"
            if self.measure(cand, pt) <= max_mm:
                return cand
        return s[:3]


# ---------------------------------------------------------------------------- columns
# Fractions of the sub-column width. Numeric columns are RIGHT-aligned so a value that
# gains a digit cannot push into its neighbour.
FR = dict(rank=.036, chip=.048, name=.066, abar=.335, abw=.105, an=.545, sh=.610,
          r1=.700, r2=.782, r3=.864, pbar=.884, pbw=.068, pn=1.0)
# ⚠ Every vertical constant below is used BOTH to draw and to compute the page height.
# The first cut carried a guessed height (34 mm for the region panel) and design A's last
# six rows fell off the bottom of the canvas - matplotlib draws them happily and only the
# spill assertion catches it.
ROW = 2.75           # country row pitch, mm (S7 runs 2.65 at the same 6.5 pt)
BARH = 1.9
TOP = 5.0            # page top to panel A label
REG_HEAD = 8.4       # panel A label to first region baseline
REG_ROW = 5.2        # region row pitch
GAP_AB = 6.2         # panel A block to panel B label
GAP_ANCH = 6.4       # panel B label to anchor-row baseline
ANCH_H = 4.2         # anchor row block
GAP_HDR = 4.0        # anchor row to column header
HDR_H = 3.4          # column header to first country row
FOOT_H = 11.0        # two footnote lines plus bottom margin


def region_h():
    return REG_HEAD + len(reg) * REG_ROW


def table_top():
    """Baseline of the first country row, measured from the page top."""
    return (TOP + region_h() + GAP_AB + GAP_ANCH + ANCH_H + GAP_HDR + HDR_H)


def role_tint(v):
    return 0.10 + 0.60 * (float(v) / MAXROLE) ** 0.5


def country_row(p, x, y, cw, r, rank=None, chip=True):
    col = TOL[r.region]
    if rank is not None:
        p.text(x + cw * FR["rank"], y, str(rank), T_SMALL, FAINT, ha="right")
    if chip:
        p.rect(x + cw * FR["chip"], y - 1.6, 0.85, 1.9, col)
    nmax = cw * (FR["abar"] - FR["name"]) - 1.6
    p.text(x + cw * FR["name"], y, p.fit(str(r.country), nmax, T_SMALL), T_SMALL, INK)
    p.rect(x + cw * FR["abar"], y - 1.75, max(cw * FR["abw"] * r.authors / MAXA, 0.18),
           BARH, col)
    p.text(x + cw * FR["an"], y, format(int(r.authors), ","), T_SMALL, INK, ha="right")
    p.text(x + cw * FR["sh"], y, "%.1f" % (100.0 * r.authors / TOT), T_SMALL, MUT, ha="right")
    for key, fk in (("first", "r1"), ("last", "r2"), ("corr", "r3")):
        v = int(r[key])
        rr = x + cw * FR[fk]
        if v:
            tw = min(cw * .072, 9.0)
            p.rect(rr + 0.8 - tw, y - 2.2, tw, 2.8, col, alpha=role_tint(v))
        p.text(rr, y, str(v) if v else "·", T_SMALL, INK if v else FAINT, ha="right")
    p.rect(x + cw * FR["pbar"], y - 1.75,
           max(cw * FR["pbw"] * r.papers / MAXP, 0.18), BARH, col, alpha=0.45)
    p.text(x + cw * FR["pn"], y, str(int(r.papers)), T_SMALL, INK, ha="right")


def col_header(p, x, y, cw, rank=True):
    p.text(x + cw * FR["abar"], y - 3.4, "AUTHOR LEVEL", 5.6, "#0f5c6b")
    p.sizes.pop()                      # a rule label, deliberately below the type floor
    p.text(x + cw * FR["pn"], y - 3.4, "PAPER LEVEL", 5.6, "#0f5c6b", ha="right")
    p.sizes.pop()
    if rank:
        p.text(x + cw * FR["rank"], y, "#", T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["name"], y, "Country", T_SMALL, FAINT)
    p.text(x + cw * FR["abar"], y, "Authors", T_SMALL, FAINT)
    p.text(x + cw * FR["sh"], y, "%", T_SMALL, FAINT, ha="right")
    for lab, fk in (("First", "r1"), ("Last", "r2"), ("Corr", "r3")):
        p.text(x + cw * FR[fk], y, lab, T_SMALL, FAINT, ha="right")
    p.text(x + cw * FR["pn"], y, "Papers", T_SMALL, FAINT, ha="right")
    p.line(x, y + 1.1, x + cw, y + 1.1, RULE, 0.5)


def region_panel(p, y0):
    p.text(0, y0, "A", 9.5, INK, weight="bold")
    p.text(4.6, y0, "By world region", T_PANEL, INK, weight="bold")
    p.text(4.6, y0 + 3.4, "filled bar: author positions (author level)   │   open bar: "
           "papers with ≥1 author from the region (paper level)", T_SMALL, MUT)
    lab, bx, bw = 30.0, 32.0, 74.0
    mxa = float(reg.authors.max())
    for i, r in reg.iterrows():
        yy = y0 + REG_HEAD + i * REG_ROW
        col = TOL[r.region]
        p.text(lab, yy, r.region, T_BODY, INK, ha="right")
        p.rect(bx, yy - 2.0, bw * r.authors / mxa, 2.2, col)
        p.text(bx + bw * r.authors / mxa + 1.2, yy - 0.2,
               "%s (%.1f%%)" % (format(int(r.authors), ","), 100.0 * r.authors / TOT),
               T_SMALL, INK)
        p.rect(bx, yy + 0.6, bw * r.papers / mxa, 1.7, "none", ec=col, lw=0.45)
        p.text(bx + bw * r.papers / mxa + 1.2, yy + 2.1, "%d papers" % int(r.papers),
               T_SMALL, MUT)
        p.text(W, yy, "%d countries" % int(r.nctry), T_SMALL, FAINT, ha="right")
    return y0 + region_h()


def anchor_row(p, y, cw=W):
    p.rect(0, y - 2.6, W, 3.9, TOL["Gulf"], alpha=0.08)
    p.text(1.4, y, "Saudi Arabia", T_SMALL, INK, weight="bold")
    p.text(22.0, y, "%s author positions (%.1f%%)   │   first %d   │   last %d   "
           "│   corr %d   │   all %d papers"
           % (format(int(SAROW.authors), ","), 100.0 * SAROW.authors / TOT,
              int(SAROW["first"]), int(SAROW["last"]), int(SAROW["corr"]),
              int(SAROW.papers)), T_SMALL, INK)
    return y + 4.2


def footer(p, y):
    p.text(0, y, "Shares are of %s country-credited author positions, not the %s distinct "
           "author positions: %d authors carry affiliations in more than one country and are "
           "credited to each." % (format(TOT, ","), format(UNIQ, ","), NDUAL), T_SMALL, MUT)
    p.text(0, y + 3.0, "Saudi Arabia appears on all %d papers by inclusion criteria, so the "
           "Papers column is informative only for the other %d countries; bars are scaled to "
           "the largest of those." % (NPAP, NCTRY - 1), T_SMALL, MUT)
    p.text(0, y + 6.0, "The %d countries with %d or more papers are named; within each region "
           "the rest are one Other row, because a country appearing once would identify that "
           "paper." % (NNAMED - 1, K_MIN_PAPERS), T_SMALL, MUT)


# ---------------------------------------------------------------------------- designs
def design_A():
    per = 52
    h = table_top() + (per - 1) * ROW + FOOT_H
    p = Page(h)
    yb = region_panel(p, TOP)
    y2 = yb + GAP_AB
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "By country: all %d, ranked by author positions" % len(cc),
           T_PANEL, INK, weight="bold")
    ya = anchor_row(p, y2 + GAP_ANCH)
    cw = (W - 6.0) / 2.0
    ytab = ya + GAP_HDR
    for c in (0, 1):
        col_header(p, c * (cw + 6.0), ytab, cw)
    for i, r in NONSA.iterrows():
        c, row = i // per, i % per
        country_row(p, c * (cw + 6.0), ytab + HDR_H + row * ROW, cw, r, rank=int(r["rank"]))
    footer(p, ytab + HDR_H + (per - 1) * ROW + 4.5)
    return p, h, "Design A"


def design_B():
    seq = []
    for g in list(reg.region):
        seq.append(("H", g))
        for _, r in srt[(srt.region == g) & (srt.country != SA)].iterrows():
            seq.append(("R", r))
    half = (len(seq) + 1) // 2 + 1
    h = table_top() + (half - 1) * ROW + FOOT_H
    p = Page(h)
    yb = region_panel(p, TOP)
    y2 = yb + GAP_AB
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "By country, grouped within region", T_PANEL, INK, weight="bold")
    ya = anchor_row(p, y2 + GAP_ANCH)
    cw = (W - 6.0) / 2.0
    ytab = ya + GAP_HDR
    for c in (0, 1):
        col_header(p, c * (cw + 6.0), ytab, cw, rank=False)

    def grp(x, y, g, cont=False):
        rr = reg[reg.region == g].iloc[0]
        p.rect(x, y - 2.3, cw, 3.2, TOL[g], alpha=0.14)
        lab = ("%s (continued)" % g if cont else
               "%s: %s positions, %d countries, %d papers"
               % (g, format(int(rr.authors), ","), int(rr.nctry), int(rr.papers)))
        p.text(x + 1.2, y, lab, T_SMALL, INK, weight="bold")

    ci, ri, cur = 0, 0, None
    for kind, a in seq:
        # ⚠ a region running over the column break must announce itself again, or column
        # two opens on countries with no region attached to them.
        if ri >= half and ci == 0:
            ci, ri = 1, 0
            if kind == "R" and cur:
                grp(cw + 6.0, ytab + HDR_H, cur, cont=True)
                ri += 1
        x = ci * (cw + 6.0)
        y = ytab + HDR_H + ri * ROW
        if kind == "H":
            cur = a
            grp(x, y, a)
        else:
            country_row(p, x, y, cw, a, rank=None, chip=False)
        ri += 1
    footer(p, ytab + HDR_H + (half - 1) * ROW + 4.5)
    return p, h, "Design B"


def design_C():
    n = 30
    rw = 3.5
    tail = NONSA.iloc[n:]
    NTAIL_LINES = 7                       # re-asserted below once the lines are measured
    h = (table_top() + 3.4 + (n - 1) * rw + 5.0 + 7.4
         + NTAIL_LINES * 2.9 + 3.5 + FOOT_H)
    p = Page(h)
    yb = region_panel(p, TOP)
    y2 = yb + GAP_AB
    p.text(0, y2, "B", 9.5, INK, weight="bold")
    p.text(4.6, y2, "By country: the %d largest, in full" % n, T_PANEL, INK,
           weight="bold")
    p.text(4.6, y2 + 3.4, "these %d hold %.1f%% of all author positions"
           % (n + 1, 100.0 * (SAROW.authors + NONSA.head(n).authors.sum()) / TOT),
           T_SMALL, MUT)
    ya = anchor_row(p, y2 + GAP_ANCH + 3.4)
    ytab = ya + GAP_HDR
    col_header(p, 0, ytab, W)
    for i, r in NONSA.head(n).iterrows():
        country_row(p, 0, ytab + HDR_H + i * rw, W, r, rank=int(r["rank"]))
    yt = ytab + HDR_H + (n - 1) * rw + 5.0
    p.text(0, yt, "C", 9.5, INK, weight="bold")
    p.text(4.6, yt, "The remaining %d countries" % len(tail), T_PANEL, INK, weight="bold")
    p.text(4.6, yt + 3.4, "%d countries  │  %s author positions (%.1f%%)  │  "
           "first %d  │  last %d  │  corr %d"
           % (len(tail), format(int(tail.authors.sum()), ","),
              100.0 * tail.authors.sum() / TOT, int(tail["first"].sum()),
              int(tail["last"].sum()), int(tail["corr"].sum())), T_SMALL, MUT)
    items = ["%s %d" % (r.country, r.authors) for _, r in tail.iterrows()]
    lines, cur = [], ""
    for it in items:
        cand = (cur + ", " + it) if cur else it
        if p.measure(cand, T_SMALL) > W - 6.0:
            lines.append(cur)
            cur = it
        else:
            cur = cand
    if cur:
        lines.append(cur)
    # the page height was reserved for NTAIL_LINES; if the measured wrap needs more, the
    # figure would grow past its own canvas, so make that a hard failure rather than a
    # silent overflow the spill check reports as six unrelated stray labels.
    assert len(lines) <= NTAIL_LINES, (len(lines), NTAIL_LINES)
    for k, ln in enumerate(lines):
        p.text(4.6, yt + 7.4 + k * 2.9, ln, T_SMALL, MUT)
    footer(p, yt + 7.4 + NTAIL_LINES * 2.9 + 3.5)
    return p, h, "Design C"


# ---------------------------------------------------------------------------- emit
def emit(p, h, stem, tag, formats=("tif",)):
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
            spill.append((round(x0, 1), round(x1, 1), t.get_text()[:44]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill[:6]
    # Two labels touching is the error a screen preview hides best - "288" and "7.5"
    # abutting read as "2887.5" and nothing warns. Compare the drawn rectangles directly.
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
    t = Image.open(base + ".tif")
    assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0), \
        (t.mode, t.tag_v2.get(259), t.info.get("dpi"))
    px = t.size
    t.close()
    print("  %-9s %.0f x %.0f mm | %d x %d px | smallest type %.1f pt"
          % (tag, W, h, px[0], px[1], min(p.sizes)))
    for ext in formats:
        fp = base + "." + ext
        print("      %-62s %8.1f KB" % (fp, os.path.getsize(fp) / 1024))


BUILD = {"A": (design_A, "08_25_2026_S1_author_countries_designA"),
         "B": (design_B, "08_25_2026_S1_author_countries_designB"),
         "C": (design_C, "08_25_2026_S1_author_countries_designC")}

if __name__ == "__main__":
    args = [a.upper() for a in sys.argv[1:] if a.upper() in BUILD] or ["B"]
    fmts = ("tif",) if len(args) > 1 else ("pdf", "tif", "png")
    print("Supplementary Figure S2 - author countries   (%s)" % ", ".join(fmts))
    for k in args:
        fn, stem = BUILD[k]
        pg, hh, tag = fn()
        emit(pg, hh, stem, tag, fmts)
