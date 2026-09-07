# -*- coding: utf-8 -*-
"""Supplementary Table S1, the appraisal instrument, as a print-native table.
Multi-page PDF plus one TIFF and PNG per page.

    python code/tables/08_22_2026_scoring_framework_print_table.py

WHY THIS EXISTS ALONGSIDE THE HTML
The HTML version is the readable one and stays (it is also the artifact behind
55dac2ad).  But a supplement is submitted as files a production system can place,
and an HTML page is not one: journals want a table they can typeset or an image
they can drop in.  This writes the same instrument at 180 mm, nothing below
6.5 pt, Arial embedded, TIFF RGB/LZW at 600 dpi - the house recipe every other
figure in the submission follows.

⚠ ONE SOURCE.  ITEMS, the census, the counts and the footnotes are imported from
code/tables/08_22_2026_scoring_framework.py, so this cannot disagree with the HTML
or with Figure 4.  Importing it re-runs its checks: every item's wording verbatim
against the instrument PDF, and the scored-item set by name against the scorer.

ONE PAGE PER STUDY TASK
A reader appraising a causal study should never have to hold two pages at once, and
the two instruments are different instruments - so the task boundary is a HARD page
break, not a suggestion.  Page 1 is the causal instrument entire; page 2 is the
descriptive instrument, the items that classify rather than score, and the scoring
conventions.  Both are asserted below, so the structure cannot rot: a later edit that
lengthens a string can only make a page taller, never move an item across the break.

Within a page the flow is still COMPUTED, NOT ASSIGNED.  Blocks carry their own
measured height, a row never breaks across pages, and a section heading or a column
header is never stranded at the foot of one.  The height ceiling is a genuine safety
check rather than the thing driving the layout - which is why it is 265 mm, above
what the causal page actually needs (246 mm), instead of the old 245 mm.  Setting it
just under the content's real height is what silently turned this into three pages
after the graded scoring cuts were spelled out in full, and the packager, hardcoded
to copy two, then shipped a supplement missing its footnotes.

OUTPUT (outputs/tables/)
  08_22_2026_instrument_table.pdf           both pages, vector
  08_22_2026_instrument_table_p1.{tif,png}  causal
  08_22_2026_instrument_table_p2.{tif,png}  descriptive + classifiers + conventions
  Stale pages from a longer previous run are deleted first.
"""
import os, re, glob, importlib.util
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyBboxPatch

D = r"."
os.chdir(D)
_spec = importlib.util.spec_from_file_location("sf", "code/tables/08_22_2026_scoring_framework.py")
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)

OUTDIR, STEM = "outputs/tables", "08_22_2026_instrument_table"
matplotlib.rcParams.update({"pdf.fonttype": 42, "ps.fonttype": 42, "font.family": "Arial"})
PT2MM = 25.4 / 72.0
W, MIN_PT = 180.0, 6.5
INK, MUT, AC = "#111417", "#4a5259", "#0f5c6b"
RULE, BAND, GREY = "#c8ced2", "#f2f5f6", "#8b8f94"
REP, VAL, OFF, GATEC = "#5aa8b8", "#1b6b7a", "#c9ced2", "#c9922f"
T_TITLE, T_HEAD, T_BODY = 9.5, 7.5, 6.5
LEAD = 1.30
line_h = lambda pt: pt * LEAD * PT2MM

# columns, in mm
# The response column carries the long text (the graded ladders), the questions are
# mostly short, so it gets the wider half.  Rebalanced 2026-08-22 when spelling the
# scoring cuts out in full pushed page 1 to 260 mm and the height assertion caught it.
C_NUM, C_ITEM, W_ITEM, C_RESP, W_RESP, C_MARK = 12.0, 14.5, 68.0, 86.0, 85.0, 176.5
SQ = 3.0
TOP, PAD = 15.0, 1.3

plain = lambda s: re.sub(r"<[^>]+>", "", s)


class Page:
    def __init__(self, H):
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W); self.ax.set_ylim(H, 0); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 0), W, H, fc="white", ec="none", zorder=0))
        self.sizes = []

    def T(self, x, y, s, pt=T_BODY, c=INK, weight="normal", ha="left", va="top", z=4):
        self.sizes.append(pt)
        return self.ax.text(x, y, s, fontsize=pt, color=c, fontweight=weight, ha=ha, va=va, zorder=z)

    def width(self, s, pt, weight="normal"):
        t = self.ax.text(0, 0, s, fontsize=pt, fontweight=weight, zorder=0)
        w = t.get_window_extent(self.fig.canvas.get_renderer()).width / self.fig.dpi * 25.4
        t.remove()
        return w

    def wrap(self, s, maxw, pt=T_BODY):
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

    def wrap2(self, s, first_w, rest_w, pt=T_BODY):
        """Wrap where the first line is shorter than the rest, because a bold
        lead-in sits in front of it."""
        out, line, maxw = [], "", first_w
        for word in s.split(" "):
            trial = word if not line else line + " " + word
            if self.width(trial, pt) > maxw and line:
                out.append(line); line = word; maxw = rest_w
            else:
                line = trial
        if line:
            out.append(line)
        return out

    def block(self, x, y, lines, pt=T_BODY, c=INK, weight="normal"):
        for i, ln in enumerate(lines):
            self.T(x, y + i * line_h(pt), ln, pt, c, weight)
        return len(lines) * line_h(pt)

    def sq(self, x, y, fc, ec=None):
        self.ax.add_patch(FancyBboxPatch((x + 0.7, y + 0.7), SQ - 1.4, SQ - 1.4,
                                         boxstyle="round,pad=0.7,rounding_size=0.7",
                                         fc=fc, ec=ec or fc, lw=0.5, zorder=3, mutation_aspect=1))


MARK = {sf.SCORED_ROLE: None, sf.RECORDED: ("white", OFF), sf.GATE: (GATEC, GATEC)}
MAXH = 265.0        # page ceiling incl. margins - a safety check, not the layout driver.
                    # See the docstring: 245 sat just under what the causal page needs,
                    # so it, not the task boundary, decided where the pages broke.

# =============================================================================
# The document as a flat list of BLOCKS, then flowed onto pages.
#
# `sec` tags the block's section - "C" causal, "D" descriptive, "X" the classifier
# items and the scoring conventions that close the table.  It exists so the page
# assertions below can state which task each page carries.
#
# `brk` forces a page break BEFORE the block: the descriptive instrument starts a
# page of its own.  `keep` marks a block that must not be the LAST on a page - a
# section heading or a column header stranded at the foot is worse than a short page.
# =============================================================================
def blocks():
    out = []

    def add(kind, payload, keep=False, brk=False, sec="X"):
        out.append({"kind": kind, "p": payload, "keep": keep, "brk": brk, "sec": sec})

    for t in ("C", "D"):
        add("sect", ("%s · %d scored items of %d asked%s"
                     % (sf.TASKNAME[t], sf.N_SCORED[t], sf.N_TOTAL[t],
                        ", plus %d gates" % sf.N_GATE[t] if sf.N_GATE[t] else ""),
                     "%d papers" % sf.CENSUS[sf.TASKNAME[t].lower()]),
            keep=True, brk=(t == "D"), sec=t)
        add("thead", ("Item, as the reviewer was asked it", "Response counted as a problem"),
            keep=True, sec=t)
        n = 0
        for dom in sf.DOM_ORDER:
            grp = [x for x in sf.ITEMS if x[1] == t and x[2] == dom]
            if not grp:
                continue
            add("dom", dom, keep=True, sec=t)
            for item, _t, _d, qk, flagged, axis, role, cond in grp:
                if role == sf.SCORED_ROLE:
                    n += 1
                    num, fill = str(n), (REP if axis == "reporting" else VAL, None)
                else:
                    num, fill = "–", MARK[role]
                add("item", (num, sf._Q[qk], plain(flagged), fill, role, bool(cond)), sec=t)
        assert n == sf.N_SCORED[t], (t, n)
    # The closing matter is deliberately NOT given brk: it belongs with the descriptive
    # instrument on page 2, which has the room for it.
    add("sect", ("Items that classify rather than score",
                 "these establish applicability and strata; they carry no problem response"), keep=True)
    add("thead", ("Item, as the reviewer was asked it", "What it does"), keep=True)
    for _i, _lab, qk, what in sf.CLASSIFIERS:
        add("class", (sf._Q[qk], what))
    add("rule", 3.0, keep=True)
    for head, body in sf.FOOTNOTES:
        add("foot", (head, body))
    return out


# --- measuring.  Widths are fixed, so every height is known before paging -----
_m = Page(400.0)


def measure(b):
    k, p = b["kind"], b["p"]
    if k == "sect":
        b["lines"] = None
        b["h"] = line_h(T_HEAD) + 1.4
    elif k == "thead":
        b["h"] = line_h(T_BODY) + 1.6
    elif k == "dom":
        b["h"] = line_h(T_BODY) + 2.2
    elif k == "item":
        num, q, flagged, fill, role, cond = p
        b["q"] = _m.wrap(q, W_ITEM - (3.0 if cond else 0.0))
        b["f"] = _m.wrap(flagged, W_RESP)
        b["h"] = max(len(b["q"]), len(b["f"])) * line_h(T_BODY) + PAD
    elif k == "class":
        q, what = p
        b["q"] = _m.wrap(q, W_ITEM)
        b["f"] = _m.wrap(what, W_RESP)
        b["h"] = max(len(b["q"]), len(b["f"])) * line_h(T_BODY) + PAD
    elif k == "rule":
        b["h"] = p
    elif k == "foot":
        head, body = p
        b["hw"] = _m.width(head, T_BODY, "bold") + 1.2
        b["lines"] = _m.wrap2(body, W - 16.0 - b["hw"], W - 16.0)
        b["h"] = len(b["lines"]) * line_h(T_BODY) + 0.8
    return b


DOC = [measure(b) for b in blocks()]
plt.close(_m.fig)

# top matter is the same height on every page: title, one wrapped sub-line, legend
TOPMATTER = 4.0 + line_h(T_TITLE) + 2 * line_h(T_BODY) + 2.0 + SQ + 3.0


def paginate(doc, limit):
    pages, cur, y = [], [], TOPMATTER
    for i, b in enumerate(doc):
        if b["brk"] and cur:
            pages.append(cur)                     # hard break: a task starts its own page
            cur, y = [], TOPMATTER
        elif y + b["h"] > limit - 4.0 and cur:
            # do not strand a heading: walk back over any trailing keep-blocks
            j = len(cur)
            while j and cur[j - 1]["keep"]:
                j -= 1
            if j == 0:
                j = len(cur)                      # a page of only headings: give up gracefully
            moved, cur = cur[j:], cur[:j]
            pages.append(cur)
            cur, y = moved, TOPMATTER + sum(m["h"] for m in moved)
        cur.append(b)
        y += b["h"]
    if cur:
        pages.append(cur)
    return pages


# Greedy filling put 237 / 240 / 29 mm on three pages - correct, and ugly.  Find the
# fewest pages the content needs, then the SMALLEST page limit that still achieves that
# many, which spreads the content evenly instead of stranding a stub at the end.
NPAGES = len(paginate(DOC, MAXH))
_lo, _hi = 40.0, MAXH
while _hi - _lo > 0.5:
    _mid = (_lo + _hi) / 2
    if len(paginate(DOC, _mid)) <= NPAGES:
        _hi = _mid
    else:
        _lo = _mid
PAGES = paginate(DOC, _hi)
assert len(PAGES) == NPAGES, (len(PAGES), NPAGES)

# ONE PAGE PER TASK.  The whole point of the hard break, asserted rather than assumed:
# if a future edit lengthens the causal instrument past the ceiling it must fail loudly
# here, not quietly become three pages that the packager then ships two of.
PAGE_SECS = [sorted({b["sec"] for b in pg}) for pg in PAGES]
assert len(PAGES) == 2, ("S9 must be exactly two pages, one per task", len(PAGES), PAGE_SECS)
assert PAGE_SECS[0] == ["C"], ("page 1 must be the causal instrument alone", PAGE_SECS[0])
assert PAGE_SECS[1] == ["D", "X"], ("page 2 must be the descriptive instrument plus the "
                                    "classifiers and conventions", PAGE_SECS[1])


def draw_page(blocks_on_page, idx, total, H):
    p = Page(H)
    p.T(8.0, 4.0, "Supplementary Table S1. The appraisal instrument"
        + ("" if idx == 0 else ", continued"), T_TITLE, INK, "bold")
    # One page per task, so the sub-line names the instrument on THIS page rather than
    # just counting pages: each page is submitted as a standalone image.
    sub = ("Every item as the reviewer was asked it, and the response the scorer counts as a "
           "methodological problem. Page 1 of %d is the causal instrument. Predictive studies "
           "(%d papers) are assigned no reporting or validity items and are not scored, leaving "
           "%d of the %d papers appraised."
           % (total, sf.CENSUS["predictive"],
              sf.CENSUS["causal"] + sf.CENSUS["descriptive"], sf.CENSUS["total"])) if idx == 0 else \
          ("Page %d of %d: the descriptive instrument, the items that classify rather than score, "
           "and the conventions the scorer applies to both pages." % (idx + 1, total))
    _sublines = p.wrap(sub, W - 16.0)
    assert len(_sublines) <= 2, ("sub-line outgrew the space TOPMATTER reserves for it",
                                 idx + 1, len(_sublines))
    p.block(8.0, 4.0 + line_h(T_TITLE), _sublines, c=MUT)
    y = 4.0 + line_h(T_TITLE) + 2 * line_h(T_BODY) + 2.0
    # The legend keys only the marks that actually appear on THIS page.  Each page is a
    # standalone figure for one task, and the descriptive instrument has no gates - a key
    # for a mark the reader cannot find is worse than a shorter legend.
    LEGEND = (("reporting item, counts", REP), ("validity item, counts", VAL),
              ("gate, routes skip logic", GATEC))
    used = {b["p"][3][0] for b in blocks_on_page if b["kind"] == "item" and b["p"][3]}
    assert used <= {fc for _lab, fc in LEGEND}, ("an unkeyed mark reached the page", used)
    lx = 8.0
    for lab, fc in LEGEND:
        if fc not in used:
            continue
        p.sq(lx, y, fc, None)
        p.T(lx + SQ + 1.3, y + SQ / 2, lab, T_BODY, MUT, va="center")
        lx += SQ + 1.3 + p.width(lab, T_BODY) + 5.0
    assert lx < W, lx
    y = TOPMATTER

    for b in blocks_on_page:
        k, pl = b["kind"], b["p"]
        if k == "sect":
            p.T(8.0, y, pl[0], T_HEAD, INK, "bold")
            p.T(8.0 + p.width(pl[0], T_HEAD, "bold") + 2.5, y + 0.7, "·  " + pl[1], T_BODY, MUT)
        elif k == "thead":
            p.T(C_NUM, y, "#", T_BODY, MUT, "bold", ha="right")
            p.T(C_ITEM, y, pl[0], T_BODY, MUT, "bold")
            p.T(C_RESP, y, pl[1], T_BODY, MUT, "bold")
            p.ax.add_line(plt.Line2D([8.0, W - 2.0], [y + line_h(T_BODY) + 0.5] * 2,
                                     color=RULE, lw=0.5, zorder=2))
        elif k == "dom":
            p.ax.add_patch(Rectangle((8.0, y - 0.4), W - 10.0, line_h(T_BODY) + 1.6,
                                     fc=BAND, ec="none", zorder=1))
            p.T(C_ITEM - 2.0, y + 0.4, pl, T_BODY, AC, "bold")
        elif k in ("item", "class"):
            if k == "item":
                num, q, flagged, fill, role, cond = pl
                ind = 3.0 if cond else 0.0
                col = GREY if role != sf.SCORED_ROLE else INK
                p.T(C_NUM, y, num, T_BODY, MUT, ha="right")
                if fill:
                    p.sq(C_MARK - SQ / 2, y - 0.1, fill[0], fill[1])
            else:
                ind, col, role = 0.0, INK, sf.SCORED_ROLE
            p.block(C_ITEM + ind, y, b["q"], c=col)
            p.block(C_RESP, y, b["f"], c=GREY if role != sf.SCORED_ROLE else MUT)
            p.ax.add_line(plt.Line2D([8.0, W - 2.0], [y + b["h"] - PAD / 2] * 2,
                                     color="#eef1f3", lw=0.4, zorder=1))
        elif k == "rule":
            p.ax.add_line(plt.Line2D([8.0, W - 2.0], [y + pl / 2] * 2, color=RULE, lw=0.5, zorder=2))
        elif k == "foot":
            p.T(8.0, y, pl[0], T_BODY, INK, "bold")
            p.T(8.0 + b["hw"], y, b["lines"][0], T_BODY, MUT)
            p.block(8.0, y + line_h(T_BODY), b["lines"][1:], c=MUT)
        y += b["h"]
    p.used = y
    return p


# =============================================================================
# Draw, check, write
# =============================================================================
# one measuring pass to find the tallest page, then redraw them all at that height so
# the pages are a uniform size, snug rather than padded to the 245 mm ceiling
_probe = [draw_page(pg, i, len(PAGES), MAXH) for i, pg in enumerate(PAGES)]
PAGE_H = max(x.used for x in _probe) + 4.0
for x in _probe:
    plt.close(x.fig)

rendered = []
for i, pg in enumerate(PAGES):
    p = draw_page(pg, i, len(PAGES), PAGE_H)
    p.fig.canvas.draw()
    rend = p.fig.canvas.get_renderer()
    mm = lambda px: px / p.fig.dpi * 25.4
    assert min(p.sizes) >= MIN_PT, min(p.sizes)
    assert p.used <= PAGE_H, ("page overflowed", i + 1, p.used)
    boxes, spill = [], []
    for t in p.ax.texts:
        b = t.get_window_extent(rend)
        x0, x1, y0, y1 = mm(b.x0), mm(b.x1), mm(b.y0), mm(b.y1)
        if x0 < -0.2 or x1 > W + 0.2 or y0 < -0.2 or y1 > PAGE_H + 0.2:
            spill.append((i + 1, round(x0, 1), round(x1, 1), t.get_text()[:50]))
        boxes.append((y0, y1, x0, x1, t.get_text()))
    assert not spill, spill
    clash = [(i + 1, a[4][:26], b[4][:26]) for j, a in enumerate(boxes) for b in boxes[j + 1:]
             if a[2] < b[3] - 0.2 and a[3] > b[2] + 0.2 and a[0] < b[1] - 0.2 and a[1] > b[0] + 0.2]
    assert not clash, clash[:6]
    rendered.append(p)

base = os.path.join(OUTDIR, STEM)
for f in glob.glob(base + "_p*.tif") + glob.glob(base + "_p*.png"):
    os.remove(f)                                  # a shorter run must not leave stale pages
with PdfPages(base + ".pdf") as pdf:
    for p in rendered:
        pdf.savefig(p.fig, facecolor="white")

from PIL import Image
Image.MAX_IMAGE_PIXELS = None
for i, p in enumerate(rendered, 1):
    png = "%s_p%d.png" % (base, i)
    p.fig.savefig(png, dpi=600, facecolor="white")
    im = Image.open(png)
    rgb = Image.new("RGB", im.size, "white")
    rgb.paste(im, mask=im.split()[3] if im.mode == "RGBA" else None)
    rgb.save("%s_p%d.tif" % (base, i), format="TIFF", compression="tiff_lzw", dpi=(600, 600))
    im.close(); plt.close(p.fig)

from pypdf import PdfReader
_r = PdfReader(base + ".pdf")
assert len(_r.pages) == len(rendered)
for pg in _r.pages:
    for _k, _v in pg["/Resources"]["/Font"].items():
        fo = _v.get_object(); df = fo.get("/DescendantFonts")
        d = df[0].get_object() if df else fo
        desc = d.get("/FontDescriptor")
        assert d.get("/Subtype") != "/Type3" and desc and any(
            x in desc for x in ("/FontFile", "/FontFile2", "/FontFile3")), fo.get("/BaseFont")
        assert "Arial" in str(fo.get("/BaseFont")), fo.get("/BaseFont")
for i in range(1, len(rendered) + 1):
    t = Image.open("%s_p%d.tif" % (base, i))
    assert t.mode == "RGB" and t.tag_v2[259] == 5 and t.info["dpi"] == (600.0, 600.0)
    t.close()

print("  %-52s %8.1f KB  (%d pages)"
      % (base + ".pdf", os.path.getsize(base + ".pdf") / 1024, len(rendered)))
for i in range(1, len(rendered) + 1):
    for ext in ("tif", "png"):
        f = "%s_p%d.%s" % (base, i, ext)
        print("  %-52s %8.1f KB" % (f, os.path.getsize(f) / 1024))
print("  %d pages of %.0f x %.0f mm, filled to %s mm; smallest type %.1f pt"
      % (len(rendered), W, PAGE_H, " / ".join("%.0f" % p.used for p in rendered), MIN_PT))
print("  causal %d scored of %d asked + %d gates; descriptive %d of %d"
      % (sf.N_SCORED["C"], sf.N_TOTAL["C"], sf.N_GATE["C"], sf.N_SCORED["D"], sf.N_TOTAL["D"]))
