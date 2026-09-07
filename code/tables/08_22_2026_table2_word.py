# -*- coding: utf-8 -*-
"""Table 2 as a Word table, beside the HTML artifact.

    python code/tables/08_22_2026_table2_word.py

WHY THIS IS NOT THE SAME PROBLEM AS TABLE 1, DESPITE LOOKING LIKE IT
Table 1 is short and very wide - 15 rows by 23 columns - so it had to be split into panels
across the page.  Table 2 is the opposite shape: **3 columns and 149 rows**.  Width is a
non-issue; portrait Letter holds it comfortably.  What Table 2 needs is length handling, so
this is ONE table that flows over pages, with the header repeated and nothing stranded:

  - the column header repeats at the top of every page (a page of bare numbers is useless);
  - a domain, a sub-domain or an item heading is bound to the row beneath it, so no heading
    ever sits alone at a page foot;
  - no row splits across a page break.

Panelling Table 2 the way Table 1 is panelled would be actively wrong: it has nothing to
panel, and cutting a 149-row list into page-sized blocks by hand is the standing bet the
S9 pagination notes warn about.

⚠ ARIAL HAS NO ↳ (U+21B3).  The HTML marks conditional items with that arrow; here they are
shown by indentation, and every non-ASCII character actually used is checked against the
font before the document is written.

⚠ ONE SOURCE.  This RE-RUNS code/tables/_gen_table2.py and then parses the slim variant it
just wrote, so the Word table is built from the very bytes the HTML artifact ships rather
than from a second derivation that could disagree.  Parsing is guarded: the row-class
vocabulary, the cell counts and the totals are all asserted, so a change to the generator's
markup fails this build loudly instead of quietly producing a wrong table.

OUTPUT
  outputs/tables/08_22_2026_table2_item_distribution.docx
"""
import os, re, html as H, runpy, importlib.util
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Pt

D = r"."
os.chdir(D)
_spec = importlib.util.spec_from_file_location("kit", "code/tables/_docx_table_kit.py")
kit = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(kit)

SRC = "outputs/tables/07_23_2026_table2_item_distribution_by_option_slim.html"
OUT = "outputs/tables/08_22_2026_table2_item_distribution.docx"

runpy.run_path("code/tables/_gen_table2.py", run_name="__main__")   # refresh, then parse
page = open(SRC, encoding="utf-8").read()

# =============================================================================
# Parse the artifact.  Every expectation is asserted; see the docstring.
# =============================================================================
txt = lambda s: H.unescape(re.sub(r"<[^>]+>", "", s)).strip()

thead = re.search(r"<thead>(.*?)</thead>", page, re.S).group(1)
heads = [txt(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", thead, re.S)]
assert len(heads) == 3, ("the slim Table 2 must have 3 columns", heads)
assert heads[1].startswith("Descriptive") and heads[2].startswith("Causal"), heads
COLS = [re.match(r"(\S+)\s*(n = .*)", h).groups() for h in heads[1:]]

tbody = re.search(r"<tbody>(.*?)</tbody>", page, re.S).group(1)
raw = re.findall(r"<tr class=\"([^\"]*)\"[^>]*>(.*?)</tr>", tbody, re.S)
assert len(raw) == len(re.findall(r"<tr", tbody)), "every body row must carry a class"

KNOWN = {"dom", "subdom", "item", "item dep", "cat ok", "cat prob", "cat None", "cat nna"}
assert {c for c, _ in raw} <= KNOWN, ("unknown row class", {c for c, _ in raw} - KNOWN)

PAD = lambda cell: int((re.search(r"padding-left:(\d+)px", cell) or [0, "0"])[1]
                       if re.search(r"padding-left:(\d+)px", cell) else 0)


def parse(cls, body):
    """-> dict(kind, label, tags, indent_px, cells)  cells = [] for a full-width heading."""
    tds = re.findall(r"<t[hd]([^>]*)>(.*?)</t[hd]>", body, re.S)
    attrs0, first = tds[0]
    ind = int(m.group(1)) if (m := re.search(r"padding-left:(\d+)px", attrs0)) else 0
    tags = [txt(t) for t in re.findall(r"<span class=\"(?:sc sc-\w|tp \w+)\">(.*?)</span>", first, re.S)]
    label = txt(re.sub(r"<span class=\"(tags|nalbl)\".*?</span>\s*", "", first, flags=re.S))
    for t in tags:                                    # the tag text rides inside the label span
        label = label.replace(t, "").strip()
    label = re.sub(r"\s*applies to\s*→\s*$", "", label).strip()
    # ⚠ Drop the artifact's ↳ (U+21B3): Arial cannot draw it and would print a box.  The
    # conditional relationship is carried by the indentation, which we keep verbatim from
    # the HTML's padding-left.  assert_glyphs() below is what caught this.
    label = label.lstrip("↳").strip()
    cells = [txt(c) for _a, c in tds[1:]]
    return {"kind": cls, "label": label, "tags": tags, "indent": ind, "cells": cells,
            "base": "applies to" in first}


ROWS = [parse(c, b) for c, b in raw]
NDOM = sum(r["kind"] == "dom" for r in ROWS)
NITEM = sum(r["kind"].startswith("item") for r in ROWS)
NCAT = sum(r["kind"].startswith("cat") for r in ROWS)
# Exact counts, as a tripwire on the artifact's shape.  They are not arbitrary:
# 2026-08-22 this caught the option-splitting fix in _gen_table2.py, which removed two
# fabricated confounding-method rows and merged a third back into the real option
# (responses 101 -> 99, total rows 149 -> 147).  If these numbers move again, something
# changed the instrument or the parser, and that is worth stopping the build for.
assert (NDOM, NITEM, NCAT) == (7, 36, 99), (NDOM, NITEM, NCAT)
assert len(ROWS) == 147, len(ROWS)
for r in ROWS:
    assert len(r["cells"]) in (0, 2), (r["kind"], r["label"], r["cells"])
    if r["kind"].startswith("cat"):
        assert len(r["cells"]) == 2, ("a response row needs both task columns", r["label"])

kit.assert_glyphs("".join(r["label"] + "".join(r["tags"]) + "".join(r["cells"]) for r in ROWS))

# =============================================================================
# Draw
# =============================================================================
doc, USABLE = kit.new_document(landscape=False, size=8)
LBL = USABLE - 2 * 1500
WIDTHS = [LBL, 1500, 1500]
PX = 11.0                                     # HTML padding-left px -> twips of Word indent

title = doc.add_paragraph()
title.paragraph_format.space_after = Pt(3)
r = title.add_run("Table 2. Distribution of every instrument item across its response options,")
r.font.name, r.font.size, r.bold, r.font.color.rgb = "Arial", Pt(11), True, kit.INK
r = title.add_run(" by study task and applicable base.")
r.font.name, r.font.size, r.font.color.rgb = "Arial", Pt(11), kit.INK

lede = doc.add_paragraph()
lede.paragraph_format.space_after = Pt(4)
r = lede.add_run(
    "Response distribution of every tool item across seven domains, shown separately for the "
    "descriptive and causal papers. Where an item does not apply to every paper — a parent "
    "question skipped it, or it was not applicable — the count it applies to sits on the item "
    "line and the response percentages below are computed within that base; those items are "
    "also indented. Items applying to all papers are percentaged of their task column.")
r.font.name, r.font.size, r.font.color.rgb = "Arial", Pt(8), kit.MUT

key = doc.add_paragraph()
key.paragraph_format.space_after = Pt(7)
for chunk, col, bold in [("Causal only / Descriptive only / Both", kit.MUT, True),
                         (" give the tasks an item is put to.   ", kit.MUT, False),
                         ("Indented items", kit.MUT, True),
                         (" are gated by the question above them.   ", kit.MUT, False),
                         ("How each item is scored", kit.MUT, True),
                         (" — whether it is a reporting or a validity question, and which "
                          "response counts as a methodological problem — is given in Figure 4 "
                          "and Supplementary Table S1, not here.", kit.MUT, False)]:
    rr = key.add_run(chunk)
    rr.font.name, rr.font.size, rr.font.color.rgb, rr.bold = "Arial", Pt(7.5), col, bold

tbl = doc.add_table(rows=1 + len(ROWS), cols=3)
tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
tbl.autofit = False
for row in tbl.rows:
    for ci, cw in enumerate(WIDTHS):
        row.cells[ci].width = kit.dxa(cw)

hdr = tbl.rows[0]
kit.repeat_header(hdr); kit.cant_split(hdr); kit.keep_next(hdr)
kit.para(hdr.cells[0], [("Domain / item / response", 8, kit.FAINT, True)], WD_ALIGN_PARAGRAPH.LEFT)
for k, (name, nlab) in enumerate(COLS, start=1):
    c = hdr.cells[k]
    kit.para(c, [(name, 8, kit.INK, True)])
    p2 = c.add_paragraph(); p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p2.paragraph_format.space_after = Pt(0)
    rr = p2.add_run(nlab.replace("n = ", "n="))
    rr.font.name, rr.font.size, rr.font.color.rgb = "Arial", Pt(6.5), kit.FAINT
for c in hdr.cells:
    kit.borders(c, bottom=(12, "1B2029"))

for i, r in enumerate(ROWS):
    row = tbl.rows[1 + i]
    kit.cant_split(row)
    kind, lbl, ind = r["kind"], r["label"], r["indent"]

    if kind in ("dom", "subdom"):
        c = row.cells[0].merge(row.cells[2])
        big = kind == "dom"
        kit.para(c, [(lbl.upper() if big else lbl, 8 if big else 7,
                      kit.ACCENT if big else kit.MUT, True)],
                 WD_ALIGN_PARAGRAPH.LEFT, indent=ind * PX, space_after=1)
        if big:
            kit.shade(c, kit.BAND)
            kit.borders(c, top=(8, "8B95A1"))
        kit.keep_next(row)
        continue

    if kind.startswith("item"):
        runs = [(lbl, 8, kit.INK, True)]
        if r["tags"]:
            runs.append(("   " + " · ".join(r["tags"]), 6.5, kit.FAINT, False))
        if r["base"]:
            runs.append(("   applies to \u2192", 6.5, kit.FAINT, False))
            kit.para(row.cells[0], runs, WD_ALIGN_PARAGRAPH.LEFT, indent=ind * PX, space_after=1)
            for k in (1, 2):
                kit.para(row.cells[k], [(r["cells"][k - 1], 8, kit.MUT, False)])
            # the separator must cross the WHOLE table.  Bordering only cells[0] left a rule
            # that stopped at the label column and read as a stray vertical edge.
            for k in (0, 1, 2):
                kit.borders(row.cells[k], top=(4, "D4D0C6"))
        else:
            c = row.cells[0].merge(row.cells[2])
            kit.para(c, runs, WD_ALIGN_PARAGRAPH.LEFT, indent=ind * PX, space_after=1)
            kit.borders(c, top=(4, "D4D0C6"))
        kit.keep_next(row)
        continue

    # \u26a0 TABLE 2 IS DESCRIPTIVE (TSA, 2026-08-22).  It reports how the papers answered, and
    # says nothing about which answer counts as a problem - that belongs to Figure 4 and to
    # Supplementary Table S1's "response counted as a problem" column, and stating it three
    # times invites the three from drifting apart.  So `cat prob` rows are drawn EXACTLY
    # like every other response row: no marker, no colour, no weight.  The class is still
    # parsed, because the row-count assertions above use it.
    kit.para(row.cells[0], [(lbl, 8, kit.MUT, False)], WD_ALIGN_PARAGRAPH.LEFT, indent=ind * PX)
    for k in (1, 2):
        kit.para(row.cells[k], [(r["cells"][k - 1], 8, kit.MUT, False)])

# --- notes: carried from the artifact, so the two cannot say different things -------------
notes = [txt(f) for f in re.findall(r"<p class=\"foot\">(.*?)</p>", page, re.S)]
assert notes, "the artifact's footnotes must survive into the Word version"
# ⚠ The notes are prose from the artifact and go through the SAME font.  assert_glyphs was
# only being run over the table rows, so a ↳ sitting in a footnote would have printed as a
# box on page 3 with nothing to catch it.  Sanitise, then check what is actually typeset.
notes = [n.replace("↳", "").replace("  ", " ").strip() for n in notes]
kit.assert_glyphs("".join(notes))
sp = doc.add_paragraph()
sp.paragraph_format.space_before = Pt(9); sp.paragraph_format.space_after = Pt(3)
rs = sp.add_run("Notes")
rs.font.name, rs.font.size, rs.bold, rs.font.color.rgb = "Arial", Pt(8.5), True, kit.INK
for n in notes:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    head, _, rest = n.partition(".")
    rh = p.add_run(head + ". ")
    rh.font.name, rh.font.size, rh.bold, rh.font.color.rgb = "Arial", Pt(7.5), True, kit.MUT
    rb = p.add_run(rest.strip())
    rb.font.name, rb.font.size, rb.font.color.rgb = "Arial", Pt(7.5), kit.FAINT

doc.save(OUT)
print("  %-58s %8.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
print("  portrait Letter, %.2f in usable; 1 table, %d rows (%d domains, %d items, %d responses)"
      % (USABLE / 1440, len(ROWS), NDOM, NITEM, NCAT))
print("  columns: %s" % " | ".join("%s %s" % c for c in COLS))
