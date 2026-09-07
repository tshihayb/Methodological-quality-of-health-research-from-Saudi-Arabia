# -*- coding: utf-8 -*-
"""PRISMA flow as a submission-ready journal figure: PDF (vector), TIFF and PNG (600 dpi).

    python code/figures/08_21_2026_prisma_print_figure.py

WHY THIS IS A REBUILD AND NOT A CONVERSION
`08_14_2026_prisma_two_stage.py` draws the same flow for the screen, on a 1,200-unit canvas
with 11-13.5 unit type. Scaled to a 180 mm journal column that type lands at about 5.7 pt,
under every journal's 6-7 pt floor, and the cream background and hairline rules do not
survive CMYK printing. So the figure is rebuilt in true print geometry: millimetres for
layout, points for type, nothing below 6.5 pt, white background, one accent colour that
still separates at 40% grey.

OUTPUT (outputs/figures/)
    08_21_2026_PRISMA_flow.pdf   vector, fonts embedded as TrueType (Type 42)
    08_21_2026_PRISMA_flow.tif   600 dpi, LZW compressed
    08_21_2026_PRISMA_flow.png   600 dpi
and the same three with the `_with_provenance_panel` suffix - see the note below.

⚠ THE PROVENANCE PANEL IS OFF BY DEFAULT
The screen figure carries a footer panel breaking down how each of the 236 exclusion reasons
was established (169 agreed / 18 adjudicated / 7 + 38 + 4 language-model assisted). Those
counts are the ones currently out with TSA and YA for determination, and tracing them to the
original screening workbooks on 2026-08-21 already showed only 162 rest on two screeners
agreeing. Printing them at publication quality would fix a number that is being revised. The
panel is also not PRISMA content - it belongs in Supplementary Methods 2. Both variants are
written so the choice stays with the author; set PANEL = True for the panel version alone.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.path import Path
from matplotlib.patches import PathPatch

D = r"."
os.chdir(D)
OUTDIR = "outputs/figures"
STEM = "08_21_2026_PRISMA_flow"

# --- print rules -------------------------------------------------------------
matplotlib.rcParams.update({
    "pdf.fonttype": 42,        # embed TrueType, not Type 3 - journals reject Type 3
    "ps.fonttype": 42,
    "font.family": "Arial",
    "svg.fonttype": "none",
})
MM = 1.0                        # the data unit IS the millimetre
PT2MM = 25.4 / 72.0
W = 180.0                       # double-column width, the common journal maximum

INK = "#111417"                 # near-black: prints as true black, screens as soft
MUT = "#4a5259"                 # secondary text, ~70% grey
AC = "#0f5c6b"                  # accent teal, 40% grey when desaturated
BD = "#9aa3a9"                  # box rule
FILL = "#ffffff"
EXF = "#f2f0ec"                 # excluded-at-screening panel
AMF = "#f6ead7"                 # post-review exclusions
AMB = "#b57f2a"
AMT = "#7a4d0d"
SUF = "#e9f1f2"                 # supplementary sample
SUB = "#7fa9b2"
ARR = "#6f787e"

# type scale, in points. Nothing below 6.5.
T_TITLE, T_HEAD, T_SUB, T_NUM, T_BAND, T_SMALL = 9.5, 7.5, 6.6, 8.5, 6.8, 6.5
LEAD = 1.30                     # line leading multiplier
PADX, PADY = 2.6, 2.2           # box padding, mm

# columns, mm
SPINE_X, SPINE_W = 12.0, 62.0
SIDE_X, SIDE_W = 78.0, 54.0
SUP_X, SUP_W = 136.0, 42.0
SPINE_CX = SPINE_X + SPINE_W / 2
SUP_CX = SUP_X + SUP_W / 2
RAIL_X = 5.0

PANEL = os.environ.get("PRISMA_PANEL", "") == "1"


def line_h(pt):
    return pt * LEAD * PT2MM


def box_h(rows):
    return PADY * 2 + sum(line_h(r[1]) for r in rows)


class Fig:
    """A tiny top-down millimetre canvas over matplotlib."""

    def __init__(self, height_mm):
        self.H = height_mm
        self.fig = plt.figure(figsize=(W / 25.4, height_mm / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(height_mm, 0)         # y grows downward
        self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, height_mm, fc="white", ec="none", zorder=0))

    def rect(self, x, y, w, h, fc=FILL, ec=BD, lw=0.5, r=1.4, z=2):
        self.ax.add_patch(FancyBboxPatch(
            (x + r, y + r), w - 2 * r, h - 2 * r,
            boxstyle="round,pad=%.3f,rounding_size=%.3f" % (r, r),
            fc=fc, ec=ec, lw=lw, zorder=z, mutation_aspect=1))

    def text(self, x, y, s, pt=T_SUB, c=INK, weight="normal", ha="left", z=4, style=None):
        self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va="top",
                     zorder=z, fontstyle=style or "normal")

    def box(self, x, y, w, rows, fc=FILL, ec=BD, lw=0.5):
        """rows: (text, pt, colour, weight) or (text, pt, colour, weight, 'right-hand value')"""
        h = box_h(rows)
        self.rect(x, y, w, h, fc, ec, lw)
        ty = y + PADY
        for r in rows:
            s, pt, c, wt = r[:4]
            self.text(x + PADX, ty, s, pt, c, wt)
            if len(r) > 4 and r[4]:
                self.text(x + w - PADX, ty, r[4], pt, INK, "bold", ha="right")
            ty += line_h(pt)
        return h

    def side_arrow(self, y_top, h_spine, colour=ARR, lw=0.6):
        """Spine box -> side box, always horizontal.

        Taking the source midpoint at one end and the target midpoint at the other makes
        the arrow slant whenever the two boxes differ in height, which they usually do.
        Both ends sit on the SPINE box's midpoint instead; the side boxes are the taller
        of each pair, so the arrow still lands well inside them.
        """
        y = y_top + h_spine / 2
        self.arrow(SPINE_X + SPINE_W, y, SIDE_X, y, colour, lw)

    def arrow(self, x1, y1, x2, y2, colour=ARR, lw=0.6, dashed=False, z=3):
        self.ax.add_patch(FancyArrowPatch(
            (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=5.0,
            lw=lw, color=colour, zorder=z, shrinkA=0, shrinkB=0,
            linestyle=(0, (2.2, 1.6)) if dashed else "solid",
            joinstyle="miter", capstyle="butt"))

    def elbow(self, pts, colour=ARR, lw=0.6, dashed=False, z=3):
        """Orthogonal polyline with an arrowhead on the final segment."""
        verts = list(pts)
        self.ax.add_patch(PathPatch(
            Path(verts[:-1], [Path.MOVETO] + [Path.LINETO] * (len(verts) - 2)),
            fc="none", ec=colour, lw=lw, zorder=z,
            linestyle=(0, (2.2, 1.6)) if dashed else "solid"))
        self.arrow(verts[-2][0], verts[-2][1], verts[-1][0], verts[-1][1], colour, lw, dashed, z)

    def band(self, y0, y1, label):
        self.ax.add_patch(Rectangle((RAIL_X, y0), 1.1, y1 - y0, fc=AC, ec="none",
                                    alpha=0.9, zorder=2))
        # one font family across the whole figure: no condensed stretch, which would
        # pull Arial Narrow into the PDF as a third embedded subset
        self.ax.text(RAIL_X - 1.0, (y0 + y1) / 2, label.upper(), fontsize=T_BAND, color=AC,
                     fontweight="bold", ha="center", va="center", rotation=90, zorder=4,
                     linespacing=1)


# =============================================================================
# Content — laid out once to measure, then drawn
# =============================================================================
REASONS = [("Non-human / laboratory", "174"), ("Non-health topic", "22"),
           ("Review (narrative / systematic)", "14"), ("Qualitative research", "11"),
           ("Non-empirical (protocol / simulation)", "9"), ("Case report / series", "6")]

IDENT = [("Records identified in PubMed", T_HEAD, INK, "bold"),
         ("2022, Saudi-affiliated; reproducible query", T_SUB, MUT, "normal"),
         ("n = 5,558", T_NUM, AC, "bold")]
MAIN = [("Main random sample", T_HEAD, INK, "bold"),
        ("simple random sample, without replacement", T_SUB, MUT, "normal"),
        ("n = 1,000", T_NUM, INK, "bold")]
SUP = [("Supplementary sample", T_HEAD, INK, "bold"),
       ("simple random sample, same query", T_SUB, MUT, "normal"),
       ("n = 20", T_NUM, INK, "bold")]
NOTSCR = [("Not screened: target met", T_SUB, MUT, "bold"),
          ("sample-size target of N = 385 reached;", T_SMALL, MUT, "normal"),
          ("records 622–1,000 never assessed", T_SMALL, MUT, "normal", "379")]
SCREEN = [("Records screened, in random order", T_HEAD, INK, "bold"),
          ("title and abstract, then full text", T_SUB, MUT, "normal"),
          ("n = 621", T_NUM, AC, "bold")]
PASSED = [("Passed screening", T_HEAD, INK, "bold"), ("n = 385", T_NUM, AC, "bold")]
ADDED = [("Added to the analysis", T_SUB, INK, "bold", "3"),
         ("2 causal · 1 predictive", T_SMALL, MUT, "normal")]
NOTADD = [("Not added", T_SUB, MUT, "bold", "17"),
          ("eligible but surplus to target", T_SMALL, MUT, "normal", "5"),
          ("excluded with reasons", T_SMALL, MUT, "normal", "12")]
ASSIGN = [("Assigned for dual quality review", T_HEAD, INK, "bold"),
          ("13 reviewers · 2 per paper · 770 reviews", T_SUB, MUT, "normal"),
          ("5 recusals (conflict of interest) re-assigned", T_SMALL, MUT, "normal")]
RECUSAL = [("Recusal reasons: conflict of interest", T_SUB, MUT, "bold", "5"),
           ("the co-principal investigator is a co-author", T_SMALL, MUT, "normal"),
           ("an author is a relative", T_SMALL, MUT, "normal"),
           ("collaborator with the first author", T_SMALL, MUT, "normal"),
           ("an author heads the reviewer's department", T_SMALL, MUT, "normal"),
           ("not stated; re-covered by a third reviewer", T_SMALL, MUT, "normal")]
RETAIN = [("Retained after post-hoc exclusions", T_HEAD, INK, "bold"),
          ("n = 382", T_NUM, AC, "bold")]
POSTEX = [("Excluded after review", T_SUB, AMT, "bold", "3"),
          ("co-authored by a study reviewer", T_SMALL, AMT, "normal", "1"),
          ("no Saudi affiliation", T_SMALL, AMT, "normal", "2")]
FINAL = [("Studies in the final analysis", T_HEAD, "#ffffff", "bold"),
         ("n = 385", T_TITLE, "#ffffff", "bold"),
         ("382 main sample + 3 supplementary · 770 reviews", T_SMALL, "#d9e9ec", "normal")]
PROV = [("169", "both screeners recorded the same reason"),
        ("18", "screeners disagreed and adjudicated it"),
        ("7", "disagreed, not adjudicated: language model"),
        ("38", "one screener gave a reason: model as second"),
        ("4", "no screener reason: model determined it")]

GAP = 5.0                                     # vertical gap between spine boxes
TOP = 13.0                                    # below the title


def layout():
    """Return (total height, dict of y positions)."""
    y = {}
    cur = TOP
    y["ident"] = cur
    cur += box_h(IDENT) + GAP + 2.0
    y["draw"] = cur                                    # main + supplementary side by side
    cur += max(box_h(MAIN), box_h(SUP), box_h(NOTSCR)) + GAP
    y["screen"] = cur
    ex_h = PADY * 2 + line_h(T_SUB) + line_h(T_SMALL) + len(REASONS) * line_h(T_SMALL)
    cur += max(box_h(SCREEN), ex_h) + GAP
    y["passed"] = cur
    cur += box_h(PASSED) + GAP + 2.0
    y["assign"] = cur
    cur += max(box_h(ASSIGN), box_h(RECUSAL)) + GAP
    y["retain"] = cur
    cur += max(box_h(RETAIN), box_h(POSTEX)) + GAP + 1.0
    y["final"] = cur
    cur += box_h(FINAL) + PADY * 2
    if PANEL:
        cur += 4.0
        y["panel"] = cur
        cur += PADY * 2 + line_h(T_SUB) + 3 * line_h(T_SMALL)
    y["_ex_h"] = ex_h
    return cur + 5.0, y


H, Y = layout()
f = Fig(H)

# --- title -------------------------------------------------------------------
f.text(SPINE_X, 4.0, "Study selection and review conduct", T_TITLE, INK, "bold")
f.text(SPINE_X, 4.0 + line_h(T_TITLE), "PRISMA flow for the 2022 Saudi health-research quality baseline",
       T_SUB, MUT)

# --- identification ----------------------------------------------------------
h_id = f.box(SPINE_X, Y["ident"], SPINE_W, IDENT)
id_b = Y["ident"] + h_id

# --- the two draws -----------------------------------------------------------
h_main = f.box(SPINE_X, Y["draw"], SPINE_W, MAIN)
h_sup = f.box(SUP_X, Y["draw"], SUP_W, SUP, fc=SUF, ec=SUB)
h_ns = f.box(SIDE_X, Y["draw"], SIDE_W, NOTSCR, fc=EXF, ec=BD)
f.arrow(SPINE_CX, id_b, SPINE_CX, Y["draw"])
f.elbow([(SPINE_CX, id_b + 1.2), (SUP_CX, id_b + 1.2), (SUP_CX, Y["draw"])])
f.side_arrow(Y["draw"], h_main)
main_b = Y["draw"] + h_main

# --- screening ---------------------------------------------------------------
h_scr = f.box(SPINE_X, Y["screen"], SPINE_W, SCREEN)
f.arrow(SPINE_CX, main_b, SPINE_CX, Y["screen"])
ex_h = Y["_ex_h"]
f.rect(SIDE_X, Y["screen"], SIDE_W, ex_h, EXF, BD)
ty = Y["screen"] + PADY
f.text(SIDE_X + PADX, ty, "Excluded at screening", T_SUB, INK, "bold")
f.text(SIDE_X + SIDE_W - PADX, ty, "236", T_SUB, INK, "bold", ha="right")
ty += line_h(T_SUB)
f.text(SIDE_X + PADX, ty, "eligibility reasons:", T_SMALL, MUT, "bold")
ty += line_h(T_SMALL)
for lab, cnt in REASONS:
    f.text(SIDE_X + PADX + 1.2, ty, lab, T_SMALL, MUT)
    f.text(SIDE_X + SIDE_W - PADX, ty, cnt, T_SMALL, INK, "bold", ha="right")
    ty += line_h(T_SMALL)
f.side_arrow(Y["screen"], h_scr)
scr_b = Y["screen"] + h_scr

h_pass = f.box(SPINE_X, Y["passed"], SPINE_W, PASSED)
f.arrow(SPINE_CX, scr_b, SPINE_CX, Y["passed"])
pass_b = Y["passed"] + h_pass

# --- supplementary branch ----------------------------------------------------
sup_b = Y["draw"] + h_sup
add_y = sup_b + GAP + 1.0
h_add = f.box(SUP_X, add_y, SUP_W, ADDED, fc=SUF, ec=SUB)
f.arrow(SUP_CX, sup_b, SUP_CX, add_y)
na_y = add_y + h_add + GAP
h_na = f.box(SUP_X, na_y, SUP_W, NOTADD, fc=EXF, ec=BD)
f.arrow(SUP_CX, add_y + h_add, SUP_CX, na_y)

# --- review conduct ----------------------------------------------------------
h_asg = f.box(SPINE_X, Y["assign"], SPINE_W, ASSIGN)
f.arrow(SPINE_CX, pass_b, SPINE_CX, Y["assign"])
h_rec = f.box(SIDE_X, Y["assign"], SIDE_W, RECUSAL, fc=EXF, ec=BD)
f.side_arrow(Y["assign"], h_asg)
asg_b = Y["assign"] + h_asg

h_ret = f.box(SPINE_X, Y["retain"], SPINE_W, RETAIN)
f.arrow(SPINE_CX, asg_b, SPINE_CX, Y["retain"])
h_pe = f.box(SIDE_X, Y["retain"], SIDE_W, POSTEX, fc=AMF, ec=AMB)
f.side_arrow(Y["retain"], h_ret)
ret_b = Y["retain"] + h_ret

# --- final -------------------------------------------------------------------
h_fin = f.box(SPINE_X, Y["final"], SPINE_W, FINAL, fc=AC, ec=AC)
f.arrow(SPINE_CX, ret_b, SPINE_CX, Y["final"])
# the 3 supplementary studies join the final box: out of the left of "Added",
# down the gap between the side and supplementary columns, then in from the right
gap_x = (SIDE_X + SIDE_W + SUP_X) / 2
f.elbow([(SUP_X, add_y + h_add / 2), (gap_x, add_y + h_add / 2),
         (gap_x, Y["final"] + h_fin / 2), (SPINE_X + SPINE_W, Y["final"] + h_fin / 2)],
        colour=AC, lw=0.7, dashed=True)

# --- optional provenance panel ----------------------------------------------
if PANEL:
    py = Y["panel"]
    ph = PADY * 2 + line_h(T_SUB) + 3 * line_h(T_SMALL)
    f.rect(SPINE_X, py, SUP_X + SUP_W - SPINE_X, ph, SUF, SUB)
    f.text(SPINE_X + PADX, py + PADY,
           "How each “excluded at screening” reason (n = 236) was established",
           T_SUB, INK, "bold")
    c1 = SPINE_X + PADX + 6.0
    c2 = SPINE_X + (SUP_X + SUP_W - SPINE_X) / 2 + 4.0
    y0 = py + PADY + line_h(T_SUB)
    for i, (n, lab) in enumerate(PROV):
        cx = c1 if i < 3 else c2
        yy = y0 + (i if i < 3 else i - 3) * line_h(T_SMALL)
        f.text(cx, yy, n, T_SMALL, AC, "bold", ha="right")
        f.text(cx + 1.4, yy, lab, T_SMALL, MUT)
    f.text(c2 - 6.0, y0 + 2 * line_h(T_SMALL),
           "model inputs used the agreed reasons as worked examples", T_SMALL, MUT)

# --- band rail ---------------------------------------------------------------
f.band(Y["ident"], id_b, "Identification")
f.band(Y["draw"] - 0.5, pass_b + 0.5, "Screening")
f.band(Y["assign"] - 0.5, ret_b + 0.5, "Review conduct")
f.band(Y["final"] - 0.5, Y["final"] + h_fin + 0.5, "Analysed")

# =============================================================================
# Write the three formats
# =============================================================================
suffix = "_with_provenance_panel" if PANEL else ""
base = os.path.join(OUTDIR, STEM + suffix)
f.fig.savefig(base + ".pdf", format="pdf", facecolor="white")
f.fig.savefig(base + ".png", dpi=600, facecolor="white")
# TIFF via PIL rather than savefig: matplotlib writes RGBA, and an alpha channel in a
# submitted TIFF trips print workflows. Flatten onto white, then LZW at 600 dpi.
from PIL import Image
_png = Image.open(base + ".png")
_rgb = Image.new("RGB", _png.size, "white")
_rgb.paste(_png, mask=_png.split()[3] if _png.mode == "RGBA" else None)
_rgb.save(base + ".tif", format="TIFF", compression="tiff_lzw", dpi=(600, 600))
_png.close()
plt.close(f.fig)

# --- self-check: the three things a production editor rejects a figure for -----
from pypdf import PdfReader
_r = PdfReader(base + ".pdf")
for _k, _v in _r.pages[0]["/Resources"]["/Font"].items():
    _fo = _v.get_object()
    _df = _fo.get("/DescendantFonts")
    _d = _df[0].get_object() if _df else _fo
    _desc = _d.get("/FontDescriptor")
    assert _d.get("/Subtype") != "/Type3", "%s is a Type 3 font" % _fo.get("/BaseFont")
    assert _desc and any(x in _desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), \
        "%s is not embedded" % _fo.get("/BaseFont")
_mb = _r.pages[0].mediabox
assert abs(float(_mb[2]) * 25.4 / 72 - W) < 0.5, "PDF is not %.0f mm wide" % W
_t = Image.open(base + ".tif")
assert _t.mode == "RGB" and _t.tag_v2[259] == 5 and _t.info["dpi"] == (600.0, 600.0), \
    "TIFF must be RGB, LZW, 600 dpi - got %s / %s / %s" % (_t.mode, _t.tag_v2[259], _t.info["dpi"])
_t.close()

for ext in ("pdf", "png", "tif"):
    p = base + "." + ext
    print("  %-58s %7.1f KB" % (p, os.path.getsize(p) / 1024))
print("  %.0f x %.0f mm · %.0f x %.0f px at 600 dpi · smallest type %.1f pt · "
      "PDF fonts embedded, TIFF RGB/LZW"
      % (W, H, W / 25.4 * 600, H / 25.4 * 600, T_SMALL))
