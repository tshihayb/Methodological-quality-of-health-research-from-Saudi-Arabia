# -*- coding: utf-8 -*-
"""Contact sheet for the two measure-set candidate families (2026-08-26).

    python code/figures/08_26_2026_fig6_contact_sheet_means.py

Two banded rows: the SEVEN-MEASURE set on top, the THREE-INDEX set beneath. Thumbnails share a
common width, so their heights are the candidates' real relative heights.

OUTPUT  outputs/figures/candidates/08_26_2026_fig6_CONTACT_SHEET_MEASURE_SETS.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

D = r"."
os.chdir(D)
Image.MAX_IMAGE_PIXELS = None
SRC = "outputs/figures/candidates"
OUT = "%s/08_26_2026_fig6_CONTACT_SHEET_MEASURE_SETS.png" % SRC

BANDS = [
    ("Seven measures — validity error score · transparency score · domains flawed · domains "
     "gapped · validity index · transparency index · acknowledgement index",
     [("7A", "the matrix: each cell spans that measure's group-mean range",
       "25 groups x 7 measures, dots"),
      ("7B", "which variable moves which measure",
       "7 panels, 10 stratifier lollipops each"),
      ("7C", "every mean printed, shaded within its own column",
       "numeric table"),
      ("7D", "all seven on ONE ruler, oriented worse-to-the-right",
       "signed SD bars, index columns flipped"),
      ("7E", "the question in fourteen rows",
       "spread bars, ends named")]),
    ("Three indices only — validity index · transparency index · acknowledgement index",
     [("3A", "the true 0-1 scale, undistorted",
       "3 dots per group, one shared axis"),
      ("3B", "zoomed, with the noise each group carries",
       "3 forests, 95% CIs"),
      ("3C", "true scale AND the magnified band, together",
       "paired strips, magnification printed"),
      ("3D", "does a group good on one index do well on the others?",
       "3-point profile per group"),
      ("3E", "are these three measurements or one?",
       "pairwise scatters, within-task r")]),
]

THUMB_W = 620
PAD, GAPX, GAPY, LABEL_H = 26, 18, 16, 74
BG, INK, MUT, FAINT = (255, 255, 255), (17, 20, 23), (74, 82, 89), (139, 143, 148)
ACC = (15, 92, 107)


def font(sz, bold=False):
    try:
        return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", sz)
    except OSError:
        return ImageFont.load_default()


F_L, F_B, F_T, F_S = font(40, True), font(23, True), font(19, True), font(17)

loaded = []
for title, items in BANDS:
    row = []
    for code, pitch, enc in items:
        f = "%s/08_26_2026_fig6_%s.png" % (SRC, code)
        assert os.path.exists(f), "run 08_26_2026_fig6_candidates_means.py first: " + f
        im = Image.open(f).convert("RGB")
        h = round(im.height * THUMB_W / im.width)
        row.append((code, pitch, enc, im.resize((THUMB_W, h), Image.LANCZOS), h))
    loaded.append((title, row))

NCOL = 5
HEAD, BANDHEAD = 96, 40
Wpx = PAD * 2 + NCOL * THUMB_W + (NCOL - 1) * GAPX
Hpx = HEAD + sum(BANDHEAD + max(r[4] for r in row) + LABEL_H + GAPY
                 for _t, row in loaded) + PAD
sheet = Image.new("RGB", (Wpx, Hpx), BG)
dr = ImageDraw.Draw(sheet)
dr.text((PAD, 24), "Figure 6 — the two measure sets, 10 candidates", INK, F_L)
dr.text((PAD, 70), "all 180 mm wide and shown at true relative height · both sets compare GROUP "
        "MEANS of Figure 5's study-level measures, nothing per-domain", MUT, F_S)

y = HEAD
for title, row in loaded:
    dr.line([PAD, y, Wpx - PAD, y], fill=ACC, width=3)
    dr.text((PAD, y + 8), title, ACC, F_B)
    y += BANDHEAD
    x = PAD
    tallest = max(r[4] for r in row)
    for code, pitch, enc, im, h in row:
        sheet.paste(im, (x, y))
        dr.rectangle([x, y, x + THUMB_W - 1, y + h - 1], outline=(210, 216, 220), width=1)
        ly = y + tallest + 8
        dr.text((x, ly), "%s   %s" % (code, pitch), INK, F_T)
        dr.text((x, ly + 24), enc, MUT, F_S)
        dr.text((x, ly + 46), "%.0f mm tall" % (im.height / THUMB_W * 180.0), FAINT, F_S)
        x += THUMB_W + GAPX
    y += tallest + LABEL_H + GAPY

sheet.save(OUT)
print("  wrote %s  (%d x %d px, %.1f MB)" % (OUT, Wpx, Hpx, os.path.getsize(OUT) / 1e6))
