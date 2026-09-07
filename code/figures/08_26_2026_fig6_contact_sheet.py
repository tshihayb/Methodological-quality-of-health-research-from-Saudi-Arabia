# -*- coding: utf-8 -*-
"""Contact sheet of the Figure 6 candidates — all of them on one page, at true relative height.

    python code/figures/08_26_2026_fig6_contact_sheet.py

Run 08_26_2026_fig6_candidates.py first.  Each thumbnail is scaled to a common WIDTH, so the
heights on this sheet are the candidates' real heights relative to one another — a design that
runs to 239 mm looks tall here because it is.  Under each one: what it argues, and its height.

OUTPUT  outputs/figures/candidates/08_26_2026_fig6_CONTACT_SHEET.png
"""
import os, glob
from PIL import Image, ImageDraw, ImageFont

D = r"."
os.chdir(D)
Image.MAX_IMAGE_PIXELS = None
SRC = "outputs/figures/candidates"
OUT = "%s/08_26_2026_fig6_CONTACT_SHEET.png" % SRC

PITCH = {  # letter -> (one-line argument, the encoding it turns on)
    "A": ("Figure 5's shared spine, re-indexed to groups", "stacked verdict + severity + band"),
    "B": ("does any group sit clear of its task mean?", "forest, 95% CIs"),
    "C": ("how far is each group from its task mean?", "diverging bars, zero-centred"),
    "D": ("which variable separates at all — ranked", "lollipop min→max"),
    "E": ("ten panels that cannot be rescaled to look decisive", "small multiples, shared scale"),
    "F": ("validity against reporting, one point per group", "scatter, point area scaled to n"),
    "G": ("every variable × every measure, on one ruler", "separation matrix in SD units"),
    "H": ("the task gap dwarfs every group gap", "dumbbells across tasks"),
    "I": ("Figure 5 panel D, stratified", "index scatter + quadrant strip"),
    "J": ("Figure 5 panel K, stratified", "acknowledgement bars"),
    "K": ("the distributions, not the means", "per-level kernel densities"),
    "L": ("the current figure, print-native on the graded axis", "table of bars"),
    "M": ("only what separates; the rest disposed of", "compact result + strip"),
    "N": ("where a variable reverses between tasks", "slopegraph"),
}

NCOL = 5
THUMB_W = 620
PAD, GAPX, GAPY = 26, 18, 14
LABEL_H = 74
BG, INK, MUT, FAINT = (255, 255, 255), (17, 20, 23), (74, 82, 89), (139, 143, 148)


def font(sz, bold=False):
    for nm in (("arialbd.ttf",) if bold else ("arial.ttf",)):
        try:
            return ImageFont.truetype(nm, sz)
        except OSError:
            pass
    return ImageFont.load_default()


F_L, F_T, F_S = font(40, True), font(19, True), font(17)

files = sorted(glob.glob("%s/08_26_2026_fig6_?.png" % SRC))
assert files, "run 08_26_2026_fig6_candidates.py first"
thumbs = []
for f in files:
    k = os.path.basename(f).split("_")[-1][0]
    im = Image.open(f).convert("RGB")
    h = round(im.height * THUMB_W / im.width)
    thumbs.append((k, im.resize((THUMB_W, h), Image.LANCZOS), h))
print("  %d candidates, tallest %d px at %d px wide" % (len(thumbs), max(t[2] for t in thumbs),
                                                        THUMB_W))

rows = [thumbs[i:i + NCOL] for i in range(0, len(thumbs), NCOL)]
row_h = [max(t[2] for t in r) + LABEL_H for r in rows]
HEAD = 96
Wpx = PAD * 2 + NCOL * THUMB_W + (NCOL - 1) * GAPX
Hpx = HEAD + sum(row_h) + GAPY * (len(rows) - 1) + PAD
sheet = Image.new("RGB", (Wpx, Hpx), BG)
dr = ImageDraw.Draw(sheet)
dr.text((PAD, 24), "Figure 6 re-cut — %d candidate designs" % len(thumbs), INK, F_L)
dr.text((PAD, 70), "all 180 mm wide and shown at true relative height · every one drawn on the "
        "graded severity axis (error_weighted), not the flag count", MUT, F_S)

y = HEAD
for r, row in zip(row_h, rows):
    x = PAD
    for k, im, h in row:
        sheet.paste(im, (x, y))
        dr.rectangle([x, y, x + THUMB_W - 1, y + h - 1], outline=(210, 216, 220), width=1)
        ly = y + h + 8
        dr.text((x, ly), "%s   %s" % (k, PITCH[k][0]), INK, F_T)
        dr.text((x, ly + 24), PITCH[k][1], MUT, F_S)
        dr.text((x, ly + 46), "%.0f mm tall" % (im.height / THUMB_W * 180.0), FAINT, F_S)
        x += THUMB_W + GAPX
    y += r + GAPY

sheet.save(OUT)
print("  wrote %s  (%d x %d px, %.1f MB)" % (OUT, Wpx, Hpx, os.path.getsize(OUT) / 1e6))
