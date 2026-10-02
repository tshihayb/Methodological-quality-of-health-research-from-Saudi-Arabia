# -*- coding: utf-8 -*-
"""Table 1 as a Word table, for journals that want a .docx rather than a web artifact.

    python code/tables/08_22_2026_table1_word.py

WHY IT IS THREE PANELS AND NOT ONE TABLE
The artifact is a three-way table: 15 rows (3 study tasks, each followed by its designs)
by 23 columns (Overall plus 22 stratum levels).  Landscape Letter at 0.6 in margins gives
14,112 dxa of usable width.  A cell reading "268 (69.6)" needs about 1,050 dxa at 8 pt, so
22 data columns want ~23,100 dxa - 1.6x what the page has, and no legible type size closes
that gap.  Shrinking below the 6.5 pt floor the rest of the submission observes is not an
option either.

So the columns are split into three panels, grouped by what they measure, each on the same
row stub.  Every panel repeats the Overall column, which costs one column and makes each
panel readable on its own instead of sending the reader back to panel A to get a baseline.

Rejected alternatives, for the record:
  - Transpose (levels as rows, task/design as columns).  Still 14 wide columns, and it puts
    the long design names into the header where they wrap worst.
  - Collapse to Overall + the three tasks.  That is the conventional journal Table 1 and it
    fits portrait easily - but it drops the design x stratifier cross-tabulation, which is
    most of what this table is for.  If a journal demands one page, that is the version to
    negotiate down to, and it should be a deliberate loss, not a silent one.

⚠ ONE SOURCE.  The derivation is imported from code/tables/_gen_table1.py, so the Word
table cannot disagree with the HTML artifact.  Importing it also rewrites the HTML, which
is intentional: the two are built from one run.  The totals are asserted below.

OUTPUT
  outputs/tables/08_22_2026_table1_study_characteristics.docx
"""
import os, importlib.util
from docx import Document
from docx.shared import Pt, Emu, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

D = r"."
os.chdir(D)

_spec = importlib.util.spec_from_file_location("t1", "code/tables/_gen_table1.py")
t1 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(t1)          # also rewrites the HTML artifact - one run, one source

# ⚠ `strata` gained a 4th field (the column's share denominator) when funding was added as a
# second block in the HTML: every stratum is now (group, level, mask, base). Funding lives in
# its own list, `strata_f`, because its funder-origin columns are denominated on the funded
# papers rather than on N -- so the two cannot simply be concatenated for the share line.
w, TASKS = t1.w, t1.TASKS
design_order, N, N_FUNDED = t1.design_order, t1.N, t1.N_FUNDED
# Funding becomes panel D. Its Overall column is dropped here (index 0 of strata_f), because
# every Word panel already repeats the shared Overall from `strata`.
strata = list(t1.strata) + list(t1.strata_f[1:])
Ns = [int(m.sum()) for _g, _l, m, _b in strata]

_kspec = importlib.util.spec_from_file_location("kit", "code/tables/_docx_table_kit.py")
kit = importlib.util.module_from_spec(_kspec); _kspec.loader.exec_module(kit)

OUT = "outputs/tables/08_22_2026_table1_study_characteristics.docx"
dxa = kit.dxa

# The stub only has to hold "Randomized clinical trial" (~1.4 in at 8 pt), so 1.9 in is
# ample; it was 2.4 in and the extra went nowhere useful.  The width matters because the
# widest panel divides what is left by ten, and at 3400 the column denominators wrapped
# mid-label ("n=274" / "(71.2%)").
STUB = 2760
INK, MUT, FAINT, ACCENT, BAND = kit.INK, kit.MUT, kit.FAINT, kit.ACCENT, kit.BAND

# --- panels: which strata indices, in order.  Index 0 is Overall, repeated in each. -------
_NB = len(t1.strata)          # where the funding strata start
PANELS = [
    ("A", "Overall, Saudi data use and team size",        [0, 1, 2, 3, 4, 5]),
    ("B", "Saudi authorship",                             [0, 6, 7, 8, 9, 10, 11, 12, 13]),
    ("C", "Institution sector and journal quartile",      [0, 14, 15, 16, 17, 18, 19, 20, 21, 22]),
    ("D", "Funding",                                      [0] + list(range(_NB, len(strata)))),
]
# every stratum level must appear exactly once outside the repeated Overall column
_seen = [i for _l, _t, idx in PANELS for i in idx if i != 0]
assert sorted(_seen) == list(range(1, len(strata))), ("panels must cover every stratum once", _seen)

# The stub shortens two design names that would otherwise wrap to four lines; the full
# wording is restored in the footnotes.  The other two shortenings happen upstream in
# _gen_table1.py, and are footnoted here for the same reason.
STUB_SHORT = {
    "Quasi-experimental (including instrumental variables, difference-in-difference, "
    "regression discontinuity design, and interrupted time series)": "Quasi-experimental",
}

doc, CONTENT = kit.new_document(landscape=True, size=8)

# the helpers that need raw OOXML live in the shared kit, so Table 1 and Table 2 cannot
# drift apart on the details that decide whether a table survives pagination
para, shade, borders = kit.para, kit.shade, kit.borders
repeat_header, cant_split, keep_next = kit.repeat_header, kit.cant_split, kit.keep_next


def fmt(n, denom):
    return "—" if denom == 0 else "%d (%.1f)" % (n, 100.0 * n / denom)


# --- title ------------------------------------------------------------------------------
h = doc.add_paragraph()
h.paragraph_format.space_after = Pt(3)
r = h.add_run("Table 1. Characteristics of the %d sampled studies." % N)
r.font.name, r.font.size, r.bold, r.font.color.rgb = "Arial", Pt(11), True, INK
r2 = h.add_run("  Study task and, within each task, study design — overall and by Saudi data "
               "use, team size, Saudi authorship, institutional sector, journal quartile and "
               "funding.")
r2.font.name, r2.font.size, r2.font.color.rgb = "Arial", Pt(9), MUT

lede = doc.add_paragraph()
lede.paragraph_format.space_after = Pt(9)
rl = lede.add_run(
    "Values are n (%%). Study-task rows give the percentage of the column; indented design "
    "rows give the percentage within that task, and sum to the task above. The %d stratum "
    "columns do not fit one page at a legible size, so they are split into four panels "
    "(A–D) over the same rows; the Overall column is repeated in each panel for reference. "
    "Every stratifier is complete, so its levels sum to %d — except funder origin, which is "
    "defined only among the %d funded papers and sums to those."
    % (len(strata) - 1, N, N_FUNDED))
rl.font.name, rl.font.size, rl.font.color.rgb = "Arial", Pt(8), MUT

# --- one table per panel ----------------------------------------------------------------
NROWS = 3 + sum(len(design_order[t]) for t in TASKS)
assert NROWS == 15, NROWS

masks = [m for _g, _l, m, _b in strata]
checked_tasks = 0

for pi, (letter, panel_title, idx) in enumerate(PANELS):
    ncol = len(idx)
    colw = (CONTENT - STUB) // ncol
    widths = [STUB] + [colw] * ncol

    pt_ = doc.add_paragraph()
    pt_.paragraph_format.space_before = Pt(10 if pi else 2)
    pt_.paragraph_format.space_after = Pt(2)
    pt_.paragraph_format.keep_with_next = True      # never leave a panel title at a page foot
    rp = pt_.add_run("Panel %s. %s" % (letter, panel_title))
    rp.font.name, rp.font.size, rp.bold, rp.font.color.rgb = "Arial", Pt(9), True, ACCENT

    tbl = doc.add_table(rows=2 + NROWS, cols=1 + ncol)
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT
    tbl.autofit = False
    for row in tbl.rows:
        for ci, cw in enumerate(widths):
            row.cells[ci].width = dxa(cw)

    # header row 1: stratifier group names, merged across their levels
    hdr1, hdr2 = tbl.rows[0], tbl.rows[1]
    for r_ in tbl.rows:
        cant_split(r_)
    repeat_header(hdr1); repeat_header(hdr2)
    para(hdr1.cells[0], [("Study task / design", 8, FAINT, True)], WD_ALIGN_PARAGRAPH.LEFT)

    spans, c = [], 1
    for i in idx:
        g = strata[i][0] or "Overall"
        if spans and spans[-1][0] == g:
            spans[-1][2] = c
        else:
            spans.append([g, c, c])
        c += 1
    for g, c0, c1 in spans:
        cellobj = hdr1.cells[c0] if c0 == c1 else hdr1.cells[c0].merge(hdr1.cells[c1])
        para(cellobj, [(g, 8, INK, True)], WD_ALIGN_PARAGRAPH.CENTER)
        shade(cellobj, BAND)

    # header row 2: level name + column denominator
    para(hdr2.cells[0], [("", 8, INK, False)], WD_ALIGN_PARAGRAPH.LEFT)
    for k, i in enumerate(idx, start=1):
        lvl, base, Nc = strata[i][1], strata[i][3], Ns[i]
        cellobj = hdr2.cells[k]
        p = para(cellobj, [(lvl, 8, INK, True)], WD_ALIGN_PARAGRAPH.RIGHT)
        p2 = cellobj.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p2.paragraph_format.space_after = Pt(0)
        # `base` is N for every stratifier except funder origin, which is defined only among
        # the funded papers and is shown as a share of those.
        rr = p2.add_run("n=%d (%s)" % (Nc, "100%" if Nc == base
                                       else "%.1f%%" % (100.0 * Nc / base)))
        rr.font.name, rr.font.size, rr.font.color.rgb = "Arial", Pt(6.5), FAINT
    for cellobj in hdr2.cells:
        borders(cellobj, bottom=(12, "1B2029"))
    keep_next(hdr1); keep_next(hdr2)

    # body
    ri = 2
    for t in TASKS:
        tmask = w.Study_Type == t
        row = tbl.rows[ri]; ri += 1
        para(row.cells[0], [(t, 8, INK, True)], WD_ALIGN_PARAGRAPH.LEFT)
        borders(row.cells[0], top=(6, "8B95A1"))
        for k, i in enumerate(idx, start=1):
            n = int((masks[i] & tmask).sum())
            para(row.cells[k], [(fmt(n, Ns[i]), 8, INK, True)])
            borders(row.cells[k], top=(6, "8B95A1"))
        # the three task rows must account for every paper in every column
        checked_tasks += 1

        for d in design_order[t]:
            dmask = tmask & (w.design == d)
            row = tbl.rows[ri]; ri += 1
            para(row.cells[0], [("    " + STUB_SHORT.get(str(d), str(d)), 8, MUT, False)],
                 WD_ALIGN_PARAGRAPH.LEFT)
            for k, i in enumerate(idx, start=1):
                n = int((masks[i] & dmask).sum())
                tn = int((masks[i] & tmask).sum())
                para(row.cells[k], [(fmt(n, tn), 8, MUT, False)])
    assert ri == 2 + NROWS, (ri, NROWS)

# =============================================================================
# Assertions - the arithmetic a reader will check, checked here first
# =============================================================================
assert checked_tasks == len(PANELS) * len(TASKS), checked_tasks
for i, (g, lvl, m, base) in enumerate(strata):
    tot = sum(int((m & (w.Study_Type == t)).sum()) for t in TASKS)
    assert tot == Ns[i], ("task rows must sum to the column N", lvl, tot, Ns[i])
    for t in TASKS:
        tn = int((m & (w.Study_Type == t)).sum())
        dsum = sum(int((m & (w.Study_Type == t) & (w.design == d)).sum()) for d in design_order[t])
        assert dsum == tn, ("design rows must sum to their task", lvl, t, dsum, tn)
# A stratifier's levels sum to its own base -- N for all of them except funder origin, which
# is defined only among the funded and sums to those. Asserting N here would have failed the
# moment funding was added, which is the point of carrying the base on the stratum.
for g in {s[0] for s in strata if s[0]}:
    base = next(s[3] for s in strata if s[0] == g)
    lv = sum(Ns[i] for i, s in enumerate(strata) if s[0] == g)
    assert lv == base, ("a stratifier's levels must sum to its base", g, lv, base)

# --- footnotes --------------------------------------------------------------------------
FOOT = [
    ("Panels.", "A–D carry the same 15 rows and differ only in which stratum columns they "
                "show; Overall is repeated in each. A panel is not a subgroup — every panel "
                "describes all %d studies. The split is a page-width device and carries no "
                "other meaning." % N),
    ("Funding (panel D).", "Coded from the full text of all %d papers. Funded = the paper "
                "states that this study received money, or personnel or equipment paid for "
                "by a named body, scheme or grant number. Non-funded = it explicitly "
                "declares it received none. Not stated = it resolves neither way. Funder "
                "origin is defined only among the %d funded and sums to those. A publication "
                "fee — an article-processing charge or an open-access agreement — is not "
                "research funding, so a paper whose only money pays for publication is "
                "recorded as not stated; %d papers turn on that rule alone, and counting "
                "their publication money as research funding instead would give funded %d "
                "(%s%%) rather than %d (%s%%). Funding is descriptive: nothing here supports "
                "a causal claim linking funders to study quality."
                % (N, N_FUNDED, t1.FUND['n_apc'], t1.FUND['f_hi'], t1.FUND['f_hi_p'],
                   t1.FUND['f_lo'], t1.FUND['f_lo_p'])),
    ("Design names.", "\u201cRandomized clinical trial\u201d includes all types of randomized "
                      "experiment; \u201cCohort\u201d includes clinical trials without "
                      "randomization; \u201cQuasi-experimental\u201d includes instrumental "
                      "variables, difference-in-differences, regression discontinuity and "
                      "interrupted time series. Predictive designs are Diagnostic and "
                      "Prognostic, which carry no epidemiological bias items (see Table 2)."),
    ("Saudi data use.", "The study used data from Saudi Arabia, as recorded by the instrument "
                        "for that task."),
    ("Number of authors.", "Team size, counting only authors with a real surname — collective "
                           "and group entries are not authors. Median 6, IQR 4–9, range 1–377."),
    ("% Saudi authors.", "Whether at least half the author list is Saudi-affiliated."),
    ("Corresponding / First / Last author.", "Whether that author's affiliation is Saudi."),
    ("Sector composition.", "Health-system = at least one Saudi author at a hospital, medical "
                            "city, Ministry of Health or military-health body; Academic-only = "
                            "university or academic affiliations only. Single vs multi-sector = "
                            "whether the paper's Saudi authors span more than one Saudi "
                            "institution type."),
    # Numbers come from t1.BOUND -- computed in _gen_table1.py, never typed here, so the
    # Word and HTML footnotes cannot drift apart.
    ("Both sector stratifiers are bounds, not points.",
        "Each Saudi author is credited to the single institution their affiliation names as "
        "top-level employer; where an affiliation names more than one, the others are not "
        "recorded, so a paper can lose a sector but never gain one. Crediting instead every "
        "institution each author is on record for moves %d papers from Academic-only to "
        "Health-system and %d from single- to multi-sector, giving Health-system %d "
        "(Academic-only %d) and Multi-sector %d (Single-sector %d). The columns above use the "
        "single-institution rule (%d and %d); read the pair as a bound. Within it no study-task "
        "percentage moves by more than %s points and no ordering changes."
        % (t1.BOUND["moved_comp"], t1.BOUND["moved_msec"], t1.BOUND["hs_hi"], t1.BOUND["ao_hi"],
           t1.BOUND["ms_hi"], t1.BOUND["ss_hi"], t1.BOUND["hs_lo"], t1.BOUND["ms_lo"],
           t1.BOUND["max_shift"])),
    # ⚠ "absent from JCR 2022" was FALSE for 32 of the 87 papers: ESCI journals appear in
    # JCR 2022 WITH an impact factor and no quartile, and a suppressed JIF is a journal that
    # is present and flagged, not missing. The identical error was corrected in the old
    # Table 4 footnote on 2026-08-15 and never propagated here. Verified 2026-08-26 against
    # the jcr_note column: 49 delisted / 27 ESCI / 6 never indexed / 5 suppressed.
    ("JCR 2022 quartile.", 'Clarivate Journal Citation Reports 2022 impact-factor quartile. Not ranked = no 2022 quartile, which is NOT the same as no impact factor: of these 87 papers, 27 are in 22 journals indexed in the Emerging Sources Citation Index in 2022, which carry a JIF but are assigned no quartile; 49 are in 4 journals delisted from the Web of Science Core Collection before the 2022 edition; 5 are in 2 journals whose 2022 JIF was suppressed; and 6 are in 5 journals not in the Core Collection at all. Composition in Supplementary Methods 4 and Supplementary Figure S4D.'),
    ("Coding.", "Study tasks and designs are as coded by the reviewers and adjudicators; the "
                "2026-08-12 inconsistency-resolution worklist relabelled no design and no "
                "follow-up."),
    ("Two cautions on the stratifiers.", "(i) Corresponding author is largely redundant with "
        "first author: the corresponding author is the first author in 67.3% of papers and the "
        "last in 24.1% (first-or-last 84.8%), and corresponding-author Saudi status agrees with "
        "first-author status 90.9% of the time versus 79.2% with last. Treat first versus last "
        "as the substantive contrast. (ii) Team size is confounded with Saudi affiliation "
        "(Spearman −0.36 with % Saudi authors): every single-author paper is ≥50% Saudi by "
        "inclusion and 84.0% of one- or two-author papers are entirely Saudi, versus 43.3% of "
        "papers with 11+ authors. Read the team-size columns as collaboration scale, not as a "
        "further affiliation measure."),
]
sp = doc.add_paragraph()
sp.paragraph_format.space_before = Pt(10)
sp.paragraph_format.space_after = Pt(3)
rs = sp.add_run("Notes")
rs.font.name, rs.font.size, rs.bold, rs.font.color.rgb = "Arial", Pt(8.5), True, INK
for head, body in FOOT:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    rh = p.add_run(head + " ")
    rh.font.name, rh.font.size, rh.bold, rh.font.color.rgb = "Arial", Pt(7.5), True, MUT
    rb = p.add_run(body)
    rb.font.name, rb.font.size, rb.font.color.rgb = "Arial", Pt(7.5), FAINT

doc.save(OUT)
print("  %-58s %8.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
print("  %d panels, %d rows each, %s data columns; landscape Letter, %.2f in usable"
      % (len(PANELS), NROWS, "/".join(str(len(i)) for _l, _t, i in PANELS), CONTENT / 1440))
print("  N = %d = %s" % (N, " + ".join("%s %d" % (t, int((w.Study_Type == t).sum())) for t in TASKS)))
